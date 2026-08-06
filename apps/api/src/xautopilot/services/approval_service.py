"""Central human-approval gates for idea generation, schedule, and publish."""

from __future__ import annotations

from dataclasses import dataclass


class ApprovalError(Exception):
    """Base class for approval gate failures."""


class IdeaNotApprovedError(ApprovalError):
    pass


class DraftNotReadyError(ApprovalError):
    pass


class DraftNotApprovedError(ApprovalError):
    pass


class MissingSelectedVariantError(ApprovalError):
    pass


# Status vocabulary aligned with existing models
IDEA_APPROVED = "approved"
DRAFT_READY = "ready"
DRAFT_APPROVED = "approved"
DRAFT_SCHEDULED = "scheduled"

PUBLISHABLE_DRAFT_STATUSES = frozenset({DRAFT_APPROVED, DRAFT_SCHEDULED})


@dataclass(frozen=True)
class IdeaState:
    status: str


@dataclass(frozen=True)
class DraftState:
    status: str
    selected_variant_id: str | None = None


def assert_can_generate_from_idea(idea: IdeaState) -> None:
    if idea.status != IDEA_APPROVED:
        raise IdeaNotApprovedError(
            f"Idea status must be '{IDEA_APPROVED}' to generate drafts (got '{idea.status}')"
        )


def assert_can_approve_draft(draft: DraftState) -> None:
    if draft.status != DRAFT_READY:
        raise DraftNotReadyError(
            f"Draft status must be '{DRAFT_READY}' to approve (got '{draft.status}')"
        )
    if not draft.selected_variant_id:
        raise MissingSelectedVariantError("Select a variant before approving a draft")


def assert_can_schedule(draft: DraftState) -> None:
    if draft.status != DRAFT_APPROVED:
        raise DraftNotApprovedError(
            f"Draft status must be '{DRAFT_APPROVED}' to schedule (got '{draft.status}')"
        )
    if not draft.selected_variant_id:
        raise MissingSelectedVariantError("Select a variant before scheduling")


def assert_can_publish(draft: DraftState) -> None:
    if draft.status not in PUBLISHABLE_DRAFT_STATUSES:
        raise DraftNotApprovedError(
            f"Draft status must be one of {sorted(PUBLISHABLE_DRAFT_STATUSES)} to publish "
            f"(got '{draft.status}')"
        )


def approve_draft_transition(draft: DraftState) -> str:
    """Return the next status after a successful approval."""
    assert_can_approve_draft(draft)
    return DRAFT_APPROVED
