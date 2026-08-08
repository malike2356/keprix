"""CRM domain constants and frozen names (programme 429 architecture lock)."""

from __future__ import annotations

from enum import StrEnum


class CrmStage(StrEnum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    LISTED = "listed"
    APPROVED = "approved"
    ENROLLED = "enrolled"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    BOOKED = "booked"
    CUSTOMER = "customer"
    PAYING = "paying"
    SUPPRESSED = "suppressed"
    BOUNCED = "bounced"
    DO_NOT_CONTACT = "do_not_contact"
    LOST = "lost"


FORWARD_STAGES: tuple[str, ...] = (
    CrmStage.DISCOVERED,
    CrmStage.ENRICHED,
    CrmStage.LISTED,
    CrmStage.APPROVED,
    CrmStage.ENROLLED,
    CrmStage.CONTACTED,
    CrmStage.ENGAGED,
    CrmStage.QUALIFIED,
    CrmStage.BOOKED,
    CrmStage.CUSTOMER,
    CrmStage.PAYING,
)

TERMINAL_STAGES: tuple[str, ...] = (
    CrmStage.SUPPRESSED,
    CrmStage.BOUNCED,
    CrmStage.DO_NOT_CONTACT,
    CrmStage.LOST,
)

ALL_STAGES: frozenset[str] = frozenset(FORWARD_STAGES + TERMINAL_STAGES)


class ProvenanceKind(StrEnum):
    OBSERVED = "observed"
    USER_SUPPLIED = "user_supplied"
    DERIVED = "derived"
    MODEL_INFERRED = "model_inferred"
    VERIFIED = "verified"


class EntityType(StrEnum):
    ACCOUNT = "account"
    LEAD = "lead"
    CONTACT = "contact"
    DEAL = "deal"
    ACTIVITY = "activity"
    LIST = "list"
    LIST_MEMBERSHIP = "list_membership"
    ENRICHMENT_JOB = "enrichment_job"
    CONSENT_RECORD = "consent_record"
    SUPPRESSION_ENTRY = "suppression_entry"
    DISCOVERY_JOB = "discovery_job"
    OUTBOX_RECORD = "outbox_record"
    MERGE_SUGGESTION = "merge_suggestion"
    CONTACTABILITY_DECISION = "contactability_decision"
    SENDER_READINESS = "sender_readiness"
    KILL_SWITCH = "kill_switch"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class MergeSuggestionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVERSED = "reversed"


class ContactabilityVerdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_REVIEW = "needs_review"


DEFAULT_DOMAIN_PACK = "generic"
