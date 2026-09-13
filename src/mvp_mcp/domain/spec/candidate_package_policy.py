"""후보 Markdown package의 결정적 구조·추적성 최소 규칙."""

from __future__ import annotations

import hashlib
import json
import re

from .candidate_package_model import (
    CandidatePackageInspection,
    CandidatePackageSource,
    CandidatePackageValidationResult,
)
from .documentation_model import DocumentProfile, RenderedDocumentationPackage
from .guide_contract import DOCUMENT_CONTRACTS

_COMMON_DOCUMENTS = {"REQUIREMENTS.md", "ARCHITECTURE.md", "AGENTS.md"}
_MVP_DOCUMENTS = {
    "IMPLEMENTATION_PLAN.md",
    "TEST_PLAN.md",
    "RELEASE_RUNBOOK.md",
}
_OPTIONAL_DOCUMENTS = {"SECURITY_PRIVACY.md", "MIGRATION_PLAN.md"}
_PROTOTYPE_DOCUMENTS = {"DELIVERY_CHECKLIST.md"}
_ALLOWED_AUXILIARY_PATHS = {"api/openapi.yaml", "prototype/index.html"}
_TECH_STACK_HEADERS = ("분류", "기술·버전", "역할", "근거 상태", "결정·근거")
_EVIDENCE_STATUSES = {"CONFIRMED", "DETECTED", "RECOMMENDED", "UNRESOLVED"}
_DIRECTORY_ACTIONS = {"KEEP", "NEW", "MODIFY", "REMOVE", "OPTIONAL"}


def inspect_candidate_package(
    source: CandidatePackageSource,
    *,
    run_id: str,
    run_version: int,
) -> CandidatePackageInspection:
    """후보 파일을 한 번만 해석해 결과와 exporter 입력을 만든다.

    revision은 profile 추론 이전의 모든 파일 본문 hash에 결속한다. 따라서 profile을 바꾸거나
    본문·경로를 한 글자라도 바꾸면 validate/preview 사이의 stale 감지가 가능하다.
    """

    revision = candidate_revision(source.files)
    issues: list[str] = []
    warnings: list[str] = []
    _validate_path_set(source.files, issues)
    profile = _infer_profile(source.files, issues)
    if profile is not None:
        _validate_expected_documents(source.files, profile, issues, warnings)
    else:
        issues.append("문서 집합에서 지원되는 문서 프로파일을 판별할 수 없습니다.")
    _validate_auxiliary_files(source.files, issues)

    valid = not issues and profile is not None
    validation = CandidatePackageValidationResult(
        run_id=run_id,
        run_version=run_version,
        candidate_root=source.candidate_root,
        candidate_revision=revision,
        profile=profile,
        file_count=len(source.files),
        valid=valid,
        issues=issues,
        warnings=warnings,
        next_action=(
            "documentation_preview_package에 동일 run_id, run_version, "
            "candidate_revision을 전달하세요."
            if valid
            else (
                "candidate_root 안의 문서를 보완한 뒤 documentation_package_status로 "
                "새 revision을 확인하세요."
            )
        ),
    )
    package = (
        RenderedDocumentationPackage(
            profile=profile,
            files=dict(source.files),
            source_contract_sha256=revision,
        )
        if valid and profile is not None
        else None
    )
    return CandidatePackageInspection(validation=validation, package=package)


def candidate_revision(files: dict[str, str]) -> str:
    """파일 경로와 UTF-8 본문 hash를 canonical JSON으로 묶은 opaque revision."""

    snapshot = {
        path: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for path, content in sorted(files.items())
    }
    encoded = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_path_set(files: dict[str, str], issues: list[str]) -> None:
    if not files:
        issues.append("candidate package가 비어 있습니다.")
        return
    allowed = {"README.md", "AGENTS.md", *_ALLOWED_AUXILIARY_PATHS}
    allowed.update(f"docs/{name}" for name in DOCUMENT_CONTRACTS)
    unexpected = sorted(set(files) - allowed)
    if unexpected:
        issues.append("허용되지 않은 candidate 경로가 있습니다: " + ", ".join(unexpected))
    for path, content in files.items():
        if not content.strip():
            issues.append(f"비어 있는 candidate 파일입니다: {path}")


def _infer_profile(files: dict[str, str], issues: list[str]) -> DocumentProfile | None:
    documents = {
        path.removeprefix("docs/")
        for path in files
        if path.startswith("docs/") and path.removeprefix("docs/") in DOCUMENT_CONTRACTS
    }
    has_prototype = bool(documents & _PROTOTYPE_DOCUMENTS)
    has_mvp = bool(documents & _MVP_DOCUMENTS)
    if has_prototype and has_mvp:
        issues.append("PROTOTYPE_4와 기본 6문서 프로파일 문서를 함께 둘 수 없습니다.")
        return None
    if has_prototype:
        if documents & _OPTIONAL_DOCUMENTS:
            issues.append("PROTOTYPE_4에는 SECURITY_PRIVACY/MIGRATION 확장 문서를 둘 수 없습니다.")
            return None
        return DocumentProfile.PROTOTYPE_4
    if "SECURITY_PRIVACY.md" in documents and "MIGRATION_PLAN.md" in documents:
        return DocumentProfile.MVP_6_FULL_RISK
    if "SECURITY_PRIVACY.md" in documents:
        return DocumentProfile.MVP_6_SECURITY
    if "MIGRATION_PLAN.md" in documents:
        return DocumentProfile.MVP_6_MIGRATION
    return DocumentProfile.MVP_6


def _validate_expected_documents(
    files: dict[str, str],
    profile: DocumentProfile,
    issues: list[str],
    warnings: list[str],
) -> None:
    expected = _expected_document_names(profile)
    actual = {
        "AGENTS.md" if path == "AGENTS.md" else path.removeprefix("docs/")
        for path in files
        if path == "AGENTS.md" or path.startswith("docs/")
    }
    missing = sorted(expected - actual)
    if missing:
        issues.append("필수 문서가 없습니다: " + ", ".join(missing))
    extra = sorted((actual - expected) & set(DOCUMENT_CONTRACTS))
    if extra:
        issues.append("선택한 프로파일에 맞지 않는 문서가 있습니다: " + ", ".join(extra))
    if "README.md" not in files:
        issues.append("필수 탐색 문서 README.md가 없습니다.")
    elif not _has_heading(files["README.md"], "#"):
        issues.append("README.md는 최상위 # 제목으로 시작해야 합니다.")

    for name in sorted(expected):
        path = "AGENTS.md" if name == "AGENTS.md" else f"docs/{name}"
        content = files.get(path)
        if content is None:
            continue
        _validate_document_content(name, content, issues, warnings)


def _expected_document_names(profile: DocumentProfile) -> set[str]:
    if profile is DocumentProfile.PROTOTYPE_4:
        return _COMMON_DOCUMENTS | _PROTOTYPE_DOCUMENTS
    names = _COMMON_DOCUMENTS | _MVP_DOCUMENTS
    if profile in {DocumentProfile.MVP_6_SECURITY, DocumentProfile.MVP_6_FULL_RISK}:
        names.add("SECURITY_PRIVACY.md")
    if profile in {DocumentProfile.MVP_6_MIGRATION, DocumentProfile.MVP_6_FULL_RISK}:
        names.add("MIGRATION_PLAN.md")
    return names


def _validate_document_content(
    name: str,
    content: str,
    issues: list[str],
    warnings: list[str],
) -> None:
    if not _has_heading(content, f"# {name}"):
        issues.append(f"{name}에 최상위 문서 제목 '# {name}'이 없습니다.")
    contract = DOCUMENT_CONTRACTS[name]
    missing_sections = [
        section for section in contract.sections if not _has_section_heading(content, section)
    ]
    if missing_sections:
        issues.append(f"{name}에 계약 섹션이 없습니다: " + ", ".join(missing_sections))
    _validate_traceability_markers(name, content, issues)
    if name == "ARCHITECTURE.md":
        _validate_architecture_ssot(content, issues)
    if name == "IMPLEMENTATION_PLAN.md":
        _validate_implementation_plan_reference(content, issues)


def _validate_traceability_markers(name: str, content: str, issues: list[str]) -> None:
    markers = {
        "REQUIREMENTS.md": ("FR-", "AC-"),
        "IMPLEMENTATION_PLAN.md": ("TASK-",),
        "TEST_PLAN.md": ("TEST-",),
        "RELEASE_RUNBOOK.md": ("REL-",),
        "DELIVERY_CHECKLIST.md": ("TASK-", "TEST-"),
    }
    missing = [marker for marker in markers.get(name, ()) if marker not in content]
    if missing:
        issues.append(f"{name}에 추적성 식별자가 없습니다: " + ", ".join(missing))


def _validate_auxiliary_files(files: dict[str, str], issues: list[str]) -> None:
    openapi = files.get("api/openapi.yaml")
    if openapi is not None and "openapi:" not in openapi:
        issues.append("api/openapi.yaml에는 openapi: 선언이 필요합니다.")
    prototype = files.get("prototype/index.html")
    if prototype is not None and "<html" not in prototype.lower():
        issues.append("prototype/index.html에는 HTML 문서 루트가 필요합니다.")


def _validate_architecture_ssot(content: str, issues: list[str]) -> None:
    _validate_technology_stack(_section_body(content, "기술 스택"), issues)
    _validate_directory_structure(_section_body(content, "디렉터리 구조"), issues)


def _validate_technology_stack(section: str | None, issues: list[str]) -> None:
    if section is None:
        return
    table_lines = section.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(table_lines)
            if _table_cells(line) == list(_TECH_STACK_HEADERS)
        ),
        None,
    )
    if header_index is None:
        issues.append("ARCHITECTURE.md의 기술 스택에는 표준 5열 Markdown 표가 필요합니다.")
        return

    data_rows: list[list[str]] = []
    for line in table_lines[header_index + 1 :]:
        cells = _table_cells(line)
        if cells is None:
            if data_rows:
                break
            continue
        if _is_table_divider(cells):
            continue
        data_rows.append(cells)
    if not data_rows:
        issues.append("ARCHITECTURE.md의 기술 스택 표에는 하나 이상의 기술 행이 필요합니다.")
        return
    for row in data_rows:
        if len(row) != len(_TECH_STACK_HEADERS) or any(not cell for cell in row):
            issues.append("ARCHITECTURE.md의 기술 스택 표 행은 비어 있지 않은 5열이어야 합니다.")
            continue
        if row[3] not in _EVIDENCE_STATUSES:
            issues.append("ARCHITECTURE.md의 기술 스택 근거 상태가 허용되지 않습니다: " + row[3])


def _validate_directory_structure(section: str | None, issues: list[str]) -> None:
    if section is None:
        return
    lines = section.splitlines()
    fence_start = next(
        (index for index, line in enumerate(lines) if line.strip() in {"```text", "```bash"}),
        None,
    )
    if fence_start is None:
        issues.append("ARCHITECTURE.md의 디렉터리 구조에는 text 또는 bash 코드 펜스가 필요합니다.")
        return
    fence_end = next(
        (index for index in range(fence_start + 1, len(lines)) if lines[index].strip() == "```"),
        None,
    )
    if fence_end is None:
        issues.append("ARCHITECTURE.md의 디렉터리 구조 코드 펜스가 닫히지 않았습니다.")
        return

    entries = [line for line in lines[fence_start + 1 : fence_end] if line.strip()]
    if not entries:
        issues.append("ARCHITECTURE.md의 디렉터리 구조에는 하나 이상의 경로가 필요합니다.")
        return
    for entry in entries:
        match = re.search(r"#\s*\[([A-Z]+)]\s+(.+)$", entry)
        path = entry.split("#", maxsplit=1)[0].strip(" │├└─|-\t")
        if not path or match is None:
            issues.append(
                "ARCHITECTURE.md의 디렉터리 경로에는 "
                "'# [KEEP|NEW|MODIFY|REMOVE|OPTIONAL] 설명'이 필요합니다."
            )
            continue
        if match.group(1) not in _DIRECTORY_ACTIONS:
            issues.append("ARCHITECTURE.md의 디렉터리 라벨이 허용되지 않습니다: " + match.group(1))


def _validate_implementation_plan_reference(content: str, issues: list[str]) -> None:
    section = _section_body(content, "변경 파일")
    if section is None:
        return
    if "ARCHITECTURE.md" not in section or "디렉터리 구조" not in section:
        issues.append(
            "IMPLEMENTATION_PLAN.md의 변경 파일은 ARCHITECTURE.md의 "
            "디렉터리 구조 SSOT를 참조해야 합니다."
        )


def _has_heading(content: str, heading: str) -> bool:
    return content.lstrip().startswith(heading)


def _has_section_heading(content: str, section: str) -> bool:
    return any(line.lstrip().startswith("##") and section in line for line in content.splitlines())


def _section_body(content: str, section: str) -> str | None:
    lines = content.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lstrip().startswith("##") and section in line
        ),
        None,
    )
    if start is None:
        return None
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].lstrip().startswith("##")),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped.strip("|"))]


def _is_table_divider(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)
