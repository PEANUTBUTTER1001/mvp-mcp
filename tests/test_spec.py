"""Adaptive Wizard가 공유하는 MVP 범위 판정 회귀 테스트."""

from __future__ import annotations

from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.model import ProjectType, SpecDraft
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase


def _wire() -> tuple[InMemorySpecRepository, ScopeMvpUseCase]:
    templates = InMemoryTemplateRepository()
    specs = InMemorySpecRepository()
    return specs, ScopeMvpUseCase(specs, templates)


def _draft(specs: InMemorySpecRepository, project_type: ProjectType) -> str:
    return specs.save(SpecDraft(project_type=project_type, user_request="새 서비스"))


def test_scope_cuts_excluded_features() -> None:
    specs, scope = _wire()
    spec_id = _draft(specs, ProjectType.MESSENGER)

    scoped = scope(spec_id, ["영상통화", "1:1 채팅"])

    assert "영상통화" not in scoped.features
    assert any("영상통화" in item for item in scoped.deferred)
    assert "1:1 채팅" in scoped.features


def test_etc_fallback_caps_features() -> None:
    specs, scope = _wire()
    spec_id = _draft(specs, ProjectType.ETC)

    scoped = scope(spec_id, [f"기능{index}" for index in range(1, 10)])

    assert len(scoped.features) == 7
    assert len(scoped.deferred) == 2


def test_intake_questions_cover_intent_discovery() -> None:
    from mvp_mcp.domain.spec.query import GetIntakeQuestionsUseCase

    questions = GetIntakeQuestionsUseCase()()

    assert {"problem", "goal", "deliverable", "constraints"} <= {item.field for item in questions}
    assert all(item.description and item.hint for item in questions)
