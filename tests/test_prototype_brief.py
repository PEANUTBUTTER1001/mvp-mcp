"""시제품 단계 분리(서버 brief 없음)·디자인 무관여·검사 조건·계약 라벨 회귀 테스트."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import CreateAdaptiveWizardDraftUseCase
from mvp_mcp.domain.spec.candidate_package_model import CandidatePackageSource
from mvp_mcp.domain.spec.candidate_package_policy import inspect_candidate_package
from mvp_mcp.domain.spec.design_direction import (
    MAX_CONTRACT_SCREENS,
    build_product_design_contract,
)
from mvp_mcp.domain.spec.model import DesignContract, ProjectType, SpecDraft
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation.tools._adaptive_wizard_snapshot import adaptive_wizard_snapshot

NOW = datetime(2026, 11, 17, tzinfo=UTC)
TASK_LABELS = {
    "design_frequent_user_tasks": {
        "check_now": "지금 날씨 바로 보기",
        "check_past": "지난 날짜 날씨 찾아보기",
    }
}
DESIGN_FILES = (
    "docs/MVPDESIGN.md",
    "docs/design-tokens.json",
    "prototype/index.html",
    "prototype/REVIEW.md",
)


class _FixedClock:
    def now(self) -> datetime:
        return NOW


def _intake(**overrides: object) -> dict[str, object]:
    return {
        "work_type": "new_project",
        "solution_family": ["product_application"],
        "primary_surface": ["android_app", "web_app"],
        "app_domain_hint": ["business"],
        "target_context": "날씨 확인",
        "pain_points": ["scattered"],
        "pain_detail": "과거 날씨를 볼 수 없다.",
        "desired_change": "지금·지난 날씨를 한 앱에서 본다.",
        "success_signals": ["time"],
        "initial_audience": "known",
        "tech_stack": "ai_recommended",
        **overrides,
    }


def _design(tasks: object, **extra: object) -> dict[str, object]:
    return {
        "design_frequent_user_tasks": tasks,
        "design_must_features": {"selected": [], "other_text": "현재 날씨, 지난 날씨"},
        **extra,
    }


def _contract(
    design: dict[str, object], labels: dict[str, dict[str, str]] | None = None
) -> DesignContract:
    contract = build_product_design_contract(_intake(), design, labels)
    assert contract is not None
    return contract


def _legacy_design_files(contract: DesignContract) -> dict[str, str]:
    draft = SpecDraft(
        project_type=ProjectType.ETC,
        user_request="안드로이드 날씨앱",
        design_contract=contract,
        features=["현재 날씨", "지난 날씨"],
    )
    return DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(draft)


def _issues(files: dict[str, str]) -> list[str]:
    result = inspect_candidate_package(
        CandidatePackageSource(candidate_root="candidate", files=files),
        run_id="run-prototype-brief-0001",
        run_version=1,
    )
    # 필수 문서(AGENTS.md 등) 누락은 이 테스트의 관심 밖이므로 디자인·시제품 항목만 본다.
    return [
        issue
        for issue in result.validation.issues
        if any(word in issue for word in ("prototype", "MVPDESIGN", "design", "디자인"))
    ]


def _skill_prototype() -> str:
    """프로토타입 스킬로 자유롭게 만든 시제품(서버 표식·토큰 없음, style=·카드·자유 색)."""

    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>날씨</title>'
        "<style>body{margin:0;background:linear-gradient(#1E3A5F,#4A90D9);color:#fff}"
        ".card{border-radius:20px;box-shadow:0 8px 24px #0003;padding:16px}</style></head>"
        '<body><main><section class="card"><h1 style="font-size:64px">12°</h1>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12"'
        ' r="5"/></svg><button type="button">새로 고침</button></section></main>'
        "<script>const data={now:12};</script></body></html>"
    )


def test_product_app_asks_no_design_questions() -> None:
    required = required_product_design_question_ids(_intake())
    guidance = {question.id for question in product_design_question_guidance(_intake())}

    for design_id in ("design_visual_tone", "design_color_choice", "design_web_behavior"):
        assert design_id not in required
        assert design_id not in guidance
    assert {"design_frequent_user_tasks", "design_must_features"} <= required


def test_confirm_answer_uses_option_label_not_placeholder_code() -> None:
    labelled = _contract(
        _design("지금 날씨 확인", confirm_desired_change="AI_SUGGESTION"),
        {"confirm_desired_change": {"AI_SUGGESTION": "과거 날씨를 한곳에서 비교한다."}},
    )
    unlabelled = _contract(_design("지금 날씨 확인", confirm_desired_change="AI_SUGGESTION"))

    assert labelled.screens[0].purpose == "과거 날씨를 한곳에서 비교한다."
    assert unlabelled.screens[0].purpose == "지금·지난 날씨를 한 앱에서 본다."


def test_frequent_tasks_become_readable_flows_with_cap() -> None:
    single = _contract(_design("지금 날씨 확인"))
    pair = _contract(_design("지금 날씨 확인, 오늘·내일 예보 확인"))
    many = _contract(_design("1. 가 2. 나 3. 다 4. 라 5. 마 6. 바 7. 사"))
    coded = _contract(_design(["check_now", "check_past"]), TASK_LABELS)

    assert [screen.name for screen in single.screens] == ["핵심 작업"]
    assert [flow.name for flow in pair.user_flows] == ["지금 날씨 확인", "오늘·내일 예보 확인"]
    assert len(many.screens) == MAX_CONTRACT_SCREENS
    assert [flow.name for flow in coded.user_flows] == [
        "지금 날씨 바로 보기",
        "지난 날짜 날씨 찾아보기",
    ]


def test_docs_with_skill_prototype_pass_and_only_external_assets_fail() -> None:
    prototype = _skill_prototype()

    assert _issues({"prototype/index.html": prototype}) == []
    external = prototype.replace(
        "</head>", '<script src="https://cdn.example.com/app.js"></script></head>'
    )
    assert any("외부 자원" in issue for issue in _issues({"prototype/index.html": external}))


def test_legacy_design_files_still_get_the_four_file_contract() -> None:
    files = _legacy_design_files(_contract(_design("지금 날씨 확인, 지난 날씨 비교")))

    assert _issues(files) == []
    without_review = {key: value for key, value in files.items() if key != "prototype/REVIEW.md"}
    assert any("함께 생성되지" in issue for issue in _issues(without_review))


def _run(
    tmp_path: Path, run_id: str, intake: dict[str, object], design: dict[str, object]
) -> tuple[CreateAdaptiveWizardDraftUseCase, SqliteAdaptiveWizardRunRepository, str]:
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / f"{run_id}.sqlite3")
    questions = intake_questions()
    design_questions = product_design_question_guidance(intake)
    ids = {question.id for question in design_questions}
    run = AdaptiveWizardRun(
        id=run_id,
        request_key=f"{run_id}-request",
        user_request="안드로이드 날씨앱",
        project_root=str(tmp_path),
        status=AdaptiveRunStatus.DESIGN_SUBMITTED,
        write_policy=WritePolicy.GENERATE_ONLY,
        version=2,
        intake_questions=questions,
        intake_submission=make_submission(f"sub-i-{run_id}", questions, intake, NOW),
        design_questions=design_questions,
        design_submission=make_submission(
            f"sub-d-{run_id}",
            design_questions,
            {key: value for key, value in design.items() if key in ids},
            NOW,
        ),
        created_at=NOW,
        updated_at=NOW,
    )
    runs.create_or_get(run)
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    create = CreateAdaptiveWizardDraftUseCase(
        runs,
        specs,
        templates,
        ScopeMvpUseCase(specs, templates),
        CandidatePackageRepository(str(tmp_path / "output")),
        _FixedClock(),
    )
    return create, runs, run_id


def test_product_draft_has_no_prototype_step_or_design_files(tmp_path: Path) -> None:
    create, runs, run_id = _run(
        tmp_path, "run-prototype-brief-0001", _intake(), _design("지금 날씨 확인, 지난 날씨 비교")
    )

    ready = create(run_id)
    assert ready.status is AdaptiveRunStatus.DRAFT_READY
    assert not hasattr(ready, "prototype_brief")
    root = Path(ready.candidate_root or "")
    assert not any((root / path).exists() for path in DESIGN_FILES)
    stored = runs.find_by_id(run_id)
    assert stored is not None
    assert "prototype_brief" not in adaptive_wizard_snapshot(stored)


def test_legacy_brief_and_visual_check_payloads_still_load() -> None:
    run = AdaptiveWizardRun(
        id="run-legacy-visual-0001",
        request_key="legacy-visual-request-0001",
        user_request="날씨",
        project_root="C:/w",
        intake_questions=intake_questions(),
        created_at=NOW,
        updated_at=NOW,
    )
    payload = {
        **run.model_dump(mode="json"),
        "visual_checks": [{"width": 375, "status": "PASS", "checked_at": NOW.isoformat()}],
        "prototype_brief": {"target_path": "prototype/index.html", "skill_guide": ["old"]},
    }
    assert AdaptiveWizardRun.model_validate(payload).id == run.id
