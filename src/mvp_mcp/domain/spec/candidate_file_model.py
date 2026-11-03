"""후보 파일 저장·충돌·중단 복구의 순수 데이터 계약."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateFileMetadata(BaseModel):
    relative_path: str
    sha256: str
    byte_count: int


class CandidateFileWriteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(pattern=r"^run-[A-Za-z0-9_-]{8,127}$")
    expected_run_version: int = Field(ge=0)
    relative_path: str = Field(min_length=1, max_length=256)
    content: str = Field(max_length=1_000_000)
    expected_file_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")

    @model_validator(mode="after")
    def _validate_utf8(self) -> CandidateFileWriteRequest:
        try:
            encoded = self.content.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("본문은 유효한 UTF-8 텍스트여야 합니다.") from exc
        if len(encoded) > 1_000_000:
            raise ValueError("후보 파일은 UTF-8 기준 1,000,000바이트 이하여야 합니다.")
        return self


class CandidateFileWriteReceipt(BaseModel):
    """본문 없이 SQLite Run snapshot에 보존하는 write-ahead 처리 기록."""

    payload_sha256: str
    relative_path: str
    previous_sha256: str | None
    content_sha256: str
    byte_count: int
    state: Literal["PENDING", "COMPLETED", "CONFLICTED"] = "PENDING"
    operation: Literal["CREATED", "UPDATED", "UNCHANGED"]


class CandidateFileWriteResult(BaseModel):
    run_id: str
    run_version: int
    relative_path: str
    status: Literal["CREATED", "UPDATED", "UNCHANGED", "REPLAYED", "CONFLICT"]
    idempotency_key: str
    stored_sha256: str | None = None
    byte_count: int | None = None
    current_file_sha256: str | None = None
    current_candidate_revision: str
    pending_idempotency_key: str | None = None
    reason: str | None = None
    next_action: str
