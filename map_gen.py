"""Procedural map generation for The Depths of Ether."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from inventory import ITEM_LIBRARY


TILE_WALL = "#"
TILE_FLOOR = "."
TILE_SAFE = "S"
TILE_TREASURE = "$"
TILE_STAIRS = ">"
TILE_UNKNOWN = "?"


@dataclass
class Room:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def intersects(self, other: "Room") -> bool:
        return not (self.x2 < other.x1 or self.x1 > other.x2 or self.y2 < other.y1 or self.y1 > other.y2)

    def tiles(self) -> Iterable[Tuple[int, int]]:
        for x in range(self.x1, self.x2 + 1):
            for y in range(self.y1, self.y2 + 1):
                yield x, y


class DungeonMap:
    """Holds the generated dungeon layout."""

    def __init__(self, width: int = 40, height: int = 40, floor: int = 1):
        self.width = width
        self.height = height
        self.floor = floor
        self.tiles: List[List[str]] = [[TILE_WALL for _ in range(height)] for _ in range(width)]
        self.revealed: Set[Tuple[int, int]] = set()
        self.visible: Set[Tuple[int, int]] = set()
        self.rooms: List[Room] = []
        self.safe_rooms: List[Room] = []
        self.treasure_rooms: List[Room] = []
        self.items: Dict[Tuple[int, int], List[str]] = {}
        self.enemy_spawns: List[Tuple[str, Tuple[int, int]]] = []
        self.start_position: Tuple[int, int] = (1, 1)
        self.stairs_position: Tuple[int, int] = (width - 2, height - 2)

    # -- Serialisation ---------------------------------------------------
    def to_dict(self) -> Dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "floor": self.floor,
            "tiles": ["".join(column) for column in self.tiles],
            "revealed": [list(pos) for pos in self.revealed],
            "items": {f"{x},{y}": items for (x, y), items in self.items.items()},
            "enemy_spawns": [
                {"type": enemy_type, "position": list(pos)} for enemy_type, pos in self.enemy_spawns
            ],
            "start": list(self.start_position),
            "stairs": list(self.stairs_position),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "DungeonMap":
        width = int(data.get("width", 40))
        height = int(data.get("height", 40))
        floor = int(data.get("floor", 1))
        dungeon = cls(width=width, height=height, floor=floor)
        rows = data.get("tiles", [])
        if rows:
            for x, column in enumerate(rows):
                for y, char in enumerate(column):
                    if x < width and y < height:
                        dungeon.tiles[x][y] = char
        dungeon.revealed = {tuple(pos) for pos in data.get("revealed", [])}  # type: ignore[arg-type]
        dungeon.items = {}
        for key, values in data.get("items", {}).items():  # type: ignore[assignment]
            x_str, y_str = key.split(",")
            dungeon.items[(int(x_str), int(y_str))] = list(values)
        dungeon.enemy_spawns = [
            (entry["type"], tuple(entry["position"]))  # type: ignore[arg-type]
            for entry in data.get("enemy_spawns", [])
        ]
        dungeon.start_position = tuple(data.get("start", [1, 1]))  # type: ignore[arg-type]
        dungeon.stairs_position = tuple(data.get("stairs", [width - 2, height - 2]))  # type: ignore[arg-type]
        return dungeon

    # -- Tile helpers ----------------------------------------------------
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> str:
        if not self.in_bounds(x, y):
            return TILE_WALL
        return self.tiles[x][y]

    def set_tile(self, x: int, y: int, value: str) -> None:
        if self.in_bounds(x, y):
            self.tiles[x][y] = value

    def is_walkable(self, x: int, y: int) -> bool:
        return self.get_tile(x, y) in {TILE_FLOOR, TILE_SAFE, TILE_TREASURE, TILE_STAIRS}

    def reveal(self, position: Tuple[int, int]) -> None:
        self.revealed.add(position)

    def reveal_around(self, position: Tuple[int, int], radius: int) -> None:
        px, py = position
        self.visible.clear()
        for x in range(px - radius, px + radius + 1):
            for y in range(py - radius, py + radius + 1):
                if not self.in_bounds(x, y):
                    continue
                if abs(px - x) + abs(py - y) <= radius:
                    self.visible.add((x, y))
                    self.revealed.add((x, y))

    def place_item(self, position: Tuple[int, int], item_name: str) -> None:
        self.items.setdefault(position, []).append(item_name)

    def take_items(self, position: Tuple[int, int]) -> List[str]:
        return self.items.pop(position, [])

    def available_floor_tiles(self) -> List[Tuple[int, int]]:
        tiles: List[Tuple[int, int]] = []
        for x in range(self.width):
            for y in range(self.height):
                if self.tiles[x][y] in {TILE_FLOOR, TILE_SAFE, TILE_TREASURE}:
                    tiles.append((x, y))
        return tiles

    # -- Generation ------------------------------------------------------
    def generate(self, rng: Optional[random.Random] = None) -> None:
        rng = rng or random.Random()
        self.tiles = [[TILE_WALL for _ in range(self.height)] for _ in range(self.width)]
        self.rooms = []
        self.safe_rooms = []
        self.treasure_rooms = []
        self.items = {}
        self.enemy_spawns = []
        self.revealed.clear()
        max_rooms = 12
        min_size, max_size = 5, 9

        for _ in range(max_rooms * 2):
            w = rng.randint(min_size, max_size)
            h = rng.randint(min_size, max_size)
            x = rng.randint(1, self.width - w - 2)
            y = rng.randint(1, self.height - h - 2)
            new_room = Room(x, y, x + w, y + h)
            if any(new_room.intersects(other) for other in self.rooms):
                continue
            self.create_room(new_room)
            if self.rooms:
                prev_center = self.rooms[-1].center()
                new_center = new_room.center()
                self.create_corridor(prev_center, new_center, rng)
            self.rooms.append(new_room)

        if not self.rooms:
            # Guarantee at least one room exists.
            self.create_room(Room(1, 1, self.width // 2, self.height // 2))
            self.rooms.append(Room(1, 1, self.width // 2, self.height // 2))

        self.start_position = self.rooms[0].center()
        self.stairs_position = self.rooms[-1].center()
        self.set_tile(*self.stairs_position, TILE_STAIRS)

        # Safe room and treasure room selection.
        if len(self.rooms) >= 2:
            self.safe_rooms = [self.rooms[len(self.rooms) // 2]]
            self.mark_room(self.safe_rooms[0], TILE_SAFE)
        if len(self.rooms) >= 3:
            treasure_room = self.rooms[-2]
            self.treasure_rooms = [treasure_room]
            self.mark_room(treasure_room, TILE_TREASURE)

        self.populate_items(rng)
        self.populate_enemy_spawns(rng)
        self.reveal_around(self.start_position, 6)

    def create_room(self, room: Room) -> None:
        for x, y in room.tiles():
            self.set_tile(x, y, TILE_FLOOR)

    def create_corridor(self, start: Tuple[int, int], end: Tuple[int, int], rng: random.Random) -> None:
        x1, y1 = start
        x2, y2 = end
        if rng.random() < 0.5:
            self.carve_h(x1, x2, y1)
            self.carve_v(y1, y2, x2)
        else:
            self.carve_v(y1, y2, x1)
            self.carve_h(x1, x2, y2)

    def carve_h(self, x1: int, x2: int, y: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.set_tile(x, y, TILE_FLOOR)

    def carve_v(self, y1: int, y2: int, x: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.set_tile(x, y, TILE_FLOOR)

    def mark_room(self, room: Room, tile: str) -> None:
        for x, y in room.tiles():
            self.set_tile(x, y, tile)

    def populate_items(self, rng: random.Random) -> None:
        loot_candidates = [name for name, data in ITEM_LIBRARY.items() if data.get("type") != "weapon"]
        for room in self.rooms:
            if rng.random() < 0.35:
                x, y = room.center()
                item = rng.choice(loot_candidates)
                self.place_item((x, y), item)
        # Guarantee at least one torch and food item.
        self.place_item(self.start_position, "Torch")
        self.place_item(self.start_position, "Bread")

    def populate_enemy_spawns(self, rng: random.Random) -> None:
        enemy_types = ["Rat", "Skeleton", "Ghost", "Shadowling", "Mimic"]
        for room in self.rooms[1:]:
            if rng.random() < 0.6:
                count = rng.randint(1, 2)
                for _ in range(count):
                    x = rng.randint(room.x1, room.x2)
                    y = rng.randint(room.y1, room.y2)
                    enemy_type = rng.choice(enemy_types)
                    self.enemy_spawns.append((enemy_type, (x, y)))
