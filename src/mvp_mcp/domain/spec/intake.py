"""의도 파악(discovery) 질문 뱅크 — 본격 명세 작성 이전의 선행 단계.

사용자가 아이디어를 제시하면 곧바로 결과물로 넘어가지 않고, 먼저 이 질문들로 진짜
문제·목표·기대 산출물·제약을 문답으로 파악한다. 서버가 소유하는 결정적 콘텐츠(질문)이며,
실제 대화·판단은 클라이언트 LLM 이 수행한다(§0 역할 분담).
"""

from __future__ import annotations

from .model import Question

# 첫 채팅에서 의도가 불명확할 때 순서대로 묻는 discovery 질문.
INTAKE_QUESTIONS: list[Question] = [
    Question(
        field="problem",
        text="지금 겪고 있는 문제나 불편은 무엇인가요?",
        description="왜 이걸 만들려 하는지의 근본 이유.",
        hint="증상이 아니라 근본 문제를 말할수록 더 좋은 설계가 나옵니다.",
    ),
    Question(
        field="goal",
        text="이걸로 궁극적으로 이루고 싶은 목표는 무엇인가요?",
        description="완료했을 때 도달하고 싶은 상태.",
        hint="정량 목표(예: 반복 작업 50% 단축)로 말하면 범위가 또렷해집니다.",
    ),
    Question(
        field="deliverable",
        text="어떤 형태의 결과물을 기대하나요?",
        options=["앱/웹 서비스", "개발 도구/MCP", "데이터/ML", "기타"],
        description="만들고 싶은 산출물의 종류.",
        hint="이 답이 프로젝트 유형과 출력 형식을 결정합니다.",
    ),
    Question(
        field="constraints",
        text="꼭 지켜야 할 제약이 있나요? (기술·기간·예산·규정 등)",
        description="설계를 제한하는 조건.",
        hint="없으면 '없음'이라고 답해도 됩니다.",
    ),
]
