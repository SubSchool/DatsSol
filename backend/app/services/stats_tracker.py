from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import desc, select

from app.core.config import get_settings
from app.db.models import TeamRoundResult, TeamStatsSnapshot
from app.db.session import SessionLocal, init_db
from app.schemas.game import TeamRoundResultOut, TeamStatsEnvelope, TeamStatsSnapshotOut


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class StatsTrackerService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=min(2.0, self._settings.stats_request_timeout_seconds),
                read=self._settings.stats_request_timeout_seconds,
                write=self._settings.stats_request_timeout_seconds,
                pool=1.0,
            ),
            headers={"Accept": "application/json"},
        )
        self._task: asyncio.Task | None = None
        self._last_error: str | None = None

    async def start(self) -> None:
        init_db()
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._client.aclose()

    async def _run_loop(self) -> None:
        while True:
            try:
                await self.refresh_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = str(exc) or repr(exc)
            await asyncio.sleep(max(15.0, self._settings.stats_poll_interval_seconds))

    async def refresh_once(self) -> None:
        init_db()
        stats_url = self._settings.datssol_active_stats_url()
        response = await self._client.get(stats_url)
        response.raise_for_status()
        payload = response.json()
        team_name = self._settings.datssol_team_name
        total_players = list((payload.get("total") or {}).get("players") or [])
        current_row: dict[str, Any] | None = None
        current_rank = 0
        for index, row in enumerate(total_players, start=1):
            if row.get("player") == team_name:
                current_row = row
                current_rank = index
                break

        round_rows: list[tuple[str, dict[str, Any], int]] = []
        realms = payload.get("realms") or {}
        for realm_name, realm in realms.items():
            players = list((realm or {}).get("players") or [])
            for index, row in enumerate(players, start=1):
                if row.get("player") == team_name:
                    round_rows.append((realm_name, realm, index))
                    break

        with SessionLocal() as session:
            if current_row is not None:
                latest = session.scalars(
                    select(TeamStatsSnapshot)
                    .where(TeamStatsSnapshot.team_name == team_name)
                    .order_by(TeamStatsSnapshot.created_at.desc(), TeamStatsSnapshot.id.desc())
                    .limit(1)
                ).first()
                score = int(current_row.get("score", 0) or 0)
                ended_at = current_row.get("endedAt", "") or ""
                rank_changed = latest is None or latest.rank != current_rank
                score_changed = latest is None or latest.score != score
                ended_changed = latest is None or latest.ended_at != ended_at
                if rank_changed or score_changed or ended_changed:
                    session.add(
                        TeamStatsSnapshot(
                            team_name=team_name,
                            rank=current_rank,
                            total_players=len(total_players),
                            score=score,
                            ended_at=ended_at,
                            payload={
                                "row": current_row,
                                "source": stats_url,
                            },
                        )
                    )

            existing_realms = {
                item
                for item in session.scalars(
                    select(TeamRoundResult.realm_name).where(TeamRoundResult.team_name == team_name)
                ).all()
            }
            for realm_name, realm, rank in round_rows:
                if realm_name in existing_realms:
                    continue
                player_row = next(
                    (row for row in (realm.get("players") or []) if row.get("player") == team_name),
                    None,
                )
                if player_row is None:
                    continue
                session.add(
                    TeamRoundResult(
                        team_name=team_name,
                        realm_name=realm_name,
                        realm_started_at=realm.get("startedAt", "") or "",
                        realm_ended_at=player_row.get("endedAt", "") or "",
                        rank=rank,
                        score=int(player_row.get("score", 0) or 0),
                        payload={
                            "realm": realm_name,
                            "game": realm.get("game", ""),
                            "player": player_row,
                            "player_count": len(realm.get("players") or []),
                        },
                    )
                )
            session.commit()
        self._last_error = None

    def snapshot(self, *, team_name: str | None = None, history_limit: int = 20, rounds_limit: int = 20) -> TeamStatsEnvelope:
        team_name = team_name or self._settings.datssol_team_name
        with SessionLocal() as session:
            history_rows = session.scalars(
                select(TeamStatsSnapshot)
                .where(TeamStatsSnapshot.team_name == team_name)
                .order_by(TeamStatsSnapshot.created_at.desc(), TeamStatsSnapshot.id.desc())
                .limit(history_limit)
            ).all()
            round_rows = session.scalars(
                select(TeamRoundResult)
                .where(TeamRoundResult.team_name == team_name)
                .order_by(desc(TeamRoundResult.realm_started_at), TeamRoundResult.id.desc())
                .limit(rounds_limit)
            ).all()

        history = [
            TeamStatsSnapshotOut(
                id=row.id,
                team_name=row.team_name,
                rank=row.rank,
                total_players=row.total_players,
                score=row.score,
                ended_at=row.ended_at,
                created_at=row.created_at,
                payload=row.payload or {},
            )
            for row in history_rows
        ]
        rounds = [
            TeamRoundResultOut(
                id=row.id,
                team_name=row.team_name,
                realm_name=row.realm_name,
                realm_started_at=row.realm_started_at,
                realm_ended_at=row.realm_ended_at,
                rank=row.rank,
                score=row.score,
                created_at=row.created_at,
                payload=row.payload or {},
            )
            for row in round_rows
        ]
        return TeamStatsEnvelope(
            team_name=team_name,
            current=history[0] if history else None,
            rounds=rounds,
            history=history,
        )


stats_tracker_service = StatsTrackerService()
