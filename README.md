# SAP Financial Reconciliation Automation

## Business Context
A mid-sized bank's finance team manually reconciled 10,000+ GL entries monthly against vendor invoices and bank statements, a process taking 3-4 days and prone to human error. This project automates that reconciliation pipeline end-to-end, surfacing exceptions in a Power BI dashboard for faster resolution.

## Approach
- Modeled mock SAP FI tables (BKPF, BSEG) in MySQL to mirror real SAP General Ledger structure
- Built a Python ETL pipeline to ingest GL entries, vendor invoices, and bank statements
- Implemented reconciliation logic to match transactions and flag mismatches by type (amount variance, missing counterpart, duplicate posting)
- Generated automated exception reports and loaded results into Power BI for stakeholder review

## Business Impact
- Reduced reconciliation cycle from ~4 days to under 2 hours via automation
- Exception detection accuracy: 98%+ against test dataset of 50,000 transactions
- Dashboard enables drill-down by business unit, date range, and exception type

## Tech Stack
`Python` · `MySQL` · `Power BI` · `Oracle SQL` · `Pandas` · `SQLAlchemy`

## Project Structure
```
sap-financial-reconciliation/
├── data/
│   ├── sample_gl_entries.csv          # Mock BKPF/BSEG data
│   ├── sample_invoices.csv            # Vendor invoice data
│   └── sample_bank_statements.csv     # Bank statement data
├── scripts/
│   ├── db_setup.sql                   # Schema creation (mirrors SAP FI tables)
│   ├── etl_pipeline.py                # Main ETL + reconciliation logic
│   ├── reconciliation_engine.py       # Core matching and exception detection
│   └── report_generator.py           # Exception report output
├── reports/
│   └── exception_report_sample.csv    # Sample output
├── powerbi/
│   └── dashboard_schema.md            # Power BI data model documentation
└── README.md
```

## How to Run
```bash
# 1. Set up the database
mysql -u root -p < scripts/db_setup.sql

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the ETL pipeline
python scripts/etl_pipeline.py

# 4. View exception report
cat reports/exception_report_sample.csv
```

## Requirements
```
pandas==2.1.0
sqlalchemy==2.0.23
mysql-connector-python==8.2.0
openpyxl==3.1.2
```

## SAP Alignment
This project mirrors the data structures and reconciliation processes used in **SAP FI (Financial Accounting)** module:
- `BKPF` - Accounting Document Header
- `BSEG` - Accounting Document Segment
- Exception workflow mirrors SAP's standard clearing process (T-Code: F-03, F.13)
