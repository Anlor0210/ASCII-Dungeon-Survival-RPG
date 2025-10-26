"""Enemy definitions and basic AI behaviours."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from map_gen import DungeonMap, TILE_WALL


@dataclass
class Enemy:
    """Base class for enemies wandering the dungeon."""

    species: str
    hp: int
    attack: int
    defense: int
    xp_reward: int
    position: Tuple[int, int]
    symbol: str = "e"
    drop_table: Sequence[Tuple[str, float, int]] = field(default_factory=list)
    can_phase: bool = False
    aggressive_radius: int = 6
    awakened: bool = True

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_turn(
        self,
        dungeon: DungeonMap,
        player_pos: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
        rng: Optional[random.Random] = None,
    ) -> Optional[str]:
        """Perform a single AI step.

        Returns an optional string message when notable actions occur.  Movement
        uses a simple breadth-first search towards the player's position when
        the enemy is aware of the player.  Sub-classes override or extend this
        behaviour to provide flavour.
        """

        rng = rng or random.Random()
        if not self.awakened:
            if self.distance(player_pos) <= 1:
                self.awakened = True
                return f"The {self.species} reveals itself!"
            return None

        if self.distance(player_pos) > self.aggressive_radius:
            return None
        next_step = self.path_towards(dungeon, player_pos, occupied, allow_walls=self.can_phase)
        if next_step and next_step not in occupied:
            occupied.discard(self.position)
            self.position = next_step
            occupied.add(self.position)
            if self.position == player_pos:
                return f"The {self.species} lunges from the dark!"
        return None

    def path_towards(
        self,
        dungeon: DungeonMap,
        target: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
        allow_walls: bool = False,
    ) -> Optional[Tuple[int, int]]:
        from collections import deque

        start = self.position
        if start == target:
            return start
        queue = deque([start])
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        while queue:
            current = queue.popleft()
            if current == target:
                break
            for nx, ny in self.neighbours(current):
                if not dungeon.in_bounds(nx, ny):
                    continue
                if not allow_walls and not dungeon.is_walkable(nx, ny):
                    continue
                if allow_walls and dungeon.get_tile(nx, ny) == TILE_WALL:
                    # Ghosts can pass through but still avoid map boundaries.
                    pass
                elif not dungeon.is_walkable(nx, ny):
                    continue
                if (nx, ny) in occupied and (nx, ny) != target:
                    continue
                if (nx, ny) in came_from:
                    continue
                came_from[(nx, ny)] = current
                queue.append((nx, ny))
        else:
            return None
        # Reconstruct path.
        if target not in came_from:
            return None
        current = target
        while came_from[current] != start:
            current = came_from[current]
            if current is None:
                return None
        return current

    def neighbours(self, pos: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        x, y = pos
        yield x + 1, y
        yield x - 1, y
        yield x, y + 1
        yield x, y - 1

    def distance(self, other: Tuple[int, int]) -> int:
        return abs(self.position[0] - other[0]) + abs(self.position[1] - other[1])

    def attack_damage(self, rng: Optional[random.Random] = None) -> int:
        rng = rng or random.Random()
        return max(1, self.attack + rng.randint(-1, 2))

    def take_damage(self, amount: int) -> int:
        damage = max(1, amount - self.defense)
        self.hp -= damage
        return damage

    def roll_loot(self, rng: Optional[random.Random] = None) -> List[str]:
        rng = rng or random.Random()
        loot: List[str] = []
        for name, chance, quantity in self.drop_table:
            if rng.random() <= chance:
                loot.extend([name] * quantity)
        return loot

    def to_dict(self) -> Dict[str, object]:
        return {
            "species": self.species,
            "hp": self.hp,
            "attack": self.attack,
            "defense": self.defense,
            "xp_reward": self.xp_reward,
            "position": list(self.position),
            "symbol": self.symbol,
            "drop_table": [list(entry) for entry in self.drop_table],
            "can_phase": self.can_phase,
            "aggressive_radius": self.aggressive_radius,
            "awakened": self.awakened,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Enemy":
        enemy = cls(
            species=str(data["species"]),
            hp=int(data["hp"]),
            attack=int(data["attack"]),
            defense=int(data["defense"]),
            xp_reward=int(data.get("xp_reward", 5)),
            position=tuple(data.get("position", (0, 0))),  # type: ignore[arg-type]
            symbol=str(data.get("symbol", "e")),
            drop_table=[tuple(entry) for entry in data.get("drop_table", [])],  # type: ignore[list-item]
            can_phase=bool(data.get("can_phase", False)),
            aggressive_radius=int(data.get("aggressive_radius", 6)),
            awakened=bool(data.get("awakened", True)),
        )
        return enemy


class Ghost(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Ghost",
            hp=18,
            attack=7,
            defense=1,
            xp_reward=14,
            position=position,
            symbol="G",
            drop_table=[("Essence", 0.6, 1)],
            can_phase=True,
            aggressive_radius=8,
        )

    def take_turn(self, dungeon: DungeonMap, player_pos: Tuple[int, int], occupied: Set[Tuple[int, int]], rng=None):
        message = super().take_turn(dungeon, player_pos, occupied, rng)
        return message


class Rat(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Rat",
            hp=8,
            attack=4,
            defense=0,
            xp_reward=6,
            position=position,
            symbol="r",
            drop_table=[("Meat", 0.4, 1)],
            aggressive_radius=5,
        )


class Skeleton(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Skeleton",
            hp=20,
            attack=6,
            defense=2,
            xp_reward=12,
            position=position,
            symbol="s",
            drop_table=[("Bone", 0.5, 1), ("Bandage", 0.2, 1)],
            aggressive_radius=6,
        )


class Shadowling(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Shadowling",
            hp=16,
            attack=5,
            defense=1,
            xp_reward=11,
            position=position,
            symbol="h",
            drop_table=[("Essence", 0.3, 1), ("Torch", 0.2, 1)],
            aggressive_radius=7,
        )

    def take_turn(self, dungeon: DungeonMap, player_pos: Tuple[int, int], occupied: Set[Tuple[int, int]], rng=None):
        rng = rng or random.Random()
        if self.distance(player_pos) <= 2 and rng.random() < 0.3:
            # Shadowlings attempt a flanking move by sidestepping.
            options = [
                (self.position[0] + dx, self.position[1] + dy)
                for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1))
            ]
            rng.shuffle(options)
            for nx, ny in options:
                if not dungeon.in_bounds(nx, ny):
                    continue
                if (nx, ny) in occupied:
                    continue
                if dungeon.is_walkable(nx, ny):
                    occupied.discard(self.position)
                    self.position = (nx, ny)
                    occupied.add(self.position)
                    break
        return super().take_turn(dungeon, player_pos, occupied, rng)


class Mimic(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Mimic",
            hp=24,
            attack=7,
            defense=3,
            xp_reward=18,
            position=position,
            symbol="M",
            drop_table=[("Ether Potion", 0.5, 1), ("Essence", 0.4, 1)],
            aggressive_radius=4,
            awakened=False,
        )


def enemy_factory(enemy_type: str, position: Tuple[int, int]) -> Enemy:
    mapping = {
        "Rat": Rat,
        "Skeleton": Skeleton,
        "Ghost": Ghost,
        "Shadowling": Shadowling,
        "Mimic": Mimic,
    }
    cls = mapping.get(enemy_type, Enemy)
    if cls is Enemy:
        return cls(
            species=enemy_type,
            hp=10,
            attack=4,
            defense=1,
            xp_reward=5,
            position=position,
        )
    return cls(position)
