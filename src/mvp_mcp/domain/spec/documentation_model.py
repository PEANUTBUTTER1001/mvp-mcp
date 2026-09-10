"""가이드 기반 리포지토리 문서화의 구조화 계약."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChangeType(StrEnum):
    NEW = "신규 개발"
    EXISTING = "기존 시스템 변경"


class DeploymentScope(StrEnum):
    LOCAL = "로컬 실험"
    INTERNAL = "내부 사용"
    PRODUCTION = "실제 사용자 배포"


class UiSurface(StrEnum):
    WEB = "웹"
    MOBILE = "모바일"
    ADMIN = "관리자 UI"
    NONE = "화면 없음"


class HttpApiMode(StrEnum):
    NEW = "신규 제공"
    CHANGE = "기존 API 변경"
    NONE = "없음"


class StorageNeed(StrEnum):
    REQUIRED = "필요"
    NOT_REQUIRED = "불필요"


class StorageType(StrEnum):
    DATABASE = "DB"
    FILE = "파일"
    EXTERNAL = "외부 저장소"


class DataChange(StrEnum):
    CHANGES = "변경함"
    NO_CHANGE = "변경하지 않음"


class AuthCapability(StrEnum):
    LOGIN = "로그인"
    SESSION = "세션"
    AUTHORIZATION = "역할·권한"
    RECOVERY = "계정 복구"
    NONE = "없음"
    UNDECIDED = "계획 미정"


class AuthMethod(StrEnum):
    PASSWORD = "이메일/비밀번호"
    SOCIAL = "소셜 로그인"
    PASSKEY = "패스키"
    SSO = "SSO"
    OTHER = "기타"
    UNDECIDED = "계획 미정"


class PersonalDataType(StrEnum):
    CONTACT = "연락처"
    ACCOUNT_ID = "계정 식별자"
    PROFILE = "프로필"
    ADDRESS = "주소"
    LOCATION = "위치"
    USER_CONTENT = "사용자 콘텐츠"
    NONE = "없음"
    UNDECIDED = "계획 미정"


class TernaryDecision(StrEnum):
    REQUIRED = "필요"
    NOT_REQUIRED = "불필요"
    UNDECIDED = "계획 미정"


class PaymentRisk(StrEnum):
    PRESENT = "있음"
    ABSENT = "없음"
    UNDECIDED = "계획 미정"


class OtherRisk(StrEnum):
    LOCATION = "위치정보"
    FILE_UPLOAD = "파일 업로드"
    EXTERNAL_INPUT = "외부 입력"
    SECRET = "비밀정보"
    PUBLIC_API = "공개 API"
    NONE = "없음"
    UNDECIDED = "계획 미정"


class PrototypePreview(StrEnum):
    REQUIRED = "필요"
    NOT_REQUIRED = "불필요"


class DocumentProfile(StrEnum):
    PROTOTYPE_4 = "PROTOTYPE_4"
    MVP_6 = "MVP_6"
    MVP_6_SECURITY = "MVP_6_SECURITY"
    MVP_6_MIGRATION = "MVP_6_MIGRATION"
    MVP_6_FULL_RISK = "MVP_6_FULL_RISK"


class Prototype4Attestation(StrEnum):
    NO_PARALLEL_HUMANS = "병렬 인간 작업 없음"
    NO_PARALLEL_AGENTS = "병렬 Agent 작업 없음"
    NO_INDEPENDENT_QA = "독립 QA 없음"
    NO_OPERATIONS_HANDOFF = "운영 인계 없음"


_PROTOTYPE_4_ATTESTATIONS = frozenset(Prototype4Attestation)


class DocumentationIntake(BaseModel):
    """Wizard가 수집하는 문서 프로파일·위험·프로토타입 판정 입력."""

    change_type: ChangeType = ChangeType.NEW
    deployment_scope: DeploymentScope = DeploymentScope.LOCAL
    ui_surfaces: list[UiSurface] = Field(default_factory=lambda: [UiSurface.NONE])
    http_api_mode: HttpApiMode = HttpApiMode.NONE
    storage_need: StorageNeed = StorageNeed.NOT_REQUIRED
    storage_types: list[StorageType] = Field(default_factory=list)
    existing_data_change: DataChange = DataChange.NO_CHANGE
    auth_capabilities: list[AuthCapability] = Field(default_factory=lambda: [AuthCapability.NONE])
    auth_methods: list[AuthMethod] = Field(default_factory=list)
    personal_data_types: list[PersonalDataType] = Field(
        default_factory=lambda: [PersonalDataType.NONE]
    )
    payment_risk: PaymentRisk = PaymentRisk.ABSENT
    other_risks: list[OtherRisk] = Field(default_factory=lambda: [OtherRisk.NONE])
    recovery_need: TernaryDecision = TernaryDecision.NOT_REQUIRED
    prototype_preview: PrototypePreview = PrototypePreview.NOT_REQUIRED
    requested_profile: DocumentProfile | None = None
    prototype4_attestations: list[Prototype4Attestation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_combinations(self) -> DocumentationIntake:
        self._exclusive(self.ui_surfaces, UiSurface.NONE, "사용자 화면")
        self._exclusive(self.auth_capabilities, AuthCapability.NONE, "인증·권한")
        self._exclusive(self.auth_capabilities, AuthCapability.UNDECIDED, "인증·권한")
        self._exclusive(self.personal_data_types, PersonalDataType.NONE, "개인정보")
        self._exclusive(self.personal_data_types, PersonalDataType.UNDECIDED, "개인정보")
        self._exclusive(self.other_risks, OtherRisk.NONE, "기타 위험")
        self._exclusive(self.other_risks, OtherRisk.UNDECIDED, "기타 위험")
        if self.storage_need is StorageNeed.REQUIRED and not self.storage_types:
            raise ValueError("저장소가 필요하면 종류를 하나 이상 선택해야 합니다.")
        if self.storage_need is StorageNeed.NOT_REQUIRED and self.storage_types:
            raise ValueError("저장소가 불필요하면 저장소 종류를 선택할 수 없습니다.")
        if AuthCapability.LOGIN in self.auth_capabilities and not self.auth_methods:
            raise ValueError("로그인을 선택하면 로그인 방식을 하나 이상 선택해야 합니다.")
        if AuthCapability.LOGIN not in self.auth_capabilities and self.auth_methods:
            raise ValueError("로그인을 선택하지 않으면 로그인 방식을 선택할 수 없습니다.")
        return self

    @staticmethod
    def _exclusive(values: Sequence[StrEnum], marker: StrEnum, label: str) -> None:
        if marker in values and len(values) != 1:
            raise ValueError(f"{label}의 '{marker.value}'은 다른 항목과 함께 선택할 수 없습니다.")

    @property
    def has_pending_decision(self) -> bool:
        return (
            AuthCapability.UNDECIDED in self.auth_capabilities
            or PersonalDataType.UNDECIDED in self.personal_data_types
            or self.payment_risk is PaymentRisk.UNDECIDED
            or OtherRisk.UNDECIDED in self.other_risks
            or self.recovery_need is TernaryDecision.UNDECIDED
            or AuthMethod.UNDECIDED in self.auth_methods
        )

    @property
    def security_active(self) -> bool:
        return (
            any(
                value not in {AuthCapability.NONE, AuthCapability.UNDECIDED}
                for value in self.auth_capabilities
            )
            or any(
                value not in {PersonalDataType.NONE, PersonalDataType.UNDECIDED}
                for value in self.personal_data_types
            )
            or self.payment_risk is PaymentRisk.PRESENT
            or any(value not in {OtherRisk.NONE, OtherRisk.UNDECIDED} for value in self.other_risks)
            or self.has_pending_decision
        )

    @property
    def migration_active(self) -> bool:
        return self.existing_data_change is DataChange.CHANGES

    @property
    def profile(self) -> DocumentProfile:
        if (
            self.requested_profile is DocumentProfile.PROTOTYPE_4
            and set(self.prototype4_attestations) == _PROTOTYPE_4_ATTESTATIONS
            and self.deployment_scope is DeploymentScope.LOCAL
            and not self.security_active
            and not self.migration_active
        ):
            return DocumentProfile.PROTOTYPE_4
        if self.security_active and self.migration_active:
            return DocumentProfile.MVP_6_FULL_RISK
        if self.security_active:
            return DocumentProfile.MVP_6_SECURITY
        if self.migration_active:
            return DocumentProfile.MVP_6_MIGRATION
        return DocumentProfile.MVP_6


class DocumentationValidationResult(BaseModel):
    profile: DocumentProfile
    bundle_valid: bool
    implementation_ready: bool
    design_approved: bool = False
    verification_done: bool = False
    release_approved: bool = False
    issues: list[str] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    next_action: str


class PreviewArtifact(BaseModel):
    relative_path: str
    category: Literal[
        "managed_documents",
        "contract_artifacts",
        "prototype_artifacts",
        "supporting_files",
        "evidence_artifacts",
        "internal_metadata",
    ]
    action: Literal["CREATE", "UPDATE_MANAGED", "KEEP_VALID", "CONFLICT_UNMANAGED"]
    new_sha256: str
    current_sha256: str | None = None


class DocumentationPreview(BaseModel):
    preview_id: str
    spec_id: str
    profile: DocumentProfile
    manifest_sha256: str
    artifacts: list[PreviewArtifact]
    conflicts: list[str] = Field(default_factory=list)
    stale_outputs: list[str] = Field(default_factory=list)
    preview_directory: str


class DocumentationApplyResult(BaseModel):
    preview_id: str
    manifest_sha256: str
    applied_outputs: list[str] = Field(default_factory=list)
    skipped_outputs: list[str] = Field(default_factory=list)
    stale_outputs: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    status: Literal["APPLIED", "BLOCKED"]


class RenderedDocumentationPackage(BaseModel):
    """렌더러가 만든 상대 경로별 UTF-8 텍스트."""

    profile: DocumentProfile
    files: dict[str, str]
    source_contract_sha256: str | None = None
