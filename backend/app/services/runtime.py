from __future__ import annotations

import asyncio
import csv
import json
import time
from datetime import datetime, timezone
from io import StringIO
from math import ceil
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import WebSocket
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LogEvent, ManualDirectiveRecord, RoundArchive, TeamRoundResult, TeamStatsSnapshot, TickSnapshot
from app.db.session import SessionLocal
from app.planning.analyze import analyze_arena
from app.planning.decide import decide_turn
from app.planning.execute import build_execution_plan
from app.planning.memory import PlannerMemory
from app.planning.strategy_registry import StrategyRegistry
from app.providers.factory import build_provider
from app.schemas.game import (
    ArenaObservation,
    CommandEnvelopeView,
    GameServerLogEntry,
    LogEventOut,
    LogsEnvelope,
    ManualDirective,
    ManualDirectiveCreate,
    ProviderSelectionRequest,
    RuntimeSnapshot,
    RoundArchiveOut,
    RoundArchivesEnvelope,
    ServerLogsEnvelope,
    StrategySelectionRequest,
    StrategyWeights,
    SubmitModeRequest,
    SubmitResultView,
    WeightsUpdateRequest,
    WorldSnapshot,
)


class TelemetryHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


class RuntimeService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._registry = StrategyRegistry()
        self._strategy_key = "frontier"
        self._weights = self._registry.get_weights(self._strategy_key)
        self._provider = build_provider(self._settings.game_provider)
        self._submit_mode = "mock" if self._provider.key == "datssol-mock" else ("live" if self._settings.datssol_submit_enabled else "dry-run")
        self._status = "stopped"
        self._last_error: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._last_processed_turn = -1
        self._turn_lock = asyncio.Lock()
        self._directives: list[ManualDirective] = []
        self._world = self._empty_world()
        self._planner_memory = PlannerMemory()
        self._runtime_session_id = uuid4().hex
        self._last_submit_dispatched_turn = -1
        self._last_submit_acked_turn = -1
        self._force_sync_live_submit_until_turn = -1
        self._last_speculative_submit_turn = -1
        self._submit_backoff_until = 0.0
        self._speculative_backoff_until = 0.0
        self._speculative_failure_streak = 0
        self._last_speculative_log_at = 0.0
        self._cached_server_logs: list[GameServerLogEntry] = []
        self._last_server_logs_fetch_at = 0.0
        self._server_logs_refresh_task: Optional[asyncio.Task] = None
        self._last_observed_arena: Optional[ArenaObservation] = None
        self._last_observed_at = 0.0
        self._last_observe_dispatch_at = 0.0
        self._observe_failure_streak = 0
        self._last_runtime_failure_signature: str | None = None
        self._last_runtime_failure_logged_at = 0.0
        self._observe_tasks: list[tuple[float, asyncio.Task[ArenaObservation]]] = []
        self._submit_tasks: dict[int, dict[str, Any]] = {}
        self._current_round_started_at: datetime | None = None
        self._current_round_started_turn = 0
        self._current_round_build_id = self._settings.app_build_id
        self._current_round_runtime_session_id = self._runtime_session_id
        self.telemetry = TelemetryHub()

    @staticmethod
    def _is_expected_submission_warning(submission: SubmitResultView) -> bool:
        markers = (
            "command already submitted this turn",
            "local guard:",
            "transport uncertain:",
        )
        return any(marker in error for error in submission.errors for marker in markers)

    @staticmethod
    def _exception_text(exc: Exception) -> str:
        base = str(exc) or repr(exc)
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                body = exc.response.text.strip()
            except Exception:
                body = ""
            if body:
                trimmed = body[:400]
                return f"{base} body={trimmed}"
        return base

    def _http_error_delay(self, exc: httpx.HTTPStatusError) -> float:
        status_code = exc.response.status_code
        retry_after = exc.response.headers.get("Retry-After")
        try:
            retry_after_seconds = float(retry_after) if retry_after is not None else 0.0
        except ValueError:
            retry_after_seconds = 0.0
        if status_code == 429:
            return max(self._settings.live_rate_limit_backoff_seconds, retry_after_seconds)
        if status_code == 400:
            return max(self._settings.live_bad_request_backoff_seconds, retry_after_seconds)
        return 0.35

    def _empty_world(self) -> WorldSnapshot:
        return WorldSnapshot(
            provider=self._provider.key,
            provider_label=self._provider.label,
            arena_name="DatsSol",
            turn=0,
            next_turn_in=0,
            width=0,
            height=0,
            action_range=2,
            plantations=[],
            enemy=[],
            constructions=[],
            beavers=[],
            cells=[],
            mountains=[],
            forecasts=[],
            upgrades=self._provider_default_upgrades(),
        )

    @staticmethod
    def _provider_default_upgrades():
        from app.schemas.game import PlantationUpgradesState

        return PlantationUpgradesState()

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            status=self._status,
            provider=self._provider.key,
            provider_label=self._provider.label,
            provider_status=self._provider.status(),
            tick_interval_ms=self._settings.tick_interval_ms,
            poll_interval_ms=self._settings.provider_poll_interval_ms,
            submit_mode=self._submit_mode,
            auth_configured=self._settings.auth_configured,
            active_strategy_key=self._strategy_key,
            strategies=self._registry.definitions(),
            weights=self._weights,
            current_turn=self._world.turn,
            pending_directives=len(self._active_directives(self._world.turn)),
            last_error=self._last_error,
        )

    def world(self) -> WorldSnapshot:
        active = self._active_directives(self._world.turn)
        return self._world.model_copy(update={"manual_directives": active})

    def _restore_recent_snapshot(self) -> None:
        if self._provider.key == "datssol-live":
            return
        if self._world.turn > 0:
            return
        with SessionLocal() as session:
            snapshot = session.scalars(
                select(TickSnapshot)
                .where(TickSnapshot.provider_key == self._provider.key)
                .order_by(TickSnapshot.created_at.desc(), TickSnapshot.id.desc())
                .limit(1)
            ).first()
        if snapshot is None:
            return
        created_at = snapshot.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        if age_seconds > 30:
            return
        try:
            restored_world = WorldSnapshot.model_validate(snapshot.world_state)
            submission_payload = (snapshot.command_batch or {}).get("submission") or {}
            restored_submission = (
                SubmitResultView.model_validate(submission_payload)
                if submission_payload
                else None
            )
        except Exception:
            return

        self._world = restored_world
        self._last_processed_turn = snapshot.tick_number
        if restored_submission is not None and not restored_submission.dry_run:
            self._last_submit_acked_turn = snapshot.tick_number
        self._record_log(
            "info",
            "runtime",
            "control",
            "restored recent snapshot",
            {
                "turn": snapshot.tick_number,
                "age_seconds": round(age_seconds, 2),
            },
            tick_number=snapshot.tick_number,
        )

    def _reset_round_tracking(self) -> None:
        self._current_round_started_at = None
        self._current_round_started_turn = 0
        self._current_round_build_id = self._settings.app_build_id
        self._current_round_runtime_session_id = self._runtime_session_id

    def _ensure_round_tracking(self, turn_no: int) -> None:
        if turn_no <= 0:
            return
        if self._current_round_started_at is None:
            self._current_round_started_at = datetime.now(timezone.utc)
            self._current_round_started_turn = turn_no
            self._current_round_build_id = self._settings.app_build_id
            self._current_round_runtime_session_id = self._runtime_session_id

    async def start(self, restore_snapshot: bool = True) -> RuntimeSnapshot:
        if self._task is not None and not self._task.done():
            self._status = "running"
            await self._broadcast_state()
            return self.snapshot()
        if restore_snapshot:
            self._restore_recent_snapshot()
        self._status = "running"
        self._last_error = None
        self._runtime_session_id = uuid4().hex
        self._record_log(
            "info",
            "runtime",
            "control",
            "runtime started",
            {"provider": self._provider.key, "submit_mode": self._submit_mode},
        )
        self._task = asyncio.create_task(self._run_loop())
        await self._broadcast_state()
        return self.snapshot()

    async def _cancel_background_tasks(self) -> None:
        tasks: list[asyncio.Task] = []
        tasks.extend(task for _, task in self._observe_tasks)
        tasks.extend(
            item["task"]
            for item in self._submit_tasks.values()
            if isinstance(item.get("task"), asyncio.Task)
        )
        if self._server_logs_refresh_task is not None:
            tasks.append(self._server_logs_refresh_task)

        self._observe_tasks = []
        self._submit_tasks = {}
        self._server_logs_refresh_task = None

        for task in tasks:
            if task.done():
                continue
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def stop(self) -> RuntimeSnapshot:
        self._status = "stopped"
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._cancel_background_tasks()
        self._record_log("warn", "runtime", "control", "runtime stopped", {"provider": self._provider.key})
        await self._broadcast_state()
        return self.snapshot()

    async def close(self) -> None:
        await self.stop()
        await self._provider.close()

    async def restart(self) -> RuntimeSnapshot:
        await self.stop()
        await self._provider.reset()
        self._last_processed_turn = -1
        self._last_submit_dispatched_turn = -1
        self._last_submit_acked_turn = -1
        self._force_sync_live_submit_until_turn = -1
        self._last_speculative_submit_turn = -1
        self._submit_backoff_until = 0.0
        self._speculative_backoff_until = 0.0
        self._speculative_failure_streak = 0
        self._last_speculative_log_at = 0.0
        self._cached_server_logs = []
        self._last_server_logs_fetch_at = 0.0
        self._server_logs_refresh_task = None
        self._last_observed_arena = None
        self._last_observed_at = 0.0
        self._last_observe_dispatch_at = 0.0
        self._observe_failure_streak = 0
        self._last_runtime_failure_signature = None
        self._last_runtime_failure_logged_at = 0.0
        self._planner_memory.reset()
        self._reset_round_tracking()
        self._directives.clear()
        self._world = self._empty_world()
        self._record_log("info", "runtime", "control", "runtime reset", {"provider": self._provider.key})
        return await self.start(restore_snapshot=False)

    async def tick_once(self) -> RuntimeSnapshot:
        await self._process_once(force=True)
        return self.snapshot()

    async def set_strategy(self, payload: StrategySelectionRequest) -> RuntimeSnapshot:
        self._strategy_key = payload.strategy_key
        self._weights = self._registry.get_weights(self._strategy_key)
        self._record_log("info", "strategy", "control", "strategy switched", {"strategy": self._strategy_key})
        await self._broadcast_state()
        return self.snapshot()

    async def update_weights(self, payload: WeightsUpdateRequest) -> RuntimeSnapshot:
        updated = self._weights.model_dump()
        updated.update(payload.model_dump(exclude_none=True))
        self._weights = StrategyWeights.model_validate(updated)
        self._record_log("info", "strategy", "control", "weights updated", self._weights.model_dump())
        await self._broadcast_state()
        return self.snapshot()

    async def set_provider(self, payload: ProviderSelectionRequest) -> RuntimeSnapshot:
        was_running = self._task is not None and not self._task.done() and self._status != "stopped"
        if was_running:
            await self.stop()
        await self._provider.close()
        self._provider = build_provider(payload.provider_key)
        self._submit_mode = "mock" if self._provider.key == "datssol-mock" else "dry-run"
        self._last_processed_turn = -1
        self._last_submit_dispatched_turn = -1
        self._last_submit_acked_turn = -1
        self._force_sync_live_submit_until_turn = -1
        self._last_speculative_submit_turn = -1
        self._submit_backoff_until = 0.0
        self._speculative_backoff_until = 0.0
        self._speculative_failure_streak = 0
        self._last_speculative_log_at = 0.0
        self._cached_server_logs = []
        self._last_server_logs_fetch_at = 0.0
        self._server_logs_refresh_task = None
        self._last_observed_arena = None
        self._last_observed_at = 0.0
        self._last_observe_dispatch_at = 0.0
        self._observe_failure_streak = 0
        self._last_runtime_failure_signature = None
        self._last_runtime_failure_logged_at = 0.0
        self._planner_memory.reset()
        self._reset_round_tracking()
        self._world = self._empty_world()
        self._record_log("info", "runtime", "control", "provider switched", {"provider": payload.provider_key})
        if was_running:
            await self.start()
        await self._broadcast_state()
        return self.snapshot()

    async def set_submit_mode(self, payload: SubmitModeRequest) -> RuntimeSnapshot:
        self._submit_mode = payload.submit_mode
        self._last_submit_dispatched_turn = -1
        self._last_submit_acked_turn = -1
        self._force_sync_live_submit_until_turn = -1
        self._submit_backoff_until = 0.0
        self._record_log("info", "runtime", "control", "submit mode changed", {"submit_mode": self._submit_mode})
        await self._broadcast_state()
        return self.snapshot()

    async def enqueue_directive(self, payload: ManualDirectiveCreate) -> ManualDirective:
        directive = ManualDirective(
            id=f"cmd-{uuid4().hex[:8]}",
            created_at_turn=self._world.turn,
            **payload.model_dump(),
        )
        self._directives.append(directive)
        with SessionLocal() as session:
            session.add(
                ManualDirectiveRecord(
                    directive_key=directive.id,
                    tick_number=self._world.turn,
                    kind=directive.kind,
                    status="active",
                    note=directive.note or "",
                    payload=directive.model_dump(mode="json"),
                )
            )
            session.commit()
        self._record_log("info", "manual", "operator", "manual directive queued", directive.model_dump(mode="json"))
        await self._broadcast_state()
        return directive

    def server_logs(self) -> ServerLogsEnvelope:
        return ServerLogsEnvelope(items=self._world.server_logs, total=len(self._world.server_logs))

    async def _refresh_server_logs(self) -> None:
        try:
            logs = await self._provider.fetch_server_logs()
            self._last_server_logs_fetch_at = time.monotonic()
            if logs:
                self._cached_server_logs = logs
        finally:
            self._server_logs_refresh_task = None

    def _schedule_server_logs_refresh(self) -> list[GameServerLogEntry]:
        if self._provider.key != "datssol-live":
            return self._cached_server_logs
        now = time.monotonic()
        if self._observe_failure_streak > 0:
            return self._cached_server_logs
        if (now - self._last_server_logs_fetch_at) >= 45.0 and (
            self._server_logs_refresh_task is None or self._server_logs_refresh_task.done()
        ):
            self._server_logs_refresh_task = asyncio.create_task(self._refresh_server_logs())
        return self._cached_server_logs

    @staticmethod
    def _runtime_failure_family(error_text: str) -> str:
        lowered = error_text.lower()
        if "timeout" in lowered:
            return "timeout"
        if "429" in lowered:
            return "http-429"
        if "400" in lowered:
            return "http-400"
        if "already submitted this turn" in lowered:
            return "duplicate-submit"
        if "local guard:" in lowered:
            return "local-guard"
        return error_text[:120]

    def _should_log_runtime_failure(self, error_text: str) -> bool:
        now = time.monotonic()
        signature = f"{self._world.turn}:{self._runtime_failure_family(error_text)}"
        if self._observe_failure_streak <= 1:
            self._last_runtime_failure_signature = signature
            self._last_runtime_failure_logged_at = now
            return True
        if signature != self._last_runtime_failure_signature:
            self._last_runtime_failure_signature = signature
            self._last_runtime_failure_logged_at = now
            return True
        if self._observe_failure_streak in {2, 3, 5, 8, 13, 21, 34, 55, 89, 144}:
            self._last_runtime_failure_logged_at = now
            return True
        if (now - self._last_runtime_failure_logged_at) >= 30.0:
            self._last_runtime_failure_logged_at = now
            return True
        return False

    def _is_round_rollover(self, turn_no: int) -> bool:
        if turn_no < 0 or self._last_processed_turn < 0:
            return False
        return (self._last_processed_turn - turn_no) > 120

    async def _reset_live_round_state(self, *, keep_world_empty: bool) -> None:
        stale_submit_tasks = [
            item["task"]
            for item in self._submit_tasks.values()
            if isinstance(item.get("task"), asyncio.Task)
        ]
        self._submit_tasks = {}
        for task in stale_submit_tasks:
            if task.done():
                continue
            task.cancel()
        for task in stale_submit_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        self._last_processed_turn = -1
        self._last_submit_dispatched_turn = -1
        self._last_submit_acked_turn = -1
        self._force_sync_live_submit_until_turn = -1
        self._last_speculative_submit_turn = -1
        self._submit_backoff_until = 0.0
        self._speculative_backoff_until = 0.0
        self._speculative_failure_streak = 0
        self._last_speculative_log_at = 0.0
        self._last_observed_arena = None
        self._last_observed_at = 0.0
        self._observe_failure_streak = 0
        self._last_runtime_failure_signature = None
        self._last_runtime_failure_logged_at = 0.0
        self._planner_memory.reset()
        self._reset_round_tracking()
        if keep_world_empty:
            self._world = self._empty_world()
        self._last_error = None

    def _project_arena_for_turn(self, arena: ArenaObservation, target_turn: int) -> ArenaObservation:
        delta = max(0, target_turn - arena.turn_no)
        if delta <= 0:
            return arena

        plantations = [item.model_copy(deep=True) for item in arena.plantations]
        constructions = [item.model_copy(deep=True) for item in arena.constructions]
        cell_by_position = {
            (cell.position.x, cell.position.y): cell.model_copy(deep=True)
            for cell in arena.cells
        }
        connected_positions = {
            (plantation.position.x, plantation.position.y)
            for plantation in plantations
            if not plantation.is_isolated
        }

        for plantation in plantations:
            key = (plantation.position.x, plantation.position.y)
            cell = cell_by_position.get(key)
            if cell is None:
                from app.schemas.game import TerraformedCellView

                cell = TerraformedCellView(
                    position=plantation.position.model_copy(deep=True),
                    terraformation_progress=plantation.terraform_progress,
                    turns_until_degradation=max(0, plantation.turns_until_cell_degradation or 80),
                )
            cell.terraformation_progress = min(100, cell.terraformation_progress + (5 * delta))
            cell_by_position[key] = cell

        projected_cells = []
        for key, cell in cell_by_position.items():
            projected = cell.model_copy(deep=True)
            if key not in connected_positions:
                remaining_until_decay = max(0, projected.turns_until_degradation - delta)
                decay_turns = max(0, delta - projected.turns_until_degradation) if projected.turns_until_degradation > 0 else delta
                projected.turns_until_degradation = remaining_until_decay
                if decay_turns > 0:
                    projected.terraformation_progress = max(0, projected.terraformation_progress - (10 * decay_turns))
            projected_cells.append(projected)

        for plantation in plantations:
            plantation.terraform_progress = next(
                (
                    cell.terraformation_progress
                    for cell in projected_cells
                    if cell.position == plantation.position
                ),
                plantation.terraform_progress,
            )
            plantation.turns_until_cell_degradation = next(
                (
                    cell.turns_until_degradation
                    for cell in projected_cells
                    if cell.position == plantation.position
                ),
                plantation.turns_until_cell_degradation,
            )
            plantation.turns_to_completion = ceil(max(0, 100 - plantation.terraform_progress) / 5) if plantation.terraform_progress < 100 else 0

        for construction in constructions:
            key = (construction.position.x, construction.position.y)
            construction.threatened = key in connected_positions

        return arena.model_copy(
            update={
                "turn_no": target_turn,
                "next_turn_in": 1.0,
                "plantations": plantations,
                "constructions": constructions,
                "cells": projected_cells,
            }
        )

    def _predicted_live_turn(self) -> int | None:
        if (
            self._last_observed_arena is None
            or self._last_observed_at <= 0
            or self._last_observed_arena.turn_no <= 0
        ):
            return None
        now = time.monotonic()
        until_next = max(0.05, self._last_observed_arena.next_turn_in)
        next_turn_at = self._last_observed_at + until_next
        if now < next_turn_at:
            return None
        progressed = 1 + int((now - next_turn_at) // 1.0)
        return self._last_observed_arena.turn_no + progressed

    async def _attempt_speculative_turn(self) -> None:
        if not self._settings.live_enable_speculative_submit:
            return
        if (
            self._provider.key != "datssol-live"
            or self._submit_mode != "live"
            or self._last_observed_arena is None
            or self._last_observed_arena.turn_no <= 0
            or time.monotonic() < self._submit_backoff_until
            or time.monotonic() < self._speculative_backoff_until
            or self._observe_failure_streak < 1
        ):
            return

        predicted_turn = self._predicted_live_turn()
        if predicted_turn is None:
            return
        if (predicted_turn - self._last_observed_arena.turn_no) > 24:
            return
        if self._last_observed_arena.turn_no <= 600 < predicted_turn:
            return
        if predicted_turn <= max(self._last_submit_dispatched_turn, self._last_speculative_submit_turn):
            return

        async with self._turn_lock:
            predicted_turn = self._predicted_live_turn()
            if predicted_turn is None:
                return
            if (predicted_turn - self._last_observed_arena.turn_no) > 24:
                return
            if self._last_observed_arena.turn_no <= 600 < predicted_turn:
                return
            if predicted_turn <= max(self._last_submit_dispatched_turn, self._last_speculative_submit_turn):
                return

            synthetic_world = self._project_arena_for_turn(self._last_observed_arena, predicted_turn)
            synthetic_world = self._planner_memory.augment_arena(synthetic_world)
            analysis = analyze_arena(synthetic_world, planner_memory=self._planner_memory)
            should_force_speculative = (
                analysis.current_mode in {"bootstrap", "defense", "rebase"}
                or len(analysis.connected_ids) <= 3
                or bool(analysis.adjacent_hq_constructions)
                or (analysis.stats.hq_remaining_turns or 0) <= 6
            )
            if not should_force_speculative:
                return
            intents, recommended_upgrade, recommended_relocation = decide_turn(
                analysis=analysis,
                weights=self._weights,
                manual_directives=self._active_directives(predicted_turn),
            )
            execution = build_execution_plan(
                analysis=analysis,
                intents=intents,
                recommended_upgrade=recommended_upgrade,
                recommended_relocation=recommended_relocation,
            )
            payload = execution.payload.model_copy(deep=True)
            payload.plantation_upgrade = None
            if recommended_relocation is None and payload.relocate_main:
                payload.relocate_main = None
            if payload.is_empty():
                return

            execution.payload = payload
            submission = await self._dispatch_live_submit(
                synthetic_world,
                execution,
                imminent_earthquake=analysis.earthquake_soon,
            )
            if submission.accepted:
                self._last_speculative_submit_turn = predicted_turn

            if submission.accepted:
                self._speculative_failure_streak = 0
                self._speculative_backoff_until = 0.0
                should_log = True
            else:
                self._speculative_failure_streak += 1
                self._speculative_backoff_until = time.monotonic() + min(
                    8.0,
                    float(2 ** min(self._speculative_failure_streak - 1, 3)),
                )
                should_log = (
                    not self._is_expected_submission_warning(submission)
                    and (
                        self._speculative_failure_streak in {1, 2, 4}
                        or (time.monotonic() - self._last_speculative_log_at) >= 12.0
                    )
                )

            if not should_log:
                return
            self._last_speculative_log_at = time.monotonic()
            self._record_log(
                "info" if submission.accepted else "warn",
                "submit",
                "speculative",
                submission.provider_message or "speculative submission finished",
                {
                    "turn": predicted_turn,
                    "predicted_turn": predicted_turn,
                    "command": payload.to_api(),
                    **submission.model_dump(mode="json"),
                },
                tick_number=predicted_turn,
            )

    def list_round_archives(self, session: Session, limit: int = 50, offset: int = 0) -> RoundArchivesEnvelope:
        total = session.scalar(select(func.count()).select_from(RoundArchive)) or 0
        rows = session.scalars(
            select(RoundArchive)
            .order_by(RoundArchive.round_ended_at.desc(), RoundArchive.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return RoundArchivesEnvelope(
            items=[
                RoundArchiveOut(
                    id=row.id,
                    provider_key=row.provider_key,
                    strategy_key=row.strategy_key,
                    build_id=row.build_id,
                    runtime_session_id=row.runtime_session_id,
                    round_started_at=row.round_started_at,
                    round_ended_at=row.round_ended_at,
                    first_turn=row.first_turn,
                    last_turn=row.last_turn,
                    observed_turns=row.observed_turns,
                    processed_turns=row.processed_turns,
                    created_at=row.created_at,
                    summary=row.summary or {},
                )
                for row in rows
            ],
            total=total,
        )

    def _archive_completed_round(self, *, ended_at: datetime) -> None:
        if self._current_round_started_at is None or self._last_processed_turn <= 0:
            return

        with SessionLocal() as session:
            rows = session.scalars(
                select(LogEvent)
                .where(LogEvent.created_at >= self._current_round_started_at)
                .where(LogEvent.created_at <= ended_at)
                .order_by(LogEvent.created_at.asc(), LogEvent.id.asc())
            ).all()

            filtered = [
                row
                for row in rows
                if (row.payload or {}).get("runtime_session_id") == self._current_round_runtime_session_id
                and (row.payload or {}).get("build_id") == self._current_round_build_id
            ]
            if not filtered:
                return

            observed_turns = {
                row.tick_number
                for row in filtered
                if row.category in {"observe", "api"} and row.tick_number > 0
            }
            processed_turns = {
                row.tick_number
                for row in filtered
                if row.category == "runtime" and row.message == "turn processed" and row.tick_number > 0
            }

            upgrades_used: dict[str, int] = {}
            successful_submits = 0
            uncertain_submits = 0
            duplicate_submits = 0
            command_posts = 0
            max_connected = 0
            max_income = 0
            max_own = 0
            first_turn = min((row.tick_number for row in filtered if row.tick_number > 0), default=self._current_round_started_turn)
            last_turn = max((row.tick_number for row in filtered if row.tick_number > 0), default=self._last_processed_turn)

            for row in filtered:
                payload = row.payload or {}
                if row.category == "api" and row.source == "command" and row.message == "POST /api/command":
                    command_posts += 1
                    request_body = ((payload.get("request") or {}).get("body") or {})
                    upgrade_name = request_body.get("plantationUpgrade")
                    if upgrade_name:
                        upgrades_used[upgrade_name] = upgrades_used.get(upgrade_name, 0) + 1
                    response_payload = payload.get("response") or {}
                    if response_payload.get("accepted"):
                        successful_submits += 1
                    errors = response_payload.get("errors") or []
                    if any("transport uncertain:" in error for error in errors):
                        uncertain_submits += 1
                    if any("command already submitted this turn" in error for error in errors):
                        duplicate_submits += 1
                elif row.category == "submit":
                    errors = payload.get("errors") or []
                    if any("transport uncertain:" in error for error in errors):
                        uncertain_submits += 1
                    if any("command already submitted this turn" in error for error in errors):
                        duplicate_submits += 1
                elif row.category == "analyze":
                    max_connected = max(max_connected, int(payload.get("connected", 0) or 0))
                    max_income = max(max_income, int(payload.get("income", 0) or 0))
                elif row.category == "observe":
                    max_own = max(max_own, int(payload.get("own", 0) or 0))

            latest_stats = session.scalars(
                select(TeamStatsSnapshot)
                .where(TeamStatsSnapshot.team_name == self._settings.datssol_team_name)
                .order_by(TeamStatsSnapshot.created_at.desc(), TeamStatsSnapshot.id.desc())
                .limit(1)
            ).first()
            linked_realm = session.scalars(
                select(TeamRoundResult)
                .where(TeamRoundResult.team_name == self._settings.datssol_team_name)
                .order_by(TeamRoundResult.created_at.desc(), TeamRoundResult.id.desc())
                .limit(1)
            ).first()

            session.add(
                RoundArchive(
                    provider_key=self._provider.key,
                    strategy_key=self._strategy_key,
                    build_id=self._current_round_build_id,
                    runtime_session_id=self._current_round_runtime_session_id,
                    round_started_at=self._current_round_started_at,
                    round_ended_at=ended_at,
                    first_turn=first_turn,
                    last_turn=last_turn,
                    observed_turns=len(observed_turns),
                    processed_turns=len(processed_turns),
                    summary={
                        "successful_submits": successful_submits,
                        "uncertain_submits": uncertain_submits,
                        "duplicate_submits": duplicate_submits,
                        "command_posts": command_posts,
                        "upgrades_used": upgrades_used,
                        "max_connected": max_connected,
                        "max_income": max_income,
                        "max_own": max_own,
                        "team_rank": latest_stats.rank if latest_stats else None,
                        "team_score_total": latest_stats.score if latest_stats else None,
                        "team_stats_ended_at": latest_stats.ended_at if latest_stats else None,
                        "latest_realm": linked_realm.realm_name if linked_realm else None,
                        "latest_realm_rank": linked_realm.rank if linked_realm else None,
                        "latest_realm_score": linked_realm.score if linked_realm else None,
                    },
                )
            )
            session.commit()

    def list_logs(
        self,
        session: Session,
        level: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        tick_from: Optional[int] = None,
        tick_to: Optional[int] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> LogsEnvelope:
        query = select(LogEvent)
        count_query = select(func.count()).select_from(LogEvent)
        filters = []
        if level:
            filters.append(LogEvent.level == level)
        if category:
            filters.append(LogEvent.category == category)
        if source:
            filters.append(LogEvent.source == source)
        if search:
            filters.append(LogEvent.message.ilike(f"%{search}%"))
        if tick_from is not None:
            filters.append(LogEvent.tick_number >= tick_from)
        if tick_to is not None:
            filters.append(LogEvent.tick_number <= tick_to)

        for filter_clause in filters:
            query = query.where(filter_clause)
            count_query = count_query.where(filter_clause)

        total = session.scalar(count_query) or 0
        rows = session.scalars(
            query.order_by(LogEvent.created_at.desc(), LogEvent.id.desc()).offset(offset).limit(limit)
        ).all()
        return LogsEnvelope(
            items=[
                LogEventOut(
                    id=row.id,
                    turn_number=row.tick_number,
                    level=row.level,
                    category=row.category,
                    source=row.source,
                    message=row.message,
                    payload=row.payload,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=total,
        )

    def export_logs_csv(self, session: Session, **filters: object) -> str:
        envelope = self.list_logs(session=session, limit=5000, offset=0, **filters)
        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["id", "created_at", "turn_number", "level", "category", "source", "message", "payload"],
        )
        writer.writeheader()
        for item in envelope.items:
            writer.writerow(
                {
                    "id": item.id,
                    "created_at": item.created_at.isoformat(),
                    "turn_number": item.turn_number,
                    "level": item.level,
                    "category": item.category,
                    "source": item.source,
                    "message": item.message,
                    "payload": json.dumps(item.payload, ensure_ascii=False),
                }
            )
        return buffer.getvalue()

    async def _handle_runtime_failure(self, exc: Exception) -> float:
        error_text = self._exception_text(exc)
        failure_family = self._runtime_failure_family(error_text)
        silent_pre_round_timeout = (
            self._provider.key == "datssol-live"
            and self._world.turn <= 0
            and (self._last_observed_arena is None or self._last_observed_arena.turn_no <= 0)
            and failure_family == "timeout"
        )
        self._last_error = None if silent_pre_round_timeout else error_text
        if silent_pre_round_timeout and hasattr(self._provider, "_last_error"):
            self._provider._last_error = None
        self._observe_failure_streak += 1
        level = "error" if isinstance(exc, httpx.HTTPStatusError) else "warn"
        if not silent_pre_round_timeout and self._should_log_runtime_failure(error_text):
            self._record_log(
                level,
                "runtime",
                "engine",
                "runtime loop failed",
                {
                    "error": error_text,
                    "error_family": failure_family,
                    "failure_streak": self._observe_failure_streak,
                },
            )
        await self._broadcast_state()
        if isinstance(exc, httpx.HTTPStatusError):
            return self._http_error_delay(exc)
        if isinstance(exc, httpx.TimeoutException):
            return 0.05
        return 0.25

    async def _observe_background(self) -> ArenaObservation:
        return await self._provider.observe()

    async def _submit_background(self, payload) -> SubmitResultView:
        try:
            return await self._provider.submit(payload, self._submit_mode)
        except httpx.HTTPStatusError as exc:
            self._submit_backoff_until = max(
                self._submit_backoff_until,
                time.monotonic() + self._http_error_delay(exc),
            )
            error_text = str(exc) or repr(exc)
            return self._local_submission_result(
                dry_run=False,
                accepted=False,
                message="Provider submit outcome is uncertain.",
                errors=[f"transport uncertain: {error_text}"],
            )
        except Exception as exc:
            error_text = self._exception_text(exc)
            if "429" in error_text:
                self._submit_backoff_until = max(
                    self._submit_backoff_until,
                    time.monotonic() + self._settings.live_rate_limit_backoff_seconds,
                )
            return self._local_submission_result(
                dry_run=False,
                accepted=False,
                message="Provider submit outcome is uncertain.",
                errors=[f"transport uncertain: {error_text}"],
            )

    def _dispatch_observe_if_due(self) -> None:
        if self._provider.key != "datssol-live" or self._status != "running":
            return
        now = time.monotonic()
        inflight_count = len(self._observe_tasks)
        if inflight_count >= self._settings.live_max_inflight_observe:
            return
        if inflight_count == 0:
            if (now - self._last_observe_dispatch_at) < self._settings.live_observe_interval_seconds:
                return
        else:
            oldest_started_at = min(started_at for started_at, _ in self._observe_tasks)
            if (now - oldest_started_at) < self._settings.live_observe_interval_seconds:
                return
            if self._last_observed_at > 0 and (now - self._last_observed_at) < self._settings.live_observe_interval_seconds:
                return
        self._observe_tasks.append((now, asyncio.create_task(self._observe_background())))
        self._last_observe_dispatch_at = now

    async def _drain_observe_tasks(self) -> None:
        if self._provider.key != "datssol-live" or not self._observe_tasks:
            return
        now = time.monotonic()
        remaining: list[tuple[float, asyncio.Task[ArenaObservation]]] = []
        successful: list[ArenaObservation] = []
        cancelled: list[asyncio.Task[ArenaObservation]] = []
        for started_at, task in self._observe_tasks:
            if not task.done():
                if (now - started_at) >= self._settings.live_stale_observe_seconds:
                    task.cancel()
                    cancelled.append(task)
                    continue
                remaining.append((started_at, task))
                continue
            try:
                successful.append(task.result())
            except asyncio.CancelledError:
                continue
            except Exception as exc:
                error_text = self._exception_text(exc)
                silent_pre_round_timeout = (
                    self._world.turn <= 0
                    and (self._last_observed_arena is None or self._last_observed_arena.turn_no <= 0)
                    and self._runtime_failure_family(error_text) == "timeout"
                )
                if not silent_pre_round_timeout:
                    self._write_log_events(
                        [
                            self._build_api_trace_event(
                                level="error" if isinstance(exc, httpx.HTTPStatusError) else "warn",
                                source="arena",
                                message="GET /api/arena failed",
                                method="GET",
                                path="/api/arena",
                                error_text=error_text,
                                tick_number=max(0, self._world.turn),
                            )
                        ]
                    )
                await self._handle_runtime_failure(exc)
        self._observe_tasks = remaining
        for task in cancelled:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        if not successful:
            return
        latest = max(successful, key=lambda item: (item.turn_no, item.next_turn_in))
        stale_tasks = [task for _, task in self._observe_tasks]
        self._observe_tasks = []
        for task in stale_tasks:
            if task.done():
                continue
            task.cancel()
        for task in stale_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        await self._handle_observed_world(latest, force=False, async_live_submit=True)

    async def _drain_submit_tasks(self) -> None:
        if not self._submit_tasks:
            return
        now = time.monotonic()
        completed_turns: list[int] = []
        should_broadcast = False
        log_events: list[LogEvent] = []
        for turn_number, item in list(self._submit_tasks.items()):
            task = item["task"]
            started_at = float(item.get("started_at", now))
            if not task.done():
                turn_age = self._world.turn - turn_number if self._world.turn > 0 else 0
                if (
                    (now - started_at) >= self._settings.live_stale_submit_seconds
                    or turn_age > 1
                ):
                    task.cancel()
                    completed_turns.append(turn_number)
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                continue
            completed_turns.append(turn_number)
            try:
                submission = task.result()
            except asyncio.CancelledError:
                continue
            except Exception as exc:
                error_text = str(exc) or repr(exc)
                submission = self._local_submission_result(
                    dry_run=False,
                    accepted=False,
                    message="Provider submit outcome is uncertain.",
                    errors=[f"transport uncertain: {error_text}"],
                )

            if submission.accepted:
                self._planner_memory.note_submission(
                    item["actions"],
                    submission,
                    imminent_earthquake=item["imminent_earthquake"],
                    issued_turn=turn_number,
                )
            elif submission.errors:
                self._last_error = submission.errors[0]

            if not any(error.startswith("transport uncertain:") for error in submission.errors):
                self._last_submit_acked_turn = max(self._last_submit_acked_turn, turn_number)

            level = (
                "warn"
                if submission.errors and self._is_expected_submission_warning(submission)
                else "error"
                if not submission.accepted and submission.errors
                else "warn"
                if submission.errors
                else "info"
            )
            log_events.append(
                self._build_log_event(
                    level,
                    "submit",
                    "provider",
                    submission.provider_message or "submission finished",
                    {
                        "turn": turn_number,
                        "dispatched_async": True,
                        "acknowledged": not any(error.startswith("transport uncertain:") for error in submission.errors),
                        "command": item["payload"],
                        **submission.model_dump(mode="json"),
                    },
                    tick_number=turn_number,
                )
            )
            log_events.append(
                self._build_api_trace_event(
                    level=level,
                    source="command",
                    message="POST /api/command",
                    method="POST",
                    path="/api/command",
                    request_payload=item["payload"],
                    response_payload=submission.model_dump(mode="json"),
                    tick_number=turn_number,
                )
            )
            if self._world.turn == turn_number:
                self._world = self._world.model_copy(
                    update={"last_submission": submission, "updated_at": datetime.utcnow()}
                )
                should_broadcast = True

        for turn_number in completed_turns:
            self._submit_tasks.pop(turn_number, None)
        self._write_log_events(log_events)
        if should_broadcast:
            await self._broadcast_state()

    async def _run_live_loop(self) -> None:
        while self._status == "running":
            try:
                await self._drain_submit_tasks()
                await self._drain_observe_tasks()
                self._dispatch_observe_if_due()
                await self._attempt_speculative_turn()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = await self._handle_runtime_failure(exc)
                if delay > 0:
                    await asyncio.sleep(delay)
                continue
            await asyncio.sleep(self._settings.live_loop_interval_seconds)

    async def _run_loop(self) -> None:
        if self._provider.key == "datssol-live":
            await self._run_live_loop()
            return

        while self._status == "running":
            delay = 0.0
            try:
                await self._process_once(force=False)
                delay = self._sleep_seconds()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = await self._handle_runtime_failure(exc)
            if delay > 0:
                await asyncio.sleep(delay)

    def _sleep_seconds(self) -> float:
        if self._provider.key == "datssol-live":
            if self._world.turn <= 0 or self._world.next_turn_in <= 0:
                return 0.35
            return max(
                0.12,
                min(
                    1.15,
                    self._world.next_turn_in + self._settings.live_submit_min_window_seconds,
                ),
            )
        return self._settings.tick_interval_ms / 1000

    def _local_submission_result(self, *, dry_run: bool, accepted: bool, message: str, errors: list[str] | None = None) -> SubmitResultView:
        return SubmitResultView(
            dry_run=dry_run,
            accepted=accepted,
            code=0,
            errors=errors or [],
            provider_message=message,
        )

    def _live_submit_guarded_turn(self) -> int:
        return max(self._last_submit_dispatched_turn, self._last_submit_acked_turn)

    @staticmethod
    def _has_existing_adjacent_handoff(
        observed_world: ArenaObservation,
        main,
    ) -> bool:
        return any(
            not plantation.is_main
            and abs(plantation.position.x - main.position.x) + abs(plantation.position.y - main.position.y) == 1
            for plantation in observed_world.plantations
        )

    @staticmethod
    def _is_compact_build_window(observed_world: ArenaObservation) -> bool:
        return len(observed_world.plantations) <= 2 and bool(observed_world.constructions)

    @staticmethod
    def _effective_main_turns_to_completion(observed_world: ArenaObservation, main) -> int | None:
        estimates: list[int] = []
        if getattr(main, "turns_to_completion", None) is not None:
            estimates.append(max(0, int(main.turns_to_completion)))
        if getattr(main, "terraform_progress", None) is not None:
            estimates.append(max(0, ceil((100 - main.terraform_progress) / 5)))

        main_cell = next(
            (
                cell
                for cell in observed_world.cells
                if cell.position.x == main.position.x and cell.position.y == main.position.y
            ),
            None,
        )
        if main_cell is not None:
            estimates.append(max(0, ceil((100 - main_cell.terraformation_progress) / 5)))

        return min(estimates) if estimates else None

    def _should_force_sync_live_submit(self, observed_world: ArenaObservation) -> bool:
        if self._provider.key != "datssol-live" or observed_world.turn_no <= 0:
            return False
        if observed_world.turn_no <= self._force_sync_live_submit_until_turn:
            return True

        main = next((plantation for plantation in observed_world.plantations if plantation.is_main), None)
        if main is None:
            return False

        turns_to_completion = self._effective_main_turns_to_completion(observed_world, main)

        if (
            len(observed_world.plantations) <= 2
            and not observed_world.constructions
            and turns_to_completion is not None
            and turns_to_completion <= 2
            and self._has_existing_adjacent_handoff(observed_world, main)
        ):
            return True

        if self._is_compact_build_window(observed_world):
            return True

        return (
            len(observed_world.plantations) <= 1
            and bool(observed_world.constructions)
            and turns_to_completion is not None
            and turns_to_completion <= 2
        )

    @staticmethod
    def _main_plantation_position(arena: ArenaObservation | None):
        if arena is None:
            return None
        main = next((plantation for plantation in arena.plantations if plantation.is_main), None)
        return main.position if main is not None else None

    @classmethod
    def _main_jump_requires_submit_reset(
        cls,
        previous_arena: ArenaObservation | None,
        current_arena: ArenaObservation,
    ) -> bool:
        previous_position = cls._main_plantation_position(previous_arena)
        current_position = cls._main_plantation_position(current_arena)
        if previous_position is None or current_position is None:
            return False
        dx = abs(previous_position.x - current_position.x)
        dy = abs(previous_position.y - current_position.y)
        return not ((dx == 0 and dy == 0) or (dx + dy == 1))

    async def _cancel_pending_submit_tasks(self, *, reason: str, tick_number: int) -> None:
        stale_submit_tasks = [
            item["task"]
            for item in self._submit_tasks.values()
            if isinstance(item.get("task"), asyncio.Task)
        ]
        self._force_sync_live_submit_until_turn = max(
            self._force_sync_live_submit_until_turn,
            tick_number + self._settings.live_submit_sync_after_main_jump_turns,
        )
        if not stale_submit_tasks:
            return
        self._submit_tasks = {}
        for task in stale_submit_tasks:
            if task.done():
                continue
            task.cancel()
        for task in stale_submit_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._record_log(
            "warn",
            "submit",
            "runtime",
            "Cancelled stale pending live submits after main plantation jump.",
            {
                "reason": reason,
                "force_sync_until_turn": self._force_sync_live_submit_until_turn,
            },
            tick_number=tick_number,
        )

    @staticmethod
    def _normalize_live_relocation_source(observed_world: ArenaObservation, execution) -> bool:
        payload = getattr(execution, "payload", None)
        if payload is None or not payload.relocate_main:
            return False

        main = next((plantation for plantation in observed_world.plantations if plantation.is_main), None)
        if main is None:
            return False

        current_source = payload.relocate_main[0]
        if current_source.x == main.position.x and current_source.y == main.position.y:
            return False

        payload.relocate_main[0] = main.position
        if getattr(execution, "command_view", None) is not None and execution.command_view.relocate_main:
            execution.command_view.relocate_main[0] = main.position
        if hasattr(execution, "relocate_main") and execution.relocate_main:
            execution.relocate_main[0] = main.position
        return True

    @staticmethod
    def _strip_unconfirmed_live_relocation(observed_world: ArenaObservation, execution) -> bool:
        payload = getattr(execution, "payload", None)
        if payload is None or not payload.relocate_main:
            return False

        target = payload.relocate_main[-1]
        target_exists = any(
            plantation.position.x == target.x and plantation.position.y == target.y
            for plantation in observed_world.plantations
        )
        if target_exists:
            return False

        payload.relocate_main = None
        if getattr(execution, "command_view", None) is not None:
            execution.command_view.relocate_main = None
        if hasattr(execution, "relocate_main"):
            execution.relocate_main = None
        return True

    def _live_submit_deadline_for_world(self, observed_world: ArenaObservation) -> float:
        deadline = self._settings.live_submit_deadline_seconds
        if self._provider.key == "datssol-live" and self._settings.datssol_active_server_target() == "production":
            deadline = min(deadline, self._settings.live_submit_production_deadline_seconds)
        main = next((plantation for plantation in observed_world.plantations if plantation.is_main), None)
        turns_to_completion = self._effective_main_turns_to_completion(observed_world, main) if main is not None else None
        has_existing_adjacent_handoff = (
            main is not None and self._has_existing_adjacent_handoff(observed_world, main)
        )
        critical_bootstrap_seed = (
            len(observed_world.plantations) <= 1
            and not observed_world.constructions
            and turns_to_completion is not None
            and turns_to_completion <= 2
        )
        bootstrap_seed = (
            len(observed_world.plantations) <= 1
            and not observed_world.constructions
            and turns_to_completion is not None
            and turns_to_completion <= 12
        )
        emergency_bootstrap = (
            len(observed_world.plantations) <= 1
            and bool(observed_world.constructions)
        )
        compact_critical_finish = (
            len(observed_world.plantations) <= 2
            and bool(observed_world.constructions)
            and turns_to_completion is not None
            and turns_to_completion <= 3
        )
        compact_existing_handoff = (
            len(observed_world.plantations) <= 2
            and not observed_world.constructions
            and has_existing_adjacent_handoff
            and turns_to_completion is not None
            and turns_to_completion <= 3
        )
        critical_compact_existing_handoff = compact_existing_handoff and turns_to_completion is not None and turns_to_completion <= 2
        if critical_bootstrap_seed:
            return max(
                self._settings.live_submit_min_window_seconds,
                min(deadline, self._settings.live_submit_critical_bootstrap_deadline_seconds),
            )
        if bootstrap_seed:
            return max(
                self._settings.live_submit_min_window_seconds,
                min(deadline, self._settings.live_submit_bootstrap_deadline_seconds),
            )
        if self._is_compact_build_window(observed_world):
            return max(
                self._settings.live_submit_min_window_seconds,
                min(deadline, self._settings.live_submit_compact_build_deadline_seconds),
            )
        if emergency_bootstrap or compact_critical_finish or compact_existing_handoff:
            compact_deadline = (
                self._settings.live_submit_compact_handoff_deadline_seconds
                if critical_compact_existing_handoff
                else self._settings.live_submit_emergency_deadline_seconds
            )
            return max(
                self._settings.live_submit_min_window_seconds,
                min(deadline, compact_deadline),
            )
        return deadline

    async def _submit_with_guards(
        self,
        observed_world: ArenaObservation,
        execution,
    ) -> SubmitResultView:
        if self._submit_mode != "live":
            return await self._provider.submit(execution.payload, self._submit_mode)

        if (
            observed_world.turn_no in self._submit_tasks
            or observed_world.turn_no <= self._live_submit_guarded_turn()
        ):
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped duplicate live submit for an already-dispatched turn.",
                errors=["local guard: duplicate live submit prevented"],
            )

        if time.monotonic() < self._submit_backoff_until:
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Live submit backoff is active after a provider rate limit.",
                errors=["local guard: live submit backoff active"],
            )

        self._normalize_live_relocation_source(observed_world, execution)
        self._strip_unconfirmed_live_relocation(observed_world, execution)

        if execution.payload.is_empty():
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped empty live submit locally.",
                errors=["local guard: empty payload skipped before provider submit"],
            )

        if observed_world.next_turn_in <= self._live_submit_deadline_for_world(observed_world):
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped late-turn live submit locally.",
                errors=[
                    f"local guard: late turn submit skipped (next_turn_in={observed_world.next_turn_in:.3f}s)"
                ],
            )

        try:
            self._last_submit_dispatched_turn = observed_world.turn_no
            result = await self._provider.submit(execution.payload, self._submit_mode)
            if not any(error.startswith("transport uncertain:") for error in result.errors):
                self._last_submit_acked_turn = max(self._last_submit_acked_turn, observed_world.turn_no)
            return result
        except Exception as exc:
            error_text = self._exception_text(exc)
            if "429" in error_text:
                self._submit_backoff_until = time.monotonic() + 1.1
            return self._local_submission_result(
                dry_run=False,
                accepted=False,
                message="Provider submit outcome is uncertain.",
                errors=[f"transport uncertain: {error_text}"],
            )

    async def _dispatch_live_submit(
        self,
        observed_world: ArenaObservation,
        execution,
        *,
        imminent_earthquake: bool,
    ) -> SubmitResultView:
        if (
            observed_world.turn_no in self._submit_tasks
            or observed_world.turn_no <= self._live_submit_guarded_turn()
        ):
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Live submit was already dispatched for this turn.",
                errors=[],
            )

        if time.monotonic() < self._submit_backoff_until:
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Live submit backoff is active after a provider rate limit.",
                errors=["local guard: live submit backoff active"],
            )

        inflight_submit_count = sum(
            1
            for item in self._submit_tasks.values()
            if isinstance(item.get("task"), asyncio.Task) and not item["task"].done()
        )
        if inflight_submit_count >= self._settings.live_max_inflight_submit:
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped live submit while older provider submits are still pending.",
                errors=["local guard: inflight live submit cap active"],
            )

        self._normalize_live_relocation_source(observed_world, execution)
        self._strip_unconfirmed_live_relocation(observed_world, execution)

        if execution.payload.is_empty():
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped empty live submit locally.",
                errors=["local guard: empty payload skipped before provider submit"],
            )

        if observed_world.next_turn_in <= self._live_submit_deadline_for_world(observed_world):
            return self._local_submission_result(
                dry_run=True,
                accepted=False,
                message="Skipped late-turn live submit locally.",
                errors=[
                    f"local guard: late turn submit skipped (next_turn_in={observed_world.next_turn_in:.3f}s)"
                ],
            )

        self._last_submit_dispatched_turn = observed_world.turn_no
        payload = execution.payload.model_copy(deep=True)
        self._submit_tasks[observed_world.turn_no] = {
            "task": asyncio.create_task(self._submit_background(payload)),
            "actions": list(execution.actions),
            "payload": payload.to_api(),
            "imminent_earthquake": imminent_earthquake,
            "started_at": time.monotonic(),
        }
        return self._local_submission_result(
            dry_run=False,
            accepted=False,
            message="Live submit dispatched asynchronously.",
        )

    async def _handle_observed_world(
        self,
        raw_world: ArenaObservation,
        *,
        force: bool,
        async_live_submit: bool,
    ) -> None:
        async with self._turn_lock:
            self._observe_failure_streak = 0
            self._last_runtime_failure_signature = None
            self._last_runtime_failure_logged_at = 0.0
            self._speculative_failure_streak = 0
            self._speculative_backoff_until = 0.0
            if self._provider.key == "datssol-live" and raw_world.turn_no <= 0:
                await self._reset_live_round_state(keep_world_empty=True)
                await self._broadcast_state()
                return
            if self._provider.key == "datssol-live" and self._is_round_rollover(raw_world.turn_no):
                previous_turn = self._world.turn
                self._archive_completed_round(ended_at=datetime.now(timezone.utc))
                await self._reset_live_round_state(keep_world_empty=False)
                self._record_log(
                    "info",
                    "runtime",
                    "engine",
                    "live round rollover detected",
                    {
                        "previous_turn": previous_turn,
                        "observed_turn": raw_world.turn_no,
                    },
                    tick_number=raw_world.turn_no,
                )
            if (
                self._provider.key == "datssol-live"
                and self._main_jump_requires_submit_reset(self._last_observed_arena, raw_world)
            ):
                self._planner_memory.reset()
                await self._cancel_pending_submit_tasks(
                    reason="main plantation jumped to a non-adjacent cell; likely respawn or stale core replacement",
                    tick_number=raw_world.turn_no,
                )
            if self._last_observed_arena is None or raw_world.turn_no >= self._last_observed_arena.turn_no:
                self._last_observed_arena = raw_world.model_copy(deep=True)
                self._last_observed_at = time.monotonic()
            if self._provider.key == "datssol-live" and raw_world.turn_no < self._last_processed_turn:
                return
            if self._provider.key == "datssol-live" and not force and raw_world.turn_no == self._last_processed_turn:
                if self._world.turn == raw_world.turn_no:
                    self._world = self._world.model_copy(update={"next_turn_in": raw_world.next_turn_in})
                await self._broadcast_state()
                return

            self._ensure_round_tracking(raw_world.turn_no)

            pipeline_steps = []
            overall_start = time.perf_counter()
            self._planner_memory.observe(raw_world)
            observed_world = self._planner_memory.augment_arena(raw_world)

            step_started = time.perf_counter()
            pipeline_steps.append(
                {
                    "name": "observe",
                    "status": "ok",
                    "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "summary": f"turn {observed_world.turn_no}, own={len(observed_world.plantations)}, enemy={len(observed_world.enemy)}, beavers={len(observed_world.beavers)}",
                    "payload": {
                        "turn": observed_world.turn_no,
                        "next_turn_in": observed_world.next_turn_in,
                        "own": len(observed_world.plantations),
                        "enemy": len(observed_world.enemy),
                        "beavers": len(observed_world.beavers),
                    },
                }
            )

            step_started = time.perf_counter()
            analysis = analyze_arena(observed_world, planner_memory=self._planner_memory)
            pipeline_steps.append(
                {
                    "name": "analyze",
                    "status": "ok",
                    "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "summary": f"mode={analysis.current_mode}, frontier candidates={len(analysis.frontier_candidates)}, connected={analysis.stats.connected_plantations}",
                    "payload": {
                        "mode": analysis.current_mode,
                        "frontier_candidates": len(analysis.frontier_candidates),
                        "connected": analysis.stats.connected_plantations,
                        "income": analysis.stats.current_income_per_tick,
                        "completion_rate_20": analysis.stats.completion_rate_20,
                        "expiration_rate_20": analysis.stats.expiration_rate_20,
                        "hq_remaining_turns": analysis.stats.hq_remaining_turns,
                    },
                }
            )

            step_started = time.perf_counter()
            intents, recommended_upgrade, recommended_relocation = decide_turn(
                analysis=analysis,
                weights=self._weights,
                manual_directives=self._active_directives(observed_world.turn_no),
            )
            pipeline_steps.append(
                {
                    "name": "decide",
                    "status": "ok",
                    "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "summary": f"intents={len(intents)}, upgrade={recommended_upgrade.name if recommended_upgrade else 'none'}",
                    "payload": {
                        "intents": len(intents),
                        "top_intent": intents[0].summary if intents else None,
                        "recommended_upgrade": recommended_upgrade.name if recommended_upgrade else None,
                    },
                }
            )

            step_started = time.perf_counter()
            execution = build_execution_plan(
                analysis=analysis,
                intents=intents,
                recommended_upgrade=recommended_upgrade,
                recommended_relocation=recommended_relocation,
            )
            if self._provider.key == "datssol-live":
                self._strip_unconfirmed_live_relocation(raw_world, execution)
            pipeline_steps.append(
                {
                    "name": "execute",
                    "status": "ok",
                    "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "summary": f"actions={len(execution.actions)}, relocate={bool(execution.relocate_main)}, upgrade={execution.upgrade_name or 'none'}",
                    "payload": {
                        "actions": len(execution.actions),
                        "relocate_main": bool(execution.relocate_main),
                        "upgrade": execution.upgrade_name,
                    },
                }
            )

            step_started = time.perf_counter()
            use_async_live_submit = (
                async_live_submit
                and self._provider.key == "datssol-live"
                and not self._should_force_sync_live_submit(observed_world)
            )
            if use_async_live_submit:
                submission = await self._dispatch_live_submit(
                    observed_world,
                    execution,
                    imminent_earthquake=analysis.earthquake_soon,
                )
            else:
                submission = await self._submit_with_guards(observed_world, execution)
                self._planner_memory.note_submission(
                    execution.actions,
                    submission,
                    imminent_earthquake=analysis.earthquake_soon,
                    issued_turn=observed_world.turn_no,
                )
            pipeline_steps.append(
                {
                    "name": "submit",
                    "status": (
                        "warn"
                        if submission.errors and self._is_expected_submission_warning(submission)
                        else "error"
                        if not submission.accepted and submission.errors
                        else "warn"
                        if submission.errors
                        else "ok"
                    ),
                    "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
                    "summary": submission.provider_message or ("dry-run" if submission.dry_run else "submitted"),
                    "payload": submission.model_dump(mode="json"),
                }
            )

            if self._provider.key == "datssol-live":
                server_logs = self._schedule_server_logs_refresh()
            else:
                server_logs = await self._provider.fetch_server_logs()
            self._last_processed_turn = observed_world.turn_no
            self._world = self._build_world_snapshot(
                observed=observed_world,
                analysis=analysis,
                intents=intents,
                execution=execution.command_view,
                planned_actions=execution.actions,
                recommended_upgrade=recommended_upgrade,
                recommended_relocation=recommended_relocation,
                submission=submission,
                server_logs=server_logs,
                pipeline_steps=pipeline_steps,
            )
            self._last_error = None
            turn_log_events = self._collect_pipeline_log_events(
                observed_world.turn_no,
                pipeline_steps,
                execution.command_view,
                submission,
            )
            if self._provider.key == "datssol-live":
                turn_log_events.insert(
                    0,
                    self._build_api_trace_event(
                        level="info",
                        source="arena",
                        message="GET /api/arena",
                        method="GET",
                        path="/api/arena",
                        response_payload=raw_world.model_dump(mode="json"),
                        tick_number=observed_world.turn_no,
                    ),
                )
                if not async_live_submit:
                    turn_log_events.append(
                        self._build_api_trace_event(
                            level=(
                                "warn"
                                if submission.errors and self._is_expected_submission_warning(submission)
                                else "error"
                                if not submission.accepted and submission.errors
                                else "warn"
                                if submission.errors
                                else "info"
                            ),
                            source="command",
                            message="POST /api/command",
                            method="POST",
                            path="/api/command",
                            request_payload=execution.payload.to_api() if execution.payload else {},
                            response_payload=submission.model_dump(mode="json"),
                            tick_number=observed_world.turn_no,
                        )
                    )
            turn_log_events.append(
                self._build_log_event(
                    "info",
                    "runtime",
                    "engine",
                    "turn processed",
                    {
                        "turn": observed_world.turn_no,
                        "duration_ms": round((time.perf_counter() - overall_start) * 1000, 2),
                        "provider": self._provider.key,
                    },
                    tick_number=observed_world.turn_no,
                )
            )
            self._persist_turn(observed_world, execution.command_view, submission, pipeline_steps, turn_log_events)
            await self._broadcast_state()

    async def _process_once(self, force: bool) -> None:
        raw_world = await self._provider.observe()
        await self._handle_observed_world(raw_world, force=force, async_live_submit=False)

    def _build_world_snapshot(
        self,
        observed: ArenaObservation,
        analysis,
        intents,
        execution: CommandEnvelopeView,
        planned_actions,
        recommended_upgrade,
        recommended_relocation,
        submission: SubmitResultView,
        server_logs: list[GameServerLogEntry],
        pipeline_steps: list[dict],
    ) -> WorldSnapshot:
        from app.schemas.game import PipelineStepView

        return WorldSnapshot(
            provider=self._provider.key,
            provider_label=self._provider.label,
            arena_name="DatsSol",
            turn=observed.turn_no,
            next_turn_in=observed.next_turn_in,
            width=observed.width,
            height=observed.height,
            action_range=observed.action_range,
            plantations=list(analysis.plantation_by_id.values()),
            enemy=analysis.arena.enemy,
            constructions=analysis.arena.constructions,
            beavers=analysis.arena.beavers,
            cells=analysis.arena.cells,
            mountains=analysis.arena.mountains,
            forecasts=observed.forecasts,
            upgrades=observed.upgrades,
            recommended_upgrade=recommended_upgrade,
            network_edges=analysis.network_edges,
            recommended_targets=analysis.frontier_candidates[:18],
            intents=intents[:20],
            planned_actions=planned_actions,
            manual_directives=self._active_directives(observed.turn_no),
            planned_relocate_main=recommended_relocation,
            stats=analysis.stats,
            alerts=analysis.alerts,
            pipeline_steps=[PipelineStepView(**item) for item in pipeline_steps],
            last_command=execution,
            last_submission=submission,
            server_logs=server_logs[:120],
            highlights=analysis.highlights,
        )

    def _build_log_event(
        self,
        level: str,
        category: str,
        source: str,
        message: str,
        payload: dict,
        tick_number: int | None = None,
    ) -> LogEvent:
        enriched_payload = {
            "provider": self._provider.key,
            "strategy": self._strategy_key,
            "build_id": self._settings.app_build_id,
            "runtime_session_id": self._runtime_session_id,
            **payload,
        }
        return LogEvent(
            tick_number=self._world.turn if tick_number is None else tick_number,
            level=level,
            category=category,
            source=source,
            message=message,
            payload=enriched_payload,
        )

    def _build_api_trace_event(
        self,
        *,
        level: str,
        source: str,
        message: str,
        method: str,
        path: str,
        tick_number: int,
        request_payload: dict | list | None = None,
        response_payload: dict | list | None = None,
        error_text: str | None = None,
    ) -> LogEvent:
        request: dict[str, Any] = {
            "method": method,
            "path": path,
        }
        if request_payload is not None:
            request["body"] = request_payload
        payload: dict[str, Any] = {
            "request": request,
        }
        if response_payload is not None:
            payload["response"] = response_payload
        if error_text is not None:
            payload["error"] = error_text
        return self._build_log_event(
            level,
            "api",
            source,
            message,
            payload,
            tick_number=tick_number,
        )

    def _write_log_events(self, events: list[LogEvent]) -> None:
        if not events:
            return
        with SessionLocal() as session:
            session.add_all(events)
            session.commit()

    def _persist_turn(
        self,
        observed: ArenaObservation,
        command_view: CommandEnvelopeView,
        submission: SubmitResultView,
        pipeline_steps: list[dict],
        log_events: list[LogEvent] | None = None,
    ) -> None:
        with SessionLocal() as session:
            session.add(
                TickSnapshot(
                    tick_number=observed.turn_no,
                    provider_key=self._provider.key,
                    strategy_key=self._strategy_key,
                    phase=self._submit_mode,
                    world_state=self._world.model_dump(mode="json"),
                    command_batch={
                        "command": command_view.model_dump(mode="json") if command_view else {},
                        "submission": submission.model_dump(mode="json"),
                        "pipeline": pipeline_steps,
                    },
                )
            )
            if log_events:
                session.add_all(log_events)
            session.commit()

    def _collect_pipeline_log_events(
        self,
        turn_number: int,
        pipeline_steps: list[dict],
        command_view: CommandEnvelopeView,
        submission: SubmitResultView,
    ) -> list[LogEvent]:
        events: list[LogEvent] = []
        for item in pipeline_steps:
            events.append(
                self._build_log_event(
                    "error" if item["status"] == "error" else "warn" if item["status"] == "warn" else "debug",
                    item["name"],
                    "pipeline",
                    item["summary"],
                    {"turn": turn_number, **item["payload"]},
                    tick_number=turn_number,
                )
            )
        events.append(
            self._build_log_event(
                "debug",
                "command",
                "planner",
                "command payload prepared",
                {"turn": turn_number, **(command_view.model_dump(mode="json") if command_view else {})},
                tick_number=turn_number,
            )
        )
        events.append(
            self._build_log_event(
                (
                    "warn"
                    if submission.errors and self._is_expected_submission_warning(submission)
                    else "error"
                    if not submission.accepted and submission.errors
                    else "warn"
                    if submission.errors
                    else "info"
                ),
                "submit",
                "provider",
                submission.provider_message or "submission finished",
                {"turn": turn_number, **submission.model_dump(mode="json")},
                tick_number=turn_number,
            )
        )
        return events

    def _record_log(
        self,
        level: str,
        category: str,
        source: str,
        message: str,
        payload: dict,
        tick_number: int | None = None,
    ) -> None:
        self._write_log_events(
            [
                self._build_log_event(
                    level,
                    category,
                    source,
                    message,
                    payload,
                    tick_number=tick_number,
                )
            ]
        )

    def _active_directives(self, current_turn: int) -> list[ManualDirective]:
        active = [item for item in self._directives if item.is_active(current_turn)]
        for directive in self._directives:
            if not directive.is_active(current_turn):
                directive.status = "expired"
        self._directives = active + [item for item in self._directives if item.status == "expired"]
        return active

    async def _broadcast_state(self) -> None:
        await self.telemetry.broadcast({"type": "world.updated", "world": self.world().model_dump(mode="json")})
        await self.telemetry.broadcast({"type": "runtime.updated", "runtime": self.snapshot().model_dump(mode="json")})


runtime_service = RuntimeService()
