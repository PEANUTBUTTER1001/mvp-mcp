"""사용자 선택 색상에서 접근 가능한 semantic palette를 만드는 회귀."""

from __future__ import annotations

import pytest

from mvp_mcp.domain.spec.palette import build_palette, contrast_ratio, normalize_hex


@pytest.mark.parametrize("seed", ["#F4C542", "#123456", "#E91E63", "#6B7280"])
def test_palette_keeps_brand_seed_and_meets_theme_contrast(seed: str) -> None:
    palette = build_palette(
        seed,
        visual_tone="차분하고 정돈된 업무 도구",
        product_category="일반 업무 관리",
    )

    assert palette.themes["light"]["primary"].startswith("#")
    for theme, roles in palette.themes.items():
        minimum = 7.0 if theme == "high_contrast" else 4.5
        for background, foreground in (
            ("primary", "on_primary"),
            ("primary_container", "on_primary_container"),
            ("surface", "text_primary"),
            ("surface", "text_secondary"),
            ("success", "on_success"),
            ("warning", "on_warning"),
            ("error", "on_error"),
            ("info", "on_info"),
        ):
            assert contrast_ratio(roles[background], roles[foreground]) >= minimum


def test_palette_uses_product_context_for_intent() -> None:
    palette = build_palette(
        "#B45309",
        visual_tone="따뜻하고 빠른 현장 운영",
        product_category="식당 운영 기록",
    )

    assert palette.intent == "warm_service"


@pytest.mark.parametrize("value", ["0F766E", "#FFF", "#GGGGGG", "#0F766E00"])
def test_normalize_hex_rejects_invalid_brand_seed(value: str) -> None:
    with pytest.raises(ValueError, match="#RRGGBB"):
        normalize_hex(value)
