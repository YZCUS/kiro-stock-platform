from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    ModelVersionResponse,
    PromoteModelRequest,
    PruneModelVersionsRequest,
    PruneModelVersionsResponse,
    RollbackModelRequest,
)
from app.settings import Settings


class ModelVersionJob:
    """Manages train-run promotion, rollback, and artifact retention."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def promote_run(
        self,
        db: AsyncSession,
        run_id: str,
        request: PromoteModelRequest,
    ) -> ModelVersionResponse:
        row = await self._get_promotable_run(db, run_id)
        now = datetime.now(timezone.utc)
        scope = self._scope_params(row)

        await db.execute(
            text(
                """
                UPDATE qlib_model_runs
                SET stage = 'archived',
                    archived_at = COALESCE(archived_at, :now),
                    updated_at = NOW()
                WHERE market = :market
                  AND universe = :universe
                  AND model_name = :model_name
                  AND feature_set = :feature_set
                  AND mode = 'train'
                  AND stage = 'previous'
                  AND run_id <> :run_id
                """
            ),
            {**scope, "run_id": run_id, "now": now},
        )
        await db.execute(
            text(
                """
                UPDATE qlib_model_runs
                SET stage = 'previous',
                    updated_at = NOW()
                WHERE market = :market
                  AND universe = :universe
                  AND model_name = :model_name
                  AND feature_set = :feature_set
                  AND mode = 'train'
                  AND stage = 'production'
                  AND run_id <> :run_id
                """
            ),
            {**scope, "run_id": run_id},
        )
        await db.execute(
            text(
                """
                UPDATE qlib_model_runs
                SET stage = 'production',
                    promoted_at = :now,
                    promoted_by = :promoted_by,
                    promotion_note = :promotion_note,
                    archived_at = NULL,
                    updated_at = NOW()
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "now": now,
                "promoted_by": request.promoted_by,
                "promotion_note": request.note,
            },
        )
        await db.commit()
        return await self.get_run(db, run_id)

    async def rollback(
        self,
        db: AsyncSession,
        request: RollbackModelRequest,
    ) -> ModelVersionResponse:
        result = await db.execute(
            text(
                """
                SELECT run_id
                FROM qlib_model_runs
                WHERE market = :market
                  AND universe = :universe
                  AND model_name = :model_name
                  AND feature_set = :feature_set
                  AND mode = 'train'
                  AND status = 'succeeded'
                  AND stage = 'previous'
                  AND artifact_uri IS NOT NULL
                  AND artifact_deleted_at IS NULL
                ORDER BY promoted_at DESC NULLS LAST, finished_at DESC NULLS LAST
                LIMIT 1
                """
            ),
            request.model_dump(),
        )
        previous_run_id = result.scalar_one_or_none()
        if previous_run_id is None:
            raise ValueError(
                "No previous model version is available for rollback "
                f"({request.market}/{request.universe}/{request.model_name})"
            )
        return await self.promote_run(
            db,
            previous_run_id,
            PromoteModelRequest(
                promoted_by=request.promoted_by,
                note=request.note or "rollback to previous model version",
            ),
        )

    async def get_run(self, db: AsyncSession, run_id: str) -> ModelVersionResponse:
        result = await db.execute(
            text(
                """
                SELECT run_id, market, universe, model_name, feature_set, status,
                       stage, artifact_uri, promoted_at, promoted_by, archived_at,
                       artifact_deleted_at
                FROM qlib_model_runs
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ValueError(f"Qlib model run does not exist: {run_id}")
        return self._to_response(row)

    async def prune_versions(
        self,
        db: AsyncSession,
        request: PruneModelVersionsRequest,
    ) -> PruneModelVersionsResponse:
        rows = await self._load_retention_candidates(db, request)
        grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
        for row in rows:
            key = (
                row["market"],
                row["universe"],
                row["model_name"],
                row["feature_set"],
            )
            grouped.setdefault(key, []).append(dict(row))

        retained_run_ids: set[str] = set()
        archived_run_ids: list[str] = []
        deleted_artifact_run_ids: list[str] = []
        for versions in grouped.values():
            versions.sort(
                key=lambda row: (
                    row["finished_at"] or row["started_at"] or row["created_at"],
                    row["run_id"],
                ),
                reverse=True,
            )
            retained = {
                row["run_id"]
                for row in versions
                if row["stage"] in {"production", "previous"}
            }
            retained.update(
                row["run_id"]
                for row in versions[: request.retain_successful_per_model]
            )
            retained_run_ids.update(retained)

            for row in versions:
                run_id = row["run_id"]
                if run_id in retained:
                    continue
                archived_run_ids.append(run_id)
                if request.delete_artifacts and row["artifact_uri"]:
                    deleted_artifact_run_ids.append(run_id)

        if not request.dry_run:
            now = datetime.now(timezone.utc)
            for run_id in archived_run_ids:
                await db.execute(
                    text(
                        """
                        UPDATE qlib_model_runs
                        SET stage = 'archived',
                            archived_at = COALESCE(archived_at, :now),
                            updated_at = NOW()
                        WHERE run_id = :run_id
                        """
                    ),
                    {"run_id": run_id, "now": now},
                )
            if request.delete_artifacts:
                by_run_id = {row["run_id"]: row for row in rows}
                for run_id in deleted_artifact_run_ids:
                    if self._delete_artifact(by_run_id[run_id]["artifact_uri"]):
                        await db.execute(
                            text(
                                """
                                UPDATE qlib_model_runs
                                SET artifact_deleted_at = COALESCE(
                                        artifact_deleted_at,
                                        :now
                                    ),
                                    updated_at = NOW()
                                WHERE run_id = :run_id
                                """
                            ),
                            {"run_id": run_id, "now": now},
                        )
            await db.commit()

        return PruneModelVersionsResponse(
            dry_run=request.dry_run,
            archived_run_ids=sorted(archived_run_ids),
            deleted_artifact_run_ids=sorted(deleted_artifact_run_ids),
            retained_run_ids=sorted(retained_run_ids),
        )

    async def _get_promotable_run(self, db: AsyncSession, run_id: str):
        result = await db.execute(
            text(
                """
                SELECT run_id, market, universe, model_name, feature_set, status,
                       mode, artifact_uri, artifact_deleted_at
                FROM qlib_model_runs
                WHERE run_id = :run_id
                FOR UPDATE
                """
            ),
            {"run_id": run_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ValueError(f"Qlib model run does not exist: {run_id}")
        if row["mode"] != "train":
            raise ValueError(f"Only train runs can be promoted: {run_id}")
        if row["status"] != "succeeded":
            raise ValueError(f"Only succeeded train runs can be promoted: {run_id}")
        if not row["artifact_uri"] or row["artifact_deleted_at"] is not None:
            raise ValueError(f"Promoted run must have a retained artifact: {run_id}")
        return row

    async def _load_retention_candidates(
        self,
        db: AsyncSession,
        request: PruneModelVersionsRequest,
    ):
        filters = [
            "mode = 'train'",
            "status = 'succeeded'",
            "artifact_uri IS NOT NULL",
        ]
        params: dict[str, Any] = {}
        for key in ("market", "universe", "model_name", "feature_set"):
            value = getattr(request, key)
            if value:
                filters.append(f"{key} = :{key}")
                params[key] = value

        result = await db.execute(
            text(
                f"""
                SELECT run_id, market, universe, model_name, feature_set, stage,
                       artifact_uri, finished_at, started_at, created_at
                FROM qlib_model_runs
                WHERE {' AND '.join(filters)}
                ORDER BY market, universe, model_name, feature_set, finished_at DESC
                """
            ),
            params,
        )
        return list(result.mappings().all())

    def _delete_artifact(self, artifact_uri: str) -> bool:
        artifact_path = Path(artifact_uri).resolve()
        artifact_root = self.settings.artifact_root.resolve()
        try:
            artifact_path.relative_to(artifact_root)
        except ValueError:
            return False

        if not artifact_path.exists():
            return True

        parent = artifact_path.parent
        if parent != artifact_root and parent.is_dir():
            shutil.rmtree(parent)
            return True

        artifact_path.unlink()
        return True

    def _scope_params(self, row) -> dict[str, str]:
        return {
            "market": row["market"],
            "universe": row["universe"],
            "model_name": row["model_name"],
            "feature_set": row["feature_set"],
        }

    def _to_response(self, row) -> ModelVersionResponse:
        return ModelVersionResponse(
            run_id=row["run_id"],
            market=row["market"],
            universe=row["universe"],
            model_name=row["model_name"],
            feature_set=row["feature_set"],
            status=row["status"],
            stage=row["stage"],
            artifact_uri=row["artifact_uri"],
            promoted_at=self._isoformat(row["promoted_at"]),
            promoted_by=row["promoted_by"],
            archived_at=self._isoformat(row["archived_at"]),
            artifact_deleted_at=self._isoformat(row["artifact_deleted_at"]),
        )

    def _isoformat(self, value) -> str | None:
        return value.isoformat() if value is not None else None
