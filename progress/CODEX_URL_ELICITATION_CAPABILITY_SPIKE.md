# Codex URL Elicitation 자동 재개 Capability Spike

> 기록일: 2026-09-11  
> 범위: 승인된 2단계 적응형 Wizard 리팩터링의 단계 1  
> 판정: **MCP 프로토콜 구현은 통과, 관찰된 Codex Desktop에서는 자동 재개 불가**

## 판정 요약

브라우저 제출 후 서버가 원래 MCP 요청의 `elicitationId`로
`notifications/elicitation/complete`를 보내고, 같은 Tool 요청이 재시도되면
`continuation_received`를 반환하는 최소 서버를 구현했다. 서버·프로토콜 수준의 E2E는
통과했다.

다만 표준은 클라이언트가 원래 요청을 **자동 재시도할 수 있다(MAY)**고만 규정한다.
2026-09-11 실제 Codex Desktop 수용 테스트에서 재시도는 관찰되지 않았다. 따라서 URL
elicitation을 이 제품의 제출 후 자동 진행 계약으로 삼지 않으며, 기존 blocking Wizard를 단순 교체하지 않는다.

## 만든 격리된 측정 경로

```text
mvp_capability_probe(probe_id)
  → URL elicitation required
  → loopback HTTP form (127.0.0.1)
  → POST 완료
  → notifications/elicitation/complete(probe_id)
  → 원래 Tool 요청 재시도 시 continuation_received
```

- 제품 `main.py`에는 등록하지 않았다. 기존 공개 Tool 12개와 사용자 워크플로는 변하지 않는다.
- 상태는 SQLite에 기록한다. 중복 POST는 한 번만 `browser_completed`로 전이한다.
- `file://` 대신 loopback HTTP URL을 쓰므로 브라우저의 로컬 파일 정책에 의존하지 않는다.
- Tool adapter는 URL elicitation 예외를 그대로 전달한다. 공통 `safe_async_tool`이 이를 일반 오류
  문자열로 바꾸지 않도록 보완했다.

## 검증 결과

| 검증 대상 | 결과 | 의미 |
|---|---|---|
| 상태 모델·SQLite 영속성·중복 전이 | 통과 | 제출과 재시도 상태가 프로세스 메모리에만 남지 않는다. |
| loopback form GET/POST | 통과 | 제출 callback이 한 번만 발생한다. |
| completion notification | 통과 | 원래 MCP session으로 완료 알림이 전달된다. |
| 메모리 MCP protocol E2E | 통과 | URL 요청 → POST → notification → **수동 retry** → `continuation_received`가 확인됐다. |
| 일반 Python MCP client 동작 확인 | 자동 재시도 없음 | 현재 SDK client는 completion notification을 받고도 재시도 로직을 구현하지 않는다. Codex 동작의 증거는 아니다. |
| 비대화형 `codex exec` 시도 | 판정 불가 | 초기 agent 응답 뒤 `mvp_capability_probe` 호출 이벤트가 나오지 않아 URL·재시도를 측정할 수 없었다. 이것만으로 Codex 미지원이라고 결론 내리지 않는다. |
| 실제 Codex Desktop 수용 테스트 | 자동 재개 실패 | `-32042` URL elicitation 응답이 Wizard 창이 아니라 Tool 오류와 링크로 표시됐다. 사용자가 `127.0.0.1` form을 직접 제출했지만, 원래 Tool 호출은 자동 재시도되지 않았다. |

현재 사용 중인 MCP 규격은 completion 뒤 클라이언트가 원래 요청을 자동 재시도할 수 있다고
표현하며, 이를 의무화하지 않는다. [MCP Elicitation specification](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
Codex App Server 문서에는 URL elicitation 요청 처리 경로가 안내돼 있지만, 브라우저 밖 제출 뒤
모델 턴 자동 재개 보장은 별도 계약으로 명시되어 있지 않다. [Codex App Server documentation](https://learn.chatgpt.com/ko-KR/docs/app-server)

## 2026-09-11 실제 Codex Desktop 수용 결과

```text
Tool 호출
  → -32042 URL elicitation error + 127.0.0.1 링크 표시
  → native Wizard 자동 표시 없음
  → 사용자가 브라우저에서 form을 직접 제출
  → 원래 Tool 호출 자동 retry 없음
```

이 결과는 이 테스트 환경의 Codex Desktop에서 두 UX 조건 모두 충족하지 못했음을 뜻한다.

1. Tool 호출 후 Web Wizard가 자동으로 열리지 않는다.
2. 브라우저 제출 후 채팅 입력 없이 같은 Tool 호출이 자동 재개되지 않는다.

`notifications/elicitation/complete`를 수신하지 않았는지, 수신했지만 retry를 하지 않았는지는
클라이언트 내부 관찰 없이는 구분할 수 없다. 하지만 제품 설계 관점에서는 결과가 같다. MCP 표준
URL elicitation에 사용자의 자동 진행 경험을 의존해서는 안 된다.

## 실제 Codex 수동 수용 테스트

이 테스트는 제품 MCP를 바꾸지 않고 임시 probe 서버만 추가해 시행한다. 일반 로컬 터미널에서
실행하고, 완료 후 즉시 제거한다.

```powershell
codex mcp add mvp-capability-probe -- `
  "C:\Users\user\PycharmProjects\mvp-mcp\.venv-exec\Scripts\python.exe" `
  "C:\Users\user\PycharmProjects\mvp-mcp\scripts\run_codex_url_elicitation_spike.py"
```

1. 새 Codex task에서 `mvp_capability_probe`를 `probe_id` 하나로 한 번 호출하게 한다.
2. 표시된 `127.0.0.1` form을 열어 **Submit** 한다.
3. 채팅을 새로 입력하지 않은 상태에서 원래 Tool 요청이 자동 재시도되어
   `status: "continuation_received"`가 나오는지 확인한다.
4. 검증 뒤 임시 서버를 제거한다.

```powershell
codex mcp remove mvp-capability-probe
```

### 수용 기준과 후속 분기

| 관찰 결과 | 단계 2 구현 선택 |
|---|---|
| 같은 요청이 자동 재시도되고 `continuation_received` 반환 | URL elicitation + 영속 Run Coordinator를 제품 경로로 채택한다. |
| 제출 알림은 오지만 재시도가 없다 | URL은 설문 UI로만 쓰고, 재개는 명시적 `documentation_wizard_run_status`/재시도 Tool 또는 사용자 승인 범위의 지속 워커로 설계한다. |
| URL elicitation 자체가 열리지 않는다 | **실제 관찰 결과.** MCP URL elicitation을 product UI로 채택하지 않는다. 영속 Run + 별도 Web Wizard + 서버 측 지속 worker를 설계한다. |

## 다음 구현의 경계

이 판정이 실제 Codex에서 확정되기 전에는 다음을 시작하지 않는다.

- 서버 측 모델 API 지속 실행 worker 도입
- 기존 Tool 대량 삭제 또는 공개 Tool 계약 변경
- 기존 세션 코드를 단순히 활성 경로에 연결하는 변경
- 사용자 `.mvpmcp/` 산출물 자동 반영 정책 변경

실제 client 결과가 기록됐으며 대체 경로가 필요하다.

## 2026-09-12 후속 결정과 구현 결과

서버 측 worker는 Codex 모델 자체를 독립적으로 재개할 수 없으므로, 모델 API·인증·감사 범위를 새로
승인하지 않는 한 이 문제의 직접 해법이 아니다. 대신 기존에 실사용된 `LocalWebSurveyForm.ask()`처럼
**현재 MCP Tool 호출을 browser POST까지 동기 대기**시키는 전송 방식을 2단계 Run에 적용했다.

```text
1차 blocking form 제출 → Tool 결과가 같은 모델 턴으로 반환
→ 모델이 2차 질문 호출 → 2차 blocking form 제출
→ DRAFT_READY + 기존 문서화 Tool 체인
```

새 `documentation_start_adaptive_wizard`는 SQLite Run에 request_key·version·제출 hash를 보관하고,
같은 request_key 또는 같은 2차 질문 재호출에서 중복 form·초안을 만들지 않는다. 이 경로는 URL
elicitation의 client retry에 의존하지 않는다. 현재는 `DRAFT_READY`와 preview 호환 연결까지이며,
후보 package·browser 완료 화면·자동 안전 반영은 별도 후속 단계다.
