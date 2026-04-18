from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DatsSol Command Bridge"
    database_url: str = "postgresql+psycopg://dats:dats@localhost:55432/dats_sol"
    tick_interval_ms: int = 1000
    provider_poll_interval_ms: int = 250
    game_provider: str = "datssol-mock"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    datssol_base_url: str = "https://games-test.datsteam.dev"
    datssol_stats_url: str = "https://games-test.datsteam.dev/stats/d596e058-a080-305b-f380-68b0753bcb9c"
    datssol_prod_base_url: str = "https://games.datsteam.dev"
    datssol_prod_stats_url: str = "https://games.datsteam.dev/stats/d596e058-a080-305b-f380-68b0753bcb9c"
    datssol_server_mode: Literal["test", "production", "auto"] = "test"
    datssol_production_switch_at_utc: str = "2026-04-18T14:00:00+00:00"
    datssol_team_name: str = "SubSchool"
    datssol_auth_token: str = ""
    datssol_submit_enabled: bool = False
    app_build_id: str = "dev"
    datssol_request_timeout_seconds: float = 0.7
    datssol_connect_timeout_seconds: float = 0.3
    datssol_round_trip_timeout_seconds: float = 0.9
    datssol_observe_request_timeout_seconds: float = 0.65
    datssol_observe_connect_timeout_seconds: float = 0.3
    datssol_observe_round_trip_timeout_seconds: float = 0.9
    datssol_submit_request_timeout_seconds: float = 0.55
    datssol_submit_connect_timeout_seconds: float = 0.3
    datssol_submit_round_trip_timeout_seconds: float = 0.85
    live_observe_interval_seconds: float = 1.0
    live_loop_interval_seconds: float = 0.15
    live_enable_speculative_submit: bool = False
    live_max_inflight_observe: int = 1
    live_max_inflight_submit: int = 1
    live_stale_observe_seconds: float = 1.1
    live_stale_submit_seconds: float = 1.0
    live_submit_min_window_seconds: float = 0.05
    live_submit_deadline_seconds: float = 0.47
    live_submit_production_deadline_seconds: float = 0.18
    live_submit_bootstrap_deadline_seconds: float = 0.2
    live_submit_critical_bootstrap_deadline_seconds: float = 0.3
    live_submit_emergency_deadline_seconds: float = 0.12
    live_submit_compact_build_deadline_seconds: float = 0.06
    live_submit_compact_handoff_deadline_seconds: float = 0.1
    live_submit_sync_after_main_jump_turns: int = 2
    live_rate_limit_backoff_seconds: float = 1.6
    live_bad_request_backoff_seconds: float = 1.6
    runtime_autostart: bool = True
    stats_poll_interval_seconds: float = 60.0
    stats_request_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def auth_configured(self) -> bool:
        return bool(self.datssol_auth_token.strip())

    def datssol_production_switch_datetime(self) -> datetime:
        value = self.datssol_production_switch_at_utc.strip()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def datssol_active_server_target(self, now: datetime | None = None) -> Literal["test", "production"]:
        if self.datssol_server_mode == "test":
            return "test"
        if self.datssol_server_mode == "production":
            return "production"
        reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return "production" if reference >= self.datssol_production_switch_datetime() else "test"

    def datssol_active_base_url(self, now: datetime | None = None) -> str:
        return self.datssol_prod_base_url if self.datssol_active_server_target(now) == "production" else self.datssol_base_url

    def datssol_active_stats_url(self, now: datetime | None = None) -> str:
        return self.datssol_prod_stats_url if self.datssol_active_server_target(now) == "production" else self.datssol_stats_url

    def datssol_next_server_switch_at_utc(self, now: datetime | None = None) -> datetime | None:
        if self.datssol_server_mode != "auto":
            return None
        reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        switch_at = self.datssol_production_switch_datetime()
        return switch_at if reference < switch_at else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
