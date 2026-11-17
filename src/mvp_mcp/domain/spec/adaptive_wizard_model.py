"""2단계 client-native 질문 흐름의 순수 Run·질문·제출 모델.

질문 UI는 MCP 클라이언트가 소유하고 이 모듈은 질문 schema·정규화 답변·상태 전이만 정의한다.
HTTP·SQLite·MCP는 이 모듈에 들어오지 않는다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .candidate_file_model import CandidateFileWriteReceipt
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


AI_SUGGEST_OPTION = "ai_suggest"
"""“잘 모르겠어요 — AI가 제안” 선택지 값. 고르면 AI 추정으로 기록하고 2차에서 확인받는다."""

AiInferenceKind: TypeAlias = Literal["unknown", "default", "empty"]
"""AI 추정 출처: 모르겠어요 선택, AI 기본값 그대로 제출, 비워 두면 AI가 채움."""

MAX_DESIGN_QUESTIONS = 10


class AdaptiveWizardSelectionAnswer(BaseModel):
    """선택값과 선택형 문항의 기타 자유 입력을 함께 보존한다."""

    model_config = ConfigDict(frozen=True)

    selected: list[str] = Field(default_factory=list, max_length=20)
    other_text: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def _validate_contents(self) -> AdaptiveWizardSelectionAnswer:
        if len(self.selected) != len(set(self.selected)) or any(
            not value.strip() for value in self.selected
        ):
            raise ValueError("선택값은 비어 있지 않은 중복 없는 문자열이어야 합니다.")
        if self.other_text is not None and not self.other_text.strip():
            raise ValueError("기타 입력은 비어 있을 수 없습니다.")
        return self


AnswerValue: TypeAlias = str | list[str] | AdaptiveWizardSelectionAnswer


class AdaptiveWizardQuestion(BaseModel):
    """클라이언트 native UI가 렌더링하는 한 문항의 안전한 선언형 정의."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    kind: WizardQuestionKind
    required: bool = True
    options: list[str] = Field(default_factory=list, max_length=20)
    allow_other: bool = False
    other_label: str = Field(default="기타 (직접 입력)", min_length=1, max_length=160)
    max_selections: int | None = Field(default=None, ge=1, le=20)
    visible_when: dict[str, list[str]] = Field(default_factory=dict, max_length=3)
    option_labels: dict[str, str] = Field(default_factory=dict, max_length=20)
    """선택지 값 → 화면 표시명. 값은 저장·분기에, 표시명은 사람에게만 쓴다."""
    exclusive_options: list[str] = Field(default_factory=list, max_length=4)
    """다른 선택지와 함께 고를 수 없는 복수 선택 값(예: ai_suggest)."""
    default: str | list[str] | None = None
    """미리 골라 둔 값. 그대로 제출되면 AI 추정(default)으로 기록한다."""
    default_other_text: str | None = Field(default=None, min_length=1, max_length=500)
    """미리 채운 기타 직접 입력(예: 분야 '날씨'). 기타를 허용하는 선택형 문항에서만 쓴다."""
    from_request: bool = False
    """최초 요청에 명시돼 미리 채운 문항. 클라이언트는 묻지 않고, 답이 빠지면 서버가 채운다."""
    required_unless: list[str] = Field(default_factory=list, max_length=3)
    """필수 문항이 비어도, 여기 나열한 문항 중 하나에 답이 있으면 통과한다."""
    ai_fill_when_empty: bool = False
    """선택 문항을 비우면 AI가 채우고 2차에서 확인받는다."""

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
        if self.kind not in options_required and self.allow_other:
            raise ValueError("기타 자유 입력은 선택형 문항에서만 허용됩니다.")
        if self.kind is not WizardQuestionKind.MULTISELECT and self.max_selections is not None:
            raise ValueError("max_selections는 복수 선택 문항에서만 허용됩니다.")
        if len(set(self.options)) != len(self.options) or any(
            not item.strip() for item in self.options
        ):
            raise ValueError("option은 비어 있지 않은 중복 없는 값이어야 합니다.")
        option_limit = len(self.options) + int(self.allow_other)
        if self.max_selections is not None and self.max_selections > option_limit:
            raise ValueError("max_selections는 선택지와 기타 입력의 합을 넘을 수 없습니다.")
        if any(
            not key or not values or any(not value for value in values)
            for key, values in self.visible_when.items()
        ):
            raise ValueError("visible_when은 대상 문항과 하나 이상의 선택값을 가져야 합니다.")
        unknown_labels = set(self.option_labels) - set(self.options)
        if unknown_labels or any(
            not label.strip() or len(label) > 160 for label in self.option_labels.values()
        ):
            raise ValueError("option_labels는 존재하는 option에 비어 있지 않은 표시명만 둡니다.")
        if self.exclusive_options:
            if self.kind is not WizardQuestionKind.MULTISELECT:
                raise ValueError("exclusive_options는 복수 선택 문항에서만 허용됩니다.")
            if set(self.exclusive_options) - set(self.options):
                raise ValueError("exclusive_options는 option 중에서만 고를 수 있습니다.")
        if self.default is not None:
            self._validate_default(self.default)
        if self.default_other_text is not None:
            if not self.allow_other:
                raise ValueError("default_other_text는 기타 입력을 허용하는 문항에서만 씁니다.")
            if self.kind is WizardQuestionKind.SELECT and self.default is not None:
                raise ValueError("단일 선택은 default와 default_other_text를 함께 둘 수 없습니다.")
        if self.from_request and self.prefilled_answer() is None:
            raise ValueError("from_request 문항에는 미리 채운 값이 필요합니다.")
        if self.id in self.required_unless:
            raise ValueError("required_unless에는 자기 자신을 넣을 수 없습니다.")
        if self.ai_fill_when_empty and self.required:
            raise ValueError("ai_fill_when_empty는 선택 문항에서만 허용됩니다.")
        return self

    def _validate_default(self, default: str | list[str]) -> None:
        if self.kind is WizardQuestionKind.SELECT:
            if not isinstance(default, str) or default not in self.options:
                raise ValueError("단일 선택 default는 option 하나여야 합니다.")
            return
        if self.kind is WizardQuestionKind.MULTISELECT:
            if (
                not isinstance(default, list)
                or not default
                or len(set(default)) != len(default)
                or set(default) - set(self.options)
            ):
                raise ValueError("복수 선택 default는 중복 없는 option 목록이어야 합니다.")
            if self.max_selections is not None and len(default) > self.max_selections:
                raise ValueError("default가 max_selections를 넘습니다.")
            if len(default) > 1 and set(default) & set(self.exclusive_options):
                raise ValueError("default에 단독 선택값과 다른 값을 함께 둘 수 없습니다.")
            return
        if not isinstance(default, str):
            raise ValueError("텍스트 문항 default는 문자열이어야 합니다.")

    def prefilled_answer(self) -> AnswerValue | None:
        """미리 채운 값(default·default_other_text)을 제출 답 형식으로 돌려준다."""

        if self.default_other_text is None:
            return self.default
        selected = [self.default] if isinstance(self.default, str) else list(self.default or [])
        return AdaptiveWizardSelectionAnswer(selected=selected, other_text=self.default_other_text)

    def label_for(self, value: str) -> str:
        """선택지 값의 사람용 표시명. 표시명이 없으면 값 그대로."""
        return self.option_labels.get(value, value)


class AdaptiveWizardSubmission(BaseModel):
    """한 단계 native 답변의 검증·정규화된 불변 snapshot."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")
    answers: dict[str, AnswerValue]
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    submitted_at: datetime
    ai_inferred: dict[str, AiInferenceKind] = Field(default_factory=dict)
    """사용자가 직접 정하지 않고 AI 추정에 맡긴 문항과 그 출처."""


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
    design_questions: list[AdaptiveWizardQuestion] = Field(
        default_factory=list, max_length=MAX_DESIGN_QUESTIONS
    )
    design_submission: AdaptiveWizardSubmission | None = None
    spec_id: str | None = None
    candidate_root: str | None = Field(default=None, max_length=4_000)
    candidate_write_receipts: dict[str, CandidateFileWriteReceipt] = Field(default_factory=dict)
    pending_candidate_write: str | None = None
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
        pending = [
            key for key, value in self.candidate_write_receipts.items() if value.state == "PENDING"
        ]
        if pending != ([self.pending_candidate_write] if self.pending_candidate_write else []):
            raise ValueError("중단된 후보 저장은 하나의 영속 PENDING 기록과 결속되어야 합니다.")
        if self.pending_candidate_write and self.status is not AdaptiveRunStatus.DRAFT_READY:
            raise ValueError("후보 저장 복구 중에는 DRAFT_READY만 허용됩니다.")
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
            or self.candidate_write_receipts
            or self.pending_candidate_write is not None
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
        _serialize_answers(normalized),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return AdaptiveWizardSubmission(
        id=submission_id,
        answers=normalized,
        payload_sha256=hashlib.sha256(encoded).hexdigest(),
        submitted_at=submitted_at,
        ai_inferred=_ai_inferred(questions, normalized),
    )


def selected_values(value: AnswerValue | None) -> list[str]:
    """선택형 답변의 선택값 목록. 문자열 답은 값 하나로, 기타 입력은 제외한다."""
    if value is None:
        return []
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return list(value.selected)
    if isinstance(value, list):
        return list(value)
    return [value] if value else []


def other_text(value: AnswerValue | None) -> str:
    """선택형 답변의 기타 자유 입력."""
    if isinstance(value, AdaptiveWizardSelectionAnswer) and value.other_text:
        return value.other_text
    return ""


def _ai_inferred(
    questions: list[AdaptiveWizardQuestion], answers: dict[str, AnswerValue]
) -> dict[str, AiInferenceKind]:
    inferred: dict[str, AiInferenceKind] = {}
    for question in questions:
        value = answers.get(question.id)
        if value is None:
            if question.ai_fill_when_empty and _is_visible(question, answers):
                inferred[question.id] = "empty"
            continue
        if AI_SUGGEST_OPTION in selected_values(value):
            inferred[question.id] = "unknown"
            continue
        if question.default is None and question.default_other_text is None:
            continue
        default = question.default
        expected = [default] if isinstance(default, str) else list(default or [])
        if sorted(selected_values(value)) == sorted(expected) and (
            other_text(value) == (question.default_other_text or "")
        ):
            inferred[question.id] = "default"
    return inferred


def _serialize_answers(answers: dict[str, AnswerValue]) -> dict[str, object]:
    return {
        question_id: (
            value.model_dump(mode="json")
            if isinstance(value, AdaptiveWizardSelectionAnswer)
            else value
        )
        for question_id, value in answers.items()
    }


def _normalize_answers(
    questions: list[AdaptiveWizardQuestion], raw_answers: dict[str, object]
) -> dict[str, AnswerValue]:
    by_id = {question.id: question for question in questions}
    unknown = set(raw_answers) - set(by_id)
    if unknown:
        raise ValueError(f"알 수 없는 설문 항목입니다: {', '.join(sorted(unknown))}")

    initially_normalized = {
        question.id: _normalize_value(question, _raw_or_prefilled(question, raw_answers))
        for question in questions
    }
    normalized: dict[str, AnswerValue] = {}
    for question in questions:
        # 선행 문항이 보일 때만 후속 문항이 보이도록, 이미 채택된 답으로 판단한다(연쇄 조건).
        if not _is_visible(question, normalized):
            continue
        value = initially_normalized[question.id]
        if question.required and _is_empty(value):
            satisfied_by = [
                other_id
                for other_id in question.required_unless
                if other_id in initially_normalized
                and not _is_empty(initially_normalized[other_id])
            ]
            if not satisfied_by:
                raise ValueError(f"필수 항목이 비어 있습니다: {question.label}")
        if _is_empty(value):
            continue
        _validate_value(question, value)
        normalized[question.id] = value
    return normalized


def _raw_or_prefilled(question: AdaptiveWizardQuestion, raw_answers: dict[str, object]) -> object:
    """요청에서 확정돼 묻지 않은 문항(from_request)의 답이 빠지면 미리 채운 값을 쓴다."""

    value = raw_answers.get(question.id)
    if value is None and question.from_request:
        return question.prefilled_answer()
    return value


def _normalize_value(question: AdaptiveWizardQuestion, value: object) -> AnswerValue:
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return value
    if isinstance(value, dict):
        if question.kind not in {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}:
            raise ValueError(f"{question.label}은(는) 문자열이어야 합니다.")
        return AdaptiveWizardSelectionAnswer.model_validate(value)
    if question.kind is WizardQuestionKind.MULTISELECT:
        if value is None:
            return []
        if isinstance(value, str):
            # 클라이언트가 한 값·쉼표 목록을 문자열로 보내도 선택값 목록으로 읽는다.
            value = value.split(",")
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{question.label}은(는) 여러 선택값이어야 합니다.")
        items = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        return _split_other(question, items)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{question.label}은(는) 문자열이어야 합니다.")
    text = value.strip()
    if question.kind is WizardQuestionKind.SELECT and text and text not in question.options:
        return _split_other(question, [text]) if question.allow_other else text
    return text


def _split_other(question: AdaptiveWizardQuestion, items: list[str]) -> AnswerValue:
    """선택지에 없는 값은 기타 입력을 허용하는 문항에서만 ``other_text``로 옮긴다."""

    unknown = [item for item in items if item not in question.options]
    if not unknown or not question.allow_other:
        return items
    known = [item for item in items if item in question.options]
    return AdaptiveWizardSelectionAnswer(selected=known, other_text=", ".join(unknown))


def _is_visible(question: AdaptiveWizardQuestion, answers: dict[str, AnswerValue]) -> bool:
    for source_id, expected_values in question.visible_when.items():
        source = answers.get(source_id, "")
        if isinstance(source, AdaptiveWizardSelectionAnswer):
            source_values = set(source.selected)
        else:
            source_values = {source} if isinstance(source, str) else set(source)
        if not source_values.intersection(expected_values):
            return False
    return True


def _is_empty(value: AnswerValue) -> bool:
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return not value.selected and value.other_text is None
    return value == "" or value == []


def _validate_value(question: AdaptiveWizardQuestion, value: AnswerValue) -> None:
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        if question.kind not in {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}:
            raise ValueError(f"{question.label}은(는) 문자열이어야 합니다.")
        if not question.allow_other:
            raise ValueError(f"{question.label}은(는) 기타 자유 입력을 허용하지 않습니다.")
        selected = set(value.selected)
        unsupported = selected - set(question.options)
        if unsupported:
            raise ValueError(
                f"{question.label}의 선택값이 올바르지 않습니다: {', '.join(sorted(unsupported))}"
            )
        if question.kind is WizardQuestionKind.SELECT and len(value.selected) > 1:
            raise ValueError(f"{question.label}은(는) 하나만 선택할 수 있습니다.")
        selection_count = len(value.selected) + int(value.other_text is not None)
        max_selections = (
            1
            if question.kind is WizardQuestionKind.SELECT
            else question.max_selections or len(question.options) + int(question.allow_other)
        )
        if selection_count > max_selections:
            raise ValueError(f"{question.label}의 최대 선택 수를 초과했습니다.")
        _validate_exclusive(question, value.selected, selection_count)
        return
    if question.kind in {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}:
        values = {value} if isinstance(value, str) else set(value)
        unsupported = values - set(question.options)
        if unsupported:
            raise ValueError(
                f"{question.label}의 선택값이 올바르지 않습니다: {', '.join(sorted(unsupported))}"
            )
        if question.kind is WizardQuestionKind.MULTISELECT and isinstance(value, list):
            if question.max_selections is not None and len(value) > question.max_selections:
                raise ValueError(f"{question.label}의 최대 선택 수를 초과했습니다.")
            _validate_exclusive(question, value, len(value))


def _validate_exclusive(
    question: AdaptiveWizardQuestion, selected: list[str], selection_count: int
) -> None:
    if selection_count > 1 and set(selected) & set(question.exclusive_options):
        names = ", ".join(question.label_for(item) for item in question.exclusive_options)
        raise ValueError(f"{question.label}에서 '{names}'은(는) 다른 선택과 함께 고를 수 없습니다.")


def _assert_unique_question_ids(questions: list[AdaptiveWizardQuestion]) -> None:
    ids = [question.id for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Wizard 문항 ID는 한 단계 안에서 중복될 수 없습니다.")
