"""생성 HTML을 실제 Chromium에서 검증한다."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.domain.spec.model import DesignContract, ProjectType, ScreenSpec, SpecDraft


def _prototype(path: Path) -> None:
    draft = SpecDraft(
        project_type=ProjectType.ETC,
        user_request="<script>alert('x')</script> 이미지 도구",
        design_contract=DesignContract(
            screens=[
                ScreenSpec(
                    name="라벨링 작업대",
                    route="/label",
                    purpose="이미지 라벨을 지정한다.",
                    ui_elements=["캔버스", "저장 버튼"],
                    states=["빈 상태", "편집 중", "저장됨"],
                ),
                ScreenSpec(
                    name="학습 현황",
                    route="/train",
                    purpose="mock 학습 상태를 확인한다.",
                    ui_elements=["진행률", "중단 버튼"],
                    states=["대기", "실행 중", "완료"],
                ),
            ]
        ),
    )
    html = HtmlPrototypeRenderer().render(draft, "a" * 64)
    path.write_bytes(html.encode("utf-8"))


def test_prototype_is_interactive_accessible_and_offline(page: Page, tmp_path: Path) -> None:
    html_path = tmp_path / "index.html"
    _prototype(html_path)
    page_errors: list[str] = []
    network_requests: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "request",
        lambda request: (
            network_requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            else None
        ),
    )

    page.goto(html_path.as_uri())
    assert page.locator(".banner").get_by_text("NON-SSOT PROTOTYPE").is_visible()
    assert page.locator("script").count() == 2
    assert page.locator("body").text_content() is not None
    assert "alert('x')" in (page.locator("h1").text_content() or "")
    assert page_errors == []
    assert network_requests == []

    second = page.locator(".nav").nth(1)
    second.click()
    assert page.locator("#screen-1").is_visible()
    page.locator("#input-1").fill("샘플")
    page.locator("#screen-1 .action").click()
    assert "Mock 처리 완료" in (page.locator("#screen-1 .status").text_content() or "")

    page.locator("body").click(position={"x": 5, "y": 5})
    for _ in range(8):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.classList.contains('nav')"):
            break
    assert page.evaluate("document.activeElement.classList.contains('nav')")
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.locator("main").evaluate("element => element.scrollWidth <= element.clientWidth")
