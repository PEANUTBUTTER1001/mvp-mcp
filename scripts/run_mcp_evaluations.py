"""문서 워크플로 평가 정의와 공개 MCP Tool 계약을 smoke-test한다."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from mvp_mcp.domain.spec.documentation_model import DocumentProfile
from mvp_mcp.main import build

REQUIRED_TOOLS = {
    "documentation_collect_intake",
    "documentation_register_requirements",
    "documentation_register_architecture",
    "documentation_register_delivery",
    "documentation_validate",
    "documentation_preview",
    "documentation_apply",
}


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "evaluations/documentation_workflows.xml")
    root = ET.parse(path).getroot()
    cases = root.findall("case")
    expected = int(root.attrib["expected-count"])
    registered = {tool.name for tool in build()._tool_manager.list_tools()}
    failures: list[str] = []
    if len(cases) != expected:
        failures.append(f"평가 개수: expected={expected}, actual={len(cases)}")
    if missing := REQUIRED_TOOLS - registered:
        failures.append(f"등록되지 않은 Tool: {', '.join(sorted(missing))}")
    seen: set[str] = set()
    valid_profiles = {item.value for item in DocumentProfile}
    for case in cases:
        case_id = case.attrib.get("id", "")
        if not case_id or case_id in seen:
            failures.append(f"평가 ID 누락/중복: {case_id or '(empty)'}")
        seen.add(case_id)
        if case.attrib.get("profile") not in valid_profiles:
            failures.append(f"{case_id}: 알 수 없는 profile")
        if not case.attrib.get("name", "").strip():
            failures.append(f"{case_id}: name 누락")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    for case in cases:
        print(f"PASS {case.attrib['id']} {case.attrib['name']}")
    print(f"RESULT {len(cases)}/{expected} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
