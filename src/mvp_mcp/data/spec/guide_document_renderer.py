"""구조화된 명세를 가이드의 전체 목차를 가진 Markdown 문서로 렌더링한다."""

# ruff: noqa: E501

from __future__ import annotations

from datetime import UTC, datetime

from mvp_mcp.domain.spec.documentation_model import ChangeType, DocumentProfile
from mvp_mcp.domain.spec.guide_contract import DOCUMENT_CONTRACTS
from mvp_mcp.domain.spec.model import SpecDraft


class GuideDocumentRenderer:
    def render(self, draft: SpecDraft, profile: DocumentProfile) -> dict[str, str]:
        if profile is DocumentProfile.PROTOTYPE_4:
            names = [
                "REQUIREMENTS.md",
                "ARCHITECTURE.md",
                "AGENTS.md",
                "DELIVERY_CHECKLIST.md",
            ]
        else:
            names = [
                "REQUIREMENTS.md",
                "ARCHITECTURE.md",
                "AGENTS.md",
                "IMPLEMENTATION_PLAN.md",
                "TEST_PLAN.md",
                "RELEASE_RUNBOOK.md",
            ]
        if profile in {DocumentProfile.MVP_6_SECURITY, DocumentProfile.MVP_6_FULL_RISK}:
            names.append("SECURITY_PRIVACY.md")
        if profile in {DocumentProfile.MVP_6_MIGRATION, DocumentProfile.MVP_6_FULL_RISK}:
            names.append("MIGRATION_PLAN.md")

        rendered: dict[str, str] = {"README.md": self._readme(names, draft)}
        for name in names:
            path = name if name == "AGENTS.md" else f"docs/{name}"
            rendered[path] = self._document(name, draft)
        return rendered

    def _document(self, name: str, draft: SpecDraft) -> str:
        contract = DOCUMENT_CONTRACTS[name]
        lines = [
            "---",
            f"document: {contract.name}",
            "version: 0.1.0",
            "status: DRAFT",
            "owner: UNASSIGNED",
            "reviewers: []",
            f"last_updated: {datetime.now(UTC).date().isoformat()}",
            'applies_to: "MVP 0.1"',
            "related_documents:",
            "  - REQUIREMENTS.md",
            "  - ARCHITECTURE.md",
            "---",
            "",
            f"# {name}",
            "",
            "> DRAFT — 문서 생성은 구현·테스트·출시 완료를 의미하지 않는다.",
            "",
            "## 이 문서가 결정하는 것",
            "",
            f"- {contract.owns}",
            "",
            "## 이 문서가 참조만 하는 것",
            "",
            f"- {contract.references}",
            "",
            "## 이 문서가 결정하지 않는 것",
            "",
            f"- {contract.excludes}",
            "",
        ]
        bodies = self._bodies(name, draft)
        for index, section in enumerate(contract.sections, start=1):
            lines.extend(
                [f"## {index}. {section}", "", bodies.get(section, self._fallback(section)), ""]
            )
        return "\n".join(lines).rstrip() + "\n"

    def _bodies(self, name: str, draft: SpecDraft) -> dict[str, str]:
        if name == "REQUIREMENTS.md":
            return self._requirements(draft)
        if name == "ARCHITECTURE.md":
            return self._architecture(draft)
        if name == "AGENTS.md":
            return self._agents(draft)
        if name == "IMPLEMENTATION_PLAN.md":
            return self._implementation(draft)
        if name == "TEST_PLAN.md":
            return self._tests(draft)
        if name == "RELEASE_RUNBOOK.md":
            return self._release(draft)
        if name == "SECURITY_PRIVACY.md":
            return self._security(draft)
        if name == "DELIVERY_CHECKLIST.md":
            return self._delivery_checklist(draft)
        return self._migration(draft)

    def _delivery_checklist(self, draft: SpecDraft) -> dict[str, str]:
        implementation = self._implementation(draft)
        tests = self._tests(draft)
        release = self._release(draft)
        return {
            "문서 정보": "1인·로컬·저위험 프로토타입 전용 통합 실행 문서다. 기본 6문서와 동시에 사용하지 않는다.",
            "implementation": "\n\n".join(
                (
                    implementation["작업 목록"],
                    implementation["우선순위"],
                    implementation["단계별 구현 계획"],
                    implementation["검증 증거"],
                )
            ),
            "verification": "\n\n".join(
                (
                    tests["테스트 지역 추적표"],
                    tests["정상 시나리오"],
                    tests["오류·예외 시나리오"],
                    tests["경계값"],
                    tests["자동 검증 명령"],
                    tests["테스트 결과"],
                )
            ),
            "delivery": "\n\n".join(
                (
                    release["배포 전 조건"],
                    release["중단·롤백 조건"],
                    release["롤백 절차"],
                    release["릴리스 결과"],
                )
            ),
            "현재 상태와 인수인계": implementation["인수인계"],
            "변경 이력": implementation["변경·영향 이력"],
        }

    @staticmethod
    def _readme(names: list[str], draft: SpecDraft) -> str:
        links = [
            f"- [{name}]({'AGENTS.md' if name == 'AGENTS.md' else f'docs/{name}'})"
            for name in names
        ]
        return "\n".join(
            [
                "# Project documentation",
                "",
                f"> {draft.user_request}",
                "",
                "이 디렉터리는 mvp-mcp가 관리하는 문서 패키지다. 문서 생성은 구현·검증·출시 완료가 아니다.",
                "",
                "## Documentation",
                "",
                *links,
                "",
                "HTTP API 계약과 선택적 프로토타입은 존재할 때 각각 `api/`와 `prototype/`에서 확인한다.",
                "검증 증거는 실제 실행 뒤에만 `artifacts/`에 기록한다.",
                "",
            ]
        )

    def _requirements(self, draft: SpecDraft) -> dict[str, str]:
        intake = draft.intake
        recommended = self._recommended_decisions(draft)
        unresolved = self._unresolved_decisions(draft)
        requirements = "\n".join(
            f"### {item.id}: {item.title}\n\n- 설명: {item.description}\n- 우선순위: {item.priority.value}\n"
            f"- 근거 상태: CONFIRMED\n- 수용 기준: {', '.join(self._ac_ids(draft, item.id))}"
            for item in draft.requirements
        )
        acceptance = []
        ac_index = 1
        for item in draft.requirements:
            for criterion in item.acceptance_criteria:
                acceptance.append(
                    f"### AC-{ac_index:03d}\n\n- 관련 요구사항: {item.id}\n- 관찰 가능한 결과: {criterion}"
                )
                ac_index += 1
        trace_rows = []
        for item in draft.requirements:
            task_ids = [task.id for task in draft.tasks if item.id in task.requirement_ids]
            test_ids = [test.id for test in draft.test_cases if item.id in test.requirement_ids]
            trace_rows.append(
                f"| {item.id} | {', '.join(self._ac_ids(draft, item.id))} | "
                f"ASR-001 | {', '.join(task_ids) or '-'} | 미구현 | "
                f"{', '.join(test_ids) or '-'} | NOT RUN | RC-001 | - |"
            )
        flows = self._flows(draft)
        return {
            "문서 정보": "상단 메타데이터가 현재 DRAFT 상태와 적용 MVP를 정의한다. 승인 책임자는 구현 착수 전에 지정한다.",
            "배경과 문제": intake.get("problem")
            or "사용자 요청에서 해결할 문제를 구체화해야 한다.",
            "제품 목표": intake.get("goal") or draft.user_request,
            "대상 사용자와 이해관계자": intake.get("target_users")
            or "직접 사용자, 운영자와 구현 담당 Agent",
            "운용 개념": flows,
            "사용자 리서치와 근거": "ASSUMED — 현재 입력은 사용자 요청과 설문에 기반한다. 첫 사용성 검증에서 가정을 확인한다.",
            "가정·제약·의존성": (
                (intake.get("constraints") or "MVP 범위를 벗어나는 기능은 DEFERRED로 관리한다.")
                + ("\n\n### 권장 기본값 결정\n\n" + recommended if recommended else "")
            ),
            "포함 범위": self._bullets(
                draft.features or [item.title for item in draft.requirements]
            ),
            "비범위": (
                self._bullets(draft.deferred)
                if draft.deferred
                else "- 명시적으로 승인되지 않은 기능 확장"
            ),
            "사용자 흐름과 상태": flows
            + "\n\n로딩·빈 상태·오류·권한 없음 상태를 각각 독립적으로 표시한다.",
            "기능 요구사항": requirements,
            "비기능 요구사항": "- NFR-PERF-001: 핵심 상호작용은 정상 로컬 환경에서 2초 안에 피드백을 표시한다.\n- NFR-A11Y-001: 키보드만으로 핵심 흐름을 완료하고 focus를 식별할 수 있어야 한다.",
            "데이터·보안 요구사항": self._data_security(draft),
            "수용 기준": "\n\n".join(acceptance),
            "성공 지표": intake.get("success_metrics")
            or "핵심 사용자 흐름 완료율과 오류 없이 완료한 세션 비율을 측정한다.",
            "요구사항 추적표": "| 요구사항 | 수용 기준 | 설계 | 작업 | 코드 | 테스트 | 결과 | 출시 점검 | 릴리스 |\n|---|---|---|---|---|---|---|---|---|\n"
            + "\n".join(trace_rows),
            "미해결 질문": unresolved
            or "- 현재 구조화 계약에 등록된 OPEN 항목 없음. 새 미결정 사항은 담당자·기한·차단 범위와 함께 등록한다.",
            "변경 이력": "| 변경 | 내용 | 영향 |\n|---|---|---|\n| CHG-001 | 초기 요구사항 계약 생성 | 모든 TASK/TEST/RC의 기준 버전 |",
        }

    def _architecture(self, draft: SpecDraft) -> dict[str, str]:
        design = draft.design_contract
        assert design is not None
        components = (
            "\n".join(
                f"| {screen.name} | {screen.purpose} 및 상태 표현 | 영속 저장 | {', '.join(item.id for item in draft.requirements)} |"
                for screen in design.screens
            )
            or "| Workflow Adapter | 사용자 흐름 입력과 결과 표시 | 도메인 규칙 결정 | FR-001 |"
        )
        interfaces = (
            "\n".join(
                f"- **{item.name} ({item.kind})**: {item.purpose}; 입력={item.input_summary}; 출력={item.output_summary}; 오류={', '.join(item.error_cases)}"
                for item in design.interfaces
            )
            or "- 외부 HTTP 계약 없음. 내부 호출은 입력 검증 후 도메인 유스케이스를 호출한다."
        )
        entities = (
            "\n".join(
                f"- **{item.name}**: 필드 {', '.join(item.fields)}; 제약 {', '.join(item.constraints)}; 관계 {', '.join(item.relations) or '없음'}"
                for item in design.data_entities
            )
            or "- 영속 데이터 없음 — 설문에서 저장소 불필요 선택."
        )
        return {
            "문서 정보": "상단 메타데이터와 REQUIREMENTS 적용 범위를 기준으로 하는 DRAFT 설계다.",
            "설계 목표": "추적 가능한 요구사항, 명시적 계층 경계, 안전한 입력 검증과 복구 가능한 변경을 우선한다.",
            "관련 요구사항과 ASR": f"- ASR-001: 활성 요구사항({', '.join(item.id for item in draft.requirements)})을 단방향 책임 구조로 구현한다.",
            "현재 구조": "신규 구축이면 NOT_APPLICABLE — 기존 구조가 없다. 기존 변경이면 실제 저장소 분석 결과로 이 절을 갱신한다.",
            "변경 후 구조": "기술 선택과 디렉터리 경로의 SSOT는 아래 두 섹션이다. 기존 저장소의 실제 구조는 조사 근거가 있을 때만 KEEP/MODIFY로 확정한다.",
            "기술 스택": self._technology_stack_table(draft),
            "디렉터리 구조": self._directory_structure_tree(draft),
            "C4 모델": "```text\n사용자 → UI/Interface Adapter → Application Use Case → Domain → Storage/External Port\n```\nC1·C2와 핵심 컴포넌트 책임까지만 표현한다.",
            "컴포넌트 책임": "| 컴포넌트 | 책임 | 비책임 | 관련 요구사항 |\n|---|---|---|---|\n"
            + components,
            "데이터 흐름": "입력 수집 → 경계 검증 → 유스케이스 처리 → 저장/외부 Port → 결과 변환 순서다. 실패는 입력을 보존하고 안전한 복구 경로를 제공한다.",
            "API·이벤트 계약": interfaces
            + (
                "\n\nHTTP 상세 계약은 `../api/openapi.yaml`만 SSOT로 사용한다."
                if draft.documentation.http_api_mode.value != "없음"
                else ""
            ),
            "데이터 모델": entities,
            "인증·권한·보안": self._data_security(draft),
            "오류 처리": self._errors(draft),
            "마이그레이션": (
                "기존 데이터 변경 시 `MIGRATION_PLAN.md`를 참조한다."
                if draft.documentation.migration_active
                else "NOT_APPLICABLE — 기존 데이터 변환을 선택하지 않았다."
            ),
            "호환성": "선택된 UI surface와 런타임을 지원한다. 공개 계약의 breaking change는 승인과 버전 변경이 필요하다.",
            "성능·확장성": "NFR-PERF-001을 기준으로 측정하고 병목이 확인되기 전 분산 구조를 도입하지 않는다.",
            "기술적 위험": "외부 의존성 실패, 잘못된 입력, 저장 실패를 주요 위험으로 관리하고 timeout·검증·재시도로 완화한다.",
            "주요 결정과 ADR": "### ADR-001: 구조화 계약에서 문서 렌더링\n\n- 상태: PROPOSED\n- 결정: 자유 형식 Markdown 대신 검증된 모델을 렌더링한다.\n- 장점: 목차·SSOT·추적성 강제\n- 단점: 모델 변경 비용\n- 재검토 조건: 가이드의 Major 변경",
            "설계 품질 게이트": "- 활성 ASR과 ADR을 검토한다.\n- OPEN 결정과 owner 없는 차단 항목이 없어야 한다.\n- 테스트 PASS나 출시 승인을 이 문서에서 주장하지 않는다.",
        }

    @staticmethod
    def _technology_stack_table(draft: SpecDraft) -> str:
        recommended = next(
            (item for item in draft.recommended_decisions if item.field == "tech_stack"),
            None,
        )
        selected = draft.answers.get("tech_stack", "")
        status = (
            "RECOMMENDED"
            if recommended is not None or selected in {"AI 권장안 사용", "기본 스택 사용"}
            else "CONFIRMED"
        )
        rationale = (
            recommended.reason
            if recommended is not None
            else (
                "Wizard에서 유형 기본 스택 사용을 선택했다."
                if status == "RECOMMENDED"
                else "사용자가 Wizard에서 직접 지정했다."
            )
        )
        roles = {
            "frontend": "사용자 인터페이스",
            "ui": "사용자 인터페이스",
            "backend": "애플리케이션·API 처리",
            "framework": "서버 프레임워크",
            "database": "영속 데이터 저장",
            "storage": "파일·객체 저장",
            "orm": "영속성 매핑",
            "auth": "인증·권한",
            "language": "구현 언어",
            "runtime": "실행 환경",
            "build": "빌드·패키징",
            "testing": "자동 검증",
            "deployment": "배포 환경",
            "distribution": "배포 방식",
            "data": "데이터 처리",
            "ml": "모델 학습·추론",
            "processing": "데이터 변환",
            "orchestration": "작업 오케스트레이션",
            "transport": "통신 전송",
            "validation": "입력 검증",
            "packaging": "패키지 관리",
        }
        rows = []
        for key, value in draft.tech_stack.items():
            escaped_value = value.replace("|", r"\|")
            rows.append(
                f"| {key} | {escaped_value} | {roles.get(key, key + ' 구성 요소')} | {status} | {rationale} |"
            )
        if not rows:
            rows.append(
                "| 구현 기술 | 미정 | 기술 선택 | UNRESOLVED | Wizard 또는 저장소 조사로 확정 필요 |"
            )
        return (
            "| 분류 | 기술·버전 | 역할 | 근거 상태 | 결정·근거 |\n"
            "|---|---|---|---|---|\n" + "\n".join(rows)
        )

    @staticmethod
    def _directory_structure_tree(draft: SpecDraft) -> str:
        if draft.documentation.change_type is ChangeType.NEW:
            entries = [
                "src/  # [NEW] 구현 소스 루트 — 기술 스택과 TASK에 맞춰 하위 구조를 확정한다.",
                "tests/  # [NEW] 자동·회귀 테스트 루트 — TEST 계약에 연결한다.",
            ]
        else:
            entries = [
                "<repository-root>/  # [OPTIONAL] 실제 저장소 조사를 마친 뒤 KEEP/MODIFY 경로로 확정한다.",
            ]
        return "```text\n" + "\n".join(entries) + "\n```"

    def _agents(self, draft: SpecDraft) -> dict[str, str]:
        commands = self._commands(draft)
        if draft.documentation.profile is DocumentProfile.PROTOTYPE_4:
            detailed_links = "- [요구사항](docs/REQUIREMENTS.md)\n- [설계](docs/ARCHITECTURE.md)\n- [실행·검증·전달](docs/DELIVERY_CHECKLIST.md)"
            plan_reference = "DELIVERY_CHECKLIST 작업 순서"
        else:
            detailed_links = "- [요구사항](docs/REQUIREMENTS.md)\n- [설계](docs/ARCHITECTURE.md)\n- [구현 계획](docs/IMPLEMENTATION_PLAN.md)\n- [테스트](docs/TEST_PLAN.md)\n- [릴리스](docs/RELEASE_RUNBOOK.md)"
            plan_reference = "IMPLEMENTATION_PLAN 작업 순서"
        return {
            "적용 범위": "이 파일은 `.mvpmcp/` 문서 계약을 사용하는 저장소 전체에 적용한다. 더 구체적인 `AGENTS.override.md`가 있는 서비스는 해당 범위에서만 추가 적용한다.",
            "문서 우선순위": f"1. 안전·권한·파괴 작업 승인\n2. 가장 구체적인 AGENTS 규칙\n3. 영역별 승인된 SSOT\n4. 승인된 현재 작업\n5. {plan_reference}",
            "프로젝트 구조": "작업 전 저장소 루트와 이 문서의 상세 문서 링크를 확인한다.",
            "설치·실행 방법": commands[0],
            "테스트·린트·빌드 명령": commands[1],
            "코딩 규칙": "기존 구조와 명명 규칙을 반복한다. 입력 경계에서 검증하고 비즈니스 로직과 I/O를 분리하며 오류를 숨기지 않는다.",
            "재사용할 구성요소": "새 코드를 만들기 전에 기존 컴포넌트·유틸리티·Port를 검색하고 같은 책임을 중복 구현하지 않는다.",
            "수정 금지 영역": "생성 파일·lockfile·공개 계약·마이그레이션·보안 규칙을 임의로 변경하지 않는다. `.mvpmcp/` 밖 파일은 별도 작업 승인 없이 수정하지 않는다.",
            "데이터·보안 규칙": "비밀정보와 개인정보를 코드·로그·증거에 기록하지 않는다. 외부 입력을 검증하고 권한은 서버 측에서 확인한다.",
            "승인 필요 작업": "- 운영 의존성 추가\n- 공개 API 변경\n- 데이터 마이그레이션·삭제\n- 실제 배포·결제·외부 전송\n- 보안 규칙 완화\n- 테스트 삭제·건너뛰기",
            "코드 리뷰 규칙": "요구사항 ID, 계층 경계, 오류·경계 입력, 데이터 손실, 권한 우회와 회귀 테스트를 확인한다.",
            "품질 게이트": "모든 필수 명령이 종료 코드 0이어야 한다. 실행하지 않은 검증은 PASS로 표시하지 않는다.",
            "완료 보고 형식": "변경 파일, 구현한 요구사항 ID, 실행한 명령과 결과, 미실행 항목, 알려진 위험과 다음 행동을 보고한다.",
            "하위 지침·오버라이드": "하위 `AGENTS.override.md`는 해당 디렉터리에만 적용되며 상위 안전·권한 규칙을 약화할 수 없다.",
            "상세 문서 링크": detailed_links,
        }

    def _implementation(self, draft: SpecDraft) -> dict[str, str]:
        rows = "\n".join(
            f"| {task.id} | {task.title} | {', '.join(task.requirement_ids)} | "
            f"{', '.join(task.depends_on) or '-'} | UNASSIGNED | READY |"
            for task in draft.tasks
        )
        files = "\n".join(f"- {task.id}: {', '.join(task.file_scope)}" for task in draft.tasks)
        files += "\n\n- 경로 SSOT: `ARCHITECTURE.md`의 `디렉터리 구조`를 따른다."
        evidence = "\n".join(
            f"- {task.id}: 완료 조건 {', '.join(task.done_when)}; 연결 TEST는 TEST_PLAN 참조"
            for task in draft.tasks
        )
        return {
            "문서 정보": "DRAFT 계획이며 상태 갱신 책임자는 구현 착수 전에 지정한다.",
            "구현 목표": f"{', '.join(item.id for item in draft.requirements)}를 구현해 {draft.intake.get('goal', draft.user_request)}를 달성한다.",
            "작업 목록": "| 작업 | 내용 | 요구사항 | 의존성 | 담당 | 상태 |\n|---|---|---|---|---|---|\n"
            + rows,
            "우선순위": "요구사항 P0, 위험 완화, 선행 의존성 순서로 수행한다. 동일 우선순위는 TEST 가능 단위가 작은 작업부터 진행한다.",
            "선행 조건과 의존성": "각 TASK의 depends_on과 활성 ADR 승인을 확인한다. OPEN 결정이 영향을 주면 시작하지 않는다.",
            "담당자·담당 Agent": "초기 상태는 UNASSIGNED다. 구현자와 독립 검토자를 작업 시작 전에 분리 지정한다.",
            "협업·변경 절차": "요구 변경은 CHG ID를 먼저 만들고 영향받는 TASK·TEST·RC를 갱신한 뒤 구현한다.",
            "단계별 구현 계획": self._bullets(
                [f"{task.id} — {task.title}" for task in draft.tasks]
            ),
            "변경 파일": files,
            "검증 증거": evidence,
            "차단 요소와 미해결 질문": "현재 OPEN 결정이 있으면 해당 TASK를 BLOCKED로 전환하고 담당자·기한을 기록한다.",
            "변경·영향 이력": "| 변경 | 요구사항 | 영향 작업 | 영향 테스트 |\n|---|---|---|---|\n| CHG-001 | 초기 계약 | 전체 TASK | 전체 TEST |",
            "현재 상태": "계획 생성 시점에는 구현 미착수다. 각 TASK는 `READY → IN_PROGRESS → REVIEW → DONE/BLOCKED`로 갱신한다.",
            "인수인계": "다음 작업자는 마지막 완료 TASK, 현재 차단 항목, 변경 파일, 검증 증거와 다음 READY TASK를 먼저 확인한다.",
        }

    def _tests(self, draft: SpecDraft) -> dict[str, str]:
        cases = "\n\n".join(
            f"### {test.id}: {test.scenario}\n\n- 관련 요구사항: {', '.join(test.requirement_ids)}\n"
            f"- 종류: {test.case_type}\n- 실행 방식: {test.kind}\n- 기대 결과: {test.expected_result}\n"
            "- 실제 결과: NOT RUN\n- 실행자: -\n- 환경: -\n- 증거: -"
            for test in draft.test_cases
        )
        result_rows = "\n".join(
            f"| {test.id} | - | NOT RUN | - | - | - | 구현·테스트 미실행 |"
            for test in draft.test_cases
        )
        trace = "\n".join(
            f"| {', '.join(test.requirement_ids)} | {', '.join(self._all_ac_for_refs(draft, test.requirement_ids))} | {test.id} | - |"
            for test in draft.test_cases
        )
        return {
            "문서 정보": "초기 실행 상태는 모두 `NOT RUN`이다. 실제 명령·환경·실행자·시각·증거가 있어야 PASS가 된다.",
            "테스트 목적과 범위": f"활성 요구사항 {', '.join(item.id for item in draft.requirements)}과 핵심 흐름을 검증한다.",
            "제외 범위": "실제 운영 배포·외부 결제·실사용자 데이터 검증은 이 초기 계획에서 실행하지 않는다.",
            "테스트 환경": "OS·브라우저·런타임·데이터 버전을 실행 시 기록한다. 현재 환경은 NOT RUN이다.",
            "테스트 지역 추적표": "| 요구사항 | 수용 기준 | 테스트 | 증거 |\n|---|---|---|---|\n"
            + trace,
            "정상 시나리오": cases,
            "오류·예외 시나리오": "잘못된 입력, 권한 없음, 저장·외부 서비스 실패 시 안전한 오류와 복구 경로를 확인한다.",
            "경계값": "빈 값, 최솟값·최댓값, 중복, 최대 길이와 대용량 입력을 검증한다.",
            "권한별 테스트": "인증·역할이 활성화되면 허용 사용자와 미인증·타 사용자 접근 차단을 각각 TEST-SEC로 검증한다.",
            "데이터·마이그레이션 테스트": "DATA 요구와 마이그레이션이 활성화되면 레코드 수·필수값·중복·재실행·복구를 검증한다.",
            "접근성 테스트": "키보드만으로 핵심 흐름을 완료하고 focus·label·대비·상태 알림을 확인한다.",
            "보안 테스트": "입력 변조, 인증·인가, 비밀정보·로그 노출과 파일 업로드 경계를 검증한다.",
            "회귀 테스트": "CHG 영향 분석에서 연결된 기존 TEST를 재실행하고 삭제·비활성화로 통과시키지 않는다.",
            "자동 검증 명령": self._commands(draft)[1],
            "수동 확인 항목": "화면 문구, 반응형 배치, 보조기술 안내와 파괴 작업 승인 표시를 사람이 확인한다.",
            "테스트 품질 게이트": "활성 S/A/B 테스트와 필수 보안 테스트가 모두 PASS이고 명령 종료 코드가 0이어야 한다.",
            "테스트 결과": "| 테스트 | 환경 | 결과 | 실행자 | 날짜 | 증거 | 비고 |\n|---|---|---|---|---|---|---|\n"
            + result_rows,
            "알려진 제한": "초기 문서 생성 시 모든 결과는 NOT RUN이며 실제 품질·배포 가능성을 보장하지 않는다.",
        }

    def _release(self, draft: SpecDraft) -> dict[str, str]:
        return {
            "문서 정보": "초기 릴리스 상태는 미출시다. Release Owner와 승인자는 실제 배포 전에 지정한다.",
            "릴리스 범위": f"후보 범위: {', '.join(item.id for item in draft.requirements)}. 최종 범위는 승인된 commit과 함께 고정한다.",
            "Definition of Done": "- 요구·AC 승인\n- 코드·문서 갱신\n- 필수 TEST PASS\n- 코드 리뷰 완료\n- 보안·마이그레이션 영향 검토\n- 배포·롤백 절차 확인\n- 제한·증거 보존",
            "버전과 대상 커밋": "버전: 미정\n\n대상 commit: NOT RUN — 구현 결과가 아직 없다.",
            "배포 artifact": "NOT RUN — artifact 이름·위치·SHA-256은 빌드 후 기록한다.",
            "배포 전 조건": "RC-001 대상 commit/artifact 확인, RC-002 활성 테스트 PASS, RC-003 OPEN 없음, RC-004 백업·롤백 확인.",
            "환경별 설정": "개발·스테이징·운영 설정과 비밀정보 위치를 분리하고 문서에 값 자체를 기록하지 않는다.",
            "빌드·배포 명령": "NOT RUN — 승인된 대상 환경의 재현 가능한 명령을 실행 전에 확정한다.",
            "마이그레이션 순서": "MIGRATION_PLAN이 있으면 해당 실행 ID를 참조한다. 없으면 NOT_APPLICABLE이다.",
            "기능 플래그": "기능 플래그가 없으면 NOT_APPLICABLE 근거를 남긴다. 있다면 기본값·활성·제거 조건을 기록한다.",
            "승인·권한자": "빌드·배포·롤백 실행자와 승인자를 분리한다. 현재 UNASSIGNED이므로 출시가 차단된다.",
            "제한 공개·카나리": "실제 사용자 배포는 작은 대상부터 시작하고 오류·지연 임계치가 정상일 때만 확대한다.",
            "모니터링 지표": "오류율, p95 지연시간, 핵심 흐름 성공률, 데이터 정합성을 관찰한다.",
            "성공·실패 판단": "수치 임계값은 운영 부하 기준으로 승인 전에 확정한다. 미확정 상태에서는 출시할 수 없다.",
            "중단·롤백 조건": "핵심 흐름 실패, 권한 우회, 데이터 손실·중복, 임계치 초과 시 즉시 중단한다.",
            "롤백 절차": "트래픽 중단 → 이전 artifact 복원 → 필요 시 데이터 복구 → 핵심 흐름 확인 → 결과 기록 순서다.",
            "장애 대응·에스컬레이션": "탐지 즉시 Release Owner에게 알리고 영향·완화·다음 갱신 시점을 기록한다.",
            "백업·복구": "백업 위치·보존·암호화와 복구 리허설 증거가 없으면 RC-004를 통과하지 않는다.",
            "릴리스 결과": "릴리스 ID: 미생성\n\n상태: NOT RUN\n\n실제 배포와 승인 증거가 없으므로 RELEASED를 표시하지 않는다.",
        }

    def _security(self, draft: SpecDraft) -> dict[str, str]:
        doc = draft.documentation
        return {
            "보안 범위": f"인증={', '.join(v.value for v in doc.auth_capabilities)}, 개인정보={', '.join(v.value for v in doc.personal_data_types)}, 기타 위험={', '.join(v.value for v in doc.other_risks)}",
            "보호 대상 자산": "계정 식별자, 사용자 콘텐츠, 인증 세션, 업로드 파일과 운영 권한을 위험 신호에 따라 보호한다.",
            "신뢰 경계": "브라우저·클라이언트와 외부 입력은 신뢰하지 않으며 서버 경계에서 형식·크기·권한을 재검증한다.",
            "위협 모델": "자격 증명 탈취, 타 사용자 리소스 접근, 악성 파일·입력, 비밀정보 노출을 주요 시나리오로 둔다.",
            "보안 요구사항": "- SEC-001: 모든 외부 입력은 허용 목록·길이·형식으로 검증한다.\n- SEC-002: 리소스 권한을 서버 측에서 확인한다.\n- SEC-003: 비밀정보와 개인정보를 로그에 남기지 않는다.",
            "인증": "선택된 방식: "
            + (", ".join(v.value for v in doc.auth_methods) or "NOT_APPLICABLE"),
            "인가": "역할과 리소스 소유권을 서버 측에서 확인하며 기본 거부 정책을 사용한다.",
            "입력값 검증": "텍스트·경로·URL·파일의 타입, 크기, 길이와 허용 형식을 경계에서 검증한다.",
            "암호화": "전송 구간 TLS와 검증된 저장 암호화를 사용하며 키는 코드·문서와 분리한다.",
            "개인정보 생명주기": "수집 목적·최소 항목·보존 기한·다운로드·삭제 흐름을 DATA/SEC ID와 연결한다.",
            "로그·비밀정보": "토큰·비밀번호·개인정보를 기록하지 않고 식별자는 필요한 경우 마스킹한다.",
            "외부 서비스·공급망": "의존성 lock과 검증을 유지하고 외부 서비스 장애·침해 시 차단·복구 경로를 둔다.",
            "OWASP ASVS 매핑": "MVP 위험에 해당하는 인증·접근통제·입력 검증·파일 처리 항목을 SEC/TEST-SEC ID에 매핑한다.",
            "보안 테스트": "TEST-SEC 시나리오로 인증 실패, 권한 우회, 악성·경계 입력과 정보 노출을 검증한다.",
            "사고 대응": "탐지 → 접근 차단 → 증거 보존 → 영향 평가 → 통지 판단 → 복구 → 사후 조치 순서다.",
            "잔여 위험·승인": "잔여 위험은 영향·완화·담당자·재검토 시점과 함께 Security Owner가 승인한다.",
        }

    def _migration(self, draft: SpecDraft) -> dict[str, str]:
        return {
            "변경 목적": f"기존 데이터 변경이 {draft.user_request} 구현에 필요하므로 DATA 요구와 연결한다.",
            "대상 데이터": draft.intake.get("data_and_rules")
            or "변경 대상 DB·파일·사용자 데이터 목록을 실행 전 확정한다.",
            "기존·신규 스키마": "필드별 기존 타입·제약·신규 타입·기본값·호환 기간을 표로 확정한다.",
            "데이터 변환 규칙": "누락·중복·잘못된 값은 별도 오류 목록으로 격리하고 원본을 수정하지 않는다.",
            "사전 백업": "변경 전 snapshot과 checksum을 만들고 암호화·보존 기간·복구 책임자를 기록한다.",
            "마이그레이션 명령": "NOT RUN — dry-run과 승인된 실제 명령을 구분해 실행 기록에 남긴다.",
            "멱등성과 재실행": "처리 ID와 완료 marker로 중복 실행을 방지하고 중간 실패 지점부터 안전하게 재개한다.",
            "단계별 검증": "전후 레코드 수, 필수값, 합계, 중복과 표본 데이터를 비교한다.",
            "중단 조건": "데이터 손실·중복, 허용 불일치율 초과, 예상 시간 초과 시 중단한다.",
            "롤백": "쓰기 중단 → 이전 코드 → 백업 복원 → 정합성 검증 → 서비스 재개 순서다.",
            "성능·소요 시간": "대상 수와 처리량을 dry-run으로 측정해 점검 시간과 서비스 영향을 확정한다.",
            "승인자·실행자": "Data Owner, Release Owner, 실행자를 분리하며 현재 UNASSIGNED이면 실행하지 않는다.",
            "실행 결과": "상태: NOT RUN — 실제 시작·종료 시각, 처리 수, 오류와 재처리 결과가 없다.",
            "복구 확인": "상태: NOT RUN — 백업 복구 후 핵심 조회·쓰기와 표본 정합성 검증 증거가 필요하다.",
        }

    @staticmethod
    def _fallback(section: str) -> str:
        return (
            f"{section}의 적용 범위, 결정 근거, 검증 기준과 책임자를 구조화 계약에 따라 기록한다."
        )

    @staticmethod
    def _bullets(values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values)

    @staticmethod
    def _flows(draft: SpecDraft) -> str:
        if draft.design_contract and draft.design_contract.user_flows:
            return "\n".join(
                f"- **{flow.name}**: {' → '.join(flow.steps)}"
                + (f"; 예외: {', '.join(flow.exception_paths)}" if flow.exception_paths else "")
                for flow in draft.design_contract.user_flows
            )
        return draft.intake.get("core_workflows") or "요청 → 입력 검증 → 처리 → 결과 확인"

    @staticmethod
    def _errors(draft: SpecDraft) -> str:
        if draft.design_contract and draft.design_contract.error_states:
            return "\n".join(
                f"- {item.trigger}: {item.user_message}; 복구={item.recovery}"
                for item in draft.design_contract.error_states
            )
        return (
            draft.intake.get("failure_behavior") or "입력을 보존하고 원인과 재시도 방법을 표시한다."
        )

    @staticmethod
    def _data_security(draft: SpecDraft) -> str:
        doc = draft.documentation
        return (
            f"- 저장소: {doc.storage_need.value} ({', '.join(v.value for v in doc.storage_types) or '없음'})\n"
            f"- 인증: {', '.join(v.value for v in doc.auth_capabilities)}\n"
            f"- 개인정보: {', '.join(v.value for v in doc.personal_data_types)}\n"
            f"- 추가 위험: {', '.join(v.value for v in doc.other_risks)}"
        )

    @staticmethod
    def _recommended_decisions(draft: SpecDraft) -> str:
        return "\n".join(
            f"- `{item.field}` = **{item.value}** ({item.source}, confidence={item.confidence}) — {item.reason}"
            for item in draft.recommended_decisions
        )

    @staticmethod
    def _unresolved_decisions(draft: SpecDraft) -> str:
        if draft.design_contract is None:
            return ""
        return "\n".join(
            f"- {item.topic}: {item.reason}; 영향={item.impact}; 담당={item.owner or 'UNASSIGNED'}; 기한={item.due_date or 'UNSET'}"
            for item in draft.design_contract.open_decisions
            if item.status == "open"
        )

    @staticmethod
    def _commands(draft: SpecDraft) -> tuple[str, str]:
        values = " ".join(draft.tech_stack.values()).lower()
        if "flutter" in values:
            return (
                "- 설치: `flutter pub get`\n- 실행: `flutter run`",
                "- 포맷: `dart format --output=none --set-exit-if-changed .`\n- 분석: `flutter analyze`\n- 테스트: `flutter test`\n- 빌드: `flutter build web`",
            )
        if any(item in values for item in ("next", "react", "node")):
            return (
                "- 설치: `npm ci`\n- 실행: `npm run dev`",
                "- 린트: `npm run lint`\n- 타입 검사: `npm run typecheck`\n- 테스트: `npm test`\n- 빌드: `npm run build`",
            )
        return (
            "- 설치: `uv sync`\n- 실행: `uv run python -m app`",
            "- 린트: `uv run ruff check`\n- 포맷: `uv run black --check .`\n- 타입 검사: `uv run mypy .`\n- 테스트: `uv run pytest -q`",
        )

    @staticmethod
    def _ac_ids(draft: SpecDraft, requirement_id: str) -> list[str]:
        ids: list[str] = []
        index = 1
        for requirement in draft.requirements:
            for _ in requirement.acceptance_criteria:
                if requirement.id == requirement_id:
                    ids.append(f"AC-{index:03d}")
                index += 1
        return ids

    def _all_ac_for_refs(self, draft: SpecDraft, refs: list[str]) -> list[str]:
        return [ac for ref in refs for ac in self._ac_ids(draft, ref)]
