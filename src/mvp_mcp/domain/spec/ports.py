"""도메인이 의존하는 외부 협력자(Port) 인터페이스.

Domain 은 시계/저장소를 직접 알지 못한다. UseCase 는 여기 정의된 ``Protocol`` 에만
의존하고, 실제 구현체는 ``data`` 레이어에 두며 ``main.py``(Composition Root)에서
주입한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .documentation_model import (
    DocumentationApplyResult,
    DocumentationPreview,
    RenderedDocumentationPackage,
)
from .model import Question, SpecDraft, WebQuestionAnswer, WebSurveyAnswer
from .survey import SurveySession


class Clock(Protocol):
    """현재 시각을 제공하는 시계(비결정성 격리·테스트 고정용 Port)."""

    def now(self) -> datetime:
        """현재 시각을 반환한다."""
        ...


class WebQuestionForm(Protocol):
    """브라우저 기반 질문 화면. 응답이 올 때까지 한 질문을 대기한다."""

    def ask(self, question: Question) -> WebQuestionAnswer:
        """질문을 표시하고 사용자가 확정한 답변을 반환한다."""
        ...


class WebSurveyForm(Protocol):
    """한 페이지 요구사항 설문을 표시하고 제출값을 기다린다."""

    def ask(self, user_request: str) -> WebSurveyAnswer:
        """초기 요청을 미리 채운 설문을 표시하고 제출값을 반환한다."""
        ...


class SurveySessionRepository(Protocol):
    """비차단 웹 설문 세션을 저장·조회한다."""

    def save(self, session: SurveySession) -> None: ...

    def find_by_id(self, session_id: str) -> SurveySession | None: ...


class WebSurveySessionForm(Protocol):
    """세션 식별자를 포함한 Wizard URL을 열고 즉시 반환한다."""

    def open(self, session_id: str, user_request: str) -> str: ...


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
