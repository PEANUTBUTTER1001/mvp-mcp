"""문서 계약에서 외부 의존성 없는 비정본 HTML 프로토타입을 렌더링한다."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from typing import TypedDict

from mvp_mcp.domain.spec.model import ScreenSpec, SpecDraft


class _ScreenData(TypedDict):
    name: str
    purpose: str
    elements: list[str]
    states: list[str]
    destructive: bool


class HtmlPrototypeRenderer:
    def render(
        self, draft: SpecDraft, source_hash: str, design_tokens: dict[str, object] | None = None
    ) -> str:
        design = draft.design_contract
        assert design is not None
        direction = design.visual_direction
        layout = direction.layout_archetype.value if direction is not None else "workspace"
        theme_css = self._theme_css(self._themes(design_tokens))
        screens: list[_ScreenData] = [
            {
                "name": item.name,
                "purpose": item.purpose,
                "elements": item.ui_elements,
                "states": item.states,
                "destructive": self._has_destructive_action(item),
            }
            for item in design.screens
        ]
        if not screens:
            screens = [
                {
                    "name": "워크플로 시뮬레이터",
                    "purpose": "CLI·MCP·API 또는 데이터 처리 흐름을 단계별로 확인한다.",
                    "elements": ["입력", "검증", "처리", "결과"],
                    "states": ["대기", "실행 중", "완료", "오류"],
                    "destructive": False,
                }
            ]
        flow_cards = self._flow_cards(draft)
        error_cards = self._error_cards(draft)
        metadata = {
            "artifact_kind": "interactive_html_prototype",
            "non_ssot": True,
            "source_contract_sha256": source_hash,
            "design_hash": source_hash,
            "layout_archetype": layout,
            "design_tokens": design_tokens or {},
            "generated_at": datetime.now(UTC).isoformat(),
            "assumptions": ["외부 호출·업로드·결제는 mock으로만 동작한다."],
            "sources": ["../docs/REQUIREMENTS.md", "../docs/ARCHITECTURE.md"],
            "design_contract_coverage": {
                "screens": len(screens),
                "user_flows": len(design.user_flows),
                "error_states": len(design.error_states),
            },
        }
        safe_json = json.dumps(metadata, ensure_ascii=False).replace("<", "\\u003c")
        nav = "\n".join(
            f'<button class="nav" type="button" role="tab" id="screen-tab-{index}" data-index="{index}" '
            f'aria-controls="screen-{index}" aria-selected="false" tabindex="-1">{escape(item["name"])}</button>'
            for index, item in enumerate(screens)
        )
        panels = "\n".join(self._panel(index, item) for index, item in enumerate(screens))
        return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none';">
<title>{escape(draft.user_request)} — NON-SSOT PROTOTYPE</title><meta name="mvp-design-hash" content="{escape(source_hash)}">
<style>
{theme_css}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
.banner{{background:color-mix(in srgb,var(--warning) 14%,var(--surface));border-bottom:1px solid var(--warning);padding:10px 20px;text-align:center;font-weight:800}}
header,main{{max-width:1080px;margin:auto}}header{{padding:28px 20px 18px}}h1{{margin:0 0 6px;font-size:clamp(24px,4vw,38px)}}
.meta{{color:var(--muted)}}.layout{{display:grid;grid-template-columns:minmax(200px,240px) minmax(0,760px);gap:24px;padding:0 20px 40px}}.layout[data-layout="guided_flow"],.layout[data-layout="reading"]{{grid-template-columns:minmax(0,760px)}}.layout[data-layout="guided_flow"] nav,.layout[data-layout="reading"] nav{{display:none}}
nav,.panel,.contract-card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-card);padding:16px}}nav{{display:flex;flex-direction:column;gap:8px;align-self:start}}
button{{font:inherit}}.nav,.action{{border:1px solid var(--line);border-radius:var(--radius-control);background:var(--surface);padding:10px 12px;text-align:left;cursor:pointer}}
.nav[aria-selected="true"],.action{{background:var(--brand);border-color:var(--brand);color:var(--on-brand)}}button:focus-visible,input:focus-visible{{outline:3px solid var(--focus);outline-offset:2px}}
.panel[hidden]{{display:none}}.panel:focus{{outline:none}}.card{{border:1px solid var(--line);border-radius:var(--radius-card);padding:14px;margin:12px 0}}fieldset{{border:0;margin:0;padding:0}}legend{{font-weight:700}}.hint{{color:var(--muted);font-size:14px}}.state-options{{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}}.state-option{{align-items:center;border:1px solid var(--line);border-radius:999px;cursor:pointer;display:inline-flex;font-size:14px;font-weight:600;gap:6px;margin:0;padding:6px 10px}}.state-option input{{accent-color:var(--brand);height:16px;margin:0;width:16px}}.state-picker[aria-invalid="true"] .state-options{{outline:2px solid var(--error);outline-offset:4px}}.status{{min-height:26px;color:var(--ok);font-weight:800}}.status[data-state="error"]{{color:var(--error)}}.contract-context{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:18px}}.contract-card{{padding:16px}}.contract-card h2,.contract-card h3{{margin-top:0}}.contract-card ol,.contract-card ul{{padding-left:22px}}.recovery{{color:var(--muted)}}
.delete-action{{border:1px solid var(--error);border-radius:var(--radius-control);background:var(--surface);color:var(--error);cursor:pointer;margin-top:12px;padding:10px 12px}}dialog{{background:var(--surface);border:1px solid var(--line);color:var(--ink);max-width:32rem;padding:20px}}dialog::backdrop{{background:color-mix(in srgb,var(--ink) 45%,transparent)}}.dialog-actions{{display:flex;gap:8px;justify-content:flex-end}}
.sources a{{color:var(--info)}}@media(max-width:767px){{.layout{{grid-template-columns:1fr}}nav{{flex-direction:row;overflow:auto}}.nav{{min-width:max-content}}}}
</style></head><body>
<div class="banner">NON-SSOT PROTOTYPE · 요구사항과 설계의 파생 미리보기 · 실제 외부 작업 없음</div>
<header><h1>{escape(draft.user_request)}</h1><p class="meta">문서 상태: DRAFT · 계약 해시: {escape(source_hash[:12])}…</p>
<p class="sources">원본: <a href="../docs/REQUIREMENTS.md">REQUIREMENTS</a> · <a href="../docs/ARCHITECTURE.md">ARCHITECTURE</a></p><button class="theme-toggle" type="button" aria-pressed="false">고대비 테마 확인</button></header>
<main class="layout" data-layout="{layout}"><nav aria-label="프로토타입 화면" role="tablist">{nav}</nav><section aria-label="화면 미리보기">{panels}<div class="contract-context" aria-label="설계 계약 근거">{flow_cards}{error_cards}</div></section></main>
<script type="application/json" id="mvpmcp-prototype-metadata">{safe_json}</script>
<script>
const buttons=[...document.querySelectorAll('.nav')],panels=[...document.querySelectorAll('.panel')];
function show(i){{buttons.forEach((b,n)=>{{b.setAttribute('aria-selected',n===i?'true':'false');b.tabIndex=n===i?0:-1;}});panels.forEach((p,n)=>p.hidden=n!==i);}}
buttons.forEach((button,index)=>{{button.addEventListener('click',()=>show(index));button.addEventListener('keydown',event=>{{let next=index;if(event.key==='ArrowRight')next=(index+1)%buttons.length;else if(event.key==='ArrowLeft')next=(index-1+buttons.length)%buttons.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=buttons.length-1;else return;event.preventDefault();show(next);buttons[next].focus();}});}});show(0);
document.querySelectorAll('.state-choice').forEach(choice=>choice.addEventListener('change',()=>{{const panel=choice.closest('.panel');const picker=panel.querySelector('.state-picker');const status=panel.querySelector('.status');picker.setAttribute('aria-invalid','false');status.dataset.state='';status.textContent='';}}));
document.querySelectorAll('.action').forEach(button=>button.addEventListener('click',()=>{{const panel=button.closest('.panel');const picker=panel.querySelector('.state-picker');const selected=picker.querySelector('.state-choice:checked');const status=panel.querySelector('.status');const invalid=selected===null;picker.setAttribute('aria-invalid',invalid?'true':'false');status.dataset.state=invalid?'error':'success';status.textContent=invalid?'Mock으로 확인할 지원 상태를 하나 선택하세요. 실제 전송은 없습니다.':`${{panel.querySelector('h2').textContent}} 화면에서 ${{selected.value}} 상태를 Mock으로 확인했습니다. 실제 전송은 없습니다.`;}}));
document.querySelectorAll('.delete-action').forEach(button=>button.addEventListener('click',()=>button.closest('.panel').querySelector('.delete-confirmation').showModal()));document.querySelectorAll('.delete-cancel').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));document.querySelectorAll('.delete-confirm').forEach(button=>button.addEventListener('click',()=>{{const panel=button.closest('.panel');const dialog=button.closest('dialog');const status=panel.querySelector('.status');dialog.close();status.dataset.state='success';status.textContent=`${{panel.querySelector('h2').textContent}} 화면의 삭제 Mock을 확인했습니다. 되돌리기 동작은 실제 데이터를 바꾸지 않습니다.`;}}));
const themeToggle=document.querySelector('.theme-toggle');themeToggle.addEventListener('click',()=>{{const high=document.documentElement.dataset.theme==='high_contrast';document.documentElement.dataset.theme=high?'':'high_contrast';themeToggle.setAttribute('aria-pressed',high?'false':'true');themeToggle.textContent=high?'고대비 테마 확인':'기본 테마로 돌아가기';}});
</script></body></html>"""

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
                    "--radius-card:0",
                )
            )

        return (
            f":root{{{declarations(themes['light'])}}}"
            f"@media (prefers-color-scheme: dark){{:root{{{declarations(themes['dark'])}}}}}"
            f":root[data-theme=\"high_contrast\"]{{{declarations(themes['high_contrast'])}}}"
        )

    @staticmethod
    def _panel(index: int, item: _ScreenData) -> str:
        elements = "".join(f"<li>{escape(value)}</li>" for value in item["elements"])
        states = "".join(
            f'<label class="state-option" for="state-{index}-{state_index}">'
            f'<input class="state-choice" type="radio" name="state-{index}" '
            f'id="state-{index}-{state_index}" value="{escape(value, quote=True)}">'
            f"<span>{escape(value)}</span></label>"
            for state_index, value in enumerate(item["states"])
        )
        name = escape(str(item["name"]))
        destructive = (
            f'<button class="delete-action" type="button">{name} 삭제 Mock</button>'
            f'<dialog class="delete-confirmation" aria-labelledby="delete-title-{index}">'
            f'<h3 id="delete-title-{index}">{name} 삭제를 확인할까요?</h3>'
            "<p>대상과 영향을 확인한 뒤 취소하거나 삭제를 Mock으로 확인할 수 있습니다.</p>"
            '<div class="dialog-actions"><button class="delete-cancel" type="button">취소</button>'
            '<button class="action delete-confirm" type="button">삭제 확인</button></div></dialog>'
            if item["destructive"]
            else ""
        )
        return f"""<article class="panel" id="screen-{index}" role="tabpanel" aria-labelledby="screen-tab-{index}" tabindex="0" hidden><h2>{name}</h2>
<p>{escape(str(item['purpose']))}</p><div class="card"><strong>주요 요소</strong><ul>{elements}</ul></div>
<div class="card"><fieldset class="state-picker" id="state-picker-{index}" aria-describedby="state-help-{index} status-{index}" aria-errormessage="status-{index}" aria-invalid="false"><legend>Mock으로 확인할 지원 상태</legend>
<p class="hint" id="state-help-{index}">이 화면의 문서 계약에 선언된 상태만 선택할 수 있으며 실제 데이터는 전송하지 않습니다.</p>
<div class="state-options">{states}</div></fieldset></div><p class="status" id="status-{index}" role="status"></p>
<button class="action" type="button">{name} 상태 확인</button>{destructive}</article>"""

    @staticmethod
    def _has_destructive_action(item: ScreenSpec) -> bool:
        return any(
            "삭제" in value for value in (*item.ui_elements, *item.states, item.name, item.purpose)
        )

    @staticmethod
    def _flow_cards(draft: SpecDraft) -> str:
        design = draft.design_contract
        assert design is not None
        if not design.user_flows:
            return (
                '<section class="contract-card"><h2>검증할 사용자 흐름</h2>'
                "<p>구체 흐름은 아직 문서 계약에 기록되지 않았습니다.</p></section>"
            )
        cards = "".join(
            "<article><h3>"
            + escape(flow.name)
            + "</h3><ol>"
            + "".join(f"<li>{escape(step)}</li>" for step in flow.steps)
            + "</ol>"
            + (
                '<p class="recovery"><strong>예외·복구:</strong> '
                + "; ".join(escape(path) for path in flow.exception_paths)
                + "</p>"
                if flow.exception_paths
                else ""
            )
            + "</article>"
            for flow in design.user_flows
        )
        return f'<section class="contract-card"><h2>검증할 사용자 흐름</h2>{cards}</section>'

    @staticmethod
    def _error_cards(draft: SpecDraft) -> str:
        design = draft.design_contract
        assert design is not None
        if not design.error_states:
            return (
                '<section class="contract-card"><h2>오류·복구 안내</h2>'
                "<p>구체 오류 상태는 아직 문서 계약에 기록되지 않았습니다.</p></section>"
            )
        errors = "".join(
            "<li><strong>"
            + escape(error.trigger)
            + "</strong>: "
            + escape(error.user_message)
            + f'<br><span class="recovery">복구: {escape(error.recovery)}</span></li>'
            for error in design.error_states
        )
        return f'<section class="contract-card"><h2>오류·복구 안내</h2><ul>{errors}</ul></section>'
