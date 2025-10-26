"""Player model and related logic for The Depths of Ether."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from inventory import Inventory, ITEM_LIBRARY, describe_item


@dataclass
class Player:
    """Represents the hero delving into the depths."""

    name: str = "Wanderer"
    max_hp: int = 30
    hp: int = 30
    max_stamina: int = 20
    stamina: int = 20
    max_sanity: int = 30
    sanity: int = 30
    max_hunger: int = 100
    hunger: int = 100
    level: int = 1
    xp: int = 0
    xp_to_next: int = 20
    base_attack: int = 3
    base_defense: int = 1
    position: Tuple[int, int] = (1, 1)
    floor: int = 1
    time_spent: int = 0
    inventory: Inventory = field(default_factory=lambda: Inventory(capacity=14))
    weapon: Optional[str] = None
    armor: Optional[str] = None
    light_radius: int = 5
    light_bonus: int = 0
    light_bonus_timer: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "max_stamina": self.max_stamina,
            "stamina": self.stamina,
            "max_sanity": self.max_sanity,
            "sanity": self.sanity,
            "max_hunger": self.max_hunger,
            "hunger": self.hunger,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next,
            "base_attack": self.base_attack,
            "base_defense": self.base_defense,
            "position": list(self.position),
            "floor": self.floor,
            "time_spent": self.time_spent,
            "inventory": self.inventory.to_dict(),
            "weapon": self.weapon,
            "armor": self.armor,
            "light_radius": self.light_radius,
            "light_bonus": self.light_bonus,
            "light_bonus_timer": self.light_bonus_timer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Player":
        player = cls()
        for key, value in data.items():
            if key == "inventory":
                player.inventory = Inventory.from_dict(value)  # type: ignore[arg-type]
            elif key == "position":
                player.position = tuple(value)  # type: ignore[arg-type]
            else:
                setattr(player, key, value)
        return player

    # -- Derived stats ---------------------------------------------------
    @property
    def attack(self) -> int:
        bonus = 0
        if self.weapon and self.weapon in ITEM_LIBRARY:
            effect = ITEM_LIBRARY[self.weapon].get("effect", {})
            bonus += int(effect.get("attack_bonus", 0))
        return self.base_attack + bonus

    @property
    def defense(self) -> int:
        bonus = 0
        if self.armor and self.armor in ITEM_LIBRARY:
            effect = ITEM_LIBRARY[self.armor].get("effect", {})
            bonus += int(effect.get("defense_bonus", 0))
        return self.base_defense + bonus

    @property
    def vision_radius(self) -> int:
        return self.light_radius + self.light_bonus

    def move(self, dx: int, dy: int, game_map: "DungeonMap") -> bool:
        """Move the player by the given offset if the destination is walkable."""

        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        if not game_map.in_bounds(new_x, new_y):
            return False
        if not game_map.is_walkable(new_x, new_y):
            return False
        self.position = (new_x, new_y)
        self.time_spent += 1
        self.consume_resources()
        game_map.reveal_around(self.position, self.vision_radius)
        return True

    def consume_resources(self) -> None:
        """Apply the upkeep costs for moving a single tile."""

        self.hunger = max(0, self.hunger - 1)
        self.stamina = max(0, self.stamina - 1)
        if self.hunger == 0:
            self.hp = max(0, self.hp - 1)
        if self.stamina == 0:
            self.sanity = max(0, self.sanity - 1)
        if self.light_bonus_timer > 0:
            self.light_bonus_timer -= 1
            if self.light_bonus_timer == 0:
                self.light_bonus = 0

    def rest(self) -> str:
        self.time_spent += 1
        self.consume_resources()
        self.stamina = min(self.max_stamina, self.stamina + 5)
        self.hp = min(self.max_hp, self.hp + 2)
        self.hunger = max(0, self.hunger - 5)
        self.sanity = min(self.max_sanity, self.sanity + 2)
        return "You take a moment to rest."

    def gain_xp(self, amount: int) -> List[str]:
        self.xp += amount
        messages = [f"Gained {amount} XP."]
        while self.xp >= self.xp_to_next:
            self.level += 1
            self.xp -= self.xp_to_next
            self.xp_to_next += 10
            self.max_hp += 5
            self.max_stamina += 3
            self.max_sanity += 2
            self.base_attack += 1
            self.base_defense += 1
            self.hp = self.max_hp
            self.stamina = self.max_stamina
            self.sanity = self.max_sanity
            messages.append(f"Level up! You are now level {self.level}.")
        return messages

    def use_item(self, item_name: str) -> str:
        """Consume or equip an item from the inventory."""

        if not self.inventory.has_item(item_name):
            return "You don't have that item."
        data = ITEM_LIBRARY.get(item_name)
        if not data:
            return "The item fizzles uselessly."
        effect = data.get("effect", {})
        item_type = data.get("type", "consumable")
        message = "Nothing happens."
        if item_type in {"food", "consumable"}:
            self.hp = min(self.max_hp, self.hp + int(effect.get("heal", 0)))
            self.stamina = min(self.max_stamina, self.stamina + int(effect.get("stamina", 0)))
            self.sanity = min(self.max_sanity, self.sanity + int(effect.get("sanity", 0)))
            self.hunger = min(self.max_hunger, self.hunger + int(effect.get("hunger", 0)))
            if effect:
                parts = []
                if effect.get("heal"):
                    parts.append(f"+{effect['heal']} HP")
                if effect.get("stamina"):
                    parts.append(f"+{effect['stamina']} STA")
                if effect.get("sanity"):
                    parts.append(f"+{effect['sanity']} SAN")
                if effect.get("hunger"):
                    parts.append(f"+{effect['hunger']} HGR")
                message = "You use the item: " + ", ".join(parts)
            self.inventory.remove_item(item_name)
        elif item_type == "weapon":
            self.weapon = item_name
            message = f"You equip the {item_name}."
        elif item_type == "utility" and "light_bonus" in effect:
            bonus = int(effect.get("light_bonus", 2))
            duration = int(effect.get("duration", 20))
            self.light_bonus = max(self.light_bonus, bonus)
            self.light_bonus_timer = max(self.light_bonus_timer, duration)
            message = "The torch lights up the darkness."
            self.inventory.remove_item(item_name)
        else:
            message = describe_item(item_name)
        return message

    def is_alive(self) -> bool:
        return self.hp > 0 and self.sanity > 0

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_sanity(self, amount: int) -> None:
        self.sanity = min(self.max_sanity, self.sanity + amount)


def default_player() -> Player:
    """Return a new player with starter equipment."""

    player = Player()
    player.inventory.add_item("Torch", 1)
    player.inventory.add_item("Bread", 2)
    player.inventory.add_item("Dagger", 1)
    player.weapon = "Dagger"
    return player
