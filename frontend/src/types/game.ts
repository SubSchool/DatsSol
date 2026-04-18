export type RuntimeStatus = 'stopped' | 'running' | 'error'
export type SubmitMode = 'mock' | 'dry-run' | 'live'
export type ManualDirectiveKind =
  | 'build'
  | 'repair'
  | 'sabotage'
  | 'beaver_attack'
  | 'relocate_main'
  | 'upgrade'

export interface Coordinate {
  x: number
  y: number
}

export interface ProviderStatus {
  ready: boolean
  message: string
  last_error: string | null
}

export interface PlantationUpgradeTier {
  name: string
  current: number
  max: number
}

export interface PlantationUpgradesState {
  points: number
  interval_turns: number
  turns_until_points: number
  max_points: number
  tiers: PlantationUpgradeTier[]
}

export interface PlantationView {
  id: string
  position: Coordinate
  hp: number
  is_main: boolean
  is_isolated: boolean
  immunity_until_turn: number
  terraform_progress: number
  turns_until_cell_degradation: number | null
  is_boosted_cell: boolean
  connected: boolean
  turns_to_completion: number | null
  projected_income_per_turn: number
  role: string
}

export interface EnemyPlantationView {
  id: string
  position: Coordinate
  hp: number
}

export interface ConstructionView {
  position: Coordinate
  progress: number
  is_boosted_cell: boolean
  threatened: boolean
}

export interface BeaverView {
  id: string
  position: Coordinate
  hp: number
  threat_score: number
}

export interface TerraformedCellView {
  position: Coordinate
  terraformation_progress: number
  turns_until_degradation: number
  is_boosted: boolean
  total_value: number
  income_per_tick: number
}

export interface MeteoForecastView {
  kind: string
  turns_until: number | null
  id: string | null
  forming: boolean | null
  position: Coordinate | null
  next_position: Coordinate | null
  radius: number | null
}

export interface UpgradeRecommendation {
  name: string
  reason: string
  priority: number
}

export interface AlertView {
  severity: 'info' | 'warn' | 'danger'
  title: string
  description: string
}

export interface TargetCandidateView {
  position: Coordinate
  score: number
  boosted: boolean
  support_count: number
  kind: 'frontier' | 'relay' | 'reclaim' | 'contest'
  reason: string
  threatened: boolean
}

export interface NetworkEdgeView {
  from_position: Coordinate
  to_position: Coordinate
  kind: 'control' | 'planned'
}

export interface PipelineStepView {
  name: string
  status: 'ok' | 'warn' | 'error'
  duration_ms: number
  summary: string
  payload: Record<string, unknown>
}

export interface StrategicIntentView {
  id: string
  kind: ManualDirectiveKind
  priority: number
  summary: string
  reason: string
  source: 'strategy' | 'manual'
  target_position: Coordinate | null
  target_entity_id: string | null
  desired_contributors: number
  score: number
  preferred_author_ids: string[]
}

export interface PlannedActionView {
  kind: 'build' | 'repair' | 'sabotage' | 'beaver_attack'
  source: 'strategy' | 'manual'
  author_id: string
  exit_position: Coordinate
  target_position: Coordinate
  path: Coordinate[]
  estimated_power: number
  reason: string
}

export interface RelocateMainPlanView {
  from_position: Coordinate
  to_position: Coordinate
  urgency: 'low' | 'medium' | 'high' | 'critical'
  reason: string
}

export interface CommandEnvelopeView {
  command: Coordinate[][]
  plantation_upgrade: string | null
  relocate_main: Coordinate[] | null
}

export interface SubmitResultView {
  dry_run: boolean
  accepted: boolean
  code: number | null
  errors: string[]
  provider_message: string
  submitted_at: string
}

export interface BattlefieldStats {
  connected_plantations: number
  isolated_plantations: number
  current_income_per_tick: number
  boosted_active_cells: number
  construction_count: number
  available_settlement_headroom: number
  visible_beavers: number
}

export interface GameServerLogEntry {
  time: string
  message: string
}

export interface ManualDirective {
  id: string
  kind: ManualDirectiveKind
  author_ids: string[]
  target_position: Coordinate | null
  target_entity_id: string | null
  upgrade_name: string | null
  relocate_to_id: string | null
  ttl_turns: number
  created_at_turn: number
  note: string | null
  status: 'active' | 'expired'
}

export interface WorldSnapshot {
  provider: string
  provider_label: string
  arena_name: string
  turn: number
  next_turn_in: number
  width: number
  height: number
  action_range: number
  plantations: PlantationView[]
  enemy: EnemyPlantationView[]
  constructions: ConstructionView[]
  beavers: BeaverView[]
  cells: TerraformedCellView[]
  mountains: Coordinate[]
  forecasts: MeteoForecastView[]
  upgrades: PlantationUpgradesState
  recommended_upgrade: UpgradeRecommendation | null
  network_edges: NetworkEdgeView[]
  recommended_targets: TargetCandidateView[]
  intents: StrategicIntentView[]
  planned_actions: PlannedActionView[]
  manual_directives: ManualDirective[]
  planned_relocate_main: RelocateMainPlanView | null
  stats: BattlefieldStats
  alerts: AlertView[]
  pipeline_steps: PipelineStepView[]
  last_command: CommandEnvelopeView | null
  last_submission: SubmitResultView | null
  server_logs: GameServerLogEntry[]
  highlights: string[]
  updated_at: string
}

export interface StrategyDefinition {
  key: string
  label: string
  description: string
}

export interface StrategyWeights {
  expansion_bias: number
  support_bias: number
  boosted_cell_bias: number
  safety_bias: number
  beaver_hunt_bias: number
  sabotage_bias: number
}

export interface RuntimeSnapshot {
  status: RuntimeStatus
  provider: string
  provider_label: string
  provider_status: ProviderStatus
  tick_interval_ms: number
  poll_interval_ms: number
  submit_mode: SubmitMode
  auth_configured: boolean
  active_strategy_key: string
  strategies: StrategyDefinition[]
  weights: StrategyWeights
  current_turn: number
  pending_directives: number
  last_error: string | null
}

export interface LogEventItem {
  id: number
  turn_number: number
  level: string
  category: string
  source: string
  message: string
  payload: Record<string, unknown>
  created_at: string
}

export interface LogsEnvelope {
  items: LogEventItem[]
  total: number
}

export interface ServerLogsEnvelope {
  items: GameServerLogEntry[]
  total: number
}

export interface LogFilters {
  level: string
  category: string
  source: string
  search: string
  tickFrom: number | null
  tickTo: number | null
}
