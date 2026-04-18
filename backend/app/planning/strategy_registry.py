from __future__ import annotations

from app.schemas.game import StrategyDefinition, StrategyWeights


class StrategyRegistry:
    def __init__(self) -> None:
        self._definitions = {
            "frontier": StrategyDefinition(
                key="frontier",
                label="Frontier Bloom",
                description="Default expansion strategy: grow a connected lattice, prioritize boosted cells and preserve the moving core.",
            ),
            "beaver-hunter": StrategyDefinition(
                key="beaver-hunter",
                label="Beaver Hunter",
                description="More aggressive toward beaver lairs when they block valuable terrain or can be burst efficiently.",
            ),
            "survival": StrategyDefinition(
                key="survival",
                label="Survival Mesh",
                description="Conservative network with stronger repair and hazard avoidance.",
            ),
            "raider": StrategyDefinition(
                key="raider",
                label="Raider",
                description="Contest nearby opponents and punish weak frontier plantations.",
            ),
        }

        self._weights = {
            "frontier": StrategyWeights(
                expansion_bias=0.88,
                support_bias=0.76,
                boosted_cell_bias=0.95,
                safety_bias=0.72,
                beaver_hunt_bias=0.42,
                sabotage_bias=0.28,
                hq_safety_margin=0.82,
                risk_cap=0.66,
                construction_cap=4,
                output_load_cap=3,
            ),
            "beaver-hunter": StrategyWeights(
                expansion_bias=0.74,
                support_bias=0.68,
                boosted_cell_bias=0.84,
                safety_bias=0.64,
                beaver_hunt_bias=0.91,
                sabotage_bias=0.24,
                hq_safety_margin=0.74,
                risk_cap=0.78,
                construction_cap=3,
                output_load_cap=3,
            ),
            "survival": StrategyWeights(
                expansion_bias=0.61,
                support_bias=0.92,
                boosted_cell_bias=0.7,
                safety_bias=0.95,
                beaver_hunt_bias=0.22,
                sabotage_bias=0.18,
                hq_safety_margin=0.92,
                risk_cap=0.54,
                construction_cap=3,
                output_load_cap=2,
            ),
            "raider": StrategyWeights(
                expansion_bias=0.7,
                support_bias=0.63,
                boosted_cell_bias=0.82,
                safety_bias=0.55,
                beaver_hunt_bias=0.35,
                sabotage_bias=0.88,
                hq_safety_margin=0.68,
                risk_cap=0.84,
                construction_cap=3,
                output_load_cap=4,
            ),
        }

    def definitions(self) -> list[StrategyDefinition]:
        return list(self._definitions.values())

    def get_definition(self, key: str) -> StrategyDefinition:
        return self._definitions.get(key, self._definitions["frontier"])

    def get_weights(self, key: str) -> StrategyWeights:
        return self._weights.get(key, self._weights["frontier"]).model_copy(deep=True)
