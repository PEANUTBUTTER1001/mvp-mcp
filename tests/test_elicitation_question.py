"""Codex MCP Elicitation 질문 포맷 테스트."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mvp_mcp.domain.spec.model import Question
from mvp_mcp.presentation.tools.ask_elicitation_question import _answer_value, _form_schema


def test_elicitation_schema_exposes_choices_and_other() -> None:
    question = Question(field="platform", text="플랫폼은?", options=["웹"], allows_other=True)

    schema = _form_schema(question).model_json_schema()

    assert schema["properties"]["answer"]["enum"] == ["웹", "기타"]
    assert _answer_value(question, SimpleNamespace(answer="기타"), "키오스크") == "기타: 키오스크"


def test_elicitation_other_requires_detail() -> None:
    question = Question(field="platform", text="플랫폼은?", options=["웹"], allows_other=True)

    with pytest.raises(ValueError, match="상세"):
        _answer_value(question, SimpleNamespace(answer="기타"))
