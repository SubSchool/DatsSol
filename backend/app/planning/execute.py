from __future__ import annotations

from dataclasses import dataclass, field

from app.planning.analyze import ArenaAnalysis
from app.planning.geometry import chebyshev_distance, is_cardinal_neighbor, within_square_radius
from app.schemas.game import (
    CommandEnvelopeView,
    Coordinate,
    PlannedActionView,
    PlayerCommandPayload,
    PlantationActionPayload,
    RelocateMainPlanView,
    StrategicIntentView,
    UpgradeRecommendation,
)


@dataclass
class ExecutionPlan:
    actions: list[PlannedActionView] = field(default_factory=list)
    upgrade_name: str | None = None
    relocate_main: list[Coordinate] | None = None
    command_view: CommandEnvelopeView | None = None
    payload: PlayerCommandPayload | None = None


def _exit_key(position: Coordinate) -> tuple[int, int]:
    return (position.x, position.y)


def _power_for_action(analysis: ArenaAnalysis, kind: str, exit_load: int) -> int:
    base = 5
    if kind in {"build", "finish_build"}:
        base = analysis.construction_power
    elif kind == "repair":
        base = analysis.repair_power
    elif kind == "sabotage":
        base = analysis.sabotage_power
    elif kind == "beaver_attack":
        base = analysis.beaver_attack_power
    return max(0, base - exit_load)


def _resolve_manual_upgrade(intents: list[StrategicIntentView]) -> str | None:
    upgrade_intent = next((item for item in intents if item.kind == "upgrade" and item.source == "manual"), None)
    return upgrade_intent.target_entity_id if upgrade_intent else None


def _resolve_manual_relocation(analysis: ArenaAnalysis, intents: list[StrategicIntentView]) -> list[Coordinate] | None:
    relocation_intent = next((item for item in intents if item.kind == "relocate_main" and item.source == "manual"), None)
    if relocation_intent is None or analysis.main_plantation is None:
        return None

    target = next(
        (
            plantation
            for plantation in analysis.arena.plantations
            if plantation.id == relocation_intent.target_entity_id
        ),
        None,
    )
    if target is None:
        return None
    return [analysis.main_plantation.position, target.position]


def _candidate_exits(analysis: ArenaAnalysis, author_id: str, target_position: Coordinate) -> list[Coordinate]:
    author = analysis.plantation_by_id[author_id]
    exits = []
    for plantation in analysis.arena.plantations:
        if plantation.id not in analysis.connected_ids:
            continue
        if within_square_radius(author.position, plantation.position, analysis.signal_range) and within_square_radius(
            plantation.position,
            target_position,
            analysis.arena.action_range,
        ):
            exits.append(plantation.position)

    exits.sort(key=lambda position: chebyshev_distance(position, target_position))
    return exits


def _author_candidates(analysis: ArenaAnalysis, intent: StrategicIntentView, used_authors: set[str]) -> list[str]:
    authors = [
        plantation.id
        for plantation in analysis.arena.plantations
        if plantation.id in analysis.connected_ids and plantation.id not in used_authors
    ]
    if intent.preferred_author_ids:
        authors = [author_id for author_id in intent.preferred_author_ids if author_id in authors]
    if intent.kind == "repair" and intent.target_entity_id:
        authors = [author_id for author_id in authors if author_id != intent.target_entity_id]

    authors.sort(
        key=lambda author_id: chebyshev_distance(
            analysis.plantation_by_id[author_id].position,
            intent.target_position or analysis.plantation_by_id[author_id].position,
        )
    )
    return authors


def _build_action(
    analysis: ArenaAnalysis,
    intent: StrategicIntentView,
    author_id: str,
    exit_position: Coordinate,
    power: int,
) -> PlannedActionView:
    return PlannedActionView(
        kind="build" if intent.kind == "finish_build" else intent.kind,
        source=intent.source,
        author_id=author_id,
        exit_position=exit_position,
        target_position=intent.target_position,
        path=[
            analysis.plantation_by_id[author_id].position,
            exit_position,
            intent.target_position,
        ],
        estimated_power=power,
        reason=intent.reason,
    )


def _fallback_action(analysis: ArenaAnalysis, blocked_author_ids: set[str] | None = None) -> PlannedActionView | None:
    main = analysis.main_plantation
    if main is None:
        return None
    if blocked_author_ids and main.id in blocked_author_ids:
        return None

    candidate_targets: list[tuple[str, Coordinate]] = []
    locked = analysis.planner_memory.bootstrap_target_for(main.position) if analysis.planner_memory else None
    if locked:
        candidate_targets.append(
            (
                "finish_build" if locked in analysis.construction_by_position else "build",
                Coordinate(x=locked[0], y=locked[1]),
            )
        )
    for construction in sorted(analysis.adjacent_hq_constructions, key=lambda item: item.progress, reverse=True):
        key = _exit_key(construction.position)
        if locked and key == locked:
            continue
        candidate_targets.append(("finish_build", construction.position))
    for candidate in analysis.frontier_candidates:
        if not is_cardinal_neighbor(candidate.position, main.position):
            continue
        key = _exit_key(candidate.position)
        if locked and key == locked:
            continue
        candidate_targets.append(("build", candidate.position))

    for kind, target in candidate_targets:
        exit_positions = _candidate_exits(analysis, main.id, target)
        if not exit_positions:
            continue
        exit_position = min(exit_positions, key=lambda position: chebyshev_distance(position, target))
        power = _power_for_action(analysis, kind, 0)
        if power <= 0:
            continue
        return PlannedActionView(
            kind="build" if kind == "finish_build" else kind,
            source="strategy",
            author_id=main.id,
            exit_position=exit_position,
            target_position=target,
            path=[main.position, exit_position, target],
            estimated_power=power,
            reason="Execution fallback: preserve HQ continuity with a safe adjacent anchor instead of emitting an empty payload.",
        )
    return None


def _verified_relocation_path(
    analysis: ArenaAnalysis,
    recommended_relocation: RelocateMainPlanView | None,
    assigned_power_by_target: dict[tuple[int, int], int],
) -> list[Coordinate] | None:
    if recommended_relocation is None:
        return None

    target_key = _exit_key(recommended_relocation.to_position)
    if target_key in analysis.plantation_by_position:
        return [recommended_relocation.from_position, recommended_relocation.to_position]

    construction = analysis.construction_by_position.get(target_key)
    if construction is None:
        return None

    remaining = max(0, 50 - construction.progress)
    if assigned_power_by_target.get(target_key, 0) < remaining:
        return None
    return [recommended_relocation.from_position, recommended_relocation.to_position]


def _relocation_target_is_busy(
    analysis: ArenaAnalysis,
    actions: list[PlannedActionView],
    target: Coordinate,
) -> bool:
    target_key = _exit_key(target)
    if target_key in analysis.plantation_by_position:
        return False
    for action in actions:
        author = analysis.plantation_by_id.get(action.author_id)
        if author is not None and _exit_key(author.position) == target_key:
            return True
        if _exit_key(action.exit_position) == target_key:
            return True
    return False


def _reserved_relocation_target_key(
    analysis: ArenaAnalysis,
    recommended_relocation: RelocateMainPlanView | None,
) -> tuple[int, int] | None:
    if recommended_relocation is None:
        return None
    if recommended_relocation.urgency not in {"high", "critical"}:
        return None
    target_key = _exit_key(recommended_relocation.to_position)
    if target_key in analysis.plantation_by_position:
        return None
    return target_key


def _reserved_relocation_main_author_id(
    analysis: ArenaAnalysis,
    recommended_relocation: RelocateMainPlanView | None,
) -> str | None:
    if recommended_relocation is None or analysis.main_plantation is None:
        return None
    if recommended_relocation.urgency not in {"high", "critical"}:
        return None
    target_key = _exit_key(recommended_relocation.to_position)
    if target_key not in analysis.plantation_by_position:
        return None
    return analysis.main_plantation.id


def build_execution_plan(
    analysis: ArenaAnalysis,
    intents: list[StrategicIntentView],
    recommended_upgrade: UpgradeRecommendation | None,
    recommended_relocation: RelocateMainPlanView | None,
) -> ExecutionPlan:
    used_authors: set[str] = set()
    exit_loads: dict[tuple[int, int], int] = {}
    assigned_power_by_target: dict[tuple[int, int], int] = {}
    actions: list[PlannedActionView] = []
    reserved_relocation_target_key = _reserved_relocation_target_key(analysis, recommended_relocation)
    reserved_relocation_main_author_id = _reserved_relocation_main_author_id(analysis, recommended_relocation)

    for intent in intents:
        if intent.kind in {"upgrade", "relocate_main"} or intent.target_position is None:
            continue

        assigned = 0
        target_key = _exit_key(intent.target_position)
        remaining_for_finish = None
        if intent.kind == "finish_build":
            construction = analysis.construction_by_position.get(target_key)
            if construction is None:
                continue
            remaining_for_finish = max(0, 50 - construction.progress)
        for author_id in _author_candidates(analysis, intent, used_authors):
            author = analysis.plantation_by_id[author_id]
            if reserved_relocation_main_author_id is not None and author_id == reserved_relocation_main_author_id:
                continue
            if reserved_relocation_target_key is not None and _exit_key(author.position) == reserved_relocation_target_key:
                continue
            exit_positions = _candidate_exits(analysis, author_id, intent.target_position)
            if reserved_relocation_target_key is not None:
                exit_positions = [
                    position for position in exit_positions if _exit_key(position) != reserved_relocation_target_key
                ]
            if not exit_positions:
                continue
            exit_position = min(
                exit_positions,
                key=lambda position: (
                    exit_loads.get(_exit_key(position), 0),
                    chebyshev_distance(position, intent.target_position),
                ),
            )
            current_exit_load = exit_loads.get(_exit_key(exit_position), 0)
            max_exit_load = 4 if intent.priority >= 110 else 3
            if current_exit_load >= max_exit_load:
                continue
            power = _power_for_action(analysis, intent.kind, current_exit_load)
            if power <= 0:
                continue

            action = _build_action(analysis, intent, author_id, exit_position, power)
            if analysis.planner_memory and analysis.planner_memory.is_path_blocked(action, analysis.arena.turn_no):
                continue
            actions.append(action)
            used_authors.add(author_id)
            exit_loads[_exit_key(exit_position)] = exit_loads.get(_exit_key(exit_position), 0) + 1
            assigned_power_by_target[target_key] = assigned_power_by_target.get(target_key, 0) + power
            assigned += 1
            if remaining_for_finish is not None and assigned_power_by_target[target_key] >= remaining_for_finish:
                break
            if assigned >= max(1, intent.desired_contributors):
                break

    if not actions:
        for intent in intents:
            if intent.kind in {"upgrade", "relocate_main"} or intent.target_position is None:
                continue
            for author_id in _author_candidates(analysis, intent, set()):
                author = analysis.plantation_by_id[author_id]
                if reserved_relocation_main_author_id is not None and author_id == reserved_relocation_main_author_id:
                    continue
                if reserved_relocation_target_key is not None and _exit_key(author.position) == reserved_relocation_target_key:
                    continue
                exit_positions = _candidate_exits(analysis, author_id, intent.target_position)
                if reserved_relocation_target_key is not None:
                    exit_positions = [
                        position for position in exit_positions if _exit_key(position) != reserved_relocation_target_key
                    ]
                if not exit_positions:
                    continue
                exit_position = min(
                    exit_positions,
                    key=lambda position: (
                        chebyshev_distance(position, intent.target_position),
                        exit_loads.get(_exit_key(position), 0),
                    ),
                )
                power = _power_for_action(analysis, intent.kind, exit_loads.get(_exit_key(exit_position), 0))
                if power <= 0:
                    continue
                actions.append(_build_action(analysis, intent, author_id, exit_position, power))
                break
            if actions:
                break

    if not actions:
        blocked_author_ids = {reserved_relocation_main_author_id} if reserved_relocation_main_author_id is not None else None
        fallback = _fallback_action(analysis, blocked_author_ids=blocked_author_ids)
        if fallback is not None:
            actions.append(fallback)

    upgrade_name = _resolve_manual_upgrade(intents) or (recommended_upgrade.name if recommended_upgrade else None)
    relocate_main = _resolve_manual_relocation(analysis, intents) or _verified_relocation_path(
        analysis,
        recommended_relocation,
        assigned_power_by_target,
    )
    if relocate_main and _relocation_target_is_busy(analysis, actions, relocate_main[1]):
        relocate_main = None

    payload = PlayerCommandPayload(
        command=[PlantationActionPayload(path=item.path) for item in actions],
        plantation_upgrade=upgrade_name,
        relocate_main=relocate_main,
    )
    command_view = CommandEnvelopeView(
        command=[item.path for item in actions],
        plantation_upgrade=upgrade_name,
        relocate_main=relocate_main,
    )
    return ExecutionPlan(
        actions=actions,
        upgrade_name=upgrade_name,
        relocate_main=relocate_main,
        command_view=command_view,
        payload=payload,
    )
