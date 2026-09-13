"""Run 소유 후보 수명주기의 순수 구조화 계약.

후보 Markdown은 모델이 candidate workspace에 작성한다. 이 모델은 그 문서를 직접 읽거나
쓰지 않고, Run에 영속할 요구사항·설계·전달·실행/릴리스 기록과 적용 이력만 표현한다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model import (
    DeliveryTestCase,
    DesignContract,
    ImplementationTask,
    ReleaseRecord,
    Requirement,
    VerificationEvidence,
)


class CandidateLifecycle(BaseModel):
    """하나의 Adaptive Run이 소유하는 구조화 문서 수명주기 snapshot."""

    lifecycle_revision: int = Field(default=0, ge=0)
    requirements: list[Requirement] = Field(default_factory=list)
    design_contract: DesignContract | None = None
    tasks: list[ImplementationTask] = Field(default_factory=list)
    test_cases: list[DeliveryTestCase] = Field(default_factory=list)
    verification: list[VerificationEvidence] = Field(default_factory=list)
    releases: list[ReleaseRecord] = Field(default_factory=list)
    verification_request_hashes: dict[str, str] = Field(default_factory=dict)
    release_request_hashes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_references(self) -> CandidateLifecycle:
        _assert_unique([item.id for item in self.requirements], "요구사항 ID")
        _assert_unique([item.id for item in self.tasks], "TASK-ID")
        _assert_unique([item.id for item in self.test_cases], "TEST-ID")
        _assert_unique([item.id for item in self.releases], "REL-ID")
        _assert_request_hashes(self.verification_request_hashes, "테스트")
        _assert_request_hashes(self.release_request_hashes, "릴리스")

        requirement_ids = {item.id for item in self.requirements}
        task_refs = {reference for task in self.tasks for reference in task.requirement_ids}
        test_refs = {reference for test in self.test_cases for reference in test.requirement_ids}
        if (self.tasks or self.test_cases) and (
            not self.design_contract
            or not requirement_ids
            or not task_refs <= requirement_ids
            or not test_refs <= requirement_ids
            or requirement_ids - task_refs
            or requirement_ids - test_refs
        ):
            raise ValueError("전달 계약은 설계와 모든 요구사항의 TASK·TEST 연결이 필요합니다.")

        test_ids = {item.id for item in self.test_cases}
        if any(item.test_id not in test_ids for item in self.verification):
            raise ValueError("검증 기록은 현재 TEST 계약을 참조해야 합니다.")
        return self


class AppliedCandidateCycle(BaseModel):
    """새 candidate cycle을 시작하기 전 보존하는 이전 적용 snapshot."""

    model_config = ConfigDict(frozen=True)

    lifecycle_revision: int = Field(ge=0)
    candidate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    preview_id: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    applied_outputs: list[str] = Field(default_factory=list)
    applied_at: datetime


class CandidateLifecycleMutationResult(BaseModel):
    """후보 수명주기 변경 뒤 모델이 candidate 문서를 갱신할 수 있게 하는 결과."""

    run_id: str
    run_version: int = Field(ge=0)
    lifecycle_revision: int = Field(ge=0)
    status: str
    candidate_sync_required: bool
    invalidated_stages: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    test_ids: list[str] = Field(default_factory=list)
    recorded_count: int = Field(default=0, ge=0)
    release_id: str | None = None
    replayed: bool = False
    next_action: str


def _assert_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label}는 중복될 수 없습니다.")


def _assert_request_hashes(values: dict[str, str], label: str) -> None:
    if any(not key.strip() or len(value) != 64 for key, value in values.items()):
        raise ValueError(f"{label} idempotency key와 payload hash가 올바르지 않습니다.")
