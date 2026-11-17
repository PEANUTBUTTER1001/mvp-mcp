"""구현 단계 Tool: 다음 작업·작업 명세·증거 기록·추적성·루트 AGENTS.md 연결 회귀 테스트."""

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
from mvp_mcp.data.spec.project_root_text_file import ProjectRootTextFileImpl
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
from mvp_mcp.domain.spec.candidate_lifecycle_model import CandidateLifecycle
from mvp_mcp.domain.spec.documentation_model import DocumentProfile
from mvp_mcp.domain.spec.implementation_usecase import (
    GetImplementationTaskContextUseCase,
    GetImplementationTraceUseCase,
    GetNextImplementationTaskUseCase,
    RecordImplementationEvidenceUseCase,
)
from mvp_mcp.domain.spec.model import (
    DeliveryTestCase,
    DesignContract,
    ImplementationTask,
    Priority,
    Requirement,
    VerificationEvidence,
    VerificationStatus,
)
from mvp_mcp.domain.spec.root_agents_link import (
    BLOCK_BEGIN,
    LinkRootAgentsUseCase,
    merged_content,
)
from mvp_mcp.presentation.resources.implementation import register_implementation_resources
from mvp_mcp.presentation.tools.implementation_next_task import (
    register_implementation_next_task_tool,
)
from mvp_mcp.presentation.tools.implementation_record_evidence import (
    register_implementation_record_evidence_tool,
)

NOW = datetime(2026, 11, 16, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return NOW


def _requirement(number: int, title: str) -> Requirement:
    return Requirement(
        id=f"FR-{number:03d}",
        title=title,
        description=title,
        priority=Priority.P0,
        acceptance_criteria=[f"{title} 기준 1", f"{title} 기준 2"],
    )


def _lifecycle() -> CandidateLifecycle:
    return CandidateLifecycle(
        lifecycle_revision=3,
        design_contract=DesignContract(),
        requirements=[_requirement(2, "가용 시간 등록"), _requirement(3, "30분 예약")],
        tasks=[
            ImplementationTask(
                id="TASK-002",
                requirement_ids=["FR-002"],
                title="가용 시간 등록",
                file_scope=["src/availability.py"],
                done_when=["트레이너가 주간 시간을 저장한다"],
            ),
            ImplementationTask(
                id="TASK-003",
                requirement_ids=["FR-003"],
                title="30분 예약",
                file_scope=["src/booking/slots.py", "tests/test_booking.py"],
                done_when=["중복 예약이 막힌다"],
                depends_on=["TASK-002"],
            ),
        ],
        test_cases=[
            DeliveryTestCase(
                id="TEST-003",
                requirement_ids=["FR-002"],
                scenario="가용 시간 저장",
                expected_result="저장된다",
                kind="automated",
            ),
            DeliveryTestCase(
                id="TEST-005",
                requirement_ids=["FR-003"],
                scenario="빈 슬롯 예약",
                expected_result="예약된다",
                kind="automated",
            ),
            DeliveryTestCase(
                id="TEST-007",
                requirement_ids=["FR-003"],
                scenario="같은 슬롯 중복 예약",
                expected_result="409 SLOT_TAKEN",
                kind="automated",
                case_type="failure",
            ),
        ],
    )


def _wire(tmp_path: Path, status: AdaptiveRunStatus = AdaptiveRunStatus.APPLIED) -> tuple:
    clock = _Clock()
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "runs.sqlite3")
    candidates = CandidatePackageRepository(str(tmp_path / "out"))
    project = tmp_path / "project"
    project.mkdir()
    run_id = "run-implementation-0001"
    root = candidates.ensure_workspace(run_id)
    questions = [
        AdaptiveWizardQuestion(id=f"q_{index}", label=f"질문 {index}", kind=WizardQuestionKind.TEXT)
        for index in range(3)
    ]
    answers = {item.id: "답" for item in questions}
    applied = status is AdaptiveRunStatus.APPLIED
    run = AdaptiveWizardRun(
        id=run_id,
        request_key="implementation-request-01",
        user_request="PT 예약",
        project_root=str(project),
        status=status,
        write_policy=WritePolicy.SAFE_AUTO_APPLY,
        version=9,
        intake_questions=questions,
        intake_submission=make_submission("sub-impl-intake-01", questions, answers, NOW),
        design_questions=questions,
        design_submission=make_submission("sub-impl-design-01", questions, answers, NOW),
        spec_id=f"adaptive-{run_id}",
        candidate_root=root,
        candidate_lifecycle=_lifecycle(),
        candidate_revision="a" * 64 if applied else None,
        candidate_profile=DocumentProfile.MVP_6 if applied else None,
        preview_id="preview-impl-0001" if applied else None,
        preview_manifest_sha256="b" * 64 if applied else None,
        preview_candidate_revision="a" * 64 if applied else None,
        applied_outputs=["docs/REQUIREMENTS.md"] if applied else [],
        created_at=NOW,
        updated_at=NOW,
    )
    runs.create_or_get(run)
    return (
        run,
        runs,
        GetNextImplementationTaskUseCase(runs),
        GetImplementationTaskContextUseCase(runs),
        GetImplementationTraceUseCase(runs),
        RecordImplementationEvidenceUseCase(runs, candidates, clock),
        LinkRootAgentsUseCase(runs, ProjectRootTextFileImpl()),
        project,
    )


def _evidence(
    test_id: str, status: VerificationStatus, note: str = "pytest"
) -> VerificationEvidence:
    return VerificationEvidence(
        test_id=test_id,
        status=status,
        evidence=f"uv run pytest -k {test_id} → {note}",
        executor="claude-code",
        executed_at=NOW,
        evidence_path="tests/test_booking.py",
    )


def test_next_task_follows_dependencies_and_finishes(tmp_path: Path) -> None:
    run, runs, next_task, _context, trace, record, _link, _project = _wire(tmp_path)

    first = next_task(run.id)
    assert first.status == "READY" and first.task is not None
    assert first.task.task_id == "TASK-002"
    assert first.remaining_task_ids == ["TASK-002", "TASK-003"]

    record(run.id, _evidence("TEST-003", VerificationStatus.PASS), "impl-key-0001")
    second = next_task(run.id)
    assert second.task is not None and second.task.task_id == "TASK-003"
    assert [test.id for test in second.task.tests] == ["TEST-005", "TEST-007"]

    record(run.id, _evidence("TEST-005", VerificationStatus.PASS), "impl-key-0002")
    failed = record(
        run.id, _evidence("TEST-007", VerificationStatus.FAIL, "중복 허용"), "impl-key-3"
    )
    assert failed.task_done == {"TASK-003": False}
    assert next_task(run.id).task.task_id == "TASK-003"  # type: ignore[union-attr]
    report = trace(run.id)
    assert report.counts["FAIL"] == 1 and report.rows[1].status == "FAIL"

    fixed = record(run.id, _evidence("TEST-007", VerificationStatus.PASS), "impl-key-0004")
    assert fixed.task_done == {"TASK-003": True}
    done = next_task(run.id)
    assert done.status == "ALL_DONE"
    assert trace(run.id).counts == {"PASS": 3, "FAIL": 0, "NOT_RUN": 0, "BLOCKED": 0, "TOTAL": 3}

    saved = runs.find_by_id(run.id)
    assert saved.status is AdaptiveRunStatus.APPLIED
    assert saved.candidate_sync_required is False
    assert saved.candidate_lifecycle.lifecycle_revision == 3


def test_task_context_contains_only_its_spec_and_reports_size(tmp_path: Path) -> None:
    run, _runs, _next, context, _trace, _record, _link, _project = _wire(tmp_path)
    result = context(run.id, "TASK-003")

    assert [item.id for item in result.requirements] == ["FR-003"]
    assert result.file_scope == ["src/booking/slots.py", "tests/test_booking.py"]
    assert result.state == "WAITING"
    assert 0 < result.bytes < result.total_spec_bytes
    with pytest.raises(PipelineError, match="TASK를 찾을 수 없습니다"):
        context(run.id, "TASK-999")


def test_evidence_requires_proof_known_test_and_stable_idempotency(tmp_path: Path) -> None:
    run, _runs, _next, _context, _trace, record, _link, _project = _wire(tmp_path)

    with pytest.raises(ValueError):
        VerificationEvidence(test_id="TEST-005", status=VerificationStatus.PASS)
    with pytest.raises(PipelineError, match="TEST 계약에 없는"):
        record(run.id, _evidence("TEST-099", VerificationStatus.PASS), "impl-key-0010")

    first = record(run.id, _evidence("TEST-005", VerificationStatus.PASS), "impl-key-0011")
    again = record(run.id, _evidence("TEST-005", VerificationStatus.PASS), "impl-key-0011")
    assert again.replayed and again.run_version == first.run_version
    with pytest.raises(PipelineError, match="idempotency_key"):
        record(run.id, _evidence("TEST-005", VerificationStatus.FAIL), "impl-key-0011")


def test_implementation_tools_require_applied_run(tmp_path: Path) -> None:
    run, _runs, next_task, _context, _trace, _record, link, _project = _wire(
        tmp_path, AdaptiveRunStatus.DRAFT_READY
    )
    with pytest.raises(PipelineError, match="NOT_READY"):
        next_task(run.id)
    with pytest.raises(PipelineError, match="NOT_READY"):
        link(run.id, "preview")


def test_root_agents_block_is_previewed_then_applied_with_hash_guard(tmp_path: Path) -> None:
    run, _runs, _next, _context, _trace, _record, link, project = _wire(tmp_path)
    agents = project / "AGENTS.md"
    agents.write_text("# AGENTS.md\n\n- 커밋 전 pytest 실행 (사용자 작성)\n", encoding="utf-8")

    preview = link(run.id, "preview")
    assert preview.action == "APPEND_BLOCK" and preview.status == "PREVIEW"
    assert agents.read_text(encoding="utf-8").count(BLOCK_BEGIN) == 0

    agents.write_text(agents.read_text(encoding="utf-8") + "- 추가 규칙\n", encoding="utf-8")
    stale = link(run.id, "apply", preview.current_sha256)
    assert stale.status == "CONFLICT"

    fresh = link(run.id, "preview")
    applied = link(run.id, "apply", fresh.current_sha256)
    text = agents.read_text(encoding="utf-8")
    assert applied.status == "APPLIED"
    assert "- 커밋 전 pytest 실행 (사용자 작성)" in text and "- 추가 규칙" in text
    assert text.count(BLOCK_BEGIN) == 1 and "implementation_next_task" in text
    assert link(run.id, "preview").status == "UNCHANGED"


def test_merged_content_creates_file_and_rejects_broken_markers() -> None:
    created, action = merged_content(None, "BLOCK")
    assert action == "CREATE_FILE" and created.startswith("# AGENTS.md")
    with pytest.raises(PipelineError, match="짝이 맞지"):
        merged_content(f"앞\n{BLOCK_BEGIN}\n끝 표식 없음\n", "BLOCK")


def test_mcp_next_task_evidence_and_trace_resource(tmp_path: Path) -> None:
    async def scenario() -> None:
        run, _runs, next_task, _context, trace, record, _link, _project = _wire(tmp_path)
        server = FastMCP("implementation_test")
        register_implementation_next_task_tool(server, next_task)
        register_implementation_record_evidence_tool(server, record)
        register_implementation_resources(server, trace)
        async with create_connected_server_and_client_session(server) as client:
            nxt = json.loads(
                (await client.call_tool("implementation_next_task", {"run_id": run.id}))
                .content[0]
                .text
                or "{}"
            )
            assert nxt["task"]["task_id"] == "TASK-002"
            recorded = await client.call_tool(
                "implementation_record_evidence",
                {
                    "run_id": run.id,
                    "evidence": {
                        "test_id": "TEST-003",
                        "status": "PASS",
                        "evidence": "uv run pytest → 1 passed",
                        "executor": "codex",
                        "executed_at": "2026-11-16T00:00:00Z",
                        "evidence_path": "tests/test_availability.py",
                    },
                    "idempotency_key": "mcp-impl-0001",
                },
            )
            assert json.loads(recorded.content[0].text or "{}")["task_done"] == {"TASK-002": True}
            resource = await client.read_resource(f"spec://runs/{run.id}/trace")
            report = json.loads(resource.contents[0].text or "{}")
            assert report["counts"]["PASS"] == 1
            missing = await client.read_resource("spec://runs/run-missing-000001/trace")
            assert "error" in json.loads(missing.contents[0].text or "{}")

    asyncio.run(scenario())
