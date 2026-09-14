# PROGRESS

## 2026-09-14 — 새 Codex Plan 실제 문서 저장 수용 확인

- 상태: **완료** (`확인됨`)
- 범위: 새 Codex `/plan` task에서 `$mvpmcp 식당 리뷰 SNS 앱 MVP 계획을 잡아줘.`를 실행한 사용자 수용 기록을
  읽기 전용으로 점검했다. 이 기록은 source 품질 게이트를 다시 실행하거나 제품 코드를 만들지 않았다.
- 결과: native 질문 묶음 제출 뒤 Run `run-Ie_LD2OjUrCy3fj3DiVU2Xpr`이 `safe_auto_apply` 정책으로
  `APPLIED`가 됐고, 문서 7개와 manifest가
  `C:\\Users\\user\\Documents\\rrr\\.mvpmcp\\adaptive-run-Ie_LD2OjUrCy3fj3DiVU2Xpr\\`에 저장됐다.
  candidate·preview는 검증 통과했고 충돌은 없었다 (`확인됨`).
- 경계: 출력에는 Android 제품 코드·빌드·테스트·배포가 `NOT RUN`으로 명시됐고, 해당 실행에서 제품 코드 Tool
  호출은 확인되지 않았다 (`확인됨`). `Plan implementation — Status: running`은 MCP 산출물이 아닌 Codex 호스트
  UI 상태로 보이며 제품 구현 시작이 아니라는 판단은 `추론`이다.
- 남은 한계: Codex Desktop Default 모드의 native form UI 미지원은 변하지 않았다. Claude·Gemini·Antigravity의
  실제 수용과 Codex UI 상태 표기의 개선 필요성은 아직 `미확인`이며 별도 승인 전에는 작업하지 않는다.

---

## 2026-09-14 10:14:19 +09:00 — 기본 `.mvpmcp` 문서 패키지 자동 저장·격리

- 시작 시각: 2026-09-14 10:14:19 +09:00
- 목표: native 질문 전에 저장 방식을 묻지 않고, Adaptive Wizard 완료 뒤 문서 패키지를 프로젝트
  `.mvpmcp/<구분 가능한 run 폴더>/`에 자동 반영하되 기존 문서를 덮어쓰지 않으며 제품 코드는 만들지 않는다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. write policy·적용 경로 계약 분석 | 🟢 완료 | 기존 safe auto-apply와 Run별 exporter 격리 경로를 재사용하기로 확정 |
| 2. 도메인·exporter 자동 반영 및 격리 경로 구현 | 🟢 완료 | `.mvpmcp/<spec_id>/`로 반영; 기존 루트·다른 Run 보존 회귀 통과 |
| 3. client Skill·문서 종료 문구 정합화 | 🟢 완료 | 네 client의 기본 저장·명시적 제품 코드 시작 문구와 README·HANDOFF 정합화 |
| 4. 회귀·품질 게이트·개인 플러그인 배포 | 🟢 완료 | 품질 게이트 73 passed; `mvpmcp@personal` `0.2.0+codex.20260914012647` 재설치·cache 검증 |

- 구현: 새 Run은 `write_policy`를 생략해도 `safe_auto_apply`로 시작하며, 1차·2차 질문에 저장 방식 문항을
  넣지 않는다. 충돌 없는 검증·preview 뒤에는 문서만 `<project_root>/.mvpmcp/<spec_id>/`에 원자 반영한다.
  같은 Run의 관리 문서는 갱신할 수 있지만, 기존 `.mvpmcp` 루트와 다른 Run 폴더는 경로가 분리되어 보존된다.
- client 계약: Codex·Claude·Gemini·Antigravity는 기본 문서 저장 완료를
  `문서 패키지 저장 완료 (.mvpmcp에 문서만 생성됨)`으로 알리고 제품 코드 구현 여부를 자동으로 묻지 않는다.
  `MVP 제품 코드 구현 시작`만 별도 제품 구현 승인이다. 명시적 후보 전용 요청만 `generate_only`를 사용한다.
- 검증: Ruff·Black·mypy 통과, 전체 pytest **73 passed**. Black/pytest cache 쓰기 권한 경고만 있었고
  결과에는 영향이 없었다. 원본·설치 cache plugin validation과 저장소·원본·cache Skill SHA-256 일치도 확인했다.
- 배포: 동기화 전 원본 세 배포 파일은 `C:\\Users\\user\\plugins\\mvpmcp.backup-20260914-102534`에 보존했고,
  공식 재설치한 personal plugin 버전은 `0.2.0+codex.20260914012647`이다.
- 완료 시각: 2026-09-14 10:27:29 +09:00. 새 Skill은 새 Codex `/plan` task에서 로드되며, 기존 대화에는
  소급 적용되지 않는다.

---

## 2026-09-14 09:27:02 +09:00 — P0 개인 플러그인 배포·설치본 검증

- 시작 시각: 2026-09-14 09:27:02 +09:00
- 목표: 검증된 `generate_only` 문서 저장 경계와 native 질문 지침을 personal `mvpmcp` 원본에
  동기화하고 공식 cachebuster·재설치로 Codex 설치본에 반영한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. marketplace·원본 플러그인 사전 점검 | 🟢 완료 | marketplace `personal`·원본 유효성 확인; 저장소/원본 Skill SHA-256 불일치 확인 |
| 2. 원본 배포 파일 임시 백업 | 🟢 완료 | `mvpmcp.backup-20260914-092702`에 세 파일 복사·SHA-256 일치 확인 |
| 3. 원본 동기화·플러그인 검증 | 🟢 완료 | 원본 Skill hash가 저장소와 일치; plugin·UTF-8 Skill 검증 통과 |
| 4. cachebuster·공식 재설치 | 🟢 완료 | `0.2.0+codex.20260914003007` 발급 후 `mvpmcp@personal` 공식 설치 성공 |
| 5. 설치본 hash·실행 정의 확인 | 🟢 완료 | 저장소·원본·설치 cache Skill SHA-256 일치; cache plugin 검증 통과 |
| 6. 새 `/plan` 수용 확인 안내·기록 | 🟠 연기 | 새 Skill·MCP Tool은 새 Plan task에서만 로드됨; 현재 Default task에서는 UI 수용 테스트 불가 |

- 배포 결과: `mvpmcp@personal`은 installed, enabled 상태이며 `0.2.0+codex.20260914003007`으로 설치됐다.
  `.mcp.json`은 현재 작업 루트의 `.venv-exec/Scripts/mvp-mcp.exe`를 가리키고, 설치 cache도
  `validate_plugin.py`를 통과했다.
- 검증 보완: Windows 기본 cp949 인코딩으로 Skill 빠른 검증이 한 번 실패했지만, `PYTHONUTF8=1` 재실행에서
  `Skill is valid!`를 확인했다. `git diff --check`는 이 작업 루트가 Git 저장소가 아니어서 적용할 수 없었다.
- 수용 경계: 재설치한 Skill과 Tool은 기존 대화에 주입되지 않는다. 사용자가 새 Codex `/plan` task에서 대표 요청을
  시작해야 native `request_user_input` UI와 generate_only 종료 확인을 수행할 수 있다.
- 품질 게이트: Ruff 통과, Black은 75개 파일 변경 없음, mypy는 61 source files 통과, pytest는 전용 basetemp에서
  **72 passed**였다. Black cache와 pytest cache 쓰기 권한 경고는 결과에 영향을 주지 않았다.
- 완료 시각: 2026-09-14 09:33:03 +09:00. 설치·정적/회귀 검증은 완료했고, 새 `/plan` UI 수용은 사용자 새 task가
  필요한 별도 호스트 확인으로 연기한다.

---

## 2026-09-14 09:16:05 +09:00 — generate_only 문서 저장 경계·오발 코드 구현 방지

- 시작 시각: 2026-09-14 09:16:05 +09:00
- 목표: `generate_only` 문서 후보 저장 뒤 Codex Plan의 일반 구현 요청이 실제 제품 코드 작성으로 이어지지 않도록
  source·설치 플러그인 지침을 보완하고, 사용자가 원치 않은 SNS MVP 파일 7개를 정확히 제거한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 원치 않은 SNS MVP 파일 범위 확인·제거 | 🟢 완료 | 지정된 7개 경로와 두 작업 루트에서 모두 부재 확인 — 제거할 잔여 파일 없음 |
| 2. generate_only 완료·후속 구현 차단 계약 | 🟢 완료 | Codex·Claude·Gemini·Antigravity 지침, README·HANDOFF, 회귀에 명시 |
| 3. 개인 플러그인 동기화·재설치 | 🟠 연기 | 외부 plugin 원본 변경은 이전 범위 제외 항목이라 별도의 명시 승인 필요 |
| 4. 검증·수용 테스트 안내 | 🟢 완료 | Ruff·Black·mypy·대상 26 passed·전체 pytest 72 passed; 새 Plan 대화 수용만 설치본 동기화 뒤 가능 |

- 삭제 확인: 사용자가 명시한 `C:\\Users\\user\\Documents\\rrr\\src\\sns_mvp`의 6개 파일과
  `tests\\test_sns_mvp.py`는 존재하지 않았다. `C:\\Users\\user\\Documents\\rrr`와 현재 작업 루트에서도
  `sns_mvp`·`test_sns_mvp.py`를 재탐색했지만 잔여 파일이 없어 추가 삭제를 수행하지 않았다.
- 구현: 모든 client Skill에 `generate_only` candidate·preview 완료를 `문서 후보 저장 완료 (코드 구현 없음)`으로
  표시하도록 추가했다. Codex의 `PLEASE IMPLEMENT THIS PLAN`과 일반 계획 구현 요청은 문서 저장 승인으로 취급하지
  않으며, `문서 후보만 유지`·`문서 반영만 별도 요청`·`실제 제품 코드 구현` 중 마지막 선택 전에는 제품 소스를
  만들거나 바꾸지 않는다.
- 검증: 대상 회귀 26 passed, 전체 pytest 72 passed, Ruff·Black·mypy가 통과했다. Black·pytest cache 접근 경고만
  있었고 결과에는 영향을 주지 않았다.
- 설치 경계: `scripts/sync_codex_plugin.py`로 `C:\\Users\\user\\plugins\\mvpmcp` 원본을 바꾸고 cachebuster·
  재설치하려 했으나, 이전에 플러그인 동기화·재설치가 명시적으로 제외됐던 외부 변경이라 현재 승인 정책에서 거절됐다.
  source 변경은 완료됐지만 설치 cache에는 아직 반영되지 않았다.

---

## 2026-09-14 00:38:21 +09:00 — Cross-client native 선택·복수선택·기타 답변 Wizard

- 시작 시각: 2026-09-14 00:38:21 +09:00
- 목표: Adaptive Wizard가 선택형 기타 입력과 최대 선택 수를 구조적으로 보존하고, Codex Plan·Claude·Antigravity의 native 질문 UI에서 동일한 단계별 답변 경험을 제공하도록 공통 계약과 연동 지침을 구현한다.
- 범위 제외: Codex Desktop UI·`/plan` 자동 활성화, 별도 App Server host·웹 폼·URL elicitation, 서버 모델 API worker·timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 플러그인 동기화·재설치, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 선택·기타 답변 schema 및 Run 정규화 | 🟢 완료 | 기존 문자열·배열 Run과 호환되는 구조화 선택 답변·snapshot JSON 직렬화 구현 |
| 2. intake 정책·candidate 문서 변환 | 🟢 완료 | `app_domain_hint` 기타 입력, 조건부 분기·candidate 문자열화 반영 |
| 3. Codex·Claude·Antigravity native 질문 지침 | 🟢 완료 | Codex Plan 선행 조건과 Codex·Claude·Gemini·Antigravity 공통 1~3문항·기타 규칙 반영 |
| 4. 회귀·문서·전체 품질 게이트 | 🟢 완료 | 대상 회귀 25 passed, Ruff·Black·mypy 통과, 전체 pytest 71 passed, diff check 통과 |
| 5. 플러그인 동기화·실클라이언트 수용 | 🟠 연기 | 사용자 승인 범위 밖; source 구현 검증 후 별도 승인 필요 |

- 구현: `AdaptiveWizardQuestion`에 `allow_other`·`other_label`·`max_selections`를 추가하고, 선택값과 기타
  입력을 보존하는 `AdaptiveWizardSelectionAnswer`를 도입했다. 일반 `str`·`list[str]` 제출 형식은 그대로
  유지하며, 조건부 표시·candidate 입력 변환·SQLite 재개·Run snapshot JSON도 구조화 답변을 처리한다.
- client 계약: Codex는 사용자가 `/plan` 또는 `Shift+Tab`으로 Plan을 연 뒤 `request_user_input`이 있을 때만
  Run을 시작한다. Claude·Gemini·Antigravity 지침도 native 질문 capability를 사전 확인한 뒤, 조건부 문항을
  1~3개씩 수집한다. 4~20개 선택지는 `다음 선택지`로, 복수 선택은 포함/제외로 수집하며 기타는
  `{"selected": [...], "other_text": "..."}`로 제출한다.
- 검증: `.venv-exec\\Scripts\\python.exe -m pytest -q --basetemp
  C:\\Users\\Public\\Documents\\ESTsoft\\CreatorTemp\\mvp-cross-client-005 tests/test_adaptive_wizard.py
  tests/test_client_native_question_guidance.py tests/test_guardrails.py`는 25 passed,
  전체 pytest는 71 passed였다. Ruff·Black·mypy와 `git diff --check`도 통과했다. Black·pytest cache 접근
  경고와 Git CRLF 경고는 결과에 영향을 주지 않았다.
- 격리: Codex Desktop UI·`/plan` 자동 전환·App Server host·웹 form·서버 worker·timeout 자동 재개·플러그인
  동기화/재설치·사용자 `.mvpmcp/` 변경은 수행하지 않았다. 설치되지 않은 source 지침의 실제 host 수용은
  별도 승인 뒤에만 확인한다.

---

## 2026-09-13 21:27:19 +09:00 — Adaptive Wizard run_id 재개 계약 보완

- 시작 시각: 2026-09-13 21:27:19 +09:00
- 목표: `INTAKE_OPEN` Adaptive Wizard를 전체 `request_key` 없이 `run_id`만으로 안전하게 재개할 수 있도록 현재 질문 schema 조회 계약·Skill 지침·회귀를 최소 보완한다.
- 범위 제외: 후보 생성·`.mvpmcp` 적용, 서버 모델 API worker, timeout 자동 재개, `safe_auto_apply`·`manual_apply`, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 플러그인 재설치, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. run status·질문 schema 계약 및 영향 범위 확인 | 🟢 완료 | Run에는 `intake_questions`가 영속되지만 공유 snapshot에서만 누락됨을 확인 |
| 2. run_id 기반 재개 최소 구현·Skill 지침 정합화 | 🟢 완료 | snapshot에 `intake_questions`를 추가하고 Codex Skill·README·HANDOFF 재개 지침을 정합화 |
| 3. 회귀·전체 품질 게이트·진행 기록 | 🟢 완료 | 대상 MCP 회귀 9 passed, Ruff·Black·mypy 및 전체 pytest 64 passed, diff check 통과 |

- 구현: 공유 Run snapshot에 영속 `intake_questions`를 직렬화해 `documentation_wizard_run_status(run_id)`가 `INTAKE_OPEN`의 재개 질문 schema를 직접 반환하도록 했다. `DESIGN_OPEN`의 기존 `design_questions` 반환은 유지했다.
- 재개 계약: Codex Skill은 중단된 Run을 `run_id`로 status 조회한 뒤 현재 단계 질문만 native UI에 표시하도록 바꿨다. `request_key` 재입력·새 Run 생성을 요구하지 않으며, 이 저장소 변경은 설치된 플러그인 cache를 동기화·재설치하지 않는다.
- 검증: 대상 MCP 회귀는 9 passed, `.venv-exec` Ruff·Black·mypy와 전체 pytest는 각각 통과했고 pytest는 64 passed였다. `git diff --check`도 공백 오류 없이 통과했다. Black·pytest의 사용자 cache 접근 경고와 Git의 CRLF 경고는 결과에 영향을 주지 않았다.
- 격리: candidate writer·validate/preview/apply Tool과 사용자 `.mvpmcp`는 호출·변경하지 않았다.
- 실제 수용 확인: 같은 `run_id`의 `documentation_wizard_run_status`가 `INTAKE_OPEN`과 `intake_questions`를 반환하고 새 Run·답변·candidate·`.mvpmcp` 변경이 없음을 확인했다. Codex Desktop Default 모드는 native form UI를 지원하지 않아 질문 표시·답변 제출은 진행하지 않았다 (`확인됨`).

---

## 2026-09-13 20:44:44 +09:00 — Codex 플러그인 동기화·native 수용 종단 검증

- 시작 시각: 2026-09-13 20:44:44 +09:00
- 목표: 원본 `mvpmcp` 플러그인을 현재 Skill·manifest 계약으로 공식 동기화·재설치하고, 임시 `generate_only` native Adaptive Wizard 종단 흐름을 검증한다.
- 범위 제외: 서버 모델 API worker, timeout 자동 재개, `safe_auto_apply`·`manual_apply`, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 원본 플러그인·공식 설치 경로 사전 확인 | 🟢 완료 | `personal` marketplace가 `C:\\Users\\user\\plugins\\mvpmcp` 원본을 가리키며 설치·활성 상태 |
| 2. 원본 동기화·공식 재설치 | 🟢 완료 | source 동기화·cachebuster·`mvpmcp@personal` 재설치 및 설치본 검증 완료 |
| 3. 임시 `generate_only` native 종단 수용 검증 | 🟠 연기 | 공식 절차상 새 Codex 대화가 필요하며, 현재 요청에는 새 task 생성 권한이 없음 |
| 4. 격리·회귀·인수인계 기록 | 🟢 완료 | 사용자 `.mvpmcp` 무변경, source·설치본 validation 및 결과 기록 완료 |

- 사전 확인: `read_marketplace_name.py`는 `personal`을 반환했고 `validate_plugin.py`는 원본을 통과시켰다. `codex plugin list`는 `mvpmcp@personal`이 설치·활성 상태이며 원본 `C:\\Users\\user\\plugins\\mvpmcp`을 사용함을 확인했다. 원본 Skill은 저장소 원본과 SHA-256이 달라 동기화가 필요하다.
- 동기화·재설치: 원본을 `C:\\Users\\user\\plugins\\mvpmcp.backup-20260913-204444`에 백업한 뒤 `scripts/sync_codex_plugin.py`로 Skill·manifest·`.mcp.json`을 갱신했다. 전용 helper가 `0.2.0+codex.20260913114857` cachebuster를 발급했고 `codex plugin add mvpmcp@personal`이 새 설치 root를 반환했다.
- 설치본 검증: 새 cache Skill의 SHA-256은 저장소 Skill과 일치하고, manifest는 native-question 설명과 새 버전, `.mcp.json`은 현재 `.venv-exec/Scripts/mvp-mcp.exe`를 가리킨다. 원본과 설치본 모두 `validate_plugin.py`를 통과했다.
- 수용 검증 경계: 공식 OpenAI 안내에 따라 새 대화에서 대표 요청을 실행해야 신규 Skill·MCP Tool이 로드된다. 현재 대화의 plugin snapshot을 재사용하거나 새 task를 임의 생성하지 않았으므로, 임시 `generate_only` native 질문·`DRAFT_READY`·candidate validate/preview 종단 수용은 새 task 생성의 명시 요청 후 수행한다. `safe_auto_apply`·`manual_apply`와 사용자 `.mvpmcp`는 호출·변경하지 않았다.

---

## 2026-09-13 20:39:48 +09:00 — Codex 플러그인 manifest native 흐름 정합화

- 시작 시각: 2026-09-13 20:39:48 +09:00
- 목표: 향후 공식 동기화가 생성할 Codex 플러그인 manifest 설명을 현재 2단계 Adaptive native 질문 흐름과 일치시킨다.
- 범위 제외: 원본 플러그인 번들·설치 cache 수정, 플러그인 재설치, MCP 서버 재시작, 서버 모델 API worker, timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. manifest 설명 계약 정정 | 🟢 완료 | “web Wizard”를 native 질문 흐름으로 교체 |
| 2. 정적 검증·현재 문서 갱신 | 🟢 완료 | help·Ruff·Black·mypy·전체 pytest 63 passed |
| 3. 설치 동기화 경계 확인 | 🟢 완료 | 원본 bundle/재설치 승인 없이는 설치본을 변경하지 않음 |

- 구현: `scripts/sync_codex_plugin.py`가 생성하는 manifest `longDescription`을 “two-stage adaptive native-question Wizard”로 정정했다. 향후 공식 동기화 때 설치 UI 설명도 현재 client-native 질문 계약을 따른다.
- 검증: `.venv-exec\\Scripts\\python.exe scripts\\sync_codex_plugin.py --help`, Ruff, Black, mypy `src`, 전체 pytest를 실행해 각각 통과했다. pytest 63 passed, Black·pytest cache 접근 경고만 있었고 결과에는 영향을 주지 않았다.
- 경계: 원본 플러그인 번들, 설치 cache, MCP 서버, 사용자 `.mvpmcp`는 변경하지 않았다. 공식 cachebuster·재설치와 native E2E는 원본 bundle/경로 및 명시적 재설치 승인 후에만 수행한다.

---

## 2026-09-13 20:34:32 +09:00 — Codex Skill 동기화 승인 준비

- 시작 시각: 2026-09-13 20:34:32 +09:00
- 목표: 플러그인 재설치 없이 저장소 Skill·설치 cache·manifest·MCP 실행 정의를 대조해, 향후 최소 동기화의 변경 대상·검증·복구 절차를 확정한다.
- 범위 제외: 플러그인 재설치·cache 수정, MCP 서버 재시작, 서버 모델 API worker, timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 배포 원본·설치 cache·실행 정의 대조 | 🟢 완료 | Skill SHA-256 불일치, cache는 현재 `.venv-exec` 서버 실행 경로를 유지 |
| 2. 최소 동기화·검증·복구 절차 확정 | 🟢 완료 | 원본의 3개 배포 파일만 대상이며 cache 직접 수정은 금지 |
| 3. 승인 게이트와 현재 문서 기록 | 🟢 완료 | 원본 번들 경로와 스크립트 설명 정정을 사전 조건으로 기록 |

- 대조 결과: 저장소 `integrations/codex/SKILL.md`(5,535 bytes, SHA-256 `4871B188…`)와 설치 cache Skill(3,463 bytes, `3ED325BE…`)은 다르다. cache manifest는 `0.2.0+codex.20260910103953`이며 `.mcp.json`으로 현재 `.venv-exec/Scripts/mvp-mcp.exe`를 실행한다.
- 최소 동기화 대상: `scripts/sync_codex_plugin.py`는 **원본 플러그인**의 `skills/mvpmcp/SKILL.md`·`.mcp.json`·`.codex-plugin/plugin.json`만 갱신한다. README 계약대로 설치 cache는 직접 수정하지 않고 공식 cachebuster·validation·재설치가 후속 단계다.
- 선행 조건: 동기화 스크립트의 manifest `longDescription`에는 아직 “adaptive web Wizard”가 있으므로 native 질문 흐름으로 정정하는 별도 소스 변경 승인이 먼저 필요하다. 또한 `C:\\Users\\user\\.codex\\plugins`에서는 원본 `mvpmcp` 디렉터리를 찾지 못했고 설치 cache만 확인했다. 재설치 승인 때 원본 플러그인 번들 또는 경로가 필요하다.
- 재설치 승인 후 검증·복구: 원본 3개 파일과 저장소 Skill hash, manifest 설명, `.mcp.json` 실행 파일 경로를 대조한 뒤 공식 cachebuster·validation·재설치를 수행한다. 설치 뒤 hash·canonical Tool 목록·임시 `generate_only` native E2E를 확인한다. 실패하면 cache를 직접 고치지 않고 현재 설치 릴리스로 되돌려 재설치한다.

---

## 2026-09-13 20:28:47 +09:00 — Codex 네이티브 Adaptive Wizard 수용 검증

- 시작 시각: 2026-09-13 20:28:47 +09:00
- 목표: 설치된 Codex Skill과 저장소의 현재 계약을 읽기 전용으로 대조하고, 임시 프로젝트에서 `generate_only` Adaptive Wizard의 네이티브 질문·재개·candidate 검증/미리보기 흐름을 수용 검증한다.
- 범위 제외: 플러그인 재설치, `safe_auto_apply`, 서버 모델 API worker, timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 대규모 파일 이동, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 설치 Skill·공개 MCP 계약 읽기 전용 대조 | 🟢 완료 | 설치 Skill은 구형 Tool 계약, 연결된 서버 Tool은 현재 canonical 계약 |
| 2. 임시 `generate_only` 네이티브 수용 흐름 실행 | 🟠 연기 | 재설치 금지 조건에서 설치 Skill이 구형 `documentation_collect_intake` 흐름을 지시해 현재 서버와 호환되지 않음 |
| 3. 격리·문서화·회귀 검증 | 🟢 완료 | writer Tool을 호출하지 않았고, 대상 회귀 24 passed 및 HANDOFF 갱신 |

- 설치본 대조: `0.2.0+codex.20260910103953`의 cache Skill은 구형 `documentation_collect_intake`·`documentation_start`를 지시한다. 반면 같은 설치본 `.mcp.json`이 실행하는 `.venv-exec/Scripts/mvp-mcp.exe`에는 현재 `documentation_start_adaptive_wizard` 등 canonical Tool이 공개되어 있다. 재설치 없이 이 불일치를 해소할 수 없으므로 Skill 주도 native UI 수용 검증은 연기한다.
- 회귀: `.venv-exec\\Scripts\\pytest.exe -q --basetemp C:\\Users\\Public\\Documents\\ESTsoft\\CreatorTemp\\pytest-adaptive-acceptance-regression-20260913-202847 tests\\test_adaptive_wizard.py tests\\test_candidate_package.py`는 24 passed를 반환했다. pytest cache 접근 경고만 있었고 테스트 결과에는 영향을 주지 않았다.
- 격리: writer Tool·`safe_auto_apply`·`manual_apply`를 호출하지 않았고, 임시 `project_root`도 만들지 않았다. 따라서 이번 작업은 기존 사용자 `.mvpmcp`를 변경하지 않았다.

---

## 2026-09-13 20:20:49 +09:00 — 구형 채팅형 adapter 체인 물리 정리

- 시작 시각: 2026-09-13 20:20:49 +09:00
- 목표: 공개 등록이 없는 `clarify_intent`·`get_missing_info`·`scope_mvp` adapter와 전용 질문·formatter 체인을 제거하고, canonical 12개 Tool·Adaptive Wizard·`spec://` Resource를 보존한다.
- 범위 제외: `ScopeMvpUseCase`, `SpecDraft`, `SpecRepository`, Resource Query, 템플릿의 활성 데이터, 서버 모델 API worker, timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 플러그인 재설치, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 전용 adapter·질문 체인 참조 재확인 | 🟢 완료 | `Question`·`QUESTION_BANK`까지 고립 체인임을 확인 |
| 2. 고립 코드·테스트·가드레일 정리 | 🟢 완료 | adapter 3개·전용 질문/formatter 체인과 legacy 회귀를 제거, 부재 가드 추가 |
| 3. 현재 상태 문서·전체 품질 게이트 | 🟢 완료 | 대상 21 passed, 전체 63 passed; Ruff·Black·mypy·diff check 통과 |

- 구현 완료: `clarify_intent`·`get_missing_info`·`scope_mvp` adapter, 전용 `Question`·질문 데이터·formatter·legacy 회귀를 제거했다. `ScopeMvpUseCase`, Resource Query, Adaptive Wizard와 `spec://` Resource는 보존했다.
- 검증: `.venv-exec\\Scripts\\ruff.exe check src tests`, `.venv-exec\\Scripts\\black.exe --check src tests`, `.venv-exec\\Scripts\\mypy.exe src`, 대상 pytest 21 passed, 전체 pytest 63 passed, `git diff --check`를 통과했다. pytest·Black cache 접근 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-13 20:15:57 +09:00 — 남은 미등록 어댑터 읽기 전용 inventory

- 시작 시각: 2026-09-13 20:15:57 +09:00
- 목표: canonical 12개 공개 Tool과 현재 Resource·Adaptive Wizard 경로를 기준으로 남은 미등록 presentation adapter 및 지원 도메인 코드의 활성·고립 여부를 분류한다.
- 범위 제외: adapter·UseCase·모델의 삭제·이동·수정, 서버 모델 API worker, timeout 자동 재개, 기존 사용자 `.mvpmcp` 변경, 플러그인 재설치, 프로토타입 시각 디자인 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 공개 등록과 presentation adapter inventory | 🟢 완료 | canonical 12개 외 미등록 adapter 3개를 확인 |
| 2. 도메인·Resource·테스트·문서 참조 분류 | 🟢 완료 | `ScopeMvpUseCase`·Resource Query는 활성, 구형 채팅형 adapter·질문 체인은 고립 |
| 3. 삭제 없는 후속 의사결정 보고 | 🟢 완료 | 물리 정리 없이 후속 감사 단위를 확정 |

- inventory 결과: `clarify_intent`·`get_missing_info` adapter와 `GetIntakeQuestionsUseCase`·`GetMissingInfoUseCase`·`INTAKE_QUESTIONS`·`QUESTION_BANK`·문답 formatter는 현재 조립·공개 문서·통합 지침에서 참조되지 않는 고립 체인이다. 관련 회귀는 `test_spec.py`의 intake 질문 1건과 `test_question_formatting.py`의 문답 formatter 2건이다.
- 보존 근거: `scope_mvp` adapter는 미등록이지만, `ScopeMvpUseCase`는 `CreateAdaptiveWizardDraftUseCase`와 `main.py::build()`가 사용한다. `GetDraftUseCase`·`GetTemplateUseCase`·`ListProjectTypesUseCase`와 `spec://` Resource도 공개 경로이므로 유지한다.
- 후속 결정: 다음 후보는 세 미등록 adapter와 전용 질문·formatter 체인만을 대상으로 한 별도 최소 제거 감사다. `ScopeMvpUseCase`, Resource Query, 템플릿 데이터의 활성 부분은 제외하며, 역사적 `PLAN.md`는 보존한다.

---

## 2026-09-13 20:02:51 +09:00 — 미등록 start_spec 레거시 물리 정리

- 시작 시각: 2026-09-13 20:02:51 +09:00
- 목표: 공개 등록이 없는 `start_spec` 어댑터와 전용 `StartSpecUseCase`·지원 코드를 제거하고, canonical 12개 Tool·Adaptive Wizard 재개·`spec://drafts/{spec_id}` Resource 계약을 보존한다.
- 범위 제외: 서버 모델 API worker, timeout 자동 재개, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경, 플러그인 재설치, 프로토타입 시각 디자인 변경, 다른 미등록 레거시 어댑터의 물리 정리.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 전용 adapter·UseCase·지원 코드 정리 | 🟢 완료 | adapter·전용 UseCase·입력 모델·포맷터를 제거하고 shared Scope/SpecDraft 경로를 보존 |
| 2. 가드레일·현재 상태 문서 정합화 | 🟢 완료 | adapter·지원 UseCase 부재 가드와 HANDOFF·현재 계획 상태를 갱신, 역사 문서는 보존 |
| 3. 대상·전체 품질 게이트 | 🟢 완료 | 대상 26 passed, 전체 65 passed; Ruff·Black·mypy·diff check 통과 |

- 구현 완료: 미등록 `start_spec` adapter, `StartSpecUseCase`, 전용 `SpecRequest`·질문 helper·formatter를 제거했다. 현재 안내 문자열은 canonical Adaptive Wizard를 가리키며, 활성 `ScopeMvpUseCase`·`SpecDraft`·`SpecRepository`·`spec://drafts/{spec_id}` Resource는 유지했다.
- 검증: `.venv-exec\\Scripts\\ruff.exe check src tests`, `.venv-exec\\Scripts\\black.exe --check src tests`, `.venv-exec\\Scripts\\mypy.exe src`, 대상 pytest 26 passed, 전체 pytest 65 passed, `git diff --check`를 통과했다. pytest·Black cache 접근 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-13 19:39:18 +09:00 — Linux CI Windows 절대경로 판정 복구

- 시작 시각: 2026-09-13 19:39:18 +09:00
- 목표: Linux GitHub Actions에서도 Windows 드라이브 절대경로를 유효한 MCP `project_root`로 인식해 adaptive Wizard 회귀를 복구한다.
- 범위 제외: candidate lifecycle·공개 Tool·Web Wizard·경로 실제 접근 정책·사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 실패 원인·영향 경로 확인 | 🟢 완료 | `Path.is_absolute()`가 Linux에서 `C:/...`를 거절해 7개 CI 실패를 유발 |
| 2. OS 독립 절대경로 판정과 회귀 보완 | 🟢 완료 | `PurePosixPath`·`PureWindowsPath`로 양쪽 문법을 명시적으로 판정 |
| 3. CI 동등 pytest·품질 재검증 | 🟢 완료 | Ruff·Black·mypy·전체 pytest 65 passed |

- 구현 완료: Linux CI에서 Windows 드라이브 경로를 거절하던 OS 종속 `Path.is_absolute()`를 제거했다. POSIX 절대경로, Windows `/`·`\\` 구분자, 드라이브 상대경로·일반 상대경로를 같은 회귀 테스트로 고정했다.
- 검증: `.venv-exec\\Scripts\\ruff.exe check` 통과, Black 80 files unchanged(사용자 cache 권한 경고만 있음), mypy 67 source files 통과, pytest 65 passed. pytest 임시 경로는 workspace 권한 충돌을 피해 `C:\\Users\\Public\\Documents\\ESTsoft\\CreatorTemp`을 사용했다.

---

## 2026-09-13 19:33:47 +09:00 — URL elicitation spike Ruff import 정렬 복구

- 시작 시각: 2026-09-13 19:33:47 +09:00
- 목표: GitHub Actions의 `uv run ruff check`가 보고한 `scripts/run_codex_url_elicitation_spike.py` import 정렬 위반을 최소 수정하고, CI와 같은 Ruff 명령으로 검증한다.
- 범위 제외: URL elicitation spike 기능 변경·삭제, 서버 Web Wizard 복구, MCP Tool 등록 변경, lifecycle·`.mvpmcp` 계약 변경, 플러그인 재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. Ruff가 기대하는 import 정렬 확인 | 🟢 완료 | CI I001과 동등한 보수적 isort diff를 재현 |
| 2. 최소 import 정렬 수정 | 🟢 완료 | 대상 스크립트 한 파일의 import group·줄바꿈만 정렬 |
| 3. CI 동등 Ruff 재검증 | 🟢 완료 | 전체 Ruff 및 보수적 import 검사 모두 통과 |

- 구현 완료: third-party와 `mvp_mcp` import group을 CI가 요구한 순서로 정렬하고 긴 import를 명시적으로 줄바꿈했다. 제품 동작·공개 Tool·URL elicitation spike의 실행 로직은 변경하지 않았다.
- 검증: `.venv-exec\\Scripts\\ruff.exe check`와 `.venv-exec\\Scripts\\ruff.exe check --isolated --select I --line-length 88 scripts/run_codex_url_elicitation_spike.py` 모두 `All checks passed!`; 대상 파일 `git diff --check` 공백 오류 없음 (CRLF 경고만 출력).

---

## 2026-09-13 13:34:57 +09:00 — Run-scoped candidate lifecycle breaking cutover

- 시작 시각: 2026-09-13 13:34:57 +09:00
- 목표: Run-scoped candidate lifecycle 공개 API 12개만 남기고, 구형 spec_id·직접 문서 Tool 10개를 안전하게 제거한다.
- 확정 범위: 신규 Candidate API MCP E2E, 구형 Tool 등록·어댑터·전용 UseCase 제거, 공개 계약 문서·가드레일 정합화, 전체 회귀 검증.
- 범위 제외: Adaptive Wizard 재개 인프라·기존 `.mvpmcp/` 파일 변경, worker·timeout 자동 재개, 플러그인 재설치, 대규모 파일 이동·루트 정리.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 신규 Candidate API MCP E2E 기준선 | 🟢 완료 | Composition Root에서 lifecycle 5개 기록→candidate sync→validate/preview와 generate_only 무반영을 검증 (16 passed) |
| 2. 구형 Tool 조립·어댑터·전용 UseCase 제거 | 🟢 완료 | `main.py` 등록·어댑터 10개·전용 UseCase를 제거하고 Adaptive Wizard 공유 ScopeMvp/SpecDraft 인프라는 보존 |
| 3. 공개 계약 문서·프롬프트·가드레일 갱신 | 🟢 완료 | canonical 12개·구형 10개 제거 완료·Run lifecycle 순서를 README/HANDOFF/통합 지침/감사/가드레일에 반영 |
| 4. 전체 회귀·품질 게이트 | 🟢 완료 | Ruff·Black·mypy 통과(67 source files), 전체 pytest 65 passed, Tool 부재·공백 검사 확인 |

- 구현 완료 시각: 2026-09-13 13:52:34 +09:00
- 구현 결과: `main.py::build()`는 Run-scoped canonical Tool 12개만 조립한다. 구형 Tool 10개 adapter와
  전용 spec_id UseCase·문서 Tool UseCase를 제거하고, 신규 Composition Root MCP E2E가 lifecycle 5개 기록,
  candidate sync, validate/preview 및 `generate_only` 무반영을 고정했다. Adaptive 재개가 공유하는
  `ScopeMvpUseCase`·`SpecDraft`·Repository와 미등록 `start_spec.py` 의존성은 물리 정리 범위에서 제외했다.
- 검증: targeted 57 passed, 최종 Ruff·Black·mypy 통과, `pytest -q --basetemp
  .pytest-tmp\\legacy-tool-removal-final-20260913 tests` 전체 65 passed, `git diff --check` 공백 오류 없음
  (line-ending 경고만 출력).
- 사용자 재확인: 2026-09-13에 `.venv-exec`으로 Ruff·Black·mypy·전체 pytest를 다시 실행했다.
  Ruff 통과, Black `80 files would be left unchanged`, mypy `67 source files` 문제 없음, pytest `65 passed`
  결과를 사용자가 직접 제공했다 (`확인됨`).

---

## 2026-09-13 12:41:55 +09:00 — Run-scoped candidate 수명주기 API

- 시작 시각: 2026-09-13 12:41:55 +09:00
- 목표: 메모리 `spec_id`에 묶인 요구사항·설계·배포·검증·릴리스 기록을 SQLite `run_id` 소유의 후보 수명주기로 추가하고, 기존 candidate validate/preview/apply 흐름과 안전하게 연결한다.
- 확정 범위: Run 영속 lifecycle 모델·revision/동시성 규칙, 후보 Tool 5개, candidate 재검증 전이, 문서·가드레일·회귀 검증.
- 범위 제외: 기존 `spec_id` Tool 5개 삭제·동작 변경, `.mvpmcp/` 형식·기존 사용자 파일 변경, 서버 모델 API worker, timeout 자동 재개, Web Wizard 복구, 대규모 파일 이동, 플러그인 재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. Run·candidate 수명주기 모델과 영속 계약 | 🟢 완료 | SQLite JSON Run의 하위 호환 기본값, lifecycle revision·candidate sync·이전 apply 이력 구현 |
| 2. 요구사항·설계·배포 후보 Tool과 invalidation | 🟢 완료 | `run_id`·optimistic version 기반 구조화 계약 갱신과 하위 계약 invalidation 구현 |
| 3. 테스트·릴리스 후보 기록 Tool과 게이트 | 🟢 완료 | append-only·idempotency key·PASS 릴리스 게이트를 Run 소유 상태로 이관 |
| 4. 조립·공개 안내·가드레일 | 🟢 완료 | `main.py::build()` 조립, canonical 12개 inventory, README·HANDOFF·세 클라이언트 가이드 반영 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | lifecycle·재시작·stale·candidate sync와 표준 전체 검사 통과 |

- 구현 완료 시각: 2026-09-13 13:03:44 +09:00
- 구현 결과: Run에 구조화 `candidate_lifecycle`과 revision·candidate sync 기준 hash·이전 apply cycle 이력을
  저장한다. 다섯 새 Tool은 최신 `expected_run_version`으로 요구사항→설계→전달→TEST/RELEASE를 갱신한다.
  구조화 변경은 `.mvpmcp/`에 쓰지 않고 candidate validate/preview binding만 무효화하며, 모델이 후보 Markdown을
  갱신한 뒤 새 revision으로 검증하도록 강제한다. 기존 spec_id Tool 5개는 직접 대체가 생겨 호환·deprecated로
  전환했고, 이전 직접 중복 Tool 5개와 함께 다음 breaking release까지 유지한다.
- 검증: targeted lifecycle/candidate/adaptive/guardrail `34 passed`, 최종 Ruff·Black·mypy 통과,
  `pytest -q --basetemp .pytest-tmp\\candidate-lifecycle-full-20260913 tests` 전체 `73 passed`.

---

## 2026-09-13 11:38:29 +09:00 — spec_id 직접 중복 Tool 유예 릴리스 전환

- 시작 시각: 2026-09-13 11:38:29 +09:00
- 목표: 직접 대체가 있는 `documentation_start`·`answer_question`·기존 validate/preview/apply을 한 릴리스 동안 유지하되, deprecated 전환 경로와 다음 breaking release 제거 조건을 공개 계약·문서·가드레일에 통일한다.
- 확정 범위: Tool 설명, 공개 inventory 가드레일, README·HANDOFF·통합 Skill·전환 감사, 회귀 검증.
- 범위 제외: 이번 릴리스의 Tool 등록 해제·adapter/UseCase 삭제, 등록·기록 Tool 5개 변경, `.mvpmcp/` 변경, 대규모 파일 이동, 플러그인 재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 직접 대체·유지 대상 계약 확정 | 🟢 완료 | 직접 중복 5개와 직접 대체 없는 spec_id Tool 5개를 분리 |
| 2. Tool 전환 안내·문서 갱신 | 🟢 완료 | Tool 설명·README·HANDOFF·Codex/Claude/Gemini Skill·전환 감사를 유예 정책으로 통일 |
| 3. 가드레일·회귀 검증 | 🟢 완료 | Tool inventory·전환 문서 계약·전체 품질 게이트 통과 |

- 구현 완료 시각: 2026-09-13 11:44:53 +09:00
- 구현 결과: 직접 대체가 있는 `documentation_start`·`answer_question`·기존 validate/preview/apply 5개는
  현재 공개·호출을 유지하되, Tool 설명과 모든 public 안내에 `deprecated`·대체 경로·다음 breaking release
  제거 조건을 명시했다. 요구사항·설계·전달·실행/릴리스 기록 Tool 5개는 직접 대체가 없어 유지 대상으로
  분리했다.
- 검증: targeted guardrail/workflow 11 passed, 최종 `ruff check src tests`, `black --check src tests`,
  `mypy --no-incremental src`, `pytest -q --basetemp .pytest-tmp\\compat-deprecation-final2-20260913 tests`
  모두 통과(68 passed). 전환 문구 정적 탐색은 README·HANDOFF·전환 감사·세 통합 Skill에서 모두 확인했고,
  `git diff --check`는 공백 오류 없이 line-ending 경고만 출력했다.

---

## 2026-09-13 00:45:12 +09:00 — Client-native 질문 UI 전환 및 Web Wizard 폐기

- 시작 시각: 2026-09-13 00:45:12 +09:00
- 목표: 설문을 위해 localhost 브라우저 창을 여는 모든 Web Wizard를 제거하고, Codex·Claude Code·Gemini CLI의 native 구조화 질문 UI가 정규화 답변을 MCP Run 흐름에 전달하도록 전환한다.
- 확정 범위: `LocalAdaptiveWizardForm`·`LocalWebSurveyForm`·`LocalWebQuestionForm`과 loopback HTTP/URL/CSRF/동기 대기 경로 폐기, 비대기형 adaptive Run 질문·제출 계약, 클라이언트별 통합 지침, 회귀 테스트·문서 갱신.
- 범위 제외: 서버 모델 API worker, 기존 사용자 `.mvpmcp` 변경, 후보 본문 자동 작성, 플러그인 재설치, 대규모 파일 이동.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. native 질문 계약·영향 경로 확정 | 🟢 완료 | Web Form 3종·URL elicitation/continuation probe·호환 Tool·조립 참조를 확인하고, 질문 schema 반환 → native UI → 답변 제출 계약으로 확정 |
| 2. 비대기형 adaptive Run 시작·제출 흐름 | 🟢 완료 | 질문 schema 즉시 반환, 답변 원자 저장, 같은 답변의 멱등 제출과 design 제출 뒤 DRAFT_READY를 구현 |
| 3. Web Wizard·호환 설문 경로 제거 및 조립 정리 | 🟢 완료 | localhost HTTP·브라우저 열기·CSRF·대기 Port·URL elicitation/continuation probe·구형 설문 Tool을 제거 |
| 4. Codex·Claude Code·Gemini CLI 통합 지침·문서 | 🟢 완료 | `request_user_input`·`AskUserQuestion`·`ask_user`가 같은 schema/answers 계약을 쓰도록 README·Skill·인수인계를 갱신 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | legacy 경로 정적 탐색 0건, MCP/Run·계층 가드레일, Ruff·Black·mypy·전체 pytest 통과 |

- 구현 완료 시각: 2026-09-13 11:11:05 +09:00
- 구현 결과: `documentation_start_adaptive_wizard`는 질문 schema를 즉시 반환하고,
  `documentation_submit_adaptive_wizard_answers`가 답변을 원자 저장한다. design 제출은 `DRAFT_READY`와
  `candidate_root`를 즉시 반환한다. localhost Web Form·URL elicitation/continuation probe·대기 Port와
  구형 설문 Tool은 제거했고, `main.py::build()`는 새 제출 UseCase와 Tool만 조립한다.
- 클라이언트 계약: Codex `request_user_input`, Claude Code `AskUserQuestion`, Gemini CLI `ask_user`가
  질문 schema의 `id`·조건·선택지를 보존해 답을 수집하고, 사용자의 별도 채팅 제출 메시지 없이 같은
  Run의 `answers`로 제출한다.
- 검증: targeted adaptive/guardrail/scaffolding 19 passed, Skill/Prompt 6 passed, 최종
  `ruff check src tests`, `black --check src tests`, `mypy --no-incremental src`,
  `pytest -q --basetemp .pytest-tmp\\native-question-final2-20260913 tests` 모두 통과(67 passed).
  legacy Web/elicitation 식별자 정적 탐색은 production·통합·현재 문서에서 0건이며, `git diff --check`는
  공백 오류 없이 line-ending 경고만 출력했다.

---

## 2026-09-12 23:13:47 +09:00 — 단계 11 문서 서술·프로토타입 품질 감사

- 시작 시각: 2026-09-12 23:13:47 +09:00
- 목표: 대표 품질 fixture와 실제 생성 프로토타입을 근거로 문서 서술·프로토타입의 수용 기준을 구체화하고, 필요한 최소 품질 보완만 구현·검증한다.
- 확정 범위: 현재 fixture·Skill·renderer·대표 출력의 읽기 전용 대조, 실제 브라우저 화면 캡처, 접근성·상태·콘텐츠 품질 수용 기준, 감사 결과에 근거한 최소 변경과 회귀 검증.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 등록 변경·삭제, 대규모 파일 이동, runtime output·cache 삭제, 기존 사용자 `.mvpmcp` 변경, 플러그인 동기화·재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. fixture·Skill·renderer 품질 기준선 | 🟢 완료 | 7개 루브릭·5개 대표 사례와 현재 self-review·renderer 계약을 읽기 전용으로 확인 |
| 2. 실제 prototype 화면 감사 | 🟠 별도 요청 대기 | 초기 화면 감사만 완료했다. 사용자가 시각적 완성도 조정은 별도 요청으로 분리함 |
| 3. 화면 목적별 Mock 상태·다중 화면 회귀 | 🟢 완료 | 범용 텍스트 `Mock 입력`을 각 `ScreenSpec.states` 선택으로 교체하고, 두 화면의 선택·상태 결과를 회귀로 고정 |
| 4. 구현·품질 게이트·검토용 HTML 재생성 | 🟢 완료 | Ruff·Black·mypy·import-linter·전체 pytest를 통과하고 별도 workspace preview를 생성; 기존 `.mvpmcp/`는 변경하지 않음 |

- 구현 완료 시각: 2026-09-12 23:23:47 +09:00
- 구현 결과: prototype이 화면 외에 DesignContract의 정상 흐름·예외 복구를 표시하고, 탭 키보드 전환 및 Mock 성공/오류 `aria` 상태를 구분한다. prototype 품질 fixture와 Codex Skill의 자체 점검도 같은 계약으로 고정했다.
- 검증: targeted pytest 3 passed, Ruff·Black·mypy·import-linter 통과, 전체 pytest 96 passed·2 xfailed. Black·pytest cache 권한 경고는 결과에 영향을 주지 않았다.
- 남은 수동 확인: 브라우저 보안 정책이 허용하는 방식으로 현재 생성 HTML의 실제 화면 캡처·가독성 검토가 필요하다. 이 작업에서는 정책 우회, 별도 브라우저·서버 사용, 기존 `.mvpmcp/` 재생성을 하지 않았다.
- 재확인 시각: 2026-09-12 23:40:25 +09:00 — 저장소의 `output/`·`outputs/`·`tests/`에 재사용 가능한 화면 이미지가 없고, 기존 in-app browser의 workspace `file:` 차단은 사용자 입력만으로 해제되지 않는다. 따라서 화면 감사는 계속 보류한다.
- preview 생성: 2026-09-12 23:44:05 +09:00 — 현재 `HtmlPrototypeRenderer`로 `output/stage11-prototype-review-20260912-234302/index.html`을 새로 생성했다. SHA-256은 `020904a691c2599f9211eef5fed80f76fd71632cb63ea4dafb0e4c3d9ba615be`이며, 사용자 흐름·오류 복구·탭 역할·offline CSP를 정적으로 확인했다. 기존 `.mvpmcp/`는 만들거나 변경하지 않았다.
- 화면 감사: 2026-09-12 23:47:26 +09:00 — 사용자 제공 초기 화면을 `output/stage11-prototype-review-20260912-234302/audit/01-start.jpeg`에 보존하고 직접 검토했다. 결과·한계·추가 캡처는 같은 폴더의 `01-start-notes.md`에 기록했다. 화면은 정상 로드됐지만 시작 화면만으로 오류·성공·모바일·키보드 상호작용은 판정할 수 없다.
- 콘텐츠·레이아웃 구현 완료: 2026-09-12 23:59:05 +09:00 — 각 화면의 `ScreenSpec.states`만 고르는 Mock 상태 시뮬레이터와 화면별 결과 문구를 구현했다. `prototype_acceptance` fixture·Codex Skill·README·Playwright 회귀를 같은 계약으로 갱신했으며, targeted pytest 3 passed 및 전체 pytest 96 passed·2 xfailed를 확인했다. 새 검토용 출력은 `output/stage11-prototype-state-review-20260912-235833/index.html`(SHA-256 `bdb280f1f49f5448e5b21535874cf5622e9b06cd967bd5fc7f0947229b56ba2e`)이다. 시각적 완성도 조정은 사용자 요청에 따라 별도 작업으로 보류한다.
- 최종 확인: 2026-09-13 00:00:26 +09:00 — Ruff·Black·Git diff 검사를 다시 통과했다. Black cache 읽기 권한 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 22:57:13 +09:00 — Clean Architecture·SOLID 최소 정리와 루트 산출물 inventory

- 시작 시각: 2026-09-12 22:57:13 +09:00
- 목표: 공개 MCP 계약과 사용자 `.mvpmcp/`를 바꾸지 않고, 계층 가드레일을 강화하고 adaptive Wizard adapter 결합을 줄이며 루트 산출물의 보존·운영 역할을 기록한다.
- 확정 범위: AST 기반 domain import 가드레일, adaptive Wizard snapshot helper 분리, candidate root의 opaque Port 값 비교, 루트 산출물 inventory·현재 상태 문서화, 회귀 검증.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 등록 변경·삭제, 대규모 파일 이동, runtime output·cache 삭제, 기존 사용자 `.mvpmcp` 변경, 플러그인 동기화·재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 계층·조립·루트 산출물 읽기 전용 기준선 | 🟢 완료 | import-linter 계약, `main.py::build()` 조립, Git 추적·참조·runtime output 보존 범위를 확인 |
| 2. Domain 가드레일·opaque candidate root 정리 | 🟢 완료 | AST 기반 import 검사와 opaque root 계약을 추가하고, 남은 `project_root` 절대경로 검증은 `core/security.py`로 이관 (`targeted pytest` 39 passed) |
| 3. Adaptive Wizard presentation helper 분리 | 🟢 완료 | peer Tool의 private helper import를 공용 private formatter로 교체 |
| 4. 루트 산출물 inventory·현재 상태 문서화 | 🟢 완료 | `progress/ROOT_ARTIFACT_AUDIT.md`에 역할·Git 추적·runtime 보존 정책을 기록하고 HANDOFF에 연결 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | Ruff·Black·mypy·import-linter 통과, targeted pytest 39 passed, 전체 pytest 96 passed·2 xfailed |

- 완료 시각: 2026-09-12 23:04:38 +09:00
- 검증 참고: `uv`가 PATH에 없어 기존 `.venv-exec`의 동등한 실행 파일을 사용했다. Black·pytest cache 읽기/쓰기 권한 경고는 검사 결과에 영향을 주지 않았다.

---

## 2026-09-12 19:16:24 +09:00 — generate_only write policy 불변성 보장

- 시작 시각: 2026-09-12 19:16:24 +09:00
- 목표: 최초 요청에서 확정한 `generate_only` write policy가 Wizard의 `document_output_mode` 선택으로 `safe_auto_apply`로 승격되지 않도록 막고, 정책 충돌 회귀를 고정한다.
- 확정 범위: Adaptive Wizard 정책 결정·검증, 충돌/정상 경로 회귀 테스트, 진행 기록, 전체 품질 게이트.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 삭제·등록 변경, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. write policy 결정 경로·영향 분석 | 🟢 완료 | 자연어만으로는 정책이 결속되지 않고, 2차 `document_output_mode`가 허용됨을 실제 기록·UseCase에서 확인 |
| 2. 정책 승격 차단 구현 | 🟢 완료 | canonical 시작 입력의 write_policy를 Run에 고정하고, 해당 1차 문항 제거·2차 document_output_mode 거부를 적용 |
| 3. 정책 충돌·정상 경로 회귀 | 🟢 완료 | 명시 generate_only 결속·동일 request_key 정책 변경 거부·2차 정책 질문 거부, 기존 1차 정책 경로 통과 (targeted pytest 13 passed) |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 94 passed·2 xfailed (`--basetemp .pytest-tmp-policy-full`) |

- 완료 시각: 2026-09-12 19:23:55 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로와 Black 사용자 cache의 권한 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 18:31:09 +09:00 — MCP 공개 Tool 전환 감사·호환 경로 명시

- 시작 시각: 2026-09-12 18:31:09 +09:00
- 목표: canonical 6개 Tool과 보존할 호환 Tool을 분류·문서화하고, 등록·설명 계약을 회귀 테스트로 고정한다.
- 확정 범위: Tool inventory 감사 문서, 호환 Tool 설명·README 안내, canonical/compatibility 등록 가드레일, 진행 기록.
- 범위 제외: Tool 등록 해제·파일/UseCase 삭제, 공개 입력·출력/상태/write policy 변경, 대규모 파일 이동, 기존 `.mvpmcp` 변경, worker·timeout 자동 재개.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 공개 Tool inventory·처분 상태 | 🟢 완료 | canonical 6개, 호환 10개, 보조 질문 2개를 대체 경로와 함께 고정 |
| 2. 호환 경로 설명·문서 | 🟢 완료 | 기존 Tool을 삭제하지 않고 호환 전용임을 설명과 README에 명시 |
| 3. 등록·설명 회귀 가드레일 | 🟢 완료 | canonical/compatibility 구분, 전체 등록 목록, 대체·보류 안내를 검증 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 92 passed·2 xfailed (`--basetemp .pytest-tmp-tool-transition-full`) |

- 완료 시각: 2026-09-12 18:35:32 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 18:11:25 +09:00 — 산출물 품질 루브릭·대표 평가 fixture

- 시작 시각: 2026-09-12 18:11:25 +09:00
- 목표: 후보 문서의 의미 품질을 위한 Skill 자체 점검 기준과 재현 가능한 대표 평가 fixture를 추가한다.
- 확정 범위: 7개 품질 범주, 5개 대표 사례, Skill 자체 점검, fixture 스키마·필수 조건 회귀 테스트, 로드맵·진행 기록 정합화.
- 범위 제외: 공개 MCP Tool·candidate 결정적 구조 검증·Run 상태·write policy 변경, 저장소 대규모 탐색, 기존 `.mvpmcp` 변경, 구형 Tool 삭제, worker·timeout 자동 재개.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 루브릭·대표 fixture 계약 | 🟢 완료 | 7개 품질 범주와 신규 웹·기존 API·리팩터링·결함 수정·ML 5개 입력·기대 근거 사례를 고정 |
| 2. Codex Skill 자체 점검 | 🟢 완료 | 후보 작성 뒤 구조 검증 전 루브릭 보완과 보수적 근거 상태 기록 절차를 추가 |
| 3. 회귀 테스트·로드맵 정합화 | 🟢 완료 | fixture 스키마·Skill 계약 회귀와 6·7·8단계 상태를 갱신 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 91 passed·2 xfailed (`--basetemp .pytest-tmp-artifact-quality-full`) |

- 완료 시각: 2026-09-12 18:15:46 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 17:52:01 +09:00 — Architecture 기술 스택·디렉터리 구조 계약 강화

- 시작 시각: 2026-09-12 17:52:01 +09:00
- 목표: 후보 package와 기존 renderer의 `ARCHITECTURE.md`에 근거 상태 기술 스택 표·라벨된 디렉터리 구조를 필수 계약으로 만들고 구조 위반을 검증에서 차단한다.
- 확정 범위: 후보와 renderer 모두 적용, 구조 엄격 차단, IMPLEMENTATION_PLAN의 Architecture SSOT 참조 존재만 차단, 새 저장소 탐색 없이 안전한 계획 경로만 renderer가 생성한다.
- 범위 제외: 실제 저장소 경로 대조, TASK별 경로 완전 일치, 서버 모델 API worker, timeout 자동 재개, 구형 Tool 삭제, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 문서 계약·candidate 구조 검증 | 🟢 완료 | Architecture 필수 섹션과 표·트리·SSOT 참조 검증을 추가하고 잘못된 헤더·상태·라벨·펜스·참조 누락을 차단 |
| 2. 기존 renderer 출력 계약 | 🟢 완료 | 근거 상태 표와 안전한 NEW/OPTIONAL 트리, 구현 계획 참조를 생성 |
| 3. Skill/Prompt·회귀 fixture | 🟢 완료 | candidate 저작 지침과 strict validation 사례, escaped pipe·권장 기본값·PROTOTYPE_4 renderer 회귀를 갱신 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 89 passed·2 xfailed (`--basetemp .pytest-tmp-architecture-contract-full`) |

- 완료 시각: 2026-09-12 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 17:31:48 +09:00 — Adaptive Wizard 질문 계약·유형 분류 재개편

- 시작 시각: 2026-09-12 17:31:48 +09:00
- 목표: 2차 Wizard의 문자열 JSON 입력을 구조화하고, Android 앱을 `blog`로 오분류하지 않도록 1·2차 문항과 유형 분류를 개선한다.
- 범위 제외: 서버 모델 API worker, Codex timeout 뒤 자동 재개, 구형 Tool 삭제, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 구조화된 2차 질문 Tool 계약·정규화 | 🟢 완료 | typed `design_questions`를 정식 입력으로 추가하고 title/type·single_select 계열을 canonical schema로 정규화; 문자열 입력은 호환 경로로 유지 |
| 2. 1차 분류 축·모바일 템플릿·유형별 문항 | 🟢 완료 | 작업 유형과 솔루션·표면·도메인 분류를 분리하고 Android/iOS/크로스플랫폼을 `MOBILE_APP`으로 우선 매핑 |
| 3. 2차 문항 지침·Skill/Prompt 갱신 | 🟢 완료 | 정식 구조화 스키마와 금지된 별칭을 서버 Prompt·Codex Skill에 반영 |
| 4. 회귀 테스트·전체 품질 게이트 | 🟢 완료 | 구조화·문자열 호환 Tool 호출, Android/mobile·웹 콘텐츠 분류 회귀와 전체 검사 통과: ruff·black·mypy, pytest 81 passed·2 xfailed |

- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건은 결과에 영향을 주지 않았다.

---

## 2026-09-12 — Codex Desktop 실제 2단계 Wizard·자동 반영 수용 테스트

- 목표: 구현 전제였던 "설문 제출 뒤 같은 task 자동 진행"과 `safe_auto_apply`의 Codex Desktop 실제
  동작을 확인한다.

| 확인 항목 | 상태 | 실제 결과 |
|---|---|---|
| 1차 blocking Wizard 대기 | 🔴 실패 | `documentation_start_adaptive_wizard` Tool 호출이 약 300초 뒤 timeout. 서버 대기만으로는 연장되지 않음. |
| timeout 뒤 Run 복구 | 🟢 완료 | 동일 `request_key` 재호출로 영속 `INTAKE_SUBMITTED` 답변을 회수. |
| 제출 뒤 채팅 없는 자동 재개 | 🔴 실패 | timeout 뒤에는 사용자의 `제출함` 메시지가 다음 Tool 호출의 계기가 됨. |
| 2차 질문 제출과 후보 작성 | 🟢 완료 | 2차 질문 정의가 두 번 형식 오류를 냈으나 세 번째 호출에서 `DRAFT_READY`와 candidate root를 발급하고 후보를 작성·검증. |
| 명시적 사전 승인 기반 safe auto apply | 🟢 완료 | 최초 자연어 요청에 `.mvpmcp/` 자동 반영 허용을 명시하면 9개 관리 문서를 충돌 없이 갱신. |

- 결정: 300초 timeout 이후 자동 재개는 **최후순위**로 연기한다. 다음 구현은 2차 질문의 문자열 JSON
  계약과 Wizard 유형·문항 품질을 먼저 개선한다.
- 주의: 이번 `candidate_valid: true`는 구조·추적성 검증 통과를 뜻하며, 문서 서술의 실무 품질은 아직
  별도 루브릭·대표 fixture로 평가하지 않았다.

---

## 2026-09-11 20:16:26 +09:00 — 동기 대기형 2단계 적응형 Wizard 기반

- 시작 시각: 2026-09-11 20:16:26 +09:00
- 목표: Codex URL elicitation 대신 검증된 loopback blocking Wizard를 사용해, 같은 MCP 작업 안에서 1차·2차 설문을 채팅 재입력 없이 진행할 수 있는 영속 Run 기반을 구현한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 2-0. 계획·기존 경로 재정렬 | 🟢 | 실제 Codex URL 재개 실패와 `LocalWebSurveyForm.ask()`의 동기 대기 계약을 확인해, blocking loopback form을 기본 전송 방식으로 확정 |
| 2-1. 영속 Adaptive Run 도메인·SQLite 저장소 | 🟢 | request_key, optimistic version, 단계별 제출 snapshot, DRAFT_READY 및 재시작 조회 모델을 구현 |
| 2-2. 1·2차 blocking Web Wizard·MCP Tool | 🟢 | loopback HTTP form, CSRF 제출 토큰, 1차→2차 대기, `DRAFT_READY + spec_id` 호환 연결과 MCP memory E2E를 구현 |
| 2-3. Skill·서버 지시문·호환 경로 | 🟢 | 서버 Prompt·Codex Skill·README를 adaptive 기본 경로로 전환하고 기존 Tool을 호환 경로로 명시 |
| 2-4. 회귀·E2E·품질 게이트 | 🟢 | ruff·black·mypy 통과, 전체 pytest `68 passed, 2 xfailed`, 기존 MCP 평가 `10/10` 통과 |

- 완료 시각: 2026-09-12 +09:00
- 구현 경계: URL elicitation·서버 측 모델 worker는 기본 경로에서 제외했다. 이번 단계는 2차 제출 뒤
  `DRAFT_READY + spec_id`와 기존 validate/preview 체인 연결까지이며, run 전용 candidate package와
  `safe_auto_apply`는 다음 단계다.

### 다음 승인 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 3-0. 후보 package·기존 exporter 재사용 설계 | 🟢 | `<output>/runs/<run_id>/candidate`와 `<output>/previews/<run_id>/<preview_id>`를 기존 exporter의 hash·충돌·원자 반영 계약에 결합 |
| 3-1. candidate 저장소·validate/preview/apply UseCase | 🟢 | 후보 파일은 Skill이 작성하고 MCP Core는 경로·UTF-8·symlink 정책, revision/version 검증, preview, `write_policy` 상태 전이를 담당 |
| 3-2. 후보 package Tool·Skill handoff·자동 안전 반영 | 🟢 | `DRAFT_READY`가 candidate root를 발급하고, status → validate → preview chain 및 `safe_auto_apply` 내부 Apply를 같은 모델 턴의 지시문에 연결 |
| 3-3. candidate E2E·회귀·품질 게이트 | 🟢 | unmanaged 충돌 보존·SQLite 재시작·stale revision·정책 거부·manual/auto apply·MCP memory E2E와 전체 품질 게이트 통과 |

- 후보 package 품질 게이트: `ruff`, `black --check`, `mypy` 통과; 전체 pytest
  `76 passed, 2 xfailed`; 기존 MCP evaluation `10/10 passed`.
- 구현 경계: candidate 본문은 서버가 모델 API로 작성하지 않는다. Codex Skill이 server-issued root 안에
  작성하고, server 재시작 뒤 process-local preview apply payload가 없으면 같은 revision으로 새 preview를
  만들어 수동 반영 binding을 복구한다. 미니 Wizard·browser 완료 화면·구형 Tool 6개 전환은 후속 단계다.

---

## 2026-09-11 18:49:27 Asia/Seoul — 2단계 적응형 Wizard 리팩터링 단계 0·1

- 시작 시각: 2026-09-11 18:49:27 Asia/Seoul
- 목표: 승인된 최종 계획의 회귀 fixture 기준선과 Codex URL elicitation 자동 재개 capability spike를 최소 변경으로 구현·검증한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 0-1. 현행 Tool·Wizard·테스트 계약 조사 | 🟢 | 기본 Tool은 blocking `SubmitWebSurveyUseCase`만 조립하며, 비차단 Begin/Submit/Resume UseCase는 미등록임을 확인 |
| 0-2. 실패 fixture·회귀 기준선 고정 | 🟢 | 중복 설문·제출 뒤 단절·URL completion 사례를 strict xfail 2건과 평가 fixture로 고정 |
| 1-1. 자동 재개 capability spike 설계·구현 | 🟢 | SQLite Probe·loopback URL form·completion notification·수동 retry MCP E2E 구현 및 통과 |
| 1-2. Codex client 연계 검증·결정 기록 | 🟢 | 실제 Codex Desktop 수용 테스트 완료. URL elicitation은 Tool 오류·링크로 표시되고, 사용자가 form을 제출해도 원래 Tool 자동 retry가 일어나지 않았다. MCP URL 재개는 제품 경로에서 제외한다. 상세는 `progress/CODEX_URL_ELICITATION_CAPABILITY_SPIKE.md` |
| 1-3. 품질 게이트·인수인계 갱신 | 🟢 | ruff·black·mypy, 전체 pytest(62 passed, 2 xfailed), 기존 MCP 평가(10/10), diff check 통과. 결과·후속 분기를 HANDOFF와 spike 기록에 반영 |

- 품질 게이트 완료: 2026-09-11 19:15:08 +09:00
- 실제 수용 결과: Codex Desktop은 URL elicitation을 native Wizard가 아닌 Tool 오류·링크로 처리했고, 브라우저 form 제출 후에도 원래 Tool을 자동 재시도하지 않았다. 다음 구현은 영속 Run + 별도 Web Wizard + 서버 측 지속 worker 대안으로 설계한다.

---

## 2026-09-10 19:23:12 +09:00 — 실클라이언트 Wizard 연속 실행·권장 기본값·상태 계약 보강

- 시작 시각: 2026-09-10 19:23:12 +09:00
- 목표: 실클라이언트 수용 테스트에서 발견된 구버전 Skill 충돌, Wizard 제출 후 중단, 미정값 반복 질문, 확정 후 수정 및 상태 게이트 결함을 해결한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 설치 Skill·신규 Tool 계약 일치화 | 🟢 | 개인 플러그인 `0.2.0+codex.20260910103953` 재설치; 설치 Skill과 원본 SHA-256 일치, 절대 MCP 실행 경로 적용 |
| 2. 설문 권장 기본값·결정 출처 모델 | 🟢 | 미입력 상세와 계획 미정 선택을 프로젝트별 보수적 기본값으로 해소하고 출처·근거·신뢰도 기록 |
| 3. OPEN 결정·preview 품질 게이트 수정 | 🟢 | `status=resolved` 결정은 허용하고 실제 open topic만 정확한 문구로 차단 |
| 4. 요구사항 수정·수동 시작 상태 전이 수정 | 🟢 | stable ID upsert·revision·후속 계약 무효화, collecting 상태 선검증, 정확한 next_action 구현 |
| 5. 통합·회귀·전체 품질 검증 | 🟢 | ruff·black·mypy 통과, pytest 55 passed, 평가 10/10, plugin/Skill validation 통과 |
| 6. 새 Codex 작업 수동 수용 테스트 | 🟢 | 사용자가 새 Codex 작업에서 고도화 산출물이 정상 생성됐음을 확인 (`확인됨`) |

- 완료 시각: 2026-09-10 19:46:03 +09:00
- 실사용 수용 확인: 2026-09-10 20:54:56 +09:00 — 새 Codex 작업의 고도화 산출물 정상 생성
- 검증 참고: pytest cache와 Black 사용자 캐시는 샌드박스 권한 경고가 있었으나 테스트·포맷 검사 결과에는 영향이 없다.

---

## 2026-09-10 11:18:12 +09:00 — HUMAN-AI 가이드 기반 문서 시스템 고도화

- 시작 시각: 2026-09-10 11:18:12 +09:00
- 목표: HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE를 유일 기준으로 구조화 문서 계약·추적성·품질 게이트·안전한 `.mvpmcp/` 출력과 선택적 HTML 프로토타입을 구현한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 0. 개발 환경·기존 기준선 복구 | 🟢 | `.venv-exec` 격리 환경 구성; ruff·black·mypy 통과, pytest 55 passed. 실행 중 서버가 `.venv` 교체를 잠가 재시작 시 정리 필요 |
| 1. 가이드 기준 고정·구조화 도메인 모델 | 🟢 | 가이드 SHA-256·coverage manifest·8문서 전체 목차·프로파일·ID 모델 구현 |
| 2. 추적성·단계 게이트·변경 이력 | 🟢 | FR/AC→TASK→TEST와 NOT RUN·증거 필수·append-only TEST/REL 계약 구현 |
| 3. 통합 Wizard·프로파일 판정 | 🟢 | 13개 문서·위험 질문과 prototype 필요/불필요, 조건부·배타 선택 구현 |
| 4. Markdown·OpenAPI·HTML 렌더링 | 🟢 | 6+조건부 2문서 전체 목차, 단일 OpenAPI, NON-SSOT 독립 HTML 구현 |
| 5. `.mvpmcp/` preview·apply | 🟢 | manifest hash·unmanaged 충돌·STALE 보존·원자적 적용 구현 |
| 6. MCP Tool·연동·레거시 cutover | 🟢 | 신규 workflow·3개 연동 지침 전환; 구형 2/6문서 Tool·exporter·모델·렌더러 삭제 |
| 7. 전체 테스트·Inspector·평가 | 🟢 | ruff·black·mypy 통과, pytest 50 passed(Chromium 포함), 환경 READY, Inspector 기동, 평가 10/10 |

- 완료 시각: 2026-09-10 13:05:00 +09:00
- 추가 발견·수정: Windows 텍스트 개행 변환으로 관리 hash가 달라지는 결함을 UTF-8 byte write로 수정하고, preview 이후 manifest 변조 차단 회귀 테스트를 추가했다.
- 운영 참고: 실행 중인 기존 MCP 서버가 원래 `.venv`를 잠가 `.venv-exec`에서 검증했다. 서버 종료 후 표준 `.venv` 재동기화가 필요하다.

---

## 2026-09-09 10:44:14 +09:00 — Wizard 즉시 재개·기술 스택 문서화

- 시작 시각: 2026-09-09 10:44:14 +09:00
- 목표: Wizard 제출을 기다려 같은 MCP 호출에서 명세 초안을 만들고, 6문서 계획에 기술 스택과 물결표 이스케이프 작성 규칙을 반영한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 제출 대기형 Wizard 흐름 구현 | 🟢 | `ask_web_survey`가 Wizard 제출을 기다리고 같은 호출에서 `spec_id`를 반환하도록 전환 |
| 기술 스택 수집·계획 문서 계약 | 🟢 | 직접 지정 시 필수 입력란을 표시하고 모든 유형의 `plan.md`에 `## 기술 스택`을 강제 |
| Markdown 물결표 작성 규칙 | 🟢 | 6문서 생성 컨텍스트에 리터럴 물결표의 `\\~` 이스케이프 규칙 반영 |
| 회귀 테스트·전체 검증 | 🟢 | ruff·black·mypy 통과, pytest 55 passed (`--basetemp .pytest-tmp-full`) |

---

## 2026-09-08 17:52:20 +09:00 — 6문서 결과물 품질 고도화

- 시작 시각: 2026-09-08 17:52:20 +09:00
- 목표: 설문·설계 계약의 상세도를 6문서 작성 컨텍스트로 전달하고, 문서 식별자와 Open Decision의 품질 게이트를 강화한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 현행 세션·문서 품질 계약 분석 | 🟢 | `resume_web_survey`의 상세 설문 누락과 기존 검증 한계를 확인 |
| 상세 설문·설계 계약 컨텍스트 전파 | 🟢 | 비차단 재개 경로를 포함해 7개 설문 상세값과 계약 세부값을 컨텍스트에 반영 |
| ID·Open Decision 품질 게이트 | 🟢 | TASK/TEST 중복·미등록·누락 ID와 미확정 결정 문서 누락을 차단 |
| 워크플로·회귀 테스트 정합화 | 🟢 | 세션 재개 지침과 상세 설문·중복 TEST 회귀 테스트 추가 |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과, pytest 54 passed (`--basetemp .pytest-tmp-full`) |

---

## 2026-09-08 16:21:44 +09:00 — 비차단 Wizard 세션·30분 만료 고도화

- 시작 시각: 2026-09-08 16:21:44 +09:00
- 목표: 브라우저 제출 대기로 MCP Tool 호출이 끝나는 문제를 제거하고, 제출 결과를 30분간 재개 가능한 세션으로 관리한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 설문 세션 모델·저장소·30분 만료 | 🟢 | 프로세스 메모리 세션과 1,800초 만료 정책 반영 |
| 비차단 시작·상태·재개 Tool | 🟢 | ask_web_survey·get_web_survey_status·resume_web_survey 등록 |
| 웹 제출 연결 및 기존 흐름 전환 | 🟢 | POST 제출값을 세션에 저장하고 blocking 대기 제거 |
| 회귀 테스트·문서 갱신 | 🟢 | Tool 등록 회귀 포함 pytest 52 passed |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과 |
| Codex 제출 완료 자동 재개 Plugin | 🟠 | 서버 범위를 넘어서는 클라이언트 어댑터 작업으로 별도 구현 필요 |

---

## 2026-09-08 12:51:13 +09:00 — 6문서 품질 계약 고도화

- 시작 시각: 2026-09-08 12:51:13 +09:00
- 목표: 기존 2문서의 상세 콘텐츠를 보존하고, 6문서 산출물의 설계·추적성·품질 게이트를 강제한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 구조화 설계 계약·검증 모델 | 🟢 | 화면·흐름·데이터·인터페이스·규칙·오류와 PASS 증거 계약 반영 |
| 문서 품질 게이트·상세 작성 컨텍스트 | 🟢 | 필수 섹션·REQ/TASK/TEST 추적성·P0 정상/경계 검증 적용 |
| Tool·워크플로·상세 설문 연결 | 🟢 | 설문 상세 항목, 신규 Tool, 자동 검증-저장 흐름 반영 |
| 회귀·품질 테스트 및 문서 갱신 | 🟢 | 품질 계약 회귀 테스트와 README·Codex 시작 Skill 갱신 |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과, pytest 51 passed; pytest 임시 폴더는 실행 사용자 TEMP 경로 사용 |


## 작업 목표

활성 프로젝트 루트의 `mvp/`에 6개 실행 계약 문서를 만들고, 요구사항·작업·테스트·검증을 추적한다.

## 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 현 구조·영향 확인 | 🟢 | 2문서 Exporter·인메모리 초안·단일 설문 흐름 확인 완료 |
| 2. 실행 계약 도메인 모델·상태 구현 | 🟢 | REQ-ID·TASK-ID·TEST-ID·검증 근거·확인 게이트 구현 완료 |
| 3. 6문서 Bundle·프로젝트 루트 Exporter 구현 | 🟢 | `<project_root>/mvp/` 고정 파일 6개 저장·재내보내기 범위 제한 완료 |
| 4. Tool·Wizard·워크플로 연결 | 🟢 | 기본 설문에 프로젝트 루트 전달, 8단계 프롬프트·전역 `/mvpmcp` Skill 갱신 완료 |
| 5. 테스트·문서 갱신 | 🟢 | 6문서 내용·재내보내기·NOT_RUN·오류 변환·README 갱신 완료 |
| 6. 품질 게이트 검증 | 🟢 | ruff·black·mypy·pytest 46개 통과 |
