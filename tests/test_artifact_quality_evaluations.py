"""후보 문서 의미 품질 Harness의 대표 사례·Skill 계약 회귀 테스트."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_PATH = _ROOT / "tests" / "fixtures" / "evaluations" / "artifact_quality_rubric.json"
_SKILL_PATH = _ROOT / "integrations" / "codex" / "SKILL.md"
_RUBRIC_LABELS = {
    "specificity": "구체성",
    "mvp_scope": "MVP 범위",
    "existing_impact": "기존 영향",
    "technology_evidence": "기술 스택 근거",
    "directory_factuality": "디렉터리 구조 사실성",
    "traceability": "추적성",
    "uncertainty": "불확실성 표기",
}
_CASE_IDS = {
    "new_web_service",
    "existing_api_compatibility_change",
    "legacy_refactor_performance_baseline",
    "reproducible_bug_fix",
    "ml_image_labeling_training",
}
_ALLOWED_EVIDENCE_STATUSES = {"CONFIRMED", "DETECTED", "RECOMMENDED", "UNRESOLVED"}
_REQUIRED_DOCUMENTS = {
    "REQUIREMENTS.md",
    "ARCHITECTURE.md",
    "IMPLEMENTATION_PLAN.md",
    "TEST_PLAN.md",
}
_PROTOTYPE_ACCEPTANCE_IDS = {
    "contract_traceability",
    "flow_and_recovery_visibility",
    "interaction_state_accessibility",
    "screen_specific_mock_state",
    "offline_non_ssot_boundary",
}


def _fixture() -> dict[str, object]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_artifact_quality_fixture_has_complete_rubric_and_representative_cases() -> None:
    fixture = _fixture()

    assert fixture["schema_version"] == 1
    rubric = fixture["rubric"]
    cases = fixture["cases"]
    prototype_acceptance = fixture["prototype_acceptance"]
    assert isinstance(rubric, list)
    assert isinstance(cases, list)
    assert {item["id"] for item in rubric} == set(_RUBRIC_LABELS)
    assert {item["label"] for item in rubric} == set(_RUBRIC_LABELS.values())
    assert all(item["expected_action"] for item in rubric)
    assert {item["id"] for item in cases} == _CASE_IDS

    observed_statuses: set[str] = set()
    for case in cases:
        input_context = case["input_context"]
        document_evidence = case["required_document_evidence"]
        statuses = set(case["expected_evidence_statuses"])
        assert set(input_context) == {
            "user_request",
            "intake_summary",
            "repository_evidence",
        }
        assert all(value for value in input_context.values())
        assert set(case["quality_focus"]).issubset(_RUBRIC_LABELS)
        assert case["quality_focus"]
        assert set(document_evidence) == _REQUIRED_DOCUMENTS
        assert all(values and all(values) for values in document_evidence.values())
        assert case["forbidden_claims"]
        assert statuses and statuses.issubset(_ALLOWED_EVIDENCE_STATUSES)
        observed_statuses.update(statuses)

    assert observed_statuses == _ALLOWED_EVIDENCE_STATUSES
    assert isinstance(prototype_acceptance, list)
    assert {item["id"] for item in prototype_acceptance} == _PROTOTYPE_ACCEPTANCE_IDS
    assert all(item["expected_action"] for item in prototype_acceptance)


def test_codex_skill_requires_artifact_quality_self_review() -> None:
    skill = _SKILL_PATH.read_text(encoding="utf-8")

    assert "## 후보 품질 자체 점검" in skill
    for label in _RUBRIC_LABELS.values():
        assert f"**{label}**" in skill
    assert "`RECOMMENDED` 또는 `UNRESOLVED`" in skill
    assert "방향을 바꾸는 고위험 차단 결정" in skill
    assert "프로토타입 품질 자체 점검" in skill
    assert "user_flows" in skill
    assert "error_states" in skill
    assert "ScreenSpec.states" in skill
