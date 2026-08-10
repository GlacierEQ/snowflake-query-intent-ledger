# ISSUE CONTRACT

## Pain
A query result collected for one purpose can be silently reused for another, and if the same query ID can later be rebound to a different purpose/column/SQL contract then earlier downstream-use decisions lose their evidentiary meaning.

## Success
- Register a non-empty query ID once with purpose, unique columns, and SQL digest.
- Refuse an attempt to rebind that query ID to a different intent; exact re-registration is idempotent.
- Bind the accepted purpose→downstream-use policy into a deterministic policy fingerprint.
- Refuse unknown query IDs, column escalation, purpose mismatch, and malformed use requests.
- Chain registration/use events so each decision binds the exact query-intent fingerprint, policy fingerprint, prior event, verdict and reason.

## Boundary
This ledger authorizes **declared downstream reuse** of a registered query identity. It does not execute SQL, verify returned data, authenticate an external actor, prove a natural-language claim, or claim Snowflake policy/RLS enforcement.
