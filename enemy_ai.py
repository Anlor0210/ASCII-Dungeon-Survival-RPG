"""Enemy definitions, personalities and status handling for MVP7."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from map_gen import DungeonMap, TILE_WALL


StatusDict = Dict[str, int]


def _status_message(species: str, status: str) -> str:
    mapping = {
        "burn": f"The {species} smoulders under etherfire.",
        "freeze": f"Frost clings to the {species}'s limbs.",
        "fear": f"Terror flickers across the {species}'s gaze.",
        "poison": f"Venom darkens the {species}'s veins.",
    }
    return mapping.get(status, "")


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
    personality: str = "aggressive"
    status_effects: StatusDict = field(default_factory=dict)
    dialogues: Sequence[str] = field(default_factory=tuple)
    status_inflictions: StatusDict = field(default_factory=dict)
    critical_chance: int = 5
    armor_block: int = 5
    boss: bool = False
    max_hp: int = 0

    def __post_init__(self) -> None:
        if self.max_hp == 0:
            self.max_hp = self.hp

    def is_alive(self) -> bool:
        return self.hp > 0

    def speak(self, rng: Optional[random.Random] = None) -> Optional[str]:
        if not self.dialogues:
            return None
        rng = rng or random.Random()
        if rng.random() < 0.4:
            return rng.choice(list(self.dialogues))
        return None

    def take_turn(
        self,
        dungeon: DungeonMap,
        player_pos: Tuple[int, int],
        occupied: Set[Tuple[int, int]],
        rng: Optional[random.Random] = None,
    ) -> Optional[str]:
        """Perform a single AI step taking the enemy personality into account."""

        rng = rng or random.Random()
        status_note = self._tick_statuses()
        if status_note:
            return status_note
        if not self.awakened:
            if self.distance(player_pos) <= 1:
                self.awakened = True
                return f"The {self.species} reveals itself!"
            return None

        if self.personality == "cautious" and self.hp < self.max_hp // 2:
            if rng.random() < 0.4:
                # Attempt to retreat
                retreat = self._step_away(dungeon, player_pos, occupied)
                if retreat:
                    occupied.discard(self.position)
                    self.position = retreat
                    occupied.add(self.position)
                    return f"The {self.species} retreats cautiously."

        if self.personality == "ambusher" and self.distance(player_pos) > 4:
            return None

        if self.distance(player_pos) > self.aggressive_radius:
            return self.speak(rng)

        next_step = self.path_towards(dungeon, player_pos, occupied, allow_walls=self.can_phase)
        if next_step and next_step not in occupied:
            occupied.discard(self.position)
            self.position = next_step
            occupied.add(self.position)
            if self.position == player_pos:
                return f"The {self.species} lunges from the dark!"
        return self.speak(rng)

    def _tick_statuses(self) -> Optional[str]:
        if not self.status_effects:
            return None
        expired: List[str] = []
        message: Optional[str] = None
        for status, turns in list(self.status_effects.items()):
            if turns <= 0:
                expired.append(status)
                continue
            if status == "burn":
                self.hp = max(0, self.hp - 3)
            elif status == "poison":
                self.hp = max(0, self.hp - 2)
            elif status == "freeze":
                # Frozen enemies skip their turn but thaw slightly.
                self.status_effects[status] = turns - 1
                return _status_message(self.species, status)
            elif status == "fear":
                self.aggressive_radius = max(3, self.aggressive_radius - 1)
            self.status_effects[status] = turns - 1
            if self.status_effects[status] <= 0:
                expired.append(status)
            else:
                message = _status_message(self.species, status)
        for status in expired:
            self.status_effects.pop(status, None)
        if self.hp <= 0:
            return f"The {self.species} succumbs to its afflictions."
        return message

    def apply_status(self, status: str, duration: int) -> None:
        status = status.lower()
        if duration <= 0:
            return
        existing = self.status_effects.get(status, 0)
        self.status_effects[status] = max(existing, duration)

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
        if target not in came_from:
            return None
        current = target
        while came_from[current] != start:
            current = came_from[current]
            if current is None:
                return None
        return current

    def _step_away(
        self, dungeon: DungeonMap, player_pos: Tuple[int, int], occupied: Set[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        options = list(self.neighbours(self.position))
        options.sort(key=lambda pos: -abs(pos[0] - player_pos[0]) - abs(pos[1] - player_pos[1]))
        for nx, ny in options:
            if not dungeon.in_bounds(nx, ny):
                continue
            if not dungeon.is_walkable(nx, ny):
                continue
            if (nx, ny) in occupied:
                continue
            return (nx, ny)
        return None

    def neighbours(self, pos: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        x, y = pos
        yield x + 1, y
        yield x - 1, y
        yield x, y + 1
        yield x, y - 1

    def distance(self, other: Tuple[int, int]) -> int:
        return abs(self.position[0] - other[0]) + abs(self.position[1] - other[1])

    def attack_damage(self, rng: Optional[random.Random] = None) -> Tuple[int, Optional[Tuple[str, int]]]:
        rng = rng or random.Random()
        critical = rng.random() * 100 < self.critical_chance
        base = max(1, self.attack + rng.randint(-1, 3))
        if critical:
            base += int(base * 0.5)
        inflicted: Optional[Tuple[str, int]] = None
        if self.status_inflictions and rng.random() < 0.35:
            status, duration = rng.choice(list(self.status_inflictions.items()))
            inflicted = (status, duration)
        return base, inflicted

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
            "personality": self.personality,
            "status_effects": self.status_effects,
            "dialogues": list(self.dialogues),
            "status_inflictions": dict(self.status_inflictions),
            "critical_chance": self.critical_chance,
            "armor_block": self.armor_block,
            "boss": self.boss,
            "max_hp": self.max_hp,
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
            personality=str(data.get("personality", "aggressive")),
            status_effects=dict(data.get("status_effects", {})),
            dialogues=tuple(data.get("dialogues", [])),
            status_inflictions=dict(data.get("status_inflictions", {})),
            critical_chance=int(data.get("critical_chance", 5)),
            armor_block=int(data.get("armor_block", 5)),
            boss=bool(data.get("boss", False)),
            max_hp=int(data.get("max_hp", data.get("hp", 10))),
        )
        return enemy


class Ghost(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Ghost",
            hp=22,
            attack=7,
            defense=1,
            xp_reward=18,
            position=position,
            symbol="G",
            drop_table=[("Essence", 0.6, 1)],
            can_phase=True,
            aggressive_radius=8,
            personality="cautious",
            dialogues=("You shouldn't be here...", "Leave this place..."),
            status_inflictions={"freeze": 3},
        )


class Rat(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Rat",
            hp=10,
            attack=4,
            defense=0,
            xp_reward=6,
            position=position,
            symbol="r",
            drop_table=[("Meat", 0.4, 1)],
            aggressive_radius=5,
            personality="aggressive",
            dialogues=("Squeek!",),
            status_inflictions={"poison": 2},
        )


class Skeleton(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Skeleton",
            hp=26,
            attack=6,
            defense=3,
            xp_reward=14,
            position=position,
            symbol="s",
            drop_table=[("Bone", 0.5, 1), ("Bandage", 0.2, 1)],
            aggressive_radius=6,
            personality="aggressive",
            dialogues=("Bones for the throne...",),
            status_inflictions={"fear": 2},
        )


class Shadowling(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Shadowling",
            hp=20,
            attack=6,
            defense=1,
            xp_reward=15,
            position=position,
            symbol="h",
            drop_table=[("Essence", 0.3, 1), ("Torch", 0.2, 1)],
            aggressive_radius=7,
            personality="ambusher",
            dialogues=("Darkness is safer...",),
            status_inflictions={"fear": 3},
        )

    def take_turn(self, dungeon: DungeonMap, player_pos: Tuple[int, int], occupied: Set[Tuple[int, int]], rng=None):
        rng = rng or random.Random()
        if self.distance(player_pos) <= 2 and rng.random() < 0.4:
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
            hp=28,
            attack=8,
            defense=4,
            xp_reward=22,
            position=position,
            symbol="M",
            drop_table=[("Ether Potion", 0.5, 1), ("Essence", 0.4, 1)],
            aggressive_radius=4,
            awakened=False,
            personality="ambusher",
            dialogues=("Treasure... for me...",),
            status_inflictions={"poison": 3},
        )


class EtherGuardian(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Ether Guardian",
            hp=60,
            attack=12,
            defense=6,
            xp_reward=60,
            position=position,
            symbol="E",
            drop_table=[("Ancient Relic", 1.0, 1), ("Legendary Elixir", 0.7, 1)],
            aggressive_radius=10,
            personality="aggressive",
            dialogues=("You trespass within the Ether Vault.", "Stand down."),
            status_inflictions={"burn": 4},
            critical_chance=15,
            armor_block=20,
            boss=True,
        )


class ShadowQueen(Enemy):
    def __init__(self, position: Tuple[int, int]):
        super().__init__(
            species="Shadow Queen",
            hp=80,
            attack=14,
            defense=7,
            xp_reward=90,
            position=position,
            symbol="Q",
            drop_table=[("Ancient Relic", 1.0, 2), ("Ether Repeater", 0.6, 1)],
            aggressive_radius=12,
            personality="cautious",
            dialogues=("Kneel, little spark...", "The void remembers."),
            status_inflictions={"fear": 5, "poison": 4},
            critical_chance=20,
            armor_block=25,
            boss=True,
        )


def enemy_factory(enemy_type: str, position: Tuple[int, int]) -> Enemy:
    mapping = {
        "Rat": Rat,
        "Skeleton": Skeleton,
        "Ghost": Ghost,
        "Shadowling": Shadowling,
        "Mimic": Mimic,
        "Ether Guardian": EtherGuardian,
        "Shadow Queen": ShadowQueen,
    }
    cls = mapping.get(enemy_type, Enemy)
    if cls is Enemy:
        return cls(
            species=enemy_type,
            hp=18,
            attack=5,
            defense=1,
            xp_reward=8,
            position=position,
            dialogues=("You should have turned back...",),
        )
    return cls(position)

