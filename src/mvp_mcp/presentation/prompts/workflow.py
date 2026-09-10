"""MVP 명세 워크플로 Prompt 어댑터.

MCP 클라이언트(예: Claude)에게 이 서버의 도구를 어떤 순서로 쓰는지 안내한다. 이 문구가
산출물 품질을 좌우한다 — 아웃풋이 아쉬우면 이 파일부터 다듬는다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

SERVER_INSTRUCTIONS = (
    "이 서버는 HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE 기반 문서 패키지를 생성한다. "
    "새 제품 아이디어에는 documentation_collect_intake(user_request, project_root)로 Wizard를 "
    "연다. 이 도구가 spec_id를 반환하면 제출은 이미 끝난 것이므로 제출 확인 메시지를 요구하거나 "
    "턴을 종료하지 말고, documentation_register_requirements → "
    "documentation_register_architecture → "
    "documentation_register_delivery → documentation_validate → documentation_preview 순서로 "
    "진행하라. "
    "preview의 파일·충돌·manifest hash를 사용자가 확인하고 명시적으로 승인한 뒤에만 "
    "documentation_apply를 호출하라. 구현·테스트·배포를 실행했다고 추측하지 마라."
)

WORKFLOW_INSTRUCTIONS = (
    "너는 가이드 기반 문서화 도구를 사용한다. 별도 요청이 없으면 한국어로 작성한다.\n\n"
    "1. `documentation_collect_intake(user_request, project_root)`로 통합 Wizard를 연다. 사용자는 "
    "제품 내용, 배포·UI·API·저장소·데이터 변경·인증·개인정보·결제·기타 위험·복구와 선택적 "
    "HTML 프로토타입 필요 여부를 제출한다. 협업 규모와 책임자는 설문에서 묻지 않는다. 반환값의 "
    "submission_status=submitted이면 같은 턴에서 next_action을 즉시 계속하며 "
    "'제출함'을 요구하지 않는다.\n"
    "2. `documentation_register_requirements`에 BIZ/FR/NFR/DATA/SEC 요구와 관찰 가능한 AC를 "
    "등록한다. `documentation_register_architecture`에 화면·흐름·데이터·인터페이스·규칙·오류와 "
    "ASR/ADR 근거를 등록한다. `documentation_register_delivery`에 모든 요구사항을 연결한 TASK와 "
    "TEST를 등록한다.\n"
    "3. 선택 입력이 비었거나 되돌릴 수 있는 저위험 항목이 계획 미정이면 서버의 "
    "recommended_decisions를 "
    "채택하고 가정으로 기록한다. 보안·법률·결제·개인정보·파괴적 데이터 변경처럼 오판 비용이 큰 "
    "항목만 사용자에게 묻는다. 기술 기본안을 채택한 설계 결정은 status=resolved, decision, "
    "source와 "
    "근거를 등록하고 OPEN으로 남기지 않는다. `documentation_validate`로 추적성과 실제 미해결 차단 "
    "항목을 확인한다.\n"
    "4. 통과하면 `documentation_preview`를 호출한다. 서버가 가이드 전체 목차의 문서를 직접 "
    "렌더링하며 HTTP API면 OpenAPI, 사용자가 필요를 선택하면 NON-SSOT HTML을 추가한다. 대상 "
    "저장소는 이 단계에서 읽기 전용이다.\n"
    "5. preview의 planned outputs, stale outputs, conflicts와 manifest hash를 사용자에게 보여준다. "
    "사용자가 명시적으로 승인한 경우에만 그 hash와 승인자·메모로 `documentation_apply`를 호출한다. "
    "unmanaged 충돌은 자동 덮어쓰지 않는다.\n"
    "6. 실제 테스트 뒤에만 `documentation_record_test_run`, 실제 배포·롤백 뒤에만 "
    "`documentation_record_release`를 호출한다. 증거 없는 PASS/RELEASED를 만들지 않는다.\n"
)


def register_prompts(mcp: FastMCP) -> None:
    """MVP 설계 워크플로 Prompt 를 등록한다."""

    @mcp.prompt()
    def mvp_spec_workflow() -> str:
        """사용자 요청을 MVP 명세로 변환하는 도구 사용 절차."""
        return WORKFLOW_INSTRUCTIONS
