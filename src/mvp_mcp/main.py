"""FastMCP 서버 엔트리포인트 및 Composition Root.

모든 의존성 와이어링(인터페이스 → 구현체)은 오직 이 모듈에서만 수행한다.
UseCase 와 Presentation 어댑터는 구현체를 알지 못한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.core.config import Settings
from mvp_mcp.core.logging import configure_logging
from mvp_mcp.data.spec.guide_document_renderer import GuideDocumentRenderer
from mvp_mcp.data.spec.guide_package_renderer import GuidePackageRendererImpl
from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.data.spec.openapi_renderer import OpenApiRenderer
from mvp_mcp.data.spec.repository_document_exporter import RepositoryDocumentExporter
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.data.system_clock import SystemClock
from mvp_mcp.domain.spec.documentation_usecase import (
    ApplyDocumentationUseCase,
    PreviewDocumentationUseCase,
    ValidateDocumentationUseCase,
)
from mvp_mcp.domain.spec.query import (
    GetDraftUseCase,
    GetTemplateUseCase,
    ListProjectTypesUseCase,
)
from mvp_mcp.domain.spec.usecase import (
    AskWebQuestionUseCase,
    ConfirmScopeUseCase,
    RecordReleaseUseCase,
    RecordVerificationUseCase,
    RegisterDeliveryContractUseCase,
    RegisterDesignContractUseCase,
    RegisterRequirementsUseCase,
    ScopeMvpUseCase,
    StartSpecUseCase,
    SubmitWebSurveyUseCase,
)
from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, register_prompts
from mvp_mcp.presentation.resources.spec import register_resources
from mvp_mcp.presentation.tools.ask_elicitation_question import (
    register_ask_elicitation_question_tool,
)
from mvp_mcp.presentation.tools.ask_web_question import register_ask_web_question_tool
from mvp_mcp.presentation.tools.documentation_apply import register_documentation_apply_tool
from mvp_mcp.presentation.tools.documentation_collect_intake import (
    register_documentation_collect_intake_tool,
)
from mvp_mcp.presentation.tools.documentation_preview import register_documentation_preview_tool
from mvp_mcp.presentation.tools.documentation_record_release import (
    register_documentation_release_tool,
)
from mvp_mcp.presentation.tools.documentation_record_test_run import (
    register_documentation_test_run_tool,
)
from mvp_mcp.presentation.tools.documentation_register_architecture import (
    register_documentation_architecture_tool,
)
from mvp_mcp.presentation.tools.documentation_register_delivery import (
    register_documentation_delivery_tool,
)
from mvp_mcp.presentation.tools.documentation_register_requirements import (
    register_documentation_requirements_tool,
)
from mvp_mcp.presentation.tools.documentation_start import register_documentation_start_tool
from mvp_mcp.presentation.tools.documentation_validate import register_documentation_validate_tool
from mvp_mcp.presentation.web.local_question_form import LocalWebQuestionForm
from mvp_mcp.presentation.web.local_survey_form import LocalWebSurveyForm


def build() -> FastMCP:
    """설정을 읽어 구현체를 조립하고 등록을 마친 FastMCP 서버를 반환한다."""
    configure_logging()  # stderr 로깅 1회 구성(stdout 은 프로토콜 전용).
    cfg = Settings()  # 부팅 시 설정 검증(fail-fast).

    # 1. 구현체 생성 (data 계층)
    template_repo = InMemoryTemplateRepository()
    spec_repo = InMemorySpecRepository()
    clock = SystemClock()
    question_form = LocalWebQuestionForm(cfg.question_timeout_seconds)
    blocking_survey_form = LocalWebSurveyForm(cfg.question_timeout_seconds)
    guide_renderer = GuidePackageRendererImpl(
        GuideDocumentRenderer(), OpenApiRenderer(), HtmlPrototypeRenderer()
    )
    repository_document_exporter = RepositoryDocumentExporter(cfg.output_dir)

    # 2. UseCase 에 구현체 주입 (domain 계층)
    start_uc = StartSpecUseCase(template_repo, spec_repo, clock)
    one_web_question_uc = AskWebQuestionUseCase(question_form)
    submit_survey_uc = SubmitWebSurveyUseCase(template_repo, spec_repo, clock, blocking_survey_form)
    scope_uc = ScopeMvpUseCase(spec_repo, template_repo)
    requirements_uc = RegisterRequirementsUseCase(spec_repo)
    confirm_uc = ConfirmScopeUseCase(spec_repo)
    contract_uc = RegisterDeliveryContractUseCase(spec_repo)
    design_uc = RegisterDesignContractUseCase(spec_repo)
    verification_uc = RecordVerificationUseCase(spec_repo)
    release_uc = RecordReleaseUseCase(spec_repo)
    draft_uc = GetDraftUseCase(spec_repo)
    types_uc = ListProjectTypesUseCase(template_repo)
    template_uc = GetTemplateUseCase(template_repo)
    documentation_validator_uc = ValidateDocumentationUseCase(spec_repo)
    documentation_preview_uc = PreviewDocumentationUseCase(
        spec_repo, guide_renderer, repository_document_exporter
    )
    documentation_apply_uc = ApplyDocumentationUseCase(repository_document_exporter)

    # 3. 어댑터 등록 (presentation 계층)
    mcp = FastMCP("Mvp", instructions=SERVER_INSTRUCTIONS)
    register_prompts(mcp)
    register_ask_web_question_tool(mcp, one_web_question_uc)
    register_ask_elicitation_question_tool(mcp)
    register_documentation_validate_tool(mcp, documentation_validator_uc)
    register_documentation_preview_tool(mcp, documentation_preview_uc)
    register_documentation_apply_tool(mcp, documentation_apply_uc)
    register_documentation_start_tool(mcp, start_uc, scope_uc)
    register_documentation_collect_intake_tool(mcp, submit_survey_uc, scope_uc)
    register_documentation_requirements_tool(mcp, requirements_uc, confirm_uc)
    register_documentation_architecture_tool(mcp, design_uc)
    register_documentation_delivery_tool(mcp, contract_uc)
    register_documentation_test_run_tool(mcp, verification_uc)
    register_documentation_release_tool(mcp, release_uc)
    register_resources(mcp, types_uc, template_uc, draft_uc)
    return mcp


def main() -> None:
    """콘솔 스크립트 진입점. 기본 stdio 전송으로 서버를 실행한다."""
    build().run()


if __name__ == "__main__":
    main()
