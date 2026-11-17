"""프로젝트 루트 AGENTS.md에 구현 Tool 사용 규칙 블록을 사용자 승인 아래 덧붙인다.

구현 AI는 세션을 시작할 때 루트 AGENTS.md를 자동으로 읽는다. 이 모듈은 사람이 쓴 내용은
그대로 두고, 표식으로 감싼 mvp-mcp 관리 블록 하나만 추가·갱신한다. 미리보기 해시와 현재
파일이 다르면 쓰지 않는다.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel

from mvp_mcp.core.exceptions import PipelineError

from .adaptive_wizard_model import AdaptiveRunStatus
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .ports import ProjectRootTextFile

AGENTS_FILE = "AGENTS.md"
BLOCK_BEGIN = "<!-- mvp-mcp:begin -->"
BLOCK_END = "<!-- mvp-mcp:end -->"


class RootAgentsLinkResult(BaseModel):
    run_id: str
    mode: Literal["preview", "apply"]
    action: Literal["CREATE_FILE", "APPEND_BLOCK", "UPDATE_BLOCK", "UNCHANGED"]
    status: Literal["PREVIEW", "APPLIED", "UNCHANGED", "CONFLICT"]
    path: str = AGENTS_FILE
    current_sha256: str | None
    block: str
    next_instruction: str


def link_block(run_id: str, spec_id: str) -> str:
    return "\n".join(
        [
            BLOCK_BEGIN,
            "## MVP 명세 연결 (mvp-mcp)",
            "",
            f"- 문서 패키지: `.mvpmcp/{spec_id}/` · run_id: `{run_id}`",
            f'- 작업 시작 전 `implementation_next_task(run_id="{run_id}")`로 다음 TASK와 '
            "필요한 명세만 받는다. 전체 문서를 매번 읽지 않는다.",
            "- 연결 TEST를 실제로 실행한 뒤 `implementation_record_evidence`로 결과·명령·"
            "실행자를 기록한다.",
            "- 실행하지 않은 TEST는 NOT_RUN으로 두고 PASS로 쓰지 않는다.",
            BLOCK_END,
        ]
    )


def merged_content(current: str | None, block: str) -> tuple[str, str]:
    """(새 내용, 동작). 사람이 쓴 부분은 그대로 두고 관리 블록만 넣거나 바꾼다."""

    if current is None:
        return f"# AGENTS.md\n\n{block}\n", "CREATE_FILE"
    start = current.find(BLOCK_BEGIN)
    end = current.find(BLOCK_END, start + 1) if start >= 0 else -1
    if start >= 0 and end >= 0:
        updated = current[:start] + block + current[end + len(BLOCK_END) :]
        return updated, ("UNCHANGED" if updated == current else "UPDATE_BLOCK")
    if start >= 0 or BLOCK_END in current:
        raise PipelineError(
            "root_agents_link",
            "AGENTS.md의 mvp-mcp 표식이 짝이 맞지 않습니다.",
            "표식(begin/end)을 직접 정리한 뒤 다시 미리보기 하세요.",
        )
    separator = "" if current.endswith("\n\n") else ("\n" if current.endswith("\n") else "\n\n")
    return f"{current}{separator}{block}\n", "APPEND_BLOCK"


class LinkRootAgentsUseCase:
    """반영된 Run의 구현 규칙을 루트 AGENTS.md 관리 블록으로 미리보기·반영한다."""

    def __init__(self, runs: AdaptiveWizardRunRepository, files: ProjectRootTextFile) -> None:
        self._runs = runs
        self._files = files

    def __call__(
        self,
        run_id: str,
        mode: Literal["preview", "apply"],
        expected_current_sha256: str | None = None,
    ) -> RootAgentsLinkResult:
        run = self._runs.find_by_id(run_id)
        if run is None or run.spec_id is None:
            raise PipelineError(
                "root_agents_link",
                "문서 패키지가 있는 Run을 찾을 수 없습니다.",
                "documentation_* 흐름이 반환한 run_id를 사용하세요.",
            )
        if run.status is not AdaptiveRunStatus.APPLIED:
            raise PipelineError(
                "root_agents_link",
                f"NOT_READY: 문서 패키지가 아직 반영되지 않았습니다 ({run.status.value}).",
                "문서 패키지를 반영한 뒤 루트 AGENTS.md 연결을 미리보기 하세요.",
            )
        try:
            current = self._files.read(run.project_root, AGENTS_FILE)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise PipelineError(
                "root_agents_link",
                f"루트 AGENTS.md를 읽을 수 없습니다: {exc}",
                "파일 권한·인코딩(UTF-8)·symlink 여부를 확인하세요.",
            ) from exc
        current_hash = _sha256(current)
        block = link_block(run.id, run.spec_id)
        content, action = merged_content(current, block)
        if mode == "preview" or action == "UNCHANGED":
            return RootAgentsLinkResult(
                run_id=run.id,
                mode=mode,
                action=action,  # type: ignore[arg-type]
                status="UNCHANGED" if action == "UNCHANGED" else "PREVIEW",
                current_sha256=current_hash,
                block=block,
                next_instruction=(
                    "사용자에게 블록을 보여 주고 동의하면 같은 run_id로 mode='apply'와 "
                    "expected_current_sha256(이 응답의 current_sha256)을 보내세요. "
                    "동의하지 않으면 아무것도 하지 마세요."
                    if action != "UNCHANGED"
                    else "이미 같은 연결 블록이 있습니다."
                ),
            )
        if expected_current_sha256 != current_hash:
            return RootAgentsLinkResult(
                run_id=run.id,
                mode=mode,
                action=action,  # type: ignore[arg-type]
                status="CONFLICT",
                current_sha256=current_hash,
                block=block,
                next_instruction="미리보기 이후 AGENTS.md가 바뀌었습니다. 다시 미리보기 하세요.",
            )
        try:
            written = self._files.replace_if_unchanged(
                run.project_root, AGENTS_FILE, content, expected_current_sha256
            )
        except (OSError, ValueError) as exc:
            raise PipelineError(
                "root_agents_link",
                f"루트 AGENTS.md를 쓸 수 없습니다: {exc}",
                "파일 권한과 잠금 상태를 확인한 뒤 다시 미리보기 하세요.",
            ) from exc
        return RootAgentsLinkResult(
            run_id=run.id,
            mode=mode,
            action=action,  # type: ignore[arg-type]
            status="APPLIED" if written else "CONFLICT",
            current_sha256=_sha256(content) if written else current_hash,
            block=block,
            next_instruction=(
                "루트 AGENTS.md에 연결 블록을 넣었습니다. 커밋 여부는 사용자가 정합니다."
                if written
                else "쓰기 직전 AGENTS.md가 바뀌었습니다. 다시 미리보기 하세요."
            ),
        )


def _sha256(content: str | None) -> str | None:
    if content is None:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
