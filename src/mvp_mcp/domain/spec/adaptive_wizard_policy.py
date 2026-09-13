"""2단계 적응형 Wizard의 질문 예산과 1차 문항 정책."""

# ruff: noqa: E501

from __future__ import annotations

from .adaptive_wizard_model import AdaptiveWizardQuestion, WizardQuestionKind, WritePolicy


def intake_questions(
    requested_write_policy: WritePolicy | None = None,
) -> list[AdaptiveWizardQuestion]:
    """공통·유형별 문항을 선언형으로 제공한다.

    작업 성격과 솔루션 분류를 분리한다. 특히 Android/iOS 앱은 콘텐츠 도메인과
    무관하게 모바일 앱으로 분류되어, 웹 블로그 템플릿으로 흡수되지 않는다.
    """

    select = WizardQuestionKind.SELECT
    text = WizardQuestionKind.TEXT
    textarea = WizardQuestionKind.TEXTAREA
    questions = [
        AdaptiveWizardQuestion(
            id="work_type",
            label="이번 작업 유형",
            description="새 프로젝트, 기능 추가, 리팩터링, 결함 수정, 문서·운영 개선 중 하나를 고르세요.",
            kind=select,
            options=[
                "new_project",
                "feature_addition",
                "refactoring",
                "bug_fix",
                "documentation_ops",
            ],
        ),
        AdaptiveWizardQuestion(
            id="solution_family",
            label="만들거나 변경할 솔루션 유형",
            description="작업의 주된 성격을 고르세요. 제품 앱의 화면·도메인은 다음 문항에서 따로 묻습니다.",
            kind=select,
            options=[
                "product_application",
                "api_service",
                "developer_tool",
                "ml_system",
                "data_pipeline",
                "automation_integration",
                "other",
            ],
        ),
        AdaptiveWizardQuestion(
            id="primary_surface",
            label="제품 앱의 주 제공 화면",
            description="제품 앱일 때만 고르세요. Android 앱은 Android를 선택하면 됩니다.",
            kind=select,
            options=["android_app", "ios_app", "cross_platform_app", "web_app"],
            visible_when={"solution_family": ["product_application"]},
        ),
        AdaptiveWizardQuestion(
            id="app_domain_hint",
            label="제품 앱의 핵심 도메인",
            description="기능 묶음의 기본값을 위한 힌트이며, 화면 유형과 혼동하지 마세요.",
            kind=select,
            options=[
                "communication",
                "commerce",
                "content_publishing",
                "general_business",
                "other",
            ],
            visible_when={"solution_family": ["product_application"]},
        ),
        AdaptiveWizardQuestion(
            id="target_context",
            label="대상 제품·저장소·영역",
            description="무엇을 대상으로 하는지와 관련 모듈·화면·기능을 적으세요.",
            kind=textarea,
        ),
        AdaptiveWizardQuestion(id="problem", label="현재 문제 또는 기회", kind=textarea),
        AdaptiveWizardQuestion(id="goal", label="이번 작업의 목표", kind=textarea),
        AdaptiveWizardQuestion(
            id="affected_users", label="영향을 받는 사용자·운영자", kind=textarea
        ),
        AdaptiveWizardQuestion(id="mvp_scope", label="이번 범위에 반드시 포함할 것", kind=textarea),
        AdaptiveWizardQuestion(id="success_criteria", label="성공을 판단할 기준", kind=textarea),
        AdaptiveWizardQuestion(
            id="constraints_risks",
            label="제약·위험·변경하면 안 되는 것",
            description="일정, 호환성, 데이터, 보안·규정, 성능, 운영 제약을 적으세요.",
            kind=textarea,
        ),
        AdaptiveWizardQuestion(
            id="write_policy",
            label="생성 문서의 파일 반영 정책",
            description="후보 생성은 항상 진행합니다. 기존 .mvpmcp 파일 반영 방식만 선택하세요.",
            kind=select,
            options=["generate_only", "safe_auto_apply", "manual_apply"],
        ),
        AdaptiveWizardQuestion(
            id="tech_stack",
            label="기술 스택 또는 AI 권장안",
            description="확정된 스택을 적거나, 아직 없으면 'AI 권장안 사용'이라고 적으세요.",
            kind=textarea,
        ),
        AdaptiveWizardQuestion(
            id="new_project_boundary",
            label="초기 출시 범위와 명시적 비범위",
            kind=textarea,
            visible_when={"work_type": ["new_project"]},
        ),
        AdaptiveWizardQuestion(
            id="new_project_launch_context",
            label="초기 사용·배포 환경",
            kind=text,
            visible_when={"work_type": ["new_project"]},
        ),
        AdaptiveWizardQuestion(
            id="new_project_known_dependencies",
            label="이미 정해진 기술·외부 의존성",
            kind=textarea,
            visible_when={"work_type": ["new_project"]},
        ),
        AdaptiveWizardQuestion(
            id="feature_affected_contracts",
            label="영향 받는 기존 기능·API·화면·데이터",
            kind=textarea,
            visible_when={"work_type": ["feature_addition"]},
        ),
        AdaptiveWizardQuestion(
            id="feature_compatibility",
            label="반드시 지켜야 하는 호환성·기존 동작",
            kind=textarea,
            visible_when={"work_type": ["feature_addition"]},
        ),
        AdaptiveWizardQuestion(
            id="feature_migration",
            label="데이터·설정·사용자 전환 필요 여부",
            kind=textarea,
            visible_when={"work_type": ["feature_addition"]},
        ),
        AdaptiveWizardQuestion(
            id="refactor_current_pain",
            label="현재 구조의 유지보수·품질 문제",
            kind=textarea,
            visible_when={"work_type": ["refactoring"]},
        ),
        AdaptiveWizardQuestion(
            id="refactor_behavior_lock",
            label="바꾸면 안 되는 외부 동작·계약",
            kind=textarea,
            visible_when={"work_type": ["refactoring"]},
        ),
        AdaptiveWizardQuestion(
            id="refactor_baseline",
            label="현재 테스트·성능·운영 기준선",
            kind=textarea,
            visible_when={"work_type": ["refactoring"]},
        ),
        AdaptiveWizardQuestion(
            id="bug_reproduction",
            label="재현 절차·발생 조건",
            kind=textarea,
            visible_when={"work_type": ["bug_fix"]},
        ),
        AdaptiveWizardQuestion(
            id="bug_expected_actual",
            label="기대 결과와 실제 결과",
            kind=textarea,
            visible_when={"work_type": ["bug_fix"]},
        ),
        AdaptiveWizardQuestion(
            id="bug_impact",
            label="영향 범위·심각도·회피 방법",
            kind=textarea,
            visible_when={"work_type": ["bug_fix"]},
        ),
        AdaptiveWizardQuestion(
            id="docs_audience",
            label="문서를 사용할 독자와 사용 시점",
            kind=textarea,
            visible_when={"work_type": ["documentation_ops"]},
        ),
        AdaptiveWizardQuestion(
            id="docs_source_material",
            label="확인해야 할 기존 문서·운영 자료·저장소 근거",
            kind=textarea,
            visible_when={"work_type": ["documentation_ops"]},
        ),
        AdaptiveWizardQuestion(
            id="docs_maintenance_owner",
            label="갱신 주기·운영 책임·변경 관리 요구",
            kind=textarea,
            visible_when={"work_type": ["documentation_ops"]},
        ),
    ]
    if requested_write_policy is not None:
        return [question for question in questions if question.id != "write_policy"]
    return questions


def validate_design_questions(
    questions: list[AdaptiveWizardQuestion],
    intake_question_ids: set[str] | None = None,
) -> list[AdaptiveWizardQuestion]:
    """모델이 만든 2차 질문이 질문 예산·안전한 선언형 계약을 지키는지 확인한다."""

    if not 3 <= len(questions) <= 7:
        raise ValueError("2차 맞춤 Wizard는 3~7개 질문이어야 합니다.")
    ids = [question.id for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("2차 Wizard 문항 ID는 중복될 수 없습니다.")
    repeated_intake_ids = set(ids).intersection(intake_question_ids or set())
    if repeated_intake_ids:
        raise ValueError(
            "2차 Wizard는 1차 문항을 다시 사용할 수 없습니다: "
            + ", ".join(sorted(repeated_intake_ids))
        )
    if "document_output_mode" in ids:
        raise ValueError(
            "2차 Wizard는 파일 반영 정책을 다시 물을 수 없습니다: document_output_mode"
        )
    if any(question.visible_when for question in questions):
        raise ValueError(
            "2차 맞춤 Wizard는 이미 분석된 질문만 포함하므로 조건부 문항을 사용할 수 없습니다."
        )
    return questions
