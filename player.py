"""Player model and progression systems for The Depths of Ether MVP7."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from inventory import Inventory, ITEM_LIBRARY, describe_item


StatusDict = Dict[str, int]


def _durability_from_item(name: Optional[str]) -> int:
    """Return the durability rating defined in :data:`ITEM_LIBRARY`."""

    if not name:
        return 0
    effect = ITEM_LIBRARY.get(name, {}).get("effect", {})
    return int(effect.get("durability", 0))


@dataclass
class Player:
    """Represents the explorer venturing into the Depths of Ether."""

    name: str = "Wanderer"
    max_hp: int = 36
    hp: int = 36
    max_stamina: int = 24
    stamina: int = 24
    max_sanity: int = 36
    sanity: int = 36
    max_hunger: int = 100
    hunger: int = 100
    level: int = 1
    xp: int = 0
    xp_to_next: int = 25
    base_attack: int = 4
    base_defense: int = 1
    base_carry_capacity: float = 45.0
    position: Tuple[int, int] = (1, 1)
    floor: int = 1
    time_spent: int = 0
    inventory: Inventory = field(
        default_factory=lambda: Inventory(capacity=16, weight_limit=45.0)
    )
    melee_weapon: Optional[str] = None
    ranged_weapon: Optional[str] = None
    armor: Optional[str] = None
    melee_durability: int = 0
    ranged_durability: int = 0
    armor_durability: int = 0
    light_radius: int = 5
    light_bonus: int = 0
    light_bonus_timer: int = 0
    karma: int = 0
    skill_points: int = 0
    chosen_trait: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    status_effects: StatusDict = field(default_factory=dict)
    temperature: int = 60
    fatigue: int = 0
    max_fatigue: int = 100
    hallucination_cooldown: int = 0

    # -- Serialisation -------------------------------------------------
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
            "base_carry_capacity": self.base_carry_capacity,
            "position": list(self.position),
            "floor": self.floor,
            "time_spent": self.time_spent,
            "inventory": self.inventory.to_dict(),
            "melee_weapon": self.melee_weapon,
            "ranged_weapon": self.ranged_weapon,
            "armor": self.armor,
            "melee_durability": self.melee_durability,
            "ranged_durability": self.ranged_durability,
            "armor_durability": self.armor_durability,
            "light_radius": self.light_radius,
            "light_bonus": self.light_bonus,
            "light_bonus_timer": self.light_bonus_timer,
            "karma": self.karma,
            "skill_points": self.skill_points,
            "chosen_trait": self.chosen_trait,
            "traits": self.traits,
            "status_effects": self.status_effects,
            "temperature": self.temperature,
            "fatigue": self.fatigue,
            "max_fatigue": self.max_fatigue,
            "hallucination_cooldown": self.hallucination_cooldown,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Player":
        player = cls()
        for key, value in data.items():
            if key == "inventory":
                player.inventory = Inventory.from_dict(value)  # type: ignore[arg-type]
            elif key == "position":
                player.position = tuple(value)  # type: ignore[arg-type]
            elif hasattr(player, key):
                setattr(player, key, value)
        player.inventory.set_weight_limit(player.base_carry_capacity)
        return player

    # -- Derived statistics -------------------------------------------
    @property
    def carry_capacity(self) -> float:
        modifier = 0.0
        if "Packrat" in self.traits:
            modifier += 10.0
        return self.base_carry_capacity + modifier

    @property
    def overburdened(self) -> bool:
        return self.inventory.total_weight() > self.carry_capacity

    @property
    def attack(self) -> int:
        return self.base_attack + self._weapon_bonus(self.melee_weapon) + self._status_attack_penalty()

    @property
    def ranged_attack(self) -> int:
        return self.base_attack + self._weapon_bonus(self.ranged_weapon) + self._status_attack_penalty()

    @property
    def defense(self) -> int:
        bonus = self._armor_bonus()
        if "Bulwark" in self.traits:
            bonus += 1
        if "fear" in self.status_effects:
            bonus = max(0, bonus - 1)
        return self.base_defense + bonus

    @property
    def armor_block_chance(self) -> int:
        if not self.armor:
            base = 5
        else:
            effect = ITEM_LIBRARY.get(self.armor, {}).get("effect", {})
            base = int(effect.get("block_chance", 5))
        if "Bulwark" in self.traits:
            base += 5
        return base

    @property
    def vision_radius(self) -> int:
        radius = self.light_radius + self.light_bonus
        if "Seer" in self.traits:
            radius += 1
        return radius

    # -- Utility -------------------------------------------------------
    def _weapon_bonus(self, weapon: Optional[str]) -> int:
        if not weapon:
            return 0
        effect = ITEM_LIBRARY.get(weapon, {}).get("effect", {})
        return int(effect.get("attack_bonus", 0))

    def _armor_bonus(self) -> int:
        if not self.armor:
            return 0
        effect = ITEM_LIBRARY.get(self.armor, {}).get("effect", {})
        return int(effect.get("defense_bonus", 0))

    def _status_attack_penalty(self) -> int:
        penalty = 0
        if "fear" in self.status_effects:
            penalty -= 2
        if "freeze" in self.status_effects:
            penalty -= 1
        return penalty

    # -- Movement and upkeep ------------------------------------------
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
        """Apply the upkeep costs for taking a single action."""

        burden_penalty = 2 if self.overburdened else 1
        self.hunger = max(0, self.hunger - 1)
        self.stamina = max(0, self.stamina - burden_penalty)
        self.fatigue = min(self.max_fatigue, self.fatigue + 3)
        if self.hunger == 0:
            self.hp = max(0, self.hp - 1)
        if self.stamina == 0:
            self.sanity = max(0, self.sanity - 1)
        if self.fatigue >= self.max_fatigue:
            self.sanity = max(0, self.sanity - 1)
        if self.light_bonus_timer > 0:
            self.light_bonus_timer -= 1
            if self.light_bonus_timer == 0:
                self.light_bonus = 0
        self._tick_statuses()

    def adjust_temperature(self, delta: int) -> None:
        """Modify the current body temperature."""

        self.temperature = max(0, min(120, self.temperature + delta))
        if self.temperature < 40:
            self.stamina = max(0, self.stamina - 2)
        elif self.temperature > 90:
            self.hunger = max(0, self.hunger - 2)

    # -- Resting -------------------------------------------------------
    def rest(self, at_campfire: bool = False) -> str:
        """Recover stamina and health by resting in place."""

        self.time_spent += 1
        self.consume_resources()
        stamina_gain = 6 if at_campfire else 4
        health_gain = 4 if at_campfire else 2
        sanity_gain = 3 if at_campfire else 1
        self.stamina = min(self.max_stamina, self.stamina + stamina_gain)
        self.hp = min(self.max_hp, self.hp + health_gain)
        self.sanity = min(self.max_sanity, self.sanity + sanity_gain)
        self.fatigue = max(0, self.fatigue - (15 if at_campfire else 8))
        if at_campfire and "Campfire" not in self.traits:
            self.temperature = min(70, max(50, self.temperature + 5))
        return "You rest and gather strength." if not at_campfire else "The campfire soothes your weary bones."

    def sleep_turn(self, at_campfire: bool = False) -> str:
        """Spend time sleeping to reset fatigue."""

        self.time_spent += 1
        self.consume_resources()
        recovery = 35 if at_campfire else 20
        self.fatigue = max(0, self.fatigue - recovery)
        self.stamina = min(self.max_stamina, self.stamina + recovery // 5)
        self.hp = min(self.max_hp, self.hp + recovery // 10)
        self.sanity = min(self.max_sanity, self.sanity + recovery // 10)
        self.temperature = min(75, max(50, self.temperature + (8 if at_campfire else 2)))
        return "You drift into uneasy sleep." if not at_campfire else "Warmth lulls you into a deep slumber."

    # -- Combat helpers ------------------------------------------------
    def spend_stamina(self, amount: int) -> None:
        self.stamina = max(0, self.stamina - amount)

    def gain_xp(self, amount: int) -> List[str]:
        self.xp += amount
        messages = [f"Gained {amount} XP."]
        while self.xp >= self.xp_to_next:
            self.level += 1
            self.xp -= self.xp_to_next
            self.xp_to_next += 15
            self.max_hp += 4
            self.max_stamina += 3
            self.max_sanity += 2
            self.base_attack += 1
            self.base_defense += 1
            self.skill_points += 1
            self.hp = self.max_hp
            self.stamina = self.max_stamina
            self.sanity = self.max_sanity
            messages.append(
                f"Level up! You are now level {self.level} and gained a skill point."
            )
        return messages

    def spend_skill_point(self, attribute: str) -> str:
        if self.skill_points <= 0:
            return "You have no skill points to spend."
        attribute = attribute.lower()
        bonuses = {
            "hp": ("max_hp", 5),
            "stamina": ("max_stamina", 4),
            "sanity": ("max_sanity", 3),
            "attack": ("base_attack", 1),
            "defense": ("base_defense", 1),
        }
        if attribute not in bonuses:
            return "Unknown attribute."
        field_name, amount = bonuses[attribute]
        setattr(self, field_name, getattr(self, field_name) + amount)
        self.skill_points -= 1
        self.hp = min(self.hp, self.max_hp)
        self.stamina = min(self.stamina, self.max_stamina)
        self.sanity = min(self.sanity, self.max_sanity)
        return f"You invest in {attribute}."

    def apply_trait(self, trait: str) -> None:
        if trait in self.traits:
            return
        self.traits.append(trait)
        self.chosen_trait = trait
        if trait == "Mind Anchor":
            self.max_sanity += 10
            self.sanity = self.max_sanity
        elif trait == "Quickstep":
            self.max_stamina += 6
            self.stamina = self.max_stamina
        elif trait == "Vital Bloom":
            self.max_hp += 8
            self.hp = self.max_hp
        elif trait == "Packrat":
            self.base_carry_capacity += 12
        elif trait == "Seer":
            self.light_radius += 1
        elif trait == "Bulwark":
            self.base_defense += 1
        self.inventory.set_weight_limit(self.carry_capacity)

    def equip_item(self, item_name: str) -> str:
        data = ITEM_LIBRARY.get(item_name)
        if not data:
            return "The item feels inert."
        effect = data.get("effect", {})
        item_type = data.get("type", "consumable")
        if item_type == "weapon":
            weapon_class = effect.get("weapon_class", "melee")
            if weapon_class == "ranged":
                self.ranged_weapon = item_name
                self.ranged_durability = _durability_from_item(item_name)
                return f"You prepare the {item_name} for ranged combat."
            self.melee_weapon = item_name
            self.melee_durability = _durability_from_item(item_name)
            return f"You grip the {item_name} tightly."
        if item_type == "armor":
            self.armor = item_name
            self.armor_durability = _durability_from_item(item_name)
            return f"You don the {item_name}."
        return describe_item(item_name)

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
            status = effect.get("status")
            if status:
                self.apply_status(str(status), duration=3)
            if effect:
                parts: List[str] = []
                for key in ("heal", "stamina", "sanity", "hunger"):
                    if key in effect:
                        parts.append(f"+{effect[key]} {key.upper()}")
                message = "You use the item: " + ", ".join(parts)
            self.inventory.remove_item(item_name)
        elif item_type in {"weapon", "armor"}:
            message = self.equip_item(item_name)
        elif item_type == "utility" and "light_bonus" in effect:
            bonus = int(effect.get("light_bonus", 2))
            duration = int(effect.get("duration", 20))
            self.light_bonus = max(self.light_bonus, bonus)
            self.light_bonus_timer = max(self.light_bonus_timer, duration)
            message = "The darkness recoils from the light."
            self.inventory.remove_item(item_name)
        else:
            message = describe_item(item_name)
        return message

    # -- Status effects ------------------------------------------------
    def apply_status(self, status: str, duration: int) -> None:
        status = status.lower()
        if duration <= 0:
            return
        existing = self.status_effects.get(status, 0)
        self.status_effects[status] = max(existing, duration)

    def has_status(self, status: str) -> bool:
        return status.lower() in self.status_effects

    def _tick_statuses(self) -> None:
        expired: List[str] = []
        for status, turns in list(self.status_effects.items()):
            if turns <= 0:
                expired.append(status)
                continue
            if status == "burn":
                self.hp = max(0, self.hp - 2)
            elif status == "poison":
                self.hp = max(0, self.hp - 1)
                self.sanity = max(0, self.sanity - 1)
            elif status == "freeze":
                self.stamina = max(0, self.stamina - 1)
            elif status == "fear":
                self.karma = max(-50, self.karma - 1)
            self.status_effects[status] = turns - 1
            if self.status_effects[status] <= 0:
                expired.append(status)
        for status in expired:
            self.status_effects.pop(status, None)

    # -- Misc helpers --------------------------------------------------
    def degrade_equipment(self, weapon_type: str) -> None:
        if weapon_type == "melee" and self.melee_weapon:
            self.melee_durability -= 1
            if self.melee_durability <= 0:
                self.melee_weapon = None
        elif weapon_type == "ranged" and self.ranged_weapon:
            self.ranged_durability -= 1
            if self.ranged_durability <= 0:
                self.ranged_weapon = None

    def degrade_armor(self) -> None:
        if not self.armor:
            return
        if self.armor_durability <= 0:
            return
        self.armor_durability -= 1
        if self.armor_durability <= 0:
            self.armor = None

    def is_alive(self) -> bool:
        return self.hp > 0 and self.sanity > 0

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_sanity(self, amount: int) -> None:
        self.sanity = min(self.max_sanity, self.sanity + amount)


def default_player() -> Player:
    """Return a new player with starter equipment and a trait choice placeholder."""

    player = Player()
    player.inventory.add_item("Torch", 1)
    player.inventory.add_item("Bread", 2)
    player.inventory.add_item("Dagger", 1)
    player.inventory.add_item("Bone Bow", 1)
    player.inventory.add_item("Bandage", 1)
    player.melee_weapon = "Dagger"
    player.melee_durability = _durability_from_item(player.melee_weapon)
    player.ranged_weapon = "Bone Bow"
    player.ranged_durability = _durability_from_item(player.ranged_weapon)
    player.inventory.set_weight_limit(player.carry_capacity)
    return player

