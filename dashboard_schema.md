# Power BI Data Model — SAP Financial Reconciliation Dashboard

## Overview
The dashboard connects to the `sap_reconciliation` MySQL database and visualizes exception data for finance teams to track, filter, and resolve reconciliation gaps.

## Tables / Queries

### 1. `fact_exceptions` (from `reconciliation_results`)
| Column | Type | Description |
|---|---|---|
| rec_id | INT | Primary key |
| run_date | DATETIME | When the pipeline ran |
| exception_type | VARCHAR | AMOUNT_VARIANCE / MISSING_GL_POSTING / DUPLICATE_POSTING / BANK_GL_VARIANCE |
| source_doc | VARCHAR | Invoice / Bank statement ID |
| counterpart_doc | VARCHAR | Matched GL document (if any) |
| gl_amount | DECIMAL | Amount per GL |
| bank_amount | DECIMAL | Amount per invoice/bank |
| variance | DECIMAL | Absolute difference |
| business_unit | VARCHAR | Company code / Vendor |
| status | VARCHAR | OPEN / RESOLVED / ESCALATED |

### 2. `dim_date` (calculated)
Generated using Power Query M:
```
= List.Dates(#date(2024,1,1), 365, #duration(1,0,0,0))
```

## Key Measures (DAX)

```dax
Total Exceptions = COUNTROWS(fact_exceptions)

Open Exceptions = CALCULATE(COUNTROWS(fact_exceptions), fact_exceptions[status] = "OPEN")

Total Variance (INR) = SUMX(fact_exceptions, fact_exceptions[variance])

Exception Resolution Rate % =
    DIVIDE(
        CALCULATE(COUNTROWS(fact_exceptions), fact_exceptions[status] = "RESOLVED"),
        COUNTROWS(fact_exceptions)
    ) * 100

Avg Days Open =
    AVERAGEX(
        FILTER(fact_exceptions, fact_exceptions[status] = "OPEN"),
        DATEDIFF(fact_exceptions[run_date], TODAY(), DAY)
    )
```

## Visuals / Pages

### Page 1: Executive Summary
- KPI cards: Total Exceptions | Open | Total Variance INR | Resolution Rate
- Donut chart: Exceptions by type
- Line chart: Exceptions over time (by run_date)

### Page 2: Exception Drill-Down
- Table: All open exceptions with filters for type, business unit, date range
- Bar chart: Variance by business unit
- Status slicer: OPEN / RESOLVED / ESCALATED

### Page 3: Aging Analysis
- Horizontal bar: Exceptions by age bucket (0-7d / 8-30d / 31-60d / >60d)
- Table: Top 10 vendors by open exception count

## Refresh Schedule
- Daily incremental refresh via MySQL DirectQuery or scheduled import
- Alert rule: notify finance team when open exceptions > 50
