"""Inventory data structures and crafting helpers for The Depths of Ether.

This module defines the items that can exist in the game, along with the
inventory container and crafting system utilities.  The design intentionally
uses lightweight data structures so the objects can be serialised directly to
JSON when saving the game state.  MVP7 expands this database with weapon tiers,
durability, weight metadata and consumable quality levels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class Item:
    """Simple representation of an item instance.

    Attributes
    ----------
    name:
        Canonical item name that should exist in :data:`ITEM_LIBRARY`.
    quantity:
        Stack size for the item.  Most equipment has a quantity of one while
        consumables can stack up to the inventory capacity.
    """

    name: str
    quantity: int = 1

    def to_dict(self) -> Dict[str, object]:
        """Serialise the item so that it can be stored inside JSON files."""
        return {"name": self.name, "quantity": self.quantity}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Item":
        """Create an :class:`Item` instance from serialised data."""
        return cls(name=str(data["name"]), quantity=int(data.get("quantity", 1)))


# -- Item library -----------------------------------------------------------
#
# The item library acts as the central database for game items.  Each entry
# stores metadata used by various systems such as combat, crafting and random
# events.  The lightweight dictionaries keep the structure flexible for the
# prototype while remaining easy to extend in future MVP iterations.
ITEM_LIBRARY: Dict[str, Dict[str, object]] = {
    # -- Light sources -------------------------------------------------
    "Torch": {
        "type": "utility",
        "tier": "basic",
        "weight": 1.0,
        "description": "A dim torch that increases your vision radius for a while.",
        "effect": {"light_bonus": 3, "duration": 30},
    },
    "Lantern": {
        "type": "utility",
        "tier": "refined",
        "weight": 1.5,
        "description": "Polished brass lantern that brightens the path.",
        "effect": {"light_bonus": 5, "duration": 60},
    },
    # -- Weapons -------------------------------------------------------
    "Dagger": {
        "type": "weapon",
        "tier": "basic",
        "weight": 2.0,
        "description": "A rusty dagger. Better than bare hands.",
        "effect": {
            "attack_bonus": 2,
            "weapon_class": "melee",
            "durability": 45,
            "crit_bonus": 5,
        },
    },
    "Short Sword": {
        "type": "weapon",
        "tier": "refined",
        "weight": 3.5,
        "description": "Well-balanced sword etched with faint runes.",
        "effect": {
            "attack_bonus": 4,
            "weapon_class": "melee",
            "durability": 75,
            "crit_bonus": 10,
        },
    },
    "Club": {
        "type": "weapon",
        "tier": "basic",
        "weight": 3.0,
        "description": "A crude club fashioned from stone and wood.",
        "effect": {
            "attack_bonus": 3,
            "weapon_class": "melee",
            "durability": 50,
        },
    },
    "Ether Blade": {
        "type": "weapon",
        "tier": "legendary",
        "weight": 3.0,
        "description": "A blade forged from essence. It hums with power.",
        "effect": {
            "attack_bonus": 7,
            "weapon_class": "melee",
            "durability": 120,
            "crit_bonus": 15,
            "status": "burn",
        },
    },
    "Bone Bow": {
        "type": "weapon",
        "tier": "basic",
        "weight": 2.5,
        "description": "A bow pieced together from sinew and bone.",
        "effect": {
            "attack_bonus": 2,
            "weapon_class": "ranged",
            "durability": 50,
            "range": 5,
            "crit_bonus": 5,
        },
    },
    "Ether Repeater": {
        "type": "weapon",
        "tier": "legendary",
        "weight": 3.0,
        "description": "Repeater that channels ether bolts over distance.",
        "effect": {
            "attack_bonus": 5,
            "weapon_class": "ranged",
            "durability": 110,
            "range": 7,
            "crit_bonus": 12,
            "status": "fear",
        },
    },
    "Hide Armor": {
        "type": "armor",
        "tier": "basic",
        "weight": 5.0,
        "description": "Padded hide armor reinforced with bone plates.",
        "effect": {"defense_bonus": 2, "durability": 60, "block_chance": 8},
    },
    "Runed Plate": {
        "type": "armor",
        "tier": "legendary",
        "weight": 8.0,
        "description": "Ancient plate armor that hums with protective wards.",
        "effect": {"defense_bonus": 4, "durability": 120, "block_chance": 15},
    },
    # -- Food and consumables -----------------------------------------
    "Bread": {
        "type": "food",
        "tier": "basic",
        "weight": 0.5,
        "description": "Stale bread that restores a bit of hunger and health.",
        "effect": {"heal": 5, "hunger": 20},
    },
    "Foraged Ration": {
        "type": "food",
        "tier": "basic",
        "weight": 0.7,
        "description": "Mixed berries and fungi. Restores stamina slightly.",
        "effect": {"stamina": 5, "hunger": 15},
    },
    "Mushroom": {
        "type": "food",
        "tier": "basic",
        "weight": 0.3,
        "description": "A glowing mushroom that restores sanity.",
        "effect": {"sanity": 10, "hunger": 5},
    },
    "Cooked Meat": {
        "type": "food",
        "tier": "refined",
        "weight": 1.0,
        "description": "Freshly cooked meat, hearty and filling.",
        "effect": {"heal": 10, "hunger": 35, "stamina": 5},
    },
    "Refined Tonic": {
        "type": "consumable",
        "tier": "refined",
        "weight": 0.3,
        "description": "Brew that sharpens the senses and steadies the mind.",
        "effect": {"sanity": 15, "stamina": 10},
    },
    "Legendary Elixir": {
        "type": "consumable",
        "tier": "legendary",
        "weight": 0.5,
        "description": "Ether distilled to its purest form.",
        "effect": {"sanity": 30, "stamina": 20, "heal": 20},
    },
    "Ether Potion": {
        "type": "consumable",
        "tier": "refined",
        "weight": 0.4,
        "description": "A bottle of shimmering ether that restores sanity and stamina.",
        "effect": {"sanity": 20, "stamina": 15},
    },
    "Bandage": {
        "type": "consumable",
        "tier": "basic",
        "weight": 0.2,
        "description": "Clean bandages to stop the bleeding.",
        "effect": {"heal": 8},
    },
    # -- Crafting components -------------------------------------------
    "Meat": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 1.0,
        "description": "Raw meat harvested from a beast.",
        "effect": {},
    },
    "Fire": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 0.0,
        "description": "A flicker of captured flame. Useful in crafting.",
        "effect": {},
    },
    "Stone": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 1.5,
        "description": "A sturdy piece of stone.",
        "effect": {},
    },
    "Wood": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 1.2,
        "description": "Damp but usable wood.",
        "effect": {},
    },
    "Cloth": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 0.8,
        "description": "Sturdy cloth salvaged from old banners.",
        "effect": {},
    },
    "Essence": {
        "type": "ingredient",
        "tier": "refined",
        "weight": 0.1,
        "description": "Crystallised monster essence.",
        "effect": {},
    },
    "Bone": {
        "type": "ingredient",
        "tier": "basic",
        "weight": 0.8,
        "description": "Jagged bone, still pulsing faintly with ether.",
        "effect": {},
    },
    "Crystal Shard": {
        "type": "ingredient",
        "tier": "refined",
        "weight": 0.6,
        "description": "A shard from an ether crystal pillar.",
        "effect": {},
    },
    "Ancient Relic": {
        "type": "ingredient",
        "tier": "legendary",
        "weight": 2.5,
        "description": "Relic humming with forgotten memories.",
        "effect": {},
    },
    # -- Utility -------------------------------------------------------
    "Camp Supplies": {
        "type": "utility",
        "tier": "refined",
        "weight": 4.0,
        "description": "Canvas, rope and incense for raising a safe campfire.",
        "effect": {},
    },
}


class Inventory:
    """Container that stores the player's carried items.

    The inventory maintains a dictionary of item names to :class:`Item`
    instances.  This allows stacking while making lookup operations efficient.
    The capacity value denotes the maximum number of distinct item stacks that
    can be carried simultaneously.
    """

    def __init__(self, capacity: int = 12, weight_limit: float = 40.0):
        self.capacity = capacity
        self.weight_limit = weight_limit
        self.items: Dict[str, Item] = {}

    # -- Utility ---------------------------------------------------------
    def is_full(self) -> bool:
        return len(self.items) >= self.capacity

    def add_item(self, name: str, quantity: int = 1) -> bool:
        """Add an item to the inventory.

        Returns ``True`` if the item was added, otherwise ``False`` if there was
        not enough space.  The method gracefully merges stacks when possible.
        """

        if name not in ITEM_LIBRARY:
            raise ValueError(f"Unknown item: {name}")
        if name in self.items:
            projected_weight = self.total_weight() + self.item_weight(name) * quantity
            if projected_weight > self.weight_limit * 1.5:
                return False
            self.items[name].quantity += quantity
            return True
        if self.is_full():
            return False
        projected_weight = self.total_weight() + self.item_weight(name) * quantity
        if projected_weight > self.weight_limit * 1.5:
            return False
        self.items[name] = Item(name=name, quantity=quantity)
        return True

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """Remove an item stack from the inventory.

        Parameters
        ----------
        name:
            Item name to remove.
        quantity:
            Amount to deduct from the stack.  When the quantity reaches zero the
            entry is removed completely.
        """

        if name not in self.items:
            return False
        stack = self.items[name]
        if stack.quantity < quantity:
            return False
        stack.quantity -= quantity
        if stack.quantity == 0:
            del self.items[name]
        return True

    def has_item(self, name: str, quantity: int = 1) -> bool:
        stack = self.items.get(name)
        return bool(stack and stack.quantity >= quantity)

    def list_items(self) -> List[Item]:
        return list(self.items.values())

    def item_weight(self, name: str) -> float:
        """Return the per-unit weight of an item."""

        data = ITEM_LIBRARY.get(name, {})
        return float(data.get("weight", 1.0))

    def total_weight(self) -> float:
        """Calculate the total carried weight."""

        return sum(self.item_weight(item.name) * item.quantity for item in self.items.values())

    def set_weight_limit(self, new_limit: float) -> None:
        """Adjust the carrying capacity associated with the inventory."""

        self.weight_limit = max(5.0, float(new_limit))

    def to_dict(self) -> Dict[str, object]:
        return {
            "capacity": self.capacity,
            "weight_limit": self.weight_limit,
            "items": [item.to_dict() for item in self.items.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Inventory":
        inv = cls(capacity=int(data.get("capacity", 12)), weight_limit=float(data.get("weight_limit", 40.0)))
        for item_data in data.get("items", []):
            item = Item.from_dict(item_data)
            inv.items[item.name] = item
        return inv


class CraftingSystem:
    """Provides crafting recipes and helpers to combine items."""

    def __init__(self):
        self.recipes: Dict[str, Dict[str, object]] = {
            "Club": {
                "ingredients": {"Stone": 1, "Wood": 1},
                "result": ("Club", 1),
                "description": "Combine stone and wood into a crude weapon.",
            },
            "Dagger": {
                "ingredients": {"Bone": 1, "Essence": 1},
                "result": ("Dagger", 1),
                "description": "Shape a dagger from bone bound with essence.",
            },
            "Short Sword": {
                "ingredients": {"Dagger": 1, "Crystal Shard": 1, "Essence": 1},
                "result": ("Short Sword", 1),
                "description": "Refine a dagger into a balanced short sword.",
            },
            "Ether Blade": {
                "ingredients": {"Short Sword": 1, "Ancient Relic": 1, "Essence": 2},
                "result": ("Ether Blade", 1),
                "description": "Fuse relics into a legendary blade.",
            },
            "Bone Bow": {
                "ingredients": {"Wood": 2, "Bone": 2},
                "result": ("Bone Bow", 1),
                "description": "Craft a ranged weapon from bone and sinew.",
            },
            "Ether Repeater": {
                "ingredients": {"Bone Bow": 1, "Crystal Shard": 2, "Essence": 2},
                "result": ("Ether Repeater", 1),
                "description": "Imbue a bow with ether conduits.",
            },
            "Cooked Meat": {
                "ingredients": {"Meat": 1, "Fire": 1},
                "result": ("Cooked Meat", 1),
                "description": "Cook raw meat to restore more hunger.",
            },
            "Refined Tonic": {
                "ingredients": {"Mushroom": 1, "Essence": 1},
                "result": ("Refined Tonic", 1),
                "description": "Distil fungus and essence into a calming brew.",
            },
            "Legendary Elixir": {
                "ingredients": {"Refined Tonic": 1, "Ancient Relic": 1},
                "result": ("Legendary Elixir", 1),
                "description": "Elevate a tonic into legendary medicine.",
            },
            "Camp Supplies": {
                "ingredients": {"Wood": 1, "Cloth": 1, "Essence": 1},
                "result": ("Camp Supplies", 1),
                "description": "Bundle supplies into a portable camp kit.",
            },
        }

    def list_recipes(self) -> Iterable[Tuple[str, Dict[str, object]]]:
        return self.recipes.items()

    def can_craft(self, inventory: Inventory, recipe_name: str) -> bool:
        recipe = self.recipes.get(recipe_name)
        if not recipe:
            return False
        for name, qty in recipe["ingredients"].items():
            if not inventory.has_item(name, qty):
                return False
        return True

    def craft(self, inventory: Inventory, recipe_name: str) -> Optional[str]:
        """Attempt to craft the specified recipe.

        Returns a descriptive string that can be fed into the event log.  When
        crafting fails ``None`` is returned.  The caller is responsible for
        presenting the message to the user.
        """

        recipe = self.recipes.get(recipe_name)
        if not recipe:
            return None
        if not self.can_craft(inventory, recipe_name):
            return "You lack the required ingredients."
        for name, qty in recipe["ingredients"].items():
            inventory.remove_item(name, qty)
        result_name, result_qty = recipe["result"]
        if not inventory.add_item(result_name, result_qty):
            # If the result cannot be added due to capacity, refund the items.
            for name, qty in recipe["ingredients"].items():
                inventory.add_item(name, qty)
            return "No room to carry the crafted item."
        return f"Crafted {result_qty}x {result_name}!"


def describe_item(name: str) -> str:
    """Return the description string for an item from the library."""

    data = ITEM_LIBRARY.get(name)
    if not data:
        return "An indescribable object."
    return str(data.get("description", "An indescribable object."))
