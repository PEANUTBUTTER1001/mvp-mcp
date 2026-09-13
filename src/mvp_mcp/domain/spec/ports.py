"""도메인이 의존하는 외부 협력자(Port) 인터페이스.

Domain 은 시계/저장소를 직접 알지 못한다. UseCase 는 여기 정의된 ``Protocol`` 에만
의존하고, 실제 구현체는 ``data`` 레이어에 두며 ``main.py``(Composition Root)에서
주입한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .candidate_package_model import CandidatePackageSource, ManagedPackageStatus
from .documentation_model import (
    DocumentationApplyResult,
    DocumentationPreview,
    RenderedDocumentationPackage,
)
from .model import SpecDraft


class Clock(Protocol):
    """현재 시각을 제공하는 시계(비결정성 격리·테스트 고정용 Port)."""

    def now(self) -> datetime:
        """현재 시각을 반환한다."""
        ...


class CandidatePackageWorkspace(Protocol):
    """서버가 발급한 Run 전용 candidate workspace I/O Port.

    같은 ``run_id``에는 재시작 뒤에도 동일한 canonical root 문자열을 반환한다. Domain은
    이 값을 파일 경로로 해석하지 않고, Port가 발급한 opaque workspace 식별자로만 비교한다.
    """

    def ensure_workspace(self, run_id: str) -> str: ...

    def read(self, run_id: str, candidate_root: str) -> CandidatePackageSource: ...


class GuidePackageRenderer(Protocol):
    """검증된 구조화 계약을 표준 문서 패키지로 렌더링한다."""

    def render(self, draft: SpecDraft) -> RenderedDocumentationPackage: ...


class RepositoryDocumentationExporter(Protocol):
    """렌더링 패키지의 preview와 승인된 apply를 수행한다."""

    def preview(
        self, spec_id: str, project_root: str, package: RenderedDocumentationPackage
    ) -> DocumentationPreview: ...

    def apply(
        self,
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> DocumentationApplyResult: ...

    def status(self, project_root: str) -> ManagedPackageStatus: ...
