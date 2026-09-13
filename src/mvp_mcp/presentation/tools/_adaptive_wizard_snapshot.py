"""Adaptive Wizard Tool이 공유하는 Run snapshot formatter."""

from __future__ import annotations

from mvp_mcp.domain.spec.adaptive_wizard_model import AdaptiveWizardRun


def adaptive_wizard_snapshot(run: AdaptiveWizardRun) -> dict[str, object]:
    """공개 Tool 응답에 필요한 영속 Run snapshot을 직렬화 가능한 값으로 만든다."""
    return {
        "run_id": run.id,
        "run_version": run.version,
        "status": run.status.value,
        "project_root": run.project_root,
        "write_policy": run.write_policy.value if run.write_policy is not None else None,
        "user_request": run.user_request,
        "intake_answers": run.intake_submission.answers if run.intake_submission else None,
        "design_questions": [question.model_dump(mode="json") for question in run.design_questions],
        "design_answers": run.design_submission.answers if run.design_submission else None,
        "spec_id": run.spec_id,
        "candidate_root": run.candidate_root,
        "candidate_lifecycle": run.candidate_lifecycle.model_dump(mode="json"),
        "candidate_sync_required": run.candidate_sync_required,
        "candidate_sync_base_revision": run.candidate_sync_base_revision,
        "candidate_revision": run.candidate_revision,
        "candidate_profile": (
            run.candidate_profile.value if run.candidate_profile is not None else None
        ),
        "preview_id": run.preview_id,
        "preview_manifest_sha256": run.preview_manifest_sha256,
        "preview_conflicts": run.preview_conflicts,
        "applied_outputs": run.applied_outputs,
        "applied_candidate_cycles": [
            cycle.model_dump(mode="json") for cycle in run.applied_candidate_cycles
        ],
    }
