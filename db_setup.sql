-- ============================================================
-- SAP FI Financial Reconciliation - Database Schema
-- Mirrors SAP BKPF (Document Header) and BSEG (Document Segment)
-- ============================================================

CREATE DATABASE IF NOT EXISTS sap_reconciliation;
USE sap_reconciliation;

-- BKPF: Accounting Document Header
CREATE TABLE IF NOT EXISTS bkpf (
    mandt       VARCHAR(3)      NOT NULL DEFAULT '100',  -- Client
    bukrs       VARCHAR(4)      NOT NULL,                -- Company Code
    belnr       VARCHAR(10)     NOT NULL,                -- Document Number
    gjahr       INT             NOT NULL,                -- Fiscal Year
    blart       VARCHAR(2),                              -- Document Type (SA=GL, KR=Vendor Invoice, ZP=Payment)
    bldat       DATE,                                    -- Document Date
    budat       DATE,                                    -- Posting Date
    monat       INT,                                     -- Fiscal Period
    cpudt       DATE,                                    -- Entry Date
    usnam       VARCHAR(12),                             -- User Name
    waers       VARCHAR(5)      DEFAULT 'INR',           -- Currency
    xblnr       VARCHAR(16),                             -- Reference Document Number
    bktxt       VARCHAR(25),                             -- Document Header Text
    PRIMARY KEY (mandt, bukrs, belnr, gjahr)
);

-- BSEG: Accounting Document Segment (Line Items)
CREATE TABLE IF NOT EXISTS bseg (
    mandt       VARCHAR(3)      NOT NULL DEFAULT '100',
    bukrs       VARCHAR(4)      NOT NULL,
    belnr       VARCHAR(10)     NOT NULL,
    gjahr       INT             NOT NULL,
    buzei       INT             NOT NULL,               -- Line Item Number
    koart       VARCHAR(1),                             -- Account Type (S=GL, K=Vendor, D=Customer)
    hkont       VARCHAR(10),                            -- GL Account
    lifnr       VARCHAR(10),                            -- Vendor Number
    kunnr       VARCHAR(10),                            -- Customer Number
    dmbtr       DECIMAL(15,2),                          -- Amount in Local Currency
    wrbtr       DECIMAL(15,2),                          -- Amount in Document Currency
    sgtxt       VARCHAR(50),                            -- Item Text
    zuonr       VARCHAR(18),                            -- Assignment (used for clearing)
    augdt       DATE,                                   -- Clearing Date
    augbl       VARCHAR(10),                            -- Clearing Document
    PRIMARY KEY (mandt, bukrs, belnr, gjahr, buzei)
);

-- Vendor Invoices (AP module simulation)
CREATE TABLE IF NOT EXISTS vendor_invoices (
    invoice_id      VARCHAR(20)     PRIMARY KEY,
    vendor_id       VARCHAR(10)     NOT NULL,
    vendor_name     VARCHAR(100),
    invoice_date    DATE,
    due_date        DATE,
    amount          DECIMAL(15,2),
    currency        VARCHAR(5)      DEFAULT 'INR',
    status          VARCHAR(20),    -- OPEN, POSTED, CLEARED, DISPUTED
    sap_doc_number  VARCHAR(10),    -- Linked BELNR if posted
    payment_ref     VARCHAR(20),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bank Statements
CREATE TABLE IF NOT EXISTS bank_statements (
    statement_id    INT             AUTO_INCREMENT PRIMARY KEY,
    bank_account    VARCHAR(20),
    value_date      DATE,
    posting_date    DATE,
    amount          DECIMAL(15,2),
    debit_credit    CHAR(1),        -- D=Debit, C=Credit
    reference       VARCHAR(50),
    description     VARCHAR(200),
    matched_doc     VARCHAR(10),    -- SAP document matched to
    match_status    VARCHAR(20) DEFAULT 'UNMATCHED'
);

-- Reconciliation Results (output table)
CREATE TABLE IF NOT EXISTS reconciliation_results (
    rec_id          INT             AUTO_INCREMENT PRIMARY KEY,
    run_date        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    exception_type  VARCHAR(50),    -- AMOUNT_VARIANCE, MISSING_COUNTERPART, DUPLICATE, TIMING_DIFF
    source_doc      VARCHAR(20),
    counterpart_doc VARCHAR(20),
    gl_amount       DECIMAL(15,2),
    bank_amount     DECIMAL(15,2),
    variance        DECIMAL(15,2),
    business_unit   VARCHAR(10),
    status          VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, RESOLVED, ESCALATED
    notes           VARCHAR(500)
);

-- Indexes for performance
CREATE INDEX idx_bkpf_budat ON bkpf(budat);
CREATE INDEX idx_bkpf_blart ON bkpf(blart);
CREATE INDEX idx_bseg_hkont ON bseg(hkont);
CREATE INDEX idx_bseg_lifnr ON bseg(lifnr);
CREATE INDEX idx_vendor_status ON vendor_invoices(status);
CREATE INDEX idx_bank_match ON bank_statements(match_status);

SELECT 'Schema created successfully' AS status;
