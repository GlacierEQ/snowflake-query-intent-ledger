-- Babel: SQL — immutable purpose-tagged query intent ledger (data-cloud native).
-- Independent reference schema; not a live Snowflake deployment claim.
-- Application code treats query_id as one-shot identity: rebinding an existing
-- ID to a different intent is refused rather than UPDATEd.

CREATE TABLE IF NOT EXISTS query_intents (
  query_id          VARCHAR PRIMARY KEY,
  purpose           VARCHAR NOT NULL,
  columns_json      VARCHAR NOT NULL,
  sql_digest        CHAR(64) NOT NULL,
  intent_fingerprint CHAR(64) NOT NULL UNIQUE,
  policy_fingerprint CHAR(64) NOT NULL,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CHECK (TRIM(query_id) <> ''),
  CHECK (TRIM(purpose) <> ''),
  CHECK (TRIM(columns_json) <> ''),
  CHECK (TRIM(sql_digest) <> ''),
  CHECK (TRIM(intent_fingerprint) <> ''),
  CHECK (TRIM(policy_fingerprint) <> '')
);

CREATE TABLE IF NOT EXISTS query_uses (
  use_id             INTEGER PRIMARY KEY,
  query_id           VARCHAR NOT NULL REFERENCES query_intents(query_id),
  use_type           VARCHAR NOT NULL,
  columns_json       VARCHAR NOT NULL,
  verdict            VARCHAR NOT NULL,
  reason             VARCHAR,
  intent_fingerprint CHAR(64),
  policy_fingerprint CHAR(64) NOT NULL,
  event_fingerprint  CHAR(64) NOT NULL UNIQUE,
  previous_event_fingerprint CHAR(64),
  used_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CHECK (TRIM(query_id) <> ''),
  CHECK (TRIM(use_type) <> ''),
  CHECK (TRIM(columns_json) <> ''),
  CHECK (verdict IN ('ALLOW', 'REFUSE'))
);

-- Default reference policy enforced by src/intent_ledger.py:
-- payroll_audit: audit_report, compliance_export
-- product_analytics: dashboard, experiment_analysis, ml_feature_draft
-- ml_feature_draft: ml_training_staging
--
-- SQL fixtures preserve identity/evidence fields; application policy decides
-- ALLOW/REFUSE. Durable database trigger/RLS enforcement is not claimed here.
