import pytest

from xautopilot.services.approval_service import (
    DraftNotApprovedError,
    DraftNotReadyError,
    DraftState,
    IdeaNotApprovedError,
    IdeaState,
    MissingSelectedVariantError,
    approve_draft_transition,
    assert_can_generate_from_idea,
    assert_can_publish,
    assert_can_schedule,
)


def test_generate_requires_approved_idea():
    with pytest.raises(IdeaNotApprovedError):
        assert_can_generate_from_idea(IdeaState(status="proposed"))
    assert_can_generate_from_idea(IdeaState(status="approved"))


def test_approve_draft_requires_ready_and_variant():
    with pytest.raises(DraftNotReadyError):
        approve_draft_transition(DraftState(status="generating", selected_variant_id="v1"))
    with pytest.raises(MissingSelectedVariantError):
        approve_draft_transition(DraftState(status="ready", selected_variant_id=None))
    assert approve_draft_transition(DraftState(status="ready", selected_variant_id="v1")) == "approved"


def test_schedule_requires_approved_draft():
    with pytest.raises(DraftNotApprovedError):
        assert_can_schedule(DraftState(status="ready", selected_variant_id="v1"))
    assert_can_schedule(DraftState(status="approved", selected_variant_id="v1"))


def test_publish_allows_approved_or_scheduled():
    assert_can_publish(DraftState(status="approved", selected_variant_id="v1"))
    assert_can_publish(DraftState(status="scheduled", selected_variant_id="v1"))
    with pytest.raises(DraftNotApprovedError):
        assert_can_publish(DraftState(status="ready", selected_variant_id="v1"))
