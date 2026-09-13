"""FastMCP 서버 엔트리포인트 및 Composition Root.

모든 의존성 와이어링(인터페이스 → 구현체)은 오직 이 모듈에서만 수행한다.
UseCase 와 Presentation 어댑터는 구현체를 알지 못한다.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mvp_mcp.core.config import Settings
from mvp_mcp.core.logging import configure_logging
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.repository_document_exporter import RepositoryDocumentExporter
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.data.system_clock import SystemClock
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    CreateAdaptiveWizardDraftUseCase,
    GetAdaptiveWizardRunUseCase,
    OpenAdaptiveDesignWizardUseCase,
    StartAdaptiveWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
)
from mvp_mcp.domain.spec.candidate_lifecycle_usecase import (
    RecordCandidateReleaseUseCase,
    RecordCandidateTestRunUseCase,
    UpdateCandidateArchitectureUseCase,
    UpdateCandidateDeliveryUseCase,
    UpdateCandidateRequirementsUseCase,
)
from mvp_mcp.domain.spec.candidate_package_usecase import (
    ApplyCandidatePackageUseCase,
    GetCandidatePackageStatusUseCase,
    PreviewCandidatePackageUseCase,
    ValidateCandidatePackageUseCase,
)
from mvp_mcp.domain.spec.query import (
    GetDraftUseCase,
    GetTemplateUseCase,
    ListProjectTypesUseCase,
)
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, register_prompts
from mvp_mcp.presentation.resources.spec import register_resources
from mvp_mcp.presentation.tools.documentation_apply_package import (
    register_documentation_apply_package_tool,
)
from mvp_mcp.presentation.tools.documentation_package_status import (
    register_documentation_package_status_tool,
)
from mvp_mcp.presentation.tools.documentation_preview_package import (
    register_documentation_preview_package_tool,
)
from mvp_mcp.presentation.tools.documentation_record_candidate_release import (
    register_documentation_record_candidate_release_tool,
)
from mvp_mcp.presentation.tools.documentation_record_candidate_test_run import (
    register_documentation_record_candidate_test_run_tool,
)
from mvp_mcp.presentation.tools.documentation_start_adaptive_wizard import (
    register_documentation_start_adaptive_wizard_tool,
)
from mvp_mcp.presentation.tools.documentation_submit_adaptive_wizard_answers import (
    register_documentation_submit_adaptive_wizard_answers_tool,
)
from mvp_mcp.presentation.tools.documentation_update_candidate_architecture import (
    register_documentation_update_candidate_architecture_tool,
)
from mvp_mcp.presentation.tools.documentation_update_candidate_delivery import (
    register_documentation_update_candidate_delivery_tool,
)
from mvp_mcp.presentation.tools.documentation_update_candidate_requirements import (
    register_documentation_update_candidate_requirements_tool,
)
from mvp_mcp.presentation.tools.documentation_validate_package import (
    register_documentation_validate_package_tool,
)
from mvp_mcp.presentation.tools.documentation_wizard_run_status import (
    register_documentation_wizard_run_status_tool,
)


def build() -> FastMCP:
    """설정을 읽어 구현체를 조립하고 등록을 마친 FastMCP 서버를 반환한다."""
    configure_logging()  # stderr 로깅 1회 구성(stdout 은 프로토콜 전용).
    cfg = Settings()  # 부팅 시 설정 검증(fail-fast).

    # 1. 구현체 생성 (data 계층)
    template_repo = InMemoryTemplateRepository()
    spec_repo = InMemorySpecRepository()
    clock = SystemClock()
    adaptive_run_repo = SqliteAdaptiveWizardRunRepository(Path(cfg.adaptive_wizard_db_path))
    candidate_package_repo = CandidatePackageRepository(cfg.output_dir)
    repository_document_exporter = RepositoryDocumentExporter(cfg.output_dir)

    # 2. UseCase 에 구현체 주입 (domain 계층)
    scope_uc = ScopeMvpUseCase(spec_repo, template_repo)
    draft_uc = GetDraftUseCase(spec_repo)
    types_uc = ListProjectTypesUseCase(template_repo)
    template_uc = GetTemplateUseCase(template_repo)
    adaptive_start_uc = StartAdaptiveWizardUseCase(adaptive_run_repo, clock)
    adaptive_design_uc = OpenAdaptiveDesignWizardUseCase(adaptive_run_repo, clock)
    adaptive_submit_uc = SubmitAdaptiveWizardAnswersUseCase(adaptive_run_repo, clock)
    adaptive_draft_uc = CreateAdaptiveWizardDraftUseCase(
        adaptive_run_repo,
        spec_repo,
        template_repo,
        scope_uc,
        candidate_package_repo,
        clock,
    )
    adaptive_run_status_uc = GetAdaptiveWizardRunUseCase(adaptive_run_repo)
    candidate_validate_uc = ValidateCandidatePackageUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )
    candidate_preview_uc = PreviewCandidatePackageUseCase(
        adaptive_run_repo,
        candidate_package_repo,
        repository_document_exporter,
        clock,
    )
    candidate_apply_uc = ApplyCandidatePackageUseCase(
        adaptive_run_repo,
        candidate_package_repo,
        repository_document_exporter,
        clock,
    )
    candidate_status_uc = GetCandidatePackageStatusUseCase(
        adaptive_run_repo,
        candidate_package_repo,
        repository_document_exporter,
    )
    candidate_requirements_uc = UpdateCandidateRequirementsUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )
    candidate_architecture_uc = UpdateCandidateArchitectureUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )
    candidate_delivery_uc = UpdateCandidateDeliveryUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )
    candidate_test_run_uc = RecordCandidateTestRunUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )
    candidate_release_uc = RecordCandidateReleaseUseCase(
        adaptive_run_repo, candidate_package_repo, clock
    )

    # 3. 어댑터 등록 (presentation 계층)
    mcp = FastMCP("Mvp", instructions=SERVER_INSTRUCTIONS)
    register_prompts(mcp)
    register_documentation_start_adaptive_wizard_tool(
        mcp,
        adaptive_start_uc,
        adaptive_design_uc,
    )
    register_documentation_submit_adaptive_wizard_answers_tool(
        mcp, adaptive_submit_uc, adaptive_draft_uc
    )
    register_documentation_wizard_run_status_tool(mcp, adaptive_run_status_uc)
    register_documentation_validate_package_tool(mcp, candidate_validate_uc)
    register_documentation_preview_package_tool(mcp, candidate_preview_uc)
    register_documentation_apply_package_tool(mcp, candidate_apply_uc)
    register_documentation_package_status_tool(mcp, candidate_status_uc)
    register_documentation_update_candidate_requirements_tool(mcp, candidate_requirements_uc)
    register_documentation_update_candidate_architecture_tool(mcp, candidate_architecture_uc)
    register_documentation_update_candidate_delivery_tool(mcp, candidate_delivery_uc)
    register_documentation_record_candidate_test_run_tool(mcp, candidate_test_run_uc)
    register_documentation_record_candidate_release_tool(mcp, candidate_release_uc)
    register_resources(mcp, types_uc, template_uc, draft_uc)
    return mcp


def main() -> None:
    """콘솔 스크립트 진입점. 기본 stdio 전송으로 서버를 실행한다."""
    build().run()


if __name__ == "__main__":
    main()
