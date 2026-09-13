"""2단계 client-native 질문 흐름의 순수 Run·질문·제출 모델.

질문 UI는 MCP 클라이언트가 소유하고 이 모듈은 질문 schema·정규화 답변·상태 전이만 정의한다.
HTTP·SQLite·MCP는 이 모듈에 들어오지 않는다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_lifecycle_model import AppliedCandidateCycle, CandidateLifecycle
from .documentation_model import DocumentProfile


class AdaptiveRunStatus(StrEnum):
    """현재 구현에서 허용하는 비대기형 Adaptive Run 단계."""

    INTAKE_OPEN = "INTAKE_OPEN"
    INTAKE_SUBMITTED = "INTAKE_SUBMITTED"
    DESIGN_OPEN = "DESIGN_OPEN"
    DESIGN_SUBMITTED = "DESIGN_SUBMITTED"
    DRAFT_READY = "DRAFT_READY"
    CANDIDATE_VALIDATED = "CANDIDATE_VALIDATED"
    PREVIEW_READY = "PREVIEW_READY"
    CONFLICTED = "CONFLICTED"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"


class WritePolicy(StrEnum):
    """1차 Wizard에서 확정해 이후에 바꿀 수 없는 파일 반영 정책."""

    GENERATE_ONLY = "generate_only"
    SAFE_AUTO_APPLY = "safe_auto_apply"
    MANUAL_APPLY = "manual_apply"


class WizardQuestionKind(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"


AnswerValue: TypeAlias = str | list[str]


class AdaptiveWizardQuestion(BaseModel):
    """클라이언트 native UI가 렌더링하는 한 문항의 안전한 선언형 정의."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    kind: WizardQuestionKind
    required: bool = True
    options: list[str] = Field(default_factory=list, max_length=20)
    visible_when: dict[str, list[str]] = Field(default_factory=dict, max_length=3)

    @model_validator(mode="before")
    @classmethod
    def _normalize_common_client_aliases(cls, value: object) -> object:
        """Normalize observed client aliases while persisting one canonical schema."""

        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for alias, canonical in (("title", "label"), ("type", "kind")):
            if canonical not in normalized and alias in normalized:
                normalized[canonical] = normalized[alias]
            normalized.pop(alias, None)
        kind = normalized.get("kind")
        if isinstance(kind, str):
            normalized["kind"] = {
                "single_select": WizardQuestionKind.SELECT.value,
                "single-select": WizardQuestionKind.SELECT.value,
                "multi_select": WizardQuestionKind.MULTISELECT.value,
                "multi-select": WizardQuestionKind.MULTISELECT.value,
            }.get(kind, kind)
        return normalized

    @model_validator(mode="after")
    def _validate_definition(self) -> AdaptiveWizardQuestion:
        options_required = {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}
        if self.kind in options_required and not self.options:
            raise ValueError("선택형 문항에는 하나 이상의 option이 필요합니다.")
        if self.kind not in options_required and self.options:
            raise ValueError("텍스트 문항에는 option을 넣을 수 없습니다.")
        if len(set(self.options)) != len(self.options) or any(
            not item.strip() for item in self.options
        ):
            raise ValueError("option은 비어 있지 않은 중복 없는 값이어야 합니다.")
        if any(
            not key or not values or any(not value for value in values)
            for key, values in self.visible_when.items()
        ):
            raise ValueError("visible_when은 대상 문항과 하나 이상의 선택값을 가져야 합니다.")
        return self


class AdaptiveWizardSubmission(BaseModel):
    """한 단계 native 답변의 검증·정규화된 불변 snapshot."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")
    answers: dict[str, AnswerValue]
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    submitted_at: datetime


class AdaptiveWizardRun(BaseModel):
    """중복 시작과 재시작 조회를 견디는 2단계 Wizard 상태."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^run-[A-Za-z0-9_-]{8,127}$")
    request_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")
    user_request: str = Field(min_length=1, max_length=8_000)
    project_root: str = Field(min_length=1, max_length=4_000)
    status: AdaptiveRunStatus = AdaptiveRunStatus.INTAKE_OPEN
    requested_write_policy: WritePolicy | None = None
    write_policy: WritePolicy | None = None
    version: int = Field(default=0, ge=0)
    intake_questions: list[AdaptiveWizardQuestion] = Field(min_length=1, max_length=32)
    intake_submission: AdaptiveWizardSubmission | None = None
    design_questions: list[AdaptiveWizardQuestion] = Field(default_factory=list, max_length=7)
    design_submission: AdaptiveWizardSubmission | None = None
    spec_id: str | None = None
    candidate_root: str | None = Field(default=None, max_length=4_000)
    candidate_lifecycle: CandidateLifecycle = Field(default_factory=CandidateLifecycle)
    candidate_sync_required: bool = False
    candidate_sync_base_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    candidate_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    candidate_profile: DocumentProfile | None = None
    preview_id: str | None = Field(default=None, max_length=256)
    preview_manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    preview_candidate_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    preview_conflicts: list[str] = Field(default_factory=list, max_length=64)
    applied_outputs: list[str] = Field(default_factory=list, max_length=64)
    applied_candidate_cycles: list[AppliedCandidateCycle] = Field(
        default_factory=list, max_length=64
    )
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _validate_state(self) -> AdaptiveWizardRun:
        _assert_unique_question_ids(self.intake_questions)
        _assert_unique_question_ids(self.design_questions)
        if (
            self.requested_write_policy is not None
            and self.write_policy is not None
            and self.requested_write_policy is not self.write_policy
        ):
            raise ValueError("최초 요청의 write_policy는 이후 제출값으로 변경할 수 없습니다.")
        if self.status is AdaptiveRunStatus.CANCELLED:
            return self
        if self.candidate_sync_required is False and self.candidate_sync_base_revision is not None:
            raise ValueError("candidate 동기화가 필요 없으면 기준 revision을 둘 수 없습니다.")
        if self.candidate_sync_required and self.status is not AdaptiveRunStatus.DRAFT_READY:
            raise ValueError("candidate 동기화 대기 상태는 DRAFT_READY에서만 허용됩니다.")
        if self.status is AdaptiveRunStatus.INTAKE_OPEN:
            if (
                self.intake_submission is not None
                or self.write_policy is not None
                or self.spec_id is not None
            ):
                raise ValueError("INTAKE_OPEN에는 제출본·write_policy·spec_id를 둘 수 없습니다.")
        else:
            if self.intake_submission is None or self.write_policy is None:
                raise ValueError(
                    "1차 제출 이후 상태에는 intake 제출본과 write_policy가 필요합니다."
                )
        if self.status is AdaptiveRunStatus.INTAKE_SUBMITTED:
            if (
                self.design_questions
                or self.design_submission is not None
                or self.spec_id is not None
            ):
                raise ValueError(
                    "INTAKE_SUBMITTED에는 아직 2차 질문·제출본·spec_id를 둘 수 없습니다."
                )
        if self.status is AdaptiveRunStatus.DESIGN_OPEN:
            if (
                not self.design_questions
                or self.design_submission is not None
                or self.spec_id is not None
            ):
                raise ValueError("DESIGN_OPEN에는 질문만 있고 제출본·spec_id는 없어야 합니다.")
        if self.status is AdaptiveRunStatus.DESIGN_SUBMITTED:
            if (
                not self.design_questions
                or self.design_submission is None
                or self.spec_id is not None
            ):
                raise ValueError("DESIGN_SUBMITTED에는 질문·제출본만 있고 spec_id는 없어야 합니다.")
        pre_candidate_statuses = {
            AdaptiveRunStatus.INTAKE_OPEN,
            AdaptiveRunStatus.INTAKE_SUBMITTED,
            AdaptiveRunStatus.DESIGN_OPEN,
            AdaptiveRunStatus.DESIGN_SUBMITTED,
        }
        if self.status in pre_candidate_statuses and (
            self.candidate_root is not None
            or self.candidate_revision is not None
            or self.candidate_profile is not None
            or any(
                value is not None
                for value in (
                    self.preview_id,
                    self.preview_manifest_sha256,
                    self.preview_candidate_revision,
                )
            )
            or self.preview_conflicts
            or self.applied_outputs
            or self.applied_candidate_cycles
            or self.candidate_lifecycle.lifecycle_revision
            or self.candidate_lifecycle.requirements
            or self.candidate_lifecycle.design_contract is not None
            or self.candidate_lifecycle.tasks
            or self.candidate_lifecycle.test_cases
            or self.candidate_lifecycle.verification
            or self.candidate_lifecycle.releases
            or self.candidate_lifecycle.verification_request_hashes
            or self.candidate_lifecycle.release_request_hashes
            or self.candidate_sync_required
            or self.candidate_sync_base_revision is not None
        ):
            raise ValueError("candidate·preview·apply 정보는 DRAFT_READY 이후에만 둘 수 있습니다.")
        package_statuses = {
            AdaptiveRunStatus.DRAFT_READY,
            AdaptiveRunStatus.CANDIDATE_VALIDATED,
            AdaptiveRunStatus.PREVIEW_READY,
            AdaptiveRunStatus.CONFLICTED,
            AdaptiveRunStatus.APPLIED,
        }
        if self.status in package_statuses:
            if not self.design_questions or self.design_submission is None or self.spec_id is None:
                raise ValueError("후보 package 단계에는 2차 질문·제출본·spec_id가 필요합니다.")
        if self.status is AdaptiveRunStatus.DRAFT_READY:
            if self.candidate_revision is not None or self.candidate_profile is not None:
                raise ValueError(
                    "DRAFT_READY에는 검증된 candidate revision·profile을 둘 수 없습니다."
                )
            if (
                any(
                    value is not None
                    for value in (
                        self.preview_id,
                        self.preview_manifest_sha256,
                        self.preview_candidate_revision,
                    )
                )
                or self.preview_conflicts
                or self.applied_outputs
            ):
                raise ValueError("DRAFT_READY에는 preview·apply 결과를 둘 수 없습니다.")
        if self.status is AdaptiveRunStatus.CANDIDATE_VALIDATED:
            self._assert_candidate_binding()
            self._assert_no_preview_or_apply()
        if self.status in {AdaptiveRunStatus.PREVIEW_READY, AdaptiveRunStatus.CONFLICTED}:
            self._assert_candidate_binding()
            self._assert_preview_binding()
            if self.status is AdaptiveRunStatus.PREVIEW_READY and self.preview_conflicts:
                raise ValueError("PREVIEW_READY에는 충돌 목록을 둘 수 없습니다.")
            if self.status is AdaptiveRunStatus.CONFLICTED and not self.preview_conflicts:
                raise ValueError("CONFLICTED에는 하나 이상의 충돌 파일이 필요합니다.")
            if self.applied_outputs:
                raise ValueError("preview 완료 상태에는 applied_outputs를 둘 수 없습니다.")
        if self.status is AdaptiveRunStatus.APPLIED:
            self._assert_candidate_binding()
            self._assert_preview_binding()
            if self.preview_conflicts:
                raise ValueError("APPLIED에는 충돌 파일을 둘 수 없습니다.")
        return self

    def _assert_candidate_binding(self) -> None:
        if (
            not self.candidate_root
            or self.candidate_revision is None
            or self.candidate_profile is None
        ):
            raise ValueError("검증 이후 상태에는 candidate root·revision·profile이 필요합니다.")

    def _assert_no_preview_or_apply(self) -> None:
        if (
            any(
                value is not None
                for value in (
                    self.preview_id,
                    self.preview_manifest_sha256,
                    self.preview_candidate_revision,
                )
            )
            or self.preview_conflicts
            or self.applied_outputs
        ):
            raise ValueError("candidate 검증 상태에는 preview·apply 결과를 둘 수 없습니다.")

    def _assert_preview_binding(self) -> None:
        if (
            self.preview_id is None
            or self.preview_manifest_sha256 is None
            or self.preview_candidate_revision is None
            or self.preview_candidate_revision != self.candidate_revision
        ):
            raise ValueError(
                "preview 상태에는 같은 candidate revision에 결속된 preview hash가 필요합니다."
            )


def make_submission(
    submission_id: str,
    questions: list[AdaptiveWizardQuestion],
    raw_answers: dict[str, object],
    submitted_at: datetime,
) -> AdaptiveWizardSubmission:
    """클라이언트 답변을 선언형 질문 규칙에 맞춰 정규화한다."""

    normalized = _normalize_answers(questions, raw_answers)
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return AdaptiveWizardSubmission(
        id=submission_id,
        answers=normalized,
        payload_sha256=hashlib.sha256(encoded).hexdigest(),
        submitted_at=submitted_at,
    )


def _normalize_answers(
    questions: list[AdaptiveWizardQuestion], raw_answers: dict[str, object]
) -> dict[str, AnswerValue]:
    by_id = {question.id: question for question in questions}
    unknown = set(raw_answers) - set(by_id)
    if unknown:
        raise ValueError(f"알 수 없는 설문 항목입니다: {', '.join(sorted(unknown))}")

    initially_normalized = {
        question.id: _normalize_value(question, raw_answers.get(question.id))
        for question in questions
    }
    normalized: dict[str, AnswerValue] = {}
    for question in questions:
        if not _is_visible(question, initially_normalized):
            continue
        value = initially_normalized[question.id]
        if question.required and _is_empty(value):
            raise ValueError(f"필수 항목이 비어 있습니다: {question.label}")
        if _is_empty(value):
            continue
        _validate_value(question, value)
        normalized[question.id] = value
    return normalized


def _normalize_value(question: AdaptiveWizardQuestion, value: object) -> AnswerValue:
    if question.kind is WizardQuestionKind.MULTISELECT:
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{question.label}은(는) 여러 선택값이어야 합니다.")
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{question.label}은(는) 문자열이어야 합니다.")
    return value.strip()


def _is_visible(question: AdaptiveWizardQuestion, answers: dict[str, AnswerValue]) -> bool:
    for source_id, expected_values in question.visible_when.items():
        source = answers.get(source_id, "")
        source_values = {source} if isinstance(source, str) else set(source)
        if not source_values.intersection(expected_values):
            return False
    return True


def _is_empty(value: AnswerValue) -> bool:
    return value == "" or value == []


def _validate_value(question: AdaptiveWizardQuestion, value: AnswerValue) -> None:
    if question.kind in {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}:
        values = {value} if isinstance(value, str) else set(value)
        unsupported = values - set(question.options)
        if unsupported:
            raise ValueError(
                f"{question.label}의 선택값이 올바르지 않습니다: {', '.join(sorted(unsupported))}"
            )


def _assert_unique_question_ids(questions: list[AdaptiveWizardQuestion]) -> None:
    ids = [question.id for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Wizard 문항 ID는 한 단계 안에서 중복될 수 없습니다.")
