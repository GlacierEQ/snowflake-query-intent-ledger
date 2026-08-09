"""Validate SQL fixture contains required governance objects."""
from __future__ import annotations
import unittest
from pathlib import Path

SQL = Path(__file__).resolve().parents[1] / "sql" / "intent_ledger.sql"

class SqlFixtureTests(unittest.TestCase):
    def test_tables_and_policy_comments(self):
        t = SQL.read_text()
        self.assertIn("CREATE TABLE IF NOT EXISTS query_intents", t)
        self.assertIn("CREATE TABLE IF NOT EXISTS query_uses", t)
        self.assertIn("payroll_audit", t)
        self.assertIn("REFERENCES query_intents", t)

if __name__ == "__main__":
    unittest.main()
