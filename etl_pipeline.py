"""
SAP Financial Reconciliation - ETL Pipeline
============================================
Ingests GL entries, vendor invoices, and bank statements,
runs reconciliation logic, and outputs exception report.
"""

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from datetime import datetime, date
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

DB_URL = os.getenv("DB_URL", "mysql+mysqlconnector://root:password@localhost/sap_reconciliation")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_gl_entries(engine) -> pd.DataFrame:
    """Extract GL entries joining BKPF + BSEG."""
    query = """
        SELECT
            h.belnr      AS doc_number,
            h.bukrs      AS company_code,
            h.blart      AS doc_type,
            h.budat      AS posting_date,
            h.waers      AS currency,
            h.xblnr      AS reference,
            l.buzei      AS line_item,
            l.koart      AS account_type,
            l.hkont      AS gl_account,
            l.lifnr      AS vendor_id,
            l.dmbtr      AS amount,
            l.sgtxt      AS description,
            l.augdt      AS clearing_date,
            l.augbl      AS clearing_doc
        FROM bkpf h
        JOIN bseg l
            ON h.mandt = l.mandt
           AND h.bukrs = l.bukrs
           AND h.belnr = l.belnr
           AND h.gjahr = l.gjahr
        WHERE h.budat >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        ORDER BY h.budat DESC
    """
    logger.info("Extracting GL entries from BKPF/BSEG...")
    df = pd.read_sql(query, engine)
    logger.info(f"  → {len(df):,} GL line items extracted")
    return df


def extract_vendor_invoices(engine) -> pd.DataFrame:
    logger.info("Extracting vendor invoices...")
    df = pd.read_sql("SELECT * FROM vendor_invoices", engine)
    logger.info(f"  → {len(df):,} vendor invoices extracted")
    return df


def extract_bank_statements(engine) -> pd.DataFrame:
    logger.info("Extracting bank statements...")
    df = pd.read_sql(
        "SELECT * FROM bank_statements WHERE match_status = 'UNMATCHED'", engine
    )
    logger.info(f"  → {len(df):,} unmatched bank transactions extracted")
    return df


# ── Transformation ────────────────────────────────────────────────────────────

def standardize_amounts(df: pd.DataFrame, amount_col: str) -> pd.DataFrame:
    """Round to 2 decimal places and handle nulls."""
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0).round(2)
    return df


def detect_duplicates(gl_df: pd.DataFrame) -> pd.DataFrame:
    """Flag duplicate postings: same amount + vendor + date."""
    dup_mask = gl_df.duplicated(
        subset=["vendor_id", "amount", "posting_date"], keep=False
    )
    dups = gl_df[dup_mask].copy()
    dups["exception_type"] = "DUPLICATE_POSTING"
    logger.info(f"  → {len(dups):,} duplicate posting exceptions detected")
    return dups


def match_invoices_to_gl(invoice_df: pd.DataFrame, gl_df: pd.DataFrame) -> pd.DataFrame:
    """Match vendor invoices to GL postings; flag unmatched and variances."""
    exceptions = []

    # Filter GL to vendor payment docs
    gl_payments = gl_df[
        (gl_df["doc_type"].isin(["KR", "ZP"])) & (gl_df["vendor_id"].notna())
    ].copy()

    for _, inv in invoice_df.iterrows():
        matched = gl_payments[
            (gl_payments["vendor_id"] == inv["vendor_id"]) &
            (gl_payments["posting_date"] >= inv["invoice_date"])
        ]

        if matched.empty:
            exceptions.append({
                "exception_type": "MISSING_GL_POSTING",
                "source_doc":     inv["invoice_id"],
                "counterpart_doc": None,
                "gl_amount":      None,
                "bank_amount":    inv["amount"],
                "variance":       inv["amount"],
                "business_unit":  inv.get("vendor_id", "UNKNOWN"),
                "status":         "OPEN",
                "notes":          f"Invoice {inv['invoice_id']} has no matching GL document"
            })
        else:
            gl_amount = matched["amount"].sum()
            variance = round(abs(gl_amount - float(inv["amount"])), 2)
            if variance > 0.01:
                exceptions.append({
                    "exception_type": "AMOUNT_VARIANCE",
                    "source_doc":     inv["invoice_id"],
                    "counterpart_doc": matched.iloc[0]["doc_number"],
                    "gl_amount":      gl_amount,
                    "bank_amount":    float(inv["amount"]),
                    "variance":       variance,
                    "business_unit":  inv.get("vendor_id", "UNKNOWN"),
                    "status":         "OPEN",
                    "notes":          f"Variance of INR {variance:,.2f} between invoice and GL"
                })

    logger.info(f"  → {len(exceptions):,} invoice-GL exceptions detected")
    return pd.DataFrame(exceptions)


def match_bank_to_gl(bank_df: pd.DataFrame, gl_df: pd.DataFrame) -> pd.DataFrame:
    """Match bank statement entries to GL; flag timing differences and missing postings."""
    exceptions = []
    gl_by_ref = gl_df.set_index("reference")["amount"].to_dict()

    for _, txn in bank_df.iterrows():
        ref = txn.get("reference", "")
        bank_amt = float(txn["amount"]) * (-1 if txn["debit_credit"] == "D" else 1)

        if ref and ref in gl_by_ref:
            gl_amt = gl_by_ref[ref]
            variance = round(abs(bank_amt - gl_amt), 2)
            if variance > 0.01:
                exceptions.append({
                    "exception_type": "BANK_GL_VARIANCE",
                    "source_doc":     ref,
                    "counterpart_doc": str(txn["statement_id"]),
                    "gl_amount":      gl_amt,
                    "bank_amount":    bank_amt,
                    "variance":       variance,
                    "business_unit":  txn.get("bank_account", "UNKNOWN"),
                    "status":         "OPEN",
                    "notes":          f"Bank amount differs from GL by INR {variance:,.2f}"
                })
        else:
            exceptions.append({
                "exception_type": "MISSING_GL_FOR_BANK_TXN",
                "source_doc":     str(txn["statement_id"]),
                "counterpart_doc": None,
                "gl_amount":      None,
                "bank_amount":    bank_amt,
                "variance":       abs(bank_amt),
                "business_unit":  txn.get("bank_account", "UNKNOWN"),
                "status":         "OPEN",
                "notes":          f"No GL posting found for bank transaction ref: {ref}"
            })

    logger.info(f"  → {len(exceptions):,} bank-GL exceptions detected")
    return pd.DataFrame(exceptions)


# ── Load ──────────────────────────────────────────────────────────────────────

def load_exceptions(exceptions_df: pd.DataFrame, engine) -> None:
    """Persist reconciliation results to database."""
    if exceptions_df.empty:
        logger.info("No exceptions to load.")
        return

    exceptions_df["run_date"] = datetime.now()
    exceptions_df.to_sql(
        "reconciliation_results",
        engine,
        if_exists="append",
        index=False,
        method="multi"
    )
    logger.info(f"  → {len(exceptions_df):,} exceptions written to reconciliation_results")


def export_exception_report(exceptions_df: pd.DataFrame) -> str:
    """Export exception report to CSV."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"exception_report_{date.today().isoformat()}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)
    exceptions_df.to_csv(filepath, index=False)
    logger.info(f"  → Exception report saved: {filepath}")
    return filepath


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_pipeline():
    logger.info("=" * 60)
    logger.info("SAP Financial Reconciliation Pipeline — START")
    logger.info("=" * 60)

    engine = create_engine(DB_URL)

    # Extract
    gl_df       = extract_gl_entries(engine)
    invoice_df  = extract_vendor_invoices(engine)
    bank_df     = extract_bank_statements(engine)

    # Standardize
    for df, col in [(gl_df, "amount"), (invoice_df, "amount"), (bank_df, "amount")]:
        standardize_amounts(df, col)

    # Reconcile
    logger.info("Running reconciliation checks...")
    duplicate_exceptions = detect_duplicates(gl_df)
    invoice_exceptions   = match_invoices_to_gl(invoice_df, gl_df)
    bank_exceptions      = match_bank_to_gl(bank_df, gl_df)

    all_exceptions = pd.concat(
        [duplicate_exceptions, invoice_exceptions, bank_exceptions],
        ignore_index=True
    )

    logger.info(f"\nTotal exceptions found: {len(all_exceptions):,}")
    if not all_exceptions.empty:
        logger.info("\nException summary:")
        logger.info(all_exceptions["exception_type"].value_counts().to_string())

    # Load
    load_exceptions(all_exceptions, engine)
    report_path = export_exception_report(all_exceptions)

    logger.info("=" * 60)
    logger.info(f"Pipeline complete. Report: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
