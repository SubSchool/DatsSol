from __future__ import annotations

import asyncio
from datetime import timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.base import ArenaProvider
from app.schemas.game import (
    ArenaObservation,
    ConstructionView,
    Coordinate,
    EnemyPlantationView,
    GameServerLogEntry,
    MeteoForecastView,
    PlantationUpgradeTier,
    PlantationUpgradesState,
    PlantationView,
    PlayerCommandPayload,
    ProviderStatus,
    PublicErrorResponse,
    SubmitResultView,
    TerraformedCellView,
    BeaverView,
)


def _coord(value: list[int] | None) -> Coordinate | None:
    if not value:
        return None
    return Coordinate.from_pair(value)


class DatsSolLiveProvider(ArenaProvider):
    key = "datssol-live"
    label = "DatsSol Live API"

    def __init__(self) -> None:
        settings = get_settings()
        headers = {}
        if settings.datssol_auth_token:
            headers["X-Auth-Token"] = settings.datssol_auth_token
        self._settings = settings
        production_target = settings.datssol_active_server_target() == "production"
        base_connect_timeout = settings.datssol_connect_timeout_seconds
        base_request_timeout = settings.datssol_request_timeout_seconds
        pool_timeout = 0.6 if production_target else 0.3
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=max(base_connect_timeout, 0.9 if production_target else base_connect_timeout),
                read=max(base_request_timeout, 1.1 if production_target else base_request_timeout),
                write=max(base_request_timeout, 1.1 if production_target else base_request_timeout),
                pool=pool_timeout,
            ),
            limits=httpx.Limits(
                max_connections=4 if production_target else 2,
                max_keepalive_connections=2 if production_target else 1,
            ),
            headers=headers,
        )
        self._last_error: str | None = None

    @staticmethod
    def _error_text(exc: Exception) -> str:
        return str(exc) or repr(exc)

    async def _request(self, method: str, url: str, *, timeout_seconds: float | None = None, **kwargs: Any) -> httpx.Response:
        base_url = self._settings.datssol_active_base_url()
        return await asyncio.wait_for(
            self._client.request(method, f"{base_url}{url}", **kwargs),
            timeout=timeout_seconds or self._settings.datssol_round_trip_timeout_seconds,
        )

    def _production_network_floor(
        self,
        *,
        connect_timeout: float,
        request_timeout: float,
        round_trip_timeout: float,
    ) -> tuple[float, float, float]:
        if self._settings.datssol_active_server_target() != "production":
            return connect_timeout, request_timeout, round_trip_timeout
        return (
            max(connect_timeout, 0.9),
            max(request_timeout, 1.1),
            max(round_trip_timeout, 1.6),
        )

    def _parse_upgrades(self, payload: dict[str, Any] | None) -> PlantationUpgradesState:
        payload = payload or {}
        return PlantationUpgradesState(
            points=payload.get("points", 0),
            interval_turns=payload.get("intervalTurns", 30),
            turns_until_points=payload.get("turnsUntilPoints", 0),
            max_points=payload.get("maxPoints", 0),
            tiers=[
                PlantationUpgradeTier(
                    name=item.get("name", ""),
                    current=item.get("current", 0),
                    max=item.get("max", 0),
                )
                for item in payload.get("tiers", [])
            ],
        )

    def _parse_arena(self, payload: dict[str, Any]) -> ArenaObservation:
        return ArenaObservation(
            turn_no=payload.get("turnNo", 0),
            next_turn_in=float(payload.get("nextTurnIn", 0)),
            width=int(payload.get("size", [0, 0])[0]),
            height=int(payload.get("size", [0, 0])[1]),
            action_range=int(payload.get("actionRange", 2)),
            plantations=[
                PlantationView(
                    id=item.get("id", ""),
                    position=Coordinate.from_pair(item.get("position", [0, 0])),
                    hp=item.get("hp", 0),
                    is_main=item.get("isMain", False),
                    is_isolated=item.get("isIsolated", False),
                    immunity_until_turn=item.get("immunityUntilTurn", 0),
                )
                for item in payload.get("plantations", [])
            ],
            enemy=[
                EnemyPlantationView(
                    id=item.get("id", ""),
                    position=Coordinate.from_pair(item.get("position", [0, 0])),
                    hp=item.get("hp", 0),
                )
                for item in payload.get("enemy", [])
            ],
            constructions=[
                ConstructionView(
                    position=Coordinate.from_pair(item.get("position", [0, 0])),
                    progress=item.get("progress", 0),
                )
                for item in payload.get("construction", [])
            ],
            beavers=[
                BeaverView(
                    id=item.get("id", ""),
                    position=Coordinate.from_pair(item.get("position", [0, 0])),
                    hp=item.get("hp", 0),
                )
                for item in payload.get("beavers", [])
            ],
            cells=[
                TerraformedCellView(
                    position=Coordinate.from_pair(item.get("position", [0, 0])),
                    terraformation_progress=item.get("terraformationProgress", 0),
                    turns_until_degradation=item.get("turnsUntilDegradation", 0),
                )
                for item in payload.get("cells", [])
            ],
            mountains=[Coordinate.from_pair(item) for item in payload.get("mountains", [])],
            forecasts=[
                MeteoForecastView(
                    kind=item.get("kind", ""),
                    turns_until=item.get("turnsUntil"),
                    id=item.get("id"),
                    forming=item.get("forming"),
                    position=_coord(item.get("position")),
                    next_position=_coord(item.get("nextPosition")),
                    radius=item.get("radius"),
                )
                for item in payload.get("meteoForecasts", [])
            ],
            upgrades=self._parse_upgrades(payload.get("plantationUpgrades")),
        )

    async def observe(self) -> ArenaObservation:
        try:
            connect_timeout, request_timeout, round_trip_timeout = self._production_network_floor(
                connect_timeout=self._settings.datssol_observe_connect_timeout_seconds,
                request_timeout=self._settings.datssol_observe_request_timeout_seconds,
                round_trip_timeout=self._settings.datssol_observe_round_trip_timeout_seconds,
            )
            response = await self._request(
                "GET",
                "/api/arena",
                timeout_seconds=round_trip_timeout,
                timeout=httpx.Timeout(
                    connect=connect_timeout,
                    read=request_timeout,
                    write=request_timeout,
                    pool=0.6 if self._settings.datssol_active_server_target() == "production" else 0.3,
                ),
            )
            response.raise_for_status()
            self._last_error = None
            return self._parse_arena(response.json())
        except Exception as exc:
            self._last_error = self._error_text(exc)
            raise

    async def submit(self, payload: PlayerCommandPayload, submit_mode: str) -> SubmitResultView:
        if submit_mode != "live":
            return SubmitResultView(
                dry_run=True,
                accepted=True,
                provider_message="Live provider is in dry-run mode. Command payload was built but not sent.",
            )

        try:
            connect_timeout, request_timeout, round_trip_timeout = self._production_network_floor(
                connect_timeout=self._settings.datssol_submit_connect_timeout_seconds,
                request_timeout=self._settings.datssol_submit_request_timeout_seconds,
                round_trip_timeout=self._settings.datssol_submit_round_trip_timeout_seconds,
            )
            response = await self._request(
                "POST",
                "/api/command",
                json=payload.to_api(),
                timeout_seconds=round_trip_timeout,
                timeout=httpx.Timeout(
                    connect=connect_timeout,
                    read=request_timeout,
                    write=request_timeout,
                    pool=0.6 if self._settings.datssol_active_server_target() == "production" else 0.3,
                ),
            )
            response.raise_for_status()
            data = PublicErrorResponse.model_validate(response.json())
            self._last_error = None
            accepted = not data.errors
            return SubmitResultView(
                dry_run=False,
                accepted=accepted,
                code=data.code,
                errors=data.errors,
                provider_message="Command submitted to DatsSol API." if accepted else f"DatsSol API returned warnings/errors: {data.errors[0]}",
            )
        except Exception as exc:
            self._last_error = self._error_text(exc)
            raise

    async def fetch_server_logs(self) -> list[GameServerLogEntry]:
        try:
            response = await self._request("GET", "/api/logs", timeout_seconds=0.35)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return []
            self._last_error = None
            return [
                GameServerLogEntry(time=item.get("time", ""), message=item.get("message", ""))
                for item in payload
            ]
        except Exception as exc:
            self._last_error = self._error_text(exc)
            return []

    async def reset(self) -> None:
        return None

    def status(self) -> ProviderStatus:
        active_target = self._settings.datssol_active_server_target()
        active_base_url = self._settings.datssol_active_base_url()
        switch_at = self._settings.datssol_next_server_switch_at_utc()
        switch_label = switch_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if switch_at else None
        if not self._settings.auth_configured:
            return ProviderStatus(
                ready=False,
                message=(
                    "Missing DatsSol auth token. Live provider will not authenticate until DATSSOL_AUTH_TOKEN is set. "
                    f"Current target: {active_target} ({active_base_url})"
                    + (f", scheduled production switch at {switch_label}" if switch_label else "")
                ),
                last_error=self._last_error,
            )
        return ProviderStatus(
            ready=True,
            message=(
                f"Live provider ready. Current target: {active_target} ({active_base_url})"
                + (f", scheduled production switch at {switch_label}" if switch_label else "")
            ),
            last_error=self._last_error,
        )

    async def close(self) -> None:
        await self._client.aclose()
