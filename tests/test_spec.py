"""MVP 명세 도메인 테스트 (PLAN §9 필수 시나리오 4건).

인메모리 리포지토리와 고정 시계를 Port 로 주입해 유스케이스를 프레임워크 없이 검증한다.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.model import ProjectType, SpecRequest
from mvp_mcp.domain.spec.output_format import OUTPUT_SECTIONS
from mvp_mcp.domain.spec.usecase import (
    AnswerQuestionUseCase,
    FinalizeSpecUseCase,
    ScopeMvpUseCase,
    StartSpecUseCase,
)

# 앱 유형(messenger) 필수 필드 전체를 채우는 답변 세트(행복 경로용).
_ALL_ANSWERS = {
    "platform": "모바일",
    "purpose": "개인 프로젝트",
    "tech_stack": "기본 스택 사용",
    "auth_method": "이메일/비밀번호",
    "realtime": "필요",
}


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, 0, 0, 0)


def _wire() -> tuple[StartSpecUseCase, AnswerQuestionUseCase, ScopeMvpUseCase, FinalizeSpecUseCase]:
    templates = InMemoryTemplateRepository()
    specs = InMemorySpecRepository()
    clock = _FixedClock()
    return (
        StartSpecUseCase(templates, specs, clock),
        AnswerQuestionUseCase(specs, templates),
        ScopeMvpUseCase(specs, templates),
        FinalizeSpecUseCase(specs, templates),
    )


def test_happy_path_messenger() -> None:
    """messenger start → 질문 5개 → 전부 answer → scope → finalize."""
    start, answer, scope, finalize = _wire()

    draft, questions = start(
        SpecRequest(project_type=ProjectType.MESSENGER, user_request="메신저 만들어줘")
    )
    assert draft.id is not None
    assert len(questions) == 5  # 앱 필수 5개(작업 인원·기간 제외) 전부 미충족.

    for field, value in _ALL_ANSWERS.items():
        _, remaining = answer(draft.id, field, value)
    assert remaining == []  # 모든 질문 소진.

    scope(draft.id, [])
    result = finalize(draft.id)

    # 11섹션 제목이 전부 컨텍스트에 포함.
    for section in OUTPUT_SECTIONS:
        assert section in result.context
    # 코어 기능은 포함, 제외 기능은 확장 언급(제외 표기)에만.
    assert "친구목록" in result.context
    assert result.draft.status == "finalized"
    assert "영상통화" not in result.draft.features
    # 산출물 언어 기본값: 한국어로 작성하도록 지시가 포함된다.
    assert "한국어" in result.context
    # 섹션별 상세 작성 지침이 포함돼 얕은 요약을 방지한다.
    assert "구현에 착수할 수 있는 수준" in result.context
    assert "PK/FK" in result.context  # DB 설계 섹션 지침
    assert "Method · Path" in result.context  # API 설계 섹션 지침
    # 산출물은 기획서 + 실행 명세서 두 문서로 구성된다.
    assert "문서 1 — 기획서 (PROPOSAL)" in result.context
    assert "문서 2 — 실행 명세서 (PLAN)" in result.context
    assert "성공 지표" in result.context  # 기획서 전용 섹션


def test_finalize_rejects_incomplete_draft() -> None:
    """추측 금지: 필드 미답변 상태에서 finalize → PipelineError(checklist)."""
    start, answer, scope, finalize = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.MESSENGER, user_request="메신저"))
    # 5개만 답변(platform, realtime 미답변) 후 scope 만 하고 finalize.
    partial = dict(_ALL_ANSWERS)
    del partial["platform"]
    del partial["realtime"]
    for field, value in partial.items():
        answer(draft.id, field, value)
    scope(draft.id, [])

    with pytest.raises(PipelineError) as exc_info:
        finalize(draft.id)

    err = exc_info.value
    assert err.stage == "checklist"
    assert "platform" in err.reason
    assert "realtime" in err.reason


def test_scope_cuts_excluded_features() -> None:
    """범위 강제: 제외 기능은 features 에 없고 deferred 에 사유와 함께."""
    start, _answer, scope, _finalize = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.MESSENGER, user_request="메신저"))

    scoped = scope(draft.id, ["영상통화", "1:1 채팅"])

    assert "영상통화" not in scoped.features
    assert any("영상통화" in d for d in scoped.deferred)
    assert "1:1 채팅" in scoped.features  # 코어 기능은 유지.


def test_etc_fallback_caps_features() -> None:
    """폴백: etc 유형 + 기능 9개 요청 → 7개만 features, 2개 deferred."""
    start, _answer, scope, _finalize = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.ETC, user_request="뭔가 새로운 서비스"))

    requested = [f"기능{i}" for i in range(1, 10)]  # 9개.
    scoped = scope(draft.id, requested)

    assert len(scoped.features) == 7
    assert len(scoped.deferred) == 2


def test_intake_questions_cover_intent_discovery() -> None:
    """선행 단계 discovery 질문에 문제·목표·기대 산출물·제약이 포함된다."""
    from mvp_mcp.domain.spec.query import GetIntakeQuestionsUseCase

    questions = GetIntakeQuestionsUseCase()()
    fields = {q.field for q in questions}
    assert {"problem", "goal", "deliverable", "constraints"} <= fields
    for q in questions:  # 문답용 설명·힌트가 채워져 있다.
        assert q.description
        assert q.hint


def test_questions_carry_description_and_hint() -> None:
    """문답식 진행을 위해 모든 질문에 설명·힌트가 채워져 있다."""
    start, _answer, _scope, _finalize = _wire()
    _draft, questions = start(
        SpecRequest(project_type=ProjectType.MCP_SERVER, user_request="MCP 도구")
    )
    assert questions  # 미충족 질문이 있음
    for q in questions:
        assert q.description, f"{q.field} 에 설명 없음"
        assert q.hint, f"{q.field} 에 힌트 없음"


def test_project_type_coerce_falls_back_to_etc() -> None:
    """미지원/빈 유형 문자열은 크래시 없이 etc 로 폴백한다."""
    assert ProjectType.coerce("messenger") is ProjectType.MESSENGER
    assert ProjectType.coerce("MESSENGER") is ProjectType.MESSENGER
    assert ProjectType.coerce("mcp-server") is ProjectType.ETC  # 미지원 값
    assert ProjectType.coerce("") is ProjectType.ETC
    assert ProjectType.coerce(None) is ProjectType.ETC


def test_start_with_unsupported_type_uses_etc() -> None:
    """지원하지 않는 유형으로 시작해도 etc 템플릿으로 세션이 열린다."""
    start, _answer, _scope, _finalize = _wire()
    draft, questions = start(
        SpecRequest(
            project_type=ProjectType.coerce("designer"),
            user_request="디자이너 MCP 만들어줘",
        )
    )
    assert draft.project_type is ProjectType.ETC
    assert len(questions) == 5  # etc 도 앱 필수 5개(작업 인원·기간 제외)를 묻는다.


def test_mcp_server_uses_dev_output_profile() -> None:
    """mcp_server 유형은 개발 도구 질문·출력 형식을 쓴다(화면/DB 대신 인터페이스)."""
    start, answer, scope, finalize = _wire()
    draft, questions = start(
        SpecRequest(project_type=ProjectType.MCP_SERVER, user_request="디자이너 MCP 만들어줘")
    )
    fields = {q.field for q in questions}
    assert "interface" in fields  # 개발 도구 전용 질문
    assert "platform" not in fields  # 앱 전용 질문은 없음

    for q in questions:
        answer(draft.id, q.field, q.options[0] if q.options else "값")
    scope(draft.id, [])
    ctx = finalize(draft.id).context

    assert "인터페이스 설계 (Tool/Resource/Prompt)" in ctx  # 개발 프로필 섹션
    assert "9. 개발 Phase" in ctx  # 개발 일정 → Phase 통합
    assert "11. 이후 확장 계획" in ctx  # 구현 순서 통합으로 12→11섹션
    assert "10. 구현 순서" not in ctx  # 구현 순서 섹션은 Phase 로 흡수됨
    assert "DB 설계" not in ctx  # 앱 섹션은 없음


def test_ml_and_data_pipeline_profiles() -> None:
    """ml_project·data_pipeline 은 각자의 데이터 중심 출력 형식을 쓴다."""
    for ptype, marker in [
        (ProjectType.ML_PROJECT, "모델/방법론"),
        (ProjectType.DATA_PIPELINE, "파이프라인 아키텍처"),
    ]:
        start, answer, scope, finalize = _wire()
        draft, questions = start(SpecRequest(project_type=ptype, user_request="데이터 프로젝트"))
        assert "data_source" in {q.field for q in questions}
        for q in questions:
            answer(draft.id, q.field, q.options[0] if q.options else "값")
        scope(draft.id, [])
        ctx = finalize(draft.id).context
        assert marker in ctx
        assert "화면 목록" not in ctx


def test_work_period_and_headcount_not_asked() -> None:
    """작업 인원(team)·작업 기간(duration)은 어떤 유형에서도 묻지 않는다."""
    start, _answer, _scope, _finalize = _wire()
    for ptype in (
        ProjectType.MESSENGER,
        ProjectType.MCP_SERVER,
        ProjectType.ML_PROJECT,
        ProjectType.DATA_PIPELINE,
        ProjectType.ETC,
    ):
        _draft, questions = start(SpecRequest(project_type=ptype, user_request="테스트"))
        fields = {q.field for q in questions}
        assert "duration" not in fields
        assert "team" not in fields


def test_custom_stack_defers_to_llm() -> None:
    """tech_stack='직접 지정'이면 서버가 기본 스택을 박지 않고 지시문을 남긴다."""
    start, answer, scope, finalize = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.MESSENGER, user_request="메신저"))
    for field, value in {**_ALL_ANSWERS, "tech_stack": "직접 지정"}.items():
        answer(draft.id, field, value)
    scope(draft.id, [])

    result = finalize(draft.id)

    assert result.draft.tech_stack == {}
    assert "직접 지정" in result.context
    assert "Flutter" not in result.context  # 기본 스택을 추측해 박지 않음.
