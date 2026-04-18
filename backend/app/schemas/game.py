from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    x: int
    y: int

    @classmethod
    def from_pair(cls, pair: list[int] | tuple[int, int]) -> "Coordinate":
        return cls(x=int(pair[0]), y=int(pair[1]))

    def to_pair(self) -> list[int]:
        return [self.x, self.y]


class ProviderStatus(BaseModel):
    ready: bool = True
    message: str = ""
    last_error: Optional[str] = None


class PlantationUpgradeTier(BaseModel):
    name: str
    current: int = 0
    max: int = 0


class PlantationUpgradesState(BaseModel):
    points: int = 0
    interval_turns: int = 30
    turns_until_points: int = 0
    max_points: int = 0
    tiers: list[PlantationUpgradeTier] = Field(default_factory=list)


class PlantationView(BaseModel):
    id: str
    position: Coordinate
    hp: int
    is_main: bool = False
    is_isolated: bool = False
    immunity_until_turn: int = 0
    terraform_progress: int = 0
    turns_until_cell_degradation: Optional[int] = None
    is_boosted_cell: bool = False
    connected: bool = True
    turns_to_completion: Optional[int] = None
    projected_income_per_turn: int = 0
    role: str = "network"


class EnemyPlantationView(BaseModel):
    id: str
    position: Coordinate
    hp: int


class ConstructionView(BaseModel):
    position: Coordinate
    progress: int
    is_boosted_cell: bool = False
    threatened: bool = False


class BeaverView(BaseModel):
    id: str
    position: Coordinate
    hp: int
    threat_score: float = 0.0


class TerraformedCellView(BaseModel):
    position: Coordinate
    terraformation_progress: int
    turns_until_degradation: int
    is_boosted: bool = False
    total_value: int = 1000
    income_per_tick: int = 50


class MeteoForecastView(BaseModel):
    kind: str
    turns_until: Optional[int] = None
    id: Optional[str] = None
    forming: Optional[bool] = None
    position: Optional[Coordinate] = None
    next_position: Optional[Coordinate] = None
    radius: Optional[int] = None


class UpgradeRecommendation(BaseModel):
    name: str
    reason: str
    priority: int = 0


class AlertView(BaseModel):
    severity: Literal["info", "warn", "danger"]
    title: str
    description: str


class TargetCandidateView(BaseModel):
    position: Coordinate
    score: float
    boosted: bool
    support_count: int
    kind: Literal["frontier", "relay", "reclaim", "contest"]
    reason: str
    threatened: bool = False


class NetworkEdgeView(BaseModel):
    from_position: Coordinate
    to_position: Coordinate
    kind: Literal["control", "planned"] = "control"


class PipelineStepView(BaseModel):
    name: str
    status: Literal["ok", "warn", "error"]
    duration_ms: float
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class StrategyDefinition(BaseModel):
    key: str
    label: str
    description: str


class StrategyWeights(BaseModel):
    expansion_bias: float = 0.85
    support_bias: float = 0.72
    boosted_cell_bias: float = 0.92
    safety_bias: float = 0.76
    beaver_hunt_bias: float = 0.44
    sabotage_bias: float = 0.32
    hq_safety_margin: float = 0.78
    risk_cap: float = 0.72
    construction_cap: int = 4
    output_load_cap: int = 3


class StrategicIntentView(BaseModel):
    id: str
    kind: Literal["build", "finish_build", "repair", "sabotage", "beaver_attack", "relocate_main", "upgrade"]
    priority: int
    summary: str
    reason: str
    source: Literal["strategy", "manual"] = "strategy"
    target_position: Optional[Coordinate] = None
    target_entity_id: Optional[str] = None
    desired_contributors: int = 0
    score: float = 0
    preferred_author_ids: list[str] = Field(default_factory=list)


class PlannedActionView(BaseModel):
    kind: Literal["build", "repair", "sabotage", "beaver_attack"]
    source: Literal["strategy", "manual"]
    author_id: str
    exit_position: Coordinate
    target_position: Coordinate
    path: list[Coordinate]
    estimated_power: int
    reason: str


class RelocateMainPlanView(BaseModel):
    from_position: Coordinate
    to_position: Coordinate
    urgency: Literal["low", "medium", "high", "critical"]
    reason: str


class CommandEnvelopeView(BaseModel):
    command: list[list[Coordinate]] = Field(default_factory=list)
    plantation_upgrade: Optional[str] = None
    relocate_main: Optional[list[Coordinate]] = None


class SubmitResultView(BaseModel):
    dry_run: bool = False
    accepted: bool = True
    code: Optional[int] = None
    errors: list[str] = Field(default_factory=list)
    provider_message: str = ""
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class BattlefieldStats(BaseModel):
    connected_plantations: int = 0
    isolated_plantations: int = 0
    current_income_per_tick: int = 0
    boosted_active_cells: int = 0
    construction_count: int = 0
    available_settlement_headroom: int = 0
    visible_beavers: int = 0
    completion_rate_20: float = 0.0
    expiration_rate_20: float = 0.0
    hq_remaining_turns: int = 0
    safe_hq_moves_count: int = 0
    idle_author_ratio: float = 0.0
    output_congestion_ratio: float = 0.0
    current_mode: str = "economy"


class GameServerLogEntry(BaseModel):
    time: str
    message: str


class ManualDirective(BaseModel):
    id: str
    kind: Literal["build", "finish_build", "repair", "sabotage", "beaver_attack", "relocate_main", "upgrade"]
    author_ids: list[str] = Field(default_factory=list)
    target_position: Optional[Coordinate] = None
    target_entity_id: Optional[str] = None
    upgrade_name: Optional[str] = None
    relocate_to_id: Optional[str] = None
    ttl_turns: int = 3
    created_at_turn: int = 0
    note: Optional[str] = None
    status: Literal["active", "expired"] = "active"

    def is_active(self, current_turn: int) -> bool:
        return self.status == "active" and (current_turn - self.created_at_turn) < self.ttl_turns


class ManualDirectiveCreate(BaseModel):
    kind: Literal["build", "finish_build", "repair", "sabotage", "beaver_attack", "relocate_main", "upgrade"]
    author_ids: list[str] = Field(default_factory=list)
    target_position: Optional[Coordinate] = None
    target_entity_id: Optional[str] = None
    upgrade_name: Optional[str] = None
    relocate_to_id: Optional[str] = None
    ttl_turns: int = 3
    note: Optional[str] = None


class WorldSnapshot(BaseModel):
    provider: str
    provider_label: str
    arena_name: str
    turn: int
    next_turn_in: float
    width: int
    height: int
    action_range: int
    plantations: list[PlantationView]
    enemy: list[EnemyPlantationView]
    constructions: list[ConstructionView]
    beavers: list[BeaverView]
    cells: list[TerraformedCellView]
    mountains: list[Coordinate]
    forecasts: list[MeteoForecastView]
    upgrades: PlantationUpgradesState
    recommended_upgrade: Optional[UpgradeRecommendation] = None
    network_edges: list[NetworkEdgeView] = Field(default_factory=list)
    recommended_targets: list[TargetCandidateView] = Field(default_factory=list)
    intents: list[StrategicIntentView] = Field(default_factory=list)
    planned_actions: list[PlannedActionView] = Field(default_factory=list)
    manual_directives: list[ManualDirective] = Field(default_factory=list)
    planned_relocate_main: Optional[RelocateMainPlanView] = None
    stats: BattlefieldStats = Field(default_factory=BattlefieldStats)
    alerts: list[AlertView] = Field(default_factory=list)
    pipeline_steps: list[PipelineStepView] = Field(default_factory=list)
    last_command: Optional[CommandEnvelopeView] = None
    last_submission: Optional[SubmitResultView] = None
    server_logs: list[GameServerLogEntry] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RuntimeSnapshot(BaseModel):
    status: Literal["stopped", "running", "error"]
    provider: str
    provider_label: str
    provider_status: ProviderStatus = Field(default_factory=ProviderStatus)
    tick_interval_ms: int
    poll_interval_ms: int
    submit_mode: Literal["mock", "dry-run", "live"]
    auth_configured: bool = False
    active_strategy_key: str
    strategies: list[StrategyDefinition]
    weights: StrategyWeights
    current_turn: int
    pending_directives: int
    last_error: Optional[str] = None


class StrategySelectionRequest(BaseModel):
    strategy_key: str


class WeightsUpdateRequest(BaseModel):
    expansion_bias: Optional[float] = None
    support_bias: Optional[float] = None
    boosted_cell_bias: Optional[float] = None
    safety_bias: Optional[float] = None
    beaver_hunt_bias: Optional[float] = None
    sabotage_bias: Optional[float] = None


class ProviderSelectionRequest(BaseModel):
    provider_key: Literal["datssol-mock", "datssol-live"]


class SubmitModeRequest(BaseModel):
    submit_mode: Literal["mock", "dry-run", "live"]


class LogEventOut(BaseModel):
    id: int
    turn_number: int
    level: str
    category: str
    source: str
    message: str
    payload: dict[str, Any]
    created_at: datetime


class LogsEnvelope(BaseModel):
    items: list[LogEventOut]
    total: int


class TeamStatsEntry(BaseModel):
    player: str
    rank: int
    score: int
    ended_at: str = ""
    counters: dict[str, int] = Field(default_factory=dict)


class TeamStatsSnapshotOut(BaseModel):
    id: int
    team_name: str
    rank: int
    total_players: int
    score: int
    ended_at: str = ""
    created_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class TeamRoundResultOut(BaseModel):
    id: int
    team_name: str
    realm_name: str
    realm_started_at: str = ""
    realm_ended_at: str = ""
    rank: int
    score: int
    created_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class TeamStatsEnvelope(BaseModel):
    team_name: str
    current: Optional[TeamStatsSnapshotOut] = None
    rounds: list[TeamRoundResultOut] = Field(default_factory=list)
    history: list[TeamStatsSnapshotOut] = Field(default_factory=list)


class RoundArchiveOut(BaseModel):
    id: int
    provider_key: str
    strategy_key: str
    build_id: str
    runtime_session_id: str
    round_started_at: datetime
    round_ended_at: datetime
    first_turn: int
    last_turn: int
    observed_turns: int
    processed_turns: int
    created_at: datetime
    summary: dict[str, Any] = Field(default_factory=dict)


class RoundArchivesEnvelope(BaseModel):
    items: list[RoundArchiveOut]
    total: int


class ServerLogsEnvelope(BaseModel):
    items: list[GameServerLogEntry]
    total: int


class ArenaObservation(BaseModel):
    turn_no: int
    next_turn_in: float
    width: int
    height: int
    action_range: int
    plantations: list[PlantationView]
    enemy: list[EnemyPlantationView]
    constructions: list[ConstructionView]
    beavers: list[BeaverView]
    cells: list[TerraformedCellView]
    mountains: list[Coordinate]
    forecasts: list[MeteoForecastView]
    upgrades: PlantationUpgradesState
    server_logs: list[GameServerLogEntry] = Field(default_factory=list)


class PlantationActionPayload(BaseModel):
    path: list[Coordinate]

    def to_api(self) -> dict[str, Any]:
        return {"path": [coordinate.to_pair() for coordinate in self.path]}


class PlayerCommandPayload(BaseModel):
    command: list[PlantationActionPayload] = Field(default_factory=list)
    plantation_upgrade: Optional[str] = None
    relocate_main: Optional[list[Coordinate]] = None

    def is_empty(self) -> bool:
        return not self.command and not self.plantation_upgrade and not self.relocate_main

    def to_api(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.command:
            payload["command"] = [item.to_api() for item in self.command]
        if self.plantation_upgrade:
            payload["plantationUpgrade"] = self.plantation_upgrade
        if self.relocate_main:
            payload["relocateMain"] = [coordinate.to_pair() for coordinate in self.relocate_main]
        return payload


class PublicErrorResponse(BaseModel):
    code: int = 0
    errors: list[str] = Field(default_factory=list)
