"""Local, transactional project/revision storage for the carbon research MVP.

The storage interface deliberately keeps full versioned input and output snapshots.
The SQLite implementation is for local development; production deployment needs the
PostgreSQL/identity/backup gate described in the task contract.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from civil_api_contracts.carbon import CarbonProjectInput, ProjectRevision
from civil_workflows.carbon import calculate_project


class RevisionConflictError(ValueError):
    """The caller edited a revision that is no longer current."""


class ProjectNotFoundError(KeyError):
    """Unknown project or revision."""


class CarbonStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS carbon_projects (
                    project_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS carbon_revisions (
                    revision_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES carbon_projects(project_id),
                    revision_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    input_snapshot_hash TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    UNIQUE(project_id, revision_number)
                );
                CREATE INDEX IF NOT EXISTS carbon_revisions_by_project
                    ON carbon_revisions(project_id, revision_number);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _make_revision(
        project_id: UUID, revision_number: int, project: CarbonProjectInput
    ) -> ProjectRevision:
        input_json = project.model_dump_json(exclude_computed_fields=True)
        return ProjectRevision(
            project_id=project_id,
            revision_id=uuid4(),
            revision_number=revision_number,
            created_at=datetime.now(UTC),
            input_snapshot_hash="sha256:" + hashlib.sha256(input_json.encode()).hexdigest(),
            project=project,
            result=calculate_project(project),
        )

    @staticmethod
    def _insert_revision(connection: sqlite3.Connection, revision: ProjectRevision) -> None:
        connection.execute(
            """INSERT INTO carbon_revisions
               (revision_id, project_id, revision_number, created_at,
                input_snapshot_hash, input_json, result_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(revision.revision_id),
                str(revision.project_id),
                revision.revision_number,
                revision.created_at.isoformat(),
                revision.input_snapshot_hash,
                revision.project.model_dump_json(exclude_computed_fields=True),
                revision.result.model_dump_json(exclude_computed_fields=True),
            ),
        )

    @staticmethod
    def _read_revision(row: sqlite3.Row) -> ProjectRevision:
        return ProjectRevision(
            project_id=UUID(row["project_id"]),
            revision_id=UUID(row["revision_id"]),
            revision_number=row["revision_number"],
            created_at=datetime.fromisoformat(row["created_at"]),
            input_snapshot_hash=row["input_snapshot_hash"],
            project=json.loads(row["input_json"]),
            result=json.loads(row["result_json"]),
        )

    def create(self, project: CarbonProjectInput) -> ProjectRevision:
        revision = self._make_revision(uuid4(), 1, project)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO carbon_projects (project_id, created_at) VALUES (?, ?)",
                (str(revision.project_id), revision.created_at.isoformat()),
            )
            self._insert_revision(connection, revision)
        return revision

    def revise(
        self, project_id: UUID, project: CarbonProjectInput, expected_revision_number: int
    ) -> ProjectRevision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT MAX(revision_number) AS current FROM carbon_revisions WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
            if row is None or row["current"] is None:
                raise ProjectNotFoundError(str(project_id))
            if row["current"] != expected_revision_number:
                raise RevisionConflictError(
                    f"expected revision {expected_revision_number}; current is {row['current']}"
                )
            revision = self._make_revision(project_id, expected_revision_number + 1, project)
            self._insert_revision(connection, revision)
        return revision

    def get(self, project_id: UUID, revision_number: int | None = None) -> ProjectRevision:
        sql = (
            "SELECT * FROM carbon_revisions WHERE project_id = ? "
            "ORDER BY revision_number DESC LIMIT 1"
            if revision_number is None
            else "SELECT * FROM carbon_revisions WHERE project_id = ? AND revision_number = ?"
        )
        params: tuple[str] | tuple[str, int] = (
            (str(project_id),) if revision_number is None else (str(project_id), revision_number)
        )
        with self._connect() as connection:
            row = connection.execute(sql, params).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"{project_id}/{revision_number}")
        return self._read_revision(row)

    def list_latest(self) -> list[ProjectRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.* FROM carbon_revisions r
                   JOIN (SELECT project_id, MAX(revision_number) AS latest
                         FROM carbon_revisions GROUP BY project_id) x
                   ON x.project_id = r.project_id AND x.latest = r.revision_number
                   ORDER BY r.created_at DESC"""
            ).fetchall()
        return [self._read_revision(row) for row in rows]

    def list_revisions(self, project_id: UUID) -> list[ProjectRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM carbon_revisions WHERE project_id = ? ORDER BY revision_number DESC",
                (str(project_id),),
            ).fetchall()
        if not rows:
            raise ProjectNotFoundError(str(project_id))
        return [self._read_revision(row) for row in rows]
