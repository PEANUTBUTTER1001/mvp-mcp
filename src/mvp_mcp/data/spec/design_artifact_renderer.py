"""디자인 계약을 문서·토큰·프로토타입 산출물로 렌더링한다."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json

from mvp_mcp.domain.spec.model import DesignDirection, SpecDraft

from .html_prototype_renderer import HtmlPrototypeRenderer


class DesignArtifactRendererImpl:
    def __init__(self, prototype: HtmlPrototypeRenderer) -> None:
        self._prototype = prototype

    def render(self, draft: SpecDraft) -> dict[str, str]:
        design = draft.design_contract
        if design is None or design.visual_direction is None:
            return {}
        direction = design.visual_direction
        design_hash = self._design_hash(draft, direction)
        tokens = self._tokens(direction, design_hash)
        return {
            "docs/MVPDESIGN.md": self._document(draft, direction, design_hash),
            "docs/design-tokens.json": json.dumps(tokens, ensure_ascii=False, indent=2) + "\n",
            "prototype/index.html": self._prototype.render(draft, design_hash, tokens),
            "prototype/REVIEW.md": self._review(direction, design_hash),
        }

    @staticmethod
    def _design_hash(draft: SpecDraft, direction: DesignDirection) -> str:
        snapshot = {
            "user_request": draft.user_request,
            "direction": direction.model_dump(mode="json"),
            "screens": [
                screen.model_dump(mode="json")
                for screen in (draft.design_contract.screens if draft.design_contract else [])
            ],
        }
        encoded = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _tokens(direction: DesignDirection, design_hash: str) -> dict[str, object]:
        return {
            "version": 1,
            "design_hash": design_hash,
            "color": DesignArtifactRendererImpl._palette(direction.seed_color),
            "spacing": {"1": "4px", "2": "8px", "3": "12px", "4": "16px", "6": "24px", "8": "32px"},
            "typography": {
                "display": {"size": "28px", "weight": 700},
                "title": {"size": "20px", "weight": 700},
                "body": {"size": "16px", "weight": 400},
                "label": {"size": "14px", "weight": 600},
                "meta": {"size": "13px", "weight": 400},
            },
            "radius": {"control": "8px", "sheet": "12px", "card": "0px"},
            "breakpoints": {"compact": "0-767px", "medium": "768-1199px", "expanded": "1200px+"},
        }

    @staticmethod
    def _palette(seed_color: str) -> dict[str, dict[str, str]]:
        """Derive selected-color roles while retaining neutral and state semantics."""

        def blend(first: str, second: str, ratio: float) -> str:
            first_rgb = tuple(int(first[index : index + 2], 16) for index in (1, 3, 5))
            second_rgb = tuple(int(second[index : index + 2], 16) for index in (1, 3, 5))
            mixed = tuple(
                round(first_value * (1 - ratio) + second_value * ratio)
                for first_value, second_value in zip(first_rgb, second_rgb, strict=True)
            )
            return "#" + "".join(f"{value:02X}" for value in mixed)

        light_primary = seed_color.upper()
        return {
            "light": {
                "primary": light_primary,
                "on_primary": "#FFFFFF",
                "primary_container": blend(light_primary, "#FFFFFF", 0.84),
                "surface": "#FFFBF7",
                "surface_muted": "#F3F4F1",
                "text_primary": "#1C1C1A",
                "text_secondary": "#5F615D",
                "outline": "#D4D6D0",
            },
            "dark": {
                "primary": blend(light_primary, "#FFFFFF", 0.58),
                "on_primary": blend(light_primary, "#000000", 0.70),
                "primary_container": blend(light_primary, "#000000", 0.65),
                "surface": "#151515",
                "surface_muted": "#232323",
                "text_primary": "#F4F1EC",
                "text_secondary": "#C8C6C0",
                "outline": "#4A4A46",
            },
            "state": {
                "success": "#157347",
                "warning": "#9A6700",
                "error": "#B42318",
                "info": "#175CD3",
                "disabled": "#A6A8A2",
                "focus_ring": "#0B5FFF",
            },
        }

    def _document(self, draft: SpecDraft, direction: DesignDirection, design_hash: str) -> str:
        palette = self._palette(direction.seed_color)
        light = palette["light"]
        dark = palette["dark"]
        state = palette["state"]
        screens = draft.design_contract.screens if draft.design_contract else []
        screen_briefs = (
            "\n\n".join(
                f"### 화면: {screen.name}\n\n- 사용자 목표: {screen.purpose}\n- 가장 중요한 정보: {', '.join(screen.ui_elements)}\n- 주 행동: {direction.primary_user_job}\n- 레이아웃: {direction.layout_archetype.value}\n- 상태: {' / '.join(screen.states)}\n- 모바일 변화: compact에서는 단일 열과 명시적 화면 이동을 사용한다.\n- 접근성 기준: 키보드 포커스, 명암 대비, 상태 텍스트를 제공한다."
                for screen in screens
            )
            or f"### 화면: 핵심 작업\n\n- 사용자 목표: {direction.primary_user_job}\n- 가장 중요한 정보: 작업 상태와 다음 행동\n- 주 행동: {direction.primary_user_job}\n- 레이아웃: {direction.layout_archetype.value}\n- 상태: 기본 / 빈 상태 / 로딩 / 오류 / 성공\n- 모바일 변화: compact에서는 단일 열을 사용한다.\n- 접근성 기준: 색상 외 상태 문구와 키보드 포커스를 제공한다."
        )
        avoid = "\n".join(f"- {item}" for item in direction.avoid_patterns)
        return f"""# MVPDESIGN.md

- design_hash: `{design_hash}`

## 1. 디자인 결정 요약

- 상태: CONFIRMED / RECOMMENDED / UNRESOLVED
- 제품 카테고리: {direction.product_category}
- 핵심 사용자: {direction.core_user}
- 자주 하는 작업: {', '.join(direction.frequent_user_tasks)}
- 가장 중요한 사용자 과업: {direction.primary_user_job}
- 디자인 한 줄 방향: {direction.visual_tone}
- 결정 근거: {direction.rationale.get("layout_archetype", "사용자 과업을 우선한다.")}

## 2. 경험 원칙

1. 사용자의 주 작업이 첫 화면에서 즉시 시작되어야 한다.
2. 상태·진행·실패·복구 방법을 항상 보여 준다.
3. 장식보다 정보 위계와 조작의 명확성을 우선한다.

## 3. 플랫폼과 인터랙션 문법

- 대상: {draft.documentation.ui_surfaces[0].value if draft.documentation.ui_surfaces else "화면 없음"}
- 플랫폼 문법: {direction.platform_grammar}
- 입력: 터치 / 키보드 / 포인터
- 접근성: 키보드, 명암 대비, 텍스트 확대, 스크린 리더

## 4. 레이아웃 전략

- 레이아웃 유형: {direction.layout_archetype.value}
- 선택 근거: {direction.rationale.get("layout_archetype", "사용자 과업을 우선한다.")}
- 내비게이션 구조: 핵심 목적지만 노출하고, 현재 작업 위치를 명확히 표시한다.
- 데스크톱 전환 규칙: expanded에서는 목록·상세 또는 작업대 보조 영역을 함께 표시한다.
- 모바일 전환 규칙: compact에서는 단일 열을 사용하고, 보조 탐색은 별도 화면 또는 시트로 연다.
- 콘텐츠 최대 폭과 정보 밀도: 본문 최대 760px, 비교가 필요한 값은 정렬된 행으로 표시한다.

## 5. 컬러 시스템

### 5.1 기준 색상

- Seed / Main color: `{direction.seed_color}`
- 상태: {direction.color_status.value}
- 역할: 핵심 행동, 현재 선택, 주요 강조
- 사용 금지: 오류·성공·경고 의미에 메인 컬러를 재사용하지 않는다.

### 5.2 테마별 팔레트

| 역할 | Light | Dark | 용도 |
| --- | --- | --- | --- |
| primary | {light["primary"]} | {dark["primary"]} | 주요 행동·선택 |
| on-primary | {light["on_primary"]} | {dark["on_primary"]} | primary 위 텍스트·아이콘 |
| primary-container | {light["primary_container"]} | {dark["primary_container"]} | 선택된 영역·약한 강조 |
| surface | {light["surface"]} | {dark["surface"]} | 기본 화면 표면 |
| surface-muted | {light["surface_muted"]} | {dark["surface_muted"]} | 보조 영역 |
| text-primary | {light["text_primary"]} | {dark["text_primary"]} | 핵심 텍스트 |
| text-secondary | {light["text_secondary"]} | {dark["text_secondary"]} | 설명·보조 텍스트 |
| outline | {light["outline"]} | {dark["outline"]} | 경계·구분선 |

### 5.3 상태 색상

| 상황 | 색상 역할 | 표현 방식 |
| --- | --- | --- |
| 성공 | success `{state["success"]}` | 완료 문구·상태 아이콘·필요한 범위의 배경 |
| 경고 | warning `{state["warning"]}` | 주의·검토 상태 |
| 오류 | error `{state["error"]}` | 실패 원인·복구 행동 |
| 정보 | info `{state["info"]}` | 중립 안내·도움말 |
| 비활성 | disabled `{state["disabled"]}` | 행동 불가 이유를 텍스트로 함께 제공 |
| 포커스 | focus-ring `{state["focus_ring"]}` | 키보드 포커스를 명확히 표시 |

### 5.4 조건별 규칙

- Light / Dark / 고대비 모드에서 각각 대비 기준을 충족한다.
- Hover / Pressed / Selected / Disabled / Focus 상태를 역할별로 정의한다.
- 오류·경고·성공은 색만으로 구분하지 않고 텍스트·아이콘·상태 메시지를 함께 제공한다.
- 컴포넌트는 Hex 값을 직접 쓰지 않고 역할 토큰만 사용한다.

## 6. 컴포넌트 사용 규칙

- Primary / Secondary / Destructive action은 행동의 위험도와 복구 가능성에 맞게 구분한다.
- 카드 사용 조건: 독립 작업 단위에만 사용하며 일반 목록을 모두 카드로 감싸지 않는다.
- 목록·테이블 사용 조건: 탐색은 목록, 비교는 정렬된 행 또는 테이블을 사용한다.
- 폼과 입력 검증: 오류 원인과 고치는 방법을 해당 입력 가까이에 표시한다.
- 로딩·빈 상태·오류·성공·되돌리기: 상태와 다음 행동을 함께 제공한다.
- 모달·시트·팝오버 사용 조건: 위험 행동 확인은 모달, 모바일 보조 탐색은 시트, 짧은 도움말은 인라인 또는 팝오버를 사용한다.

## 7. 화면별 설계 브리프

{screen_briefs}

## 8. AI식 디자인 방지 규칙

{avoid}
- 실제 제품 데이터·흐름과 무관한 장식 요소를 넣지 않는다.

## 9. 프로토타입 범위와 수용 기준

- prototype이 보여 줄 사용자 흐름: {direction.primary_user_job}
- mock 범위: 화면별 기본 / 빈 상태 / 로딩 / 오류 / 성공
- 실제 동작으로 오해하면 안 되는 항목: 서버 저장, 인증, 외부 연동, 결제
- 시각 검토 기준: 375px, 768px, 1440px에서 주요 행동·상태·탐색이 보인다.
- 구현 전 확인 항목: UNRESOLVED 결정과 실제 데이터·권한 범위를 확인한다.

## 10. 구현 준수 규칙

- 구현 시작 전 MVPDESIGN.md와 design-tokens.json을 읽는다.
- 새 화면은 7절의 화면 브리프를 먼저 추가한다.
- 디자인 변경은 문서와 코드에서 함께 반영한다.
- 구현 결과는 문서의 레이아웃·상태·접근성 기준으로 검토한다.

## 11. 구현 토큰

- 반응형 구간: compact 0–767px / medium 768–1199px / expanded 1200px 이상
- 간격 토큰: 4px / 8px / 12px / 16px / 24px / 32px
- 모서리 토큰: control 8px / sheet 12px / card 0px
- 타이포그래피 토큰: display 28px / title 20px / body 16px / label 14px / meta 13px

## 12. 화면 상태 매트릭스

| 상태 | 반드시 보여 줄 것 | 사용자 복구 행동 |
| --- | --- | --- |
| 기본 | 주 행동과 현재 정보 | 작업 시작 |
| 빈 상태 | 원인과 다음 행동 | 항목 추가 또는 조건 변경 |
| 로딩 | 진행 상태와 중복 실행 방지 | 기다리기 |
| 오류 | error `{state["error"]}` | 재시도 또는 수정 |
| 성공 | success `{state["success"]}` | 계속 작업 또는 되돌리기 |

## 13. 콘텐츠와 표기 규칙

- 버튼은 `저장`, `추가`, `수정`, `삭제`처럼 동사 중심으로 쓴다.
- `시작하기`, `인사이트 보기`, `더 알아보기` 같은 일반적 문구를 사용하지 않는다.
- 빈 상태에는 원인, 현재 상태, 다음 행동을 함께 쓴다.
- 성공 메시지는 수행한 행동과 대상을 구체적으로 쓴다.

## 14. 에이전트 검증 게이트

- HTML 생성 전 UNRESOLVED 결정을 임의로 확정하지 않는다.
- HTML 생성 후 화면 브리프와 상태 매트릭스를 375px, 768px, 1440px에서 확인한다.
- 직접 Hex 값·임의 여백값 대신 design-tokens.json 역할 토큰을 사용한다.
- 8절 금지 규칙 위반 여부를 확인하고 REVIEW.md에 기록한다.
"""

    @staticmethod
    def _review(direction: DesignDirection, design_hash: str) -> str:
        return f"""# Prototype review

- design_hash: `{design_hash}`
- 레이아웃: `{direction.layout_archetype.value}`
- 반응형 우선순위: `{direction.responsive_priority.value}`

| 뷰포트 | 확인 항목 | 상태 |
| --- | --- | --- |
| 375px | 단일 열, 주요 행동, 상태 문구, 키보드 포커스 | NOT RUN |
| 768px | 탐색과 상세 정보 전환, 텍스트 확대 | NOT RUN |
| 1440px | 정보 밀도, 목록·상세 또는 작업대 구조 | NOT RUN |

## Mock 범위

- 실제 서버 저장, 인증, 결제, 외부 API 호출은 수행하지 않는다.
- HTML은 문서 계약을 검토하기 위한 NON-SSOT 시제품이다.
"""
