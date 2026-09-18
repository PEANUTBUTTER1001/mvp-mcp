"""디자인 계약 산출물과 제품 UI Wizard 회귀."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.design_artifact_renderer import DesignArtifactRendererImpl
from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardRun,
    WritePolicy,
    make_submission,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    intake_questions,
    product_design_question_guidance,
    required_product_design_question_ids,
    validate_design_questions,
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import CreateAdaptiveWizardDraftUseCase
from mvp_mcp.domain.spec.candidate_package_model import CandidatePackageSource
from mvp_mcp.domain.spec.candidate_package_policy import inspect_candidate_package
from mvp_mcp.domain.spec.design_direction import build_product_design_contract
from mvp_mcp.domain.spec.documentation_model import (
    DocumentationIntake,
    PrototypePreview,
    UiSurface,
)
from mvp_mcp.domain.spec.model import ProjectType, SpecDraft
from mvp_mcp.domain.spec.palette import contrast_ratio
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 16, tzinfo=UTC)


def _intake() -> dict[str, str]:
    return {
        "work_type": "new_project",
        "solution_family": "product_application",
        "primary_surface": "web_app",
        "app_domain_hint": "general_business",
        "target_context": "식당 운영 기록",
        "problem": "마감 기록이 누락되기 쉽다.",
        "goal": "당일 영업 기록을 빠르게 입력하고 확인한다.",
        "affected_users": "식당 운영자",
        "mvp_scope": "매출 기록, 지출 기록, 날짜별 확인",
        "success_criteria": "오늘 기록을 3분 안에 저장한다.",
        "constraints_risks": "기록 누락을 명확히 보여 준다.",
        "tech_stack": "AI 권장안 사용",
        "new_project_boundary": "기록 입력과 확인만 포함한다.",
        "new_project_launch_context": "매장 모바일과 데스크톱 브라우저",
        "new_project_known_dependencies": "없음",
    }


def _design_answers() -> dict[str, object]:
    return {
        "design_frequent_user_tasks": "오늘 매출 기록, 지출 기록, 날짜별 기록 검토",
        "design_visual_tone": "차분하고 정돈된 운영 도구, 화려한 대시보드는 피한다.",
        "design_color_source": "#0F766E",
        "design_web_behavior": "balanced",
    }


def test_product_design_questions_are_required_and_web_adds_behavior() -> None:
    intake = _intake()
    questions = product_design_question_guidance(intake)
    required = required_product_design_question_ids(intake)

    assert {question.id for question in questions} == required
    assert questions[0].label == "사용자가 이 제품에서 자주 하는 작업은 무엇인가요?"
    assert (
        validate_design_questions(
            questions, {question.id for question in intake_questions()}, required
        )
        == questions
    )

    with pytest.raises(ValueError, match="제품 UI 디자인 질문"):
        validate_design_questions(
            questions[:-1], {question.id for question in intake_questions()}, required
        )


def test_design_artifacts_have_complete_document_tokens_and_shared_hash() -> None:
    intake = _intake()
    contract = build_product_design_contract(
        intake, {key: str(value) for key, value in _design_answers().items()}
    )
    assert contract is not None
    draft = SpecDraft(
        project_type=ProjectType.ETC,
        user_request="식당 기록 관리 앱",
        design_contract=contract,
        documentation=DocumentationIntake(
            ui_surfaces=[UiSurface.WEB], prototype_preview=PrototypePreview.REQUIRED
        ),
    )

    artifacts = DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(draft)
    assert set(artifacts) == {
        "docs/MVPDESIGN.md",
        "docs/design-tokens.json",
        "prototype/index.html",
        "prototype/REVIEW.md",
    }
    document = artifacts["docs/MVPDESIGN.md"]
    tokens = json.loads(artifacts["docs/design-tokens.json"])
    design_hash = tokens["design_hash"]
    adjustment_reason = (
        "선택한 색상과 전경색의 WCAG 대비를 충족하도록 UI용 primary tone을 조정했다."
    )

    assert all(f"## {index}." in document for index in range(1, 15))
    assert "## 1. 디자인 결정 요약" in document
    assert "## 7. 화면별 설계 브리프" in document
    assert "## 10. 구현 준수 규칙" in document
    assert "| 결정 영역 | 결정값 | 상태 | 근거 | 검증 기준 |" in document
    assert "### 화면: 핵심 작업" in document
    assert "빈 상태" in document
    assert tokens["version"] == 3
    assert tokens["palette_source"] == {
        "brand_seed": "#0F766E",
        "seed_status": "CONFIRMED",
        "palette_intent": "warm_service",
        "generator": "oklch-v1",
        "primary_adjusted_for_accessibility": True,
        "adjustment_reason": adjustment_reason,
    }
    assert tokens["platform_targets"] == ["web", "mobile", "desktop"]
    assert tokens["cross_platform"]["enabled"] is True
    assert tokens["color"]["light"]["primary"] == "#0F766E"
    assert tokens["color"]["light"]["primary_container"] != "#CCFBF1"
    assert tokens["color"]["dark"]["primary"] != tokens["color"]["light"]["primary"]
    assert tokens["accessibility"]["high_contrast_text_minimum_ratio"] == 7.0
    for theme in ("light", "dark", "high_contrast"):
        assert "disabled_content" in tokens["color"][theme]
        assert "error_container" in tokens["color"][theme]
        assert contrast_ratio(
            tokens["color"][theme]["primary"], tokens["color"][theme]["on_primary"]
        ) >= (7.0 if theme == "high_contrast" else 4.5)
    assert "var(--brand)" in artifacts["prototype/index.html"]
    assert 'data-theme="high_contrast"' in artifacts["prototype/index.html"]
    assert "style=" not in artifacts["prototype/index.html"]
    assert "aria-errormessage=" in artifacts["prototype/index.html"]
    assert design_hash in document
    assert design_hash in artifacts["prototype/index.html"]
    assert design_hash in artifacts["prototype/REVIEW.md"]
    assert 'data-layout="list_detail"' in artifacts["prototype/index.html"]


def test_candidate_policy_rejects_design_hash_mismatch() -> None:
    intake = _intake()
    contract = build_product_design_contract(
        intake, {key: str(value) for key, value in _design_answers().items()}
    )
    assert contract is not None
    draft = SpecDraft(
        project_type=ProjectType.ETC, user_request="식당 기록", design_contract=contract
    )
    files = DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(draft)
    tokens = json.loads(files["docs/design-tokens.json"])
    tokens["design_hash"] = "b" * 64
    files["docs/design-tokens.json"] = json.dumps(tokens)

    result = inspect_candidate_package(
        CandidatePackageSource(candidate_root="candidate", files=files),
        run_id="run-design-artifact-0001",
        run_version=1,
    )

    assert any("design_hash가 일치" in issue for issue in result.validation.issues)


def test_candidate_policy_rejects_incomplete_design_token_theme() -> None:
    intake = _intake()
    contract = build_product_design_contract(
        intake, {key: str(value) for key, value in _design_answers().items()}
    )
    assert contract is not None
    draft = SpecDraft(
        project_type=ProjectType.ETC, user_request="식당 기록", design_contract=contract
    )
    files = DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(draft)
    tokens = json.loads(files["docs/design-tokens.json"])
    del tokens["color"]["high_contrast"]["disabled_content"]
    files["docs/design-tokens.json"] = json.dumps(tokens)

    result = inspect_candidate_package(
        CandidatePackageSource(candidate_root="candidate", files=files),
        run_id="run-design-artifact-0002",
        run_version=1,
    )

    assert any("high_contrast theme 역할" in issue for issue in result.validation.issues)


def test_candidate_policy_rejects_v3_palette_with_insufficient_primary_contrast() -> None:
    contract = build_product_design_contract(
        _intake(), {key: str(value) for key, value in _design_answers().items()}
    )
    assert contract is not None
    files = DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(
        SpecDraft(project_type=ProjectType.ETC, user_request="식당 기록", design_contract=contract)
    )
    tokens = json.loads(files["docs/design-tokens.json"])
    tokens["color"]["light"]["primary"] = "#FFFFFF"
    tokens["color"]["light"]["on_primary"] = "#FFFFFF"
    files["docs/design-tokens.json"] = json.dumps(tokens)

    result = inspect_candidate_package(
        CandidatePackageSource(candidate_root="candidate", files=files),
        run_id="run-design-artifact-0003",
        run_version=1,
    )

    assert any("primary/on_primary 대비" in issue for issue in result.validation.issues)


def test_candidate_policy_accepts_legacy_v2_design_tokens() -> None:
    contract = build_product_design_contract(
        _intake(), {key: str(value) for key, value in _design_answers().items()}
    )
    assert contract is not None
    files = DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(
        SpecDraft(project_type=ProjectType.ETC, user_request="식당 기록", design_contract=contract)
    )
    tokens = json.loads(files["docs/design-tokens.json"])
    tokens["version"] = 2
    tokens.pop("palette_source")
    tokens.pop("accessibility")
    files["docs/design-tokens.json"] = json.dumps(tokens)

    result = inspect_candidate_package(
        CandidatePackageSource(candidate_root="candidate", files=files),
        run_id="run-design-artifact-legacy-v2",
        run_version=1,
    )

    assert not any("version 2 또는 3" in issue for issue in result.validation.issues)
    assert not any("palette_source" in issue for issue in result.validation.issues)


def test_product_wizard_initializes_design_artifacts_in_candidate_root(tmp_path: Path) -> None:
    clock = _FixedClock()
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "runs.sqlite3")
    candidates = CandidatePackageRepository(str(tmp_path / "output"))
    intake_questions_value = intake_questions()
    design_questions = product_design_question_guidance(_intake())
    run = AdaptiveWizardRun(
        id="run-design-artifact-0001",
        request_key="design-artifact-request-0001",
        user_request="식당 기록 관리 앱",
        project_root=str(tmp_path),
        status=AdaptiveRunStatus.DESIGN_SUBMITTED,
        write_policy=WritePolicy.GENERATE_ONLY,
        version=2,
        intake_questions=intake_questions_value,
        intake_submission=make_submission(
            "sub-intake-design-0001", intake_questions_value, _intake(), clock.now()
        ),
        design_questions=design_questions,
        design_submission=make_submission(
            "sub-design-artifact-0001", design_questions, _design_answers(), clock.now()
        ),
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    runs.create_or_get(run)
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    create = CreateAdaptiveWizardDraftUseCase(
        runs,
        specs,
        templates,
        ScopeMvpUseCase(specs, templates),
        candidates,
        clock,
        DesignArtifactRendererImpl(HtmlPrototypeRenderer()),
    )

    ready = create(run.id)
    assert ready.status is AdaptiveRunStatus.DRAFT_READY
    assert ready.candidate_root is not None
    root = Path(ready.candidate_root)
    assert (root / "docs" / "MVPDESIGN.md").is_file()
    assert (root / "docs" / "design-tokens.json").is_file()
    assert (root / "prototype" / "index.html").is_file()
    assert (root / "prototype" / "REVIEW.md").is_file()
