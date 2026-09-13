"""SQLite 기반 적응형 Wizard Run 저장소."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.domain.spec.adaptive_wizard_model import AdaptiveWizardRun


class SqliteAdaptiveWizardRunRepository:
    """request_key unique 제약과 optimistic version으로 Run을 영속화한다."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path.resolve()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_wizard_runs (
                    id TEXT PRIMARY KEY,
                    request_key TEXT NOT NULL UNIQUE,
                    version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)

    def create_or_get(self, run: AdaptiveWizardRun) -> tuple[AdaptiveWizardRun, bool]:
        """동일 request_key에 대해 기존 Run을 재사용한다."""

        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO adaptive_wizard_runs (id, request_key, version, payload_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (run.id, run.request_key, run.version, _serialize(run)),
                )
            except sqlite3.IntegrityError as exc:
                existing = _find_by_request_key(connection, run.request_key)
                if existing is None:
                    raise PipelineError(
                        "adaptive_wizard",
                        "동시 Wizard 생성 상태를 복구하지 못했습니다.",
                        "같은 request_key로 다시 시도하세요.",
                    ) from exc
                return existing, False
        return run, True

    def find_by_id(self, run_id: str) -> AdaptiveWizardRun | None:
        """Run ID로 최신 snapshot을 읽는다."""

        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM adaptive_wizard_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return _deserialize(row["payload_json"]) if row is not None else None

    def save(self, run: AdaptiveWizardRun, expected_version: int) -> AdaptiveWizardRun:
        """현재 version을 비교해 충돌 없는 다음 snapshot만 기록한다."""

        if run.version != expected_version + 1:
            raise ValueError(
                "저장하려는 AdaptiveRun version이 expected_version보다 정확히 1 커야 합니다."
            )
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE adaptive_wizard_runs
                SET version = ?, payload_json = ?
                WHERE id = ? AND version = ?
                """,
                (run.version, _serialize(run), run.id, expected_version),
            )
            if cursor.rowcount != 1:
                raise PipelineError(
                    "adaptive_wizard",
                    "다른 요청이 Wizard 상태를 먼저 변경했습니다.",
                    "documentation_wizard_run_status로 현재 상태를 확인하세요.",
                )
        return run

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _find_by_request_key(
    connection: sqlite3.Connection, request_key: str
) -> AdaptiveWizardRun | None:
    row = connection.execute(
        "SELECT payload_json FROM adaptive_wizard_runs WHERE request_key = ?", (request_key,)
    ).fetchone()
    return _deserialize(row["payload_json"]) if row is not None else None


def _serialize(run: AdaptiveWizardRun) -> str:
    return json.dumps(
        run.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _deserialize(payload: str) -> AdaptiveWizardRun:
    return AdaptiveWizardRun.model_validate_json(payload)
