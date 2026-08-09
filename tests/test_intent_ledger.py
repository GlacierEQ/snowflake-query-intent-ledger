
from __future__ import annotations
import unittest
from src.intent_ledger import IntentLedger, QueryIntent, UseVerdict

class IntentTests(unittest.TestCase):
    def test_purpose_mismatch(self):
        led = IntentLedger()
        led.register(QueryIntent("q1", "payroll_audit", ("salary", "name"), "sql1"))
        v, r = led.use("q1", "dashboard", ("salary",))
        self.assertEqual(v, UseVerdict.REFUSE)
        self.assertEqual(r, "PURPOSE_MISMATCH")

    def test_allow_audit(self):
        led = IntentLedger()
        led.register(QueryIntent("q1", "payroll_audit", ("salary", "name"), "sql1"))
        v, r = led.use("q1", "audit_report", ("salary",))
        self.assertEqual(v, UseVerdict.ALLOW)

if __name__ == "__main__":
    unittest.main()
