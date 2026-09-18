"""브랜드 seed를 접근 가능한 semantic palette로 변환하는 순수 도메인 규칙."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, pi, pow, sin, sqrt

_STATUS_HUES = {
    "success": 145.0,
    "warning": 82.0,
    "error": 28.0,
    "info": 255.0,
}
_CONTRAST_PAIRS = (
    ("primary", "on_primary"),
    ("primary_container", "on_primary_container"),
    ("surface", "text_primary"),
    ("surface", "text_secondary"),
    ("success", "on_success"),
    ("warning", "on_warning"),
    ("error", "on_error"),
    ("info", "on_info"),
)


@dataclass(frozen=True)
class PaletteBuild:
    """Renderer가 직렬화할 palette와 생성 근거."""

    themes: dict[str, dict[str, str]]
    intent: str
    primary_adjusted: bool
    adjustment_reason: str | None
    contrast_pairs: dict[str, dict[str, float]]


def build_palette(seed_color: str, *, visual_tone: str, product_category: str) -> PaletteBuild:
    """OKLCH 톤을 사용해 브랜드·중립·상태 역할을 결정적으로 만든다."""

    seed = normalize_hex(seed_color)
    seed_l, seed_c, seed_h = hex_to_oklch(seed)
    intent = palette_intent(visual_tone, product_category)
    neutral_chroma = 0.008 if intent == "calm_operational" else 0.016
    status_shift = 8.0 if intent == "warm_service" else 0.0

    light_primary, light_on, light_adjusted = accessible_role(seed_l, seed_c, seed_h, 4.5)
    dark_primary, dark_on, dark_adjusted = accessible_role(0.78, seed_c, seed_h, 4.5)
    high_primary, high_on, high_adjusted = accessible_role(seed_l, seed_c, seed_h, 7.0)
    light = _theme(
        seed_h,
        neutral_chroma,
        status_shift,
        primary=light_primary,
        on_primary=light_on,
        surface_lightness=0.985,
        dark=False,
        high_contrast=False,
    )
    dark = _theme(
        seed_h,
        neutral_chroma,
        status_shift,
        primary=dark_primary,
        on_primary=dark_on,
        surface_lightness=0.13,
        dark=True,
        high_contrast=False,
    )
    high_contrast = _theme(
        seed_h,
        neutral_chroma,
        status_shift,
        primary=high_primary,
        on_primary=high_on,
        surface_lightness=1.0,
        dark=False,
        high_contrast=True,
    )
    themes = {"light": light, "dark": dark, "high_contrast": high_contrast}
    contrast_pairs = {
        theme: {
            f"{background}/{foreground}": round(
                contrast_ratio(values[background], values[foreground]), 2
            )
            for background, foreground in _CONTRAST_PAIRS
        }
        for theme, values in themes.items()
    }
    adjusted = light_adjusted or dark_adjusted or high_adjusted
    return PaletteBuild(
        themes=themes,
        intent=intent,
        primary_adjusted=adjusted,
        adjustment_reason=(
            "선택한 색상과 전경색의 WCAG 대비를 충족하도록 UI용 primary tone을 조정했다."
            if adjusted
            else None
        ),
        contrast_pairs=contrast_pairs,
    )


def palette_intent(visual_tone: str, product_category: str) -> str:
    """기존 디자인 결정에서 팔레트의 중립·상태 조화 방향을 고른다."""

    source = f"{visual_tone} {product_category}".lower()
    if any(term in source for term in ("식당", "음식", "예약", "서비스", "따뜻")):
        return "warm_service"
    if any(term in source for term in ("금융", "의료", "보안", "신뢰", "정확")):
        return "trustworthy_precision"
    if any(term in source for term in ("창작", "커뮤니티", "콘텐츠", "놀이")):
        return "expressive_creative"
    return "calm_operational"


def normalize_hex(value: str) -> str:
    """유효한 #RRGGBB만 canonical uppercase로 정규화한다."""

    if len(value) != 7 or not value.startswith("#"):
        raise ValueError("brand seed는 #RRGGBB 형식이어야 합니다.")
    try:
        int(value[1:], 16)
    except ValueError as error:
        raise ValueError("brand seed는 #RRGGBB 형식이어야 합니다.") from error
    return value.upper()


def contrast_ratio(first: str, second: str) -> float:
    """WCAG 상대 휘도 대비비를 계산한다."""

    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    lighter, darker = max(first_luminance, second_luminance), min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def relative_luminance(value: str) -> float:
    channels = [int(normalize_hex(value)[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def hex_to_oklch(value: str) -> tuple[float, float, float]:
    """sRGB Hex를 OKLCH로 변환한다."""

    channels = [int(normalize_hex(value)[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    red, green, blue = [_to_linear(channel) for channel in channels]
    l_value = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    m_value = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    s_value = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    l_root, m_root, s_root = (_cuberoot(l_value), _cuberoot(m_value), _cuberoot(s_value))
    lightness = 0.2104542553 * l_root + 0.793617785 * m_root - 0.0040720468 * s_root
    a_value = 1.9779984951 * l_root - 2.428592205 * m_root + 0.4505937099 * s_root
    b_value = 0.0259040371 * l_root + 0.7827717662 * m_root - 0.808675766 * s_root
    chroma = sqrt(a_value**2 + b_value**2)
    hue = degrees(atan2(b_value, a_value)) % 360
    return lightness, chroma, hue


def oklch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    """색역 밖 chroma를 줄이며 OKLCH를 displayable sRGB Hex로 바꾼다."""

    bounded_lightness = min(1.0, max(0.0, lightness))
    for attempt in range(20):
        candidate_chroma = chroma * (0.86**attempt)
        red, green, blue = _oklch_to_linear_rgb(bounded_lightness, candidate_chroma, hue)
        if all(-0.0001 <= channel <= 1.0001 for channel in (red, green, blue)):
            return _rgb_to_hex(red, green, blue)
    red, green, blue = _oklch_to_linear_rgb(bounded_lightness, 0.0, hue)
    return _rgb_to_hex(red, green, blue)


def accessible_role(
    lightness: float, chroma: float, hue: float, minimum: float
) -> tuple[str, str, bool]:
    """가장 가까운 톤과 흑백 전경 조합 중 요구 대비를 충족하는 값을 고른다."""

    candidates = [(lightness, chroma)]
    candidates.extend((tone / 100, chroma) for tone in range(5, 100, 5))
    for candidate_lightness, candidate_chroma in sorted(
        candidates, key=lambda item: abs(item[0] - lightness)
    ):
        color = oklch_to_hex(candidate_lightness, candidate_chroma, hue)
        foreground = max(("#000000", "#FFFFFF"), key=lambda item: contrast_ratio(color, item))
        if contrast_ratio(color, foreground) >= minimum:
            return color, foreground, color != oklch_to_hex(lightness, chroma, hue)
    raise ValueError("접근 가능한 primary tone을 만들 수 없습니다.")


def _theme(
    brand_hue: float,
    neutral_chroma: float,
    status_shift: float,
    *,
    primary: str,
    on_primary: str,
    surface_lightness: float,
    dark: bool,
    high_contrast: bool,
) -> dict[str, str]:
    minimum = 7.0 if high_contrast else 4.5
    surface = (
        "#FFFFFF"
        if high_contrast and not dark
        else oklch_to_hex(surface_lightness, neutral_chroma, brand_hue)
    )
    surface_muted = (
        surface
        if high_contrast
        else oklch_to_hex(
            surface_lightness - 0.035 if dark else surface_lightness - 0.025,
            neutral_chroma,
            brand_hue,
        )
    )
    surface_raised = (
        surface
        if high_contrast
        else oklch_to_hex(
            surface_lightness + 0.045 if dark else min(1.0, surface_lightness + 0.01),
            neutral_chroma,
            brand_hue,
        )
    )
    text_primary = (
        "#000000"
        if high_contrast
        else oklch_to_hex(0.12 if not dark else 0.94, neutral_chroma, brand_hue)
    )
    text_secondary = (
        "#1A1A1A"
        if high_contrast
        else oklch_to_hex(0.39 if not dark else 0.76, neutral_chroma, brand_hue)
    )
    primary_container, on_primary_container, _ = accessible_role(
        0.94 if not dark else 0.28,
        0.06,
        brand_hue,
        minimum,
    )
    values = {
        "primary": primary,
        "on_primary": on_primary,
        "primary_container": primary_container,
        "on_primary_container": on_primary_container,
        "surface": surface,
        "surface_muted": surface_muted,
        "surface_raised": surface_raised,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "outline": (
            "#000000"
            if high_contrast
            else oklch_to_hex(0.55 if not dark else 0.48, neutral_chroma, brand_hue)
        ),
        "outline_strong": (
            "#000000"
            if high_contrast
            else oklch_to_hex(0.42 if not dark else 0.68, neutral_chroma, brand_hue)
        ),
        "disabled_surface": (
            "#E6E6E6"
            if high_contrast
            else oklch_to_hex(0.9 if not dark else 0.24, neutral_chroma, brand_hue)
        ),
        "disabled_content": (
            "#454545"
            if high_contrast
            else oklch_to_hex(0.48 if not dark else 0.65, neutral_chroma, brand_hue)
        ),
        "disabled_outline": (
            "#454545"
            if high_contrast
            else oklch_to_hex(0.7 if not dark else 0.42, neutral_chroma, brand_hue)
        ),
        "focus_ring": "#000000" if high_contrast else _focus_color(brand_hue, dark),
        "primary_hover": _shift_primary(primary, -0.05 if not dark else 0.05),
        "primary_pressed": _shift_primary(primary, -0.10 if not dark else 0.10),
        "primary_selected": primary_container,
    }
    for role, base_hue in _STATUS_HUES.items():
        hue = (base_hue + status_shift) % 360
        status, on_status, _ = accessible_role(0.48 if not dark else 0.75, 0.15, hue, minimum)
        container, _, _ = accessible_role(0.93 if not dark else 0.28, 0.08, hue, minimum)
        values[role] = status
        values[f"{role}_container"] = container
        values[f"on_{role}"] = on_status
    return values


def _focus_color(hue: float, dark: bool) -> str:
    color, _, _ = accessible_role(0.66 if dark else 0.48, 0.16, hue, 3.0)
    return color


def _shift_primary(value: str, difference: float) -> str:
    lightness, chroma, hue = hex_to_oklch(value)
    return oklch_to_hex(min(1.0, max(0.0, lightness + difference)), chroma, hue)


def _to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _to_srgb(channel: float) -> float:
    bounded = min(1.0, max(0.0, channel))
    if bounded <= 0.0031308:
        return 12.92 * bounded
    return float(1.055 * pow(bounded, 1 / 2.4) - 0.055)


def _cuberoot(value: float) -> float:
    return float(pow(value, 1 / 3) if value >= 0 else -pow(-value, 1 / 3))


def _oklch_to_linear_rgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    angle = hue * pi / 180
    a_value = chroma * cos(angle)
    b_value = chroma * sin(angle)
    l_root = lightness + 0.3963377774 * a_value + 0.2158037573 * b_value
    m_root = lightness - 0.1055613458 * a_value - 0.0638541728 * b_value
    s_root = lightness - 0.0894841775 * a_value - 1.291485548 * b_value
    l_value, m_value, s_value = l_root**3, m_root**3, s_root**3
    return (
        4.0767416621 * l_value - 3.3077115913 * m_value + 0.2309699292 * s_value,
        -1.2684380046 * l_value + 2.6097574011 * m_value - 0.3413193965 * s_value,
        -0.0041960863 * l_value - 0.7034186147 * m_value + 1.707614701 * s_value,
    )


def _rgb_to_hex(red: float, green: float, blue: float) -> str:
    return "#" + "".join(f"{round(_to_srgb(channel) * 255):02X}" for channel in (red, green, blue))
