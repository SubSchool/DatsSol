from __future__ import annotations

from math import ceil
from uuid import uuid4

from app.planning.analyze import ArenaAnalysis, recommend_upgrade
from app.planning.geometry import cardinal_neighbors, chebyshev_distance, clamp_to_map, is_cardinal_neighbor, within_square_radius
from app.schemas.game import (
    Coordinate,
    ConstructionView,
    ManualDirective,
    RelocateMainPlanView,
    StrategicIntentView,
    StrategyWeights,
    UpgradeRecommendation,
)


def _intent_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _position_key(position: Coordinate) -> tuple[int, int]:
    return (position.x, position.y)


def _connected_plantations(analysis: ArenaAnalysis):
    return [plantation for plantation in analysis.arena.plantations if plantation.id in analysis.connected_ids]


def _strict_anchor_mode(analysis: ArenaAnalysis) -> bool:
    connected = analysis.stats.connected_plantations
    if analysis.opening_stage == "seed_anchor":
        return True
    if analysis.opening_stage == "second_anchor":
        return len(analysis.hq_anchor_candidates) < 1
    return analysis.main_plantation is not None and len(analysis.hq_anchor_candidates) < 1 and connected <= 2


def _connected_cardinal_support_count(analysis: ArenaAnalysis, position: Coordinate) -> int:
    support_count = 0
    for neighbor in cardinal_neighbors(position):
        plantation = analysis.plantation_by_position.get(_position_key(neighbor))
        if plantation and plantation.id in analysis.connected_ids:
            support_count += 1
    return support_count


def _construction_stabilizes_hq_route(analysis: ArenaAnalysis, position: Coordinate) -> bool:
    if analysis.main_plantation and is_cardinal_neighbor(position, analysis.main_plantation.position):
        return True
    return _connected_cardinal_support_count(analysis, position) >= 2


def _legal_exit_count(analysis: ArenaAnalysis, target: Coordinate) -> int:
    return sum(
        1
        for plantation in analysis.arena.plantations
        if plantation.id in analysis.connected_ids
        and within_square_radius(plantation.position, target, analysis.arena.action_range)
    )


def _build_contributor_budget(
    analysis: ArenaAnalysis,
    target: Coordinate,
    preferred_count: int,
    *,
    baseline: int = 1,
    urgent: bool = False,
) -> int:
    if preferred_count <= 0:
        return 0

    legal_exits = max(1, _legal_exit_count(analysis, target))
    connected = analysis.stats.connected_plantations

    if connected <= 2:
        contributors_per_exit = 5 if urgent else 4
    elif connected <= 4:
        contributors_per_exit = 4 if urgent else 3
    elif connected <= 6:
        contributors_per_exit = 3 if urgent else 2
    else:
        contributors_per_exit = 2 if urgent else 1

    if connected <= 2:
        hard_cap = 8 if urgent else 6
    else:
        hard_cap = 6 if urgent else 5 if connected <= 6 else 4
    desired = max(baseline, min(hard_cap, legal_exits * contributors_per_exit))
    return min(preferred_count, max(1, desired))


def _beaver_metrics_for_position(
    analysis: ArenaAnalysis,
    position: Coordinate,
) -> dict[str, int | bool | Coordinate] | None:
    if not analysis.arena.beavers:
        return None

    connected = _connected_plantations(analysis)
    best: dict[str, int | bool | Coordinate] | None = None
    for beaver in analysis.arena.beavers:
        distance = chebyshev_distance(position, beaver.position)
        support_nodes = 0
        perimeter_nodes = 0
        strike_nodes = 0
        for plantation in connected:
            plant_distance = chebyshev_distance(plantation.position, beaver.position)
            if plant_distance <= 5:
                support_nodes += 1
            if plant_distance <= 2:
                strike_nodes += 1
            if 3 <= plant_distance <= 4:
                perimeter_nodes += 1
        perimeter_ready = perimeter_nodes >= 3 or (perimeter_nodes >= 2 and support_nodes >= 4)
        metrics = {
            "distance": distance,
            "support_nodes": support_nodes,
            "perimeter_nodes": perimeter_nodes,
            "strike_nodes": strike_nodes,
            "perimeter_ready": perimeter_ready,
            "beaver_position": beaver.position,
        }
        if best is None:
            best = metrics
            continue
        if (
            distance < int(best["distance"])
            or (
                distance == int(best["distance"])
                and perimeter_nodes > int(best["perimeter_nodes"])
            )
        ):
            best = metrics
    return best


def _scored_build_candidate(
    analysis: ArenaAnalysis,
    candidate,
    weights: StrategyWeights,
) -> float:
    score = candidate.score * (1.0 + weights.expansion_bias * 0.2)
    score += max(0, candidate.support_count - 1) * (18 + (weights.support_bias * 18))
    if candidate.boosted:
        score += 30 * weights.boosted_cell_bias
    if analysis.stats.connected_plantations <= 3 and candidate.kind == "relay":
        score += 34
    if analysis.opening_stage == "double_lane" and candidate.support_count >= 2:
        score += 28

    beaver_campaign_ready = analysis.stats.connected_plantations >= 5
    beaver_metrics = _beaver_metrics_for_position(analysis, candidate.position)
    if beaver_metrics is not None:
        distance = int(beaver_metrics["distance"])
        support_nodes = int(beaver_metrics["support_nodes"])
        perimeter_nodes = int(beaver_metrics["perimeter_nodes"])
        strike_nodes = int(beaver_metrics["strike_nodes"])
        perimeter_ready = bool(beaver_metrics["perimeter_ready"])
        if distance <= 1:
            score -= 180
        elif distance == 2 and beaver_campaign_ready:
            score += 44 + (strike_nodes * 12) if perimeter_ready else -120
        elif distance in {3, 4} and beaver_campaign_ready:
            score += 92 + (support_nodes * 6) + (22 if candidate.support_count >= 2 else 0)
            if perimeter_nodes < 4:
                score += 12
        elif distance == 5 and beaver_campaign_ready:
            score += 26 + (10 if candidate.support_count >= 2 else 0)
        elif not beaver_campaign_ready and distance in {3, 4}:
            score += 58 + (support_nodes * 4) + (18 if candidate.support_count >= 2 else 0)
        elif not beaver_campaign_ready and distance >= 5 and candidate.support_count >= 1:
            score += 12
        if candidate.threatened and distance <= 2 and (not perimeter_ready or not beaver_campaign_ready):
            score -= 36

    return round(score, 2)


def _has_beaver_bypass_candidate(analysis: ArenaAnalysis, beaver_position: Coordinate) -> bool:
    return any(
        chebyshev_distance(candidate.position, beaver_position) >= 3 and candidate.support_count >= 1
        for candidate in analysis.frontier_candidates
    )


def _serialize_active_construction_lane(analysis: ArenaAnalysis) -> bool:
    if not analysis.arena.constructions:
        return False
    if analysis.current_mode in {"bootstrap", "rebase"}:
        return True
    if analysis.stats.connected_plantations <= 5:
        return True
    if analysis.stats.visible_beavers > 0:
        return True
    return False


def _small_network_beaver_safe_build(analysis: ArenaAnalysis, position: Coordinate) -> bool:
    if analysis.stats.connected_plantations >= 5:
        return True
    beaver_metrics = _beaver_metrics_for_position(analysis, position)
    if beaver_metrics is None:
        return True
    return int(beaver_metrics["distance"]) >= 3


def _preferred_authors_for_target(
    analysis: ArenaAnalysis,
    target: Coordinate,
    limit: int = 6,
    purpose: str = "build",
) -> list[str]:
    candidates = [plantation for plantation in analysis.arena.plantations if plantation.id in analysis.connected_ids]

    def score(item) -> tuple[float, ...]:
        distance = chebyshev_distance(item.position, target)
        main_penalty = 1000 if item.is_main and purpose != "repair" else 420 if item.is_main else 0
        articulation_penalty = 420 if item.id in analysis.articulation_ids and purpose != "repair" else 140 if item.id in analysis.articulation_ids else 0
        low_hp_penalty = max(0, 36 - item.hp) * (12 if purpose != "repair" else 5)
        expiring_penalty = 0
        if item.turns_to_completion is not None:
            expiring_penalty = max(0, 10 - item.turns_to_completion) * (28 if purpose != "repair" else 10)
        role_bonus = -35 if item.role in {"leaf", "relay"} and purpose != "repair" else 0
        immunity_bonus = -10 if item.immunity_until_turn > analysis.arena.turn_no else 0
        return (
            distance * 100 + main_penalty + articulation_penalty + low_hp_penalty + expiring_penalty + role_bonus + immunity_bonus,
            distance,
            -item.hp,
        )

    candidates.sort(key=score)
    return [item.id for item in candidates[:limit]]


def _bootstrap_target(analysis: ArenaAnalysis) -> Coordinate | None:
    main = analysis.main_plantation
    if main is None:
        return None

    occupied = (
        set(analysis.plantation_by_position.keys())
        | analysis.enemy_positions
        | analysis.beaver_positions
        | analysis.mountain_positions
    )
    memory = analysis.planner_memory
    locked_key = memory.bootstrap_target_for(main.position) if memory else None
    if locked_key:
        if locked_key in analysis.construction_by_position:
            return Coordinate(x=locked_key[0], y=locked_key[1])
        if locked_key not in occupied:
            return Coordinate(x=locked_key[0], y=locked_key[1])
        if memory:
            memory.clear_bootstrap_target()

    if analysis.adjacent_hq_constructions:
        best = max(
            analysis.adjacent_hq_constructions,
            key=lambda item: (item.progress, -analysis.cell_by_position.get(_position_key(item.position), 0)),
        )
        if memory:
            memory.lock_bootstrap_target(main.position, best.position)
        return best.position

    reachable_constructions = [
        construction
        for construction in analysis.arena.constructions
        if construction.progress >= 20
        and _construction_stabilizes_hq_route(analysis, construction.position)
        and _preferred_authors_for_target(analysis, construction.position, limit=1, purpose="finish_build")
    ]
    if reachable_constructions:
        best = max(
            reachable_constructions,
            key=lambda item: (
                item.progress,
                -chebyshev_distance(main.position, item.position),
                analysis.cell_by_position.get(_position_key(item.position), 0),
            ),
        )
        if memory:
            memory.lock_bootstrap_target(main.position, best.position)
        return best.position

    adjacent_frontier = [
        candidate
        for candidate in analysis.frontier_candidates
        if is_cardinal_neighbor(candidate.position, main.position)
    ]
    if adjacent_frontier:
        target = adjacent_frontier[0].position
        if memory:
            memory.lock_bootstrap_target(main.position, target)
        return target

    fallback_positions: list[Coordinate] = []
    for neighbor in cardinal_neighbors(main.position):
        key = _position_key(neighbor)
        if not clamp_to_map(neighbor, analysis.arena.width, analysis.arena.height):
            continue
        if key in occupied or key in analysis.construction_positions:
            continue
        fallback_positions.append(neighbor)
    fallback_positions.sort(
        key=lambda position: (
            analysis.cell_by_position.get(_position_key(position), 0),
            0 if (position.x % 7 == 0 and position.y % 7 == 0) else 1,
            position.x,
            position.y,
        )
    )
    if fallback_positions and memory:
        memory.lock_bootstrap_target(main.position, fallback_positions[0])
    return fallback_positions[0] if fallback_positions else None


def _adjacent_finishable_hq_construction(analysis: ArenaAnalysis) -> ConstructionView | None:
    best: ConstructionView | None = None
    best_score = -1
    for construction in analysis.adjacent_hq_constructions:
        preferred_authors = _preferred_authors_for_target(analysis, construction.position, limit=10, purpose="finish_build")
        if not preferred_authors:
            continue
        remaining = max(0, 50 - construction.progress)
        if remaining <= 0:
            continue
        estimated_burst = len(preferred_authors) * analysis.construction_power
        if estimated_burst < remaining:
            continue
        score = construction.progress
        if score > best_score:
            best = construction
            best_score = score
    return best


def _fresh_adjacent_handoff_anchor(analysis: ArenaAnalysis) -> object | None:
    main = analysis.main_plantation
    if main is None:
        return None
    anchors = [
        plantation
        for plantation in analysis.arena.plantations
        if plantation.id in analysis.connected_ids
        and plantation.id != main.id
        and is_cardinal_neighbor(main.position, plantation.position)
        and plantation.turns_to_completion is not None
        and plantation.turns_to_completion > (analysis.stats.hq_remaining_turns or main.turns_to_completion or 0)
        and plantation.terraform_progress <= 10
    ]
    if not anchors:
        return None
    anchors.sort(
        key=lambda plantation: (
            plantation.turns_to_completion or 0,
            -plantation.terraform_progress,
            plantation.hp,
        ),
        reverse=True,
    )
    return anchors[0]


def decide_main_relocation(analysis: ArenaAnalysis, weights: StrategyWeights) -> RelocateMainPlanView | None:
    main = analysis.main_plantation
    if main is None:
        return None

    turns_to_completion = analysis.stats.hq_remaining_turns or main.turns_to_completion or 0
    finishable_anchor = _adjacent_finishable_hq_construction(analysis)
    if finishable_anchor is not None and turns_to_completion <= 3:
        return RelocateMainPlanView(
            from_position=main.position,
            to_position=finishable_anchor.position,
            urgency="critical",
            reason="The current HQ tile is about to finish. This adjacent construction can be completed in the same turn, so the HQ should hand off immediately after build resolution.",
        )

    fresh_handoff_anchor = _fresh_adjacent_handoff_anchor(analysis)
    if fresh_handoff_anchor is not None and analysis.stats.connected_plantations <= 2:
        return RelocateMainPlanView(
            from_position=main.position,
            to_position=fresh_handoff_anchor.position,
            urgency="critical" if turns_to_completion <= 8 else "high",
            reason="A fresh adjacent anchor has already completed and has a longer lifetime than the current HQ tile. Hand off immediately before opening the next build so the colony stops dying with a valid replacement next door.",
        )

    compact_existing_anchor = next(
        (
            plantation
            for plantation in sorted(
                (
                    plantation
                    for plantation in analysis.arena.plantations
                    if plantation.id in analysis.connected_ids
                    and plantation.id != main.id
                    and is_cardinal_neighbor(main.position, plantation.position)
                ),
                key=lambda plantation: (
                    plantation.turns_to_completion or 0,
                    -plantation.hp,
                    len(
                        [
                            other
                            for other in analysis.arena.plantations
                            if other.id in analysis.connected_ids
                            and other.id != plantation.id
                            and is_cardinal_neighbor(other.position, plantation.position)
                        ]
                    ),
                ),
                reverse=True,
            )
        ),
        None,
    )
    compact_anchor_turns = compact_existing_anchor.turns_to_completion if compact_existing_anchor is not None else None
    compact_anchor_progress = compact_existing_anchor.terraform_progress if compact_existing_anchor is not None else None
    compact_core_handoff = analysis.stats.connected_plantations <= 2
    fresh_compact_anchor = compact_core_handoff and compact_anchor_progress is not None and compact_anchor_progress <= 10
    compact_trigger_turns = 18 if fresh_compact_anchor else (10 if compact_core_handoff else 12)
    compact_turn_advantage = 2 if fresh_compact_anchor else 4
    compact_relocation_ready = False
    if (
        compact_existing_anchor is not None
        and analysis.stats.connected_plantations <= 4
        and compact_anchor_turns is not None
        and compact_anchor_turns > turns_to_completion
    ):
        if compact_core_handoff:
            compact_relocation_ready = (
                turns_to_completion <= compact_trigger_turns
                and compact_anchor_turns >= (turns_to_completion + compact_turn_advantage)
            )
        else:
            compact_relocation_ready = (
                turns_to_completion <= compact_trigger_turns
                or compact_anchor_turns >= (turns_to_completion + compact_turn_advantage)
            )
    if compact_relocation_ready:
        return RelocateMainPlanView(
            from_position=main.position,
            to_position=compact_existing_anchor.position,
            urgency="critical" if turns_to_completion <= 4 or main.hp <= 20 else "high",
            reason="A compact core already has a live adjacent handoff anchor with more remaining lifetime than the current HQ tile. Move early instead of risking another self-inflicted HQ wipe while waiting for the last possible window.",
        )

    trigger_turns = 4 if weights.hq_safety_margin >= 0.7 else 3
    if len(analysis.hq_anchor_candidates) <= 1:
        trigger_turns += 1
    if analysis.current_mode in {"bootstrap", "defense", "rebase"}:
        trigger_turns += 1
    if turns_to_completion > trigger_turns and main.hp > 25:
        return None

    if not analysis.hq_anchor_candidates:
        return None

    target = analysis.hq_anchor_candidates[0]
    urgency = "critical" if turns_to_completion <= 2 or main.hp <= 20 else "high"
    return RelocateMainPlanView(
        from_position=main.position,
        to_position=target,
        urgency=urgency,
        reason="Move the HQ before its tile finishes or the core becomes too fragile to keep the network alive.",
    )


def decide_bootstrap_intents(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    main = analysis.main_plantation
    if main is None:
        return []

    needs_anchor = analysis.current_mode == "bootstrap" or (
        (analysis.stats.hq_remaining_turns or 0) <= 6 and not analysis.hq_anchor_candidates
    )
    if not needs_anchor:
        return []

    target = _bootstrap_target(analysis)
    if target is None:
        return []

    target_key = _position_key(target)
    existing_construction = analysis.construction_by_position.get(target_key)
    if existing_construction is not None:
        remaining = max(0, 50 - existing_construction.progress)
        preferred_authors = _preferred_authors_for_target(analysis, target, limit=10, purpose="finish_build")
        if not preferred_authors:
            return []
        can_finish_now = (len(preferred_authors) * analysis.construction_power) >= remaining
        desired_contributors = _build_contributor_budget(
            analysis,
            target,
            len(preferred_authors),
            baseline=max(1, ceil(remaining / max(1, analysis.construction_power))),
            urgent=True,
        )
        priority = 170 if (analysis.stats.hq_remaining_turns or 0) <= 3 else 162 if can_finish_now else 156
        return [
            StrategicIntentView(
                id=_intent_id("bootstrap-finish"),
                kind="finish_build",
                priority=priority,
                summary=f"Secure HQ anchor at {target.x},{target.y}",
                reason="Bootstrap rule: when the colony is down to a single live command node, the next adjacent anchor must be finished before any broader frontier plans.",
                target_position=target,
                desired_contributors=desired_contributors,
                score=round(320 - remaining + (40 if can_finish_now else 0) + (weights.support_bias * 25), 2),
                preferred_author_ids=preferred_authors,
            )
        ]

    if target_key in analysis.plantation_by_position:
        return []

    preferred_authors = _preferred_authors_for_target(analysis, target, limit=8, purpose="build")
    if not preferred_authors:
        return []
    return [
        StrategicIntentView(
            id=_intent_id("bootstrap-build"),
            kind="build",
            priority=164 if (analysis.stats.hq_remaining_turns or 0) <= 6 else 152,
            summary=f"Seed HQ anchor at {target.x},{target.y}",
            reason="Bootstrap rule: keep an adjacent build locked next to the HQ until it becomes a real handoff anchor.",
            target_position=target,
            desired_contributors=_build_contributor_budget(
                analysis,
                target,
                len(preferred_authors),
                baseline=1,
                urgent=True,
            ),
            score=round(280 + (weights.expansion_bias * 20), 2),
            preferred_author_ids=preferred_authors,
        )
    ]


def decide_repairs(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    for plantation in analysis.arena.plantations:
        if plantation.id not in analysis.connected_ids:
            continue
        if plantation.immunity_until_turn > analysis.arena.turn_no:
            continue

        critical = plantation.is_main or plantation.id in analysis.articulation_ids
        threshold = 34 if plantation.is_main else 30 if critical else 24
        if analysis.earthquake_now:
            threshold += 8 if critical else 4
        if plantation.hp >= threshold:
            continue

        priority = 126 if plantation.is_main else 112 if critical else 84
        if analysis.current_mode in {"bootstrap", "defense"}:
            priority += 6
        intents.append(
            StrategicIntentView(
                id=_intent_id("repair"),
                kind="repair",
                priority=priority,
                summary=f"Repair {plantation.id}",
                reason="Preserve the command graph before a bridge, HQ or other valuable node falls out of the network.",
                target_position=plantation.position,
                target_entity_id=plantation.id,
                desired_contributors=3 if plantation.is_main else 2 if critical else 1,
                score=round((threshold - plantation.hp) * (1.25 + weights.safety_bias), 2),
                preferred_author_ids=_preferred_authors_for_target(analysis, plantation.position, limit=8, purpose="repair"),
            )
        )
    return intents


def decide_finish_builds(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    if not analysis.arena.constructions or not analysis.connected_ids:
        return intents

    strict_anchor_mode = _strict_anchor_mode(analysis)
    for construction in analysis.arena.constructions:
        remaining = max(0, 50 - construction.progress)
        if remaining <= 0:
            continue
        preferred_authors = _preferred_authors_for_target(analysis, construction.position, limit=10, purpose="finish_build")
        if not preferred_authors:
            continue

        adjacent_to_main = bool(analysis.main_plantation and is_cardinal_neighbor(construction.position, analysis.main_plantation.position))
        if strict_anchor_mode and not _construction_stabilizes_hq_route(analysis, construction.position):
            continue
        can_finish_now = len(preferred_authors) * analysis.construction_power >= remaining
        stagnant = analysis.planner_memory.stagnant_streak(_position_key(construction.position)) if analysis.planner_memory else 0
        threatened = any(chebyshev_distance(beaver.position, construction.position) <= 2 for beaver in analysis.arena.beavers)
        if analysis.earthquake_now and not can_finish_now:
            continue
        contributors = _build_contributor_budget(
            analysis,
            construction.position,
            len(preferred_authors),
            baseline=max(1, ceil(remaining / max(1, analysis.construction_power))),
            urgent=adjacent_to_main or strict_anchor_mode or can_finish_now,
        )
        priority = 122 if can_finish_now else 114 if adjacent_to_main else 98
        if analysis.current_mode == "bootstrap" and adjacent_to_main:
            priority = 160 if can_finish_now else 148
        elif analysis.current_mode == "defense" and adjacent_to_main:
            priority += 6
        if analysis.earthquake_soon and can_finish_now:
            priority += 8
        score = (
            240
            - (remaining * 2.2)
            + (45 if can_finish_now else 0)
            + (35 if adjacent_to_main else 0)
            + (18 if construction.is_boosted_cell else 0)
            - (stagnant * 16)
            - (22 if threatened else 0)
        )
        intents.append(
            StrategicIntentView(
                id=_intent_id("finish"),
                kind="finish_build",
                priority=priority,
                summary=f"Finish build at {construction.position.x},{construction.position.y}",
                reason="Existing construction has better EV than opening another unfinished node, especially when it stabilizes the HQ route.",
                target_position=construction.position,
                desired_contributors=contributors,
                score=round(score * (1 + weights.expansion_bias * 0.08), 2),
                preferred_author_ids=preferred_authors,
            )
        )
    return intents


def decide_builds(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    if analysis.stats.available_settlement_headroom <= 0 or not analysis.connected_ids:
        return intents
    if analysis.stats.connected_plantations <= 2 and _fresh_adjacent_handoff_anchor(analysis) is not None:
        return intents

    strict_anchor_mode = _strict_anchor_mode(analysis)
    hq_route_constructions = sum(
        1
        for construction in analysis.arena.constructions
        if _construction_stabilizes_hq_route(analysis, construction.position)
    )
    if strict_anchor_mode and hq_route_constructions > 0:
        return intents

    if analysis.current_mode == "bootstrap":
        target = _bootstrap_target(analysis)
        if target is None or _position_key(target) in analysis.construction_by_position:
            return intents
        preferred_authors = _preferred_authors_for_target(analysis, target, limit=8, purpose="build")
        if not preferred_authors:
            return intents
        return [
            StrategicIntentView(
                id=_intent_id("build"),
                kind="build",
                priority=150,
                summary=f"Build at {target.x},{target.y}",
                reason="Bootstrap mode locks one adjacent anchor next to the HQ until construction starts and then keeps feeding that exact target.",
                target_position=target,
                desired_contributors=_build_contributor_budget(
                    analysis,
                    target,
                    len(preferred_authors),
                    baseline=1,
                    urgent=True,
                ),
                score=300,
                preferred_author_ids=preferred_authors,
                source="strategy",
            )
        ]

    connected = analysis.stats.connected_plantations
    open_constructions = sum(
        1
        for construction in analysis.arena.constructions
        if not strict_anchor_mode or _construction_stabilizes_hq_route(analysis, construction.position)
    )
    tempo_behind = analysis.stats.completion_rate_20 <= (analysis.stats.expiration_rate_20 + 0.05)
    if analysis.earthquake_now:
        return intents

    if _serialize_active_construction_lane(analysis):
        return intents

    if open_constructions and connected <= 1:
        return intents

    construction_cap = min(
        max(1, weights.construction_cap),
        max(1, analysis.stats.available_settlement_headroom),
        5,
    )
    if connected <= 1:
        construction_cap = 1
    elif connected <= 2:
        construction_cap = min(construction_cap, 2)
    elif connected <= 4:
        construction_cap = min(construction_cap, 3)
    elif connected <= 7:
        construction_cap = min(construction_cap, 4)
    if analysis.earthquake_soon:
        construction_cap = min(construction_cap, 1)
    if tempo_behind and not (connected <= 2 and open_constructions == 0):
        construction_cap = min(construction_cap, max(1, open_constructions + 1))
    if strict_anchor_mode:
        construction_cap = min(construction_cap, max(1, len(analysis.hq_anchor_candidates) + 1))
    if open_constructions >= construction_cap and analysis.current_mode != "rebase":
        return intents
    if analysis.earthquake_soon and open_constructions > 0 and analysis.current_mode != "rebase":
        return intents

    target_budget = max(0, construction_cap - open_constructions)
    if strict_anchor_mode and open_constructions > 0:
        target_budget = min(target_budget, 1)
    elif analysis.current_mode == "economy":
        target_budget = min(target_budget, 2 if analysis.stats.connected_plantations <= 2 else 3)
    elif analysis.current_mode == "defense":
        target_budget = min(target_budget, 1 if analysis.hq_anchor_candidates else 2)
    if tempo_behind and open_constructions > 0:
        target_budget = min(target_budget, 1)
    if analysis.earthquake_soon:
        target_budget = min(target_budget, 1)

    opening_candidates: list[Coordinate] = []
    frontier_pool = analysis.frontier_candidates
    if strict_anchor_mode and analysis.main_plantation:
        if analysis.opening_stage == "second_anchor" and analysis.stats.connected_plantations <= 2:
            frontier_pool = [
                candidate
                for candidate in analysis.frontier_candidates
                if is_cardinal_neighbor(candidate.position, analysis.main_plantation.position)
            ]
        else:
            frontier_pool = [
                candidate
                for candidate in analysis.frontier_candidates
                if is_cardinal_neighbor(candidate.position, analysis.main_plantation.position)
            ]
    ranked_frontier = sorted(
        [candidate for candidate in frontier_pool if _small_network_beaver_safe_build(analysis, candidate.position)],
        key=lambda candidate: (
            _scored_build_candidate(analysis, candidate, weights),
            candidate.support_count,
            1 if candidate.boosted else 0,
        ),
        reverse=True,
    )

    if analysis.main_plantation:
        hq_adjacent = [
            candidate
            for candidate in ranked_frontier
            if is_cardinal_neighbor(candidate.position, analysis.main_plantation.position)
        ]
        if analysis.opening_stage in {"seed_anchor", "second_anchor"} and target_budget > 0:
            if analysis.opening_stage == "second_anchor" and analysis.stats.connected_plantations <= 2:
                opening_candidates.extend(candidate.position for candidate in hq_adjacent[:target_budget])
            else:
                opening_candidates.extend(candidate.position for candidate in hq_adjacent[:target_budget])
        elif analysis.opening_stage == "double_lane":
            lane_candidates = [
                candidate
                for candidate in ranked_frontier
                if candidate.support_count >= 2
                or any(is_cardinal_neighbor(candidate.position, anchor) for anchor in analysis.hq_anchor_candidates[:2])
            ]
            if target_budget > 0:
                opening_candidates.extend(candidate.position for candidate in lane_candidates[:1])

    picked: set[tuple[int, int]] = set()
    for opening_position in opening_candidates:
        picked.add(_position_key(opening_position))
        candidate = next(item for item in ranked_frontier if item.position == opening_position)
        anchor_candidate = bool(analysis.main_plantation and is_cardinal_neighbor(candidate.position, analysis.main_plantation.position))
        dynamic_score = _scored_build_candidate(analysis, candidate, weights)
        intents.append(
            StrategicIntentView(
                id=_intent_id("build"),
                kind="build",
                priority=116 if analysis.opening_stage in {"seed_anchor", "second_anchor"} else 102,
                summary=f"Build at {candidate.position.x},{candidate.position.y}",
                reason="Opening policy: maintain two safe HQ anchors before spending tempo on deeper frontier bets.",
                target_position=candidate.position,
                desired_contributors=_build_contributor_budget(
                    analysis,
                    candidate.position,
                    len(_preferred_authors_for_target(analysis, candidate.position, limit=8, purpose="build")),
                    baseline=3 if analysis.earthquake_soon and anchor_candidate else 2 if anchor_candidate else 1,
                    urgent=anchor_candidate or analysis.opening_stage in {"seed_anchor", "second_anchor", "double_lane"},
                ),
                score=round(dynamic_score + 80, 2),
                preferred_author_ids=_preferred_authors_for_target(analysis, candidate.position, limit=8, purpose="build"),
                source="strategy",
            )
        )

    for candidate in ranked_frontier:
        if len(intents) >= target_budget:
            break
        key = _position_key(candidate.position)
        if key in picked:
            continue

        anchor_candidate = bool(analysis.main_plantation and is_cardinal_neighbor(candidate.position, analysis.main_plantation.position))
        beaver_metrics = _beaver_metrics_for_position(analysis, candidate.position)
        desired_contributors = 2 if candidate.boosted or candidate.kind == "relay" or anchor_candidate else 1
        if analysis.stats.connected_plantations <= 3 and candidate.support_count >= 2:
            desired_contributors = max(desired_contributors, 2)
        if analysis.stats.connected_plantations >= 5 and beaver_metrics is not None and int(beaver_metrics["distance"]) in {3, 4}:
            desired_contributors = max(desired_contributors, 2)
        if analysis.earthquake_soon and (anchor_candidate or candidate.support_count >= 2):
            desired_contributors = max(desired_contributors, 3)
        priority = 108 if anchor_candidate and (analysis.main_plantation and (analysis.main_plantation.turns_to_completion or 0) <= 6) else 86 if candidate.support_count >= 2 else 74
        if candidate.kind == "relay":
            priority += 8
        if analysis.current_mode == "rebase":
            priority += 12 if anchor_candidate or candidate.kind == "relay" else 0
        if analysis.stats.connected_plantations >= 5 and beaver_metrics is not None and int(beaver_metrics["distance"]) in {3, 4}:
            priority += 10
        score = _scored_build_candidate(analysis, candidate, weights)
        intents.append(
            StrategicIntentView(
                id=_intent_id("build"),
                kind="build",
                priority=priority,
                summary=f"Build at {candidate.position.x},{candidate.position.y}",
                reason=candidate.reason,
                target_position=candidate.position,
                desired_contributors=_build_contributor_budget(
                    analysis,
                    candidate.position,
                    len(_preferred_authors_for_target(analysis, candidate.position, limit=8, purpose="build")),
                    baseline=desired_contributors,
                    urgent=anchor_candidate or candidate.support_count >= 2,
                ),
                score=round(score, 2),
                preferred_author_ids=_preferred_authors_for_target(analysis, candidate.position, limit=8, purpose="build"),
                source="strategy",
            )
        )
        picked.add(key)
    return intents


def decide_beaver_hunts(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    if analysis.current_mode == "bootstrap":
        return intents
    if not analysis.arena.beavers:
        return intents

    small_network = analysis.stats.connected_plantations < 5
    for beaver in analysis.arena.beavers:
        beaver_metrics = _beaver_metrics_for_position(analysis, beaver.position)
        if beaver_metrics is None:
            continue
        local_support = sum(
            1
            for plantation in analysis.arena.plantations
            if plantation.id in analysis.connected_ids and chebyshev_distance(plantation.position, beaver.position) <= 5
        )
        if local_support == 0:
            continue

        strike_nodes = int(beaver_metrics["strike_nodes"])
        perimeter_nodes = int(beaver_metrics["perimeter_nodes"])
        perimeter_ready = bool(beaver_metrics["perimeter_ready"])
        net_damage_cap = (local_support * analysis.beaver_attack_power) - 5
        threatened_core = any(
            plantation.id in analysis.connected_ids and chebyshev_distance(plantation.position, beaver.position) <= 2
            for plantation in analysis.arena.plantations
        )
        if strike_nodes == 0:
            continue
        if small_network:
            if _has_beaver_bypass_candidate(analysis, beaver.position):
                continue
            if local_support < 2:
                continue
            intents.append(
                StrategicIntentView(
                    id=_intent_id("beaver"),
                    kind="beaver_attack",
                    priority=96 if threatened_core else 76,
                    summary=f"Attack beaver {beaver.id}",
                    reason="The small network has no clean bypass around this beaver lane. Break the blocker now instead of freezing the whole expansion front.",
                    target_position=beaver.position,
                    target_entity_id=beaver.id,
                    desired_contributors=min(max(2, strike_nodes + 1), local_support, 4),
                    score=round((local_support * 16) + (40 if threatened_core else 0) + (weights.beaver_hunt_bias * 18), 2),
                    preferred_author_ids=_preferred_authors_for_target(analysis, beaver.position, limit=10, purpose="beaver_attack"),
                )
            )
            continue
        if not threatened_core and not perimeter_ready:
            continue
        if not threatened_core and local_support < 4:
            continue
        if net_damage_cap <= 0 and not threatened_core:
            continue
        if not threatened_core and beaver.hp > 40 and net_damage_cap < 12:
            continue

        nearby_enemy = any(chebyshev_distance(enemy.position, beaver.position) <= 4 for enemy in analysis.arena.enemy)
        if nearby_enemy and net_damage_cap < 10 and analysis.current_mode != "contested":
            continue

        intents.append(
            StrategicIntentView(
                id=_intent_id("beaver"),
                kind="beaver_attack",
                priority=98 if threatened_core else 82 if perimeter_nodes >= 3 else 74,
                summary=f"Attack beaver {beaver.id}",
                reason="Take beaver EV only after the perimeter is staged and the local burst is real. Do not walk straight into lair range with a paper-thin lane.",
                target_position=beaver.position,
                target_entity_id=beaver.id,
                desired_contributors=min(max(2, strike_nodes + 1), local_support, 5),
                score=round((net_damage_cap * 8) + (45 if threatened_core else 0) + (perimeter_nodes * 12) + (weights.beaver_hunt_bias * 25), 2),
                preferred_author_ids=_preferred_authors_for_target(analysis, beaver.position, limit=10, purpose="beaver_attack"),
            )
        )
    return intents


def decide_sabotage(analysis: ArenaAnalysis, weights: StrategyWeights) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    if analysis.current_mode == "bootstrap":
        return intents
    if not analysis.arena.enemy or weights.sabotage_bias < 0.35:
        return intents
    if analysis.current_mode not in {"raid", "contested", "defense"} and analysis.stats.completion_rate_20 <= analysis.stats.expiration_rate_20:
        return intents

    for enemy in analysis.arena.enemy:
        local_support = sum(
            1
            for plantation in analysis.arena.plantations
            if plantation.id in analysis.connected_ids and chebyshev_distance(plantation.position, enemy.position) <= 5
        )
        if local_support < 2:
            continue

        contested_boost = 35 if enemy.position.x % 7 == 0 and enemy.position.y % 7 == 0 else 0
        close_to_core = bool(analysis.main_plantation and chebyshev_distance(enemy.position, analysis.main_plantation.position) <= 8)
        if not close_to_core and contested_boost == 0 and analysis.current_mode != "raid":
            continue

        intents.append(
            StrategicIntentView(
                id=_intent_id("sabotage"),
                kind="sabotage",
                priority=88 if analysis.current_mode in {"raid", "contested"} else 74,
                summary=f"Sabotage enemy {enemy.id}",
                reason="Short, local raids are only worth it when they threaten a nearby cluster or a high-value contested lane.",
                target_position=enemy.position,
                target_entity_id=enemy.id,
                desired_contributors=min(local_support, 3),
                score=round((local_support * 14) + contested_boost + (weights.sabotage_bias * 28), 2),
                preferred_author_ids=_preferred_authors_for_target(analysis, enemy.position, limit=8, purpose="sabotage"),
            )
        )
    return intents


def apply_manual_directives(analysis: ArenaAnalysis, directives: list[ManualDirective]) -> list[StrategicIntentView]:
    intents: list[StrategicIntentView] = []
    for directive in directives:
        if not directive.is_active(analysis.arena.turn_no):
            continue
        summary = directive.note or f"Manual {directive.kind}"
        intents.append(
            StrategicIntentView(
                id=f"manual-{directive.id}",
                kind=directive.kind,
                priority=130,
                summary=summary,
                reason=summary,
                source="manual",
                target_position=directive.target_position,
                target_entity_id=directive.target_entity_id or directive.relocate_to_id or directive.upgrade_name,
                desired_contributors=max(1, len(directive.author_ids)) if directive.kind not in {"upgrade", "relocate_main"} else 0,
                score=999,
                preferred_author_ids=directive.author_ids,
            )
        )
    return intents


def _intent_identity(intent: StrategicIntentView) -> tuple[str, str | None, tuple[int, int] | None, str]:
    position = _position_key(intent.target_position) if intent.target_position else None
    return (intent.kind, intent.target_entity_id, position, intent.source)


def decide_turn(
    analysis: ArenaAnalysis,
    weights: StrategyWeights,
    manual_directives: list[ManualDirective],
) -> tuple[list[StrategicIntentView], UpgradeRecommendation | None, RelocateMainPlanView | None]:
    intents: list[StrategicIntentView] = []
    intents.extend(decide_bootstrap_intents(analysis, weights))
    intents.extend(decide_repairs(analysis, weights))
    intents.extend(decide_finish_builds(analysis, weights))
    intents.extend(decide_builds(analysis, weights))
    intents.extend(decide_beaver_hunts(analysis, weights))
    intents.extend(decide_sabotage(analysis, weights))
    intents.extend(apply_manual_directives(analysis, manual_directives))
    deduped: dict[tuple[str, str | None, tuple[int, int] | None, str], StrategicIntentView] = {}
    for intent in intents:
        identity = _intent_identity(intent)
        current = deduped.get(identity)
        if current is None or (intent.priority, intent.score) > (current.priority, current.score):
            deduped[identity] = intent
    result = list(deduped.values())
    result.sort(key=lambda item: (item.priority, item.score), reverse=True)
    return result, recommend_upgrade(analysis), decide_main_relocation(analysis, weights)
