"""Random event handlers, NPC dialogues and crafting for MVP7."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from inventory import CraftingSystem
from player import Player


@dataclass
class NPCDialogue:
    """Represents a branching conversation node."""

    name: str
    portrait: str
    description: str
    options: Sequence[Dict[str, object]]


class EventSystem:
    """Manages world events that can occur during exploration."""

    def __init__(self):
        self.ether_storm_timer: int = 0
        self.crafting = CraftingSystem()
        self.merchant_inventory: List[str] = ["Bread", "Torch", "Refined Tonic", "Bandage"]
        self.memory_fragments: List[str] = [
            "You recall the first time the ether whispered your name...",
            "A child's laughter echoes, then twists into static.",
            "The city above drowned beneath luminous tides.",
            "Hands reaching from a mirror pull you into the depth.",
        ]
        self.fragment_index: int = 0

    def is_darkened(self) -> bool:
        return self.ether_storm_timer > 0

    def tick(self) -> None:
        if self.ether_storm_timer > 0:
            self.ether_storm_timer -= 1

    # -- Event management ---------------------------------------------
    def trigger_random_event(self, player: Player, rng: Optional[random.Random] = None) -> List[str]:
        rng = rng or random.Random()
        events = [
            self.hallucination_event,
            self.memory_fragment_event,
            self.merchant_event,
            self.whisperer_event,
            self.prisoner_event,
            self.scholar_event,
            self.environmental_event,
            self.ether_storm_event,
        ]
        weights = [
            0.2 if player.sanity < 25 else 0.1,
            0.1,
            0.15,
            0.1,
            0.1,
            0.1,
            0.15,
            0.1,
        ]
        event = rng.choices(events, weights=weights, k=1)[0]
        messages = event(player, rng)
        if rng.random() < 0.4:
            messages.append(self.sound_cue(rng))
        return messages

    def sound_cue(self, rng: random.Random) -> str:
        return rng.choice(
            [
                "[sound] You hear footsteps...",
                "[sound] Something whispers your name.",
                "[sound] Chains rattle deep below.",
            ]
        )

    # -- Event implementations ----------------------------------------
    def hallucination_event(self, player: Player, rng: random.Random) -> List[str]:
        loss = rng.randint(1, 5)
        player.sanity = max(0, player.sanity - loss)
        return [
            "A wave of nausea hits you as the world bends out of shape...",
            "Illusory silhouettes stalk the edges of your vision.",
            f"You lose {loss} sanity points.",
        ]

    def memory_fragment_event(self, player: Player, rng: random.Random) -> List[str]:
        if self.fragment_index >= len(self.memory_fragments):
            return ["A familiar silence blankets the corridor."]
        fragment = self.memory_fragments[self.fragment_index]
        self.fragment_index += 1
        player.karma += 1
        return ["A memory fragment surfaces...", fragment]

    def merchant_event(self, player: Player, rng: random.Random) -> List[str]:
        npc = NPCDialogue(
            name="Merchant",
            portrait="[M]",
            description="A robed merchant emerges from the shadows.",
            options=[
                {"text": "Trade", "action": "trade"},
                {"text": "Share a story", "action": "story"},
                {"text": "Leave", "action": "leave"},
            ],
        )
        print(self._npc_header(npc))
        for index, option in enumerate(npc.options, 1):
            print(f"  {index}. {option['text']}")
        choice = input("Choose: ").strip()
        if choice == "1":
            return self._perform_trade(player, rng)
        if choice == "2":
            player.karma += 2
            player.restore_sanity(2)
            return ["You swap tales and gain a sliver of hope (+2 SAN)."]
        return ["You bow out of the negotiation."]

    def _perform_trade(self, player: Player, rng: random.Random) -> List[str]:
        inventory = list(self.merchant_inventory)
        rng.shuffle(inventory)
        offers = inventory[:3]
        costs = {"Bread": 1, "Torch": 1, "Refined Tonic": 3, "Bandage": 2, "Legendary Elixir": 5}
        print("The merchant reveals glittering wares:")
        for index, item in enumerate(offers, 1):
            price = costs.get(item, 2)
            print(f"  {index}. {item} ({price} Essence)")
        print("  0. Exit trade")
        currency = player.inventory.items.get("Essence")
        essence = currency.quantity if currency else 0
        choice = input(f"Essence shards [{essence}]. Buy what? ").strip()
        if choice == "0" or not choice.isdigit():
            return ["You end the trade."]
        index = int(choice) - 1
        if not (0 <= index < len(offers)):
            return ["The merchant frowns at your confusion."]
        item = offers[index]
        cost = costs.get(item, 2)
        if not player.inventory.has_item("Essence", cost):
            return ["You lack the required essence."]
        if not player.inventory.add_item(item):
            return ["You cannot carry any more."]
        player.inventory.remove_item("Essence", cost)
        self.merchant_inventory.append("Legendary Elixir")
        return [f"Purchased {item}."]

    def whisperer_event(self, player: Player, rng: random.Random) -> List[str]:
        npc = NPCDialogue(
            name="Whisperer",
            portrait="[W]",
            description="A cloaked figure mutters forbidden names.",
            options=[
                {"text": "Listen", "action": "listen"},
                {"text": "Refuse", "action": "refuse"},
            ],
        )
        print(self._npc_header(npc))
        print("Their voice cuts through the hum of ether.")
        for index, option in enumerate(npc.options, 1):
            print(f"  {index}. {option['text']}")
        choice = input("Choose: ").strip()
        if choice == "1":
            player.apply_status("fear", 3)
            player.karma -= 2
            return ["Knowledge claws at your mind (-2 karma, Fear applied)."]
        player.restore_sanity(3)
        return ["You resist the whispers (+3 SAN)."]

    def prisoner_event(self, player: Player, rng: random.Random) -> List[str]:
        npc = NPCDialogue(
            name="Old Prisoner",
            portrait="[O]",
            description="An emaciated prisoner rattles spectral chains.",
            options=[
                {"text": "Free him (use Bandage)", "action": "free"},
                {"text": "Extract information", "action": "info"},
                {"text": "Leave", "action": "leave"},
            ],
        )
        print(self._npc_header(npc))
        for index, option in enumerate(npc.options, 1):
            print(f"  {index}. {option['text']}")
        choice = input("Choose: ").strip()
        if choice == "1":
            if player.inventory.remove_item("Bandage"):
                player.karma += 3
                player.restore_sanity(4)
                return ["You tend to his wounds. Gratitude warms you (+karma, +SAN)."]
            return ["You have no bandage to spare."]
        if choice == "2":
            player.karma -= 1
            player.inventory.add_item("Cloth")
            return ["His whispers reveal hidden alcoves (-karma, gained Cloth)."]
        return ["You leave the prisoner to his fate."]

    def scholar_event(self, player: Player, rng: random.Random) -> List[str]:
        npc = NPCDialogue(
            name="Wandering Scholar",
            portrait="[S]",
            description="A scholar sketches glyphs on the floor.",
            options=[
                {"text": "Study together", "action": "study"},
                {"text": "Demand knowledge", "action": "demand"},
            ],
        )
        print(self._npc_header(npc))
        for index, option in enumerate(npc.options, 1):
            print(f"  {index}. {option['text']}")
        choice = input("Choose: ").strip()
        if choice == "1":
            player.restore_sanity(2)
            player.inventory.add_item("Crystal Shard")
            return ["You learn new sigils (+SAN, gained Crystal Shard)."]
        player.karma -= 2
        player.apply_status("fear", 2)
        return ["He recoils and curses your greed (-karma, Fear applied)."]

    def environmental_event(self, player: Player, rng: random.Random) -> List[str]:
        hazards = [
            ("A pocket of toxic gas bursts!", ("poison", 3)),
            ("Frost creeps along the walls...", ("freeze", 2)),
            ("The ground pulses with dread.", ("fear", 2)),
        ]
        description, status = rng.choice(hazards)
        player.apply_status(status[0], status[1])
        return [description, f"You are afflicted with {status[0].title()}!"]

    def ether_storm_event(self, player: Player, rng: random.Random) -> List[str]:
        duration = rng.randint(4, 8)
        self.ether_storm_timer = duration
        player.light_bonus = 0
        player.light_bonus_timer = 0
        return ["An ether storm howls. All lights sputter out!", f"Darkness will linger for {duration} turns."]

    # -- Campfires -----------------------------------------------------
    def can_build_campfire(self, player: Player) -> bool:
        return player.inventory.has_item("Camp Supplies") or (
            player.inventory.has_item("Wood") and player.inventory.has_item("Fire")
        )

    def build_campfire(self, player: Player) -> Optional[str]:
        if not self.can_build_campfire(player):
            return None
        if player.inventory.remove_item("Camp Supplies"):
            return "You arrange the camp supplies and spark a fire."
        if player.inventory.remove_item("Wood") and player.inventory.remove_item("Fire"):
            return "You combine wood and captured flame into a campfire."
        return None

    # -- Crafting ------------------------------------------------------
    def list_crafting_options(self) -> Iterable[tuple[str, Dict[str, object]]]:
        return self.crafting.list_recipes()

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

    # -- Helpers -------------------------------------------------------
    def _npc_header(self, npc: NPCDialogue) -> str:
        border = "+" + "-" * 28 + "+"
        portrait_line = f"| {npc.portrait:<26}|"
        description_line = f"| {npc.description[:26]:<26}|"
        return "\n".join([border, portrait_line, description_line, border])

