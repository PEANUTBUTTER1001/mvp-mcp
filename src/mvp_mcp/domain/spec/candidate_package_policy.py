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
from .palette import contrast_ratio, normalize_hex

_COMMON_DOCUMENTS = {"REQUIREMENTS.md", "ARCHITECTURE.md", "AGENTS.md"}
_MVP_DOCUMENTS = {
    "IMPLEMENTATION_PLAN.md",
    "TEST_PLAN.md",
    "RELEASE_RUNBOOK.md",
}
_OPTIONAL_DOCUMENTS = {"SECURITY_PRIVACY.md", "MIGRATION_PLAN.md"}
_PROTOTYPE_DOCUMENTS = {"DELIVERY_CHECKLIST.md"}
_ALLOWED_AUXILIARY_PATHS = {
    "api/openapi.yaml",
    "prototype/index.html",
    "prototype/REVIEW.md",
    "docs/MVPDESIGN.md",
    "docs/design-tokens.json",
}
_TECH_STACK_HEADERS = ("분류", "기술·버전", "역할", "근거 상태", "결정·근거")
_EVIDENCE_STATUSES = {"CONFIRMED", "DETECTED", "RECOMMENDED", "UNRESOLVED"}
_DIRECTORY_ACTIONS = {"KEEP", "NEW", "MODIFY", "REMOVE", "OPTIONAL"}
_DESIGN_CORE_SECTIONS = (
    "디자인 결정 요약",
    "경험 원칙",
    "플랫폼과 인터랙션 문법",
    "레이아웃 전략",
    "컬러 시스템",
    "컴포넌트 사용 규칙",
    "화면별 설계 브리프",
    "AI식 디자인 방지 규칙",
    "프로토타입 범위와 수용 기준",
    "구현 준수 규칙",
)
_TOKEN_THEME_KEYS = {
    "primary",
    "on_primary",
    "primary_container",
    "on_primary_container",
    "surface",
    "surface_muted",
    "surface_raised",
    "text_primary",
    "text_secondary",
    "outline",
    "outline_strong",
    "success",
    "success_container",
    "warning",
    "warning_container",
    "error",
    "error_container",
    "info",
    "info_container",
    "disabled_surface",
    "disabled_content",
    "disabled_outline",
    "focus_ring",
    "primary_hover",
    "primary_pressed",
    "primary_selected",
}
_TOKEN_V3_THEME_KEYS = _TOKEN_THEME_KEYS | {"on_success", "on_warning", "on_error", "on_info"}
_TOKEN_CONTRAST_PAIRS = (
    ("primary", "on_primary"),
    ("primary_container", "on_primary_container"),
    ("surface", "text_primary"),
    ("surface", "text_secondary"),
    ("success", "on_success"),
    ("warning", "on_warning"),
    ("error", "on_error"),
    ("info", "on_info"),
)


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
    _validate_design_artifacts(source.files, issues)

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
            design_hash=_design_hash_from(source.files),
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


def _design_hash_from(files: dict[str, str]) -> str | None:
    tokens = files.get("docs/design-tokens.json")
    if tokens is None:
        return None
    try:
        value = json.loads(tokens)
    except json.JSONDecodeError:
        return None
    design_hash = value.get("design_hash") if isinstance(value, dict) else None
    return (
        design_hash
        if isinstance(design_hash, str) and re.fullmatch(r"[a-f0-9]{64}", design_hash)
        else None
    )


def _validate_design_artifacts(files: dict[str, str], issues: list[str]) -> None:
    design_paths = {
        "docs/MVPDESIGN.md",
        "docs/design-tokens.json",
        "prototype/index.html",
        "prototype/REVIEW.md",
    }
    present = design_paths.intersection(files)
    if not present:
        return
    missing = sorted(design_paths - set(files))
    if missing:
        issues.append("디자인 산출물이 함께 생성되지 않았습니다: " + ", ".join(missing))
        return
    document = files["docs/MVPDESIGN.md"]
    required_sections = [f"## {index}." for index in range(1, 15)]
    if any(section not in document for section in required_sections):
        issues.append("MVPDESIGN.md에는 1~14절이 모두 필요합니다.")
    for index, title in enumerate(_DESIGN_CORE_SECTIONS, start=1):
        if f"## {index}. {title}" not in document:
            issues.append(f"MVPDESIGN.md {index}절의 핵심 표준 제목이 필요합니다: {title}")
    try:
        tokens = json.loads(files["docs/design-tokens.json"])
    except json.JSONDecodeError:
        issues.append("design-tokens.json은 유효한 JSON이어야 합니다.")
        return
    design_hash = tokens.get("design_hash") if isinstance(tokens, dict) else None
    if not isinstance(design_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", design_hash):
        issues.append("design-tokens.json에는 design_hash가 필요합니다.")
        return
    version = tokens.get("version")
    if version not in {2, 3}:
        issues.append(
            "design-tokens.json은 지원되는 version 2 또는 3 디자인 token 계약이어야 합니다."
        )
    color = tokens.get("color")
    if not isinstance(color, dict):
        issues.append("design-tokens.json에는 color theme 계약이 필요합니다.")
    else:
        for theme in ("light", "dark", "high_contrast"):
            values = color.get(theme)
            if not isinstance(values, dict):
                issues.append(f"design-tokens.json에 {theme} theme이 필요합니다.")
                continue
            required_roles = _TOKEN_V3_THEME_KEYS if version == 3 else _TOKEN_THEME_KEYS
            missing_roles = sorted(required_roles - set(values))
            if missing_roles:
                issues.append(
                    f"design-tokens.json의 {theme} theme 역할이 누락되었습니다: "
                    + ", ".join(missing_roles)
                )
            if version == 3:
                _validate_theme_contrast(theme, values, issues)
    if version == 3:
        _validate_v3_palette_source(tokens, issues)
    prototype = files["prototype/index.html"]
    if re.search(r"<[^>]+\sstyle\s*=", prototype, flags=re.IGNORECASE):
        issues.append("prototype/index.html에는 style= 인라인 속성을 사용할 수 없습니다.")
    if (
        "var(--brand)" not in prototype
        or 'data-theme="high_contrast"' not in prototype
        or "aria-errormessage=" not in prototype
    ):
        issues.append(
            "prototype/index.html은 semantic token·고대비 theme·오류 대상 연결을 사용해야 합니다."
        )
    if (
        design_hash not in document
        or design_hash not in prototype
        or design_hash not in files["prototype/REVIEW.md"]
    ):
        issues.append("MVPDESIGN, tokens, prototype, REVIEW의 design_hash가 일치해야 합니다.")


def _validate_v3_palette_source(tokens: dict[object, object], issues: list[str]) -> None:
    source = tokens.get("palette_source")
    if not isinstance(source, dict):
        issues.append("version 3 design-tokens.json에는 palette_source가 필요합니다.")
        return
    brand_seed = source.get("brand_seed")
    try:
        valid_seed = isinstance(brand_seed, str) and normalize_hex(brand_seed) == brand_seed.upper()
    except ValueError:
        valid_seed = False
    if not valid_seed:
        issues.append("palette_source.brand_seed는 #RRGGBB 형식이어야 합니다.")
    if source.get("generator") != "oklch-v1":
        issues.append("palette_source.generator는 oklch-v1이어야 합니다.")
    if not isinstance(source.get("palette_intent"), str):
        issues.append("palette_source.palette_intent가 필요합니다.")
    accessibility = tokens.get("accessibility")
    if not isinstance(accessibility, dict):
        issues.append("version 3 design-tokens.json에는 accessibility 계약이 필요합니다.")
        return
    if accessibility.get("normal_text_minimum_ratio") != 4.5:
        issues.append("accessibility.normal_text_minimum_ratio는 4.5여야 합니다.")
    if accessibility.get("high_contrast_text_minimum_ratio") != 7.0:
        issues.append("accessibility.high_contrast_text_minimum_ratio는 7.0이어야 합니다.")


def _validate_theme_contrast(theme: str, values: dict[object, object], issues: list[str]) -> None:
    minimum = 7.0 if theme == "high_contrast" else 4.5
    for background, foreground in _TOKEN_CONTRAST_PAIRS:
        background_value, foreground_value = values.get(background), values.get(foreground)
        if not isinstance(background_value, str) or not isinstance(foreground_value, str):
            continue
        try:
            ratio = contrast_ratio(background_value, foreground_value)
        except ValueError:
            issues.append(
                f"design-tokens.json의 {theme} {background}/{foreground} 값은 Hex여야 합니다."
            )
            continue
        if ratio < minimum:
            issues.append(
                f"design-tokens.json의 {theme} {background}/{foreground} 대비 {ratio:.2f}:1이 "
                f"최소 {minimum:.1f}:1보다 낮습니다."
            )


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
