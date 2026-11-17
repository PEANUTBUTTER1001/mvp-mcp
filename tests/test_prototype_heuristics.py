# ruff: noqa: E501
"""생성 MVP 시제품의 슬롭 지양·휴리스틱 회귀 테스트.

- 카드 중첩 없음: 입력·버튼·대화상자·접는 패널 외 네 면 테두리 박스 0
- 배지는 상태 값에만
- 기본 화면에 개발자 용어 없음(설명 패널 안에만)
- 375/768/1440px 가로 넘침 0, list_detail은 넓은 화면에서만 2열
- 키보드만으로 입력·제출
- 기존 계약: 토큰 색(:root 밖 Hex 없음)·style= 금지·고대비·aria-errormessage·design_hash
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import Page

from mvp_mcp.data.spec.design_artifact_renderer import DesignArtifactRendererImpl
from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.domain.spec.design_direction import build_product_design_contract
from mvp_mcp.domain.spec.documentation_model import (
    DocumentationIntake,
    PrototypePreview,
    UiSurface,
)
from mvp_mcp.domain.spec.model import ProjectType, SpecDraft

DEV_TERMS = ("NON-SSOT", "Mock", "계약", "hash", "DRAFT", "FR-", "TASK-")
STATUS_BADGES = {"예정", "완료", "대기", "새로 추가"}
CONTROL_TAGS = {"INPUT", "TEXTAREA", "SELECT", "BUTTON", "DIALOG", "DETAILS", "PROGRESS"}

INTAKE: dict[str, object] = {
    "work_type": "new_project",
    "solution_family": ["product_application"],
    "primary_surface": ["web_app", "android_app"],
    "app_domain_hint": ["booking", "fitness"],
    "pain_detail": "전화·카톡 예약이라 시간이 겹쳐요.",
    "desired_change": "회원이 직접 예약하고 트레이너가 출석을 확인한다.",
    "initial_audience": "customers",
    "tech_stack": "ai_recommended",
}


def _files(tasks: str, features: list[str]) -> dict[str, str]:
    contract = build_product_design_contract(
        INTAKE,
        {
            "design_frequent_user_tasks": tasks,
            "design_visual_tone": ["trust"],
            "design_color_choice": "#1F7A6D",
            "design_web_behavior": "mobile",
        },
    )
    draft = SpecDraft(
        project_type=ProjectType.ETC,
        user_request="동네 헬스장 PT 예약",
        design_contract=contract,
        features=features,
        documentation=DocumentationIntake(
            ui_surfaces=[UiSurface.WEB], prototype_preview=PrototypePreview.REQUIRED
        ),
    )
    return DesignArtifactRendererImpl(HtmlPrototypeRenderer()).render(draft)


SAMPLES = {
    "workspace": (
        "1) 회원이 빈 시간 찾아 예약 2) 트레이너가 오늘 일정 확인 3) 예약 취소",
        ["트레이너 가용 시간 등록", "30분 단위 예약", "출석 체크"],
    ),
    "list_detail": ("오늘 매출 기록, 날짜별 기록 검토, 기록 검색, 처리 진행률", []),
}


def _open(page: Page, tmp_path: Path, sample: str) -> str:
    html = _files(*SAMPLES[sample])["prototype/index.html"]
    path = tmp_path / f"{sample}.html"
    path.write_bytes(html.encode("utf-8"))
    page.goto(path.as_uri())
    return html


@pytest.mark.parametrize("sample", sorted(SAMPLES))
def test_no_card_boxes_status_only_badges_and_no_dev_terms(
    page: Page, tmp_path: Path, sample: str
) -> None:
    _open(page, tmp_path, sample)
    boxed = page.evaluate(
        """(controls) => [...document.querySelectorAll('body *')].filter(el => {
            if (controls.includes(el.tagName) || el.closest('details.about')) return false;
            const s = getComputedStyle(el);
            return ['Top','Right','Bottom','Left'].every(side => parseFloat(s['border' + side + 'Width']) > 0);
        }).map(el => el.tagName + '.' + el.className)""",
        sorted(CONTROL_TAGS),
    )
    assert boxed == []
    badges = set(page.locator(".badge").all_text_contents())
    assert badges and badges <= STATUS_BADGES
    visible = page.locator("body").inner_text()
    assert [term for term in DEV_TERMS if term in visible] == []
    page.locator("details.about summary").click()
    about = page.locator("details.about").inner_text()
    assert "NON-SSOT" in about and "계약 해시" in about


@pytest.mark.parametrize("sample", sorted(SAMPLES))
@pytest.mark.parametrize("width", [375, 768, 1440])
def test_no_horizontal_overflow(page: Page, tmp_path: Path, sample: str, width: int) -> None:
    page.set_viewport_size({"width": width, "height": 900})
    _open(page, tmp_path, sample)
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0


def test_list_detail_is_two_columns_only_on_wide_screens(page: Page, tmp_path: Path) -> None:
    columns = "() => getComputedStyle(document.querySelector('.areas')).gridTemplateColumns.split(' ').length"
    page.set_viewport_size({"width": 1440, "height": 900})
    _open(page, tmp_path, "list_detail")
    assert page.locator("main").get_attribute("data-layout") == "list_detail"
    assert page.evaluate(columns) == 2
    page.set_viewport_size({"width": 375, "height": 900})
    assert page.evaluate(columns) == 1


def test_keyboard_only_submit_reaches_success(page: Page, tmp_path: Path) -> None:
    _open(page, tmp_path, "workspace")
    page.locator("body").click(position={"x": 2, "y": 2})
    for _ in range(10):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.tagName") == "INPUT":
            break
    assert page.evaluate("document.activeElement.tagName") == "INPUT"
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
    page.keyboard.type("화요일 19:00")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    assert "완료" in (page.locator(".screen-status").first.text_content() or "")


def test_prototype_keeps_token_colors_and_validation_contract() -> None:
    files = _files(*SAMPLES["workspace"])
    html = files["prototype/index.html"]
    design_hash = re.search(r'"design_hash": "([a-f0-9]{64})"', files["docs/design-tokens.json"])
    assert design_hash is not None and design_hash.group(1) in html
    assert not re.search(r"<[^>]+\sstyle\s*=", html, flags=re.IGNORECASE)
    for required in ("var(--brand)", 'data-theme="high_contrast"', "aria-errormessage="):
        assert required in html
    css = html[html.index("<style>") : html.index("</style>")]
    outside_root = re.sub(r":root(\[[^\]]*\])?\{[^}]*\}", "", css)
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", outside_root)
    body = html[html.index("</style>") :]
    assert not re.search(r"#[0-9A-Fa-f]{6}\b", body.split('id="mvpmcp-prototype-metadata"')[0])
