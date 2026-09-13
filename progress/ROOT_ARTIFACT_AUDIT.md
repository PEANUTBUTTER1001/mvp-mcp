# 루트 산출물 inventory

> 상태: **2026-09-12 읽기 전용 감사 기반 — 이동·삭제 없이 보존 역할만 기록**

## 목적과 경계

저장소 루트의 문서·설정·runtime 산출물을 현재 계약, 역사·템플릿 참고, 평가 입력,
로컬 runtime 데이터로 구분한다. 이 문서는 어떤 파일도 이동·삭제하거나 기존 사용자
`.mvpmcp/`를 변경하는 권한을 부여하지 않는다.

## Git 추적 루트 항목

| 분류 | 항목 | 역할과 처리 정책 |
|---|---|---|
| 현재 작업 계약 | `AGENTS.md`, `README.md`, `HANDOFF.md` | 작업 규칙, 제품 계약, 현재 상태를 각각 소유한다. 구현 전 먼저 읽고 유지한다. |
| 빌드·배포 계약 | `pyproject.toml`, `uv.lock`, `Dockerfile`, CI, `.gitignore` | 의존성·품질 게이트·컨테이너·추적 제외 규칙이다. 현재 위치를 유지한다. |
| 역사·템플릿 참고 | `TEMPLATE.md`, `ARCHITECTURE_REVIEW.md` | 템플릿 구조와 역사적 설계 배경이다. `AGENTS.md`가 참고 위치로 지정하므로 보존한다. |
| 역사적 제품 기획 | `PLAN.md`, `PROPOSAL.md` | 파일 자체의 상태 표기대로 현재 구현 기준으로 사용하지 않는다. 현재 계약은 README와 HANDOFF다. |
| 평가 입력 | `evaluations/documentation_workflows.xml` | `scripts/run_mcp_evaluations.py`의 기본 입력이므로 추적·보존한다. |

## 로컬 runtime 산출물

| 경로 | 관찰된 역할 | 정책 |
|---|---|---|
| `output/` | 기본 설정이 만드는 SQLite Run DB, candidate, preview snapshot | 활성 서버 데이터다. 감사·정리 작업에서 삭제·이동하지 않는다. |
| `outputs/`, `debug.log`, cache, `.pytest-tmp-*` | `.gitignore`로 제외된 이전 실행·검증 산출물 | Git 추적 대상이 아니다. 별도 명시 승인 없이는 정리하지 않는다. |
| 기존 대상 프로젝트의 `.mvpmcp/` | 이 저장소 밖 사용자 관리 문서 패키지 | 이 서버의 preview/apply 정책이 허용하는 별도 요청에서만 다룬다. 이 마일스톤의 대상이 아니다. |

## 후속 물리 정리 전 게이트

1. Git 추적 여부와 원격·CI·스크립트 참조를 다시 확인한다.
2. 현재 계약·역사 참고·runtime 데이터 중 어느 역할인지 기록한다.
3. 이동 후 모든 링크·스크립트·Docker build context·평가 입력을 갱신하고 품질 게이트를 통과시킨다.
4. 파일 이동·삭제와 runtime data 정리는 사용자에게 별도로 승인받는다.

## 이번 마일스톤의 결과

- 루트 파일·디렉터리·runtime output은 이동하거나 삭제하지 않았다.
- Tool 등록, 플러그인 설치, server worker, timeout 자동 재개, 기존 사용자 `.mvpmcp/`는 범위 밖으로 유지했다.
