from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from app.schemas.game import (
    ArenaObservation,
    BeaverView,
    Coordinate,
    EnemyPlantationView,
    PlannedActionView,
    SubmitResultView,
    TerraformedCellView,
)


def _pos_key(position) -> tuple[int, int]:
    return (position.x, position.y)


def _path_key(action: PlannedActionView) -> tuple[tuple[int, int], ...]:
    return tuple((point.x, point.y) for point in action.path)


@dataclass
class PendingActionTarget:
    kind: str
    target_position: tuple[int, int]
    issued_turn: int
    ignore_no_progress_once: bool = False


@dataclass
class KnownEnemy:
    id: str
    position: tuple[int, int]
    hp: int
    last_seen_turn: int


@dataclass
class KnownBeaver:
    id: str
    position: tuple[int, int]
    hp: int
    last_seen_turn: int


@dataclass
class PlannerMemory:
    completion_turns: deque[int] = field(default_factory=lambda: deque(maxlen=256))
    expiration_turns: deque[int] = field(default_factory=lambda: deque(maxlen=256))
    previous_plantation_ids: set[str] = field(default_factory=set)
    previous_construction_progress: dict[tuple[int, int], int] = field(default_factory=dict)
    stagnant_construction_streaks: dict[tuple[int, int], int] = field(default_factory=dict)
    path_fail_streaks: dict[tuple[tuple[int, int], ...], int] = field(default_factory=dict)
    path_blocked_until: dict[tuple[tuple[int, int], ...], int] = field(default_factory=dict)
    pending_action_targets: dict[tuple[tuple[int, int], ...], PendingActionTarget] = field(default_factory=dict)
    last_observed_turn: int = -1
    turns_without_assets: int = 0
    last_mode: str = "economy"
    known_mountains: set[tuple[int, int]] = field(default_factory=set)
    known_cells: dict[tuple[int, int], tuple[int, int, int]] = field(default_factory=dict)
    known_enemy: dict[str, KnownEnemy] = field(default_factory=dict)
    known_beavers: dict[str, KnownBeaver] = field(default_factory=dict)
    locked_bootstrap_target: tuple[int, int] | None = None
    locked_bootstrap_origin: tuple[int, int] | None = None
    previous_main_position: tuple[int, int] | None = None

    @staticmethod
    def _project_known_cell(
        progress: int,
        turns_until_degradation: int,
        turns_elapsed: int,
    ) -> tuple[int, int] | None:
        if progress <= 0:
            return None
        if turns_elapsed <= 0:
            return (progress, max(0, turns_until_degradation))

        remaining_grace = max(0, turns_until_degradation - turns_elapsed)
        degrading_turns = max(0, turns_elapsed - turns_until_degradation)
        projected_progress = max(0, progress - (degrading_turns * 10))
        if projected_progress <= 0:
            return None
        return (projected_progress, remaining_grace)

    def reset(self) -> None:
        self.completion_turns.clear()
        self.expiration_turns.clear()
        self.previous_plantation_ids.clear()
        self.previous_construction_progress.clear()
        self.stagnant_construction_streaks.clear()
        self.path_fail_streaks.clear()
        self.path_blocked_until.clear()
        self.pending_action_targets.clear()
        self.last_observed_turn = -1
        self.turns_without_assets = 0
        self.last_mode = "economy"
        self.known_mountains.clear()
        self.known_cells.clear()
        self.known_enemy.clear()
        self.known_beavers.clear()
        self.locked_bootstrap_target = None
        self.locked_bootstrap_origin = None
        self.previous_main_position = None

    def bootstrap_target_for(self, main_position) -> tuple[int, int] | None:
        main_key = _pos_key(main_position)
        if self.locked_bootstrap_origin != main_key:
            return None
        return self.locked_bootstrap_target

    def lock_bootstrap_target(self, main_position, target_position) -> None:
        self.locked_bootstrap_origin = _pos_key(main_position)
        self.locked_bootstrap_target = _pos_key(target_position)

    def clear_bootstrap_target(self) -> None:
        self.locked_bootstrap_target = None
        self.locked_bootstrap_origin = None

    def _remember_world(self, arena: ArenaObservation) -> None:
        self.known_mountains.update(_pos_key(item) for item in arena.mountains)
        for cell in arena.cells:
            self.known_cells[_pos_key(cell.position)] = (
                cell.terraformation_progress,
                cell.turns_until_degradation,
                arena.turn_no,
            )
        for enemy in arena.enemy:
            self.known_enemy[enemy.id] = KnownEnemy(
                id=enemy.id,
                position=_pos_key(enemy.position),
                hp=enemy.hp,
                last_seen_turn=arena.turn_no,
            )
        for beaver in arena.beavers:
            self.known_beavers[beaver.id] = KnownBeaver(
                id=beaver.id,
                position=_pos_key(beaver.position),
                hp=beaver.hp,
                last_seen_turn=arena.turn_no,
            )

        occupied = {_pos_key(item.position) for item in arena.plantations} | {_pos_key(item.position) for item in arena.constructions}
        self.known_enemy = {
            enemy_id: enemy
            for enemy_id, enemy in self.known_enemy.items()
            if (arena.turn_no - enemy.last_seen_turn) <= 15 and enemy.position not in occupied
        }
        self.known_beavers = {
            beaver_id: beaver
            for beaver_id, beaver in self.known_beavers.items()
            if (arena.turn_no - beaver.last_seen_turn) <= 180 and beaver.position not in occupied
        }

    def augment_arena(self, arena: ArenaObservation) -> ArenaObservation:
        cell_positions = {_pos_key(cell.position) for cell in arena.cells}
        enemy_ids = {enemy.id for enemy in arena.enemy}
        beaver_ids = {beaver.id for beaver in arena.beavers}

        merged_cells = list(arena.cells)
        refreshed_known_cells: dict[tuple[int, int], tuple[int, int, int]] = {}
        for position, (progress, turns_until_deg, _) in self.known_cells.items():
            if position in cell_positions:
                refreshed_known_cells[position] = (
                    progress,
                    turns_until_deg,
                    arena.turn_no,
                )
                continue
            projected = self._project_known_cell(
                progress,
                turns_until_deg,
                max(0, arena.turn_no - self.last_observed_turn),
            )
            if projected is None:
                continue
            projected_progress, projected_turns_until_deg = projected
            refreshed_known_cells[position] = (
                projected_progress,
                projected_turns_until_deg,
                arena.turn_no,
            )
            merged_cells.append(
                TerraformedCellView(
                    position=Coordinate(x=position[0], y=position[1]),
                    terraformation_progress=projected_progress,
                    turns_until_degradation=projected_turns_until_deg,
                )
            )
        self.known_cells = refreshed_known_cells

        merged_enemy = list(arena.enemy)
        for enemy_id, enemy in self.known_enemy.items():
            if enemy_id in enemy_ids:
                continue
            merged_enemy.append(
                EnemyPlantationView(
                    id=enemy.id,
                    position=Coordinate(x=enemy.position[0], y=enemy.position[1]),
                    hp=enemy.hp,
                )
            )

        merged_beavers = list(arena.beavers)
        for beaver_id, beaver in self.known_beavers.items():
            if beaver_id in beaver_ids:
                continue
            merged_beavers.append(
                BeaverView(
                    id=beaver.id,
                    position=Coordinate(x=beaver.position[0], y=beaver.position[1]),
                    hp=beaver.hp,
                )
            )

        return arena.model_copy(
            update={
                "cells": merged_cells,
                "enemy": merged_enemy,
                "beavers": merged_beavers,
                "mountains": [Coordinate(x=x, y=y) for x, y in sorted(self.known_mountains)],
            }
        )

    def observe(self, arena: ArenaObservation) -> None:
        if self.last_observed_turn >= 0 and arena.turn_no < self.last_observed_turn:
            self.reset()
        if arena.turn_no == self.last_observed_turn:
            return

        current_plantation_ids = {plantation.id for plantation in arena.plantations}
        current_construction_progress = {
            _pos_key(construction.position): construction.progress for construction in arena.constructions
        }
        current_plantation_positions = {_pos_key(plantation.position) for plantation in arena.plantations}
        current_enemy_positions = {_pos_key(enemy.position) for enemy in arena.enemy}
        current_beaver_positions = {_pos_key(beaver.position) for beaver in arena.beavers}
        self._remember_world(arena)
        self.path_blocked_until = {
            path_key: blocked_until
            for path_key, blocked_until in self.path_blocked_until.items()
            if blocked_until > arena.turn_no
        }

        main = next((plantation for plantation in arena.plantations if plantation.is_main), None)
        current_main_position = _pos_key(main.position) if main else None
        if current_main_position != self.previous_main_position:
            if self.locked_bootstrap_origin != current_main_position:
                self.clear_bootstrap_target()
            self.previous_main_position = current_main_position
        if (
            self.locked_bootstrap_target
            and (
                self.locked_bootstrap_target in current_plantation_positions
                or self.locked_bootstrap_target in current_enemy_positions
                or self.locked_bootstrap_target in current_beaver_positions
                or self.locked_bootstrap_target in self.known_mountains
            )
        ):
            self.clear_bootstrap_target()

        resolved_pending: list[tuple[tuple[tuple[int, int], ...], PendingActionTarget]] = [
            (path_key, pending)
            for path_key, pending in self.pending_action_targets.items()
            if pending.issued_turn < arena.turn_no
        ]
        for path_key, pending in resolved_pending:
            kind = pending.kind
            target_position = pending.target_position
            if kind in {"build", "finish_build"}:
                previous_progress = self.previous_construction_progress.get(target_position, 0)
                current_progress = current_construction_progress.get(target_position, 0)
                target_became_plantation = target_position in current_plantation_positions
                if target_became_plantation or current_progress > previous_progress:
                    self.path_fail_streaks[path_key] = 0
                    self.path_blocked_until.pop(path_key, None)
                elif pending.ignore_no_progress_once:
                    self.path_fail_streaks[path_key] = 0
                    self.path_blocked_until.pop(path_key, None)
                else:
                    next_fail_streak = self.path_fail_streaks.get(path_key, 0) + 1
                    self.path_fail_streaks[path_key] = next_fail_streak
                    if next_fail_streak >= 2:
                        self.path_blocked_until[path_key] = arena.turn_no + 3
            del self.pending_action_targets[path_key]

        completed_positions = {
            position
            for position in current_plantation_positions
            if self.previous_construction_progress.get(position, 0) > 0
        }
        for _ in completed_positions:
            self.completion_turns.append(arena.turn_no)

        lost_count = max(0, len(self.previous_plantation_ids - current_plantation_ids))
        for _ in range(lost_count):
            self.expiration_turns.append(arena.turn_no)

        next_stagnant: dict[tuple[int, int], int] = {}
        for position, progress in current_construction_progress.items():
            previous_progress = self.previous_construction_progress.get(position)
            if previous_progress is None:
                next_stagnant[position] = 0
                continue
            next_stagnant[position] = self.stagnant_construction_streaks.get(position, 0) + 1 if progress <= previous_progress else 0
        self.stagnant_construction_streaks = next_stagnant

        self.turns_without_assets = self.turns_without_assets + 1 if not arena.plantations and not arena.constructions else 0
        self.previous_plantation_ids = current_plantation_ids
        self.previous_construction_progress = current_construction_progress
        self.last_observed_turn = arena.turn_no

    def note_submission(
        self,
        actions: list[PlannedActionView],
        submission: SubmitResultView,
        *,
        imminent_earthquake: bool = False,
        issued_turn: int | None = None,
    ) -> None:
        if not actions or submission.dry_run or not submission.accepted:
            return
        submission_turn = self.last_observed_turn if issued_turn is None else issued_turn
        for action in actions:
            key = _path_key(action)
            self.pending_action_targets[key] = PendingActionTarget(
                kind=action.kind,
                target_position=_pos_key(action.target_position),
                issued_turn=submission_turn,
                ignore_no_progress_once=imminent_earthquake and action.kind == "build",
            )

    def completion_rate(self, current_turn: int, window: int = 20) -> float:
        return round(sum(1 for turn in self.completion_turns if (current_turn - turn) < window) / window, 3)

    def expiration_rate(self, current_turn: int, window: int = 20) -> float:
        return round(sum(1 for turn in self.expiration_turns if (current_turn - turn) < window) / window, 3)

    def stagnant_streak(self, position: tuple[int, int]) -> int:
        return self.stagnant_construction_streaks.get(position, 0)

    def path_fail_streak(self, action: PlannedActionView) -> int:
        return self.path_fail_streaks.get(_path_key(action), 0)

    def is_path_blocked(self, action: PlannedActionView, current_turn: int) -> bool:
        if action.kind == "build":
            return False
        return self.path_blocked_until.get(_path_key(action), -1) > current_turn
