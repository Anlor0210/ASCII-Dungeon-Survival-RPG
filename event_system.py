"""Random event handlers for The Depths of Ether."""
from __future__ import annotations

import random
from typing import List, Optional

from inventory import CraftingSystem
from player import Player


class EventSystem:
    """Manages world events that can occur during exploration."""

    def __init__(self):
        self.ether_storm_timer: int = 0
        self.crafting = CraftingSystem()

    def is_darkened(self) -> bool:
        return self.ether_storm_timer > 0

    def tick(self) -> None:
        if self.ether_storm_timer > 0:
            self.ether_storm_timer -= 1

    def trigger_random_event(self, player: Player, rng: Optional[random.Random] = None) -> List[str]:
        rng = rng or random.Random()
        events = [
            self.hallucination_event,
            self.merchant_event,
            self.cursed_shrine_event,
            self.ether_storm_event,
        ]
        event = rng.choice(events)
        return event(player, rng)

    # -- Event implementations ------------------------------------------
    def hallucination_event(self, player: Player, rng: random.Random) -> List[str]:
        loss = rng.randint(2, 6)
        player.sanity = max(0, player.sanity - loss)
        scramble = "".join(rng.choice("@#$%^&*") for _ in range(20))
        return [
            "A wave of nausea hits you as the world bends out of shape...",
            f"{scramble}",
            f"You lose {loss} sanity points.",
        ]

    def merchant_event(self, player: Player, rng: random.Random) -> List[str]:
        print("\nA robed merchant emerges from the shadows. \"Care to trade?\"")
        options = {
            "1": ("Buy Torch (2 essence)", self._buy_item, (player, "Torch", 2)),
            "2": ("Buy Bread (1 essence)", self._buy_item, (player, "Bread", 1)),
            "3": ("Buy Ether Potion (3 essence)", self._buy_item, (player, "Ether Potion", 3)),
            "4": ("Sell Bone (+1 essence)", self._sell_item, (player, "Bone", 1)),
            "5": ("Leave", None, None),
        }
        currency = player.inventory.items.get("Essence", None)
        essence = currency.quantity if currency else 0
        print(f"You currently hold {essence} essence shards.")
        while True:
            for key, (desc, _, _) in options.items():
                print(f"  {key}. {desc}")
            choice = input("Choose an option: ").strip()
            action = options.get(choice)
            if not action:
                print("The merchant tilts their head, awaiting a proper response.")
                continue
            if action[1] is None:
                break
            message = action[1](*action[2])  # type: ignore[misc]
            print(message)
        return ["You conclude your dealings with the merchant."]

    def _buy_item(self, player: Player, item: str, cost: int) -> str:
        if not player.inventory.has_item("Essence", cost):
            return "You lack the required essence."
        if not player.inventory.add_item(item):
            return "You cannot carry any more." 
        player.inventory.remove_item("Essence", cost)
        return f"Purchased {item}."

    def _sell_item(self, player: Player, item: str, value: int) -> str:
        if not player.inventory.has_item(item):
            return "You have nothing to offer."
        player.inventory.remove_item(item)
        player.inventory.add_item("Essence", value)
        return "You trade the item for glimmering essence."

    def cursed_shrine_event(self, player: Player, rng: random.Random) -> List[str]:
        print("\nA cursed shrine pulses with violet light. It promises power for blood.")
        print("Sacrifice 5 HP for a permanent attack bonus? (y/n)")
        choice = input("> ").strip().lower()
        if choice.startswith("y") and player.hp > 5:
            player.hp -= 5
            player.base_attack += 1
            return ["You bleed onto the shrine. Power surges through you (+1 ATK)."]
        return ["You resist the dark bargain and step away."]

    def ether_storm_event(self, player: Player, rng: random.Random) -> List[str]:
        duration = rng.randint(4, 8)
        self.ether_storm_timer = duration
        player.light_bonus = 0
        player.light_bonus_timer = 0
        return ["An ether storm howls. All lights sputter out!", f"The darkness will linger for {duration} turns."]

    # -- Crafting --------------------------------------------------------
    def attempt_crafting(self, player: Player) -> List[str]:
        print("\nAvailable recipes:")
        for name, info in self.crafting.list_recipes():
            ingredients = ", ".join(f"{qty}x {item}" for item, qty in info["ingredients"].items())
            print(f"- {name}: {ingredients}")
        recipe = input("Craft which item? (blank to cancel) ").strip()
        if not recipe:
            return ["You decide not to craft anything."]
        message = self.crafting.craft(player.inventory, recipe)
        if message:
            return [message]
        return ["The crafting attempt fails."]
