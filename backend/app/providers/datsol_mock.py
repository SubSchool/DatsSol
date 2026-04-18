from __future__ import annotations

from copy import deepcopy
from math import ceil
from random import Random

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
    SubmitResultView,
    TerraformedCellView,
    BeaverView,
)


def _key(position: Coordinate) -> tuple[int, int]:
    return (position.x, position.y)


class DatsSolMockProvider(ArenaProvider):
    key = "datssol-mock"
    label = "DatsSol Mock Sandbox"

    def __init__(self) -> None:
        self._rng = Random(77)
        self._status = ProviderStatus(ready=True, message="Mock sandbox ready.")
        self._next_id = 3
        self._spawn = Coordinate(x=4, y=18)
        self._construction_last_progress: dict[tuple[int, int], int] = {}
        self._server_logs: list[GameServerLogEntry] = []
        self._state = self._bootstrap()

    def _bootstrap(self) -> ArenaObservation:
        mountains = [
            Coordinate(x=x, y=y)
            for x in range(0, 48)
            for y in range(0, 36)
            if (x in {18, 19, 28} and 5 <= y <= 28) or (y == 11 and 10 <= x <= 22)
        ]
        arena = ArenaObservation(
            turn_no=1,
            next_turn_in=1.0,
            width=48,
            height=36,
            action_range=2,
            plantations=[
                PlantationView(
                    id="p-main",
                    position=Coordinate(x=4, y=18),
                    hp=50,
                    is_main=True,
                    immunity_until_turn=3,
                ),
                PlantationView(
                    id="p-1",
                    position=Coordinate(x=5, y=18),
                    hp=42,
                ),
            ],
            enemy=[
                EnemyPlantationView(id="enemy-1", position=Coordinate(x=37, y=14), hp=48),
                EnemyPlantationView(id="enemy-2", position=Coordinate(x=38, y=15), hp=50),
                EnemyPlantationView(id="enemy-3", position=Coordinate(x=36, y=15), hp=33),
            ],
            constructions=[
                ConstructionView(position=Coordinate(x=6, y=18), progress=25),
                ConstructionView(position=Coordinate(x=5, y=19), progress=10),
            ],
            beavers=[
                BeaverView(id="beaver-1", position=Coordinate(x=12, y=18), hp=100),
                BeaverView(id="beaver-2", position=Coordinate(x=29, y=8), hp=100),
                BeaverView(id="beaver-3", position=Coordinate(x=33, y=26), hp=100),
            ],
            cells=[
                TerraformedCellView(position=Coordinate(x=4, y=18), terraformation_progress=30, turns_until_degradation=80),
                TerraformedCellView(position=Coordinate(x=5, y=18), terraformation_progress=12, turns_until_degradation=80),
                TerraformedCellView(position=Coordinate(x=37, y=14), terraformation_progress=56, turns_until_degradation=80),
                TerraformedCellView(position=Coordinate(x=38, y=15), terraformation_progress=18, turns_until_degradation=80),
            ],
            mountains=mountains,
            forecasts=[
                MeteoForecastView(kind="earthquake", turns_until=6),
                MeteoForecastView(
                    kind="sandstorm",
                    id="storm-alpha",
                    forming=True,
                    turns_until=4,
                    position=Coordinate(x=24, y=18),
                    next_position=Coordinate(x=26, y=20),
                    radius=4,
                ),
            ],
            upgrades=PlantationUpgradesState(
                points=1,
                interval_turns=30,
                turns_until_points=12,
                max_points=15,
                tiers=[
                    PlantationUpgradeTier(name="repair_power", current=0, max=3),
                    PlantationUpgradeTier(name="max_hp", current=0, max=5),
                    PlantationUpgradeTier(name="settlement_limit", current=0, max=10),
                    PlantationUpgradeTier(name="signal_range", current=0, max=10),
                    PlantationUpgradeTier(name="vision_range", current=0, max=5),
                    PlantationUpgradeTier(name="decay_mitigation", current=0, max=3),
                    PlantationUpgradeTier(name="earthquake_mitigation", current=0, max=3),
                    PlantationUpgradeTier(name="beaver_damage_mitigation", current=0, max=5),
                ],
            ),
        )
        self._server_logs = [
            GameServerLogEntry(time="mock", message="Spawned main plantation on the western ridge."),
            GameServerLogEntry(time="mock", message="Initial survey complete."),
        ]
        return arena

    def _tier_value(self, name: str) -> int:
        tier = next((item for item in self._state.upgrades.tiers if item.name == name), None)
        return tier.current if tier else 0

    def _plantation_by_position(self) -> dict[tuple[int, int], PlantationView]:
        return {_key(item.position): item for item in self._state.plantations}

    def _enemy_by_position(self) -> dict[tuple[int, int], EnemyPlantationView]:
        return {_key(item.position): item for item in self._state.enemy}

    def _beaver_by_position(self) -> dict[tuple[int, int], BeaverView]:
        return {_key(item.position): item for item in self._state.beavers}

    def _construction_by_position(self) -> dict[tuple[int, int], ConstructionView]:
        return {_key(item.position): item for item in self._state.constructions}

    async def observe(self) -> ArenaObservation:
        return deepcopy(self._state)

    async def submit(self, payload: PlayerCommandPayload, submit_mode: str) -> SubmitResultView:
        if payload.is_empty():
            return SubmitResultView(
                dry_run=False,
                accepted=True,
                code=0,
                errors=["empty command: no plantation actions, no relocateMain, and no plantationUpgrade provided"],
                provider_message="Mock sandbox accepted the empty command with a warning.",
            )

        exit_loads: dict[tuple[int, int], int] = {}
        self._apply_upgrade(payload.plantation_upgrade)

        own_by_pos = self._plantation_by_position()
        enemy_by_pos = self._enemy_by_position()
        beaver_by_pos = self._beaver_by_position()
        construction_by_pos = self._construction_by_position()

        for action in payload.command:
            if len(action.path) < 3:
                continue
            author, exit_position, target = action.path
            if _key(author) not in own_by_pos:
                continue
            load = exit_loads.get(_key(exit_position), 0)
            exit_loads[_key(exit_position)] = load + 1

            target_key = _key(target)
            if target_key in own_by_pos:
                power = max(0, (5 + self._tier_value("repair_power")) - load)
                if power <= 0:
                    continue
                if target_key == _key(author):
                    continue
                own_by_pos[target_key].hp = min(50 + self._tier_value("max_hp") * 10, own_by_pos[target_key].hp + power)
            elif target_key in enemy_by_pos:
                power = max(0, 5 - load)
                if power <= 0:
                    continue
                enemy_by_pos[target_key].hp = max(0, enemy_by_pos[target_key].hp - 5 + self._rng.randint(0, 1))
                if enemy_by_pos[target_key].hp == 0:
                    self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"Enemy plantation at {target.x},{target.y} was destroyed."))
            elif target_key in beaver_by_pos:
                power = max(0, 5 - load)
                if power <= 0:
                    continue
                beaver_by_pos[target_key].hp = max(0, beaver_by_pos[target_key].hp - max(1, 5 - load))
                if beaver_by_pos[target_key].hp == 0:
                    self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"Beaver lair {beaver_by_pos[target_key].id} destroyed."))
            else:
                power = max(0, (5 + self._tier_value("repair_power")) - load)
                if power <= 0:
                    continue
                construction = construction_by_pos.get(target_key)
                if construction is None:
                    construction = ConstructionView(position=target, progress=0)
                    self._state.constructions.append(construction)
                    construction_by_pos[target_key] = construction
                construction.progress += power
                self._construction_last_progress[target_key] = self._state.turn_no

        self._state.enemy = [item for item in enemy_by_pos.values() if item.hp > 0]
        self._state.beavers = [item for item in beaver_by_pos.values() if item.hp > 0]
        self._process_constructions()
        self._apply_relocation(payload.relocate_main)
        self._advance_turn()

        return SubmitResultView(
            dry_run=False,
            accepted=True,
            code=0,
            errors=[],
            provider_message="Mock sandbox executed the turn.",
        )

    def _apply_upgrade(self, upgrade_name: str | None) -> None:
        if not upgrade_name or self._state.upgrades.points <= 0:
            return
        tier = next((item for item in self._state.upgrades.tiers if item.name == upgrade_name), None)
        if tier and tier.current < tier.max:
            tier.current += 1
            self._state.upgrades.points -= 1
            self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"Upgrade applied: {upgrade_name}."))

    def _apply_relocation(self, relocate_main: list[Coordinate] | None) -> None:
        if not relocate_main or len(relocate_main) != 2:
            return
        source_key = _key(relocate_main[0])
        target_key = _key(relocate_main[1])
        own_by_pos = self._plantation_by_position()
        source = own_by_pos.get(source_key)
        target = own_by_pos.get(target_key)
        if source and target and source.is_main:
            source.is_main = False
            target.is_main = True
            self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"Main control relocated to {target.position.x},{target.position.y}."))

    def _advance_turn(self) -> None:
        self._state.turn_no += 1
        self._state.next_turn_in = 1.0
        if self._state.turn_no > 600:
            self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message="Mock round completed. Resetting colony state for the next round."))
            self._state = self._bootstrap()
            self._construction_last_progress.clear()
            return
        self._state.upgrades.turns_until_points -= 1
        if self._state.upgrades.turns_until_points <= 0:
            self._state.upgrades.turns_until_points = self._state.upgrades.interval_turns
            if self._state.upgrades.points < self._state.upgrades.max_points:
                self._state.upgrades.points += 1

        self._process_forecasts()
        self._process_beavers()
        self._process_terraforming()
        self._update_isolation()

    def _process_constructions(self) -> None:
        max_hp = 50 + self._tier_value("max_hp") * 10
        decay = max(0, 10 - self._tier_value("decay_mitigation") * 2)
        remaining: list[ConstructionView] = []
        for construction in self._state.constructions:
            key = _key(construction.position)
            if construction.progress >= 50:
                new_plantation = PlantationView(
                    id=f"p-{self._next_id}",
                    position=construction.position,
                    hp=max_hp,
                    immunity_until_turn=self._state.turn_no + 3,
                )
                self._next_id += 1
                self._state.plantations.append(new_plantation)
                self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"New plantation founded at {construction.position.x},{construction.position.y}."))
                continue
            if self._construction_last_progress.get(key) != self._state.turn_no - 1:
                construction.progress = max(0, construction.progress - decay)
            if construction.progress > 0:
                remaining.append(construction)
        self._state.constructions = remaining

    def _process_forecasts(self) -> None:
        earthquake = next((item for item in self._state.forecasts if item.kind == "earthquake"), None)
        if earthquake:
            earthquake.turns_until = max(0, (earthquake.turns_until or 0) - 1)
            if earthquake.turns_until == 0:
                damage = max(0, 10 - self._tier_value("earthquake_mitigation") * 2)
                for plantation in self._state.plantations:
                    if plantation.immunity_until_turn > self._state.turn_no:
                        continue
                    plantation.hp = max(1 if plantation.is_main else 0, plantation.hp - damage)
                for construction in self._state.constructions:
                    construction.progress = max(0, construction.progress - damage)
                self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message="Earthquake hit the map."))
                earthquake.turns_until = 10

        storm = next((item for item in self._state.forecasts if item.kind == "sandstorm"), None)
        if storm and storm.forming:
            storm.turns_until = max(0, (storm.turns_until or 0) - 1)
            if storm.turns_until == 0:
                storm.forming = False
        elif storm and storm.position and storm.next_position:
            storm.position = storm.next_position
            storm.next_position = Coordinate(
                x=min(self._state.width - 1, storm.next_position.x + 2),
                y=min(self._state.height - 1, storm.next_position.y + 2),
            )
            for plantation in self._state.plantations:
                if plantation.immunity_until_turn > self._state.turn_no:
                    continue
                if abs(plantation.position.x - storm.position.x) <= (storm.radius or 0) and abs(plantation.position.y - storm.position.y) <= (storm.radius or 0):
                    plantation.hp = max(1, plantation.hp - 2)

    def _process_beavers(self) -> None:
        mitigation = self._tier_value("beaver_damage_mitigation") * 2
        for beaver in self._state.beavers:
            beaver.hp = min(100, beaver.hp + 5)
            for plantation in self._state.plantations:
                if plantation.immunity_until_turn > self._state.turn_no:
                    continue
                if abs(plantation.position.x - beaver.position.x) <= 2 and abs(plantation.position.y - beaver.position.y) <= 2:
                    plantation.hp = max(1 if plantation.is_main else 0, plantation.hp - max(0, 15 - mitigation))
            for construction in self._state.constructions:
                if abs(construction.position.x - beaver.position.x) <= 2 and abs(construction.position.y - beaver.position.y) <= 2:
                    construction.progress = max(0, construction.progress - max(0, 15 - mitigation))

        self._state.plantations = [item for item in self._state.plantations if item.hp > 0 or item.is_main]

    def _process_terraforming(self) -> None:
        cell_by_position = {_key(item.position): item for item in self._state.cells}
        remaining_plantations: list[PlantationView] = []
        for plantation in self._state.plantations:
            key = _key(plantation.position)
            cell = cell_by_position.get(key)
            if cell is None:
                cell = TerraformedCellView(
                    position=plantation.position,
                    terraformation_progress=0,
                    turns_until_degradation=80,
                )
                self._state.cells.append(cell)
                cell_by_position[key] = cell
            cell.terraformation_progress = min(100, cell.terraformation_progress + 5)
            if cell.terraformation_progress >= 100:
                self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message=f"Plantation at {plantation.position.x},{plantation.position.y} completed terraforming and vanished."))
                if plantation.is_main:
                    self._respawn_after_main_loss()
                    return
                continue
            remaining_plantations.append(plantation)
        self._state.plantations = remaining_plantations

        for cell in self._state.cells:
            if cell.terraformation_progress >= 100:
                cell.turns_until_degradation -= 1
                if cell.turns_until_degradation <= 0:
                    cell.terraformation_progress = max(0, cell.terraformation_progress - 10)

    def _update_isolation(self) -> None:
        main = next((item for item in self._state.plantations if item.is_main), None)
        if main is None:
            self._respawn_after_main_loss()
            return

        visited = set()
        queue = [main]
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            for plantation in self._state.plantations:
                if plantation.id == current.id:
                    continue
                if abs(plantation.position.x - current.position.x) + abs(plantation.position.y - current.position.y) == 1:
                    queue.append(plantation)

        decay = max(0, 10 - self._tier_value("decay_mitigation") * 2)
        for plantation in self._state.plantations:
            plantation.is_isolated = plantation.id not in visited
            if plantation.is_isolated and not plantation.is_main:
                plantation.hp = max(0, plantation.hp - decay)
        self._state.plantations = [item for item in self._state.plantations if item.hp > 0 or item.is_main]

    def _respawn_after_main_loss(self) -> None:
        self._server_logs.insert(0, GameServerLogEntry(time=f"T{self._state.turn_no}", message="Main plantation was lost. The colony respawned on the edge."))
        self._state.plantations = [
            PlantationView(
                id="p-main",
                position=self._spawn,
                hp=50,
                is_main=True,
                immunity_until_turn=self._state.turn_no + 3,
            )
        ]
        self._state.constructions = []

    async def fetch_server_logs(self) -> list[GameServerLogEntry]:
        return self._server_logs[:120]

    async def reset(self) -> None:
        self._state = self._bootstrap()
        self._construction_last_progress.clear()

    def status(self) -> ProviderStatus:
        return self._status
