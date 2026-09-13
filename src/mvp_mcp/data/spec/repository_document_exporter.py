"""`.mvpmcp/` 문서 패키지의 preview·충돌 감지·원자적 적용."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from secrets import token_urlsafe
from typing import Literal

from mvp_mcp.domain.spec.candidate_package_model import ManagedPackageStatus
from mvp_mcp.domain.spec.documentation_model import (
    DocumentationApplyResult,
    DocumentationPreview,
    PreviewArtifact,
    RenderedDocumentationPackage,
)


@dataclass
class _PreviewState:
    result: DocumentationPreview
    project_root: Path
    package: RenderedDocumentationPackage
    manifest: dict[str, object]


class RepositoryDocumentExporter:
    def __init__(self, output_dir: str) -> None:
        self._output = Path(output_dir).resolve()
        self._previews: dict[str, _PreviewState] = {}

    def preview(
        self, spec_id: str, project_root: str, package: RenderedDocumentationPackage
    ) -> DocumentationPreview:
        root = Path(project_root).resolve()
        if not root.is_dir():
            raise ValueError("프로젝트 루트가 존재하는 디렉터리가 아닙니다.")
        target = self._safe_root(root)
        previous = self._read_manifest(target)
        managed = previous.get("managed_files", {}) if isinstance(previous, dict) else {}
        if not isinstance(managed, dict):
            managed = {}

        artifacts: list[PreviewArtifact] = []
        conflicts: list[str] = []
        for relative, content in sorted(package.files.items()):
            destination = self._safe_destination(target, relative)
            new_hash = self._hash_text(content)
            current_hash = self._hash_file(destination) if destination.is_file() else None
            old_hash = managed.get(relative)
            action: Literal["CREATE", "UPDATE_MANAGED", "KEEP_VALID", "CONFLICT_UNMANAGED"]
            if current_hash is None:
                action = "CREATE"
            elif current_hash == new_hash:
                action = "KEEP_VALID"
            elif isinstance(old_hash, str) and current_hash == old_hash:
                action = "UPDATE_MANAGED"
            else:
                action = "CONFLICT_UNMANAGED"
                conflicts.append(relative)
            artifacts.append(
                PreviewArtifact(
                    relative_path=relative,
                    category=self._category(relative),
                    action=action,
                    new_sha256=new_hash,
                    current_sha256=current_hash,
                )
            )

        current_paths = set(package.files)
        stale = sorted(str(path) for path in managed if path not in current_paths)
        manifest: dict[str, object] = {
            "schema_version": 1,
            "spec_id": spec_id,
            "profile": package.profile.value,
            "source_contract_sha256": package.source_contract_sha256,
            "managed_files": {
                artifact.relative_path: artifact.new_sha256 for artifact in artifacts
            },
            "stale_outputs": stale,
        }
        manifest_text = self._canonical_json(manifest)
        manifest_hash = self._hash_text(manifest_text)
        artifacts.append(
            PreviewArtifact(
                relative_path=".manifest.json",
                category="internal_metadata",
                action=self._manifest_action(target / ".manifest.json", manifest_hash),
                new_sha256=manifest_hash,
                current_sha256=(
                    self._hash_file(target / ".manifest.json")
                    if (target / ".manifest.json").is_file()
                    else None
                ),
            )
        )

        preview_id = token_urlsafe(18)
        directory = (self._output / "previews" / self._safe_segment(spec_id) / preview_id).resolve()
        if self._output not in directory.parents:
            raise ValueError("preview 경로가 서버 출력 디렉터리 밖을 가리킵니다.")
        for relative, content in package.files.items():
            path = self._safe_destination(directory, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
        (directory / ".manifest.json").write_bytes(manifest_text.encode("utf-8"))

        result = DocumentationPreview(
            preview_id=preview_id,
            spec_id=spec_id,
            profile=package.profile,
            manifest_sha256=manifest_hash,
            artifacts=artifacts,
            conflicts=conflicts,
            stale_outputs=stale,
            preview_directory=str(directory),
        )
        self._previews[preview_id] = _PreviewState(result, root, package, manifest)
        return result

    def apply(
        self,
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> DocumentationApplyResult:
        state = self._previews.get(preview_id)
        if state is None:
            raise ValueError("preview를 찾을 수 없거나 만료되었습니다. 다시 preview하세요.")
        result = state.result
        if result.manifest_sha256 != manifest_sha256:
            raise ValueError("승인한 manifest hash가 현재 preview와 다릅니다.")
        if not approved_by or not approval_note:
            raise ValueError("적용 승인자와 승인 메모가 필요합니다.")
        if result.conflicts:
            return DocumentationApplyResult(
                preview_id=preview_id,
                manifest_sha256=manifest_sha256,
                conflicts=result.conflicts,
                stale_outputs=result.stale_outputs,
                status="BLOCKED",
            )

        target = self._safe_root(state.project_root)
        for artifact in result.artifacts:
            destination = self._safe_destination(target, artifact.relative_path)
            current = self._hash_file(destination) if destination.is_file() else None
            if current != artifact.current_sha256:
                raise ValueError(
                    f"preview 이후 대상 파일이 변경되었습니다: {artifact.relative_path}"
                )

        transaction = target / ".transactions" / token_urlsafe(12)
        staged = transaction / "staged"
        backup = transaction / "backup"
        applied: list[str] = []
        skipped: list[str] = []
        try:
            staged.mkdir(parents=True, exist_ok=False)
            backup.mkdir(parents=True, exist_ok=False)
            files = dict(state.package.files)
            manifest = dict(state.manifest)
            manifest["approval"] = {"approved_by": approved_by, "approval_note": approval_note}
            files[".manifest.json"] = self._canonical_json(manifest)
            for relative, content in files.items():
                path = self._safe_destination(staged, relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode("utf-8"))
            target.mkdir(parents=True, exist_ok=True)
            for artifact in result.artifacts:
                relative = artifact.relative_path
                if artifact.action == "KEEP_VALID":
                    skipped.append(relative)
                    continue
                destination = self._safe_destination(target, relative)
                source = self._safe_destination(staged, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    backup_path = self._safe_destination(backup, relative)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup_path)
                os.replace(source, destination)
                applied.append(relative)
        except Exception:
            for relative in reversed(applied):
                destination = self._safe_destination(target, relative)
                backup_path = self._safe_destination(backup, relative)
                if backup_path.exists():
                    os.replace(backup_path, destination)
                elif destination.exists():
                    destination.unlink()
            raise
        finally:
            if transaction.exists():
                shutil.rmtree(transaction, ignore_errors=True)
            transactions = target / ".transactions"
            if transactions.is_dir() and not any(transactions.iterdir()):
                transactions.rmdir()
        del self._previews[preview_id]
        return DocumentationApplyResult(
            preview_id=preview_id,
            manifest_sha256=manifest_sha256,
            applied_outputs=applied,
            skipped_outputs=skipped,
            stale_outputs=result.stale_outputs,
            status="APPLIED",
        )

    def status(self, project_root: str) -> ManagedPackageStatus:
        """대상 ``.mvpmcp/`` manifest를 수정 없이 읽는 진단 snapshot."""

        root = Path(project_root).resolve()
        if not root.is_dir():
            raise ValueError("프로젝트 루트가 존재하는 디렉터리가 아닙니다.")
        target = self._safe_root(root)
        manifest_path = target / ".manifest.json"
        manifest = self._read_manifest(target)
        managed = manifest.get("managed_files", {}) if isinstance(manifest, dict) else {}
        stale = manifest.get("stale_outputs", []) if isinstance(manifest, dict) else []
        spec_id = manifest.get("spec_id")
        profile = manifest.get("profile")
        return ManagedPackageStatus(
            target_root=str(target),
            manifest_present=manifest_path.is_file(),
            spec_id=spec_id if isinstance(spec_id, str) else None,
            profile=profile if isinstance(profile, str) else None,
            managed_files=(
                sorted(key for key, value in managed.items() if isinstance(value, str))
                if isinstance(managed, dict)
                else []
            ),
            stale_outputs=(
                sorted(item for item in stale if isinstance(item, str))
                if isinstance(stale, list)
                else []
            ),
        )

    @staticmethod
    def _safe_root(project_root: Path) -> Path:
        target = (project_root / ".mvpmcp").resolve()
        if target.parent != project_root:
            raise ValueError(".mvpmcp 출력 경로가 프로젝트 루트 밖을 가리킵니다.")
        if target.exists() and target.is_symlink():
            raise ValueError(".mvpmcp는 symlink/reparse 출력 루트일 수 없습니다.")
        return target

    @staticmethod
    def _safe_destination(root: Path, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise ValueError(f"허용되지 않은 상대 경로입니다: {relative}")
        destination = root.joinpath(*pure.parts).resolve()
        if root.resolve() not in destination.parents:
            raise ValueError(f"출력 경로가 .mvpmcp 밖을 가리킵니다: {relative}")
        for parent in destination.parents:
            if parent == root.parent:
                break
            if parent.exists() and parent.is_symlink():
                raise ValueError(f"symlink/reparse 경로를 사용할 수 없습니다: {relative}")
        return destination

    @staticmethod
    def _category(relative: str):  # type: ignore[no-untyped-def]
        if relative == "README.md":
            return "supporting_files"
        if relative.startswith("prototype/"):
            return "prototype_artifacts"
        if relative.startswith("api/"):
            return "contract_artifacts"
        if relative.startswith("artifacts/"):
            return "evidence_artifacts"
        return "managed_documents"

    @staticmethod
    def _manifest_action(path: Path, new_hash: str):  # type: ignore[no-untyped-def]
        if not path.is_file():
            return "CREATE"
        if RepositoryDocumentExporter._hash_file(path) == new_hash:
            return "KEEP_VALID"
        return "UPDATE_MANAGED"

    @staticmethod
    def _hash_text(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _canonical_json(value: dict[str, object]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    @staticmethod
    def _read_manifest(target: Path) -> dict[str, object]:
        path = target / ".manifest.json"
        if not path.is_file():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_segment(value: str) -> str:
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not value or any(char not in allowed for char in value):
            raise ValueError("spec_id에 경로로 사용할 수 없는 문자가 있습니다.")
        return value
