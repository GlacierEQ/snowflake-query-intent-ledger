-- Babel: SQL — purpose-tagged query intent ledger (data-cloud native).
-- Independent reference schema; not a live Snowflake deployment claim.

CREATE TABLE IF NOT EXISTS query_intents (
  query_id        VARCHAR PRIMARY KEY,
  purpose         VARCHAR NOT NULL,  -- payroll_audit | product_analytics | ml_feature_draft
  columns_json    VARCHAR NOT NULL,
  sql_digest      CHAR(64) NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_uses (
  use_id          INTEGER PRIMARY KEY,
  query_id        VARCHAR NOT NULL REFERENCES query_intents(query_id),
  use_type        VARCHAR NOT NULL,
  columns_json    VARCHAR NOT NULL,
  verdict         VARCHAR NOT NULL, -- ALLOW | REFUSE
  reason          VARCHAR,
  used_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policy: purpose → allowed use_type (documented; enforce in app or policy engine)
-- payroll_audit: audit_report, compliance_export
-- product_analytics: dashboard, experiment_analysis, ml_feature_draft
