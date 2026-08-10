from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text())


CANONICAL = load("machine/canonical-position.json")
CAPABILITIES = load("machine/capabilities.json")
TARGET = load("machine/target-contract.json")


class CanonicalPositionContractTests(unittest.TestCase):
    def test_repository_owns_only_purpose_bound_query_reuse(self):
        self.assertEqual(CANONICAL["role"], "CANONICAL_SPECIALIST")
        self.assertEqual(CANONICAL["owns"], "purpose_bound_query_reuse_governance")
        self.assertIn("SQL execution or query-result verification", CANONICAL["does_not_own"])
        self.assertIn("natural-language claim citation fencing", CANONICAL["does_not_own"])

    def test_claim_fence_sibling_is_not_integrated(self):
        edge = CANONICAL["relationships"][0]
        self.assertEqual(edge["repository"], "GlacierEQ/snowflake-cortex-claim-bound")
        self.assertFalse(edge["integration_exercised"])

    def test_capabilities_are_repository_native(self):
        capabilities = set(CAPABILITIES["capabilities"])
        self.assertNotIn("hyper-scaling", capabilities)
        self.assertIn("one_shot_query_intent_identity", capabilities)
        self.assertIn("purpose_policy_fingerprint", capabilities)
        self.assertIn("chained_query_use_receipt", capabilities)

    def test_target_waits_for_exact_head_proof(self):
        self.assertEqual(TARGET["current"]["state"], "PROMOTED")
        self.assertTrue(TARGET["current"]["canonical_position_pending_exact_head_proof"])
        self.assertEqual(TARGET["promotion"]["next_gate"], "CANONICAL_POSITION_RESOLVED")

    def test_truth_boundary_excludes_execution_and_external_policy_claims(self):
        boundary = CAPABILITIES["truth_boundary"]
        self.assertIn("does not execute SQL", boundary)
        self.assertIn("authenticate external actors", boundary)
        self.assertIn("enforce Snowflake RLS", boundary)


if __name__ == "__main__":
    unittest.main()
