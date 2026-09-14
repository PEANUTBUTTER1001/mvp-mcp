# MCP 공개 Tool 전환 감사

> 상태: **2026-09-14 갱신 — canonical 12개만 공개, Run-scoped candidate lifecycle breaking cutover·구형 Tool 10개 제거 완료**
>
> 작성일: 2026-09-12

## 목적과 경계

이 감사는 현재 공개 MCP Tool의 역할·대체 가능성·삭제 조건을 고정한다. 2026-09-13 사용자가
client-native 질문 UI 전환을 승인해 localhost Web Wizard, URL elicitation/continuation probe와 그 호환
Tool을 제거하고, 질문 schema → UI capability가 있는 호스트 → 구조화 답변 제출 계약으로 바꿨다. 현재 Codex Desktop Default 모드는 그 native form UI를 제공하지 않는다.

2026-09-14 source 계약은 선택형 schema에 `allow_other`, `other_label`, `max_selections`를 추가했다.
선택지는 최대 20개이고, 기타를 포함한 선택 답은 `{"selected": [...], "other_text": "..."}`로 정규화한다.
기존 `str`·`list[str]` 답변도 계속 유효하다. Codex Plan·Claude·Gemini·Antigravity 연동 지침은 이 schema를
각 클라이언트의 native 질문 Tool로 1~3문항씩 수집한다. 2026-09-14 새 Codex Plan task의 실제 수용은
`safe_auto_apply` 문서 저장까지 확인됐고 (`확인됨`), Claude·Gemini·Antigravity의 실제 수용은 아직
`미확인`이다.

## Canonical Tool 12개

| Tool | 역할 | 상태 |
|---|---|---|
| `documentation_start_adaptive_wizard` | Run 생성과 1·2차 질문 schema 반환 | canonical |
| `documentation_submit_adaptive_wizard_answers` | 호스트 UI가 수집한 구조화 답변 원자 저장·2차 제출 뒤 candidate 발급 | canonical |
| `documentation_wizard_run_status` | Wizard Run·현재 열린 질문 schema 읽기 전용 복구 | canonical |
| `documentation_update_candidate_requirements` | Run 소유 stable-ID 요구사항 갱신 | canonical |
| `documentation_update_candidate_architecture` | Run 소유 상세 설계 계약 갱신 | canonical |
| `documentation_update_candidate_delivery` | Run 소유 TASK·TEST 계약 갱신 | canonical |
| `documentation_record_candidate_test_run` | Run 소유 append-only TEST 증거 기록 | canonical |
| `documentation_record_candidate_release` | Run 소유 append-only 릴리스 기록 | canonical |
| `documentation_validate_package` | 후보 package 구조·추적성 검증 | canonical |
| `documentation_preview_package` | 후보 diff·preview와 조건부 안전 반영 | canonical |
| `documentation_apply_package` | `manual_apply` 후보 반영 | canonical |
| `documentation_package_status` | candidate·preview·manifest 상태 조회 | canonical |

## 2026-09-13 breaking cutover에서 제거한 Tool

| Tool | 분류 | 대체 또는 보류 근거 | 처분 상태 |
|---|---|---|---|
| `documentation_start` | 구형 생성 진입 | `documentation_start_adaptive_wizard` + 답변 제출 Tool | 제거 완료 |
| `answer_question` | 구형 단일 답변 제출 | `documentation_submit_adaptive_wizard_answers` | 제거 완료 |
| `documentation_validate` | 구형 spec 검증 | `documentation_validate_package` | 제거 완료 |
| `documentation_preview` | 구형 spec preview | `documentation_preview_package` | 제거 완료 |
| `documentation_apply` | 구형 spec 반영 | `documentation_apply_package` | 제거 완료 |
| `documentation_register_requirements` | spec_id 요구사항 관리 | `documentation_update_candidate_requirements` | 제거 완료 |
| `documentation_register_architecture` | spec_id 설계 관리 | `documentation_update_candidate_architecture` | 제거 완료 |
| `documentation_register_delivery` | spec_id TASK·TEST 관리 | `documentation_update_candidate_delivery` | 제거 완료 |
| `documentation_record_test_run` | append-only TEST 실행 기록 | `documentation_record_candidate_test_run` | 제거 완료 |
| `documentation_record_release` | append-only 릴리스 기록 | `documentation_record_candidate_release` | 제거 완료 |

이 이름은 더 이상 등록되지 않으므로 구형 클라이언트 호출은 MCP의 Tool 미존재 오류를 받는다. 새 문서 생성은
canonical adaptive 흐름과 Run-scoped candidate lifecycle만 사용한다.

## 2026-09-13에 제거한 Tool·경로

| 제거 대상 | 대체 | 이유 |
|---|---|---|
| `documentation_collect_intake`, `ask_web_question`, `ask_next_web_question`, `ask_elicitation_question` | `documentation_start_adaptive_wizard` + `documentation_submit_adaptive_wizard_answers` | 서버가 브라우저를 열거나 답변을 대기하지 않음 |
| Local Web Form 3종·loopback HTTP/CSRF | 질문 schema를 표시할 수 있는 호스트 UI | 사용자가 Web 창을 열지 않음. 현재 Codex Desktop Default 모드는 native form UI 미지원 |
| URL elicitation/continuation probe와 `safe_async_tool` 특례 | 없음 | 제품 경로가 아니며 자동 재개 계약을 제공하지 못함 |

## cutover 검증 결과

1. canonical 12개 Tool만 `main.py::build()`에 등록되며, 제거 대상 10개는 Tool inventory 가드레일에서 부재를 확인한다.
2. Composition Root MCP E2E는 lifecycle 5개 기록 → candidate sync → validate → preview와 `generate_only`의 `.mvpmcp/` 무반영을 확인한다.
3. Run-scoped lifecycle은 SQLite Run에만 구조화 계약·idempotency receipt·이전 적용 이력을 보관하고, candidate Markdown과 `.mvpmcp/`는 기존 validate/preview/apply 경계를 유지한다.
