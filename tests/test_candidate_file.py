"""후보 파일 저장의 실제 I/O·재시작·충돌·MCP 정책 회귀."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from pydantic import ValidationError

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardRun,
    WritePolicy,
)
from mvp_mcp.domain.spec.candidate_file_model import CandidateFileWriteRequest
from mvp_mcp.domain.spec.candidate_file_usecase import WriteCandidateFileUseCase
from mvp_mcp.domain.spec.candidate_lifecycle_usecase import UpdateCandidateRequirementsUseCase
from mvp_mcp.domain.spec.model import Priority, RequirementInput
from mvp_mcp.main import build
from tests.test_candidate_package import _FixedClock, _wire, _write_valid_mvp_candidate


def _system(tmp_path: Path, policy: WritePolicy = WritePolicy.GENERATE_ONLY) -> SimpleNamespace:
    run, runs, candidates, validate, preview, apply, status, project, root = _wire(tmp_path, policy)
    return SimpleNamespace(
        run=run,
        runs=runs,
        candidates=candidates,
        writer=WriteCandidateFileUseCase(runs, candidates, _FixedClock()),
        validate=validate,
        preview=preview,
        apply=apply,
        status=status,
        project=project,
        root=root,
    )


def _request(system: SimpleNamespace, **changes: object) -> CandidateFileWriteRequest:
    return CandidateFileWriteRequest.model_validate(
        {
            "run_id": system.run.id,
            "expected_run_version": system.runs.find_by_id(system.run.id).version,
            "relative_path": "README.md",
            "content": "# 후보\n",
            "expected_file_sha256": None,
            "idempotency_key": "file-request-0001",
            **changes,
        }
    )


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_create_update_and_late_replay_preserve_bytes_and_newer_edits(tmp_path: Path) -> None:
    s = _system(tmp_path)
    body = '# 문서\r\n$env:SECRET $(anything) `quotes` "한글"\n<script>mock()</script>\n'
    first_request = _request(s, content=body)
    first = s.writer(first_request)
    assert first.status == "CREATED"
    assert (s.root / "README.md").read_bytes() == body.encode("utf-8")
    metadata = s.status(s.run.id).candidate_files[0]
    assert metadata.sha256 == first.stored_sha256 == _hash(body)
    assert metadata.byte_count == len(body.encode("utf-8"))
    second = s.writer(
        _request(
            s,
            content="# 새 문서\n",
            expected_file_sha256=first.stored_sha256,
            idempotency_key="file-request-0002",
        )
    )
    assert second.status == "UPDATED"
    replay = s.writer(first_request)
    assert replay.status == "REPLAYED"
    assert replay.run_version == second.run_version
    assert replay.stored_sha256 == first.stored_sha256
    assert replay.current_file_sha256 == second.stored_sha256
    assert (s.root / "README.md").read_text(encoding="utf-8") == "# 새 문서\n"
    assert not any(path.name.startswith(".candidate") for path in s.root.iterdir())


@pytest.mark.parametrize(
    "changes",
    [
        {"content": "different"},
        {"relative_path": "AGENTS.md"},
        {"expected_file_sha256": "a" * 64},
        {"expected_run_version": 999},
    ],
)
def test_idempotency_key_is_bound_to_the_entire_original_request(
    tmp_path: Path, changes: dict
) -> None:
    s = _system(tmp_path)
    request = _request(s)
    saved = s.writer(request)
    result = s.writer(request.model_copy(update=changes))
    assert result.reason == "IDEMPOTENCY_KEY_REUSED"
    assert result.run_version == saved.run_version
    assert _hash((s.root / "README.md").read_bytes().decode("utf-8")) == saved.stored_sha256
    assert result.current_file_sha256 == (
        None if changes.get("relative_path") == "AGENTS.md" else saved.stored_sha256
    )


@pytest.mark.parametrize(
    "condition,reason",
    [
        ({"expected_run_version": 0}, "RUN_VERSION_CHANGED"),
        ({"expected_file_sha256": "a" * 64}, "FILE_CHANGED"),
        ({}, "FILE_CHANGED"),
    ],
)
def test_conflict_never_overwrites_user_content(
    tmp_path: Path, condition: dict, reason: str
) -> None:
    s = _system(tmp_path)
    (s.root / "README.md").write_bytes(b"user-edited\r\n")
    result = s.writer(_request(s, **condition))
    assert result.status == "CONFLICT" and result.reason == reason
    assert result.current_file_sha256 == _hash("user-edited\r\n")
    assert result.run_version == s.run.version
    assert (s.root / "README.md").read_bytes() == b"user-edited\r\n"


def test_unchanged_write_keeps_validation_and_preview_binding(tmp_path: Path, monkeypatch) -> None:
    s = _system(tmp_path)
    _write_valid_mvp_candidate(s.root)
    observed = s.status(s.run.id)
    verified = s.validate(s.run.id, observed.run_version, observed.current_candidate_revision)
    previewed = s.preview(s.run.id, verified.run_version, verified.candidate_revision)
    body = (s.root / "README.md").read_bytes().decode("utf-8")
    request = _request(s, content=body, expected_file_sha256=_hash(body))

    def forbid_replace(*args):
        pytest.fail("UNCHANGED 요청이 파일 교체를 시도했습니다.")

    monkeypatch.setattr(os, "replace", forbid_replace)
    result = s.writer(request)
    assert result.status == "UNCHANGED"
    current = s.status(s.run.id)
    assert current.status == "PREVIEW_READY"
    assert current.preview_id == previewed.preview.preview_id
    assert current.recorded_candidate_revision == verified.candidate_revision
    assert s.writer(request).status == "REPLAYED"


@pytest.mark.parametrize("policy", list(WritePolicy))
def test_modified_candidate_invalidates_old_binding_and_preserves_write_policies(
    tmp_path: Path,
    policy: WritePolicy,
) -> None:
    s = _system(tmp_path, policy)
    _write_valid_mvp_candidate(s.root)
    observed = s.status(s.run.id)
    verified = s.validate(s.run.id, observed.run_version, observed.current_candidate_revision)
    prior = s.preview(s.run.id, verified.run_version, verified.candidate_revision)
    old_body = (s.root / "README.md").read_bytes().decode("utf-8")
    changed = s.writer(
        _request(s, content=old_body + "\n보완\n", expected_file_sha256=_hash(old_body))
    )
    current = s.status(s.run.id)
    assert current.status == "DRAFT_READY"
    assert current.preview_id is None and current.recorded_candidate_revision is None
    if policy is WritePolicy.SAFE_AUTO_APPLY:
        assert len(current.applied_candidate_cycles) == 1
        assert (
            s.project / ".mvpmcp" / s.run.spec_id / "README.md"
        ).read_bytes() == old_body.encode("utf-8")
    with pytest.raises(PipelineError):
        s.preview(s.run.id, changed.run_version, prior.candidate_revision)
    if policy is WritePolicy.MANUAL_APPLY:
        with pytest.raises(PipelineError):
            s.apply(
                s.run.id,
                changed.run_version,
                prior.preview.preview_id,
                prior.preview.manifest_sha256,
                "tester",
                "explicit test approval",
            )
    verified = s.validate(s.run.id, current.run_version, current.current_candidate_revision)
    refreshed = s.preview(s.run.id, verified.run_version, verified.candidate_revision)
    assert refreshed.status == (
        "APPLIED" if policy is WritePolicy.SAFE_AUTO_APPLY else "PREVIEW_READY"
    )
    if policy is WritePolicy.GENERATE_ONLY:
        assert not (s.project / ".mvpmcp").exists()


@pytest.mark.parametrize(
    "relative",
    [
        "../README.md",
        "/README.md",
        "C:/README.md",
        r"C:\README.md",
        "//server/share/README.md",
        "README.md:stream",
        "docs/../README.md",
        "docs//REQUIREMENTS.md",
        "./README.md",
        "docs\\REQUIREMENTS.md",
        "src/main.py",
        ".manifest.json",
        ".git/config",
        "docs/sources/original.md",
    ],
)
def test_only_exact_existing_package_paths_are_writable(tmp_path: Path, relative: str) -> None:
    s = _system(tmp_path)
    with pytest.raises(PipelineError, match="상대 경로"):
        s.writer(_request(s, relative_path=relative))
    assert list(s.root.iterdir()) == []
    assert not s.runs.find_by_id(s.run.id).candidate_write_receipts


def test_missing_or_early_run_cannot_create_workspace(tmp_path: Path) -> None:
    s = _system(tmp_path)
    with pytest.raises(PipelineError, match="찾을 수"):
        s.writer(_request(s, run_id="run-missing-0001"))
    assert not (s.root.parent.parent / "run-missing-0001").exists()
    early = s.run.model_copy(
        update={
            "status": AdaptiveRunStatus.INTAKE_OPEN,
            "candidate_root": None,
            "spec_id": None,
            "write_policy": None,
            "intake_submission": None,
            "design_questions": [],
            "design_submission": None,
            "version": s.run.version + 1,
        }
    )
    s.runs.save(early, expected_version=s.run.version)
    with pytest.raises(PipelineError, match="상태"):
        s.writer(_request(s))
    assert list(s.root.iterdir()) == []


def test_byte_limit_is_utf8_bytes_not_character_count(tmp_path: Path) -> None:
    s = _system(tmp_path)
    with pytest.raises(ValidationError, match="1,000,000"):
        _request(s, content="가" * 333_334)
    with pytest.raises(ValidationError):
        _request(s, content="\ud800")
    result = s.writer(_request(s, content="a" * 1_000_000))
    assert result.byte_count == 1_000_000
    assert s.status(s.run.id).candidate_files[0].byte_count == 1_000_000


@pytest.mark.parametrize("failure_point", ["replace", "fsync"])
def test_write_failure_preserves_file_and_same_request_can_resume(
    tmp_path: Path, monkeypatch, failure_point: str
) -> None:
    s = _system(tmp_path)
    (s.root / "README.md").write_bytes(b"original")
    request = _request(s, expected_file_sha256=_hash("original"))
    with monkeypatch.context() as patch:

        def fail_replace(*args):
            raise PermissionError("injected replace failure")

        patch.setattr(os, failure_point, fail_replace)
        with pytest.raises(PipelineError, match="PermissionError"):
            s.writer(request)
    assert (s.root / "README.md").read_bytes() == b"original"
    current = s.status(s.run.id)
    assert current.pending_candidate_write == request.idempotency_key
    assert len(current.candidate_files) == 1
    assert not list(s.root.glob(".mvpmcp-write-*.tmp"))
    blocked = s.writer(_request(s, idempotency_key="another-request-0001"))
    assert blocked.reason == "PENDING_WRITE"
    with pytest.raises(PipelineError, match="복구"):
        s.validate(s.run.id, current.run_version, current.current_candidate_revision)
    with pytest.raises(PipelineError, match="복구"):
        UpdateCandidateRequirementsUseCase(s.runs, s.candidates, _FixedClock())(
            s.run.id,
            current.run_version,
            [
                RequirementInput(
                    title="blocked",
                    description="pending write must block lifecycle mutation",
                    priority=Priority.P0,
                    acceptance_criteria=["no mutation"],
                )
            ],
        )
    assert s.writer(request).status == "UPDATED"
    assert s.status(s.run.id).pending_candidate_write is None


_CRASH_SCRIPT = r"""
import json, os, sys
from pathlib import Path
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.data.system_clock import SystemClock
from mvp_mcp.domain.spec.candidate_file_model import CandidateFileWriteRequest
from mvp_mcp.domain.spec.candidate_file_usecase import WriteCandidateFileUseCase
base, phase = Path(sys.argv[1]), sys.argv[2]
request = CandidateFileWriteRequest.model_validate_json((base/'request.json').read_text('utf-8'))
original_replace = os.replace
def crash_replace(source, destination):
    if phase == 'after':
        original_replace(source, destination)
    os._exit(73)
os.replace = crash_replace
WriteCandidateFileUseCase(
    SqliteAdaptiveWizardRunRepository(base/'adaptive-runs.sqlite3'),
    CandidatePackageRepository(str(base/'server-output')), SystemClock()
)(request)
"""


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize("external_edit", [False, True])
def test_real_process_death_and_repository_recreation_recover_or_preserve_conflict(
    tmp_path: Path,
    phase: str,
    external_edit: bool,
) -> None:
    s = _system(tmp_path)
    request = _request(s)
    (tmp_path / "request.json").write_text(request.model_dump_json(), encoding="utf-8")
    child = subprocess.run(
        [sys.executable, "-c", _CRASH_SCRIPT, str(tmp_path), phase], capture_output=True, timeout=20
    )
    assert child.returncode == 73, child.stderr.decode(errors="replace")
    if external_edit:
        (s.root / "README.md").write_bytes(b"external-edit")
    restarted = WriteCandidateFileUseCase(
        SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3"),
        CandidatePackageRepository(str(tmp_path / "server-output")),
        _FixedClock(),
    )
    result = restarted(request)
    assert s.status(s.run.id).pending_candidate_write is None
    assert len(s.status(s.run.id).candidate_files) == 1
    if external_edit:
        assert result.reason == "FILE_CHANGED"
        assert (s.root / "README.md").read_bytes() == b"external-edit"
        assert restarted(request).status == "CONFLICT"
        fresh = _request(
            s, expected_file_sha256=_hash("external-edit"), idempotency_key="after-conflict-0001"
        )
        assert restarted(fresh).status == "UPDATED"
    else:
        assert result.status == "CREATED"
        assert (s.root / "README.md").read_bytes() == request.content.encode("utf-8")
        assert restarted(request).status == "REPLAYED"
    payload = s.runs.find_by_id(s.run.id).model_dump_json()
    assert request.content not in payload


def test_concurrent_writers_do_not_lose_an_update(tmp_path: Path) -> None:
    s = _system(tmp_path)
    first = _request(s)
    second = _request(s, content="other", idempotency_key="file-request-0002")
    other_writer = WriteCandidateFileUseCase(
        SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3"),
        CandidatePackageRepository(str(tmp_path / "server-output")),
        _FixedClock(),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(s.writer, first)
        b = pool.submit(other_writer, second)
        results = [a.result(timeout=10), b.result(timeout=10)]
    assert sorted(result.status for result in results) == ["CONFLICT", "CREATED"]
    assert s.status(s.run.id).pending_candidate_write is None


def test_other_process_cannot_write_during_an_active_package_operation(tmp_path: Path) -> None:
    s = _system(tmp_path)
    request = _request(s)
    (tmp_path / "request.json").write_text(request.model_dump_json(), encoding="utf-8")
    normal_writer = _CRASH_SCRIPT.replace("os.replace = crash_replace", "")
    with s.candidates.exclusive(s.run.id):
        child = subprocess.run(
            [sys.executable, "-c", normal_writer, str(tmp_path), "unused"],
            capture_output=True,
            timeout=20,
        )
        assert child.returncode != 0
        assert b"candidate_write" in child.stderr
        assert not (s.root / "README.md").exists()
        assert s.runs.find_by_id(s.run.id).pending_candidate_write is None
    assert s.writer(request).status == "CREATED"


def test_atomic_replacement_does_not_modify_a_hardlinked_external_original(tmp_path: Path) -> None:
    s = _system(tmp_path)
    original = tmp_path / "protected-original.md"
    original.write_bytes(b"original")
    os.link(original, s.root / "README.md")
    result = s.writer(_request(s, expected_file_sha256=_hash("original")))
    assert result.status == "UPDATED"
    assert original.read_bytes() == b"original"
    assert (s.root / "README.md").read_bytes() == "# 후보\n".encode()


def test_new_file_refuses_to_exceed_existing_package_count_limit(tmp_path: Path) -> None:
    s = _system(tmp_path)
    for index in range(32):
        (s.root / f"external-{index}.md").write_bytes(b"external")
    with pytest.raises(PipelineError, match="32개"):
        s.writer(_request(s))
    assert not (s.root / "README.md").exists()
    assert s.runs.find_by_id(s.run.id).pending_candidate_write is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 파일 잠금 회귀")
def test_windows_locked_file_remains_intact_then_resumes(tmp_path: Path) -> None:
    s = _system(tmp_path)
    (s.root / "README.md").write_bytes(b"original")
    request = _request(s, expected_file_sha256=_hash("original"))
    with (s.root / "README.md").open("rb"):
        with pytest.raises(PipelineError):
            s.writer(request)
        assert (s.root / "README.md").read_bytes() == b"original"
    assert s.writer(request).status == "UPDATED"


@pytest.mark.parametrize("location", ["root", "parent", "file"])
def test_linked_paths_cannot_escape_candidate(tmp_path: Path, location: str) -> None:
    s = _system(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = s.root if location == "root" else s.root / "docs"
    if location == "file":
        protected = outside / "protected.md"
        protected.write_bytes(b"protected")
        try:
            (s.root / "README.md").symlink_to(protected)
        except OSError:
            pytest.skip("파일 symlink 생성 권한 없음; junction 두 경계는 별도 검증")
    else:
        if location == "root":
            s.root.rmdir()
        if sys.platform == "win32":
            import _winapi

            _winapi.CreateJunction(str(outside), str(linked))
        else:
            linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(PipelineError, match="symlink|reparse"):
        s.writer(
            _request(
                s, relative_path=("docs/REQUIREMENTS.md" if location == "parent" else "README.md")
            )
        )
    assert not (outside / "REQUIREMENTS.md").exists()
    if location == "file":
        assert protected.read_bytes() == b"protected"
    else:
        assert list(outside.iterdir()) == []


def test_old_run_payload_defaults_and_persistent_receipt_contain_no_body(tmp_path: Path) -> None:
    s = _system(tmp_path)
    old = s.run.model_dump(mode="json")
    old.pop("candidate_write_receipts")
    old.pop("pending_candidate_write")
    restored = AdaptiveWizardRun.model_validate(old)
    assert restored.candidate_write_receipts == {} and restored.pending_candidate_write is None
    request = _request(s, content="private unique body must stay out of sqlite payload")
    s.writer(request)
    receipt = s.runs.find_by_id(s.run.id).candidate_write_receipts[request.idempotency_key]
    assert request.content not in receipt.model_dump_json()
    assert receipt.state == "COMPLETED"


@pytest.mark.parametrize("policy", list(WritePolicy))
def test_composed_mcp_writes_all_files_and_completes_policy_without_shell(
    tmp_path: Path,
    monkeypatch,
    policy: WritePolicy,
) -> None:
    s = _system(tmp_path, policy)
    source = tmp_path / "model-authored"
    source.mkdir()
    _write_valid_mvp_candidate(source)
    monkeypatch.setenv("MVP_OUTPUT_DIR", str(tmp_path / "server-output"))
    monkeypatch.setenv("MVP_ADAPTIVE_WIZARD_DB_PATH", str(tmp_path / "adaptive-runs.sqlite3"))

    def forbid_shell(*args, **kwargs):
        pytest.fail("MCP 후보 저장 흐름이 셸/외부 프로세스를 호출했습니다.")

    monkeypatch.setattr(subprocess, "run", forbid_shell)

    async def scenario() -> None:
        async with create_connected_server_and_client_session(build()) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools.tools if t.name == "documentation_write_candidate_file")
            assert len(tools.tools) == 13
            assert tool.annotations.idempotentHint and not tool.annotations.readOnlyHint
            version = s.run.version
            for index, path in enumerate(sorted(source.rglob("*.md"))):
                response = await client.call_tool(
                    "documentation_write_candidate_file",
                    {
                        "run_id": s.run.id,
                        "expected_run_version": version,
                        "relative_path": path.relative_to(source).as_posix(),
                        "content": path.read_bytes().decode("utf-8"),
                        "expected_file_sha256": None,
                        "idempotency_key": f"mcp-file-request-{index:04d}",
                    },
                )
                result = json.loads(response.content[0].text)
                assert result["status"] == "CREATED"
                version = result["run_version"]
            response = await client.call_tool("documentation_package_status", {"run_id": s.run.id})
            status = json.loads(response.content[0].text)
            assert status["candidate_valid"] and len(status["candidate_files"]) == 7
            response = await client.call_tool(
                "documentation_validate_package",
                {
                    "run_id": s.run.id,
                    "run_version": version,
                    "candidate_revision": status["current_candidate_revision"],
                },
            )
            valid = json.loads(response.content[0].text)
            assert valid["valid"]
            response = await client.call_tool(
                "documentation_preview_package",
                {
                    "run_id": s.run.id,
                    "run_version": valid["run_version"],
                    "candidate_revision": valid["candidate_revision"],
                },
            )
            result = json.loads(response.content[0].text)
            if policy is WritePolicy.MANUAL_APPLY:
                response = await client.call_tool(
                    "documentation_apply_package",
                    {
                        "run_id": s.run.id,
                        "run_version": result["run_version"],
                        "preview_id": result["preview"]["preview_id"],
                        "manifest_sha256": result["preview"]["manifest_sha256"],
                        "approved_by": "test-user",
                        "approval_note": "explicit test approval",
                    },
                )
                result = json.loads(response.content[0].text)
            assert result["status"] == (
                "PREVIEW_READY" if policy is WritePolicy.GENERATE_ONLY else "APPLIED"
            )
            assert (s.project / ".mvpmcp").exists() == (policy is not WritePolicy.GENERATE_ONLY)

    asyncio.run(scenario())
