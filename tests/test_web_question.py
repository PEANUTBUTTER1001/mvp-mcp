"""네이티브 UI 미지원 시 사용하는 웹 질문 흐름 테스트."""

from __future__ import annotations

import json
import threading
from urllib.request import Request, urlopen

import pytest

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.model import ProjectType, Question, SpecRequest, WebQuestionAnswer
from mvp_mcp.domain.spec.usecase import AskNextWebQuestionUseCase, StartSpecUseCase
from mvp_mcp.presentation.web.local_question_form import LocalWebQuestionForm, _render_page


class _FixedClock:
    def now(self):  # type: ignore[no-untyped-def]
        from datetime import datetime

        return datetime(2026, 1, 1)


class _AnsweringForm:
    def __init__(self, value: str) -> None:
        self.value = value
        self.questions: list[Question] = []

    def ask(self, question: Question) -> WebQuestionAnswer:
        self.questions.append(question)
        return WebQuestionAnswer(value=self.value)


def _start_messenger() -> tuple[InMemorySpecRepository, InMemoryTemplateRepository, str]:
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    draft, _questions = StartSpecUseCase(templates, specs, _FixedClock())(
        SpecRequest(project_type=ProjectType.MESSENGER, user_request="식당 평가 앱")
    )
    assert draft.id is not None
    return specs, templates, draft.id


def test_web_question_answer_is_applied_and_returns_next_question() -> None:
    specs, templates, spec_id = _start_messenger()
    form = _AnsweringForm("웹")

    draft, remaining, answer = AskNextWebQuestionUseCase(specs, templates, form)(spec_id)

    assert form.questions[0].field == "platform"
    assert answer.value == "웹"
    assert draft.answers["platform"] == "웹"
    assert remaining[0].field == "purpose"


def test_web_question_rejects_value_outside_choices() -> None:
    specs, templates, spec_id = _start_messenger()
    form = _AnsweringForm("허용되지 않은 값")

    with pytest.raises(PipelineError, match="허용되지 않은 선택값"):
        AskNextWebQuestionUseCase(specs, templates, form)(spec_id)


def test_other_requires_detail_and_is_rendered_as_an_input_field() -> None:
    question = Question(
        field="platform",
        text="어떤 플랫폼인가요?",
        options=["웹", "모바일"],
        allows_other=True,
    )

    with pytest.raises(ValueError, match="기타 상세"):
        LocalWebQuestionForm._validate_submission(question, {"choice": "__other__"})

    assert (
        LocalWebQuestionForm._validate_submission(
            question, {"choice": "__other__", "other_text": "키오스크 앱"}
        )
        == "기타: 키오스크 앱"
    )
    page = _render_page(question, "one-time-token")
    assert 'data-choice="__other__"' in page
    assert "기타 상세 내용" in page


def test_local_web_form_waits_for_and_returns_browser_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """웹 UI 응답이 대기 중인 Tool 호출로 돌아오는 루프백 통합 흐름."""
    form = LocalWebQuestionForm(timeout_seconds=2)
    opened = threading.Event()
    urls: list[str] = []
    result: list[WebQuestionAnswer] = []

    def fake_open(url: str) -> bool:
        urls.append(url)
        opened.set()
        return True

    monkeypatch.setattr("mvp_mcp.presentation.web.local_question_form.webbrowser.open", fake_open)
    question = Question(field="platform", text="플랫폼은?", options=["웹"], allows_other=True)
    worker = threading.Thread(target=lambda: result.append(form.ask(question)))
    worker.start()
    try:
        assert opened.wait(timeout=1)
        with urlopen(urls[0], timeout=1) as response:  # noqa: S310 - loopback test URL
            page = response.read().decode("utf-8")
        assert "플랫폼은?" in page

        request = Request(
            urls[0],
            data=json.dumps({"choice": "__other__", "other_text": "키오스크"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=1) as response:  # noqa: S310 - loopback test URL
            assert json.loads(response.read()) == {"value": "기타: 키오스크"}
        worker.join(timeout=1)
        assert result == [WebQuestionAnswer(value="기타: 키오스크")]
    finally:
        form.close()


def test_web_form_opens_browser_only_for_the_first_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 Wizard 프로세스에서는 다음 질문에 새 브라우저 창을 열지 않는다."""
    form = LocalWebQuestionForm(timeout_seconds=2)
    urls: list[str] = []
    opened = threading.Event()

    def fake_open(url: str) -> bool:
        urls.append(url)
        opened.set()
        return True

    monkeypatch.setattr("mvp_mcp.presentation.web.local_question_form.webbrowser.open", fake_open)
    question = Question(field="platform", text="플랫폼은?", options=["웹"])

    def submit_active(value: str) -> None:
        with form._lock:
            token = next(iter(form._pending))
        url = f"http://127.0.0.1:{form._server.server_port}/questions/{token}"
        request = Request(
            url,
            data=json.dumps({"choice": value}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=1):  # noqa: S310 - loopback test URL
            pass

    try:
        first = threading.Thread(target=lambda: form.ask(question))
        first.start()
        assert opened.wait(timeout=1)
        submit_active("웹")
        first.join(timeout=1)

        second = threading.Thread(target=lambda: form.ask(question))
        second.start()
        submit_active("웹")
        second.join(timeout=1)
        assert len(urls) == 1
    finally:
        form.close()
