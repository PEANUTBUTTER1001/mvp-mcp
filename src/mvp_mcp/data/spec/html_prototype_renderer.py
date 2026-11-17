"""문서 계약에서 외부 의존성 없는 비정본(NON-SSOT) MVP 시제품 HTML을 렌더링한다.

원칙(서비스 흐름 v2 디자인 규칙):
- 계약 뷰어가 아니라 실제 제품처럼 보이고 조작되는 화면을 만든다. 화면 요소 문자열은 키워드
  규칙으로 목록·입력·검색·진행·삭제 확인·버튼 UI가 된다.
- 단일 열, 카드 중첩 없음. 네 면 테두리는 입력·버튼·대화상자·접는 패널에만 쓰고, 배지는 상태
  값에만 쓴다.
- 사용자 화면에는 개발자 용어를 두지 않는다. 시제품 성격·계약 해시·원본 문서·사용자 흐름·
  오류 복구·화면 상태 미리보기·고대비 전환은 기본으로 닫힌 설명 패널에 둔다.
- 색은 :root 토큰 변수로만 지정하고 ``style=`` 속성을 쓰지 않는다. 외부 요청은 없다.
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import escape

from mvp_mcp.domain.spec.model import SpecDraft

MAX_SCREENS = 8
MAX_AREAS = 6

_DESTRUCTIVE = ("삭제", "취소", "제거", "delete", "cancel", "remove")
_LIST = (
    "목록",
    "조회",
    "현황",
    "내역",
    "보기",
    "검토",
    "리스트",
    "일정",
    "히스토리",
    "list",
    "history",
)
_FORM = (
    "예약",
    "등록",
    "입력",
    "작성",
    "추가",
    "저장",
    "신청",
    "기록",
    "업로드",
    "upload",
    "create",
    "add",
    "save",
)
_SEARCH = ("검색", "찾기", "search", "찾")
_PROGRESS = ("진행률", "진행", "처리 상태", "상태", "progress")
_EMPTY_STATES = ("빈", "없음", "empty")
_LOADING_STATES = ("로딩", "불러오", "저장 중", "실행 중", "처리 중", "전송 중", "loading")
_ERROR_STATES = ("오류", "실패", "에러", "error")
_SUCCESS_STATES = ("성공", "완료", "저장됨", "success", "done")
_ROW_META = ("오늘 14:00", "내일 10:30", "이번 주 금요일")
_ROW_STATUS = ("예정", "완료", "대기")


@dataclass
class _Area:
    index: int
    text: str
    kind: str
    verb: str
    noun: str


@dataclass
class _Screen:
    name: str
    purpose: str
    states: list[str]
    areas: list[_Area] = field(default_factory=list)
    overflow: list[str] = field(default_factory=list)


class HtmlPrototypeRenderer:
    def render(
        self, draft: SpecDraft, source_hash: str, design_tokens: dict[str, object] | None = None
    ) -> str:
        design = draft.design_contract
        assert design is not None
        direction = design.visual_direction
        layout = direction.layout_archetype.value if direction is not None else "workspace"
        platform = (
            "mobile"
            if direction is not None
            and [target.value for target in direction.platform_targets] == ["mobile"]
            else "web"
        )
        screens = self._screens(draft)
        error_message, recovery = (
            (design.error_states[0].user_message, design.error_states[0].recovery)
            if design.error_states
            else ("입력 내용을 확인해 주세요.", "표시된 칸을 고친 뒤 다시 시도해 주세요.")
        )
        metadata = {
            "artifact_kind": "interactive_html_prototype",
            "non_ssot": True,
            "source_contract_sha256": source_hash,
            "design_hash": source_hash,
            "layout_archetype": layout,
            "design_tokens": design_tokens or {},
            "generated_at": datetime.now(UTC).isoformat(),
            "assumptions": ["외부 호출·업로드·결제는 시제품 안에서만 흉내 낸다."],
            "sources": ["../docs/REQUIREMENTS.md", "../docs/ARCHITECTURE.md"],
            "design_contract_coverage": {
                "screens": len(screens),
                "user_flows": len(design.user_flows),
                "error_states": len(design.error_states),
            },
        }
        safe_json = json.dumps(metadata, ensure_ascii=False).replace("<", "\\u003c")
        tabs = (
            '<nav class="tabs" aria-label="화면"><div role="tablist">'
            + "".join(
                f'<button type="button" role="tab" id="tab-{index}" aria-controls="screen-{index}" '
                f'aria-selected="false" tabindex="-1">{escape(screen.name)}</button>'
                for index, screen in enumerate(screens)
            )
            + "</div></nav>"
            if len(screens) > 1
            else ""
        )
        panels = "".join(
            self._screen(index, screen, len(screens) > 1, error_message, recovery)
            for index, screen in enumerate(screens)
        )
        title = escape(draft.user_request)
        theme_css = self._theme_css(self._themes(design_tokens))
        return (
            "<!doctype html>\n"
            '<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none';\">\n"
            f'<title>{title} — 시제품</title><meta name="mvp-design-hash" content="{escape(source_hash)}">\n'
            f"<style>\n{theme_css}\n{_CSS}</style></head>\n"
            f'<body data-platform="{platform}">\n'
            f'<header class="top"><h1>{title}</h1><p class="notice">시제품이에요 · 입력한 내용은 저장되지 않아요</p></header>\n'
            f"{tabs}\n"
            f'<main class="layout" data-layout="{escape(layout)}">{panels}</main>\n'
            f"{self._about(draft, screens, source_hash)}\n"
            f'<script type="application/json" id="mvpmcp-prototype-metadata">{safe_json}</script>\n'
            f"<script>\n{_SCRIPT}</script></body></html>"
        )

    # ------------------------------------------------------------------ 화면 구성
    def _screens(self, draft: SpecDraft) -> list[_Screen]:
        design = draft.design_contract
        assert design is not None
        raw = [
            (item.name, item.purpose, list(item.ui_elements), list(item.states))
            for item in design.screens[:MAX_SCREENS]
        ]
        if not raw:
            raw = [
                (
                    "처리 흐름",
                    "입력을 받아 처리하고 결과를 확인해요.",
                    ["요청 입력", "처리 진행 상태", "결과 목록"],
                    ["기본", "빈 상태", "처리 중", "오류", "완료"],
                )
            ]
        if len(raw) == 1 and draft.features:
            name, purpose, elements, states = raw[0]
            raw = [(name, purpose, list(dict.fromkeys([*elements, *draft.features])), states)]
        screens = []
        for name, purpose, elements, states in raw:
            screen = _Screen(name=name, purpose=purpose, states=states or ["기본"])
            screen.areas = [_area(index, text) for index, text in enumerate(elements[:MAX_AREAS])]
            screen.overflow = elements[MAX_AREAS:]
            screens.append(screen)
        return screens

    def _screen(
        self, index: int, screen: _Screen, tabbed: bool, error_message: str, recovery: str
    ) -> str:
        role = f' role="tabpanel" aria-labelledby="tab-{index}" tabindex="0"' if tabbed else ""
        list_area = next((area for area in screen.areas if area.kind == "list"), None)
        form_area = next((area for area in screen.areas if area.kind == "form"), None)
        empty_title = (
            f"{list_area.noun} — 아직 없어요." if list_area else "아직 표시할 내용이 없어요."
        )
        empty_action = (
            f'<button type="button" class="primary empty-go" data-target="field-{index}-{form_area.index}">{escape(form_area.noun)} {escape(form_area.verb)}부터 시작하기</button>'
            if form_area
            else ""
        )
        areas = "".join(self._area_html(index, area, screen) for area in screen.areas)
        return (
            f'<section class="screen" id="screen-{index}" data-state="default" data-error-message="{escape(error_message, quote=True)}" '
            f'data-recovery="{escape(recovery, quote=True)}"{role}>'
            f'<h2>{escape(screen.name)}</h2><p class="lede">{escape(screen.purpose)}</p>'
            f'<p class="screen-status" id="status-{index}" role="status" aria-live="polite"></p>'
            f'<div class="empty"><p class="empty-title">{escape(empty_title)}</p>'
            f'<p class="hint">새 항목이 생기면 여기에 바로 보여요.</p>{empty_action}</div>'
            f'<div class="areas">{areas}</div></section>'
        )

    def _area_html(self, screen_index: int, area: _Area, screen: _Screen) -> str:
        key = f"{screen_index}-{area.index}"
        heading = f'<h3 id="area-{key}">{escape(area.text)}</h3>'
        open_tag = f'<section class="area area-{area.kind}" aria-labelledby="area-{key}">'
        if area.kind == "list":
            rows = "".join(
                f'<li class="row"><span class="row-title">{escape(area.noun)} {number + 1}</span>'
                f'<span class="row-meta">{_ROW_META[number]}</span>'
                f'<span class="badge">{_ROW_STATUS[number]}</span></li>'
                for number in range(3)
            )
            body = f'<ul class="rows" aria-label="{escape(area.noun, quote=True)} 목록">{rows}</ul>'
        elif area.kind == "form":
            body = (
                f'<div class="field"><label for="field-{key}">{escape(area.noun)}</label>'
                f'<input type="text" id="field-{key}" aria-invalid="false" aria-describedby="err-{key}" aria-errormessage="err-{key}">'
                f'<p class="field-error" id="err-{key}"></p></div>'
                f'<button type="button" class="primary form-submit" data-field="field-{key}" data-error="err-{key}" '
                f'data-verb="{escape(area.verb, quote=True)}" data-noun="{escape(area.noun, quote=True)}">{escape(area.verb)}</button>'
            )
        elif area.kind == "search":
            body = (
                f'<label for="search-{key}">{escape(area.noun)} 검색</label>'
                f'<input type="search" id="search-{key}" class="search" aria-describedby="count-{key}">'
                f'<p class="hint search-count" id="count-{key}">예시 결과 3개</p>'
            )
        elif area.kind == "progress":
            body = (
                f'<progress max="100" value="60" aria-labelledby="area-{key}"></progress>'
                '<p class="hint">진행 중 · 예상 완료 내일</p>'
            )
        elif area.kind == "destructive":
            body = (
                f'<button type="button" class="danger open-confirm" data-dialog="confirm-{key}">{escape(area.verb)}</button>'
                f'<dialog id="confirm-{key}" aria-labelledby="confirm-title-{key}">'
                f'<h3 id="confirm-title-{key}">{escape(area.text)} — 정말 진행할까요?</h3>'
                "<p>진행한 뒤에도 바로 되돌릴 수 있어요.</p>"
                '<div class="dialog-actions"><button type="button" class="ghost dialog-cancel">그만두기</button>'
                f'<button type="button" class="danger dialog-confirm" data-done="{escape(area.text, quote=True)}">{escape(area.verb)}</button></div></dialog>'
            )
        else:
            body = f'<button type="button" class="secondary plain-action" data-label="{escape(area.verb, quote=True)}">{escape(area.verb)}</button>'
        return f"{open_tag}{heading}{body}</section>"

    def _about(self, draft: SpecDraft, screens: list[_Screen], source_hash: str) -> str:
        design = draft.design_contract
        assert design is not None
        previews = "".join(
            f'<fieldset class="state-preview" data-screen="{index}" aria-describedby="status-{index}" aria-errormessage="status-{index}">'
            f"<legend>화면 상태 미리보기 · {escape(screen.name)}</legend>"
            + "".join(
                f'<label class="choice"><input type="radio" name="state-{index}" value="{_state_kind(state)}" '
                f'data-label="{escape(state, quote=True)}"{" checked" if position == 0 else ""}>{escape(state)}</label>'
                for position, state in enumerate(screen.states)
            )
            + "</fieldset>"
            for index, screen in enumerate(screens)
        )
        flows = (
            "".join(
                f"<li><strong>{escape(flow.name)}</strong>: "
                + " → ".join(escape(step) for step in flow.steps)
                + (
                    f'<br><span class="hint">예외·복구: {"; ".join(escape(path) for path in flow.exception_paths)}</span>'
                    if flow.exception_paths
                    else ""
                )
                + "</li>"
                for flow in design.user_flows
            )
            or "<li>문서 계약에 아직 사용자 흐름이 없습니다.</li>"
        )
        errors = (
            "".join(
                f"<li><strong>{escape(error.trigger)}</strong>: {escape(error.user_message)} "
                f'<span class="hint">복구: {escape(error.recovery)}</span></li>'
                for error in design.error_states
            )
            or "<li>문서 계약에 아직 오류 상태가 없습니다.</li>"
        )
        overflow = [item for screen in screens for item in screen.overflow]
        others = (
            "<h3>그 밖의 요소</h3><ul>"
            + "".join(f"<li>{escape(item)}</li>" for item in overflow)
            + "</ul>"
            if overflow
            else ""
        )
        return (
            '<details class="about"><summary>이 시제품에 대해</summary><div class="about-body">'
            "<p>요구사항·설계 문서에서 자동으로 만든 NON-SSOT 시제품입니다. 기준은 문서이며 화면은 확정 디자인이 아닙니다. "
            "외부 호출·저장·결제는 일어나지 않습니다.</p>"
            f'<p class="hint">계약 해시: <code>{escape(source_hash[:12])}…</code> · 원본: '
            '<a href="../docs/REQUIREMENTS.md">REQUIREMENTS</a> · <a href="../docs/ARCHITECTURE.md">ARCHITECTURE</a></p>'
            f"{previews}"
            f"<h3>사용자 흐름</h3><ul>{flows}</ul>"
            f"<h3>오류·복구</h3><ul>{errors}</ul>{others}"
            '<button type="button" class="secondary theme-toggle" aria-pressed="false">고대비로 보기</button>'
            "</div></details>"
        )

    # ------------------------------------------------------------------ 테마
    @staticmethod
    def _themes(design_tokens: dict[str, object] | None) -> dict[str, dict[str, str]]:
        light = {
            "primary": "Highlight",
            "on_primary": "HighlightText",
            "surface": "Canvas",
            "surface_muted": "Canvas",
            "text_primary": "CanvasText",
            "text_secondary": "CanvasText",
            "outline": "GrayText",
            "success": "CanvasText",
            "warning": "CanvasText",
            "error": "CanvasText",
            "info": "Highlight",
            "focus_ring": "Highlight",
        }
        dark = dict(light)
        fallback = {"light": light, "dark": dark, "high_contrast": {**light}}
        if design_tokens is None:
            return fallback
        color = design_tokens.get("color")
        if not isinstance(color, dict):
            return fallback
        token_themes = {name: color.get(name) for name in ("light", "dark", "high_contrast")}
        if not all(isinstance(theme, dict) for theme in token_themes.values()):
            return fallback

        def values(section: dict[object, object], defaults: dict[str, str]) -> dict[str, str]:
            return {name: value(section, name, default) for name, default in defaults.items()}

        def value(section: dict[object, object], name: str, default: str) -> str:
            candidate = section.get(name)
            return candidate if isinstance(candidate, str) else default

        return {
            "light": values(token_themes["light"], light),  # type: ignore[arg-type]
            "dark": values(token_themes["dark"], dark),  # type: ignore[arg-type]
            "high_contrast": values(token_themes["high_contrast"], light),  # type: ignore[arg-type]
        }

    @staticmethod
    def _theme_css(themes: dict[str, dict[str, str]]) -> str:
        def declarations(values: dict[str, str]) -> str:
            return ";".join(
                (
                    f"--ink:{values['text_primary']}",
                    f"--muted:{values['text_secondary']}",
                    f"--brand:{values['primary']}",
                    f"--on-brand:{values['on_primary']}",
                    f"--line:{values['outline']}",
                    f"--bg:{values['surface_muted']}",
                    f"--surface:{values['surface']}",
                    f"--ok:{values['success']}",
                    f"--warning:{values['warning']}",
                    f"--error:{values['error']}",
                    f"--info:{values['info']}",
                    f"--focus:{values['focus_ring']}",
                    "--radius-control:8px",
                )
            )

        return (
            f":root{{{declarations(themes['light'])}}}"
            f"@media (prefers-color-scheme: dark){{:root{{{declarations(themes['dark'])}}}}}"
            f':root[data-theme="high_contrast"]{{{declarations(themes["high_contrast"])}}}'
        )


def _area(index: int, text: str) -> _Area:
    lowered = text.lower()
    for kind, words in (
        ("destructive", _DESTRUCTIVE),
        ("list", _LIST),
        ("search", ("검색", "search")),
        ("form", _FORM),
        ("search", _SEARCH),
        ("progress", _PROGRESS),
    ):
        found = [word for word in words if word in lowered]
        if found:
            verb = max(found, key=lambda word: (lowered.rfind(word), len(word)))
            noun = _list_noun(text) if kind == "list" else _noun(text, verb)
            return _Area(index, text, kind, _verb_label(kind, verb, text), noun)
    return _Area(index, text, "action", _button_label(text), _strip_actor(text))


def _verb_label(kind: str, verb: str, text: str) -> str:
    if kind == "form":
        return {
            "찾": "찾기",
            "upload": "업로드",
            "create": "만들기",
            "add": "추가",
            "save": "저장",
        }.get(verb, verb)
    if kind == "destructive":
        return {"delete": "삭제", "cancel": "취소", "remove": "제거"}.get(verb, verb)
    return verb


def _noun(text: str, verb: str) -> str:
    position = text.lower().rfind(verb)
    remainder = (text[:position] + text[position + len(verb) :]) if position >= 0 else text
    remainder = re.sub(r"(찾아|하기|하는|해서|및)\s*$", "", remainder.strip(" ·-/,"))
    remainder = re.sub(r"\s+", " ", remainder).strip(" ·-/,")
    return _strip_actor(remainder) if remainder else text


_LIST_VERBS = ("확인", "보기", "조회", "검토", "살펴보기")


def _list_noun(text: str) -> str:
    """목록 이름: 뒤의 보기·확인 동사를 떼고 행위자를 뺀 명사구 (예: 트레이너가 오늘 일정 확인 → 오늘 일정)."""
    words = text.split()
    while len(words) > 1 and words[-1] in _LIST_VERBS:
        words.pop()
    return _strip_actor(" ".join(words)) or text


def _strip_actor(text: str) -> str:
    """앞의 행위자(회원이·트레이너가·사용자는)를 뗀다. 남는 말이 없으면 그대로 둔다."""
    words = text.split()
    if len(words) > 1 and re.fullmatch(r".+(이|가|은|는)", words[0]):
        return " ".join(words[1:])
    return text


def _button_label(text: str) -> str:
    return text if len(text) <= 14 else text.split()[-1]


def _state_kind(state: str) -> str:
    lowered = state.lower()
    for kind, words in (
        ("empty", _EMPTY_STATES),
        ("loading", _LOADING_STATES),
        ("error", _ERROR_STATES),
        ("success", _SUCCESS_STATES),
    ):
        if any(word in lowered for word in words):
            return kind
    return "default" if state.strip() in {"기본", "default", "편집 중", "대기"} else "note"


_CSS = r"""
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}
h1,h2,h3,p{margin:0}
.top,.tabs,.layout,.about{max-width:760px;margin:0 auto;padding:0 20px}
.top{padding-top:28px;padding-bottom:12px}
h1{font-size:clamp(22px,4vw,30px);line-height:1.3}
.notice,.hint,.lede,.row-meta{color:var(--muted)}
.notice{font-size:14px;margin-top:4px}
.tabs{border-bottom:1px solid var(--line);overflow-x:auto}
.tabs [role=tablist]{display:flex;gap:4px}
.tabs [role=tab]{border:0;border-bottom:2px solid transparent;background:none;color:var(--muted);padding:10px 12px;min-height:44px;cursor:pointer;font:inherit;white-space:nowrap}
.tabs [role=tab][aria-selected=true]{color:var(--ink);border-bottom-color:var(--brand);font-weight:700}
.layout{padding-top:24px;padding-bottom:32px}
.screen[hidden]{display:none}
.screen:focus{outline:none}
h2{font-size:20px}
.lede{margin-top:4px}
.screen-status{min-height:24px;margin:12px 0;font-weight:600}
.screen-status[data-kind=error]{color:var(--error)}
.screen-status[data-kind=success]{color:var(--ok)}
.areas{display:grid;gap:28px}
.area{padding-top:18px;border-top:1px solid var(--line)}
.area h3{font-size:16px;margin-bottom:10px}
.rows{list-style:none;margin:0;padding:0}
.row[hidden]{display:none}
.row{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
.row-title{font-weight:600;flex:1 1 auto;min-width:0}
.badge{display:inline-block;padding:0 8px;border-radius:4px;background:var(--bg);color:var(--ink);font-size:13px;font-weight:700;line-height:22px;box-shadow:inset 0 0 0 1px var(--line)}
.field{display:grid;gap:6px;margin-bottom:12px}
label{font-weight:600}
input[type=text],input[type=search]{width:100%;min-height:44px;padding:8px 12px;border:1px solid var(--line);border-radius:var(--radius-control);background:var(--surface);color:var(--ink);font:inherit}
input[aria-invalid=true]{border-color:var(--error);border-width:2px}
.field-error{color:var(--error);font-size:14px;min-height:0}
.field-error:empty{display:none}
button{font:inherit;min-height:44px;padding:0 16px;border-radius:var(--radius-control);cursor:pointer}
.primary{background:var(--brand);color:var(--on-brand);border:1px solid var(--brand);font-weight:700}
.secondary,.ghost{background:var(--surface);color:var(--ink);border:1px solid var(--line)}
.ghost{border-color:transparent}
.danger{background:var(--surface);color:var(--error);border:1px solid var(--error);font-weight:700}
.link{min-height:0;padding:0;border:0;background:none;color:var(--info);text-decoration:underline;font-weight:600}
button:disabled{opacity:.5;cursor:not-allowed}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
progress{width:100%;height:12px;accent-color:var(--brand)}
.empty{display:none;padding:16px 0}
.empty-title{font-weight:700;margin-bottom:4px}
.empty .primary{margin-top:12px}
.screen[data-state=empty] .empty,.screen[data-empty=true] .empty{display:block}
.screen[data-state=empty] .rows,.screen[data-empty=true] .rows{display:none}
.screen[aria-busy=true] .areas{opacity:.6}
dialog{max-width:28rem;border:1px solid var(--line);border-radius:var(--radius-control);background:var(--surface);color:var(--ink);padding:20px}
dialog::backdrop{background:color-mix(in srgb,var(--ink) 45%,transparent)}
dialog h3{margin-bottom:8px}
.dialog-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;margin-top:16px}
.about{padding-bottom:40px}
.about summary{cursor:pointer;color:var(--muted);font-weight:600;min-height:44px;display:flex;align-items:center}
.about-body{display:grid;gap:12px;padding:8px 0 0 12px;border-left:2px solid var(--line)}
.about h3{font-size:15px;margin-top:8px}
.about ul{margin:0;padding-left:20px}
.state-preview{border:0;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:4px 16px}
.state-preview[hidden]{display:none}
.state-preview legend{font-weight:600;padding:0;margin-bottom:4px}
.choice{display:inline-flex;gap:6px;align-items:center;font-weight:400;min-height:44px}
.choice input{accent-color:var(--brand);width:18px;height:18px}
code{font-family:ui-monospace,Consolas,monospace}
a{color:var(--info)}
@media (min-width:1024px){
  .layout[data-layout=list_detail],body:has(.layout[data-layout=list_detail]) .top,body:has(.layout[data-layout=list_detail]) .about{max-width:1080px}
  .layout[data-layout=list_detail] .areas{grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:start}
  .layout[data-layout=list_detail] .area-list{grid-row:span 3}
}
@media (max-width:480px){.top,.tabs,.layout,.about{padding-left:16px;padding-right:16px}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""

_SCRIPT = r"""
const tabs=[...document.querySelectorAll('[role=tab]')],screens=[...document.querySelectorAll('.screen')],previews=[...document.querySelectorAll('.state-preview')];
function show(i){tabs.forEach((t,n)=>{t.setAttribute('aria-selected',n===i?'true':'false');t.tabIndex=n===i?0:-1;});screens.forEach((s,n)=>{s.hidden=n!==i;});previews.forEach(p=>{p.hidden=p.dataset.screen!==String(i);});}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>show(index));tab.addEventListener('keydown',event=>{let next=index;if(event.key==='ArrowRight')next=(index+1)%tabs.length;else if(event.key==='ArrowLeft')next=(index-1+tabs.length)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;event.preventDefault();show(next);tabs[next].focus();});});
show(0);
function status(screen,kind,text,undo){const el=screen.querySelector('.screen-status');el.dataset.kind=kind;el.textContent=text;if(undo){const b=document.createElement('button');b.type='button';b.className='link';b.textContent='되돌리기';b.addEventListener('click',()=>{undo();status(screen,'info','되돌렸어요.');});el.append(' ',b);}}
function syncEmpty(screen){const rows=screen.querySelector('.rows');if(rows)screen.dataset.empty=rows.children.length===0?'true':'false';}
function clearErrors(screen){screen.querySelectorAll('[aria-invalid=true]').forEach(i=>i.setAttribute('aria-invalid','false'));screen.querySelectorAll('.field-error').forEach(e=>{e.textContent='';});}
function addRow(screen,text){const rows=screen.querySelector('.rows');if(!rows)return null;const li=document.createElement('li');li.className='row';const t=document.createElement('span');t.className='row-title';t.textContent=text;const m=document.createElement('span');m.className='row-meta';m.textContent='방금';const b=document.createElement('span');b.className='badge';b.textContent='새로 추가';li.append(t,m,b);rows.prepend(li);syncEmpty(screen);return li;}
document.querySelectorAll('.form-submit').forEach(button=>button.addEventListener('click',()=>{const screen=button.closest('.screen');const input=document.getElementById(button.dataset.field);const error=document.getElementById(button.dataset.error);const value=input.value.trim();if(!value){input.setAttribute('aria-invalid','true');error.textContent=button.dataset.noun+'을(를) 입력해 주세요.';input.focus();status(screen,'error',screen.dataset.errorMessage+' '+screen.dataset.recovery);return;}input.setAttribute('aria-invalid','false');error.textContent='';const row=addRow(screen,value);input.value='';status(screen,'success',button.dataset.verb+' 완료 — '+button.dataset.noun+': '+value,()=>{if(row){row.remove();syncEmpty(screen);}input.value=value;});}));
document.querySelectorAll('input[aria-invalid]').forEach(input=>input.addEventListener('input',()=>{if(input.value.trim()){input.setAttribute('aria-invalid','false');const e=document.getElementById(input.getAttribute('aria-errormessage'));if(e)e.textContent='';}}));
document.querySelectorAll('.search').forEach(input=>input.addEventListener('input',()=>{const screen=input.closest('.screen');const rows=[...screen.querySelectorAll('.row')];const q=input.value.trim();let count=0;rows.forEach(r=>{const hit=!q||r.textContent.includes(q);r.hidden=!hit;if(hit)count++;});const out=document.getElementById(input.getAttribute('aria-describedby'));if(out)out.textContent=rows.length?('결과 '+count+'개'):'예시 결과 3개';}));
document.querySelectorAll('.open-confirm').forEach(button=>button.addEventListener('click',()=>document.getElementById(button.dataset.dialog).showModal()));
document.querySelectorAll('.dialog-cancel').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
document.querySelectorAll('.dialog-confirm').forEach(button=>button.addEventListener('click',()=>{const screen=button.closest('.screen');button.closest('dialog').close();const row=screen.querySelector('.row');if(row)row.hidden=true;status(screen,'success',button.dataset.done+' 완료',()=>{if(row)row.hidden=false;});}));
document.querySelectorAll('.plain-action').forEach(button=>button.addEventListener('click',()=>status(button.closest('.screen'),'info',button.dataset.label+'을(를) 눌렀어요. 시제품이라 실제로 처리되지는 않아요.')));
document.querySelectorAll('.empty-go').forEach(button=>button.addEventListener('click',()=>{const screen=button.closest('.screen');screen.dataset.state='default';const field=document.getElementById(button.dataset.target);if(field)field.focus();}));
function applyState(screen,kind,label){screen.dataset.state=kind==='empty'?'empty':'default';screen.removeAttribute('aria-busy');screen.querySelectorAll('.areas button').forEach(b=>{b.disabled=false;});clearErrors(screen);
 if(kind==='loading'){screen.setAttribute('aria-busy','true');screen.querySelectorAll('.areas button').forEach(b=>{b.disabled=true;});status(screen,'info','불러오는 중이에요…');}
 else if(kind==='error'){const input=screen.querySelector('.areas input[aria-errormessage]');if(input){input.setAttribute('aria-invalid','true');const e=document.getElementById(input.getAttribute('aria-errormessage'));if(e)e.textContent=screen.dataset.errorMessage;}status(screen,'error',screen.dataset.errorMessage+' '+screen.dataset.recovery);}
 else if(kind==='success'){status(screen,'success',label+' — 방금 처리했어요.',()=>{});}
 else if(kind==='empty'){status(screen,'info','');}
 else if(kind==='note'){status(screen,'info',label);}
 else{status(screen,'info','');}}
document.querySelectorAll('.state-preview input').forEach(input=>input.addEventListener('change',()=>{const screen=document.getElementById('screen-'+input.closest('.state-preview').dataset.screen);applyState(screen,input.value,input.dataset.label);}));
screens.forEach(syncEmpty);
const toggle=document.querySelector('.theme-toggle');if(toggle)toggle.addEventListener('click',()=>{const high=document.documentElement.dataset.theme==='high_contrast';document.documentElement.dataset.theme=high?'':'high_contrast';toggle.setAttribute('aria-pressed',high?'false':'true');toggle.textContent=high?'고대비로 보기':'기본 테마로 돌아가기';});
"""
