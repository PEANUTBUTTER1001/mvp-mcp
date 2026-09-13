"""Run 전용 후보 문서 package의 순수 계약.

후보 본문은 Skill/모델이 작성한다. 이 모듈은 그 본문을 읽는 I/O나 MCP 전송을 알지 않고,
경로별 텍스트·revision·검증/preview 결과만 표현한다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .candidate_lifecycle_model import AppliedCandidateCycle, CandidateLifecycle
from .documentation_model import (
    DocumentationApplyResult,
    DocumentationPreview,
    DocumentProfile,
    RenderedDocumentationPackage,
)


class CandidatePackageSource(BaseModel):
    """서버가 발급한 candidate root에서 읽은 UTF-8 상대 경로별 본문."""

    candidate_root: str = Field(min_length=1, max_length=4_000)
    files: dict[str, str] = Field(default_factory=dict, max_length=32)


class CandidatePackageValidationResult(BaseModel):
    """결정적으로 다시 계산 가능한 후보 구조·내용 검증 결과."""

    run_id: str
    run_version: int = Field(ge=0)
    candidate_root: str
    candidate_revision: str
    profile: DocumentProfile | None = None
    file_count: int = Field(ge=0)
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str


class CandidatePackageInspection(BaseModel):
    """UseCase 내부에서만 사용하는 검증 결과와 exporter 입력의 묶음."""

    validation: CandidatePackageValidationResult
    package: RenderedDocumentationPackage | None = None


class CandidatePackagePreviewResult(BaseModel):
    """candidate revision에 결속된 preview와 조건부 자동 반영 결과."""

    run_id: str
    run_version: int = Field(ge=0)
    candidate_revision: str
    preview: DocumentationPreview
    status: str
    auto_apply: DocumentationApplyResult | None = None
    next_action: str


class CandidatePackageApplyResult(BaseModel):
    """수동 반영 또는 정책 거부의 구조화 결과."""

    run_id: str
    run_version: int = Field(ge=0)
    candidate_revision: str | None = None
    status: str
    preview_id: str | None = None
    manifest_sha256: str | None = None
    applied_outputs: list[str] = Field(default_factory=list)
    skipped_outputs: list[str] = Field(default_factory=list)
    stale_outputs: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    next_action: str


class ManagedPackageStatus(BaseModel):
    """실제 ``.mvpmcp/`` manifest의 읽기 전용 snapshot."""

    target_root: str
    manifest_present: bool
    spec_id: str | None = None
    profile: str | None = None
    managed_files: list[str] = Field(default_factory=list)
    stale_outputs: list[str] = Field(default_factory=list)


class CandidatePackageStatusResult(BaseModel):
    """Run, on-disk candidate, 실제 관리 package를 함께 보는 복구 snapshot."""

    run_id: str
    run_version: int = Field(ge=0)
    status: str
    write_policy: str
    candidate_root: str
    candidate_lifecycle: CandidateLifecycle
    candidate_sync_required: bool
    candidate_sync_base_revision: str | None = None
    current_candidate_revision: str
    recorded_candidate_revision: str | None = None
    candidate_profile: DocumentProfile | None = None
    candidate_valid: bool
    candidate_issues: list[str] = Field(default_factory=list)
    candidate_warnings: list[str] = Field(default_factory=list)
    preview_id: str | None = None
    preview_manifest_sha256: str | None = None
    preview_conflicts: list[str] = Field(default_factory=list)
    applied_outputs: list[str] = Field(default_factory=list)
    applied_candidate_cycles: list[AppliedCandidateCycle] = Field(default_factory=list)
    managed_package: ManagedPackageStatus
    resume_hint: str


def package_from_inspection(inspection: CandidatePackageInspection) -> RenderedDocumentationPackage:
    """유효한 inspection만 exporter 입력으로 승격한다."""

    package = inspection.package
    if package is None:
        raise ValueError("유효하지 않은 후보 package는 preview할 수 없습니다.")
    return package
