import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.config import Settings
from app.planning.analyze import analyze_arena, recommend_upgrade
from app.planning.geometry import chebyshev_distance
from app.planning.decide import decide_turn
from app.planning.execute import build_execution_plan
from app.planning.memory import PlannerMemory
from app.planning.strategy_registry import StrategyRegistry
from app.providers.datsol_live import DatsSolLiveProvider
from app.providers.datsol_mock import DatsSolMockProvider
from app.services.runtime import RuntimeService
from app.schemas.game import (
    ConstructionView,
    Coordinate,
    PlantationActionPayload,
    PlantationView,
    PlayerCommandPayload,
    RelocateMainPlanView,
    StrategicIntentView,
    SubmitResultView,
    TerraformedCellView,
)


def test_settings_auto_server_target_switches_once_at_fixed_utc_time() -> None:
    settings = Settings(
        datssol_server_mode="auto",
        datssol_production_switch_at_utc="2026-04-18T14:00:00+00:00",
    )

    before = datetime(2026, 4, 18, 13, 59, 59, tzinfo=timezone.utc)
    after = datetime(2026, 4, 18, 14, 0, 0, tzinfo=timezone.utc)

    assert settings.datssol_active_server_target(before) == "test"
    assert settings.datssol_active_server_target(after) == "production"
    assert settings.datssol_next_server_switch_at_utc(before) == datetime(2026, 4, 18, 14, 0, 0, tzinfo=timezone.utc)
    assert settings.datssol_next_server_switch_at_utc(after) is None


def test_live_provider_uses_active_base_url_for_request_target() -> None:
    provider = DatsSolLiveProvider()
    provider._settings = Settings(
        datssol_server_mode="auto",
        datssol_production_switch_at_utc="2026-04-18T14:00:00+00:00",
        datssol_base_url="https://games-test.datsteam.dev",
        datssol_prod_base_url="https://games.datsteam.dev",
    )

    assert provider._settings.datssol_active_base_url(datetime(2026, 4, 18, 13, 0, 0, tzinfo=timezone.utc)) == "https://games-test.datsteam.dev"
    assert provider._settings.datssol_active_base_url(datetime(2026, 4, 18, 14, 0, 0, tzinfo=timezone.utc)) == "https://games.datsteam.dev"


def test_frontier_strategy_prefers_survivability_upgrade_and_relocation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()

    main = next(item for item in arena.plantations if item.is_main)
    main.hp = 24
    main.immunity_until_turn = 0
    for cell in arena.cells:
        if cell.position == main.position:
            cell.terraformation_progress = 85

    analysis = analyze_arena(arena)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert intents
    assert intents[0].kind == "repair"
    assert upgrade is not None
    assert upgrade.name == "repair_power"
    assert relocate is not None
    assert relocate.from_position == main.position


def test_execution_plan_builds_paths_and_upgrade_payload() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    analysis = analyze_arena(arena)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    execution = build_execution_plan(
        analysis=analysis,
        intents=intents,
        recommended_upgrade=upgrade,
        recommended_relocation=relocate,
    )

    assert execution.payload is not None
    assert execution.command_view is not None
    assert upgrade is not None
    assert execution.payload.plantation_upgrade == upgrade.name
    assert execution.command_view.plantation_upgrade == upgrade.name
    assert execution.actions
    assert all(len(action.path) == 3 for action in execution.actions)


def test_existing_relocation_target_waits_for_handoff_before_next_build() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 100}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-safe", "position": Coordinate(x=10, y=11), "hp": 100, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    template_cell = arena.cells[0]
    arena.plantations = [main, anchor]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 80, "turns_until_degradation": 24}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 5, "turns_until_degradation": 39}),
    ]

    analysis = analyze_arena(arena)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )
    execution = build_execution_plan(
        analysis=analysis,
        intents=intents,
        recommended_upgrade=upgrade,
        recommended_relocation=relocate,
    )

    assert relocate is not None
    assert execution.relocate_main is not None
    assert not execution.actions


def test_second_anchor_prefers_adjacent_build_over_off_main_finish() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    main.hp = 50
    anchor = next(item for item in arena.plantations if not item.is_main)

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.opening_stage in {"second_anchor", "double_lane"}
    finish_intents = [item for item in intents if item.kind == "finish_build"]
    assert all(
        (
            abs(item.target_position.x - main.position.x) + abs(item.target_position.y - main.position.y) == 1
            or abs(item.target_position.x - anchor.position.x) + abs(item.target_position.y - anchor.position.y) == 1
        )
        for item in finish_intents
    )
    opening_intent = next(item for item in intents if item.kind in {"build", "finish_build"})
    assert (
        abs(opening_intent.target_position.x - main.position.x) + abs(opening_intent.target_position.y - main.position.y) == 1
        or abs(opening_intent.target_position.x - anchor.position.x) + abs(opening_intent.target_position.y - anchor.position.y) == 1
    )


def test_second_anchor_branches_only_after_fresh_handoff_relocation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 50}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}
    )
    arena.plantations = [main, anchor]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 60, "turns_until_degradation": 40}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 5, "turns_until_degradation": 50}),
        template_cell.model_copy(
            update={"position": Coordinate(x=10, y=9), "terraformation_progress": 60, "turns_until_degradation": 40}
        ),
        template_cell.model_copy(
            update={"position": Coordinate(x=12, y=10), "terraformation_progress": 0, "turns_until_degradation": 50}
        ),
    ]
    arena.mountains = [
        Coordinate(x=9, y=10),
        Coordinate(x=10, y=11),
        Coordinate(x=11, y=9),
        Coordinate(x=11, y=11),
    ]

    analysis = analyze_arena(arena)
    intents, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.opening_stage in {"second_anchor", "double_lane"}
    assert relocate is not None
    assert relocate.to_position == anchor.position
    assert not [item for item in intents if item.kind == "build"]


def test_single_main_prefers_adjacent_hq_anchor() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = []
    arena.enemy = []
    arena.beavers = []

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert intents
    assert intents[0].kind == "build"
    assert abs(intents[0].target_position.x - main.position.x) + abs(intents[0].target_position.y - main.position.y) == 1


def test_compact_existing_anchor_relocates_before_last_moment() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    anchor = next(item for item in arena.plantations if not item.is_main)
    main = main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50})
    anchor = anchor.model_copy(update={"position": Coordinate(x=11, y=10), "hp": 50, "is_main": False})
    arena.plantations = [main, anchor]
    arena.constructions = []
    arena.enemy = []
    arena.beavers = []
    arena.cells = [arena.cells[0].model_copy(update={"position": main.position, "terraformation_progress": 60})]

    analysis = analyze_arena(arena)
    _, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 2
    assert analysis.stats.hq_remaining_turns == 8
    assert relocate is not None
    assert relocate.to_position == anchor.position

def test_single_node_bootstrap_ignores_diagonal_started_construction() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    moved_main = next(item for item in arena.plantations if item.is_main).model_copy(update={"position": Coordinate(x=10, y=10)})
    arena.plantations = [moved_main]
    arena.constructions = [ConstructionView(position=Coordinate(x=11, y=11), progress=30)]
    arena.cells = []

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert intents
    assert analysis.current_mode == "bootstrap"
    assert intents[0].kind == "build"
    assert intents[0].target_position != arena.constructions[0].position
    assert abs(intents[0].target_position.x - moved_main.position.x) + abs(intents[0].target_position.y - moved_main.position.y) == 1


def test_second_anchor_can_finish_branch_from_existing_handoff_anchor() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    main = next(item for item in arena.plantations if item.is_main).model_copy(update={"position": Coordinate(x=10, y=10)})
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"position": Coordinate(x=11, y=10), "hp": 50}
    )
    arena.plantations = [main, anchor]
    arena.constructions = [ConstructionView(position=Coordinate(x=11, y=11), progress=40)]
    arena.cells = []

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.opening_stage in {"second_anchor", "double_lane"}
    finish_intent = next(
        item
        for item in intents
        if item.kind == "finish_build" and item.target_position == arena.constructions[0].position
    )
    assert finish_intent.target_position == arena.constructions[0].position


def test_fragile_bootstrap_spends_upgrade_on_decay_mitigation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = [ConstructionView(position=Coordinate(x=main.position.x - 1, y=main.position.y), progress=12)]
    arena.enemy = []
    arena.beavers = []
    arena.upgrades = arena.upgrades.model_copy(
        update={
            "points": 1,
            "tiers": [
                item.model_copy(
                    update={
                        "current": {
                            "repair_power": 3,
                            "max_hp": 4,
                            "signal_range": 4,
                            "earthquake_mitigation": 2,
                            "decay_mitigation": 0,
                        }.get(item.name, item.current)
                    }
                )
                for item in arena.upgrades.tiers
            ],
        }
    )

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "decay_mitigation"


def test_points_are_not_hoarded_in_fragile_bootstrap() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = []
    arena.enemy = []
    arena.beavers = []
    arena.upgrades = arena.upgrades.model_copy(
        update={
            "points": 1,
            "tiers": [
                item.model_copy(
                    update={
                        "current": {
                            "repair_power": 3,
                            "max_hp": 4,
                            "signal_range": 4,
                            "earthquake_mitigation": 2,
                            "decay_mitigation": 0,
                        }.get(item.name, item.current)
                    }
                )
                for item in arena.upgrades.tiers
            ],
        }
    )

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None


def test_bootstrap_prefers_quake_mitigation_for_active_build() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = [ConstructionView(position=Coordinate(x=main.position.x - 1, y=main.position.y), progress=25)]
    arena.enemy = []
    arena.beavers = []
    arena.forecasts = [SimpleNamespace(kind="earthquake", turns_until=3)]
    arena.upgrades = arena.upgrades.model_copy(
        update={
            "points": 1,
            "tiers": [
                item.model_copy(
                    update={
                        "current": {
                            "repair_power": 3,
                            "max_hp": 0,
                            "earthquake_mitigation": 0,
                        }.get(item.name, item.current)
                    }
                )
                for item in arena.upgrades.tiers
            ],
        }
    )

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert analysis.current_mode == "bootstrap"
    assert upgrade is not None
    assert upgrade.name == "earthquake_mitigation"


def test_compact_two_node_core_prefers_quake_mitigation_for_next_anchor() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
    ]
    arena.constructions = [ConstructionView(position=Coordinate(x=12, y=10), progress=20)]
    arena.forecasts = [SimpleNamespace(kind="earthquake", turns_until=2)]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": Coordinate(x=10, y=10), "terraformation_progress": 20, "turns_until_degradation": 46}),
        template_cell.model_copy(update={"position": Coordinate(x=11, y=10), "terraformation_progress": 85, "turns_until_degradation": 33}),
    ]
    arena.upgrades = arena.upgrades.model_copy(
        update={
            "points": 1,
            "tiers": [
                item.model_copy(
                    update={
                        "current": {
                            "repair_power": 3,
                            "max_hp": 5,
                            "signal_range": 2,
                            "earthquake_mitigation": 0,
                            "decay_mitigation": 3,
                        }.get(item.name, item.current)
                    }
                )
                for item in arena.upgrades.tiers
            ],
        }
    )

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert analysis.stats.connected_plantations == 2
    assert analysis.current_mode == "economy"
    assert upgrade is not None
    assert upgrade.name == "earthquake_mitigation"


def test_early_expansion_prefers_max_hp_before_generic_decay() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]
    arena.constructions = [ConstructionView(position=Coordinate(x=9, y=10), progress=20)]
    arena.forecasts = []
    arena.upgrades = arena.upgrades.model_copy(
        update={
            "points": 1,
            "tiers": [
                item.model_copy(
                    update={
                        "current": {
                            "repair_power": 3,
                            "max_hp": 3,
                            "signal_range": 2,
                            "decay_mitigation": 1,
                            "earthquake_mitigation": 0,
                        }.get(item.name, item.current)
                    }
                )
                for item in arena.upgrades.tiers
            ],
        }
    )

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert analysis.current_mode in {"economy", "bootstrap", "defense", "rebase"}
    assert upgrade is not None
    assert upgrade.name == "max_hp"


def test_failed_live_backoff_does_not_blacklist_path() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    memory = PlannerMemory()
    memory.observe(arena)
    analysis = analyze_arena(arena, planner_memory=memory)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )
    execution = build_execution_plan(
        analysis=analysis,
        intents=intents,
        recommended_upgrade=upgrade,
        recommended_relocation=relocate,
    )

    memory.note_submission(
        execution.actions,
        SubmitResultView(
            dry_run=True,
            accepted=False,
            errors=["local guard: live submit backoff active"],
            provider_message="Live submit backoff is active after a provider rate limit.",
        ),
    )

    assert execution.actions
    assert not memory.is_path_blocked(execution.actions[0], arena.turn_no)
    assert memory.path_fail_streak(execution.actions[0]) == 0


def test_imminent_quake_does_not_blacklist_build_path() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.forecasts = [item.model_copy(update={"turns_until": 1}) if item.kind == "earthquake" else item for item in arena.forecasts]
    memory = PlannerMemory()
    memory.observe(arena)
    analysis = analyze_arena(arena, planner_memory=memory)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )
    execution = build_execution_plan(
        analysis=analysis,
        intents=intents,
        recommended_upgrade=upgrade,
        recommended_relocation=relocate,
    )

    build_action = next(action for action in execution.actions if action.kind == "build")
    memory.note_submission(
        [build_action],
        SubmitResultView(
            dry_run=False,
            accepted=True,
            errors=[],
            provider_message="submitted",
        ),
        imminent_earthquake=True,
    )

    next_arena = arena.model_copy(
        update={
            "turn_no": arena.turn_no + 1,
            "constructions": [],
            "plantations": arena.plantations,
        }
    )
    memory.observe(next_arena)

    assert not memory.is_path_blocked(build_action, next_arena.turn_no)


def test_bootstrap_target_stays_locked_across_turns() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = []
    arena.enemy = []
    arena.beavers = []

    memory = PlannerMemory()
    memory.observe(arena)
    analysis = analyze_arena(arena, planner_memory=memory)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )
    first_target = intents[0].target_position

    next_arena = arena.model_copy(update={"turn_no": arena.turn_no + 1})
    memory.observe(next_arena)
    next_analysis = analyze_arena(next_arena, planner_memory=memory)
    next_intents, _, _ = decide_turn(
        analysis=next_analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert first_target is not None
    assert next_intents[0].target_position == first_target


def test_bootstrap_finish_can_trigger_same_turn_relocation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    arena.constructions = [ConstructionView(position=main.position.model_copy(update={"x": main.position.x + 1}), progress=45)]
    arena.enemy = []
    arena.beavers = []
    for cell in arena.cells:
        if cell.position == main.position:
            cell.terraformation_progress = 85

    analysis = analyze_arena(arena)
    intents, upgrade, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert intents
    assert intents[0].kind == "finish_build"
    assert upgrade is not None
    assert upgrade.name == "repair_power"
    assert relocate is not None
    assert relocate.to_position == arena.constructions[0].position


def test_frontier_candidates_skip_branch_off_expiring_single_support() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.constructions = []
    arena.enemy = []
    arena.beavers = []

    expiring_support = next(item for item in arena.plantations if not item.is_main)
    for cell in arena.cells:
        if cell.position == expiring_support.position:
            cell.terraformation_progress = 70

    analysis = analyze_arena(arena)
    candidate_positions = {(item.position.x, item.position.y) for item in analysis.frontier_candidates}

    # (6,18) would extend only through the soon-to-expire plantation at (5,18), so it should not be proposed.
    assert (6, 18) not in candidate_positions


def test_small_network_upgrade_order_delays_decay_and_vision() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=24)]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = tier.max
        elif tier.name == "max_hp":
            tier.current = 2
        elif tier.name == "signal_range":
            tier.current = 1
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "max_hp"


def test_bootstrap_active_construction_prefers_repair_power_before_signal_range() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=25)]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = 2
        elif tier.name == "max_hp":
            tier.current = 1
        elif tier.name == "signal_range":
            tier.current = 0
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "repair_power"


def test_opening_upgrade_ladder_keeps_repair_power_until_tier_three_even_after_hp_spend() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=28)]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = 1
        elif tier.name == "max_hp":
            tier.current = 3
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "repair_power"


def test_bootstrap_active_construction_prefers_max_hp_before_second_signal_tier() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=25)]
    for cell in arena.cells:
        if cell.position == arena.plantations[0].position:
            cell.terraformation_progress = 45
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = tier.max
        elif tier.name == "max_hp":
            tier.current = 3
        elif tier.name == "signal_range":
            tier.current = 1
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "max_hp"


def test_post_speedcap_opening_prefers_decay_before_first_signal_tier() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=30)]
    for cell in arena.cells:
        if cell.position == arena.plantations[0].position:
            cell.terraformation_progress = 55
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = tier.max
        elif tier.name == "max_hp":
            tier.current = tier.max
        elif tier.name == "signal_range":
            tier.current = 0
        elif tier.name == "decay_mitigation":
            tier.current = 0
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "decay_mitigation"


def test_opening_upgrade_ladder_starts_hp_after_third_repair_tier() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [next(item for item in arena.plantations if item.is_main)]
    arena.constructions = [ConstructionView(position=Coordinate(x=5, y=18), progress=30)]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = 3
        elif tier.name == "max_hp":
            tier.current = 0
        elif tier.name == "signal_range":
            tier.current = 1
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert upgrade is not None
    assert upgrade.name == "max_hp"


def test_beaver_visible_prefers_safe_perimeter_build_before_attack() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=10, y=18)})]
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=4, y=18)}),
        arena.plantations[1].model_copy(update={"position": Coordinate(x=5, y=18)}),
        arena.plantations[1].model_copy(update={"id": "p-2", "position": Coordinate(x=4, y=19), "hp": 50}),
        arena.plantations[1].model_copy(update={"id": "p-3", "position": Coordinate(x=5, y=19), "hp": 50}),
    ]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    build_intents = [item for item in intents if item.kind == "build"]
    beaver_intents = [item for item in intents if item.kind == "beaver_attack"]

    assert build_intents
    assert not beaver_intents
    nearest_dist = chebyshev_distance(build_intents[0].target_position, arena.beavers[0].position)
    assert nearest_dist >= 3


def test_beaver_hunt_waits_for_five_live_bases_even_if_perimeter_is_ready() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=10, y=10), "hp": 20})]
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=8, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=8, y=9), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=8, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=9, y=10), "hp": 50, "is_main": False}),
    ]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 4
    assert not [item for item in intents if item.kind == "beaver_attack"]


def test_opening_does_not_take_beaver_mitigation_before_five_live_bases() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=10, y=12)})]
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = 3
        elif tier.name == "max_hp":
            tier.current = 4
        elif tier.name == "signal_range":
            tier.current = tier.max
        elif tier.name == "earthquake_mitigation":
            tier.current = tier.max
        elif tier.name == "decay_mitigation":
            tier.current = 1
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert analysis.stats.connected_plantations == 4
    assert upgrade is not None
    assert upgrade.name != "beaver_damage_mitigation"


def test_small_network_blocked_by_beaver_prefers_mitigation_before_signal() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.cells = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=13, y=10), "hp": 100})]
    arena.mountains = [
        Coordinate(x=9, y=10),
        Coordinate(x=9, y=11),
        Coordinate(x=10, y=9),
        Coordinate(x=11, y=9),
        Coordinate(x=10, y=12),
        Coordinate(x=11, y=12),
    ]
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]
    for tier in arena.upgrades.tiers:
        if tier.name == "repair_power":
            tier.current = 3
        elif tier.name == "signal_range":
            tier.current = 1
        else:
            tier.current = 0
    arena.upgrades.points = 1

    analysis = analyze_arena(arena)
    upgrade = recommend_upgrade(analysis)

    assert analysis.stats.connected_plantations == 4
    assert upgrade is not None
    assert upgrade.name == "beaver_damage_mitigation"


def test_small_connected_cluster_can_assign_more_than_three_builders() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    arena.cells = []
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-4", "position": Coordinate(x=12, y=10), "hp": 50, "is_main": False}),
    ]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    build_intent = next(item for item in intents if item.kind == "build")

    assert analysis.stats.connected_plantations == 5
    assert build_intent.desired_contributors > 3


def test_two_node_core_relocates_before_opening_next_build_from_fresh_anchor() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 50}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-safe", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 15, "turns_until_degradation": 85}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 5, "turns_until_degradation": 95}),
    ]
    arena.plantations = [main, anchor]

    analysis = analyze_arena(arena)
    intents, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.stats.connected_plantations == 2
    assert relocate is not None
    assert relocate.to_position == anchor.position
    assert not build_intents


def test_compact_core_relocates_to_youngest_adjacent_anchor() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 50}
    )
    anchor_old = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-old", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}
    )
    anchor_young = anchor_old.model_copy(update={"id": "anchor-young", "position": Coordinate(x=10, y=11)})
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    arena.plantations = [main, anchor_old, anchor_young]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 50, "turns_until_degradation": 50}),
        template_cell.model_copy(update={"position": anchor_old.position, "terraformation_progress": 70, "turns_until_degradation": 30}),
        template_cell.model_copy(update={"position": anchor_young.position, "terraformation_progress": 10, "turns_until_degradation": 70}),
    ]

    analysis = analyze_arena(arena)
    _, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 3
    assert analysis.stats.hq_remaining_turns == 10
    assert relocate is not None
    assert relocate.to_position == anchor_young.position


def test_compact_core_relocates_early_even_with_parallel_construction() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 50}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-safe", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [main, anchor]
    arena.constructions = [ConstructionView(position=Coordinate(x=12, y=10), progress=15)]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 50, "turns_until_degradation": 50}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 5, "turns_until_degradation": 70}),
    ]

    analysis = analyze_arena(arena)
    _, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 2
    assert analysis.stats.hq_remaining_turns == 10
    assert relocate is not None
    assert relocate.to_position == anchor.position


def test_fresh_adjacent_anchor_blocks_new_build_until_handoff() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=9, y=143), "hp": 90}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-fresh", "position": Coordinate(x=9, y=142), "hp": 100, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    arena.plantations = [main, anchor]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 70, "turns_until_degradation": 26}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 5, "turns_until_degradation": 39}),
    ]

    analysis = analyze_arena(arena)
    intents, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 2
    assert analysis.stats.hq_remaining_turns == 6
    assert relocate is not None
    assert relocate.to_position == anchor.position
    assert not [item for item in intents if item.kind == "build"]


def test_compact_core_relocates_immediately_after_second_anchor_completes() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=10, y=10), "hp": 50}
    )
    anchor = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "anchor-fresh", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    arena.plantations = [main, anchor]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 10, "turns_until_degradation": 90}),
        template_cell.model_copy(update={"position": anchor.position, "terraformation_progress": 0, "turns_until_degradation": 100}),
    ]

    analysis = analyze_arena(arena)
    _, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    assert analysis.stats.connected_plantations == 2
    assert analysis.stats.hq_remaining_turns == 18
    assert relocate is not None
    assert relocate.to_position == anchor.position


def test_post_handoff_second_anchor_build_stays_adjacent_to_current_main() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=11, y=10), "hp": 90}
    )
    old_support = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "old-support", "position": Coordinate(x=10, y=10), "hp": 100, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []
    arena.plantations = [main, old_support]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 5, "turns_until_degradation": 39}),
        template_cell.model_copy(update={"position": old_support.position, "terraformation_progress": 85, "turns_until_degradation": 23}),
    ]

    analysis = analyze_arena(arena)
    intents, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.opening_stage == "second_anchor"
    assert relocate is None
    assert build_intents
    assert all(
        abs(item.target_position.x - main.position.x) + abs(item.target_position.y - main.position.y) == 1
        for item in build_intents
    )


def test_two_node_post_handoff_finishes_existing_main_adjacent_construction_before_new_build() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main).model_copy(
        update={"position": Coordinate(x=11, y=10), "hp": 90}
    )
    old_support = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"id": "old-support", "position": Coordinate(x=10, y=10), "hp": 100, "is_main": False}
    )
    arena.enemy = []
    arena.beavers = []
    arena.plantations = [main, old_support]
    arena.constructions = [ConstructionView(position=Coordinate(x=12, y=10), progress=20)]
    template_cell = arena.cells[0]
    arena.cells = [
        template_cell.model_copy(update={"position": main.position, "terraformation_progress": 5, "turns_until_degradation": 39}),
        template_cell.model_copy(update={"position": old_support.position, "terraformation_progress": 85, "turns_until_degradation": 23}),
    ]

    analysis = analyze_arena(arena)
    intents, _, relocate = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    finish_intents = [item for item in intents if item.kind == "finish_build"]
    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.opening_stage in {"second_anchor", "double_lane"}
    assert relocate is None
    assert finish_intents
    assert finish_intents[0].target_position == Coordinate(x=12, y=10)
    assert not build_intents


def test_compact_core_finishes_existing_construction_before_opening_new_one() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.beavers = []
    arena.cells = []
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]
    arena.constructions = [ConstructionView(position=Coordinate(x=9, y=10), progress=25)]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    finish_intents = [item for item in intents if item.kind == "finish_build"]
    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.stats.connected_plantations == 4
    assert analysis.stats.safe_hq_moves_count >= 1
    assert finish_intents
    assert not build_intents


def test_small_network_prefers_beaver_bypass_build_before_attack() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.cells = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=13, y=10), "hp": 100})]
    arena.mountains = []
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    build_intents = [item for item in intents if item.kind == "build"]
    beaver_intents = [item for item in intents if item.kind == "beaver_attack"]

    assert analysis.stats.connected_plantations == 4
    assert build_intents
    assert not beaver_intents
    nearest_dist = min(chebyshev_distance(item.target_position, arena.beavers[0].position) for item in build_intents)
    assert nearest_dist >= 3


def test_small_network_attacks_beaver_when_no_bypass_exists() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    support = next(item for item in arena.plantations if not item.is_main)
    arena.enemy = []
    arena.constructions = []
    arena.cells = []
    arena.beavers = [arena.beavers[0].model_copy(update={"position": Coordinate(x=13, y=10), "hp": 20})]
    arena.mountains = [
        Coordinate(x=9, y=10),
        Coordinate(x=9, y=11),
        Coordinate(x=10, y=9),
        Coordinate(x=11, y=9),
        Coordinate(x=10, y=12),
        Coordinate(x=11, y=12),
    ]
    arena.plantations = [
        main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50}),
        support.model_copy(update={"id": "p-1", "position": Coordinate(x=11, y=10), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-2", "position": Coordinate(x=10, y=11), "hp": 50, "is_main": False}),
        support.model_copy(update={"id": "p-3", "position": Coordinate(x=11, y=11), "hp": 50, "is_main": False}),
    ]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    beaver_intents = [item for item in intents if item.kind == "beaver_attack"]
    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.stats.connected_plantations == 4
    assert beaver_intents
    assert not build_intents


def test_seed_anchor_still_serializes_when_only_hq_anchor_is_under_construction() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.enemy = []
    arena.beavers = []
    arena.cells = []
    arena.plantations = [main.model_copy(update={"position": Coordinate(x=10, y=10), "hp": 50})]
    arena.constructions = [ConstructionView(position=Coordinate(x=11, y=10), progress=25)]

    analysis = analyze_arena(arena)
    intents, _, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )

    finish_intents = [item for item in intents if item.kind == "finish_build"]
    build_intents = [item for item in intents if item.kind == "build"]

    assert analysis.opening_stage == "seed_anchor"
    assert finish_intents
    assert not build_intents


def test_planner_memory_resets_when_turn_number_rolls_back() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    memory = PlannerMemory()
    memory.observe(arena)
    memory.lock_bootstrap_target(arena.plantations[0].position, Coordinate(x=arena.plantations[0].position.x + 1, y=arena.plantations[0].position.y))
    memory.path_fail_streaks[((1, 1), (1, 2), (1, 3))] = 2

    next_round_arena = arena.model_copy(update={"turn_no": 1})
    memory.last_observed_turn = 25
    memory.observe(next_round_arena)

    assert memory.last_observed_turn == 1
    assert memory.locked_bootstrap_target is None
    assert not memory.path_fail_streaks


def test_planner_memory_projects_known_cells_forward_during_degradation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena = arena.model_copy(
        update={
            "turn_no": 10,
            "cells": [
                TerraformedCellView(
                    position=Coordinate(x=20, y=20),
                    terraformation_progress=100,
                    turns_until_degradation=3,
                )
            ],
        }
    )
    memory = PlannerMemory()
    memory.observe(arena)

    later_arena = arena.model_copy(
        update={
            "turn_no": 18,
            "cells": [],
        }
    )
    augmented = memory.augment_arena(later_arena)

    remembered = next(cell for cell in augmented.cells if cell.position == Coordinate(x=20, y=20))
    assert remembered.terraformation_progress == 50
    assert remembered.turns_until_degradation == 0


def test_planner_memory_drops_known_cells_after_full_decay() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    arena = arena.model_copy(
        update={
            "turn_no": 10,
            "cells": [
                TerraformedCellView(
                    position=Coordinate(x=21, y=21),
                    terraformation_progress=40,
                    turns_until_degradation=1,
                )
            ],
        }
    )
    memory = PlannerMemory()
    memory.observe(arena)

    later_arena = arena.model_copy(
        update={
            "turn_no": 20,
            "cells": [],
        }
    )
    augmented = memory.augment_arena(later_arena)

    assert not [cell for cell in augmented.cells if cell.position == Coordinate(x=21, y=21)]


def test_execution_plan_drops_unverified_relocation() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    target = main.position.model_copy(update={"x": main.position.x + 1})
    arena.constructions = [ConstructionView(position=target, progress=30)]
    arena.enemy = []
    arena.beavers = []

    analysis = analyze_arena(arena)
    intents, upgrade, _ = decide_turn(
        analysis=analysis,
        weights=StrategyRegistry().get_weights("frontier"),
        manual_directives=[],
    )
    execution = build_execution_plan(
        analysis=analysis,
        intents=intents,
        recommended_upgrade=upgrade,
        recommended_relocation=RelocateMainPlanView(
            from_position=main.position,
            to_position=target,
            urgency="critical",
            reason="test",
        ),
    )

    assert execution.relocate_main is None


def test_execution_plan_keeps_existing_relocation_target_available_as_author() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    helper = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"position": main.position.model_copy(update={"x": main.position.x + 1})}
    )
    arena.plantations = [main, helper]
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []

    analysis = analyze_arena(arena)
    intent_target = helper.position.model_copy(update={"y": helper.position.y + 1})
    execution = build_execution_plan(
        analysis=analysis,
        intents=[
            StrategicIntentView(
                id="busy-relocate-test",
                kind="build",
                priority=120,
                summary="Use relocation target as an author",
                reason="test",
                target_position=intent_target,
                desired_contributors=1,
                preferred_author_ids=[helper.id],
            )
        ],
        recommended_upgrade=None,
        recommended_relocation=RelocateMainPlanView(
            from_position=main.position,
            to_position=helper.position,
            urgency="critical",
            reason="test",
        ),
    )

    assert any(action.author_id == helper.id for action in execution.actions)
    assert execution.relocate_main == [main.position, helper.position]
    assert execution.payload is not None
    assert execution.payload.relocate_main == [main.position, helper.position]


def test_execution_plan_reserves_current_main_author_for_existing_handoff() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    helper = next(item for item in arena.plantations if not item.is_main).model_copy(
        update={"position": main.position.model_copy(update={"x": main.position.x + 1})}
    )
    arena.plantations = [main, helper]
    arena.enemy = []
    arena.beavers = []
    arena.constructions = []

    analysis = analyze_arena(arena)
    intent_target = main.position.model_copy(update={"y": main.position.y - 1})
    execution = build_execution_plan(
        analysis=analysis,
        intents=[
            StrategicIntentView(
                id="busy-main-relocate-test",
                kind="build",
                priority=120,
                summary="Use current main as an author",
                reason="test",
                target_position=intent_target,
                desired_contributors=1,
                preferred_author_ids=[main.id],
            )
        ],
        recommended_upgrade=None,
        recommended_relocation=RelocateMainPlanView(
            from_position=main.position,
            to_position=helper.position,
            urgency="critical",
            reason="test",
        ),
    )

    assert not execution.actions
    assert execution.relocate_main == [main.position, helper.position]
    assert execution.payload is not None
    assert execution.payload.command == []


def test_mock_build_then_relocate_same_turn() -> None:
    provider = DatsSolMockProvider()
    arena = provider._bootstrap()
    main = next(item for item in arena.plantations if item.is_main)
    arena.plantations = [main]
    target = main.position.model_copy(update={"x": main.position.x + 1})
    arena.constructions = [ConstructionView(position=target, progress=45)]
    arena.enemy = []
    arena.beavers = []
    provider._state = arena

    result = asyncio.run(
        provider.submit(
            PlayerCommandPayload(
                command=[
                    PlantationActionPayload(path=[main.position, main.position, target]),
                ],
                relocate_main=[main.position, target],
            ),
            submit_mode="live",
        )
    )

    updated = asyncio.run(provider.observe())
    relocated_main = next(item for item in updated.plantations if item.is_main)

    assert result.accepted
    assert relocated_main.position == target


def test_runtime_live_round_rollover_resets_and_processes_new_turn() -> None:
    async def run_case() -> RuntimeService:
        provider = DatsSolMockProvider()
        older_arena = provider._bootstrap()
        newer_arena = older_arena.model_copy(update={"turn_no": 5})

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._world = runtime._empty_world().model_copy(update={"turn": 600})
        runtime._last_processed_turn = 600
        runtime._last_submit_dispatched_turn = 600
        runtime._last_submit_acked_turn = 600
        runtime._last_speculative_submit_turn = 600
        runtime._last_observed_arena = older_arena.model_copy(update={"turn_no": 600})
        runtime._planner_memory.last_observed_turn = 600

        async def fake_submit(*args, **kwargs):
            return SubmitResultView(dry_run=True, accepted=True, errors=[], provider_message="dry-run")

        async def fake_broadcast():
            return None

        runtime._submit_with_guards = fake_submit
        runtime._persist_turn = lambda *args, **kwargs: None
        runtime._broadcast_state = fake_broadcast

        await runtime._handle_observed_world(newer_arena, force=False, async_live_submit=False)
        return runtime

    runtime = asyncio.run(run_case())

    assert runtime._world.turn == 5
    assert runtime._last_processed_turn == 5
    assert runtime._last_submit_dispatched_turn == -1
    assert runtime._last_submit_acked_turn == -1
    assert runtime._planner_memory.last_observed_turn == 5


def test_runtime_live_pre_round_zero_clears_stale_round_state() -> None:
    async def run_case() -> RuntimeService:
        provider = DatsSolMockProvider()
        old_arena = provider._bootstrap().model_copy(update={"turn_no": 600})
        zero_arena = provider._bootstrap().model_copy(
            update={
                "turn_no": 0,
                "next_turn_in": 0.0,
                "plantations": [],
                "constructions": [],
                "enemy": [],
                "beavers": [],
                "cells": [],
            }
        )

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._world = runtime._empty_world().model_copy(update={"turn": 600})
        runtime._last_processed_turn = 600
        runtime._last_submit_dispatched_turn = 600
        runtime._last_submit_acked_turn = 600
        runtime._last_speculative_submit_turn = 600
        runtime._last_observed_arena = old_arena
        runtime._planner_memory.last_observed_turn = 600

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        await runtime._handle_observed_world(zero_arena, force=False, async_live_submit=False)
        return runtime

    runtime = asyncio.run(run_case())

    assert runtime._world.turn == 0
    assert runtime._last_processed_turn == -1
    assert runtime._last_submit_dispatched_turn == -1
    assert runtime._last_submit_acked_turn == -1
    assert runtime._last_speculative_submit_turn == -1
    assert runtime._last_observed_arena is None
    assert runtime._planner_memory.last_observed_turn == -1


def test_async_dispatch_is_not_marked_accepted_before_provider_ack() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_max_inflight_submit = 1

        arena = DatsSolMockProvider()._bootstrap()
        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)

        async def fake_submit(payload, submit_mode):
            await asyncio.sleep(0)
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        runtime._provider.submit = fake_submit
        dispatch = await runtime._dispatch_live_submit(arena, execution, imminent_earthquake=False)
        for _ in range(4):
            await asyncio.sleep(0)
            await runtime._drain_submit_tasks()
            if not runtime._submit_tasks:
                break
        return runtime, arena.turn_no, dispatch

    runtime, turn_no, dispatch = asyncio.run(run_case())

    assert not dispatch.accepted
    assert runtime._last_submit_dispatched_turn == turn_no
    assert runtime._last_submit_acked_turn == turn_no


def test_async_dispatch_skips_turn_already_dispatched_even_without_inflight_task() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"

        arena = DatsSolMockProvider()._bootstrap()
        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)

        runtime._last_submit_dispatched_turn = arena.turn_no
        runtime._submit_tasks = {}

        return await runtime._dispatch_live_submit(arena, execution, imminent_earthquake=False)

    submission = asyncio.run(run_case())

    assert submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Live submit was already dispatched for this turn."


def test_live_submit_guard_skips_late_turn_window() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.datssol_server_mode = "test"
        runtime._settings.live_submit_deadline_seconds = 0.5

        arena = DatsSolMockProvider()._bootstrap().model_copy(update={"next_turn_in": 0.49})
        main = next(item for item in arena.plantations if item.is_main)
        arena.constructions = []
        arena.plantations.append(
            PlantationView(
                id="late-turn-support",
                position=Coordinate(x=main.position.x + 1, y=main.position.y + 1),
                hp=100,
                is_main=False,
                is_isolated=False,
                immunity_until_turn=0,
                terraform_progress=0,
                turns_until_cell_degradation=None,
                is_boosted_cell=False,
                connected=True,
                turns_to_completion=None,
                projected_income_per_turn=0,
                role="network",
            )
        )
        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert submission.dry_run
    assert not submission.accepted
    assert "late-turn" in submission.provider_message.lower()
    assert any("late turn submit skipped" in error for error in submission.errors)


def test_live_submit_guard_uses_tighter_deadline_on_production() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.datssol_server_mode = "production"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_production_deadline_seconds = 0.18
        runtime._settings.live_submit_bootstrap_deadline_seconds = 0.2

        arena = DatsSolMockProvider()._bootstrap().model_copy(update={"next_turn_in": 0.19})
        arena.plantations[0].terraform_progress = 55
        arena.plantations[0].turns_to_completion = 9

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_tighter_window_for_emergency_bootstrap() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.18

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.19,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=102, y=99),
                        progress=28,
                    )
                ],
            }
        )
        arena.plantations[0].terraform_progress = 80
        arena.plantations[0].turns_to_completion = 4

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_emergency_bootstrap_when_hq_turns_are_derived() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.18

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.44,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=102, y=99),
                        progress=36,
                    )
                ],
            }
        )
        arena.plantations[0].terraform_progress = 55
        arena.plantations[0].turns_to_completion = None

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_emergency_bootstrap_even_with_fresh_hq_cell() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.18

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.44,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=102, y=99),
                        progress=5,
                    )
                ],
            }
        )
        arena.plantations[0].terraform_progress = 0
        arena.plantations[0].turns_to_completion = None

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_tighter_window_for_active_construction_bootstrap() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.12

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.13,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=102, y=99),
                        progress=32,
                    )
                ],
            }
        )
        arena.plantations[0].terraform_progress = 75
        arena.plantations[0].turns_to_completion = 5

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_tighter_window_for_compact_critical_finish() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.12

        base = DatsSolMockProvider()._bootstrap()
        anchor = base.plantations[0].model_copy(
            update={
                "id": "anchor-1",
                "position": Coordinate(x=101, y=100),
                "is_main": False,
                "terraform_progress": 20,
                "turns_to_completion": 16,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.18,
                "plantations": [base.plantations[0].model_copy(deep=True), anchor],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=101, y=99),
                        progress=8,
                    )
                ],
            }
        )
        arena.plantations[0].terraform_progress = 85
        arena.plantations[0].turns_to_completion = 3

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_compact_build_window_on_tighter_deadline() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.datssol_server_mode = "production"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_production_deadline_seconds = 0.18
        runtime._settings.live_submit_compact_build_deadline_seconds = 0.06

        base = DatsSolMockProvider()._bootstrap()
        main = base.plantations[0].model_copy(
            update={"terraform_progress": 0, "turns_to_completion": None},
            deep=True,
        )
        helper = base.plantations[0].model_copy(
            update={
                "id": "anchor-1",
                "position": Coordinate(x=main.position.x + 1, y=main.position.y),
                "is_main": False,
                "terraform_progress": 0,
                "turns_to_completion": None,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.064,
                "plantations": [main, helper],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=main.position.x, y=main.position.y - 1),
                        progress=5,
                    )
                ],
            }
        )
        for cell in arena.cells:
            if cell.position.x == main.position.x and cell.position.y == main.position.y:
                cell.terraformation_progress = 20

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_compact_critical_finish_when_hq_turns_are_derived_from_cell() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.12

        base = DatsSolMockProvider()._bootstrap()
        main = base.plantations[0].model_copy(
            update={
                "terraform_progress": 0,
                "turns_to_completion": None,
            },
            deep=True,
        )
        anchor = base.plantations[0].model_copy(
            update={
                "id": "anchor-1",
                "position": Coordinate(x=101, y=100),
                "is_main": False,
                "terraform_progress": 20,
                "turns_to_completion": 16,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.18,
                "plantations": [main, anchor],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=101, y=99),
                        progress=8,
                    )
                ],
            }
        )
        for cell in arena.cells:
            if cell.position.x == main.position.x and cell.position.y == main.position.y:
                cell.terraformation_progress = 95

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_tighter_window_for_compact_existing_handoff() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.12

        base = DatsSolMockProvider()._bootstrap()
        main = base.plantations[0].model_copy(
            update={
                "terraform_progress": 90,
                "turns_to_completion": 2,
            },
            deep=True,
        )
        anchor = base.plantations[0].model_copy(
            update={
                "id": "anchor-existing",
                "position": Coordinate(x=main.position.x, y=main.position.y - 1),
                "is_main": False,
                "terraform_progress": 20,
                "turns_to_completion": 16,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.18,
                "plantations": [main, anchor],
                "constructions": [],
            }
        )
        execution = build_execution_plan(
            analysis=analyze_arena(arena),
            intents=[],
            recommended_upgrade=None,
            recommended_relocation=RelocateMainPlanView(
                from_position=main.position,
                to_position=anchor.position,
                urgency="critical",
                reason="test",
            ),
        )
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_critical_compact_existing_handoff_in_0111s_window() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_emergency_deadline_seconds = 0.12
        runtime._settings.live_submit_compact_handoff_deadline_seconds = 0.1

        base = DatsSolMockProvider()._bootstrap()
        main = base.plantations[0].model_copy(
            update={
                "terraform_progress": 90,
                "turns_to_completion": 2,
            },
            deep=True,
        )
        anchor = base.plantations[0].model_copy(
            update={
                "id": "anchor-existing",
                "position": Coordinate(x=main.position.x, y=main.position.y - 1),
                "is_main": False,
                "terraform_progress": 5,
                "turns_to_completion": 19,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.111,
                "plantations": [main, anchor],
                "constructions": [],
            }
        )
        execution = build_execution_plan(
            analysis=analyze_arena(arena),
            intents=[],
            recommended_upgrade=None,
            recommended_relocation=RelocateMainPlanView(
                from_position=main.position,
                to_position=anchor.position,
                urgency="critical",
                reason="test",
            ),
        )
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_allows_tighter_window_for_bootstrap_seed() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_bootstrap_deadline_seconds = 0.2

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.212,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [],
            }
        )
        arena.plantations[0].terraform_progress = 55
        arena.plantations[0].turns_to_completion = 9

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert not submission.dry_run
    assert not submission.accepted
    assert submission.provider_message == "Provider submit outcome is uncertain."
    assert any("transport uncertain:" in error for error in submission.errors)


def test_live_submit_guard_skips_critical_bootstrap_seed_in_risky_window() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.datssol_server_mode = "test"
        runtime._settings.live_submit_deadline_seconds = 0.47
        runtime._settings.live_submit_bootstrap_deadline_seconds = 0.2
        runtime._settings.live_submit_critical_bootstrap_deadline_seconds = 0.3

        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "next_turn_in": 0.295,
                "plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)],
                "constructions": [],
            }
        )
        arena.plantations[0].terraform_progress = 90
        arena.plantations[0].turns_to_completion = 2

        analysis = analyze_arena(arena)
        intents, upgrade, relocate = decide_turn(
            analysis=analysis,
            weights=StrategyRegistry().get_weights("frontier"),
            manual_directives=[],
        )
        execution = build_execution_plan(analysis, intents, upgrade, relocate)
        return await runtime._submit_with_guards(arena, execution)

    submission = asyncio.run(run_case())

    assert submission.dry_run
    assert not submission.accepted
    assert "late-turn" in submission.provider_message.lower()
    assert any("late turn submit skipped" in error for error in submission.errors)


def test_live_submit_strips_relocation_to_unconfirmed_new_plantation() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"

        arena = DatsSolMockProvider()._bootstrap()
        main = next(item for item in arena.plantations if item.is_main)
        arena = arena.model_copy(
            update={
                "next_turn_in": 0.9,
                "plantations": [main.model_copy(deep=True)],
                "constructions": [
                    ConstructionView(
                        position=Coordinate(x=main.position.x + 1, y=main.position.y),
                        progress=45,
                    )
                ],
            }
        )
        analysis = analyze_arena(arena)
        target = arena.constructions[0].position
        execution = build_execution_plan(
            analysis=analysis,
            intents=[
                StrategicIntentView(
                    id="finish-anchor",
                    kind="finish_build",
                    priority=130,
                    summary="Finish anchor",
                    reason="test",
                    target_position=target,
                    desired_contributors=1,
                    preferred_author_ids=[main.id],
                )
            ],
            recommended_upgrade=None,
            recommended_relocation=RelocateMainPlanView(
                from_position=main.position,
                to_position=target,
                urgency="critical",
                reason="test",
            ),
        )
        captured: dict[str, object] = {}

        async def fake_submit(payload, submit_mode):
            captured["payload"] = payload.model_dump(mode="json")
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        runtime._provider.submit = fake_submit
        result = await runtime._submit_with_guards(arena, execution)
        return execution, captured["payload"], result, main.position, target

    execution, submitted_payload, result, _, _ = asyncio.run(run_case())

    assert result.accepted
    assert execution.relocate_main is None
    assert execution.payload.relocate_main is None
    assert execution.command_view.relocate_main is None
    assert submitted_payload["relocate_main"] is None


def test_live_submit_normalizes_relocation_source_to_current_main() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"

        arena = DatsSolMockProvider()._bootstrap()
        main = next(item for item in arena.plantations if item.is_main).model_copy(
            update={"position": Coordinate(x=20, y=20)}
        )
        target_plantation = next(item for item in arena.plantations if not item.is_main).model_copy(
            update={"position": Coordinate(x=21, y=20)}
        )
        arena = arena.model_copy(
            update={
                "next_turn_in": 0.9,
                "plantations": [main, target_plantation],
                "constructions": [],
            }
        )
        analysis = analyze_arena(arena)
        execution = build_execution_plan(
            analysis=analysis,
            intents=[],
            recommended_upgrade=None,
            recommended_relocation=RelocateMainPlanView(
                from_position=Coordinate(x=19, y=20),
                to_position=target_plantation.position,
                urgency="critical",
                reason="test",
            ),
        )
        captured: dict[str, object] = {}

        async def fake_submit(payload, submit_mode):
            captured["payload"] = payload.model_dump(mode="json")
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        runtime._provider.submit = fake_submit
        result = await runtime._submit_with_guards(arena, execution)
        return execution, captured["payload"], result, main.position

    execution, submitted_payload, result, main_position = asyncio.run(run_case())

    assert result.accepted
    assert execution.relocate_main is not None
    assert execution.relocate_main[0] == main_position
    assert execution.payload.relocate_main[0] == main_position
    assert execution.command_view.relocate_main[0] == main_position
    assert submitted_payload["relocate_main"][0] == main_position.model_dump(mode="json")


def test_submit_guard_strips_unconfirmed_relocation_when_finish_is_not_guaranteed() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = DatsSolMockProvider()
        runtime._submit_mode = "live"
        runtime._settings.live_submit_deadline_seconds = 0.05
        main = PlantationView(
            id="main",
            position=Coordinate(x=10, y=10),
            hp=50,
            is_main=True,
            is_isolated=False,
            immunity_until_turn=0,
            terraform_progress=95,
            turns_to_completion=1,
        )
        target = Coordinate(x=11, y=10)
        arena = DatsSolMockProvider()._bootstrap().model_copy(
            update={
                "turn_no": 15,
                "next_turn_in": 0.6,
                "plantations": [main],
                "constructions": [
                    ConstructionView(
                        position=target,
                        progress=41,
                    )
                ],
            }
        )
        analysis = analyze_arena(arena)
        execution = build_execution_plan(
            analysis=analysis,
            intents=[
                StrategicIntentView(
                    id="finish-anchor",
                    kind="finish_build",
                    priority=130,
                    summary="Finish anchor",
                    reason="test",
                    target_position=target,
                    desired_contributors=0,
                    preferred_author_ids=[],
                )
            ],
            recommended_upgrade=None,
            recommended_relocation=RelocateMainPlanView(
                from_position=main.position,
                to_position=target,
                urgency="critical",
                reason="test",
            ),
        )
        captured: dict[str, object] = {}

        async def fake_submit(payload, submit_mode):
            captured["payload"] = payload.model_dump(mode="json")
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        runtime._provider.submit = fake_submit
        result = await runtime._submit_with_guards(arena, execution)
        return execution, captured["payload"], result

    execution, submitted_payload, result = asyncio.run(run_case())

    assert result.accepted
    assert execution.relocate_main is None
    assert execution.payload.relocate_main is None
    assert execution.command_view.relocate_main is None
    assert submitted_payload["relocate_main"] is None


def test_main_jump_requires_submit_reset_for_non_adjacent_respawn() -> None:
    previous = DatsSolMockProvider()._bootstrap().model_copy(
        update={"plantations": [DatsSolMockProvider()._bootstrap().plantations[0].model_copy(deep=True)]}
    )
    current_main = previous.plantations[0].model_copy(deep=True)
    current_main.position = Coordinate(x=150, y=150)
    current = previous.model_copy(update={"turn_no": previous.turn_no + 1, "plantations": [current_main]})

    assert RuntimeService._main_jump_requires_submit_reset(previous, current)


def test_cancel_pending_submit_tasks_clears_stale_async_submits() -> None:
    async def run_case():
        runtime = RuntimeService()
        task = asyncio.create_task(asyncio.sleep(10))
        runtime._submit_tasks = {
            12: {
                "task": task,
                "actions": [],
                "payload": {},
                "imminent_earthquake": False,
                "started_at": 0.0,
            }
        }
        await runtime._cancel_pending_submit_tasks(reason="test", tick_number=13)
        return runtime, task

    runtime, task = asyncio.run(run_case())

    assert runtime._submit_tasks == {}
    assert task.cancelled()
    assert runtime._force_sync_live_submit_until_turn == 15


def test_runtime_uses_sync_submit_briefly_after_main_jump_reset() -> None:
    async def run_case() -> tuple[bool, RuntimeService]:
        arena = DatsSolMockProvider()._bootstrap()
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._force_sync_live_submit_until_turn = arena.turn_no
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        called = {"sync": False}

        async def fake_sync_submit(observed_world, execution):
            called["sync"] = True
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError("async live submit should be suppressed during post-jump sync window")

        runtime._submit_with_guards = fake_sync_submit
        runtime._dispatch_live_submit = forbidden_dispatch

        await runtime._handle_observed_world(arena, force=True, async_live_submit=True)
        return called["sync"], runtime

    used_sync_submit, runtime = asyncio.run(run_case())

    assert used_sync_submit
    assert runtime._world.turn == 1


def test_runtime_uses_sync_submit_for_critical_single_node_finish_window() -> None:
    async def run_case() -> tuple[bool, RuntimeService]:
        arena = DatsSolMockProvider()._bootstrap()
        main = next(item for item in arena.plantations if item.is_main)
        arena.plantations = [main.model_copy(update={"terraform_progress": 95, "turns_to_completion": 1})]
        arena.constructions = [ConstructionView(position=Coordinate(x=main.position.x - 1, y=main.position.y), progress=40)]

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        called = {"sync": False}

        async def fake_sync_submit(observed_world, execution):
            called["sync"] = True
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError("async live submit should be suppressed during critical single-node finish windows")

        runtime._submit_with_guards = fake_sync_submit
        runtime._dispatch_live_submit = forbidden_dispatch

        await runtime._handle_observed_world(arena, force=True, async_live_submit=True)
        return called["sync"], runtime

    used_sync_submit, runtime = asyncio.run(run_case())

    assert used_sync_submit
    assert runtime._world.turn == 1


def test_runtime_uses_sync_submit_for_critical_single_node_finish_window_when_cell_is_ahead() -> None:
    async def run_case() -> tuple[bool, RuntimeService]:
        arena = DatsSolMockProvider()._bootstrap()
        main = next(item for item in arena.plantations if item.is_main)
        arena.plantations = [main.model_copy(update={"terraform_progress": 0, "turns_to_completion": None})]
        arena.constructions = [ConstructionView(position=Coordinate(x=main.position.x - 1, y=main.position.y), progress=40)]
        arena.cells = [
            cell.model_copy(
                update={"terraformation_progress": 95}
                if cell.position.x == main.position.x and cell.position.y == main.position.y
                else {}
            )
            for cell in arena.cells
        ]

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        called = {"sync": False}

        async def fake_sync_submit(observed_world, execution):
            called["sync"] = True
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError("async live submit should be suppressed when the cell is the only accurate HQ lifetime source")

        runtime._submit_with_guards = fake_sync_submit
        runtime._dispatch_live_submit = forbidden_dispatch

        await runtime._handle_observed_world(arena, force=True, async_live_submit=True)
        return called["sync"], runtime

    used_sync_submit, runtime = asyncio.run(run_case())

    assert used_sync_submit
    assert runtime._world.turn == 1


def test_runtime_uses_sync_submit_for_compact_build_window_even_when_hq_is_not_critical() -> None:
    async def run_case() -> tuple[bool, RuntimeService]:
        arena = DatsSolMockProvider()._bootstrap()
        main = next(item for item in arena.plantations if item.is_main)
        helper = main.model_copy(
            update={
                "id": "anchor-1",
                "position": Coordinate(x=main.position.x + 1, y=main.position.y),
                "is_main": False,
                "terraform_progress": 0,
                "turns_to_completion": None,
            },
            deep=True,
        )
        arena.plantations = [main.model_copy(update={"terraform_progress": 0, "turns_to_completion": None}), helper]
        arena.constructions = [ConstructionView(position=Coordinate(x=main.position.x, y=main.position.y - 1), progress=8)]
        arena.cells = [
            cell.model_copy(
                update={"terraformation_progress": 20}
                if cell.position.x == main.position.x and cell.position.y == main.position.y
                else {}
            )
            for cell in arena.cells
        ]

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        called = {"sync": False}

        async def fake_sync_submit(observed_world, execution):
            called["sync"] = True
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError("async live submit should be suppressed during compact build windows")

        runtime._submit_with_guards = fake_sync_submit
        runtime._dispatch_live_submit = forbidden_dispatch

        await runtime._handle_observed_world(arena, force=True, async_live_submit=True)
        return called["sync"], runtime

    used_sync_submit, runtime = asyncio.run(run_case())

    assert used_sync_submit
    assert runtime._world.turn == 1


def test_runtime_uses_sync_submit_for_critical_existing_adjacent_handoff_window() -> None:
    async def run_case() -> tuple[bool, RuntimeService]:
        base = DatsSolMockProvider()._bootstrap()
        main = base.plantations[0].model_copy(
            update={
                "terraform_progress": 90,
                "turns_to_completion": 2,
            },
            deep=True,
        )
        anchor = base.plantations[0].model_copy(
            update={
                "id": "anchor-existing",
                "position": Coordinate(x=main.position.x, y=main.position.y - 1),
                "is_main": False,
                "terraform_progress": 5,
                "turns_to_completion": 19,
            },
            deep=True,
        )
        arena = base.model_copy(
            update={
                "next_turn_in": 0.111,
                "plantations": [main, anchor],
                "constructions": [],
            }
        )

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        called = {"sync": False}

        async def fake_sync_submit(observed_world, execution):
            called["sync"] = True
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        async def forbidden_dispatch(*args, **kwargs):
            raise AssertionError("async live submit should be suppressed during critical existing-handoff windows")

        runtime._submit_with_guards = fake_sync_submit
        runtime._dispatch_live_submit = forbidden_dispatch

        await runtime._handle_observed_world(arena, force=True, async_live_submit=True)
        return called["sync"], runtime

    used_sync_submit, runtime = asyncio.run(run_case())

    assert used_sync_submit
    assert runtime._world.turn == 1


def test_runtime_resets_planner_memory_after_main_jump() -> None:
    async def run_case() -> bool:
        previous = DatsSolMockProvider()._bootstrap().model_copy(update={"turn_no": 10})
        current_main = previous.plantations[0].model_copy(deep=True)
        current_main.position = Coordinate(x=150, y=150)
        current = previous.model_copy(update={"turn_no": 11, "plantations": [current_main]})

        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._last_observed_arena = previous
        runtime._schedule_server_logs_refresh = lambda: []
        runtime._persist_turn = lambda *args, **kwargs: None

        async def fake_broadcast():
            return None

        runtime._broadcast_state = fake_broadcast

        reset_called = {"value": False}
        memory = PlannerMemory()
        original_reset = memory.reset

        def wrapped_reset():
            reset_called["value"] = True
            original_reset()

        memory.reset = wrapped_reset
        runtime._planner_memory = memory

        async def fake_submit(observed_world, execution):
            return SubmitResultView(dry_run=False, accepted=True, errors=[], provider_message="ack")

        runtime._submit_with_guards = fake_submit
        runtime._dispatch_live_submit = fake_submit

        await runtime._handle_observed_world(current, force=True, async_live_submit=True)
        return reset_called["value"]

    assert asyncio.run(run_case())


def test_speculative_submit_is_disabled_by_default() -> None:
    async def run_case():
        runtime = RuntimeService()
        runtime._provider = SimpleNamespace(key="datssol-live", label="DatsSol Live")
        runtime._submit_mode = "live"
        runtime._settings.live_enable_speculative_submit = False
        runtime._observe_failure_streak = 3
        runtime._last_observed_at = 1.0
        runtime._last_observed_arena = DatsSolMockProvider()._bootstrap().model_copy(update={"turn_no": 10, "next_turn_in": 0.1})
        runtime._predicted_live_turn = lambda: 11

        async def forbidden(*args, **kwargs):
            raise AssertionError("speculative submit should not run when disabled")

        runtime._dispatch_live_submit = forbidden
        await runtime._attempt_speculative_turn()

    asyncio.run(run_case())
