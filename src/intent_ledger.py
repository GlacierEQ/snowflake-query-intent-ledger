
"""Query intent ledger — purpose-tagged query results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class UseVerdict(str, Enum):
    ALLOW = "ALLOW"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class QueryIntent:
    query_id: str
    purpose: str  # e.g. payroll_audit, product_analytics
    columns: tuple[str, ...]
    sql_digest: str

    def fingerprint(self) -> str:
        return digest({"id": self.query_id, "purpose": self.purpose, "cols": list(self.columns), "sql": self.sql_digest})


# purpose -> allowed downstream uses
POLICY: dict[str, set[str]] = {
    "payroll_audit": {"audit_report", "compliance_export"},
    "product_analytics": {"dashboard", "experiment_analysis", "ml_feature_draft"},
    "ml_feature_draft": {"ml_training_staging"},
}


@dataclass
class IntentLedger:
    intents: dict[str, QueryIntent] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    def register(self, intent: QueryIntent) -> None:
        self.intents[intent.query_id] = intent

    def use(self, query_id: str, use_type: str, columns: tuple[str, ...]) -> tuple[UseVerdict, str | None]:
        intent = self.intents.get(query_id)
        if intent is None:
            verdict, reason = UseVerdict.REFUSE, "UNKNOWN_QUERY"
        elif any(c not in intent.columns for c in columns):
            verdict, reason = UseVerdict.REFUSE, "COLUMN_NOT_IN_QUERY"
        elif use_type not in POLICY.get(intent.purpose, set()):
            verdict, reason = UseVerdict.REFUSE, "PURPOSE_MISMATCH"
        else:
            verdict, reason = UseVerdict.ALLOW, None
        self.events.append(
            {
                "query_id": query_id,
                "use_type": use_type,
                "columns": list(columns),
                "verdict": verdict.value,
                "reason": reason,
            }
        )
        return verdict, reason

    def fingerprint(self) -> str:
        return digest({"events": self.events, "intents": {k: v.fingerprint() for k, v in self.intents.items()}})
