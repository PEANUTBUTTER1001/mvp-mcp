"""Run 전용 candidate package 검증·preview·write policy 회귀 테스트."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.repository_document_exporter import RepositoryDocumentExporter
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardQuestion,
    AdaptiveWizardRun,
    WizardQuestionKind,
    WritePolicy,
    make_submission,
)
from mvp_mcp.domain.spec.candidate_lifecycle_usecase import (
    UpdateCandidateRequirementsUseCase,
)
from mvp_mcp.domain.spec.candidate_package_usecase import (
    ApplyCandidatePackageUseCase,
    GetCandidatePackageStatusUseCase,
    PreviewCandidatePackageUseCase,
    ValidateCandidatePackageUseCase,
)
from mvp_mcp.domain.spec.guide_contract import DOCUMENT_CONTRACTS
from mvp_mcp.domain.spec.model import Priority, RequirementInput
from mvp_mcp.main import build
from mvp_mcp.presentation.tools.documentation_apply_package import (
    register_documentation_apply_package_tool,
)
from mvp_mcp.presentation.tools.documentation_package_status import (
    register_documentation_package_status_tool,
)
from mvp_mcp.presentation.tools.documentation_preview_package import (
    register_documentation_preview_package_tool,
)
from mvp_mcp.presentation.tools.documentation_validate_package import (
    register_documentation_validate_package_tool,
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 12, tzinfo=UTC)


def _wire(tmp_path: Path, policy: WritePolicy = WritePolicy.GENERATE_ONLY) -> tuple[
    AdaptiveWizardRun,
    SqliteAdaptiveWizardRunRepository,
    CandidatePackageRepository,
    ValidateCandidatePackageUseCase,
    PreviewCandidatePackageUseCase,
    ApplyCandidatePackageUseCase,
    GetCandidatePackageStatusUseCase,
    Path,
    Path,
]:
    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "server-output"
    candidates = CandidatePackageRepository(str(output))
    candidate_root = candidates.ensure_workspace("run-candidate-0001")
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    clock = _FixedClock()
    intake_questions = [
        AdaptiveWizardQuestion(
            id="write_policy",
            label="반영 정책",
            kind=WizardQuestionKind.SELECT,
            options=[value.value for value in WritePolicy],
        )
    ]
    design_questions = [
        AdaptiveWizardQuestion(
            id=f"design_{index}",
            label=f"설계 {index}",
            kind=WizardQuestionKind.TEXT,
        )
        for index in range(1, 4)
    ]
    run = AdaptiveWizardRun(
        id="run-candidate-0001",
        request_key="candidate-request-0001",
        user_request="후보 package를 생성한다",
        project_root=str(project),
        status=AdaptiveRunStatus.DRAFT_READY,
        write_policy=policy,
        version=4,
        intake_questions=intake_questions,
        intake_submission=make_submission(
            "sub-intake-0001",
            intake_questions,
            {"write_policy": policy.value},
            clock.now(),
        ),
        design_questions=design_questions,
        design_submission=make_submission(
            "sub-design-0001",
            design_questions,
            {question.id: "확정" for question in design_questions},
            clock.now(),
        ),
        spec_id="adaptive-run-candidate-0001",
        candidate_root=candidate_root,
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    runs.create_or_get(run)
    exporter = RepositoryDocumentExporter(str(output))
    return (
        run,
        runs,
        candidates,
        ValidateCandidatePackageUseCase(runs, candidates, clock),
        PreviewCandidatePackageUseCase(runs, candidates, exporter, clock),
        ApplyCandidatePackageUseCase(runs, candidates, exporter, clock),
        GetCandidatePackageStatusUseCase(runs, candidates, exporter),
        project,
        Path(candidate_root),
    )


def _write_valid_mvp_candidate(root: Path) -> None:
    (root / "README.md").write_text("# Candidate package\n", encoding="utf-8")
    names = {
        "REQUIREMENTS.md",
        "ARCHITECTURE.md",
        "AGENTS.md",
        "IMPLEMENTATION_PLAN.md",
        "TEST_PLAN.md",
        "RELEASE_RUNBOOK.md",
    }
    for name in names:
        path = root / name if name == "AGENTS.md" else root / "docs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = {
            "REQUIREMENTS.md": "FR-001\nAC-001",
            "IMPLEMENTATION_PLAN.md": "TASK-001",
            "TEST_PLAN.md": "TEST-001\nNOT RUN",
            "RELEASE_RUNBOOK.md": "REL-001\nNOT RUN",
        }.get(name, "내용")
        section_values = {
            "기술 스택": (
                "| 분류 | 기술·버전 | 역할 | 근거 상태 | 결정·근거 |\n"
                "|---|---|---|---|---|\n"
                "| Runtime | Python 3.12 | 실행 환경 | CONFIRMED | 후보 작성자가 명시한 런타임 |"
            ),
            "디렉터리 구조": "```text\nsrc/  # [KEEP] 구현 소스\n```",
            "변경 파일": "TASK-001\n\n- 경로 SSOT: `ARCHITECTURE.md`의 `디렉터리 구조`를 따른다.",
        }
        sections = "\n\n".join(
            f"## {section}\n\n{section_values.get(section, markers)}"
            for section in DOCUMENT_CONTRACTS[name].sections
        )
        path.write_text(f"# {name}\n\n{sections}\n", encoding="utf-8")


def test_generate_only_candidate_validate_preview_keeps_project_unchanged(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, preview, _apply, status, project, candidate = _wire(tmp_path)
    _write_valid_mvp_candidate(candidate)

    observed = status(run.id)
    assert observed.current_candidate_revision
    assert observed.candidate_valid
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    assert validated.valid
    assert validated.run_version == 5
    prepared = preview(run.id, validated.run_version, validated.candidate_revision)

    assert prepared.status == AdaptiveRunStatus.PREVIEW_READY.value
    assert prepared.preview.preview_directory.endswith(prepared.preview.preview_id)
    preview_directory = (
        candidate.parent.parent.parent / "previews" / run.id / prepared.preview.preview_id
    )
    assert preview_directory.is_dir()
    assert not (project / ".mvpmcp").exists()
    assert status(run.id).status == AdaptiveRunStatus.PREVIEW_READY.value


@pytest.mark.parametrize(
    ("path", "original", "replacement", "expected_issue"),
    [
        (
            "docs/ARCHITECTURE.md",
            "| 분류 | 기술·버전 | 역할 | 근거 상태 | 결정·근거 |",
            "| 분류 | 기술 | 역할 | 근거 상태 | 결정·근거 |",
            "표준 5열",
        ),
        (
            "docs/ARCHITECTURE.md",
            "| Runtime | Python 3.12 | 실행 환경 | CONFIRMED | 후보 작성자가 명시한 런타임 |",
            "| Runtime | Python 3.12 | 실행 환경 | ASSUMED | 후보 작성자가 명시한 런타임 |",
            "근거 상태가 허용되지",
        ),
        (
            "docs/ARCHITECTURE.md",
            "src/  # [KEEP] 구현 소스",
            "src/  # [UNKNOWN] 구현 소스",
            "디렉터리 라벨이 허용되지",
        ),
        (
            "docs/ARCHITECTURE.md",
            "```text\nsrc/  # [KEEP] 구현 소스\n```",
            "src/  # [KEEP] 구현 소스",
            "코드 펜스",
        ),
        (
            "docs/IMPLEMENTATION_PLAN.md",
            "`ARCHITECTURE.md`의 `디렉터리 구조`를 따른다.",
            "구현 계획의 경로를 따른다.",
            "디렉터리 구조 SSOT를 참조",
        ),
    ],
)
def test_candidate_validation_rejects_architecture_contract_violations(
    tmp_path: Path,
    path: str,
    original: str,
    replacement: str,
    expected_issue: str,
) -> None:
    run, _runs, _candidates, validate, _preview, _apply, status, _project, candidate = _wire(
        tmp_path
    )
    _write_valid_mvp_candidate(candidate)
    target = candidate / path
    target.write_text(
        target.read_text(encoding="utf-8").replace(original, replacement), encoding="utf-8"
    )

    observed = status(run.id)
    result = validate(run.id, observed.run_version, observed.current_candidate_revision)

    assert not result.valid
    assert expected_issue in "\n".join(result.issues)


def test_candidate_validation_allows_escaped_pipe_in_technology_value(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, _preview, _apply, status, _project, candidate = _wire(
        tmp_path
    )
    _write_valid_mvp_candidate(candidate)
    architecture = candidate / "docs" / "ARCHITECTURE.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8").replace("Python 3.12", r"Python \| 3.12"),
        encoding="utf-8",
    )

    observed = status(run.id)
    result = validate(run.id, observed.run_version, observed.current_candidate_revision)

    assert result.valid


def test_safe_auto_apply_applies_only_when_no_conflict(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, preview, apply, status, project, candidate = _wire(
        tmp_path, WritePolicy.SAFE_AUTO_APPLY
    )
    _write_valid_mvp_candidate(candidate)
    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    result = preview(run.id, validated.run_version, validated.candidate_revision)

    assert result.status == AdaptiveRunStatus.APPLIED.value
    assert result.auto_apply is not None
    assert result.auto_apply.status == "APPLIED"
    assert (project / ".mvpmcp" / "docs" / "REQUIREMENTS.md").is_file()
    assert status(run.id).status == AdaptiveRunStatus.APPLIED.value
    denied = apply(run.id, result.run_version, "unused", "0" * 64, "", "")
    assert denied.status == "POLICY_DENIED"


def test_safe_auto_apply_preserves_unmanaged_conflict_and_candidate(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, preview, _apply, status, project, candidate = _wire(
        tmp_path, WritePolicy.SAFE_AUTO_APPLY
    )
    _write_valid_mvp_candidate(candidate)
    conflict = project / ".mvpmcp" / "docs" / "REQUIREMENTS.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("user-owned", encoding="utf-8")

    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    result = preview(run.id, validated.run_version, validated.candidate_revision)

    assert result.status == AdaptiveRunStatus.CONFLICTED.value
    assert "docs/REQUIREMENTS.md" in result.preview.conflicts
    assert conflict.read_text(encoding="utf-8") == "user-owned"
    assert (candidate / "docs" / "REQUIREMENTS.md").is_file()
    assert status(run.id).status == AdaptiveRunStatus.CONFLICTED.value


def test_manual_apply_requires_binding_and_explicit_approval(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, preview, apply, status, project, candidate = _wire(
        tmp_path, WritePolicy.MANUAL_APPLY
    )
    _write_valid_mvp_candidate(candidate)
    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    prepared = preview(run.id, validated.run_version, validated.candidate_revision)

    with pytest.raises(PipelineError, match="승인자"):
        apply(
            run.id,
            prepared.run_version,
            prepared.preview.preview_id,
            prepared.preview.manifest_sha256,
            "",
            "",
        )
    applied = apply(
        run.id,
        prepared.run_version,
        prepared.preview.preview_id,
        prepared.preview.manifest_sha256,
        "project-owner",
        "후보 preview 확인 후 수동 반영",
    )
    assert applied.status == "APPLIED"
    assert (project / ".mvpmcp" / "AGENTS.md").is_file()
    assert status(run.id).status == AdaptiveRunStatus.APPLIED.value


def test_candidate_change_after_validation_requires_new_revision(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, preview, _apply, status, _project, candidate = _wire(
        tmp_path
    )
    _write_valid_mvp_candidate(candidate)
    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    requirements = candidate / "docs" / "REQUIREMENTS.md"
    requirements.write_text(requirements.read_text(encoding="utf-8") + "\n변경\n", encoding="utf-8")

    with pytest.raises(PipelineError, match="candidate_revision"):
        preview(run.id, validated.run_version, validated.candidate_revision)
    refreshed = status(run.id)
    assert refreshed.current_candidate_revision != validated.candidate_revision
    assert refreshed.recorded_candidate_revision == validated.candidate_revision


def test_invalid_candidate_does_not_advance_run_version(tmp_path: Path) -> None:
    run, _runs, _candidates, validate, _preview, _apply, status, _project, candidate = _wire(
        tmp_path
    )
    (candidate / "README.md").write_text("# incomplete\n", encoding="utf-8")
    observed = status(run.id)
    result = validate(run.id, observed.run_version, observed.current_candidate_revision)

    assert not result.valid
    assert result.run_version == run.version
    assert any("필수 문서" in issue for issue in result.issues)
    assert status(run.id).status == AdaptiveRunStatus.DRAFT_READY.value


def test_candidate_and_validation_survive_server_recreation(tmp_path: Path) -> None:
    run, _runs, candidates, validate, _preview, _apply, status, project, candidate = _wire(tmp_path)
    _write_valid_mvp_candidate(candidate)
    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)

    restored_runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    restored_exporter = RepositoryDocumentExporter(str(tmp_path / "server-output"))
    restored_status = GetCandidatePackageStatusUseCase(restored_runs, candidates, restored_exporter)
    restored_preview = PreviewCandidatePackageUseCase(
        restored_runs, candidates, restored_exporter, _FixedClock()
    )
    current = restored_status(run.id)
    assert current.run_version == validated.run_version
    assert current.current_candidate_revision == validated.candidate_revision
    replayed = restored_preview(run.id, current.run_version, current.current_candidate_revision)

    assert replayed.status == AdaptiveRunStatus.PREVIEW_READY.value
    assert not (project / ".mvpmcp").exists()


def test_lifecycle_change_requires_a_fresh_candidate_document_revision(tmp_path: Path) -> None:
    run, runs, candidates, validate, _preview, _apply, status, _project, candidate = _wire(tmp_path)
    _write_valid_mvp_candidate(candidate)
    observed = status(run.id)
    validated = validate(run.id, observed.run_version, observed.current_candidate_revision)
    requirements = UpdateCandidateRequirementsUseCase(runs, candidates, _FixedClock())
    updated = requirements(
        run.id,
        validated.run_version,
        [
            RequirementInput(
                title="Run 후보 계약을 영속한다",
                description="구조화 lifecycle 변경은 candidate 문서 갱신을 요구한다.",
                priority=Priority.P0,
                acceptance_criteria=["Run에 저장한다", "candidate를 다시 검증한다"],
            )
        ],
    )

    with pytest.raises(PipelineError, match="candidate Markdown"):
        validate(run.id, updated.run_version, observed.current_candidate_revision)

    requirements_document = candidate / "docs" / "REQUIREMENTS.md"
    requirements_document.write_text(
        requirements_document.read_text(encoding="utf-8") + "\n\nRun lifecycle 반영\n",
        encoding="utf-8",
    )
    refreshed = status(run.id)
    result = validate(run.id, refreshed.run_version, refreshed.current_candidate_revision)

    assert result.valid
    assert result.run_version == refreshed.run_version + 1
    assert not status(run.id).candidate_sync_required


def test_candidate_package_tools_complete_status_validate_preview_chain(tmp_path: Path) -> None:
    async def scenario() -> None:
        run, _runs, _candidates, validate, preview, apply, status, _project, candidate = _wire(
            tmp_path
        )
        _write_valid_mvp_candidate(candidate)
        server = FastMCP("candidate_package_test")
        register_documentation_package_status_tool(server, status)
        register_documentation_validate_package_tool(server, validate)
        register_documentation_preview_package_tool(server, preview)
        register_documentation_apply_package_tool(server, apply)

        async with create_connected_server_and_client_session(server) as client:
            status_response = await client.call_tool(
                "documentation_package_status", {"run_id": run.id}
            )
            assert status_response.isError is False
            observed = json.loads(status_response.content[0].text or "{}")
            validate_response = await client.call_tool(
                "documentation_validate_package",
                {
                    "run_id": run.id,
                    "run_version": observed["run_version"],
                    "candidate_revision": observed["current_candidate_revision"],
                },
            )
            assert validate_response.isError is False
            validated = json.loads(validate_response.content[0].text or "{}")
            preview_response = await client.call_tool(
                "documentation_preview_package",
                {
                    "run_id": run.id,
                    "run_version": validated["run_version"],
                    "candidate_revision": validated["candidate_revision"],
                },
            )
            assert preview_response.isError is False
            result = json.loads(preview_response.content[0].text or "{}")
            assert result["status"] == AdaptiveRunStatus.PREVIEW_READY.value

    asyncio.run(scenario())


def test_composed_server_runs_candidate_lifecycle_then_validates_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Composition Root의 신규 lifecycle Tool만으로 후보 계약부터 preview까지 진행한다."""

    async def scenario() -> None:
        run, _runs, _candidates, _validate, _preview, _apply, _status, project, candidate = _wire(
            tmp_path
        )
        _write_valid_mvp_candidate(candidate)
        monkeypatch.setenv("MVP_OUTPUT_DIR", str(tmp_path / "server-output"))
        monkeypatch.setenv("MVP_ADAPTIVE_WIZARD_DB_PATH", str(tmp_path / "adaptive-runs.sqlite3"))
        server = build()

        async with create_connected_server_and_client_session(server) as client:
            requirements_response = await client.call_tool(
                "documentation_update_candidate_requirements",
                {
                    "run_id": run.id,
                    "expected_run_version": run.version,
                    "requirements": [
                        {
                            "title": "Run 소유 후보 계약을 관리한다",
                            "description": "요구사항부터 릴리스 기록까지 Run으로 추적한다.",
                            "priority": "P0",
                            "acceptance_criteria": [
                                "요구사항을 Run에 저장한다",
                                "candidate를 다시 검증한다",
                            ],
                        }
                    ],
                },
            )
            assert requirements_response.isError is False
            requirements = json.loads(requirements_response.content[0].text or "{}")
            assert requirements["candidate_sync_required"] is True

            architecture_response = await client.call_tool(
                "documentation_update_candidate_architecture",
                {
                    "run_id": run.id,
                    "expected_run_version": requirements["run_version"],
                    "contract": {},
                },
            )
            assert architecture_response.isError is False
            architecture = json.loads(architecture_response.content[0].text or "{}")

            delivery_response = await client.call_tool(
                "documentation_update_candidate_delivery",
                {
                    "run_id": run.id,
                    "expected_run_version": architecture["run_version"],
                    "tasks": [
                        {
                            "id": "TASK-001",
                            "requirement_ids": ["FR-001"],
                            "title": "후보 lifecycle을 저장한다",
                            "file_scope": [
                                "src/mvp_mcp/domain/spec/candidate_lifecycle_usecase.py"
                            ],
                            "done_when": ["Run에서 lifecycle을 조회할 수 있다"],
                        }
                    ],
                    "tests": [
                        {
                            "id": "TEST-001",
                            "requirement_ids": ["FR-001"],
                            "scenario": "후보 lifecycle을 기록한 뒤 Run을 조회한다",
                            "expected_result": "요구사항과 전달 계약이 남아 있다",
                            "kind": "automated",
                        }
                    ],
                },
            )
            assert delivery_response.isError is False
            delivery = json.loads(delivery_response.content[0].text or "{}")

            test_response = await client.call_tool(
                "documentation_record_candidate_test_run",
                {
                    "run_id": run.id,
                    "expected_run_version": delivery["run_version"],
                    "runs": [
                        {
                            "test_id": "TEST-001",
                            "status": "PASS",
                            "evidence": "pytest tests/test_candidate_package.py",
                            "executor": "pytest",
                            "executed_at": "2026-09-13T00:00:00Z",
                            "evidence_path": "tests/test_candidate_package.py",
                        }
                    ],
                    "idempotency_key": "composed-candidate-test-0001",
                },
            )
            assert test_response.isError is False
            test_run = json.loads(test_response.content[0].text or "{}")

            release_response = await client.call_tool(
                "documentation_record_candidate_release",
                {
                    "run_id": run.id,
                    "expected_run_version": test_run["run_version"],
                    "record": {
                        "id": "REL-20260913-01",
                        "status": "RELEASED",
                        "commit": "abc1234",
                        "artifact": "dist/mvp-mcp.whl",
                        "checksum_sha256": "a" * 64,
                        "executor": "pytest",
                        "executed_at": "2026-09-13T00:00:00Z",
                        "evidence": "candidate lifecycle MCP E2E",
                    },
                    "idempotency_key": "composed-candidate-release-0001",
                },
            )
            assert release_response.isError is False

            status_response = await client.call_tool(
                "documentation_package_status", {"run_id": run.id}
            )
            assert status_response.isError is False
            stale = json.loads(status_response.content[0].text or "{}")
            assert stale["candidate_sync_required"] is True
            assert stale["candidate_lifecycle"]["releases"][0]["id"] == "REL-20260913-01"

            requirements_document = candidate / "docs" / "REQUIREMENTS.md"
            requirements_document.write_text(
                requirements_document.read_text(encoding="utf-8") + "\n\nRun lifecycle 반영\n",
                encoding="utf-8",
            )
            refreshed_response = await client.call_tool(
                "documentation_package_status", {"run_id": run.id}
            )
            refreshed = json.loads(refreshed_response.content[0].text or "{}")

            validate_response = await client.call_tool(
                "documentation_validate_package",
                {
                    "run_id": run.id,
                    "run_version": refreshed["run_version"],
                    "candidate_revision": refreshed["current_candidate_revision"],
                },
            )
            assert validate_response.isError is False
            validated = json.loads(validate_response.content[0].text or "{}")

            preview_response = await client.call_tool(
                "documentation_preview_package",
                {
                    "run_id": run.id,
                    "run_version": validated["run_version"],
                    "candidate_revision": validated["candidate_revision"],
                },
            )
            assert preview_response.isError is False
            preview = json.loads(preview_response.content[0].text or "{}")
            assert preview["status"] == AdaptiveRunStatus.PREVIEW_READY.value
            assert not (project / ".mvpmcp").exists()

    asyncio.run(scenario())
