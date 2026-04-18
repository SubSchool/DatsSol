from __future__ import annotations

from app.schemas.game import Coordinate


def chebyshev_distance(a: Coordinate, b: Coordinate) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def is_cardinal_neighbor(a: Coordinate, b: Coordinate) -> bool:
    return manhattan_distance(a, b) == 1


def within_square_radius(origin: Coordinate, target: Coordinate, radius: int) -> bool:
    return abs(origin.x - target.x) <= radius and abs(origin.y - target.y) <= radius


def cardinal_neighbors(origin: Coordinate) -> list[Coordinate]:
    return [
        Coordinate(x=origin.x + 1, y=origin.y),
        Coordinate(x=origin.x - 1, y=origin.y),
        Coordinate(x=origin.x, y=origin.y + 1),
        Coordinate(x=origin.x, y=origin.y - 1),
    ]


def is_boosted_cell(position: Coordinate) -> bool:
    return position.x % 7 == 0 and position.y % 7 == 0


def clamp_to_map(position: Coordinate, width: int, height: int) -> bool:
    return 0 <= position.x < width and 0 <= position.y < height
