"""FastMCP 서버 엔트리포인트 및 Composition Root.

모든 의존성 와이어링(인터페이스 → 구현체)은 오직 이 모듈에서만 수행한다.
UseCase 와 Presentation 어댑터는 구현체를 알지 못한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.core.config import Settings
from mvp_mcp.core.logging import configure_logging
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.data.system_clock import SystemClock
from mvp_mcp.domain.spec.query import (
    GetDraftUseCase,
    GetIntakeQuestionsUseCase,
    GetMissingInfoUseCase,
    GetTemplateUseCase,
    ListProjectTypesUseCase,
)
from mvp_mcp.domain.spec.usecase import (
    AnswerQuestionUseCase,
    FinalizeSpecUseCase,
    ScopeMvpUseCase,
    StartSpecUseCase,
)
from mvp_mcp.presentation.prompts.workflow import register_prompts
from mvp_mcp.presentation.resources.spec import register_resources
from mvp_mcp.presentation.tools.answer_question import register_answer_question_tool
from mvp_mcp.presentation.tools.clarify_intent import register_clarify_intent_tool
from mvp_mcp.presentation.tools.finalize_spec import register_finalize_spec_tool
from mvp_mcp.presentation.tools.get_missing_info import register_get_missing_info_tool
from mvp_mcp.presentation.tools.scope_mvp import register_scope_mvp_tool
from mvp_mcp.presentation.tools.start_spec import register_start_spec_tool


def build() -> FastMCP:
    """설정을 읽어 구현체를 조립하고 등록을 마친 FastMCP 서버를 반환한다."""
    configure_logging()  # stderr 로깅 1회 구성(stdout 은 프로토콜 전용).
    _cfg = Settings()  # 부팅 시 설정 검증(fail-fast).

    # 1. 구현체 생성 (data 계층)
    template_repo = InMemoryTemplateRepository()
    spec_repo = InMemorySpecRepository()
    clock = SystemClock()

    # 2. UseCase 에 구현체 주입 (domain 계층)
    start_uc = StartSpecUseCase(template_repo, spec_repo, clock)
    answer_uc = AnswerQuestionUseCase(spec_repo, template_repo)
    scope_uc = ScopeMvpUseCase(spec_repo, template_repo)
    finalize_uc = FinalizeSpecUseCase(spec_repo, template_repo)
    missing_uc = GetMissingInfoUseCase(spec_repo, template_repo)
    draft_uc = GetDraftUseCase(spec_repo)
    types_uc = ListProjectTypesUseCase(template_repo)
    template_uc = GetTemplateUseCase(template_repo)
    intake_uc = GetIntakeQuestionsUseCase()

    # 3. 어댑터 등록 (presentation 계층)
    mcp = FastMCP("Mvp")
    register_prompts(mcp)
    register_clarify_intent_tool(mcp, intake_uc)
    register_start_spec_tool(mcp, start_uc)
    register_answer_question_tool(mcp, answer_uc)
    register_get_missing_info_tool(mcp, missing_uc)
    register_scope_mvp_tool(mcp, scope_uc)
    register_finalize_spec_tool(mcp, finalize_uc)
    register_resources(mcp, types_uc, template_uc, draft_uc)
    return mcp


def main() -> None:
    """콘솔 스크립트 진입점. 기본 stdio 전송으로 서버를 실행한다."""
    build().run()


if __name__ == "__main__":
    main()
