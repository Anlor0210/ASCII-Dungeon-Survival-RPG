"""Inventory and item management for The Depths of Ether.

This module defines the items that can exist in the game, along with the
inventory container and crafting system utilities.  The design intentionally
uses lightweight data structures so the objects can be serialised directly to
JSON when saving the game state.
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
    "Torch": {
        "type": "utility",
        "description": "A dim torch that increases your vision radius for a while.",
        "effect": {"light_bonus": 3, "duration": 30},
    },
    "Dagger": {
        "type": "weapon",
        "description": "A rusty dagger. Better than bare hands.",
        "effect": {"attack_bonus": 2},
    },
    "Club": {
        "type": "weapon",
        "description": "A crude club fashioned from stone and wood.",
        "effect": {"attack_bonus": 3},
    },
    "Bread": {
        "type": "food",
        "description": "Stale bread that restores a bit of hunger and health.",
        "effect": {"heal": 5, "hunger": 20},
    },
    "Mushroom": {
        "type": "food",
        "description": "A glowing mushroom that restores sanity.",
        "effect": {"sanity": 10, "hunger": 5},
    },
    "Cooked Meat": {
        "type": "food",
        "description": "Freshly cooked meat, hearty and filling.",
        "effect": {"heal": 10, "hunger": 35},
    },
    "Meat": {
        "type": "ingredient",
        "description": "Raw meat harvested from a beast.",
        "effect": {},
    },
    "Fire": {
        "type": "ingredient",
        "description": "A flicker of captured flame. Useful in crafting.",
        "effect": {},
    },
    "Stone": {
        "type": "ingredient",
        "description": "A sturdy piece of stone.",
        "effect": {},
    },
    "Wood": {
        "type": "ingredient",
        "description": "Damp but usable wood.",
        "effect": {},
    },
    "Ether Potion": {
        "type": "consumable",
        "description": "A bottle of shimmering ether that restores sanity and stamina.",
        "effect": {"sanity": 20, "stamina": 15},
    },
    "Essence": {
        "type": "ingredient",
        "description": "Crystallised monster essence.",
        "effect": {},
    },
    "Bone": {
        "type": "ingredient",
        "description": "Jagged bone, still pulsing faintly with ether.",
        "effect": {},
    },
    "Ether Blade": {
        "type": "weapon",
        "description": "A blade forged from essence. It hums with power.",
        "effect": {"attack_bonus": 6},
    },
    "Bandage": {
        "type": "consumable",
        "description": "Clean bandages to stop the bleeding.",
        "effect": {"heal": 8},
    },
}


class Inventory:
    """Container that stores the player's carried items.

    The inventory maintains a dictionary of item names to :class:`Item`
    instances.  This allows stacking while making lookup operations efficient.
    The capacity value denotes the maximum number of distinct item stacks that
    can be carried simultaneously.
    """

    def __init__(self, capacity: int = 12):
        self.capacity = capacity
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
            self.items[name].quantity += quantity
            return True
        if self.is_full():
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

    def to_dict(self) -> Dict[str, object]:
        return {
            "capacity": self.capacity,
            "items": [item.to_dict() for item in self.items.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Inventory":
        inv = cls(capacity=int(data.get("capacity", 12)))
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
            "Cooked Meat": {
                "ingredients": {"Meat": 1, "Fire": 1},
                "result": ("Cooked Meat", 1),
                "description": "Cook raw meat to restore more hunger.",
            },
            "Ether Blade": {
                "ingredients": {"Essence": 1, "Bone": 1},
                "result": ("Ether Blade", 1),
                "description": "Fuse essence and bone into a potent blade.",
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
