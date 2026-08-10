"""Query intent ledger — immutable purpose-tagged query identity and reuse decisions.

The ledger governs whether a registered query result may be reused for a named
downstream purpose and column subset. It does not execute SQL, verify query
results, or prove that a natural-language claim is semantically supported.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class UseVerdict(str, Enum):
    ALLOW = "ALLOW"
    REFUSE = "REFUSE"


class RegisterVerdict(str, Enum):
    REGISTERED = "REGISTERED"
    ALREADY_REGISTERED = "ALREADY_REGISTERED"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class QueryIntent:
    query_id: str
    purpose: str
    columns: tuple[str, ...]
    sql_digest: str

    def canonical_columns(self) -> tuple[str, ...]:
        return tuple(sorted(self.columns))

    def fingerprint(self) -> str:
        return digest(
            {
                "id": self.query_id,
                "purpose": self.purpose,
                "cols": list(self.canonical_columns()),
                "sql": self.sql_digest,
            }
        )


DEFAULT_POLICY: Mapping[str, frozenset[str]] = {
    "payroll_audit": frozenset({"audit_report", "compliance_export"}),
    "product_analytics": frozenset(
        {"dashboard", "experiment_analysis", "ml_feature_draft"}
    ),
    "ml_feature_draft": frozenset({"ml_training_staging"}),
}


@dataclass
class IntentLedger:
    policy: Mapping[str, frozenset[str]] = field(default_factory=lambda: DEFAULT_POLICY)
    intents: dict[str, QueryIntent] = field(default_factory=dict, init=False)
    events: list[dict] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        normalized: dict[str, frozenset[str]] = {}
        for purpose, uses in self.policy.items():
            if not purpose.strip():
                raise ValueError("policy purpose must be non-empty")
            clean_uses = frozenset(uses)
            if not clean_uses or any(not use.strip() for use in clean_uses):
                raise ValueError(f"policy uses must be non-empty for purpose {purpose}")
            normalized[purpose] = clean_uses
        self.policy = normalized
        self.policy_fingerprint = digest(
            {
                purpose: sorted(uses)
                for purpose, uses in sorted(normalized.items())
            }
        )

    def _validate_intent(self, intent: QueryIntent) -> str | None:
        if not intent.query_id.strip():
            return "EMPTY_QUERY_ID"
        if not intent.purpose.strip():
            return "EMPTY_PURPOSE"
        if intent.purpose not in self.policy:
            return "UNKNOWN_PURPOSE"
        if not intent.sql_digest.strip():
            return "EMPTY_SQL_DIGEST"
        if not intent.columns:
            return "EMPTY_COLUMNS"
        if any(not column.strip() for column in intent.columns):
            return "EMPTY_COLUMN"
        if len(intent.columns) != len(set(intent.columns)):
            return "DUPLICATE_COLUMN"
        return None

    def _append_event(self, body: dict) -> dict:
        previous = self.events[-1]["event_fingerprint"] if self.events else None
        event = dict(body)
        event["policy_fingerprint"] = self.policy_fingerprint
        event["previous_event_fingerprint"] = previous
        event["event_fingerprint"] = digest(event)
        self.events.append(event)
        return event

    def register(self, intent: QueryIntent) -> tuple[RegisterVerdict, str | None]:
        reason = self._validate_intent(intent)
        if reason is not None:
            self._append_event(
                {
                    "event_type": "REGISTER",
                    "query_id": intent.query_id,
                    "intent_fingerprint": intent.fingerprint(),
                    "verdict": RegisterVerdict.REFUSE.value,
                    "reason": reason,
                }
            )
            return RegisterVerdict.REFUSE, reason

        existing = self.intents.get(intent.query_id)
        if existing is not None:
            if existing.fingerprint() == intent.fingerprint():
                self._append_event(
                    {
                        "event_type": "REGISTER",
                        "query_id": intent.query_id,
                        "intent_fingerprint": intent.fingerprint(),
                        "verdict": RegisterVerdict.ALREADY_REGISTERED.value,
                        "reason": None,
                    }
                )
                return RegisterVerdict.ALREADY_REGISTERED, None
            self._append_event(
                {
                    "event_type": "REGISTER",
                    "query_id": intent.query_id,
                    "intent_fingerprint": intent.fingerprint(),
                    "existing_intent_fingerprint": existing.fingerprint(),
                    "verdict": RegisterVerdict.REFUSE.value,
                    "reason": "QUERY_ID_REBIND",
                }
            )
            return RegisterVerdict.REFUSE, "QUERY_ID_REBIND"

        self.intents[intent.query_id] = intent
        self._append_event(
            {
                "event_type": "REGISTER",
                "query_id": intent.query_id,
                "intent_fingerprint": intent.fingerprint(),
                "verdict": RegisterVerdict.REGISTERED.value,
                "reason": None,
            }
        )
        return RegisterVerdict.REGISTERED, None

    def use(
        self,
        query_id: str,
        use_type: str,
        columns: tuple[str, ...],
    ) -> tuple[UseVerdict, str | None]:
        canonical_columns = tuple(sorted(columns))
        intent = self.intents.get(query_id)
        if not query_id.strip():
            verdict, reason = UseVerdict.REFUSE, "EMPTY_QUERY_ID"
        elif not use_type.strip():
            verdict, reason = UseVerdict.REFUSE, "EMPTY_USE_TYPE"
        elif not columns:
            verdict, reason = UseVerdict.REFUSE, "EMPTY_COLUMNS"
        elif any(not column.strip() for column in columns):
            verdict, reason = UseVerdict.REFUSE, "EMPTY_COLUMN"
        elif len(columns) != len(set(columns)):
            verdict, reason = UseVerdict.REFUSE, "DUPLICATE_COLUMN"
        elif intent is None:
            verdict, reason = UseVerdict.REFUSE, "UNKNOWN_QUERY"
        elif any(column not in intent.columns for column in canonical_columns):
            verdict, reason = UseVerdict.REFUSE, "COLUMN_NOT_IN_QUERY"
        elif use_type not in self.policy.get(intent.purpose, frozenset()):
            verdict, reason = UseVerdict.REFUSE, "PURPOSE_MISMATCH"
        else:
            verdict, reason = UseVerdict.ALLOW, None

        self._append_event(
            {
                "event_type": "USE",
                "query_id": query_id,
                "intent_fingerprint": intent.fingerprint() if intent else None,
                "use_type": use_type,
                "columns": list(canonical_columns),
                "verdict": verdict.value,
                "reason": reason,
            }
        )
        return verdict, reason

    def intent_fingerprint(self, query_id: str) -> str:
        intent = self.intents.get(query_id)
        if intent is None:
            raise KeyError(query_id)
        return intent.fingerprint()

    def fingerprint(self) -> str:
        return digest(
            {
                "policy_fingerprint": self.policy_fingerprint,
                "events": [event["event_fingerprint"] for event in self.events],
                "intents": {
                    query_id: intent.fingerprint()
                    for query_id, intent in sorted(self.intents.items())
                },
            }
        )
