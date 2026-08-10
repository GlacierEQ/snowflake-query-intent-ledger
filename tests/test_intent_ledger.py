from __future__ import annotations

import unittest

from src.intent_ledger import (
    IntentLedger,
    QueryIntent,
    RegisterVerdict,
    UseVerdict,
)


class IntentTests(unittest.TestCase):
    @staticmethod
    def payroll_intent() -> QueryIntent:
        return QueryIntent("q1", "payroll_audit", ("salary", "name"), "sql1")

    def test_purpose_mismatch(self):
        ledger = IntentLedger()
        self.assertEqual(ledger.register(self.payroll_intent())[0], RegisterVerdict.REGISTERED)
        verdict, reason = ledger.use("q1", "dashboard", ("salary",))
        self.assertEqual(verdict, UseVerdict.REFUSE)
        self.assertEqual(reason, "PURPOSE_MISMATCH")

    def test_allow_audit(self):
        ledger = IntentLedger()
        ledger.register(self.payroll_intent())
        verdict, reason = ledger.use("q1", "audit_report", ("salary",))
        self.assertEqual(verdict, UseVerdict.ALLOW)
        self.assertIsNone(reason)

    def test_query_id_cannot_be_rebound(self):
        ledger = IntentLedger()
        original = self.payroll_intent()
        ledger.register(original)
        verdict, reason = ledger.register(
            QueryIntent("q1", "product_analytics", ("salary",), "sql2")
        )
        self.assertEqual(verdict, RegisterVerdict.REFUSE)
        self.assertEqual(reason, "QUERY_ID_REBIND")
        self.assertEqual(ledger.intent_fingerprint("q1"), original.fingerprint())

    def test_exact_reregistration_is_idempotent(self):
        ledger = IntentLedger()
        intent = self.payroll_intent()
        self.assertEqual(ledger.register(intent)[0], RegisterVerdict.REGISTERED)
        self.assertEqual(ledger.register(intent)[0], RegisterVerdict.ALREADY_REGISTERED)
        self.assertEqual(len(ledger.intents), 1)

    def test_invalid_intent_dimensions_refuse(self):
        cases = [
            QueryIntent("", "payroll_audit", ("salary",), "sql"),
            QueryIntent("q", "", ("salary",), "sql"),
            QueryIntent("q", "unknown", ("salary",), "sql"),
            QueryIntent("q", "payroll_audit", (), "sql"),
            QueryIntent("q", "payroll_audit", ("",), "sql"),
            QueryIntent("q", "payroll_audit", ("salary", "salary"), "sql"),
            QueryIntent("q", "payroll_audit", ("salary",), ""),
        ]
        for intent in cases:
            with self.subTest(intent=intent):
                ledger = IntentLedger()
                verdict, reason = ledger.register(intent)
                self.assertEqual(verdict, RegisterVerdict.REFUSE)
                self.assertIsNotNone(reason)
                self.assertEqual(ledger.intents, {})

    def test_unknown_query_refuses(self):
        verdict, reason = IntentLedger().use("missing", "dashboard", ("x",))
        self.assertEqual(verdict, UseVerdict.REFUSE)
        self.assertEqual(reason, "UNKNOWN_QUERY")

    def test_column_escalation_refuses(self):
        ledger = IntentLedger()
        ledger.register(self.payroll_intent())
        verdict, reason = ledger.use("q1", "audit_report", ("ssn",))
        self.assertEqual(verdict, UseVerdict.REFUSE)
        self.assertEqual(reason, "COLUMN_NOT_IN_QUERY")

    def test_invalid_use_dimensions_refuse(self):
        ledger = IntentLedger()
        ledger.register(self.payroll_intent())
        cases = [
            ("", "audit_report", ("salary",), "EMPTY_QUERY_ID"),
            ("q1", "", ("salary",), "EMPTY_USE_TYPE"),
            ("q1", "audit_report", (), "EMPTY_COLUMNS"),
            ("q1", "audit_report", ("",), "EMPTY_COLUMN"),
            ("q1", "audit_report", ("salary", "salary"), "DUPLICATE_COLUMN"),
        ]
        for query_id, use_type, columns, expected in cases:
            with self.subTest(expected=expected):
                verdict, reason = ledger.use(query_id, use_type, columns)
                self.assertEqual(verdict, UseVerdict.REFUSE)
                self.assertEqual(reason, expected)

    def test_column_order_is_canonical_in_use_receipt(self):
        first = IntentLedger()
        second = IntentLedger()
        intent = QueryIntent("q1", "payroll_audit", ("salary", "name"), "sql1")
        first.register(intent)
        second.register(intent)
        first.use("q1", "audit_report", ("salary", "name"))
        second.use("q1", "audit_report", ("name", "salary"))
        self.assertEqual(first.events[-1]["event_fingerprint"], second.events[-1]["event_fingerprint"])
        self.assertEqual(first.fingerprint(), second.fingerprint())

    def test_policy_identity_is_bound_into_ledger(self):
        default = IntentLedger()
        custom = IntentLedger(policy={"payroll_audit": frozenset({"audit_report"})})
        self.assertNotEqual(default.policy_fingerprint, custom.policy_fingerprint)
        self.assertNotEqual(default.fingerprint(), custom.fingerprint())

    def test_event_chain_binds_history(self):
        ledger = IntentLedger()
        ledger.register(self.payroll_intent())
        ledger.use("q1", "audit_report", ("salary",))
        self.assertEqual(
            ledger.events[1]["previous_event_fingerprint"],
            ledger.events[0]["event_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
