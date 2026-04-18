from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from app.planning.geometry import (
    cardinal_neighbors,
    chebyshev_distance,
    clamp_to_map,
    is_boosted_cell,
    is_cardinal_neighbor,
    manhattan_distance,
)
from app.planning.memory import PlannerMemory
from app.schemas.game import (
    AlertView,
    ArenaObservation,
    BattlefieldStats,
    ConstructionView,
    Coordinate,
    NetworkEdgeView,
    PlantationUpgradeTier,
    PlantationView,
    TargetCandidateView,
    UpgradeRecommendation,
)


@dataclass
class ArenaAnalysis:
    arena: ArenaObservation
    tier_by_name: dict[str, PlantationUpgradeTier]
    main_plantation: PlantationView | None
    plantation_by_id: dict[str, PlantationView]
    plantation_by_position: dict[tuple[int, int], PlantationView]
    construction_by_position: dict[tuple[int, int], ConstructionView]
    cell_by_position: dict[tuple[int, int], int]
    cell_turns_by_position: dict[tuple[int, int], int]
    construction_positions: set[tuple[int, int]]
    enemy_positions: set[tuple[int, int]]
    beaver_positions: set[tuple[int, int]]
    mountain_positions: set[tuple[int, int]]
    connected_ids: set[str]
    articulation_ids: set[str]
    critical_positions: set[tuple[int, int]]
    depth_by_id: dict[str, int]
    network_edges: list[NetworkEdgeView]
    frontier_candidates: list[TargetCandidateView]
    alerts: list[AlertView]
    stats: BattlefieldStats
    settlement_limit: int
    signal_range: int
    vision_range: int
    construction_power: int
    repair_power: int
    sabotage_power: int
    beaver_attack_power: int
    decay_speed: int
    earthquake_mitigation: int
    beaver_damage_mitigation: int
    earthquake_turns_until: int | None = None
    earthquake_now: bool = False
    earthquake_soon: bool = False
    current_mode: str = "economy"
    opening_stage: str = "economy"
    hq_anchor_candidates: list[Coordinate] = field(default_factory=list)
    adjacent_hq_constructions: list[ConstructionView] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    planner_memory: PlannerMemory | None = None


def _key(position: Coordinate) -> tuple[int, int]:
    return (position.x, position.y)


def _tier_map(arena: ArenaObservation) -> dict[str, PlantationUpgradeTier]:
    return {tier.name: tier for tier in arena.upgrades.tiers}


def _tier_value(tiers: dict[str, PlantationUpgradeTier], name: str) -> int:
    return tiers.get(name, PlantationUpgradeTier(name=name, current=0, max=0)).current


def _build_connected_component(
    plantations: list[PlantationView], main: PlantationView | None
) -> tuple[set[str], list[NetworkEdgeView], dict[str, list[str]], dict[str, int]]:
    if main is None:
        return set(), [], {}, {}

    position_to_id = {_key(item.position): item.id for item in plantations}
    adjacency = {item.id: [] for item in plantations}
    edges: list[NetworkEdgeView] = []
    for plantation in plantations:
        for candidate in plantations:
            if plantation.id == candidate.id or not is_cardinal_neighbor(plantation.position, candidate.position):
                continue
            adjacency[plantation.id].append(candidate.id)
            if plantation.id < candidate.id:
                edges.append(NetworkEdgeView(from_position=plantation.position, to_position=candidate.position))

    queue = [main.id]
    visited: set[str] = set()
    depth_by_id: dict[str, int] = {main.id: 0}
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        current_depth = depth_by_id.get(current_id, 0)
        for candidate_id in adjacency.get(current_id, []):
            if candidate_id not in depth_by_id:
                depth_by_id[candidate_id] = current_depth + 1
            if candidate_id not in visited:
                queue.append(candidate_id)

    connected_edges = [
        edge
        for edge in edges
        if position_to_id[_key(edge.from_position)] in visited and position_to_id[_key(edge.to_position)] in visited
    ]
    return visited, connected_edges, adjacency, depth_by_id


def _articulation_points(
    connected_ids: set[str],
    adjacency: dict[str, list[str]],
) -> set[str]:
    order: dict[str, int] = {}
    low: dict[str, int] = {}
    visited: set[str] = set()
    articulation: set[str] = set()
    counter = 0

    def dfs(node_id: str, parent_id: str | None) -> None:
        nonlocal counter
        visited.add(node_id)
        order[node_id] = counter
        low[node_id] = counter
        counter += 1

        child_count = 0
        for neighbor_id in adjacency.get(node_id, []):
            if neighbor_id not in connected_ids:
                continue
            if neighbor_id == parent_id:
                continue
            if neighbor_id not in visited:
                child_count += 1
                dfs(neighbor_id, node_id)
                low[node_id] = min(low[node_id], low[neighbor_id])
                if parent_id is not None and low[neighbor_id] >= order[node_id]:
                    articulation.add(node_id)
            else:
                low[node_id] = min(low[node_id], order[neighbor_id])

        if parent_id is None and child_count > 1:
            articulation.add(node_id)

    for node_id in connected_ids:
        if node_id not in visited:
            dfs(node_id, None)

    return articulation


def _cell_progress(arena: ArenaObservation) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], int]]:
    progress = {}
    turns = {}
    for cell in arena.cells:
        progress[_key(cell.position)] = cell.terraformation_progress
        turns[_key(cell.position)] = cell.turns_until_degradation
    return progress, turns


def _occupied_positions(
    arena: ArenaObservation,
) -> tuple[set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]]]:
    constructions = {_key(item.position) for item in arena.constructions}
    enemies = {_key(item.position) for item in arena.enemy}
    beavers = {_key(item.position) for item in arena.beavers}
    mountains = {_key(item) for item in arena.mountains}
    return constructions, enemies, beavers, mountains


def _safe_hq_moves(analysis: ArenaAnalysis) -> list[Coordinate]:
    if analysis.main_plantation is None:
        return []
    options: list[tuple[int, Coordinate]] = []
    for plantation in analysis.arena.plantations:
        if plantation.id == analysis.main_plantation.id or plantation.id not in analysis.connected_ids:
            continue
        if not is_cardinal_neighbor(analysis.main_plantation.position, plantation.position):
            continue
        pressure = sum(1 for beaver in analysis.arena.beavers if chebyshev_distance(beaver.position, plantation.position) <= 2)
        progress = analysis.cell_by_position.get(_key(plantation.position), 0)
        remaining_turns = ceil(max(0, 100 - progress) / 5) if progress < 100 else 0
        adjacent_future_links = 0
        for neighbor in cardinal_neighbors(plantation.position):
            neighbor_key = _key(neighbor)
            if not clamp_to_map(neighbor, analysis.arena.width, analysis.arena.height):
                continue
            if neighbor_key in analysis.mountain_positions or neighbor_key in analysis.enemy_positions or neighbor_key in analysis.beaver_positions:
                continue
            if neighbor_key in analysis.construction_positions:
                adjacent_future_links += 1
                continue
            neighbor_plantation = analysis.plantation_by_position.get(neighbor_key)
            if neighbor_plantation and neighbor_plantation.id in analysis.connected_ids:
                adjacent_future_links += 1
                continue
            if neighbor_key not in analysis.plantation_by_position:
                neighbor_progress = analysis.cell_by_position.get(neighbor_key, 0)
                if neighbor_progress <= 55:
                    adjacent_future_links += 1
        score = (
            (remaining_turns * 14)
            + sum(
                12
                for other in analysis.arena.plantations
                if other.id in analysis.connected_ids and other.id != plantation.id and is_cardinal_neighbor(other.position, plantation.position)
            )
            + (adjacent_future_links * 10)
            - (pressure * 15)
        )
        if remaining_turns <= 6:
            score -= (7 - remaining_turns) * 16
        options.append((score, plantation.position))
    options.sort(key=lambda item: item[0], reverse=True)
    return [position for _, position in options]


def _dedupe_constructions(arena: ArenaObservation) -> list[ConstructionView]:
    by_position: dict[tuple[int, int], ConstructionView] = {}
    for construction in arena.constructions:
        key = _key(construction.position)
        existing = by_position.get(key)
        if existing is None or construction.progress > existing.progress:
            by_position[key] = construction
    return list(by_position.values())


def _opening_stage(analysis: ArenaAnalysis) -> str:
    if analysis.current_mode == "bootstrap":
        return "seed_anchor"
    adjacent_constructions = sum(
        1
        for construction in analysis.arena.constructions
        if analysis.main_plantation and is_cardinal_neighbor(construction.position, analysis.main_plantation.position)
    )
    if not analysis.main_plantation:
        return "rebase"
    if len(analysis.connected_ids) <= 1:
        return "seed_anchor"
    if (len(analysis.hq_anchor_candidates) + adjacent_constructions) < 2:
        return "second_anchor"
    if len(analysis.connected_ids) <= 6:
        return "double_lane"
    return "economy"


def _candidate_reason(
    analysis: ArenaAnalysis,
    position: Coordinate,
    boosted: bool,
    support_count: int,
    progress_bonus: int,
    remaining_turns: int,
    threatened: bool,
) -> tuple[str, str]:
    if analysis.main_plantation and is_cardinal_neighbor(position, analysis.main_plantation.position):
        return "relay", "prepare an adjacent anchor for the next HQ relocation."
    if boosted:
        return "frontier", "boosted tile with acceptable network geometry."
    if progress_bonus > 0 and remaining_turns >= 10:
        return "reclaim", "reuse an early-progress cell that still has enough lifetime to support the backbone."
    if support_count >= 2:
        return "relay", "extend the backbone with multi-side support."
    if threatened:
        return "contest", "claim the lane before hazards or rivals make it more expensive."
    return "frontier", "expand the rolling carpet while keeping the chain compact."


def _build_frontier_candidates(analysis: ArenaAnalysis) -> list[TargetCandidateView]:
    if not analysis.main_plantation:
        return []

    candidates: dict[tuple[int, int], TargetCandidateView] = {}
    occupied = (
        set(analysis.plantation_by_position.keys())
        | analysis.construction_positions
        | analysis.enemy_positions
        | analysis.beaver_positions
        | analysis.mountain_positions
    )
    hq_turns = analysis.main_plantation.turns_to_completion or 0
    memory = analysis.planner_memory
    expected_build_turns = ceil(50 / max(1, analysis.construction_power))

    for plantation in analysis.arena.plantations:
        if plantation.id not in analysis.connected_ids:
            continue

        for neighbor in cardinal_neighbors(plantation.position):
            position_key = _key(neighbor)
            if not clamp_to_map(neighbor, analysis.arena.width, analysis.arena.height):
                continue
            if position_key in occupied:
                continue

            support_nodes = [
                other
                for other in analysis.arena.plantations
                if other.id in analysis.connected_ids and is_cardinal_neighbor(other.position, neighbor)
            ]
            support_count = len(support_nodes)
            support_multiplicity = sum(
                1
                for other in analysis.arena.plantations
                if other.id in analysis.connected_ids and chebyshev_distance(other.position, neighbor) <= analysis.arena.action_range
            )
            frontier_neighbors = sum(
                1
                for next_neighbor in cardinal_neighbors(neighbor)
                if clamp_to_map(next_neighbor, analysis.arena.width, analysis.arena.height)
                and _key(next_neighbor) not in occupied
            )
            progress_bonus = analysis.cell_by_position.get(position_key, 0)
            remaining_turns = ceil(max(0, 100 - progress_bonus) / 5) if progress_bonus < 100 else 0
            boosted = is_boosted_cell(neighbor)
            anchor_bonus = 60 if is_cardinal_neighbor(neighbor, analysis.main_plantation.position) else 0
            compact_handoff_bonus = 0
            if (
                analysis.opening_stage == "second_anchor"
                and analysis.stats.connected_plantations <= 2
                and any(is_cardinal_neighbor(neighbor, anchor) for anchor in analysis.hq_anchor_candidates[:2])
            ):
                compact_handoff_bonus = 150
            cycle_bonus = 30 if support_count >= 2 else 0
            hq_pressure_bonus = 45 if anchor_bonus and hq_turns and hq_turns <= 6 else 0
            reclaim_bonus = min(progress_bonus, 25) * 0.8
            lifetime_bonus = remaining_turns * 4
            mature_penalty = max(0, progress_bonus - 30) * 2.4
            if anchor_bonus:
                mature_penalty += max(0, progress_bonus - 20) * 3.2
            if remaining_turns and remaining_turns <= 6:
                mature_penalty += (7 - remaining_turns) * 18
            fragile_support_penalty = 0
            if support_nodes:
                expiring_supports = [
                    other
                    for other in support_nodes
                    if 0 < (other.turns_to_completion or 999) <= (expected_build_turns + 3)
                ]
                if support_count == 1 and anchor_bonus == 0 and expiring_supports:
                    # Do not open a fresh branch from a node that will disappear before the branch can become self-sustaining.
                    continue
                if support_count == 1 and anchor_bonus == 0:
                    sole_support_turns = support_nodes[0].turns_to_completion or 999
                    if sole_support_turns <= (expected_build_turns + 6):
                        fragile_support_penalty += (expected_build_turns + 7 - sole_support_turns) * 18
                elif len(expiring_supports) == support_count and anchor_bonus == 0:
                    fragile_support_penalty += 36
            depth_bonus = max(
                (
                    analysis.depth_by_id.get(other.id, 0)
                    for other in analysis.arena.plantations
                    if other.id in analysis.connected_ids and is_cardinal_neighbor(other.position, neighbor)
                ),
                default=0,
            ) * 9
            skinny_penalty = 20 if support_count == 1 and depth_bonus >= 18 and anchor_bonus == 0 else 0
            beaver_penalty = sum(max(0, 5 - chebyshev_distance(beaver.position, neighbor)) * 10 for beaver in analysis.arena.beavers)
            enemy_penalty = sum(max(0, 5 - chebyshev_distance(enemy.position, neighbor)) * 12 for enemy in analysis.arena.enemy)
            forecast_penalty = 0
            for forecast in analysis.arena.forecasts:
                if forecast.kind == "sandstorm" and forecast.position and forecast.radius is not None:
                    if chebyshev_distance(forecast.position, neighbor) <= forecast.radius + 1:
                        forecast_penalty += 18
                if forecast.kind == "earthquake" and (forecast.turns_until or 0) == 0:
                    forecast_penalty += 12
            stagnant_penalty = (memory.stagnant_streak(position_key) * 25) if memory else 0
            threatened = beaver_penalty > 0 or forecast_penalty > 0 or enemy_penalty > 0
            candidate_kind, candidate_reason = _candidate_reason(
                analysis=analysis,
                position=neighbor,
                boosted=boosted,
                support_count=support_count,
                progress_bonus=progress_bonus,
                remaining_turns=remaining_turns,
                threatened=threatened,
            )
            score = (
                100
                + anchor_bonus
                + hq_pressure_bonus
                + cycle_bonus
                + (120 if boosted else 0)
                + reclaim_bonus
                + lifetime_bonus
                + (support_count * 18)
                + (support_multiplicity * 8)
                + depth_bonus
                + (frontier_neighbors * 7)
                - beaver_penalty
                - enemy_penalty
                - forecast_penalty
                - stagnant_penalty
                - skinny_penalty
                - fragile_support_penalty
                - mature_penalty
            )
            if analysis.opening_stage == "seed_anchor":
                score += 120 if anchor_bonus else -80
            elif analysis.opening_stage == "second_anchor":
                if anchor_bonus:
                    score += 100
                elif compact_handoff_bonus:
                    score += compact_handoff_bonus
                else:
                    score -= 55
            elif analysis.opening_stage == "double_lane":
                score += 65 if support_count >= 2 else 0
            if analysis.current_mode == "rebase":
                score += 25 if anchor_bonus or support_count >= 2 else 0
            elif analysis.current_mode == "defense":
                score += 20 if support_count >= 2 else -15
            elif analysis.current_mode == "contested":
                score += 18 if boosted or threatened else 0
            elif analysis.current_mode == "raid":
                score -= 10 if support_count < 2 else 0

            existing = candidates.get(position_key)
            if existing is None or score > existing.score:
                candidates[position_key] = TargetCandidateView(
                    position=neighbor,
                    score=round(score, 2),
                    boosted=boosted,
                    support_count=support_count,
                    kind=candidate_kind,
                    reason=candidate_reason,
                    threatened=threatened,
                )

    return sorted(candidates.values(), key=lambda item: (-item.score, item.position.x, item.position.y))


def _build_alerts(analysis: ArenaAnalysis) -> list[AlertView]:
    alerts: list[AlertView] = []
    if analysis.main_plantation:
        turns_to_completion = analysis.main_plantation.turns_to_completion or 0
        if turns_to_completion <= 3:
            alerts.append(
                AlertView(
                    severity="danger",
                    title="HQ Relocation Critical",
                    description=f"The main plantation vanishes in {turns_to_completion} turns unless an adjacent anchor is ready.",
                )
            )
        elif turns_to_completion <= 6:
            alerts.append(
                AlertView(
                    severity="warn",
                    title="HQ Relocation Window",
                    description=f"The main plantation should start handoff prep now. Safe adjacent anchors: {len(analysis.hq_anchor_candidates)}.",
                )
            )

    isolated = [item for item in analysis.arena.plantations if item.id not in analysis.connected_ids]
    if isolated:
        alerts.append(
            AlertView(
                severity="warn",
                title="Isolated Branches",
                description=f"{len(isolated)} plantations are disconnected and degrading without score.",
            )
        )

    if analysis.stats.available_settlement_headroom <= 2:
        alerts.append(
            AlertView(
                severity="warn",
                title="Settlement Limit Pressure",
                description="Headroom is almost gone. Overbuilding can randomly delete an old node or the main.",
            )
        )

    if analysis.planner_memory and analysis.planner_memory.turns_without_assets >= 2:
        alerts.append(
            AlertView(
                severity="danger",
                title="Respawn Pressure",
                description=f"No visible plantations or constructions for {analysis.planner_memory.turns_without_assets} turns.",
            )
        )

    for forecast in analysis.arena.forecasts:
        if forecast.kind == "earthquake" and (forecast.turns_until or 0) <= 1:
            alerts.append(
                AlertView(
                    severity="warn",
                    title="Earthquake Forecast",
                    description="A quake is imminent. Only critical nodes and finishable builds should receive emergency resources.",
                )
            )
        if forecast.kind == "sandstorm" and forecast.forming:
            alerts.append(
                AlertView(
                    severity="info",
                    title="Sandstorm Forming",
                    description="A storm is about to cross the center line. Exposed frontier nodes should not be overcommitted.",
                )
            )

    return alerts


def _select_mode(analysis: ArenaAnalysis) -> str:
    if not analysis.arena.plantations and not analysis.arena.constructions:
        return "rebase"

    if analysis.main_plantation and len(analysis.connected_ids) <= 1:
        return "bootstrap"

    if analysis.main_plantation and (
        (analysis.main_plantation.turns_to_completion or 0) <= 3
        or analysis.main_plantation.hp <= 25
        or (len(analysis.hq_anchor_candidates) == 0 and not analysis.adjacent_hq_constructions)
    ):
        return "defense"

    nearby_enemy = any(
        chebyshev_distance(analysis.main_plantation.position, enemy.position) <= 8
        for enemy in analysis.arena.enemy
    ) if analysis.main_plantation else False
    contested_beaver = any(
        any(chebyshev_distance(enemy.position, beaver.position) <= 4 for enemy in analysis.arena.enemy)
        for beaver in analysis.arena.beavers
    )
    if nearby_enemy and contested_beaver:
        return "contested"
    if nearby_enemy and len(analysis.connected_ids) >= 3:
        return "raid"
    return "economy"


def _build_stats(analysis: ArenaAnalysis) -> BattlefieldStats:
    boosted_active = 0
    income = 0
    hq_remaining_turns = analysis.main_plantation.turns_to_completion if analysis.main_plantation else 0
    safe_hq_moves_count = len(analysis.hq_anchor_candidates)
    for plantation in analysis.arena.plantations:
        if plantation.id not in analysis.connected_ids:
            continue
        progress = analysis.cell_by_position.get(_key(plantation.position), 0)
        if progress >= 100:
            continue
        boosted = is_boosted_cell(plantation.position)
        if boosted:
            boosted_active += 1
        income += 75 if boosted else 50

    memory = analysis.planner_memory
    completion_rate = memory.completion_rate(analysis.arena.turn_no) if memory else 0.0
    expiration_rate = memory.expiration_rate(analysis.arena.turn_no) if memory else 0.0
    connected = len(analysis.connected_ids)
    construction_count = len(analysis.arena.constructions)
    idle_ratio = (
        round(max(0.0, (connected - min(connected, construction_count + 1)) / connected), 3) if connected else 0.0
    )
    congestion_ratio = (
        round(max(0.0, (construction_count - max(1, safe_hq_moves_count)) / max(1, connected)), 3)
        if connected
        else 0.0
    )

    return BattlefieldStats(
        connected_plantations=connected,
        isolated_plantations=max(0, len(analysis.arena.plantations) - connected),
        current_income_per_tick=income,
        boosted_active_cells=boosted_active,
        construction_count=construction_count,
        available_settlement_headroom=max(
            0,
            analysis.settlement_limit - len(analysis.arena.plantations) - len(analysis.arena.constructions),
        ),
        visible_beavers=len(analysis.arena.beavers),
        completion_rate_20=completion_rate,
        expiration_rate_20=expiration_rate,
        hq_remaining_turns=hq_remaining_turns or 0,
        safe_hq_moves_count=safe_hq_moves_count,
        idle_author_ratio=idle_ratio,
        output_congestion_ratio=congestion_ratio,
        current_mode=analysis.current_mode,
    )


def recommend_upgrade(analysis: ArenaAnalysis) -> UpgradeRecommendation | None:
    if analysis.arena.upgrades.points <= 0:
        return None

    repair_tier = analysis.tier_by_name.get("repair_power")
    signal_tier = analysis.tier_by_name.get("signal_range")
    settlement_tier = analysis.tier_by_name.get("settlement_limit")
    vision_tier = analysis.tier_by_name.get("vision_range")
    quake_tier = analysis.tier_by_name.get("earthquake_mitigation")
    beaver_tier = analysis.tier_by_name.get("beaver_damage_mitigation")
    decay_tier = analysis.tier_by_name.get("decay_mitigation")
    max_hp_tier = analysis.tier_by_name.get("max_hp")
    total_spent_points = sum(max(0, tier.current) for tier in analysis.arena.upgrades.tiers)
    connected_count = len(analysis.connected_ids)
    small_network = connected_count <= 3
    stable_network = connected_count >= 5 or analysis.stats.safe_hq_moves_count >= 2
    early_expansion = analysis.current_mode in {"bootstrap", "rebase"} or connected_count <= 4
    signal_need = (
        len(analysis.connected_ids) >= 4
        or analysis.stats.idle_author_ratio >= 0.25
        or analysis.current_mode == "rebase"
    )
    nearby_beavers = sum(
        1
        for beaver in analysis.arena.beavers
        if any(
            plantation.id in analysis.connected_ids and chebyshev_distance(plantation.position, beaver.position) <= 2
            for plantation in analysis.arena.plantations
        )
    )
    connected_plantations = [plantation for plantation in analysis.arena.plantations if plantation.id in analysis.connected_ids]

    def has_beaver_bypass_candidate(beaver_position: Coordinate) -> bool:
        return any(
            chebyshev_distance(candidate.position, beaver_position) >= 3
            and candidate.support_count >= 1
            for candidate in analysis.frontier_candidates
        )

    blocked_by_beavers = any(
        any(chebyshev_distance(plantation.position, beaver.position) <= 4 for plantation in connected_plantations)
        and not has_beaver_bypass_candidate(beaver.position)
        for beaver in analysis.arena.beavers
    )
    early_survivability_ready = (
        (max_hp_tier.current if max_hp_tier else 0) >= 3
        and (signal_tier.current if signal_tier else 0) >= 1
    )
    construction_pressure = (
        analysis.stats.construction_count > 0
        or analysis.stats.completion_rate_20 <= (analysis.stats.expiration_rate_20 + 0.15)
        or analysis.stats.hq_remaining_turns <= 8
    )
    stockpiled_points = analysis.arena.upgrades.points >= 2

    if repair_tier and repair_tier.current < min(repair_tier.max, 3):
        if (
            analysis.stats.available_settlement_headroom <= 0
            and settlement_tier
            and settlement_tier.current < settlement_tier.max
        ):
            return UpgradeRecommendation(
                name="settlement_limit",
                priority=109,
                reason="The colony is hard-capped on plantations. Buying settlement limit is the only allowed interruption to the opening construction ladder, because the next build progress would otherwise delete the oldest live base and can wipe the HQ chain.",
            )
        return UpgradeRecommendation(
            name="repair_power",
            priority=108,
            reason="Opening doctrine: spend every available early point on construction tempo until repair power reaches tier three. In this ruleset that is the direct way to make new bases finish before the current HQ tile disappears.",
        )

    if analysis.current_mode == "bootstrap" and repair_tier and repair_tier.current < min(repair_tier.max, 2):
        return UpgradeRecommendation(
            name="repair_power",
            priority=102,
            reason="Bootstrap mode needs raw build tempo first. Repair power also increases construction throughput, which is the core bottleneck when the colony only has one live anchor.",
        )

    if (
        analysis.current_mode == "bootstrap"
        and analysis.stats.construction_count > 0
        and analysis.earthquake_turns_until is not None
        and analysis.earthquake_turns_until <= 4
        and quake_tier
        and quake_tier.current < quake_tier.max
    ):
        return UpgradeRecommendation(
            name="earthquake_mitigation",
            priority=101,
            reason="A bootstrap anchor is still under construction and a quake is imminent. Earthquake mitigation applies to unfinished builds, while max HP does not, so protecting the build lane is the highest-value spend.",
        )

    if (
        analysis.stats.connected_plantations <= 2
        and analysis.current_mode != "bootstrap"
        and analysis.stats.construction_count > 0
        and analysis.earthquake_turns_until is not None
        and analysis.earthquake_turns_until <= 2
        and quake_tier
        and quake_tier.current < quake_tier.max
    ):
        return UpgradeRecommendation(
            name="earthquake_mitigation",
            priority=100,
            reason="A compact post-handoff core is still feeding the next anchor and a quake lands before the build lane is stable. Earthquake mitigation is worth more than generic routing or economy upgrades because it protects the unfinished third-node conversion directly.",
        )

    if (
        blocked_by_beavers
        and connected_count < 5
        and beaver_tier
        and beaver_tier.current < min(beaver_tier.max, 1)
        and repair_tier
        and repair_tier.current >= min(repair_tier.max, 3)
    ):
        return UpgradeRecommendation(
            name="beaver_damage_mitigation",
            priority=100,
            reason="The small network is already pinned against a beaver lane and there is no clean bypass candidate. Buy one beaver mitigation tier before forcing the attack so fresh anchors and the handoff core do not melt on contact.",
        )

    if (
        max_hp_tier
        and max_hp_tier.current < min(max_hp_tier.max, 5)
        and repair_tier
        and repair_tier.current >= min(repair_tier.max, 3)
        and 3 <= total_spent_points < 8
    ):
        if (
            analysis.stats.available_settlement_headroom <= 1
            and settlement_tier
            and settlement_tier.current < settlement_tier.max
        ):
            return UpgradeRecommendation(
                name="settlement_limit",
                priority=107,
                reason="The early fixed ladder only breaks for hard settlement-limit pressure. Buying limit now is safer than letting the oldest node, including a potential HQ lane, get deleted on the next construction progress.",
            )
        return UpgradeRecommendation(
            name="max_hp",
            priority=106,
            reason="After the first three construction tiers, the next opening points should harden the rolling HQ handoff chain. Early max HP is better than signal or generic mitigation until the compact core stops collapsing back to a single live plantation.",
        )

    if (
        early_expansion
        and construction_pressure
        and repair_tier
        and repair_tier.current >= min(repair_tier.max, 3)
        and max_hp_tier
        and max_hp_tier.current >= min(max_hp_tier.max, 5)
        and decay_tier
        and decay_tier.current < min(decay_tier.max, 1)
    ):
        return UpgradeRecommendation(
            name="decay_mitigation",
            priority=105,
            reason="Construction speed is already capped, so the next best build-lane boost is preventing unfinished anchors from sliding backwards. Buy the first decay tier before extra signal range once repair power and max HP are both online.",
        )

    if analysis.current_mode == "bootstrap" and max_hp_tier and max_hp_tier.current < 1:
        return UpgradeRecommendation(
            name="max_hp",
            priority=100,
            reason="A fragile early HQ lane loses too much tempo to beavers and incidental pressure. One HP tier makes the first anchor transfer less brittle.",
        )

    if (
        analysis.current_mode == "bootstrap"
        and analysis.stats.construction_count > 0
        and repair_tier
        and repair_tier.current < repair_tier.max
    ):
        return UpgradeRecommendation(
            name="repair_power",
            priority=99,
            reason="Bootstrap is still feeding a live anchor build. Finishing the construction tempo line before routing upgrades shortens the 1->2 plantation transition and reduces failed HQ handoff windows.",
        )

    if analysis.current_mode == "bootstrap" and signal_tier and signal_tier.current < 1:
        return UpgradeRecommendation(
            name="signal_range",
            priority=98,
            reason="Signal range unlocks more valid output points around the HQ lane and reduces early routing failures while the network is still tiny.",
        )

    if (
        analysis.current_mode == "bootstrap"
        and analysis.stats.construction_count > 0
        and max_hp_tier
        and max_hp_tier.current < min(max_hp_tier.max, 4)
    ):
        return UpgradeRecommendation(
            name="max_hp",
            priority=97,
            reason="The first live anchor is still being built and the colony is not out of the brittle handoff phase yet. Another HP tier is worth more than secondary routing or generic decay protection because it most directly reduces HQ-loss risk during the 1->2 transition.",
        )

    if early_expansion and construction_pressure and early_survivability_ready and decay_tier and decay_tier.current < 1:
        return UpgradeRecommendation(
            name="decay_mitigation",
            priority=97,
            reason="The opening is still fragile and unfinished builds are missing turns. One decay tier keeps adjacent anchors from sliding backwards before they can convert into real plantations.",
        )

    if analysis.earthquake_now and quake_tier and quake_tier.current < quake_tier.max:
        return UpgradeRecommendation(
            name="earthquake_mitigation",
            priority=100,
            reason="A quake lands this turn. Immediate mitigation is the highest-value way to preserve active anchors and unfinished builds.",
        )

    if (
        analysis.stats.available_settlement_headroom <= 2
        and settlement_tier
        and settlement_tier.current < settlement_tier.max
    ):
        return UpgradeRecommendation(
            name="settlement_limit",
            priority=96,
            reason="The network is too close to the cap. Extra headroom avoids deleting old nodes or the HQ by mistake.",
        )

    if analysis.current_mode == "defense" and max_hp_tier and max_hp_tier.current < max_hp_tier.max:
        return UpgradeRecommendation(
            name="max_hp",
            priority=92,
            reason="The core is under pressure. More HP raises the odds that the HQ lane survives long enough to relocate and keep scoring.",
        )

    if small_network and repair_tier and repair_tier.current < repair_tier.max:
        return UpgradeRecommendation(
            name="repair_power",
            priority=94,
            reason="A tiny network still wins or loses on raw construction tempo. Maxing repair power early keeps the rolling carpet from falling behind expiration.",
        )

    if small_network and max_hp_tier and max_hp_tier.current < min(max_hp_tier.max, 3):
        return UpgradeRecommendation(
            name="max_hp",
            priority=92,
            reason="With only a few live plantations, each node matters too much. Early HP buys time for relocations and protects fresh anchors from incidental damage.",
        )

    if small_network and signal_tier and signal_tier.current < min(signal_tier.max, 2):
        return UpgradeRecommendation(
            name="signal_range",
            priority=90,
            reason="A second signal tier opens more legal outputs while the lattice is still compact and makes dual-support builds easier to route.",
        )

    if connected_count >= 5 and early_expansion and nearby_beavers >= 1 and beaver_tier and beaver_tier.current < 1:
        return UpgradeRecommendation(
            name="beaver_damage_mitigation",
            priority=89,
            reason="The opening is drifting toward active beaver lanes. One mitigation tier protects fresh anchors and unfinished builds while we set up a perimeter instead of diving in early.",
        )

    if analysis.earthquake_soon and quake_tier and quake_tier.current < quake_tier.max:
        return UpgradeRecommendation(
            name="earthquake_mitigation",
            priority=90,
            reason="An imminent quake makes shallow builds and bridges fragile. Mitigation protects the rolling carpet from tempo loss.",
        )

    if early_expansion and max_hp_tier and max_hp_tier.current < min(max_hp_tier.max, 4):
        return UpgradeRecommendation(
            name="max_hp",
            priority=89,
            reason="The opening is still thin and every future HQ anchor inherits the global HP tier only after it completes. Pushing one more HP tier before generic mitigation makes relocations and early handoffs much less brittle.",
        )

    if (
        early_expansion
        and construction_pressure
        and early_survivability_ready
        and decay_tier
        and decay_tier.current < min(decay_tier.max, 2)
    ):
        return UpgradeRecommendation(
            name="decay_mitigation",
            priority=88,
            reason="The network is still losing too much tempo to stalled construction. Extra decay mitigation is worth more than hoarding points while the backbone is underbuilt.",
        )

    if connected_count >= 5 and nearby_beavers >= 2 and beaver_tier and beaver_tier.current < beaver_tier.max:
        return UpgradeRecommendation(
            name="beaver_damage_mitigation",
            priority=86,
            reason="Multiple beaver lairs are already touching productive cells. Mitigation keeps the economic lane alive while we expand.",
        )

    if repair_tier and repair_tier.current < min(repair_tier.max, 2):
        return UpgradeRecommendation(
            name="repair_power",
            priority=84,
            reason="Construction tempo is the real economic multiplier in DatsSol. Early repair power improves both repairs and building, which keeps completion rate above expiration rate.",
        )

    if signal_need and signal_tier and signal_tier.current < signal_tier.max:
        return UpgradeRecommendation(
            name="signal_range",
            priority=82,
            reason="Signal range unlocks more distinct outputs per target and makes the backbone less dependent on a single relay.",
        )

    if max_hp_tier and max_hp_tier.current < min(max_hp_tier.max, 2):
        return UpgradeRecommendation(
            name="max_hp",
            priority=78,
            reason="Early max HP gives the network more slack against beavers, sandstorms and incidental raids while the carpet is still thin.",
        )

    if repair_tier and repair_tier.current < repair_tier.max:
        return UpgradeRecommendation(
            name="repair_power",
            priority=76,
            reason="More repair power still compounds construction tempo on the backbone and makes emergency fortification cheaper.",
        )

    if nearby_beavers >= 1 and beaver_tier and beaver_tier.current < beaver_tier.max:
        return UpgradeRecommendation(
            name="beaver_damage_mitigation",
            priority=74,
            reason="Nearby beavers keep taxing fresh anchors. Mitigation lowers the tempo penalty of expanding through active lairs.",
        )

    if vision_tier and vision_tier.current < vision_tier.max and (connected_count >= 6 or (analysis.stats.visible_beavers > 0 and connected_count >= 4)):
        return UpgradeRecommendation(
            name="vision_range",
            priority=70,
            reason="More vision improves beaver timing, raid detection and rebase safety once the network leaves the spawn corridor.",
        )

    if decay_tier and decay_tier.current < decay_tier.max and stable_network and (
        analysis.stats.construction_count > 0 or analysis.stats.isolated_plantations > 0
    ):
        return UpgradeRecommendation(
            name="decay_mitigation",
            priority=64,
            reason="Decay mitigation buys time for unfinished or temporarily disconnected branches to recover instead of collapsing outright.",
        )

    if vision_tier and vision_tier.current < vision_tier.max and stable_network:
        return UpgradeRecommendation(
            name="vision_range",
            priority=54,
            reason="More vision improves rebase safety, beaver timing and enemy bridge discovery.",
        )

    if decay_tier and decay_tier.current < decay_tier.max and stable_network:
        return UpgradeRecommendation(
            name="decay_mitigation",
            priority=52,
            reason="Decay mitigation buys recovery time when a build misses a turn or a branch loses connectivity.",
        )

    fallback_candidates: list[tuple[str, PlantationUpgradeTier | None, bool, int, str]] = [
        (
            "decay_mitigation",
            decay_tier,
            early_expansion or construction_pressure or stockpiled_points,
            48,
            "Unused upgrade points are low-EV while the build lane is still fragile. Decay mitigation is the safest generic tempo upgrade when construction misses a tick.",
        ),
        (
            "max_hp",
            max_hp_tier,
            early_expansion or analysis.current_mode == "defense",
            46,
            "Extra HP is still valuable while the HQ lane is thin. Spending the point now is better than stockpiling it for a perfect moment.",
        ),
        (
            "earthquake_mitigation",
            quake_tier,
            analysis.earthquake_soon or stockpiled_points,
            44,
            "Quake mitigation is a clean sink for spare points once core build tempo is online and it directly protects unfinished construction.",
        ),
        (
            "beaver_damage_mitigation",
            beaver_tier,
            nearby_beavers > 0 or stockpiled_points,
            42,
            "Beaver mitigation keeps future expansion lanes and staging anchors alive longer than idle points ever will.",
        ),
        (
            "signal_range",
            signal_tier,
            signal_need or stockpiled_points,
            40,
            "If no higher-leverage tier is available, more signal range still improves routing freedom and output diversity.",
        ),
        (
            "vision_range",
            vision_tier,
            connected_count >= 6 or stockpiled_points,
            36,
            "Vision is not an opening priority, but it is still better than floating points once the backbone exists.",
        ),
        (
            "settlement_limit",
            settlement_tier,
            analysis.stats.available_settlement_headroom <= 4 or stockpiled_points,
            34,
            "Extra settlement headroom is a low-drama fallback that prevents accidental self-deletes once the carpet starts widening.",
        ),
    ]
    for name, tier, condition, priority, reason in fallback_candidates:
        if condition and tier and tier.current < tier.max:
            return UpgradeRecommendation(name=name, priority=priority, reason=reason)

    return None


def analyze_arena(arena: ArenaObservation, planner_memory: PlannerMemory | None = None) -> ArenaAnalysis:
    tier_by_name = _tier_map(arena)
    arena = arena.model_copy(update={"constructions": _dedupe_constructions(arena)})
    plantations = [item.model_copy(deep=True) for item in arena.plantations]
    constructions = [item.model_copy(deep=True) for item in arena.constructions]
    plantation_by_id = {item.id: item for item in plantations}
    plantation_by_position = {_key(item.position): item for item in plantations}
    construction_by_position = {_key(item.position): item for item in constructions}
    main_plantation = next((item for item in plantations if item.is_main), None)
    connected_ids, network_edges, adjacency, depth_by_id = _build_connected_component(plantations, main_plantation)
    cell_by_position, cell_turns_by_position = _cell_progress(arena)
    construction_positions, enemy_positions, beaver_positions, mountain_positions = _occupied_positions(arena)
    articulation_ids = _articulation_points(connected_ids, adjacency) if connected_ids else set()
    critical_positions = {_key(plantation_by_id[item_id].position) for item_id in articulation_ids}

    for plantation in plantations:
        position_key = _key(plantation.position)
        progress = cell_by_position.get(position_key, 0)
        plantation.terraform_progress = progress
        plantation.turns_until_cell_degradation = cell_turns_by_position.get(position_key)
        plantation.is_boosted_cell = is_boosted_cell(plantation.position)
        plantation.connected = plantation.id in connected_ids
        plantation.turns_to_completion = ceil(max(0, 100 - progress) / 5) if progress < 100 else 0
        plantation.projected_income_per_turn = (
            75 if plantation.connected and plantation.is_boosted_cell else 50 if plantation.connected else 0
        )
        if plantation.is_main:
            plantation.role = "main"
        elif plantation.id in articulation_ids:
            plantation.role = "bridge"
        elif plantation.turns_to_completion is not None and plantation.turns_to_completion <= 4:
            plantation.role = "handoff"
        elif plantation.is_boosted_cell:
            plantation.role = "boosted"
        else:
            plantation.role = "relay"

    arena = arena.model_copy(update={"plantations": plantations, "constructions": constructions})

    settlement_limit = 30 + _tier_value(tier_by_name, "settlement_limit")
    signal_range = 3 + _tier_value(tier_by_name, "signal_range")
    vision_range = 3 + (_tier_value(tier_by_name, "vision_range") * 2)
    repair_tier = _tier_value(tier_by_name, "repair_power")
    construction_power = 5 + repair_tier
    repair_power = 5 + repair_tier
    sabotage_power = 5
    beaver_attack_power = 5
    decay_speed = max(0, 10 - (_tier_value(tier_by_name, "decay_mitigation") * 2))
    earthquake_mitigation = _tier_value(tier_by_name, "earthquake_mitigation") * 2
    beaver_damage_mitigation = _tier_value(tier_by_name, "beaver_damage_mitigation") * 2
    earthquake_turns_until = min(
        (forecast.turns_until for forecast in arena.forecasts if forecast.kind == "earthquake" and forecast.turns_until is not None),
        default=None,
    )

    analysis = ArenaAnalysis(
        arena=arena,
        tier_by_name=tier_by_name,
        main_plantation=plantation_by_id.get(main_plantation.id) if main_plantation else None,
        plantation_by_id=plantation_by_id,
        plantation_by_position=plantation_by_position,
        construction_by_position=construction_by_position,
        cell_by_position=cell_by_position,
        cell_turns_by_position=cell_turns_by_position,
        construction_positions=construction_positions,
        enemy_positions=enemy_positions,
        beaver_positions=beaver_positions,
        mountain_positions=mountain_positions,
        connected_ids=connected_ids,
        articulation_ids=articulation_ids,
        critical_positions=critical_positions,
        depth_by_id=depth_by_id,
        network_edges=network_edges,
        frontier_candidates=[],
        alerts=[],
        stats=BattlefieldStats(),
        settlement_limit=settlement_limit,
        signal_range=signal_range,
        vision_range=vision_range,
        construction_power=construction_power,
        repair_power=repair_power,
        sabotage_power=sabotage_power,
        beaver_attack_power=beaver_attack_power,
        decay_speed=decay_speed,
        earthquake_mitigation=earthquake_mitigation,
        beaver_damage_mitigation=beaver_damage_mitigation,
        earthquake_turns_until=earthquake_turns_until,
        earthquake_now=earthquake_turns_until == 0,
        earthquake_soon=earthquake_turns_until is not None and earthquake_turns_until <= 1,
        planner_memory=planner_memory,
    )
    if analysis.main_plantation is not None:
        analysis.adjacent_hq_constructions = [
            construction
            for construction in constructions
            if is_cardinal_neighbor(construction.position, analysis.main_plantation.position)
        ]
    analysis.hq_anchor_candidates = _safe_hq_moves(analysis)
    analysis.current_mode = _select_mode(analysis)
    analysis.opening_stage = _opening_stage(analysis)
    analysis.frontier_candidates = _build_frontier_candidates(analysis)
    analysis.stats = _build_stats(analysis)
    analysis.alerts = _build_alerts(analysis)
    analysis.highlights = [
        f"mode: {analysis.current_mode}",
        f"opening stage: {analysis.opening_stage}",
        f"completion/expiration tempo: {analysis.stats.completion_rate_20:.2f}/{analysis.stats.expiration_rate_20:.2f}",
        f"hq remaining turns: {analysis.stats.hq_remaining_turns}",
        f"safe hq anchors: {analysis.stats.safe_hq_moves_count}",
        f"frontier targets scored: {len(analysis.frontier_candidates)}",
    ]
    return analysis
