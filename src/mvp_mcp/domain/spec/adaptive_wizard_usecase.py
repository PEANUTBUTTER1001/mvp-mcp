"""client-native 2단계 Adaptive Wizard의 상태 전이 UseCase."""

from __future__ import annotations

from collections.abc import Mapping
from secrets import token_urlsafe

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.core.security import is_absolute_path

from .adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardQuestion,
    AdaptiveWizardRun,
    AdaptiveWizardSubmission,
    WritePolicy,
    make_submission,
)
from .adaptive_wizard_policy import intake_questions, validate_design_questions
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .documentation_model import ChangeType, DocumentationIntake
from .model import ProjectType, RecommendedDecision, SpecDraft
from .ports import CandidatePackageWorkspace, Clock
from .repository import SpecRepository, TemplateRepository
from .usecase import ScopeMvpUseCase


class StartAdaptiveWizardUseCase:
    """1차 질문 schema를 가진 영속 Run을 시작하거나 같은 Run을 반환한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._clock = clock

    def __call__(
        self,
        user_request: str,
        project_root: str,
        request_key: str,
        write_policy: WritePolicy | None = None,
    ) -> AdaptiveWizardRun:
        _validate_project_root(project_root)
        now = self._clock.now()
        initial = AdaptiveWizardRun(
            id=f"run-{token_urlsafe(18)}",
            request_key=request_key,
            user_request=user_request.strip(),
            project_root=project_root,
            requested_write_policy=write_policy,
            intake_questions=intake_questions(write_policy),
            created_at=now,
            updated_at=now,
        )
        run, _created = self._runs.create_or_get(initial)
        _assert_same_start_request(run, initial)
        return run


class OpenAdaptiveDesignWizardUseCase:
    """모델이 만든 3~7개 맞춤 질문 schema를 Run에 한 번만 연다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._clock = clock

    def __call__(self, run_id: str, questions: list[AdaptiveWizardQuestion]) -> AdaptiveWizardRun:
        run = _require_run(self._runs, run_id)
        questions = validate_design_questions(
            questions, {question.id for question in run.intake_questions}
        )
        if run.status in {
            AdaptiveRunStatus.DESIGN_SUBMITTED,
            AdaptiveRunStatus.DRAFT_READY,
            AdaptiveRunStatus.CANDIDATE_VALIDATED,
            AdaptiveRunStatus.PREVIEW_READY,
            AdaptiveRunStatus.CONFLICTED,
            AdaptiveRunStatus.APPLIED,
        }:
            _assert_same_questions(run.design_questions, questions)
            return run
        if run.status is AdaptiveRunStatus.INTAKE_SUBMITTED:
            opened = run.model_copy(
                update={
                    "status": AdaptiveRunStatus.DESIGN_OPEN,
                    "design_questions": questions,
                    "version": run.version + 1,
                    "updated_at": self._clock.now(),
                }
            )
            run = self._runs.save(opened, expected_version=run.version)
        elif run.status is AdaptiveRunStatus.DESIGN_OPEN:
            _assert_same_questions(run.design_questions, questions)
        else:
            raise PipelineError(
                "adaptive_wizard",
                f"2차 Wizard를 열 수 없는 상태입니다: {run.status.value}",
                "1차 Wizard 제출이 완료된 같은 run_id를 사용하세요.",
            )

        return run


class SubmitAdaptiveWizardAnswersUseCase:
    """클라이언트 native 질문 UI가 모은 한 단계 답변을 원자적으로 저장한다."""

    def __init__(self, runs: AdaptiveWizardRunRepository, clock: Clock) -> None:
        self._runs = runs
        self._clock = clock

    def __call__(self, run_id: str, phase: str, answers: dict[str, object]) -> AdaptiveWizardRun:
        run = _require_run(self._runs, run_id)
        if phase == "intake":
            return _record_intake_submission(
                self._runs,
                run,
                make_submission(
                    f"sub-{token_urlsafe(18)}",
                    run.intake_questions,
                    answers,
                    self._clock.now(),
                ),
                self._clock,
            )
        if phase == "design":
            return _record_design_submission(
                self._runs,
                run,
                make_submission(
                    f"sub-{token_urlsafe(18)}",
                    run.design_questions,
                    answers,
                    self._clock.now(),
                ),
                self._clock,
            )
        raise PipelineError(
            "adaptive_wizard",
            f"알 수 없는 Wizard 단계입니다: {phase}",
            "phase에는 intake 또는 design만 사용하세요.",
        )


class GetAdaptiveWizardRunUseCase:
    """새 Wizard를 만들지 않고 영속 Run snapshot만 조회한다."""

    def __init__(self, runs: AdaptiveWizardRunRepository) -> None:
        self._runs = runs

    def __call__(self, run_id: str) -> AdaptiveWizardRun:
        return _require_run(self._runs, run_id)


class CreateAdaptiveWizardDraftUseCase:
    """2차 제출 snapshot을 기존 검증·preview 흐름의 scoped draft로 연결한다.

    이 호환 계층은 새 설문 답변을 다시 사용자에게 묻지 않는다. 이후의 요구사항·설계·TASK/TEST
    등록과 기존 preview는 그대로 재사용하므로, 후보 생성 전에도 현재 서버의 안전한 문서 계약을
    유지할 수 있다.
    """

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        specs: SpecRepository,
        templates: TemplateRepository,
        scope: ScopeMvpUseCase,
        candidates: CandidatePackageWorkspace,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._specs = specs
        self._templates = templates
        self._scope = scope
        self._candidates = candidates
        self._clock = clock

    def __call__(self, run_id: str) -> AdaptiveWizardRun:
        run = _require_run(self._runs, run_id)
        if run.status in _PACKAGE_READY_STATUSES:
            run = self._ensure_candidate_workspace(run)
            spec_id = run.spec_id
            assert spec_id is not None
            if self._specs.find_by_id(spec_id) is None:
                self._persist_scoped_draft(run, spec_id)
            return run
        if run.status is not AdaptiveRunStatus.DESIGN_SUBMITTED:
            raise PipelineError(
                "adaptive_wizard",
                f"2차 Wizard를 완료하지 않은 상태입니다: {run.status.value}",
                "2차 설문 제출을 완료한 run_id를 사용하세요.",
            )
        if run.intake_submission is None or run.design_submission is None:
            raise PipelineError(
                "adaptive_wizard",
                "제출 snapshot을 찾을 수 없습니다.",
                "documentation_wizard_run_status로 run 상태를 확인하세요.",
            )

        spec_id = f"adaptive-{run.id}"
        scoped = self._persist_scoped_draft(run, spec_id)
        ready = run.model_copy(
            update={
                "status": AdaptiveRunStatus.DRAFT_READY,
                "spec_id": scoped.id,
                "candidate_root": self._candidates.ensure_workspace(run.id),
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        return self._runs.save(ready, expected_version=run.version)

    def _ensure_candidate_workspace(self, run: AdaptiveWizardRun) -> AdaptiveWizardRun:
        candidate_root = self._candidates.ensure_workspace(run.id)
        if run.candidate_root is not None:
            if run.candidate_root != candidate_root:
                raise PipelineError(
                    "candidate_package",
                    "Run의 candidate root가 서버가 발급한 경로와 다릅니다.",
                    "candidate_root를 변경하지 말고 새 Wizard run으로 다시 시작하세요.",
                )
            return run
        repaired = run.model_copy(
            update={
                "candidate_root": candidate_root,
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        return self._runs.save(repaired, expected_version=run.version)

    def _persist_scoped_draft(self, run: AdaptiveWizardRun, spec_id: str) -> SpecDraft:
        assert run.intake_submission is not None
        assert run.design_submission is not None
        intake = _string_answers(run.intake_submission.answers)
        design = _string_answers(run.design_submission.answers)
        project_type = _resolve_project_type(intake)
        template = self._templates.get(project_type)
        if template is None:
            raise PipelineError(
                "adaptive_wizard",
                f"지원하지 않는 산출물 유형입니다: {project_type.value}",
                "project_type을 etc로 선택하거나 지원 유형을 사용하세요.",
            )
        draft = SpecDraft(
            id=spec_id,
            project_type=project_type,
            user_request=run.user_request,
            project_root=run.project_root,
            answers=_seed_template_answers(template.required_fields, intake),
            intake={**intake, **{f"design_{key}": value for key, value in design.items()}},
            tech_stack=_resolve_tech_stack(template.default_stack, intake["tech_stack"]),
            recommended_decisions=_recommended_stack_decision(intake["tech_stack"]),
            documentation=DocumentationIntake(
                change_type=(
                    ChangeType.NEW
                    if intake.get("work_type") == "new_project"
                    else ChangeType.EXISTING
                )
            ),
            created_at=self._clock.now(),
        )
        self._specs.save(draft)
        return self._scope(spec_id, _requested_features(intake["mvp_scope"]))


def _record_intake_submission(
    runs: AdaptiveWizardRunRepository,
    run: AdaptiveWizardRun,
    submission: AdaptiveWizardSubmission,
    clock: Clock,
) -> AdaptiveWizardRun:
    if run.intake_submission is not None:
        _assert_same_submission(run.intake_submission, submission)
        return run
    if run.status is not AdaptiveRunStatus.INTAKE_OPEN:
        raise PipelineError(
            "adaptive_wizard",
            f"1차 제출을 기록할 수 없는 상태입니다: {run.status.value}",
            "run 상태를 조회한 뒤 재시도하세요.",
        )
    write_policy = run.requested_write_policy
    if write_policy is None:
        try:
            write_policy = WritePolicy(str(submission.answers["write_policy"]))
        except (KeyError, ValueError) as exc:
            raise PipelineError(
                "adaptive_wizard",
                "1차 Wizard의 파일 반영 정책이 올바르지 않습니다.",
                "write_policy를 선택한 뒤 설문을 다시 제출하세요.",
            ) from exc
    elif (
        submitted_policy := submission.answers.get("write_policy")
    ) is not None and submitted_policy != write_policy.value:
        raise PipelineError(
            "adaptive_wizard",
            "최초 요청의 파일 반영 정책과 다른 제출값은 사용할 수 없습니다.",
            "새 write_policy가 필요하면 새 request_key로 Wizard를 시작하세요.",
        )
    submitted = run.model_copy(
        update={
            "status": AdaptiveRunStatus.INTAKE_SUBMITTED,
            "write_policy": write_policy,
            "intake_submission": submission,
            "version": run.version + 1,
            "updated_at": clock.now(),
        }
    )
    return runs.save(submitted, expected_version=run.version)


def _record_design_submission(
    runs: AdaptiveWizardRunRepository,
    run: AdaptiveWizardRun,
    submission: AdaptiveWizardSubmission,
    clock: Clock,
) -> AdaptiveWizardRun:
    if run.design_submission is not None:
        _assert_same_submission(run.design_submission, submission)
        return run
    if run.status is not AdaptiveRunStatus.DESIGN_OPEN:
        raise PipelineError(
            "adaptive_wizard",
            f"2차 제출을 기록할 수 없는 상태입니다: {run.status.value}",
            "run 상태를 조회한 뒤 재시도하세요.",
        )
    submitted = run.model_copy(
        update={
            "status": AdaptiveRunStatus.DESIGN_SUBMITTED,
            "design_submission": submission,
            "version": run.version + 1,
            "updated_at": clock.now(),
        }
    )
    return runs.save(submitted, expected_version=run.version)


def _require_run(runs: AdaptiveWizardRunRepository, run_id: str) -> AdaptiveWizardRun:
    run = runs.find_by_id(run_id)
    if run is None:
        raise PipelineError(
            "adaptive_wizard",
            "Wizard run을 찾을 수 없습니다.",
            "반환된 run_id를 그대로 사용하거나 새 Wizard를 시작하세요.",
        )
    return run


def _validate_project_root(project_root: str) -> None:
    if not project_root.strip() or not is_absolute_path(project_root):
        raise PipelineError(
            "adaptive_wizard",
            "project_root는 절대 경로여야 합니다.",
            "대상 프로젝트의 절대 경로를 사용하세요.",
        )


def _assert_same_start_request(existing: AdaptiveWizardRun, requested: AdaptiveWizardRun) -> None:
    if (
        existing.user_request != requested.user_request
        or existing.project_root != requested.project_root
    ):
        raise PipelineError(
            "adaptive_wizard",
            "같은 request_key가 다른 요청 또는 프로젝트 경로에 사용됐습니다.",
            "새 작업에는 새 request_key를 사용하세요.",
        )
    requested_policy = requested.requested_write_policy
    existing_policy = existing.requested_write_policy or existing.write_policy
    if requested_policy is not None and existing_policy is not requested_policy:
        raise PipelineError(
            "adaptive_wizard",
            "같은 request_key에서 최초 파일 반영 정책을 변경할 수 없습니다.",
            "기존 정책을 그대로 재시도하거나 새 request_key로 Wizard를 시작하세요.",
        )


def _assert_same_questions(
    existing: list[AdaptiveWizardQuestion], requested: list[AdaptiveWizardQuestion]
) -> None:
    if [item.model_dump(mode="json") for item in existing] != [
        item.model_dump(mode="json") for item in requested
    ]:
        raise PipelineError(
            "adaptive_wizard",
            "같은 run_id의 2차 질문은 변경할 수 없습니다.",
            "기존 질문을 그대로 다시 사용하거나 새 request_key로 새 Wizard를 시작하세요.",
        )


def _assert_same_submission(
    existing: AdaptiveWizardSubmission | None, requested: AdaptiveWizardSubmission
) -> None:
    if existing is None or existing.payload_sha256 != requested.payload_sha256:
        raise PipelineError(
            "adaptive_wizard",
            "같은 단계에 다른 제출본을 다시 기록할 수 없습니다.",
            "현재 run 상태를 조회하고 필요한 경우 새 Wizard를 시작하세요.",
        )


def _string_answers(answers: Mapping[str, str | list[str]]) -> dict[str, str]:
    return {
        key: ", ".join(value) if isinstance(value, list) else str(value)
        for key, value in answers.items()
    }


def _resolve_project_type(intake: dict[str, str]) -> ProjectType:
    """Map the new orthogonal intake classification to existing templates.

    Older persisted Runs contain ``project_type`` and continue to use it. New
    product-app Runs classify a mobile surface before their domain hint so an
    Android app cannot be treated as a web blog.
    """

    if "solution_family" not in intake:
        return ProjectType.coerce(intake.get("project_type"))

    family = intake["solution_family"]
    if family == "developer_tool":
        return ProjectType.MCP_SERVER
    if family == "ml_system":
        return ProjectType.ML_PROJECT
    if family == "data_pipeline":
        return ProjectType.DATA_PIPELINE
    if family != "product_application":
        return ProjectType.ETC

    if intake.get("primary_surface") in {
        "android_app",
        "ios_app",
        "cross_platform_app",
    }:
        return ProjectType.MOBILE_APP
    return {
        "communication": ProjectType.MESSENGER,
        "commerce": ProjectType.SHOPPING_MALL,
        "content_publishing": ProjectType.BLOG,
    }.get(intake.get("app_domain_hint") or "", ProjectType.ETC)


def _seed_template_answers(required_fields: list[str], intake: dict[str, str]) -> dict[str, str]:
    defaults = {
        "platform": _platform_for_intake(intake),
        "purpose": intake["goal"],
        "tech_stack": intake["tech_stack"],
        "auth_method": "없음",
        "realtime": "불필요",
        "interface": "MCP 도구",
        "runtime": "Python",
        "distribution": "소스 직접",
        "data_source": "CSV/파일",
        "task_type": "탐색 분석",
        "deployment_target": "배치 파이프라인",
    }
    return {field: defaults[field] for field in required_fields}


def _platform_for_intake(intake: dict[str, str]) -> str:
    return {
        "android_app": "Android",
        "ios_app": "iOS",
        "cross_platform_app": "크로스플랫폼 모바일",
        "web_app": "웹",
    }.get(intake.get("primary_surface") or "", "웹")


def _resolve_tech_stack(default_stack: dict[str, str], selected: str) -> dict[str, str]:
    if selected.strip() == "AI 권장안 사용":
        return dict(default_stack)
    return {"사용자 지정": selected}


def _recommended_stack_decision(selected: str) -> list[RecommendedDecision]:
    if selected.strip() != "AI 권장안 사용":
        return []
    return [
        RecommendedDecision(
            field="tech_stack",
            value="유형 기본 권장안",
            reason="1차 Wizard에서 AI 권장안 사용을 선택했습니다.",
            source="recommended_default",
            confidence="medium",
        )
    ]


def _requested_features(scope: str) -> list[str]:
    values = [
        item.strip(" -\t") for item in scope.replace(";", "\n").replace(",", "\n").splitlines()
    ]
    features = [item for item in values if item]
    return features or [scope]


_PACKAGE_READY_STATUSES = {
    AdaptiveRunStatus.DRAFT_READY,
    AdaptiveRunStatus.CANDIDATE_VALIDATED,
    AdaptiveRunStatus.PREVIEW_READY,
    AdaptiveRunStatus.CONFLICTED,
    AdaptiveRunStatus.APPLIED,
}
