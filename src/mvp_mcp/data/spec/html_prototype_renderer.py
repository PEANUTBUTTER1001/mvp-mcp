"""문서 계약에서 외부 의존성 없는 비정본 HTML 프로토타입을 렌더링한다."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from typing import TypedDict

from mvp_mcp.domain.spec.model import SpecDraft


class _ScreenData(TypedDict):
    name: str
    purpose: str
    elements: list[str]
    states: list[str]


class HtmlPrototypeRenderer:
    def render(self, draft: SpecDraft, source_hash: str) -> str:
        design = draft.design_contract
        assert design is not None
        screens: list[_ScreenData] = [
            {
                "name": item.name,
                "purpose": item.purpose,
                "elements": item.ui_elements,
                "states": item.states,
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
                }
            ]
        metadata = {
            "artifact_kind": "interactive_html_prototype",
            "non_ssot": True,
            "source_contract_sha256": source_hash,
            "generated_at": datetime.now(UTC).isoformat(),
            "assumptions": ["외부 호출·업로드·결제는 mock으로만 동작한다."],
            "sources": ["../docs/REQUIREMENTS.md", "../docs/ARCHITECTURE.md"],
        }
        safe_json = json.dumps(metadata, ensure_ascii=False).replace("<", "\\u003c")
        nav = "\n".join(
            f'<button class="nav" type="button" data-index="{index}" aria-controls="screen-{index}">{escape(item["name"])}</button>'
            for index, item in enumerate(screens)
        )
        panels = "\n".join(self._panel(index, item) for index, item in enumerate(screens))
        return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none';">
<title>{escape(draft.user_request)} — NON-SSOT PROTOTYPE</title>
<style>
:root{{--ink:#172033;--muted:#667085;--brand:#155eef;--line:#d7dfeb;--bg:#f4f7fb;--ok:#067647}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
.banner{{background:#fff2cc;border-bottom:1px solid #e0b300;padding:10px 20px;text-align:center;font-weight:800}}
header,main{{max-width:1080px;margin:auto}}header{{padding:28px 20px 18px}}h1{{margin:0 0 6px;font-size:clamp(24px,4vw,38px)}}
.meta{{color:var(--muted)}}.layout{{display:grid;grid-template-columns:230px 1fr;gap:18px;padding:0 20px 40px}}
nav,.panel{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px}}nav{{display:flex;flex-direction:column;gap:8px;align-self:start}}
button{{font:inherit}}.nav,.action{{border:1px solid var(--line);border-radius:10px;background:#fff;padding:10px 12px;text-align:left;cursor:pointer}}
.nav[aria-current="page"],.action{{background:var(--brand);border-color:var(--brand);color:#fff}}button:focus-visible,input:focus-visible{{outline:3px solid #f79009;outline-offset:2px}}
.panel[hidden]{{display:none}}.card{{border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}}label{{display:block;font-weight:700;margin:12px 0 5px}}input{{width:100%;padding:10px;border:1px solid #98a2b3;border-radius:9px}}.status{{min-height:26px;color:var(--ok);font-weight:800}}
.sources a{{color:#175cd3}}@media(max-width:720px){{.layout{{grid-template-columns:1fr}}nav{{flex-direction:row;overflow:auto}}.nav{{min-width:max-content}}}}
</style></head><body>
<div class="banner">NON-SSOT PROTOTYPE · 요구사항과 설계의 파생 미리보기 · 실제 외부 작업 없음</div>
<header><h1>{escape(draft.user_request)}</h1><p class="meta">문서 상태: DRAFT · 계약 해시: {escape(source_hash[:12])}…</p>
<p class="sources">원본: <a href="../docs/REQUIREMENTS.md">REQUIREMENTS</a> · <a href="../docs/ARCHITECTURE.md">ARCHITECTURE</a></p></header>
<main class="layout"><nav aria-label="프로토타입 화면">{nav}</nav><section aria-live="polite">{panels}</section></main>
<script type="application/json" id="mvpmcp-prototype-metadata">{safe_json}</script>
<script>
const buttons=[...document.querySelectorAll('.nav')],panels=[...document.querySelectorAll('.panel')];
function show(i){{buttons.forEach((b,n)=>b.setAttribute('aria-current',n===i?'page':'false'));panels.forEach((p,n)=>p.hidden=n!==i);}}
buttons.forEach((b,i)=>b.addEventListener('click',()=>show(i)));show(0);
document.querySelectorAll('.action').forEach(button=>button.addEventListener('click',()=>{{const panel=button.closest('.panel');const input=panel.querySelector('input');const status=panel.querySelector('.status');status.textContent=input.value.trim()?'Mock 처리 완료 — 실제 전송되지 않았습니다.':'입력값을 확인하세요.';}}));
</script></body></html>"""

    @staticmethod
    def _panel(index: int, item: _ScreenData) -> str:
        elements = "".join(f"<li>{escape(value)}</li>" for value in item["elements"])
        states = "".join(f'<span class="card">{escape(value)}</span>' for value in item["states"])
        return f"""<article class="panel" id="screen-{index}" hidden><h2>{escape(str(item['name']))}</h2>
<p>{escape(str(item['purpose']))}</p><div class="card"><strong>주요 요소</strong><ul>{elements}</ul></div>
<div class="card"><strong>지원 상태</strong><div>{states}</div></div><label for="input-{index}">Mock 입력</label>
<input id="input-{index}" autocomplete="off" placeholder="실제 데이터는 전송되지 않습니다"><p class="status" role="status"></p>
<button class="action" type="button">흐름 실행</button></article>"""
