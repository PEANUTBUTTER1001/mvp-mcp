"""가이드 기반 문서 프로파일·렌더링·preview/apply 테스트."""

from __future__ import annotations

from pathlib import Path

import pytest

from mvp_mcp.data.spec.guide_document_renderer import GuideDocumentRenderer
from mvp_mcp.data.spec.guide_package_renderer import GuidePackageRendererImpl
from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.data.spec.openapi_renderer import OpenApiRenderer
from mvp_mcp.data.spec.repository_document_exporter import RepositoryDocumentExporter
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.domain.spec.documentation_model import (
    AuthCapability,
    AuthMethod,
    DataChange,
    DocumentationIntake,
    DocumentProfile,
    HttpApiMode,
    OtherRisk,
    PersonalDataType,
    Prototype4Attestation,
    PrototypePreview,
    StorageNeed,
    StorageType,
    UiSurface,
)
from mvp_mcp.domain.spec.documentation_usecase import (
    ApplyDocumentationUseCase,
    PreviewDocumentationUseCase,
    ValidateDocumentationUseCase,
)
from mvp_mcp.domain.spec.guide_contract import DOCUMENT_CONTRACTS
from mvp_mcp.domain.spec.model import (
    BusinessRule,
    DataEntity,
    DeliveryTestCase,
    DesignContract,
    ErrorState,
    ImplementationTask,
    InterfaceContract,
    OpenDecision,
    Priority,
    ProjectType,
    Requirement,
    RequirementKind,
    ScreenSpec,
    SpecDraft,
    UserFlow,
)


def _draft(root: Path, documentation: DocumentationIntake | None = None) -> SpecDraft:
    requirement = Requirement(
        id="FR-001",
        kind=RequirementKind.FR,
        title="이미지 라벨 저장",
        description="사용자는 이미지에 분류 라벨을 지정하고 저장한다.",
        priority=Priority.P0,
        acceptance_criteria=["유효한 라벨이 저장된다.", "빈 라벨은 저장되지 않는다."],
    )
    return SpecDraft(
        project_type=ProjectType.ML_PROJECT,
        user_request="이미지 라벨링부터 모델 학습까지 지원되는 프로그램",
        project_root=str(root),
        intake={
            "problem": "라벨링과 학습 도구가 분리되어 실험 재현이 어렵다.",
            "goal": "하나의 흐름에서 데이터셋을 만들고 학습 결과를 비교한다.",
            "target_users": "컴퓨터 비전 실험 담당자",
            "success_metrics": "샘플 데이터로 라벨링부터 학습 완료까지 한 세션에 수행",
        },
        features=["이미지 가져오기", "라벨 편집", "데이터셋 분할", "모델 학습"],
        tech_stack={"runtime": "Python", "ml": "PyTorch"},
        requirements=[requirement],
        design_contract=DesignContract(
            screens=[
                ScreenSpec(
                    name="라벨링 작업대",
                    route="/label",
                    purpose="이미지를 보고 라벨을 지정한다.",
                    ui_elements=["이미지 캔버스", "라벨 목록", "저장 버튼"],
                    states=["로딩", "빈 데이터셋", "편집 중", "저장 오류"],
                )
            ],
            user_flows=[
                UserFlow(
                    name="학습 데이터 준비",
                    steps=["이미지 선택", "라벨 지정", "검증", "데이터셋 저장"],
                    exception_paths=["지원하지 않는 파일은 격리"],
                )
            ],
            data_entities=[
                DataEntity(
                    name="Annotation",
                    fields=["image_id: UUID", "label: string"],
                    constraints=["label은 허용 목록 값"],
                )
            ],
            interfaces=[
                InterfaceContract(
                    name="Annotation API",
                    kind="HTTP API",
                    purpose="라벨을 저장한다.",
                    input_summary="image_id와 label",
                    output_summary="저장된 annotation",
                    error_cases=["지원하지 않는 label", "이미지 없음"],
                )
            ],
            business_rules=[
                BusinessRule(
                    title="라벨 허용 목록",
                    rule="프로젝트에 등록된 라벨만 저장한다.",
                    rationale="학습 클래스의 일관성을 유지한다.",
                )
            ],
            error_states=[
                ErrorState(
                    trigger="이미지 읽기 실패",
                    user_message="이미지를 열 수 없습니다.",
                    recovery="파일을 건너뛰고 오류 목록을 제공한다.",
                )
            ],
        ),
        tasks=[
            ImplementationTask(
                id="TASK-001",
                requirement_ids=["FR-001"],
                title="라벨 저장 구현",
                file_scope=["src/labeling.py"],
                done_when=["TEST-001 통과"],
            )
        ],
        test_cases=[
            DeliveryTestCase(
                id="TEST-001",
                requirement_ids=["FR-001"],
                scenario="유효한 라벨 저장",
                expected_result="annotation이 저장된다.",
                kind="automated",
            )
        ],
        scope_confirmed=True,
        status="confirmed",
        documentation=documentation
        or DocumentationIntake(
            ui_surfaces=[UiSurface.WEB],
            http_api_mode=HttpApiMode.NEW,
            storage_need=StorageNeed.REQUIRED,
            storage_types=[StorageType.FILE],
            auth_capabilities=[AuthCapability.LOGIN],
            auth_methods=[AuthMethod.PASSWORD],
            personal_data_types=[PersonalDataType.USER_CONTENT],
            other_risks=[OtherRisk.FILE_UPLOAD, OtherRisk.EXTERNAL_INPUT],
            prototype_preview=PrototypePreview.REQUIRED,
        ),
    )


def _renderer() -> GuidePackageRendererImpl:
    return GuidePackageRendererImpl(
        GuideDocumentRenderer(), OpenApiRenderer(), HtmlPrototypeRenderer()
    )


def test_profiles_are_selected_from_security_and_migration_signals() -> None:
    assert DocumentationIntake().profile is DocumentProfile.MVP_6
    assert (
        DocumentationIntake(auth_capabilities=[AuthCapability.UNDECIDED]).profile
        is DocumentProfile.MVP_6_SECURITY
    )
    assert (
        DocumentationIntake(existing_data_change=DataChange.CHANGES).profile
        is DocumentProfile.MVP_6_MIGRATION
    )
    assert (
        DocumentationIntake(
            existing_data_change=DataChange.CHANGES,
            other_risks=[OtherRisk.FILE_UPLOAD],
        ).profile
        is DocumentProfile.MVP_6_FULL_RISK
    )


def test_exclusive_and_dependent_survey_choices_are_rejected() -> None:
    with pytest.raises(ValueError, match="함께 선택"):
        DocumentationIntake(ui_surfaces=[UiSurface.NONE, UiSurface.WEB])
    with pytest.raises(ValueError, match="종류"):
        DocumentationIntake(storage_need=StorageNeed.REQUIRED)
    with pytest.raises(ValueError, match="로그인 방식"):
        DocumentationIntake(auth_capabilities=[AuthCapability.LOGIN])


def test_renderer_fills_every_guide_section_and_optional_artifacts(tmp_path: Path) -> None:
    package = _renderer().render(_draft(tmp_path))

    assert package.profile is DocumentProfile.MVP_6_SECURITY
    assert "docs/SECURITY_PRIVACY.md" in package.files
    assert "docs/MIGRATION_PLAN.md" not in package.files
    assert "api/openapi.yaml" in package.files
    assert "prototype/index.html" in package.files
    for filename, contract in DOCUMENT_CONTRACTS.items():
        if filename in {"MIGRATION_PLAN.md", "DELIVERY_CHECKLIST.md"}:
            continue
        path = filename if filename == "AGENTS.md" else f"docs/{filename}"
        content = package.files[path]
        for index, section in enumerate(contract.sections, start=1):
            assert f"## {index}. {section}" in content
        assert "## 이 문서가 결정하는 것" in content
        assert "owner: UNASSIGNED" in content
    html = package.files["prototype/index.html"]
    assert "NON-SSOT PROTOTYPE" in html
    assert "connect-src 'none'" in html
    assert "mvpmcp-prototype-metadata" in html
    assert "http://" not in html and "https://" not in html


def test_prototype_four_requires_explicit_low_risk_attestations(tmp_path: Path) -> None:
    attestations = list(Prototype4Attestation)
    intake = DocumentationIntake(
        requested_profile=DocumentProfile.PROTOTYPE_4,
        prototype4_attestations=attestations,
    )
    assert intake.profile is DocumentProfile.PROTOTYPE_4
    package = _renderer().render(_draft(tmp_path, intake))
    assert {path for path in package.files if path.endswith(".md")} == {
        "README.md",
        "AGENTS.md",
        "docs/REQUIREMENTS.md",
        "docs/ARCHITECTURE.md",
        "docs/DELIVERY_CHECKLIST.md",
    }
    assert "docs/TEST_PLAN.md" not in package.files

    incomplete = intake.model_copy(update={"prototype4_attestations": attestations[:-1]})
    assert incomplete.profile is DocumentProfile.MVP_6
    risky = intake.model_copy(update={"other_risks": [OtherRisk.FILE_UPLOAD]})
    assert risky.profile is DocumentProfile.MVP_6_SECURITY


def test_pending_decision_blocks_preview(tmp_path: Path) -> None:
    draft = _draft(
        tmp_path,
        DocumentationIntake(auth_capabilities=[AuthCapability.UNDECIDED]),
    )
    repo = InMemorySpecRepository()
    spec_id = repo.save(draft)
    result = ValidateDocumentationUseCase(repo)(spec_id)
    assert result.bundle_valid
    assert not result.implementation_ready
    assert any("계획 미정" in item for item in result.blocking_items)


def test_resolved_design_decision_does_not_block_preview(tmp_path: Path) -> None:
    draft = _draft(tmp_path)
    assert draft.design_contract is not None
    draft.design_contract.open_decisions = [
        OpenDecision(
            topic="GUI 프레임워크",
            reason="Windows Python GUI 기본안",
            impact="화면과 패키징",
            status="resolved",
            decision="PySide6",
            source="recommended_default",
            confidence="high",
        )
    ]
    repo = InMemorySpecRepository()
    spec_id = repo.save(draft)

    result = ValidateDocumentationUseCase(repo)(spec_id)

    assert result.bundle_valid
    assert result.implementation_ready


def test_preview_apply_and_stale_prototype_flow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "server-output"
    repo = InMemorySpecRepository()
    spec_id = repo.save(_draft(project))
    exporter = RepositoryDocumentExporter(str(output))
    preview_uc = PreviewDocumentationUseCase(repo, _renderer(), exporter)
    apply_uc = ApplyDocumentationUseCase(exporter)

    preview = preview_uc(spec_id)
    assert not (project / ".mvpmcp").exists()
    assert not preview.conflicts
    assert any(item.relative_path == "prototype/index.html" for item in preview.artifacts)
    applied = apply_uc(
        preview.preview_id,
        preview.manifest_sha256,
        "project-owner",
        "생성 파일과 경로를 확인함",
    )
    assert applied.status == "APPLIED"
    assert (project / ".mvpmcp" / "prototype" / "index.html").is_file()
    assert (project / ".mvpmcp" / ".manifest.json").is_file()

    current = repo.find_by_id(spec_id)
    assert current is not None
    repo.save(
        current.model_copy(
            update={
                "documentation": current.documentation.model_copy(
                    update={"prototype_preview": PrototypePreview.NOT_REQUIRED}
                )
            }
        )
    )
    next_preview = preview_uc(spec_id)
    assert "prototype/index.html" in next_preview.stale_outputs
    assert (project / ".mvpmcp" / "prototype" / "index.html").is_file()


def test_unmanaged_conflict_blocks_all_target_writes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    conflict = project / ".mvpmcp" / "docs" / "REQUIREMENTS.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("user-owned", encoding="utf-8")
    repo = InMemorySpecRepository()
    spec_id = repo.save(_draft(project))
    exporter = RepositoryDocumentExporter(str(tmp_path / "preview"))
    preview = PreviewDocumentationUseCase(repo, _renderer(), exporter)(spec_id)

    assert "docs/REQUIREMENTS.md" in preview.conflicts
    result = ApplyDocumentationUseCase(exporter)(
        preview.preview_id, preview.manifest_sha256, "owner", "검토함"
    )
    assert result.status == "BLOCKED"
    assert conflict.read_text(encoding="utf-8") == "user-owned"
    assert not (project / ".mvpmcp" / "AGENTS.md").exists()


def test_apply_rejects_manifest_changed_after_preview(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    repo = InMemorySpecRepository()
    spec_id = repo.save(_draft(project))
    exporter = RepositoryDocumentExporter(str(tmp_path / "preview"))
    preview_uc = PreviewDocumentationUseCase(repo, _renderer(), exporter)
    apply_uc = ApplyDocumentationUseCase(exporter)
    initial = preview_uc(spec_id)
    apply_uc(initial.preview_id, initial.manifest_sha256, "owner", "초기 승인")

    preview = preview_uc(spec_id)
    manifest = project / ".mvpmcp" / ".manifest.json"
    manifest.write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="preview 이후 대상 파일이 변경"):
        apply_uc(preview.preview_id, preview.manifest_sha256, "owner", "재승인")
