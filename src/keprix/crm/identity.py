"""Identity resolution for CRM entities (exact keys; fuzzy = Soft Wall suggestion)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.crm.store import CrmStore, _normalise_email, _primary_email


@dataclass(frozen=True)
class ExactMatch:
    entity_type: str
    entity_id: str
    match_keys: tuple[str, ...]


@dataclass(frozen=True)
class FuzzyCandidate:
    entity_type: str
    entity_id: str
    score: float
    match_keys: tuple[str, ...]
    explanation: str


class IdentityResolver:
    """Resolve identities with exact verified keys. Fuzzy never auto-merges."""

    def __init__(self, store: CrmStore) -> None:
        self._store = store

    def resolve_account(self, workspace_id: str, **fields: Any) -> ExactMatch | None:
        row = self._store._find_account_key(workspace_id, fields)
        if not row:
            return None
        keys = self._account_keys(fields, row)
        return ExactMatch("account", row["id"], keys)

    def resolve_lead(self, workspace_id: str, **fields: Any) -> ExactMatch | None:
        row = self._store._find_lead_key(workspace_id, fields)
        if not row:
            return None
        keys = self._lead_keys(fields, row)
        return ExactMatch("lead", row["id"], keys)

    def resolve_contact(self, workspace_id: str, **fields: Any) -> ExactMatch | None:
        row = self._store._find_contact_key(workspace_id, fields)
        if not row:
            return None
        keys = self._contact_keys(fields, row)
        return ExactMatch("contact", row["id"], keys)

    def upsert_with_identity(
        self,
        workspace_id: str,
        entity_type: str,
        **fields: Any,
    ) -> dict[str, Any]:
        entity_type = entity_type.lower().strip()
        if entity_type == "account":
            return self._store.upsert_account(workspace_id, **fields)
        if entity_type == "lead":
            return self._store.upsert_lead(workspace_id, **fields)
        if entity_type == "contact":
            return self._store.upsert_contact(workspace_id, **fields)
        raise ValueError(f"unsupported entity_type for upsert: {entity_type}")

    def suggest_fuzzy_merges(
        self,
        workspace_id: str,
        *,
        entity_type: str,
        name: str | None = None,
        domain: str | None = None,
        persist: bool = True,
        min_score: float = 0.72,
    ) -> list[dict[str, Any]]:
        """Create Soft Wall-ready merge suggestions. Never merges consent."""
        entity_type = entity_type.lower().strip()
        candidates = self._fuzzy_candidates(
            workspace_id,
            entity_type=entity_type,
            name=name,
            domain=domain,
            min_score=min_score,
        )
        suggestions: list[dict[str, Any]] = []
        for cand in candidates:
            # Pair against nearest sibling already in workspace with same fuzzy signal.
            peers = self._peer_rows(workspace_id, entity_type)
            left = next((p for p in peers if p["id"] == cand.entity_id), None)
            if not left:
                continue
            for right in peers:
                if right["id"] == left["id"]:
                    continue
                score, keys, explanation = self._pair_score(entity_type, left, right, name, domain)
                if score < min_score:
                    continue
                if persist:
                    suggestion = self._store.create_merge_suggestion(
                        workspace_id,
                        entity_type=entity_type,
                        left_id=left["id"],
                        right_id=right["id"],
                        match_keys=list(keys),
                        score=score,
                        explanation=explanation,
                        field_diff=self._field_diff(left, right),
                    )
                    suggestions.append(suggestion)
                else:
                    suggestions.append(
                        {
                            "entity_type": entity_type,
                            "left_id": left["id"],
                            "right_id": right["id"],
                            "match_keys": list(keys),
                            "score": score,
                            "explanation": explanation,
                            "status": "pending",
                        }
                    )
                break
        return suggestions

    def apply_merge_suggestion(
        self,
        workspace_id: str,
        suggestion_id: str,
        *,
        survivor_id: str | None = None,
        actor_type: str = "user",
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """Apply an approved merge. Consent records are never moved between people."""
        suggestion = self._store.get_merge_suggestion(workspace_id, suggestion_id)
        if not suggestion:
            raise LookupError("merge_suggestion_not_found")
        if suggestion.get("status") not in (None, "pending", "approved"):
            raise ValueError(f"merge suggestion not applicable: {suggestion.get('status')}")

        left_id = suggestion["left_id"]
        right_id = suggestion["right_id"]
        entity_type = suggestion["entity_type"]
        survivor = survivor_id or left_id
        merged = right_id if survivor == left_id else left_id
        if survivor not in (left_id, right_id) or merged not in (left_id, right_id):
            raise ValueError("survivor_id must be left_id or right_id")

        left = self._get_entity(workspace_id, entity_type, left_id)
        right = self._get_entity(workspace_id, entity_type, right_id)
        if not left or not right:
            raise LookupError("merge_entity_not_found")

        # Soft-delete the non-survivor; keep consent on original subject ids.
        self._soft_delete_entity(workspace_id, entity_type, merged)
        history = self._store.record_merge_history(
            workspace_id,
            suggestion_id=suggestion_id,
            entity_type=entity_type,
            survivor_id=survivor,
            merged_id=merged,
            snapshot={"left": left, "right": right},
            reversible=True,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        self._store.update_merge_suggestion(
            workspace_id,
            suggestion_id,
            status="approved",
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return {"suggestion": suggestion, "history": history, "survivor_id": survivor, "merged_id": merged}

    def reverse_merge(
        self,
        workspace_id: str,
        history_id: str,
        *,
        actor_type: str = "user",
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        rows = self._store.list_merge_history(workspace_id, limit=500)
        history = next((r for r in rows if r["id"] == history_id), None)
        if not history:
            raise LookupError("merge_history_not_found")
        if not history.get("reversible") or history.get("reversed_at"):
            raise ValueError("merge_not_reversible")
        snapshot = history.get("snapshot") or {}
        merged = snapshot.get("left") if snapshot.get("left", {}).get("id") == history["merged_id"] else snapshot.get("right")
        if not isinstance(merged, dict):
            raise ValueError("missing_merge_snapshot")
        # Re-create soft-deleted entity by clearing deleted_at via create+id is hard;
        # restore by inserting a new row from snapshot is safer for UI review.
        restored = self._restore_entity(workspace_id, history["entity_type"], merged)
        # Mark history reversed by appending note in suggestion status if present.
        if history.get("suggestion_id"):
            self._store.update_merge_suggestion(
                workspace_id,
                history["suggestion_id"],
                status="reversed",
                actor_type=actor_type,
                actor_id=actor_id,
            )
        return {"history": history, "restored": restored}

    def _get_entity(self, workspace_id: str, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        if entity_type == "account":
            return self._store.get_account(workspace_id, entity_id)
        if entity_type == "lead":
            return self._store.get_lead(workspace_id, entity_id)
        if entity_type == "contact":
            return self._store.get_contact(workspace_id, entity_id)
        return None

    def _soft_delete_entity(self, workspace_id: str, entity_type: str, entity_id: str) -> None:
        if entity_type == "account":
            self._store.delete_account(workspace_id, entity_id)
        elif entity_type == "lead":
            self._store.delete_lead(workspace_id, entity_id)
        elif entity_type == "contact":
            self._store.delete_contact(workspace_id, entity_id)

    def _restore_entity(
        self,
        workspace_id: str,
        entity_type: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        data = {k: v for k, v in snapshot.items() if k not in ("id", "created_at", "updated_at", "deleted_at", "version")}
        data["external_source_id"] = data.get("external_source_id") or f"restore:{snapshot.get('id')}"
        if entity_type == "account":
            return self._store.create_account(workspace_id, str(data.get("name") or "Restored"), **data)
        if entity_type == "lead":
            return self._store.create_lead(workspace_id, **data)
        if entity_type == "contact":
            return self._store.create_contact(
                workspace_id,
                str(data.get("display_name") or "Restored"),
                **data,
            )
        raise ValueError(f"unsupported entity_type: {entity_type}")

    def _peer_rows(self, workspace_id: str, entity_type: str) -> list[dict[str, Any]]:
        if entity_type == "account":
            return self._store.list_accounts(workspace_id, limit=500)
        if entity_type == "lead":
            return self._store.list_leads(workspace_id, limit=500)
        if entity_type == "contact":
            return self._store.list_contacts(workspace_id, limit=500)
        return []

    def _fuzzy_candidates(
        self,
        workspace_id: str,
        *,
        entity_type: str,
        name: str | None,
        domain: str | None,
        min_score: float,
    ) -> list[FuzzyCandidate]:
        rows = self._peer_rows(workspace_id, entity_type)
        out: list[FuzzyCandidate] = []
        needle = (name or "").strip().lower()
        domain_n = (domain or "").strip().lower()
        for row in rows:
            score = 0.0
            keys: list[str] = []
            hay = str(row.get("name") or row.get("display_name") or row.get("company_name") or "").lower()
            if needle and hay and (needle in hay or hay in needle):
                score += 0.75
                keys.append("name_fuzzy")
            row_domain = str(row.get("domain") or "").lower()
            if domain_n and row_domain and domain_n == row_domain:
                score += 0.2
                keys.append("domain")
            if score >= min_score:
                out.append(
                    FuzzyCandidate(
                        entity_type=entity_type,
                        entity_id=row["id"],
                        score=min(score, 0.99),
                        match_keys=tuple(keys),
                        explanation="fuzzy name/domain overlap; Soft Wall required",
                    )
                )
        return out

    def _pair_score(
        self,
        entity_type: str,
        left: dict[str, Any],
        right: dict[str, Any],
        name: str | None,
        domain: str | None,
    ) -> tuple[float, tuple[str, ...], str]:
        score = 0.0
        keys: list[str] = []
        ln = str(left.get("name") or left.get("display_name") or left.get("company_name") or "").lower()
        rn = str(right.get("name") or right.get("display_name") or right.get("company_name") or "").lower()
        if ln and rn and (ln == rn or ln in rn or rn in ln):
            score += 0.75
            keys.append("name_fuzzy")
        ld = str(left.get("domain") or "").lower()
        rd = str(right.get("domain") or "").lower()
        if ld and rd and ld == rd:
            score += 0.2
            keys.append("domain")
        # Never treat email equality here as auto-merge; exact path handles that.
        explanation = f"fuzzy overlap on {', '.join(keys) or 'weak signals'}; consent not transferable"
        return min(score, 0.99), tuple(keys), explanation

    def _field_diff(self, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        keys = sorted(set(left.keys()) | set(right.keys()))
        diff: dict[str, Any] = {}
        for key in keys:
            if key in ("id", "created_at", "updated_at", "version", "workspace_id"):
                continue
            if left.get(key) != right.get(key):
                diff[key] = {"left": left.get(key), "right": right.get(key)}
        return diff

    def _account_keys(self, fields: dict[str, Any], row: dict[str, Any]) -> tuple[str, ...]:
        keys: list[str] = []
        if fields.get("external_source_id") and fields.get("external_source_id") == row.get("external_source_id"):
            keys.append("external_source_id")
        if fields.get("company_number") and fields.get("company_number") == row.get("company_number"):
            keys.append("company_number")
        if fields.get("domain") and str(fields.get("domain")).lower() == str(row.get("domain") or "").lower():
            keys.append("domain")
        email = _primary_email(fields.get("emails") or [])
        if email and email == _primary_email(row.get("emails") or []):
            keys.append("email")
        return tuple(keys or ("exact",))

    def _lead_keys(self, fields: dict[str, Any], row: dict[str, Any]) -> tuple[str, ...]:
        keys: list[str] = []
        if fields.get("external_source_id") and fields.get("external_source_id") == row.get("external_source_id"):
            keys.append("external_source_id")
        if fields.get("company_number") and fields.get("company_number") == row.get("company_number"):
            keys.append("company_number")
        email = _normalise_email(str(fields.get("email") or "")) or _primary_email(fields.get("emails") or [])
        if email and email == _primary_email(row.get("emails") or []):
            keys.append("email")
        return tuple(keys or ("exact",))

    def _contact_keys(self, fields: dict[str, Any], row: dict[str, Any]) -> tuple[str, ...]:
        keys: list[str] = []
        if fields.get("external_source_id") and fields.get("external_source_id") == row.get("external_source_id"):
            keys.append("external_source_id")
        email = _normalise_email(str(fields.get("email") or "")) or _primary_email(fields.get("emails") or [])
        if email and email == _primary_email(row.get("emails") or []):
            keys.append("email")
        return tuple(keys or ("exact",))
