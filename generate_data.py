"""
Generate realistic mock SAP FI data for testing the reconciliation pipeline.
Run this script to populate the data/ directory with CSV files.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


COMPANY_CODES  = ["IN01", "IN02"]
DOC_TYPES      = ["SA", "KR", "ZP", "RE"]
GL_ACCOUNTS    = ["200100", "200200", "210000", "400000", "401000", "100000"]
VENDORS        = [f"V{str(i).zfill(5)}" for i in range(1, 21)]
CURRENCIES     = ["INR"]
BUSINESS_UNITS = ["BU01", "BU02", "BU03"]

start = date(2024, 1, 1)
end   = date(2024, 3, 31)

# ── BKPF (Document Headers) ──────────────────────────────────────────────────
n_docs = 500
bkpf_rows = []
for i in range(1, n_docs + 1):
    doc_date = random_date(start, end)
    bkpf_rows.append({
        "MANDT": "100",
        "BUKRS": random.choice(COMPANY_CODES),
        "BELNR": f"{1000000 + i:010d}",
        "GJAHR": 2024,
        "BLART": random.choice(DOC_TYPES),
        "BLDAT": doc_date,
        "BUDAT": doc_date + timedelta(days=random.randint(0, 2)),
        "MONAT": doc_date.month,
        "WAERS": "INR",
        "XBLNR": f"REF{random.randint(10000, 99999)}",
        "USNAM": f"USER{random.randint(1,5):02d}",
    })

bkpf_df = pd.DataFrame(bkpf_rows)
bkpf_df.to_csv(os.path.join(DATA_DIR, "sample_gl_entries_bkpf.csv"), index=False)

# ── BSEG (Document Line Items) ───────────────────────────────────────────────
bseg_rows = []
for _, h in bkpf_df.iterrows():
    n_lines = random.randint(1, 4)
    for j in range(1, n_lines + 1):
        amount = round(random.uniform(1000, 500000), 2)
        bseg_rows.append({
            "MANDT":  h["MANDT"],
            "BUKRS":  h["BUKRS"],
            "BELNR":  h["BELNR"],
            "GJAHR":  h["GJAHR"],
            "BUZEI":  j,
            "KOART":  random.choice(["S", "K", "D"]),
            "HKONT":  random.choice(GL_ACCOUNTS),
            "LIFNR":  random.choice(VENDORS) if h["BLART"] in ["KR", "ZP"] else None,
            "DMBTR":  amount,
            "WRBTR":  amount,
            "SGTXT":  f"Line item {j} for {h['BELNR']}",
            "ZUONR":  h["XBLNR"],
            "AUGDT":  None,
            "AUGBL":  None,
        })

bseg_df = pd.DataFrame(bseg_rows)
# Introduce ~5% duplicates for testing
dup_sample = bseg_df.sample(frac=0.05, random_state=42).copy()
bseg_df = pd.concat([bseg_df, dup_sample], ignore_index=True)
bseg_df.to_csv(os.path.join(DATA_DIR, "sample_gl_entries_bseg.csv"), index=False)

# ── Vendor Invoices ──────────────────────────────────────────────────────────
invoice_rows = []
for i in range(1, 201):
    vendor = random.choice(VENDORS)
    inv_date = random_date(start, end)
    amount = round(random.uniform(5000, 300000), 2)
    # 85% matched to a GL doc, 15% missing
    matched = random.random() > 0.15
    invoice_rows.append({
        "invoice_id":    f"INV{2024000 + i:010d}",
        "vendor_id":     vendor,
        "vendor_name":   f"Vendor {vendor}",
        "invoice_date":  inv_date,
        "due_date":      inv_date + timedelta(days=30),
        "amount":        amount if matched else amount * random.uniform(1.01, 1.05),
        "currency":      "INR",
        "status":        "OPEN" if not matched else "POSTED",
        "sap_doc_number": f"{random.randint(1000001, 1000500):010d}" if matched else None,
        "payment_ref":   f"PAY{random.randint(10000, 99999)}" if matched else None,
    })

invoice_df = pd.DataFrame(invoice_rows)
invoice_df.to_csv(os.path.join(DATA_DIR, "sample_invoices.csv"), index=False)

# ── Bank Statements ──────────────────────────────────────────────────────────
bank_rows = []
for i in range(1, 301):
    txn_date = random_date(start, end)
    amount = round(random.uniform(1000, 200000), 2)
    matched = random.random() > 0.12
    bank_rows.append({
        "statement_id":  i,
        "bank_account":  f"HDFC{random.randint(1,3):02d}001",
        "value_date":    txn_date,
        "posting_date":  txn_date + timedelta(days=random.randint(0, 1)),
        "amount":        amount,
        "debit_credit":  random.choice(["D", "C"]),
        "reference":     f"REF{random.randint(10000, 99999)}" if matched else f"EXT{i:05d}",
        "description":   f"Transaction {i}",
        "match_status":  "UNMATCHED",
    })

bank_df = pd.DataFrame(bank_rows)
bank_df.to_csv(os.path.join(DATA_DIR, "sample_bank_statements.csv"), index=False)

print(f"✓ Data generated:")
print(f"  BKPF: {len(bkpf_df):,} documents")
print(f"  BSEG: {len(bseg_df):,} line items (incl. ~5% duplicates)")
print(f"  Invoices: {len(invoice_df):,}")
print(f"  Bank statements: {len(bank_df):,}")
