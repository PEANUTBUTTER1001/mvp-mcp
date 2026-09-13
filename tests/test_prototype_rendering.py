"""생성 HTML을 실제 Chromium에서 검증한다."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.domain.spec.model import (
    DesignContract,
    ErrorState,
    ProjectType,
    ScreenSpec,
    SpecDraft,
    UserFlow,
)


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
            ],
            user_flows=[
                UserFlow(
                    name="라벨 저장",
                    steps=["이미지 선택", "라벨 지정", "저장 확인"],
                    exception_paths=["지원하지 않는 파일은 오류 목록으로 이동"],
                )
            ],
            error_states=[
                ErrorState(
                    trigger="이미지 읽기 실패",
                    user_message="이미지를 열 수 없습니다.",
                    recovery="다른 파일을 선택하거나 오류 목록을 확인한다.",
                )
            ],
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
    assert page.get_by_text("라벨 저장", exact=True).is_visible()
    assert "지원하지 않는 파일은 오류 목록으로 이동" in (
        page.locator(".recovery").nth(0).text_content() or ""
    )
    assert "이미지를 열 수 없습니다." in (
        page.get_by_role("heading", name="오류·복구 안내").locator("..").text_content() or ""
    )
    assert page.locator('input[type="text"]').count() == 0
    assert page.get_by_text("Mock으로 확인할 지원 상태", exact=True).first.is_visible()
    assert page_errors == []
    assert network_requests == []

    first = page.get_by_role("tab", name="라벨링 작업대")
    second = page.get_by_role("tab", name="학습 현황")
    assert first.get_attribute("aria-selected") == "true"
    second.click()
    assert page.locator("#screen-1").is_visible()
    assert second.get_attribute("aria-selected") == "true"
    page.locator("#screen-1 .action").click()
    assert page.locator("#screen-1 .status").get_attribute("data-state") == "error"
    assert page.locator("#state-picker-1").get_attribute("aria-invalid") == "true"

    page.locator("#state-1-1").check()
    assert page.locator("#state-picker-1").get_attribute("aria-invalid") == "false"
    page.locator("#screen-1 .action").click()
    assert "학습 현황 화면에서 실행 중 상태를 Mock으로 확인했습니다." in (
        page.locator("#screen-1 .status").text_content() or ""
    )
    assert page.locator("#screen-1 .status").get_attribute("data-state") == "success"

    first.click()
    page.locator("#state-0-2").check()
    page.locator("#screen-0 .action").click()
    assert "라벨링 작업대 화면에서 저장됨 상태를 Mock으로 확인했습니다." in (
        page.locator("#screen-0 .status").text_content() or ""
    )

    second.focus()
    page.keyboard.press("ArrowLeft")
    assert first.get_attribute("aria-selected") == "true"

    page.locator("body").click(position={"x": 5, "y": 5})
    for _ in range(8):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.classList.contains('nav')"):
            break
    assert page.evaluate("document.activeElement.classList.contains('nav')")
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.locator("main").evaluate("element => element.scrollWidth <= element.clientWidth")
