"""생성 MVP 시제품 HTML을 실제 Chromium에서 검증한다 (실제 UI·상태·키보드·오프라인)."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, expect

from mvp_mcp.data.spec.html_prototype_renderer import HtmlPrototypeRenderer
from mvp_mcp.domain.spec.model import (
    DesignContract,
    ErrorState,
    ProjectType,
    ScreenSpec,
    SpecDraft,
    UserFlow,
)


def _draft() -> SpecDraft:
    return SpecDraft(
        project_type=ProjectType.ETC,
        user_request="<script>alert('x')</script> PT 예약",
        design_contract=DesignContract(
            screens=[
                ScreenSpec(
                    name="예약",
                    route="/booking",
                    purpose="회원이 빈 시간을 골라 예약한다.",
                    ui_elements=[
                        "회원이 빈 시간 찾아 예약",
                        "오늘 일정 확인",
                        "회원 검색",
                        "예약 삭제",
                    ],
                    states=["기본", "빈 상태", "저장 중", "오류", "저장됨"],
                ),
                ScreenSpec(
                    name="학습 현황",
                    route="/train",
                    purpose="학습 상태를 확인한다.",
                    ui_elements=["진행률", "중단 버튼"],
                    states=["대기", "실행 중", "완료"],
                ),
            ],
            user_flows=[
                UserFlow(
                    name="예약 저장",
                    steps=["빈 시간 선택", "예약", "확인"],
                    exception_paths=["겹치는 시간은 다시 선택"],
                )
            ],
            error_states=[
                ErrorState(
                    trigger="같은 시간 중복",
                    user_message="이미 예약된 시간이에요.",
                    recovery="다른 시간을 골라 주세요.",
                )
            ],
        ),
    )


def _open(page: Page, tmp_path: Path) -> tuple[list[str], list[str]]:
    path = tmp_path / "index.html"
    path.write_bytes(HtmlPrototypeRenderer().render(_draft(), "a" * 64).encode("utf-8"))
    errors: list[str] = []
    requests: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "request",
        lambda request: (
            requests.append(request.url)
            if request.url.startswith(("http://", "https://"))
            else None
        ),
    )
    page.goto(path.as_uri())
    return errors, requests


def test_prototype_renders_real_ui_offline_and_escaped(page: Page, tmp_path: Path) -> None:
    errors, requests = _open(page, tmp_path)

    assert "alert('x')" in (page.locator("h1").text_content() or "")
    assert page.locator("script").count() == 2
    assert page.get_by_text("시제품이에요 · 입력한 내용은 저장되지 않아요").is_visible()
    screen = page.locator("#screen-0")
    assert screen.get_by_role("button", name="예약", exact=True).is_visible()
    assert screen.get_by_role("textbox", name="빈 시간", exact=True).is_visible()
    assert screen.locator(".rows .row").count() == 3
    assert screen.get_by_role("searchbox", name="회원 검색").is_visible()
    assert screen.get_by_role("button", name="삭제", exact=True).is_visible()
    page.get_by_role("tab", name="학습 현황").click()
    assert page.locator("#screen-1 progress").is_visible()
    assert errors == [] and requests == []


def test_form_validates_succeeds_and_undoes(page: Page, tmp_path: Path) -> None:
    _open(page, tmp_path)
    screen = page.locator("#screen-0")
    field = screen.get_by_role("textbox", name="빈 시간", exact=True)

    screen.get_by_role("button", name="예약", exact=True).click()
    expect(field).to_have_attribute("aria-invalid", "true")
    message_id = field.get_attribute("aria-errormessage")
    assert "빈 시간" in (page.locator(f"#{message_id}").text_content() or "")
    assert "다른 시간을 골라 주세요." in (screen.locator(".screen-status").text_content() or "")

    field.fill("화요일 19:00")
    screen.get_by_role("button", name="예약", exact=True).click()
    expect(field).to_have_attribute("aria-invalid", "false")
    assert "예약 완료" in (screen.locator(".screen-status").text_content() or "")
    assert screen.locator(".row-title").first.text_content() == "화요일 19:00"
    screen.get_by_role("button", name="되돌리기").click()
    assert screen.locator(".row").count() == 3
    expect(field).to_have_value("화요일 19:00")


def test_search_filters_rows_and_delete_confirms_with_undo(page: Page, tmp_path: Path) -> None:
    _open(page, tmp_path)
    screen = page.locator("#screen-0")
    screen.get_by_role("searchbox", name="회원 검색").fill("2")
    assert screen.locator(".search-count").text_content() == "결과 1개"
    screen.get_by_role("searchbox", name="회원 검색").fill("")

    screen.get_by_role("button", name="삭제", exact=True).click()
    dialog = screen.locator("dialog")
    assert dialog.is_visible()
    dialog.get_by_role("button", name="그만두기").click()
    assert not dialog.is_visible()
    screen.get_by_role("button", name="삭제", exact=True).click()
    dialog.get_by_role("button", name="삭제").click()
    assert "예약 삭제 완료" in (screen.locator(".screen-status").text_content() or "")
    assert screen.locator(".row:visible").count() == 2
    screen.get_by_role("button", name="되돌리기").click()
    assert screen.locator(".row:visible").count() == 3


def test_state_preview_reaches_empty_loading_error_and_success(page: Page, tmp_path: Path) -> None:
    _open(page, tmp_path)
    about = page.locator("details.about")
    assert about.get_attribute("open") is None
    about.locator("summary").click()
    preview = page.locator('.state-preview[data-screen="0"]')
    screen = page.locator("#screen-0")

    preview.get_by_label("빈 상태").check()
    assert screen.locator(".empty").is_visible()
    assert screen.locator(".rows").is_hidden()
    screen.get_by_role("button", name="빈 시간 예약부터 시작하기").click()
    expect(screen.get_by_role("textbox", name="빈 시간", exact=True)).to_be_focused()

    preview.get_by_label("저장 중").check()
    assert screen.get_attribute("aria-busy") == "true"
    assert screen.get_by_role("button", name="예약", exact=True).is_disabled()

    preview.get_by_label("오류").check()
    expect(screen.get_by_role("textbox", name="빈 시간", exact=True)).to_have_attribute(
        "aria-invalid", "true"
    )

    preview.get_by_label("저장됨").check()
    assert "방금 처리했어요" in (screen.locator(".screen-status").text_content() or "")
    assert screen.get_attribute("aria-busy") is None


def test_tabs_keyboard_focus_and_high_contrast(page: Page, tmp_path: Path) -> None:
    _open(page, tmp_path)
    first = page.get_by_role("tab", name="예약")
    second = page.get_by_role("tab", name="학습 현황")
    assert first.get_attribute("aria-selected") == "true"
    first.focus()
    page.keyboard.press("ArrowRight")
    assert second.get_attribute("aria-selected") == "true"
    expect(second).to_be_focused()
    assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
    assert page.locator('.state-preview[data-screen="1"]').count() == 1
    page.keyboard.press("Home")
    assert first.get_attribute("aria-selected") == "true"

    page.locator("details.about summary").click()
    toggle = page.locator(".theme-toggle")
    assert toggle.text_content() == "고대비로 보기"
    toggle.click()
    assert page.locator("html").get_attribute("data-theme") == "high_contrast"
    assert toggle.get_attribute("aria-pressed") == "true"
