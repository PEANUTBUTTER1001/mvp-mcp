"""세션 시작·질문·MVP 범위 유스케이스 테스트."""

from __future__ import annotations

from datetime import datetime

from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.model import ProjectType, SpecRequest
from mvp_mcp.domain.spec.usecase import AnswerQuestionUseCase, ScopeMvpUseCase, StartSpecUseCase


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1)


def _wire() -> tuple[StartSpecUseCase, AnswerQuestionUseCase, ScopeMvpUseCase]:
    templates = InMemoryTemplateRepository()
    specs = InMemorySpecRepository()
    return (
        StartSpecUseCase(templates, specs, _FixedClock()),
        AnswerQuestionUseCase(specs, templates),
        ScopeMvpUseCase(specs, templates),
    )


def test_start_and_answer_only_ask_missing_template_fields() -> None:
    start, answer, _scope = _wire()
    draft, questions = start(
        SpecRequest(
            project_type=ProjectType.MESSENGER,
            user_request="메신저 만들어줘",
            known_info={"platform": "모바일"},
        )
    )
    assert draft.id is not None
    assert "platform" not in {item.field for item in questions}
    _, remaining = answer(draft.id, "purpose", "개인 프로젝트")
    assert "purpose" not in {item.field for item in remaining}


def test_scope_cuts_excluded_features() -> None:
    start, _answer, scope = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.MESSENGER, user_request="메신저"))
    scoped = scope(draft.id, ["영상통화", "1:1 채팅"])
    assert "영상통화" not in scoped.features
    assert any("영상통화" in item for item in scoped.deferred)
    assert "1:1 채팅" in scoped.features


def test_etc_fallback_caps_features() -> None:
    start, _answer, scope = _wire()
    draft, _ = start(SpecRequest(project_type=ProjectType.ETC, user_request="새 서비스"))
    scoped = scope(draft.id, [f"기능{i}" for i in range(1, 10)])
    assert len(scoped.features) == 7
    assert len(scoped.deferred) == 2


def test_intake_questions_cover_intent_discovery() -> None:
    from mvp_mcp.domain.spec.query import GetIntakeQuestionsUseCase

    questions = GetIntakeQuestionsUseCase()()
    assert {"problem", "goal", "deliverable", "constraints"} <= {item.field for item in questions}
    assert all(item.description and item.hint for item in questions)
