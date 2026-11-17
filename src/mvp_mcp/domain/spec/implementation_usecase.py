"""반영된 Run의 구조화 명세를 구현 AI가 작업 단위로 꺼내 쓰고 결과를 기록하는 UseCase.

문서 후보를 다시 만들지 않는다. APPLIED Run의 요구사항·TASK·TEST 계약만 읽고, 실제 실행
증거는 append-only로 쌓는다. 증거 기록은 문서 재동기화를 요구하지 않는다.
"""

from __future__ import annotations

import hashlib
import json

from mvp_mcp.core.exceptions import PipelineError

from .adaptive_wizard_model import AdaptiveRunStatus, AdaptiveWizardRun
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .implementation_model import (
    EvidenceRecordResult,
    NextTaskResult,
    RequirementView,
    TaskContext,
    TestState,
    TestStatusView,
    TraceReport,
    TraceRow,
)
from .model import ImplementationTask, VerificationEvidence
from .ports import CandidatePackageWorkspace, Clock

_IMPLEMENTATION_KEY_PREFIX = "impl:"


class _RunSpec:
    """APPLIED Run의 lifecycle을 작업·테스트 관계로 해석한 읽기 전용 뷰."""

    def __init__(self, run: AdaptiveWizardRun) -> None:
        self.run = run
        lifecycle = run.candidate_lifecycle
        self.tasks = list(lifecycle.tasks)
        self.task_by_id = {task.id: task for task in self.tasks}
        self.requirements = {item.id: item for item in lifecycle.requirements}
        self.tests = list(lifecycle.test_cases)
        latest: dict[str, VerificationEvidence] = {}
        for evidence in lifecycle.verification:
            latest[evidence.test_id] = evidence
        self.latest = latest

    def tests_for(self, task: ImplementationTask) -> list[TestStatusView]:
        wanted = set(task.requirement_ids)
        return [
            self._test_view(test.id)
            for test in self.tests
            if wanted.intersection(test.requirement_ids)
        ]

    def _test_view(self, test_id: str) -> TestStatusView:
        test = next(item for item in self.tests if item.id == test_id)
        evidence = self.latest.get(test_id)
        return TestStatusView(
            id=test.id,
            scenario=test.scenario,
            expected_result=test.expected_result,
            kind=test.kind,
            latest_status=_state(evidence),
            latest_evidence=evidence.evidence if evidence else "",
            latest_executor=evidence.executor if evidence else "",
        )

    def is_done(self, task: ImplementationTask) -> bool:
        tests = self.tests_for(task)
        return bool(tests) and all(item.latest_status == "PASS" for item in tests)

    def state(self, task: ImplementationTask) -> str:
        if not self.tests_for(task):
            return "NO_TESTS"
        if self.is_done(task):
            return "DONE"
        deps_done = all(
            dep in self.task_by_id and self.is_done(self.task_by_id[dep]) for dep in task.depends_on
        )
        return "READY" if deps_done else "WAITING"

    def context(self, task: ImplementationTask) -> TaskContext:
        context = TaskContext(
            run_id=self.run.id,
            task_id=task.id,
            title=task.title,
            state=self.state(task),  # type: ignore[arg-type]
            depends_on=list(task.depends_on),
            file_scope=list(task.file_scope),
            done_when=list(task.done_when),
            requirements=[
                RequirementView(
                    id=req.id, title=req.title, acceptance_criteria=list(req.acceptance_criteria)
                )
                for req_id in task.requirement_ids
                if (req := self.requirements.get(req_id)) is not None
            ],
            tests=self.tests_for(task),
            next_instruction=(
                "file_scope 안에서 구현하고 연결 TEST를 실제로 실행한 뒤 "
                "implementation_record_evidence로 결과를 기록하세요. 실행하지 않은 TEST는 "
                "기록하지 말고 NOT_RUN으로 두세요."
            ),
        )
        body = context.model_dump_json(exclude={"bytes", "total_spec_bytes"})
        return context.model_copy(
            update={
                "bytes": len(body.encode("utf-8")),
                "total_spec_bytes": len(
                    self.run.candidate_lifecycle.model_dump_json().encode("utf-8")
                ),
            }
        )


class GetNextImplementationTaskUseCase:
    """선행 작업이 끝났고 아직 검증되지 않은 첫 TASK를 고른다."""

    def __init__(self, runs: AdaptiveWizardRunRepository) -> None:
        self._runs = runs

    def __call__(self, run_id: str) -> NextTaskResult:
        spec = _RunSpec(_require_applied(self._runs, run_id))
        warnings = [
            f"{task.id}: 연결된 TEST가 없어 완료를 확인할 수 없습니다."
            for task in spec.tasks
            if spec.state(task) == "NO_TESTS"
        ]
        warnings += [
            f"{task.id}: 알 수 없는 선행 작업 {dep}"
            for task in spec.tasks
            for dep in task.depends_on
            if dep not in spec.task_by_id
        ]
        remaining = [task.id for task in spec.tasks if spec.state(task) != "DONE"]
        ready = next((task for task in spec.tasks if spec.state(task) == "READY"), None)
        if ready is not None:
            return NextTaskResult(
                run_id=run_id,
                status="READY",
                task=spec.context(ready),
                remaining_task_ids=remaining,
                warnings=warnings,
                next_instruction=f"{ready.id}를 구현하세요. 명세는 task에 모두 들어 있습니다.",
            )
        if all(spec.state(task) == "DONE" for task in spec.tasks) and spec.tasks:
            return NextTaskResult(
                run_id=run_id,
                status="ALL_DONE",
                remaining_task_ids=[],
                warnings=warnings,
                next_instruction="모든 TASK의 연결 TEST가 PASS입니다. spec://runs/{run_id}/trace로 "
                "최종 상태를 확인하세요.",
            )
        return NextTaskResult(
            run_id=run_id,
            status="BLOCKED",
            remaining_task_ids=remaining,
            warnings=warnings
            or ["선행 작업 순환 또는 TEST 없는 작업 때문에 진행할 TASK가 없습니다."],
            next_instruction="warnings의 TASK·TEST 계약을 사용자와 확인하세요.",
        )


class GetImplementationTaskContextUseCase:
    """TASK 하나에 필요한 요구사항·수용 기준·TEST·파일 범위만 반환한다."""

    def __init__(self, runs: AdaptiveWizardRunRepository) -> None:
        self._runs = runs

    def __call__(self, run_id: str, task_id: str) -> TaskContext:
        spec = _RunSpec(_require_applied(self._runs, run_id))
        task = spec.task_by_id.get(task_id)
        if task is None:
            raise PipelineError(
                "implementation",
                f"TASK를 찾을 수 없습니다: {task_id}",
                "implementation_next_task가 반환한 task_id를 사용하세요.",
            )
        return spec.context(task)


class GetImplementationTraceUseCase:
    """요구사항 → TASK → TEST → 최신 상태 추적표."""

    def __init__(self, runs: AdaptiveWizardRunRepository) -> None:
        self._runs = runs

    def __call__(self, run_id: str) -> TraceReport:
        spec = _RunSpec(_require_applied(self._runs, run_id))
        rows = []
        for requirement in spec.run.candidate_lifecycle.requirements:
            tests = [
                spec._test_view(test.id)
                for test in spec.tests
                if requirement.id in test.requirement_ids
            ]
            rows.append(
                TraceRow(
                    requirement_id=requirement.id,
                    title=requirement.title,
                    task_ids=[
                        task.id for task in spec.tasks if requirement.id in task.requirement_ids
                    ],
                    tests=tests,
                    status=_aggregate([item.latest_status for item in tests]),
                )
            )
        states = [spec._test_view(test.id).latest_status for test in spec.tests]
        counts = {state: states.count(state) for state in ("PASS", "FAIL", "NOT_RUN", "BLOCKED")}
        counts["TOTAL"] = len(states)
        return TraceReport(run_id=run_id, rows=rows, counts=counts)


class RecordImplementationEvidenceUseCase:
    """구현 중 실제 실행한 TEST 결과를 APPLIED Run에 append-only로 기록한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        candidates: CandidatePackageWorkspace,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._clock = clock

    def __call__(
        self, run_id: str, evidence: VerificationEvidence, idempotency_key: str
    ) -> EvidenceRecordResult:
        key = idempotency_key.strip()
        if not key:
            raise PipelineError(
                "implementation", "idempotency_key가 비어 있습니다.", "호출별 고유 key를 주세요."
            )
        _require_applied(self._runs, run_id)
        with self._candidates.exclusive(run_id):
            run = _require_applied(self._runs, run_id)
            lifecycle = run.candidate_lifecycle
            if evidence.test_id not in {item.id for item in lifecycle.test_cases}:
                raise PipelineError(
                    "implementation",
                    f"Run의 TEST 계약에 없는 ID입니다: {evidence.test_id}",
                    "implementation_task_context의 tests에 있는 ID를 사용하세요.",
                )
            stamped = (
                evidence
                if evidence.executed_at is not None
                else evidence.model_copy(update={"executed_at": self._clock.now()})
            )
            payload = _hash(evidence)
            stored_key = _IMPLEMENTATION_KEY_PREFIX + key
            previous = lifecycle.verification_request_hashes.get(stored_key)
            if previous is not None:
                if previous != payload:
                    raise PipelineError(
                        "implementation",
                        "같은 idempotency_key에 다른 결과를 기록할 수 없습니다.",
                        "새 실행에는 새 idempotency_key를 사용하세요.",
                    )
                return _result(run, evidence, replayed=True)
            updated = run.model_copy(
                update={
                    "candidate_lifecycle": lifecycle.model_copy(
                        update={
                            "verification": [*lifecycle.verification, stamped],
                            "verification_request_hashes": {
                                **lifecycle.verification_request_hashes,
                                stored_key: payload,
                            },
                        }
                    ),
                    "version": run.version + 1,
                    "updated_at": self._clock.now(),
                }
            )
            saved = self._runs.save(updated, expected_version=run.version)
            return _result(saved, stamped, replayed=False)


def _result(
    run: AdaptiveWizardRun, evidence: VerificationEvidence, *, replayed: bool
) -> EvidenceRecordResult:
    spec = _RunSpec(run)
    test = next(item for item in spec.tests if item.id == evidence.test_id)
    tasks = [task for task in spec.tasks if set(task.requirement_ids) & set(test.requirement_ids)]
    done = {task.id: spec.is_done(task) for task in tasks}
    return EvidenceRecordResult(
        run_id=run.id,
        run_version=run.version,
        test_id=evidence.test_id,
        status=_state(evidence),
        replayed=replayed,
        task_ids=[task.id for task in tasks],
        task_done=done,
        next_instruction=(
            "연결 TASK가 모두 완료됐습니다. implementation_next_task로 다음 작업을 받으세요."
            if done and all(done.values())
            else "남은 연결 TEST를 실행해 기록하거나, 실패한 TEST를 고친 뒤 다시 기록하세요."
        ),
    )


def _require_applied(runs: AdaptiveWizardRunRepository, run_id: str) -> AdaptiveWizardRun:
    run = runs.find_by_id(run_id)
    if run is None:
        raise PipelineError(
            "implementation",
            "Wizard run을 찾을 수 없습니다.",
            "문서 패키지를 만든 run_id를 그대로 사용하세요.",
        )
    if run.status is not AdaptiveRunStatus.APPLIED:
        raise PipelineError(
            "implementation",
            f"NOT_READY: 문서 패키지가 아직 반영되지 않았습니다 ({run.status.value}).",
            "documentation_preview_package·apply로 문서를 반영한 뒤 구현 Tool을 사용하세요.",
        )
    if not run.candidate_lifecycle.tasks:
        raise PipelineError(
            "implementation",
            "NOT_READY: Run에 구조화된 TASK 계약이 없습니다.",
            "documentation_update_candidate_delivery로 TASK·TEST를 등록한 Run을 사용하세요.",
        )
    return run


def _state(evidence: VerificationEvidence | None) -> TestState:
    if evidence is None:
        return "NOT_RUN"
    return evidence.status.value


def _aggregate(states: list[TestState]) -> TestState:
    if "FAIL" in states:
        return "FAIL"
    if "BLOCKED" in states:
        return "BLOCKED"
    if states and all(state == "PASS" for state in states):
        return "PASS"
    return "NOT_RUN"


def _hash(evidence: VerificationEvidence) -> str:
    encoded = json.dumps(
        evidence.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
