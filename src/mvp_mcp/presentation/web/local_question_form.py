"""MCP 클라이언트에 네이티브 질문 UI가 없을 때 쓰는 로컬 웹 질문 화면."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import webbrowser
from dataclasses import dataclass, field
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from mvp_mcp.domain.spec.model import Question, WebQuestionAnswer

_LOGGER = logging.getLogger(__name__)
_MAX_BODY_BYTES = 8_192


@dataclass
class _PendingQuestion:
    question: Question
    event: threading.Event = field(default_factory=threading.Event)
    answer: WebQuestionAnswer | None = None


class LocalWebQuestionForm:
    """루프백 HTTP 화면을 열고 사용자 응답을 동기적으로 기다린다."""

    def __init__(self, timeout_seconds: int = 900) -> None:
        self._timeout_seconds = timeout_seconds
        self._pending: dict[str, _PendingQuestion] = {}
        self._lock = threading.Lock()
        self._browser_opened = False
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="mvp-mcp-question-ui",
            daemon=True,
        )
        self._thread.start()

    def ask(self, question: Question) -> WebQuestionAnswer:
        """브라우저를 열고 해당 질문의 한 번뿐인 응답을 기다린다."""
        token = secrets.token_urlsafe(24)
        pending = _PendingQuestion(question=question)
        with self._lock:
            self._pending[token] = pending
        url = f"http://127.0.0.1:{self._server.server_port}/questions/{token}"
        with self._lock:
            should_open_browser = not self._browser_opened
            self._browser_opened = True
        if should_open_browser and not webbrowser.open(url):
            with self._lock:
                self._browser_opened = False
            self._discard(token)
            raise OSError("로컬 브라우저를 열 수 없습니다.")
        if not pending.event.wait(timeout=self._timeout_seconds):
            self._discard(token)
            raise TimeoutError("질문 응답 대기 시간이 초과되었습니다.")
        answer = self._discard(token).answer
        if answer is None:
            raise RuntimeError("질문 응답을 찾을 수 없습니다.")
        return answer

    def close(self) -> None:
        """테스트 또는 서버 종료 시 루프백 서버를 정리한다."""
        self._server.shutdown()
        self._server.server_close()

    def _discard(self, token: str) -> _PendingQuestion:
        with self._lock:
            pending = self._pending.pop(token, None)
        if pending is None:
            raise RuntimeError("질문 세션을 찾을 수 없습니다.")
        return pending

    def _get(self, token: str) -> _PendingQuestion | None:
        with self._lock:
            return self._pending.get(token)

    def _submit(self, token: str, payload: dict[str, Any]) -> str:
        pending = self._get(token)
        if pending is None:
            raise ValueError("만료되었거나 이미 처리된 질문입니다.")
        if pending.answer is not None:
            raise ValueError("이미 처리된 질문입니다.")
        value = self._validate_submission(pending.question, payload)
        pending.answer = WebQuestionAnswer(value=value)
        pending.event.set()
        return value

    @staticmethod
    def _validate_submission(question: Question, payload: dict[str, Any]) -> str:
        choice = payload.get("choice")
        other_text = payload.get("other_text")
        if not isinstance(choice, str):
            raise ValueError("선택값이 올바르지 않습니다.")
        if not question.options:
            value = choice.strip()
            if not value:
                raise ValueError("답변을 입력해주세요.")
            return value
        if choice == "__other__":
            if (
                not question.allows_other
                or not isinstance(other_text, str)
                or not other_text.strip()
            ):
                raise ValueError("기타 상세 내용을 입력해주세요.")
            return f"기타: {other_text.strip()}"
        if choice not in question.options:
            raise ValueError("제시된 선택지 중 하나를 골라주세요.")
        if choice == "기타":
            if not isinstance(other_text, str) or not other_text.strip():
                raise ValueError("기타 상세 내용을 입력해주세요.")
            return f"기타: {other_text.strip()}"
        return choice

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        form = self

        class QuestionHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                if urlparse(self.path).path == "/active-question":
                    self._send_active_question()
                    return
                token = self._token()
                if token is None:
                    self._send(HTTPStatus.NOT_FOUND, "질문 세션을 찾을 수 없습니다.", "text/plain")
                    return
                pending = form._get(token)
                if pending is None:
                    self._send(HTTPStatus.NOT_FOUND, "질문 세션을 찾을 수 없습니다.", "text/plain")
                    return
                self._send(
                    HTTPStatus.OK,
                    _render_page(pending.question, token),
                    "text/html; charset=utf-8",
                )

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
                token = self._token()
                if token is None:
                    self._send_json(
                        HTTPStatus.NOT_FOUND, {"error": "질문 세션을 찾을 수 없습니다."}
                    )
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 1 or length > _MAX_BODY_BYTES:
                        raise ValueError("요청 본문 크기가 올바르지 않습니다.")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("요청 형식이 올바르지 않습니다.")
                    value = form._submit(token, payload)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send_json(HTTPStatus.OK, {"value": value})

            def log_message(self, message: str, *args: object) -> None:
                _LOGGER.debug("local question UI: " + message, *args)

            def _token(self) -> str | None:
                path = urlparse(self.path).path
                prefix = "/questions/"
                if not path.startswith(prefix):
                    return None
                token = path.removeprefix(prefix)
                return token if token and "/" not in token else None

            def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_json(self, status: HTTPStatus, body: dict[str, str]) -> None:
                self._send(
                    status,
                    json.dumps(body, ensure_ascii=False),
                    "application/json; charset=utf-8",
                )

            def _send_active_question(self) -> None:
                with form._lock:
                    token = next(iter(form._pending), None)
                if token is None:
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.end_headers()
                    return
                self._send_json(HTTPStatus.OK, {"token": token})

        return QuestionHandler


def _render_page(question: Question, token: str) -> str:
    options = "".join(
        f'<button class="choice" type="button" data-choice="{escape(option, quote=True)}">'
        f"{escape(option)}</button>"
        for option in question.options
    )
    if question.options and question.allows_other and "기타" not in question.options:
        options += '<button class="choice" type="button" data-choice="__other__">기타</button>'
    answer_control = ""
    if not question.options:
        answer_control = '<textarea id="free-answer" placeholder="답변을 입력해주세요."></textarea>'
    description = ""
    if question.description:
        description = f'<p class="description">{escape(question.description)}</p>'
    hint = f'<p class="hint">힌트: {escape(question.hint)}</p>' if question.hint else ""
    html = _PAGE_TEMPLATE.replace("__TITLE__", escape(question.text))
    html = html.replace("__DESCRIPTION__", description).replace("__HINT__", hint)
    html = html.replace("__OPTIONS__", options).replace("__ANSWER_CONTROL__", answer_control)
    html = html.replace("__TOKEN__", token)
    return html.replace("__CHOICE_MODE__", str(bool(question.options)).lower())


_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MVP 기획 인터뷰</title><style>
body{margin:0;background:#f5f7fb;color:#1c2430;font:16px system-ui,sans-serif}
main{max-width:680px;margin:48px auto;padding:32px;background:#fff;
border:1px solid #dce3ed;border-radius:16px}
.step,.description,.hint{color:#52657c}.step{font-size:14px}h1{font-size:24px;line-height:1.4}
.choices{display:grid;gap:10px}.choice,textarea{box-sizing:border-box;width:100%;padding:15px;
text-align:left;border:1px solid #bdc9d8;border-radius:10px;background:#fff;
color:inherit;font:inherit}
.choice.selected{border-color:#1769e0;background:#edf5ff}textarea{min-height:110px;resize:vertical}
#other{display:none;margin-top:14px}#other.visible{display:block}label{display:block;margin-bottom:7px;font-weight:600}
.footer{display:flex;justify-content:flex-end;margin-top:24px}#next{padding:11px 18px;border:0;
border-radius:9px;background:#1769e0;color:white;font:inherit;font-weight:600}
#next:disabled{opacity:.45}#error{min-height:20px;color:#b42318}
</style></head><body><main><p class="step">MVP 기획 인터뷰</p><h1>__TITLE__</h1>
__DESCRIPTION____HINT__<div class="choices">__OPTIONS__</div>__ANSWER_CONTROL__
<div id="other"><label for="other-answer">기타 상세 내용</label>
<textarea id="other-answer" placeholder="원하시는 내용을 입력해주세요."></textarea></div>
<div class="footer"><button id="next" type="button" disabled>다음</button></div>
<p id="error" role="alert"></p></main><script>
const choiceMode=__CHOICE_MODE__;let selected='';
const other=document.querySelector('#other'),next=document.querySelector('#next');
const error=document.querySelector('#error'),free=document.querySelector('#free-answer');
const otherInput=document.querySelector('#other-answer');
document.querySelectorAll('.choice').forEach(button=>button.onclick=()=>{
selected=button.dataset.choice;document.querySelectorAll('.choice').forEach(item=>item.classList.toggle('selected',item===button));
const show=selected==='기타'||selected==='__other__';other.classList.toggle('visible',show);
next.disabled=show&&!otherInput.value.trim();if(show)otherInput.focus();});
if(free)free.oninput=()=>next.disabled=!free.value.trim();
if(otherInput)otherInput.oninput=()=>{if(selected==='기타'||selected==='__other__')next.disabled=!otherInput.value.trim();};
next.onclick=async()=>{const choice=choiceMode?selected:free.value;
const response=await fetch('/questions/__TOKEN__',{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({choice,other_text:otherInput?otherInput.value:''})});
const body=await response.json();if(!response.ok){error.textContent=body.error;return;}
document.querySelector('main').innerHTML='<p class="step">MVP 기획 인터뷰</p>'+
'<h1>답변이 반영되었습니다.</h1><p>AI 대화가 다음 질문을 계속 진행합니다.</p>';};
setInterval(async()=>{const response=await fetch('/active-question');
if(response.status!==200)return;const active=await response.json();
if(!location.pathname.endsWith(active.token))location.assign('/questions/'+active.token);},500);
</script></body></html>"""
