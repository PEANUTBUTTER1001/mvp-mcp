"""기본 인터뷰 경로인 단일 페이지 웹 Wizard."""

# ruff: noqa: E501

from __future__ import annotations

import json
import logging
import secrets
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from mvp_mcp.domain.spec.documentation_model import DocumentationIntake
from mvp_mcp.domain.spec.model import ProjectType, WebSurveyAnswer

_LOGGER = logging.getLogger(__name__)
_MAX_BODY_BYTES = 32_768


@dataclass
class _PendingSurvey:
    user_request: str
    event: threading.Event = field(default_factory=threading.Event)
    answer: WebSurveyAnswer | None = None


class LocalWebSurveyForm:
    """루프백 브라우저에서 한 번에 설문을 받고 제출값을 기다린다."""

    def __init__(
        self,
        timeout_seconds: int = 1800,
        on_submit: Callable[[str, WebSurveyAnswer], None] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._on_submit = on_submit
        self._pending: dict[str, _PendingSurvey] = {}
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="mvp-mcp-survey-ui", daemon=True
        )
        self._thread.start()

    def ask(self, user_request: str) -> WebSurveyAnswer:
        token = secrets.token_urlsafe(24)
        pending = _PendingSurvey(user_request=user_request)
        with self._lock:
            self._pending[token] = pending
        url = f"http://127.0.0.1:{self._server.server_port}/survey/{token}"
        if not webbrowser.open(url):
            self._discard(token)
            raise OSError("로컬 브라우저를 열 수 없습니다.")
        if not pending.event.wait(timeout=self._timeout_seconds):
            self._discard(token)
            raise TimeoutError("설문 응답 대기 시간이 초과되었습니다.")
        answer = self._discard(token).answer
        if answer is None:
            raise RuntimeError("설문 응답을 찾을 수 없습니다.")
        return answer

    def open(self, session_id: str, user_request: str) -> str:
        """비차단 세션 URL을 열고 즉시 반환한다."""
        pending = _PendingSurvey(user_request=user_request)
        with self._lock:
            self._pending[session_id] = pending
        url = f"http://127.0.0.1:{self._server.server_port}/survey/{session_id}"
        if not webbrowser.open(url):
            self._discard(session_id)
            raise OSError("로컬 브라우저를 열 수 없습니다.")
        return url

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _discard(self, token: str) -> _PendingSurvey:
        with self._lock:
            pending = self._pending.pop(token, None)
        if pending is None:
            raise RuntimeError("설문 세션을 찾을 수 없습니다.")
        return pending

    def _get(self, token: str) -> _PendingSurvey | None:
        with self._lock:
            return self._pending.get(token)

    def _submit(self, token: str, payload: dict[str, Any]) -> WebSurveyAnswer:
        pending = self._get(token)
        if pending is None:
            raise ValueError("만료되었거나 이미 처리된 설문입니다.")
        if pending.answer is not None:
            raise ValueError("이미 제출된 설문입니다.")
        answer = self._validate_submission(pending.user_request, payload)
        if self._on_submit is not None:
            self._on_submit(token, answer)
            self._discard(token)
            return answer
        pending.answer = answer
        pending.event.set()
        return answer

    @staticmethod
    def _validate_submission(user_request: str, payload: dict[str, Any]) -> WebSurveyAnswer:
        raw_type = payload.get("project_type")
        type_map = {
            "app": ProjectType.ETC,
            "other": ProjectType.ETC,
            "mcp": ProjectType.MCP_SERVER,
            "ml": ProjectType.ML_PROJECT,
            "data": ProjectType.DATA_PIPELINE,
        }
        if raw_type not in type_map:
            raise ValueError("결과물 유형을 선택해주세요.")
        features = payload.get("requested_features", "")
        if not isinstance(features, str):
            raise ValueError("MVP 기능 입력이 올바르지 않습니다.")

        def choices(name: str) -> list[str]:
            value = payload.get(name, [])
            if isinstance(value, str):
                return [value] if value else []
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return value
            raise ValueError(f"{name} 선택값이 올바르지 않습니다.")

        documentation_values = {
            "change_type": payload.get("change_type", "신규 개발"),
            "deployment_scope": payload.get("deployment_scope", "로컬 실험"),
            "ui_surfaces": choices("ui_surfaces") or ["화면 없음"],
            "http_api_mode": payload.get("http_api_mode", "없음"),
            "storage_need": payload.get("storage_need", "불필요"),
            "storage_types": choices("storage_types"),
            "existing_data_change": payload.get("existing_data_change", "변경하지 않음"),
            "auth_capabilities": choices("auth_capabilities") or ["없음"],
            "auth_methods": choices("auth_methods"),
            "personal_data_types": choices("personal_data_types") or ["없음"],
            "payment_risk": payload.get("payment_risk", "없음"),
            "other_risks": choices("other_risks") or ["없음"],
            "recovery_need": payload.get("recovery_need", "불필요"),
            "prototype_preview": payload.get("prototype_preview", "불필요"),
        }
        if "change_type" in payload:
            required_multi = (
                "ui_surfaces",
                "auth_capabilities",
                "personal_data_types",
                "other_risks",
            )
            missing_multi = [name for name in required_multi if not choices(name)]
            if missing_multi:
                raise ValueError("다중 선택 필수 항목이 비어 있습니다: " + ", ".join(missing_multi))
        documentation = DocumentationIntake.model_validate(documentation_values)
        ui_values = documentation_values["ui_surfaces"]
        auth_values = documentation_values["auth_methods"]
        values = {
            "project_type": type_map[raw_type],
            "user_request": payload.get("user_request", user_request),
            "problem": payload.get("problem", ""),
            "goal": payload.get("goal", ""),
            "purpose": payload.get("purpose", ""),
            "tech_stack": payload.get("tech_stack", ""),
            "custom_tech_stack": payload.get("custom_tech_stack", ""),
            "requested_features": features.replace("\n", ",").split(","),
            "constraints": payload.get("constraints", ""),
            "reference": payload.get("reference", ""),
            "platform": payload.get("platform", "") or ", ".join(ui_values),
            "auth_method": payload.get("auth_method", "") or ", ".join(auth_values) or "없음",
            "realtime": payload.get("realtime", ""),
            "interface": payload.get("interface", ""),
            "runtime": payload.get("runtime", ""),
            "distribution": payload.get("distribution", ""),
            "data_source": payload.get("data_source", ""),
            "task_type": payload.get("task_type", ""),
            "deployment_target": payload.get("deployment_target", ""),
            "target_users": payload.get("target_users", ""),
            "core_workflows": payload.get("core_workflows", ""),
            "data_and_rules": payload.get("data_and_rules", ""),
            "required_screens": payload.get("required_screens", ""),
            "failure_behavior": payload.get("failure_behavior", ""),
            "success_metrics": payload.get("success_metrics", ""),
            "open_decisions": payload.get("open_decisions", ""),
            "documentation": documentation,
        }
        try:
            return WebSurveyAnswer.model_validate(values)
        except ValidationError as exc:
            raise ValueError("설문의 필수 항목을 모두 작성해주세요.") from exc

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        form = self

        class SurveyHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                token = self._token()
                pending = form._get(token) if token else None
                if pending is None:
                    self._send(HTTPStatus.NOT_FOUND, "설문 세션을 찾을 수 없습니다.", "text/plain")
                    return
                assert token is not None
                self._send(
                    HTTPStatus.OK,
                    _render_page(pending.user_request, token),
                    "text/html; charset=utf-8",
                )

            def do_POST(self) -> None:  # noqa: N802
                token = self._token()
                if token is None:
                    self._send_json(
                        HTTPStatus.NOT_FOUND, {"error": "설문 세션을 찾을 수 없습니다."}
                    )
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 1 or length > _MAX_BODY_BYTES:
                        raise ValueError("요청 본문 크기가 올바르지 않습니다.")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("요청 형식이 올바르지 않습니다.")
                    answer = form._submit(token, payload)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send_json(HTTPStatus.OK, {"project_type": answer.project_type.value})

            def log_message(self, message: str, *args: object) -> None:
                _LOGGER.debug("local survey UI: " + message, *args)

            def _token(self) -> str | None:
                path = urlparse(self.path).path
                prefix = "/survey/"
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
                    status, json.dumps(body, ensure_ascii=False), "application/json; charset=utf-8"
                )

        return SurveyHandler


def _render_page(user_request: str, token: str) -> str:
    page = _PAGE_TEMPLATE.replace("__TOKEN__", token).replace("__REQUEST__", escape(user_request))
    page = page.replace(
        "MVP 범위와 두 개의 명세 문서를 생성합니다.", "MVP 범위와 6개 실행 계약 문서를 생성합니다."
    )
    page = page.replace(
        "기획서·구현서를 생성하고 있습니다.", "6개 실행 계약 문서를 생성하고 있습니다."
    )
    return (
        page.replace(
            '<div class="error"',
            _GOVERNANCE_SURVEY + _DETAIL_SURVEY + '<div class="error"',
        )
        .replace("</head>", _CHOICE_STYLE + "</head>")
        .replace("</body>", _CHOICE_ENHANCEMENT + "</body>")
    )


_CHOICE_STYLE = """<style>
.choice-hint{color:var(--m);display:block;font-size:13px;margin:0 0 8px}
.choice-group{display:flex;flex-wrap:wrap;gap:8px}
.choice{align-items:center;border:1px solid #bdc9d8;border-radius:999px;cursor:pointer;display:inline-flex;gap:7px;padding:8px 11px}
.choice:has(input:checked){background:#eaf1ff;border-color:var(--b);color:#0b3c9d;font-weight:700}
.choice input{accent-color:var(--b);height:16px;margin:0;padding:0;width:16px}
.choice.disabled{cursor:not-allowed;opacity:.45}
</style>"""


_DETAIL_SURVEY = """<section class="section"><h2>5. 실행 계약 상세 정보</h2><p class="desc">아래 답변은 화면·데이터·예외·테스트가 포함된 상세 실행 문서를 만드는 기준입니다. 모르는 내용은 마지막 항목에 남겨주세요.</p><div class="grid"><label class="field"><b>대상 사용자와 사용 맥락</b><textarea name="target_users" placeholder="누가, 언제, 얼마나 자주 사용하나요?"></textarea></label><label class="field"><b>핵심 사용자 흐름</b><textarea name="core_workflows" placeholder="예: 기록 추가 → 검토 → 저장 → 다시 찾기"></textarea></label><label class="field"><b>저장 데이터와 업무 규칙</b><textarea name="data_and_rules" placeholder="저장할 항목, 수정/삭제/정렬/검증 규칙"></textarea></label><label class="field"><b>필수 화면과 상태</b><textarea name="required_screens" placeholder="목록, 입력, 상세와 빈 화면·오류 화면"></textarea></label><label class="field"><b>실패 시 기대 동작</b><textarea name="failure_behavior" placeholder="입력 오류, 저장 실패, 외부 연동 실패 시 복구 방법"></textarea></label><label class="field"><b>성공 지표</b><textarea name="success_metrics" placeholder="완료를 어떻게 판단하나요?"></textarea></label><label class="field full"><b>미확정 결정</b><textarea name="open_decisions" placeholder="아직 결정하지 못한 기술, 데이터, 정책 항목"></textarea></label></div></section>"""


_GOVERNANCE_SURVEY = """<section class="section"><h2>4. 문서·위험·프로토타입 설정</h2><p class="desc">답변에 따라 기본 6문서와 보안·마이그레이션 문서, OpenAPI, HTML 프로토타입을 선택합니다.</p><div class="grid">
<label class="field req">작업 성격<select name="change_type" required><option value="">선택해주세요</option><option>신규 개발</option><option>기존 시스템 변경</option></select></label>
<label class="field req">사용·배포 범위<select name="deployment_scope" required><option value="">선택해주세요</option><option>로컬 실험</option><option>내부 사용</option><option>실제 사용자 배포</option></select></label>
<label class="field full req">사용자 화면<select name="ui_surfaces" multiple><option>웹</option><option>모바일</option><option>관리자 UI</option><option>화면 없음</option></select></label>
<label class="field req">HTTP API<select name="http_api_mode" required><option value="">선택해주세요</option><option>신규 제공</option><option>기존 API 변경</option><option>없음</option></select></label>
<label class="field req">데이터 저장<select name="storage_need" required><option value="">선택해주세요</option><option>필요</option><option>불필요</option></select></label>
<label class="field" id="storage-types" hidden>저장소 종류<select name="storage_types" multiple><option>DB</option><option>파일</option><option>외부 저장소</option></select></label>
<label class="field req">기존 데이터 변경<select name="existing_data_change" required><option value="">선택해주세요</option><option>변경함</option><option>변경하지 않음</option></select></label>
<label class="field full req">인증·권한<select name="auth_capabilities" multiple><option>로그인</option><option>세션</option><option>역할·권한</option><option>계정 복구</option><option>없음</option><option>계획 미정</option></select></label>
<label class="field full" id="auth-methods" hidden>로그인 방식<select name="auth_methods" multiple><option>이메일/비밀번호</option><option>소셜 로그인</option><option>패스키</option><option>SSO</option><option>기타</option><option>계획 미정</option></select></label>
<label class="field full req">개인정보<select name="personal_data_types" multiple><option>연락처</option><option>계정 식별자</option><option>프로필</option><option>주소</option><option>위치</option><option>사용자 콘텐츠</option><option>없음</option><option>계획 미정</option></select></label>
<label class="field req">결제·고가치 자산<select name="payment_risk" required><option value="">선택해주세요</option><option>있음</option><option>없음</option><option>계획 미정</option></select></label>
<label class="field full req">기타 위험<select name="other_risks" multiple><option>위치정보</option><option>파일 업로드</option><option>외부 입력</option><option>비밀정보</option><option>공개 API</option><option>없음</option><option>계획 미정</option></select></label>
<label class="field req">운영 복구<select name="recovery_need" required><option value="">선택해주세요</option><option>필요</option><option>불필요</option><option>계획 미정</option></select></label>
<label class="field req">HTML 프로토타입 보기<select name="prototype_preview" required><option value="">선택해주세요</option><option>필요</option><option>불필요</option></select></label>
</div></section>"""


_CHOICE_ENHANCEMENT = """<script>
(() => {
  const form = document.querySelector('#survey');
  let sequence = 0;

  document.querySelectorAll('select').forEach(select => {
    const group = document.createElement('span');
    group.className = 'choice-group';
    group.dataset.multiple = String(select.multiple);
    const placeholder = select.querySelector('option[value=""]');
    if (placeholder) {
      const hint = document.createElement('span');
      hint.className = 'choice-hint';
      hint.textContent = placeholder.textContent;
      group.append(hint);
    }
    Array.from(select.options).filter(option => option.value).forEach(option => {
      const choice = document.createElement('span');
      choice.className = 'choice';
      const input = document.createElement('input');
      input.type = select.multiple ? 'checkbox' : 'radio';
      input.name = select.name;
      input.value = option.value;
      input.disabled = select.disabled;
      input.required = select.required && !select.multiple;
      input.id = `choice-${select.name}-${sequence++}`;
      input.setAttribute('aria-label', option.textContent.trim());
      const text = document.createElement('span');
      text.textContent = option.textContent;
      choice.append(input, text);
      choice.addEventListener('click', event => {
        if (event.target !== input && !input.disabled) {
          input.checked = select.multiple ? !input.checked : true;
          input.dispatchEvent(new Event('change', {bubbles: true}));
        }
      });
      group.append(choice);
    });
    select.replaceWith(group);
  });

  const selectedProjectType = () =>
    form.querySelector('input[name="project_type"]:checked')?.value || '';
  const updateCustomTechStack = () => {
    const field = document.querySelector('#custom-tech-stack');
    const input = field.querySelector('textarea');
    const direct = form.querySelector('input[name="tech_stack"]:checked')?.value === '직접 지정';
    field.hidden = !direct;
    input.required = direct;
    input.disabled = !direct;
    if (!direct) input.value = '';
  };
  const updateBranches = () => {
    document.querySelectorAll('.branch').forEach(branch => {
      const active = branch.dataset.type.split(' ').includes(selectedProjectType());
      branch.classList.toggle('show', active);
      branch.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(input => {
        input.disabled = !active;
        input.required = active && input.type === 'radio';
        input.closest('.choice').classList.toggle('disabled', !active);
        if (!active) input.checked = false;
      });
    });
  };
  const updateConditionalFields = () => {
    const storage = form.querySelector('input[name="storage_need"]:checked')?.value === '필요';
    const storageField = document.querySelector('#storage-types');
    storageField.hidden = !storage;
    storageField.querySelectorAll('input').forEach(input => { input.disabled = !storage; if (!storage) input.checked = false; });
    const login = [...form.querySelectorAll('input[name="auth_capabilities"]:checked')].some(input => input.value === '로그인');
    const authField = document.querySelector('#auth-methods');
    authField.hidden = !login;
    authField.querySelectorAll('input').forEach(input => { input.disabled = !login; if (!login) input.checked = false; });
  };
  const enforceExclusive = event => {
    if (event.target.type !== 'checkbox' || !event.target.checked) return;
    const exclusive = ['없음', '계획 미정'];
    const group = [...form.querySelectorAll(`input[name="${event.target.name}"]`)];
    if (exclusive.includes(event.target.value)) group.forEach(input => { if (input !== event.target) input.checked = false; });
    else group.filter(input => exclusive.includes(input.value)).forEach(input => { input.checked = false; });
  };
  form.addEventListener('change', event => {
    enforceExclusive(event);
    if (event.target.name === 'project_type') updateBranches();
    if (event.target.name === 'tech_stack') updateCustomTechStack();
    if (['storage_need', 'auth_capabilities'].includes(event.target.name)) updateConditionalFields();
  });
  updateBranches();
  updateCustomTechStack();
  updateConditionalFields();
})();
</script>"""


_PAGE_TEMPLATE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MVP 요구사항 설문</title><style>
:root{--b:#155eef;--i:#172033;--m:#62708a;--l:#dce4ef}*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:var(--i);font:16px system-ui,sans-serif}header{background:#155eef;color:#fff;padding:28px}header div,main{max-width:820px;margin:auto}header h1{margin:0;font-size:24px}header p{margin:7px 0 0;color:#dbeafe}main{margin-top:25px;margin-bottom:50px;background:#fff;border:1px solid var(--l);border-radius:16px;padding:28px}.section{padding:22px 0;border-bottom:1px solid #e8edf4}.section:last-child{border:0}h2{font-size:19px;margin:0 0 5px}.desc{color:var(--m);margin:0 0 16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.field{display:block}.full{grid-column:1/-1}label{display:block;font-weight:700;margin-bottom:6px}.req:after{content:' *';color:#d92d20}input,textarea,select{width:100%;border:1px solid #bdc9d8;border-radius:9px;padding:11px;font:inherit}textarea{min-height:88px;resize:vertical}.branch{display:none;margin-top:17px;padding:18px;border:1px solid #b9ddd7;border-radius:12px;background:#f1fbf9}.branch.show{display:block}.error{display:none;margin-top:20px;padding:12px;color:#a41c14;background:#fff1f0;border-radius:8px}.error.show{display:block}.actions{display:flex;justify-content:space-between;align-items:center;gap:14px;padding-top:25px}.actions span{color:var(--m);font-size:13px}.submit{border:0;border-radius:9px;background:var(--b);color:#fff;padding:12px 17px;font:inherit;font-weight:800;cursor:pointer}@media(max-width:620px){main{margin:0;border-radius:0;border:0}.grid{grid-template-columns:1fr}.full{grid-column:auto}.actions{align-items:stretch;flex-direction:column}.submit{width:100%}}</style></head><body>
<header><div><h1>MVP 요구사항 설문</h1><p>한 번 작성하면 MVP 범위와 두 개의 명세 문서를 생성합니다.</p></div></header><main><form id="survey" novalidate>
<section class="section"><h2>1. 프로젝트 개요</h2><p class="desc">무엇을, 왜 만들려는지 적어주세요.</p><div class="grid"><div class="field full"><label class="req">만들려는 서비스 또는 프로그램<input name="user_request" required value="__REQUEST__"></label></div><div class="field"><label class="req">현재 문제 또는 불편<textarea name="problem" required></textarea></label></div><div class="field"><label class="req">이루고 싶은 목표<textarea name="goal" required></textarea></label></div></div></section>
<section class="section"><h2>2. 결과물과 기본 조건</h2><p class="desc">선택한 유형에 맞는 항목만 나타납니다.</p><div class="grid"><div class="field"><label class="req">결과물 유형<select name="project_type" id="type" required><option value="">선택해주세요</option><option value="app">앱/웹 서비스</option><option value="mcp">개발 도구/MCP</option><option value="ml">데이터/ML</option><option value="data">데이터 파이프라인</option><option value="other">기타</option></select></label></div><div class="field"><label class="req">개발 목적<select name="purpose" required><option value="">선택해주세요</option><option>개인 프로젝트</option><option>회사 프로젝트</option><option>포트폴리오</option><option>상용 서비스</option></select></label></div><div class="field"><label class="req">기술 스택<select name="tech_stack" required><option value="">선택해주세요</option><option>기본 스택 사용</option><option>직접 지정</option></select></label></div><div class="field"><label>제약사항<textarea name="constraints" placeholder="기간, 예산, 기술, 보안·규정 등"></textarea></label></div><label class="field full" id="custom-tech-stack" hidden><b>직접 지정 기술 스택</b><textarea name="custom_tech_stack" placeholder="예: Next.js, FastAPI, PostgreSQL, Docker"></textarea></label></div>
<div class="branch" data-type="app other"><h3>앱/웹 서비스 항목</h3><div class="grid"><label class="field full req">실시간 기능<select name="realtime"><option value="">선택해주세요</option><option>필요</option><option>불필요</option></select></label></div></div>
<div class="branch" data-type="mcp"><h3>MCP/개발 도구 항목</h3><div class="grid"><label class="field req">제공 인터페이스<select name="interface"><option value="">선택해주세요</option><option>MCP 도구</option><option>CLI</option><option>라이브러리 API</option><option>HTTP API</option></select></label><label class="field req">실행 환경/언어<select name="runtime"><option value="">선택해주세요</option><option>Python</option><option>Node.js</option><option>Go</option></select></label><label class="field full req">배포 방식<select name="distribution"><option value="">선택해주세요</option><option>PyPI/npm</option><option>Docker</option><option>소스 직접</option></select></label></div></div>
<div class="branch" data-type="ml"><h3>데이터/ML 항목</h3><div class="grid"><label class="field req">데이터 출처<select name="data_source"><option value="">선택해주세요</option><option>CSV/파일</option><option>DB</option><option>API 수집</option><option>스트리밍</option></select></label><label class="field req">문제 유형<select name="task_type"><option value="">선택해주세요</option><option>분류</option><option>회귀</option><option>생성</option><option>추천</option><option>탐색 분석</option></select></label><label class="field full req">산출물 형태<select name="deployment_target"><option value="">선택해주세요</option><option>배치 파이프라인</option><option>실시간 API</option><option>노트북 리포트</option></select></label></div></div>
<div class="branch" data-type="data"><h3>데이터 파이프라인 항목</h3><div class="grid"><label class="field req">데이터 출처<select name="data_source"><option value="">선택해주세요</option><option>CSV/파일</option><option>DB</option><option>API 수집</option><option>스트리밍</option></select></label><label class="field req">산출물 형태<select name="deployment_target"><option value="">선택해주세요</option><option>배치 파이프라인</option><option>실시간 API</option><option>노트북 리포트</option></select></label></div></div></section>
<section class="section"><h2>3. MVP 범위</h2><p class="desc">초기 버전에 꼭 필요한 기능만 적어주세요.</p><div class="grid"><label class="field full req">꼭 포함할 기능<textarea name="requested_features" required placeholder="예: 식당 등록, 평가 체크리스트, 후기 작성, 기록 조회"></textarea></label><label class="field full">참고 서비스 또는 추가 요청<textarea name="reference"></textarea></label></div></section><div class="error" id="error" role="alert"></div><div class="actions"><span>제출 뒤 답변을 검증하고 문서 생성을 시작합니다.</span><button class="submit">설문 제출</button></div></form></main><script>
const form=document.querySelector('#survey'),type=document.querySelector('#type'),error=document.querySelector('#error');function showBranches(){document.querySelectorAll('.branch').forEach(x=>{const active=x.dataset.type.split(' ').includes(type.value);x.classList.toggle('show',active);x.querySelectorAll('select').forEach(y=>{y.required=active;y.disabled=!active})})}type.onchange=showBranches;showBranches();form.onsubmit=async e=>{e.preventDefault();error.classList.remove('show');if(!form.reportValidity())return;const data=new FormData(form),values={};for(const [key,value] of data.entries()){if(values[key]===undefined)values[key]=value;else if(Array.isArray(values[key]))values[key].push(value);else values[key]=[values[key],value]}const response=await fetch('/survey/__TOKEN__',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});const body=await response.json();if(!response.ok){error.textContent=body.error;error.classList.add('show');return}document.querySelector('main').textContent='설문이 제출되었습니다. 문서 계약을 검증하고 preview를 준비합니다.'};</script></body></html>"""
