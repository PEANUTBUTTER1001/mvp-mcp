"""MVP 명세 도메인 모델.

입력 경계에서 검증되는 요청 모델과, 서버가 소유하는 상태 엔티티(``SpecDraft``)를
정의한다. Pydantic 모델이라 프레임워크가 아니라 검증 라이브러리에만 의존한다.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .documentation_model import DocumentationIntake


class ProjectType(StrEnum):
    """지원 프로젝트 유형. 미지원 요청은 ``ETC`` 로 폴백한다."""

    MESSENGER = "messenger"
    SHOPPING_MALL = "shopping_mall"
    BLOG = "blog"
    MCP_SERVER = "mcp_server"
    ML_PROJECT = "ml_project"
    DATA_PIPELINE = "data_pipeline"
    ETC = "etc"

    @classmethod
    def coerce(cls, value: str | None) -> ProjectType:
        """문자열을 유형으로 변환한다. 비거나 미지원 값이면 ``ETC`` 로 폴백한다.

        LLM 이 임의의 유형 문자열(예: "mcp-server")을 넘기거나 값을 생략해도
        크래시 대신 ``ETC`` 로 흡수한다(기획: "미지원 유형은 전부 기타로").
        """
        if not value:
            return cls.ETC
        try:
            return cls(value.strip().lower())
        except ValueError:
            return cls.ETC


class Priority(StrEnum):
    """요구사항 구현 우선순위."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class RequirementKind(StrEnum):
    """가이드가 허용하는 실제 요구사항 ID 접두사."""

    BIZ = "BIZ"
    FR = "FR"
    NFR_PERF = "NFR-PERF"
    NFR_A11Y = "NFR-A11Y"
    DATA = "DATA"
    SEC = "SEC"


class VerificationStatus(StrEnum):
    """실제 증거에 근거한 검증 상태."""

    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class ReleaseStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    RELEASED = "RELEASED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class RequirementInput(BaseModel):
    """LLM이 의미를 정리해 등록하는 요구사항 입력."""

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Priority
    acceptance_criteria: list[str] = Field(min_length=1)
    kind: RequirementKind = RequirementKind.FR

    @field_validator("title", "description")
    @classmethod
    def _reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("요구사항 텍스트는 공백만으로 입력할 수 없습니다.")
        return value.strip()

    @field_validator("acceptance_criteria")
    @classmethod
    def _validate_criteria(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            raise ValueError("수용 기준을 하나 이상 입력하세요.")
        return cleaned


class Requirement(RequirementInput):
    """서버가 ID를 부여한 확정 요구사항."""

    id: str
    status: Literal["confirmed", "deferred"] = "confirmed"


class ScreenSpec(BaseModel):
    """화면과 상태를 포함한 UI 설계 계약."""

    name: str = Field(min_length=1)
    route: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    ui_elements: list[str] = Field(min_length=1)
    states: list[str] = Field(min_length=1)


class UserFlow(BaseModel):
    """정상·예외 흐름을 함께 기록하는 사용자 여정."""

    name: str = Field(min_length=1)
    steps: list[str] = Field(min_length=2)
    exception_paths: list[str] = Field(default_factory=list)


class DataEntity(BaseModel):
    """저장 데이터 또는 핵심 도메인 객체의 설계 계약."""

    name: str = Field(min_length=1)
    fields: list[str] = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    relations: list[str] = Field(default_factory=list)


class InterfaceContract(BaseModel):
    """API, MCP Tool, CLI 등 외부 인터페이스의 입력·출력 계약."""

    name: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    input_summary: str = Field(min_length=1)
    output_summary: str = Field(min_length=1)
    error_cases: list[str] = Field(min_length=1)


class BusinessRule(BaseModel):
    """도메인·보안·AI 처리 등 반드시 지켜야 하는 규칙."""

    title: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ErrorState(BaseModel):
    """사용자에게 보이는 실패 상태와 복구 경로."""

    trigger: str = Field(min_length=1)
    user_message: str = Field(min_length=1)
    recovery: str = Field(min_length=1)


class OpenDecision(BaseModel):
    """구현 전 결정과 해소 상태를 명시적으로 기록하는 항목."""

    topic: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    status: Literal["open", "resolved"] = "open"
    decision: str = ""
    source: Literal["user", "recommended_default", "inferred"] = "user"
    confidence: Literal["high", "medium", "low"] = "medium"
    owner: str = ""
    due_date: str = ""

    @model_validator(mode="after")
    def _resolved_requires_decision(self) -> OpenDecision:
        if self.status == "resolved" and not self.decision.strip():
            raise ValueError("해결된 결정에는 확정한 decision이 필요합니다.")
        return self


class RecommendedDecision(BaseModel):
    """Wizard의 미입력·미정값을 권장 기본값으로 해소한 근거."""

    field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source: Literal["recommended_default", "inferred"] = "recommended_default"
    confidence: Literal["high", "medium", "low"] = "medium"


class DesignContract(BaseModel):
    """6문서의 상세도를 뒷받침하는 구조화 설계 계약."""

    screens: list[ScreenSpec] = Field(default_factory=list)
    user_flows: list[UserFlow] = Field(default_factory=list)
    data_entities: list[DataEntity] = Field(default_factory=list)
    interfaces: list[InterfaceContract] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)
    error_states: list[ErrorState] = Field(default_factory=list)
    open_decisions: list[OpenDecision] = Field(default_factory=list)
    type_sections: dict[str, list[str]] = Field(default_factory=dict)


class ImplementationTask(BaseModel):
    """별도 구현 AI에게 전달하는 구현 작업."""

    id: str = Field(pattern=r"^TASK-\d{3}$")
    requirement_ids: list[str] = Field(min_length=1)
    title: str = Field(min_length=1)
    file_scope: list[str] = Field(min_length=1)
    done_when: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)


class DeliveryTestCase(BaseModel):
    """요구사항과 연결된 테스트 계약."""

    id: str = Field(pattern=r"^TEST-(?:(?:SEC|DATA|PERF)-)?\d{3}$")
    requirement_ids: list[str] = Field(min_length=1)
    scenario: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    kind: Literal["automated", "manual"]
    case_type: Literal["normal", "boundary", "failure"] = "normal"


class VerificationEvidence(BaseModel):
    """실제 구현·테스트 뒤 기록하는 검증 근거."""

    test_id: str = Field(pattern=r"^TEST-(?:(?:SEC|DATA|PERF)-)?\d{3}$")
    status: VerificationStatus
    evidence: str = ""
    executor: str = ""
    executed_at: datetime | None = None
    evidence_path: str = ""

    @model_validator(mode="after")
    def _pass_requires_evidence(self) -> VerificationEvidence:
        if self.status is VerificationStatus.PASS and (
            not self.evidence.strip()
            or not self.executor.strip()
            or self.executed_at is None
            or not self.evidence_path.strip()
        ):
            raise ValueError("PASS 상태에는 근거·검증자·실행 시각·증거 경로가 필요합니다.")
        return self


class ReleaseRecord(BaseModel):
    """실제 릴리스 또는 롤백 실행의 append-only 기록."""

    id: str = Field(pattern=r"^REL-\d{8}-\d{2}$")
    status: ReleaseStatus
    commit: str = ""
    artifact: str = ""
    checksum_sha256: str = ""
    executor: str = ""
    executed_at: datetime | None = None
    evidence: str = ""

    @model_validator(mode="after")
    def _completed_release_requires_evidence(self) -> ReleaseRecord:
        if self.status is not ReleaseStatus.NOT_RUN and (
            not self.commit.strip()
            or not self.artifact.strip()
            or not self.checksum_sha256.strip()
            or not self.executor.strip()
            or self.executed_at is None
            or not self.evidence.strip()
        ):
            raise ValueError(
                "실행된 릴리스에는 commit·artifact·checksum·실행자·시각·증거가 필요합니다."
            )
        return self


class SpecRequest(BaseModel):
    """``start_spec`` 입력 검증."""

    project_type: ProjectType
    user_request: str = Field(min_length=1, description="사용자의 원문 요청")
    known_info: dict[str, str] = Field(
        default_factory=dict,
        description="LLM 이 요청에서 이미 추출한 필드값 (예: {'platform': '모바일'})",
    )
    project_root: str = ""
    documentation: DocumentationIntake = Field(default_factory=DocumentationIntake)


class Question(BaseModel):
    """미충족 필드에 대해 사용자에게 물을 질문."""

    field: str = Field(description="답이 저장될 필드 키")
    text: str = Field(description="사용자에게 물을 문구")
    options: list[str] = Field(default_factory=list, description="보기(있으면 객관식)")
    description: str = Field(default="", description="이 항목이 무엇인지 한 줄 설명")
    hint: str = Field(default="", description="어떤 선택이 좋은지 안내하는 힌트")
    allows_other: bool = Field(
        default=False,
        description="선택지 외의 내용을 '기타' 상세 입력으로 받을 수 있는지",
    )


class WebQuestionAnswer(BaseModel):
    """로컬 웹 질문 화면에서 확정한 하나의 답변."""

    value: str = Field(min_length=1, description="검증된 답변 값")

    @field_validator("value")
    @classmethod
    def _reject_blank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("답변은 공백만으로 구성할 수 없습니다.")
        return value


class WebSurveyAnswer(BaseModel):
    """한 번에 제출된 웹 Wizard 요구사항 설문 답변."""

    project_type: ProjectType
    user_request: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    tech_stack: str = Field(min_length=1)
    custom_tech_stack: str = ""
    requested_features: list[str] = Field(min_length=1)
    constraints: str = ""
    reference: str = ""
    platform: str = ""
    auth_method: str = ""
    realtime: str = ""
    interface: str = ""
    runtime: str = ""
    distribution: str = ""
    data_source: str = ""
    task_type: str = ""
    deployment_target: str = ""
    target_users: str = ""
    core_workflows: str = ""
    data_and_rules: str = ""
    required_screens: str = ""
    failure_behavior: str = ""
    success_metrics: str = ""
    open_decisions: str = ""
    documentation: DocumentationIntake = Field(default_factory=DocumentationIntake)

    @field_validator(
        "user_request",
        "problem",
        "goal",
        "purpose",
        "tech_stack",
        "custom_tech_stack",
        "constraints",
        "reference",
        "platform",
        "auth_method",
        "realtime",
        "interface",
        "runtime",
        "distribution",
        "data_source",
        "task_type",
        "deployment_target",
        "target_users",
        "core_workflows",
        "data_and_rules",
        "required_screens",
        "failure_behavior",
        "success_metrics",
        "open_decisions",
    )
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("user_request", "problem", "goal", "purpose", "tech_stack")
    @classmethod
    def _reject_blank_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("필수 설문 항목은 공백만으로 입력할 수 없습니다.")
        return value

    @field_validator("requested_features")
    @classmethod
    def _reject_blank_features(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            raise ValueError("MVP 기능을 하나 이상 입력해주세요.")
        return cleaned

    @model_validator(mode="after")
    def _require_type_fields(self) -> WebSurveyAnswer:
        required_by_type: dict[ProjectType, tuple[str, ...]] = {
            ProjectType.ETC: ("platform", "auth_method", "realtime"),
            ProjectType.MCP_SERVER: ("interface", "runtime", "distribution"),
            ProjectType.ML_PROJECT: ("data_source", "task_type", "deployment_target"),
            ProjectType.DATA_PIPELINE: ("data_source", "deployment_target"),
        }
        missing = [
            field
            for field in required_by_type.get(self.project_type, ())
            if not getattr(self, field)
        ]
        if missing:
            raise ValueError(f"유형별 필수 항목이 비어 있습니다: {', '.join(missing)}")
        if self.tech_stack == "직접 지정" and not self.custom_tech_stack:
            raise ValueError("직접 지정한 기술 스택을 입력해주세요.")
        return self

    def template_answers(self) -> dict[str, str]:
        """선택된 템플릿이 요구하는 답변만 반환한다."""
        fields = (
            "purpose",
            "tech_stack",
            "platform",
            "auth_method",
            "realtime",
            "interface",
            "runtime",
            "distribution",
            "data_source",
            "task_type",
            "deployment_target",
            "target_users",
            "core_workflows",
            "data_and_rules",
            "required_screens",
            "failure_behavior",
            "success_metrics",
            "open_decisions",
        )
        return {field: getattr(self, field) for field in fields if getattr(self, field)}


class DomainTemplate(BaseModel):
    """유형별 MVP 템플릿(서버가 소유하는 결정적 데이터)."""

    type: ProjectType
    display_name: str
    core_features: list[str] = Field(description="MVP 포함 기능")
    excluded_features: list[str] = Field(description="MVP 제외 기능(확장 계획으로 이동)")
    default_stack: dict[str, str] = Field(description="기본 기술 스택")
    required_fields: list[str] = Field(description="필수 정보 키 목록")
    # 유형별 출력 형식 오버라이드. None 이면 앱용 기본 11섹션을 쓴다.
    output_sections: list[str] | None = Field(
        default=None, description="산출물 섹션 순서(유형별 오버라이드)"
    )
    output_guide: dict[str, str] | None = Field(
        default=None, description="섹션별 작성 지침(유형별 오버라이드)"
    )


class SpecDraft(BaseModel):
    """진행 중 명세 초안(엔티티). 서버가 소유하는 상태."""

    id: str | None = None
    project_type: ProjectType
    user_request: str
    project_root: str = ""
    answers: dict[str, str] = Field(default_factory=dict, description="field → 답변")
    intake: dict[str, str] = Field(
        default_factory=dict, description="문제·목표·제약 등 설문으로 수집한 추가 정보"
    )
    features: list[str] = Field(default_factory=list, description="확정된 MVP 기능")
    deferred: list[str] = Field(default_factory=list, description="컷된 기능('기능 — 사유' 형식)")
    tech_stack: dict[str, str] = Field(default_factory=dict)
    requirements: list[Requirement] = Field(default_factory=list)
    tasks: list[ImplementationTask] = Field(default_factory=list)
    test_cases: list[DeliveryTestCase] = Field(default_factory=list)
    design_contract: DesignContract | None = None
    verification: list[VerificationEvidence] = Field(default_factory=list)
    releases: list[ReleaseRecord] = Field(default_factory=list)
    recommended_decisions: list[RecommendedDecision] = Field(default_factory=list)
    revision: int = Field(default=1, ge=1)
    scope_confirmed: bool = False
    status: Literal["collecting", "scoped", "confirmed", "finalized"] = "collecting"
    created_at: datetime | None = None
    documentation: DocumentationIntake = Field(default_factory=DocumentationIntake)
