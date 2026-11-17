"""구현 단계에서 AI 에이전트가 읽는 작업·명세·추적성 결과 모델."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TestState = Literal["PASS", "FAIL", "NOT_RUN", "BLOCKED"]


class TestStatusView(BaseModel):
    """TEST 계약과 가장 최근에 기록된 실행 결과."""

    id: str
    scenario: str
    expected_result: str
    kind: str
    latest_status: TestState = "NOT_RUN"
    latest_evidence: str = ""
    latest_executor: str = ""


class RequirementView(BaseModel):
    id: str
    title: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class TaskContext(BaseModel):
    """한 TASK를 구현하는 데 필요한 명세만 모은 결과."""

    run_id: str
    task_id: str
    title: str
    state: Literal["DONE", "READY", "WAITING", "NO_TESTS"]
    depends_on: list[str] = Field(default_factory=list)
    file_scope: list[str] = Field(default_factory=list)
    done_when: list[str] = Field(default_factory=list)
    requirements: list[RequirementView] = Field(default_factory=list)
    tests: list[TestStatusView] = Field(default_factory=list)
    bytes: int = Field(default=0, ge=0)
    total_spec_bytes: int = Field(default=0, ge=0)
    next_instruction: str = ""


class NextTaskResult(BaseModel):
    run_id: str
    status: Literal["READY", "ALL_DONE", "BLOCKED"]
    task: TaskContext | None = None
    remaining_task_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_instruction: str


class TraceRow(BaseModel):
    requirement_id: str
    title: str
    task_ids: list[str] = Field(default_factory=list)
    tests: list[TestStatusView] = Field(default_factory=list)
    status: TestState


class TraceReport(BaseModel):
    run_id: str
    rows: list[TraceRow] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    note: str = "PASS는 실행 명령·출력 근거가 기록된 경우에만 표시된다. 미실행은 NOT_RUN이다."


class EvidenceRecordResult(BaseModel):
    run_id: str
    run_version: int
    test_id: str
    status: TestState
    replayed: bool = False
    task_ids: list[str] = Field(default_factory=list)
    task_done: dict[str, bool] = Field(default_factory=dict)
    next_instruction: str
