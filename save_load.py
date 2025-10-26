"""Save and load helpers supporting multiple save slots."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

from enemy_ai import Enemy
from map_gen import DungeonMap
from player import Player


class SaveManager:
    """Serialises the current game state to disk."""

    def __init__(self, directory: str = "saves"):
        self.directory = directory
        self.slot = 1
        os.makedirs(self.directory, exist_ok=True)

    @property
    def filename(self) -> str:
        return os.path.join(self.directory, f"save_{self.slot}.json")

    def set_slot(self, slot: int) -> None:
        self.slot = max(1, min(slot, 3))

    def save(
        self,
        player: Player,
        dungeon: DungeonMap,
        enemies: Sequence[Enemy],
        log: Sequence[str],
        event_state: Dict[str, object],
    ) -> None:
        data = {
            "player": player.to_dict(),
            "dungeon": dungeon.to_dict(),
            "enemies": [enemy.to_dict() for enemy in enemies if enemy.is_alive()],
            "log": list(log)[-80:],
            "event_state": event_state,
        }
        with open(self.filename, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def load(self) -> Optional[Tuple[Player, DungeonMap, List[Enemy], List[str], Dict[str, object]]]:
        if not os.path.exists(self.filename):
            return None
        with open(self.filename, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        player = Player.from_dict(data["player"])
        dungeon = DungeonMap.from_dict(data["dungeon"])
        enemies = [Enemy.from_dict(info) for info in data.get("enemies", [])]
        log = list(data.get("log", []))
        event_state = dict(data.get("event_state", {}))
        return player, dungeon, enemies, log, event_state

    def delete(self) -> None:
        if os.path.exists(self.filename):
            os.remove(self.filename)
