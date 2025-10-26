"""Entry point for The Depths of Ether (MVP7 Enhanced Edition)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from enemy_ai import Enemy, enemy_factory
from event_system import EventSystem
from map_gen import DungeonMap
from player import Player, default_player
from save_load import SaveManager
from ui_console import draw_interface, render_inventory
from inventory import ITEM_LIBRARY


ASCII_LOGO = [
    "     ________  __            __          __             ",
    "    /_  __/ / / /___  ____  / /_  ____ _/ /_____  _____ ",
    "     / / / /_/ / __ \\ / __ \\ / / / / __ `/ __/ __ \\/ ___/ ",
    "    / / / __  / /_/ / /_/ / / /_/ / /_/ / /_/ /_/ / /    ",
    "   /_/ /_/ /_/ .___/\\____/_/\\__,_/\\__,_/\\__/\\____/_/     ",
    "            /_/                                         ",
]


@dataclass
class GameState:
    player: Player
    dungeon: DungeonMap
    enemies: List[Enemy]
    log: List[str] = field(default_factory=list)
    event_system: EventSystem = field(default_factory=EventSystem)
    rng: random.Random = field(default_factory=random.Random)
    finale_reached: bool = False

    def log_event(self, message: str) -> None:
        self.log.append(message)
        if len(self.log) > 120:
            self.log = self.log[-120:]


def display_intro() -> None:
    for frame in range(2):
        print("\n".join(ASCII_LOGO))
        if frame == 0:
            time.sleep(0.8)
            print("\nThe Depths of Ether - Enhanced Edition")
            time.sleep(1.2)
        time.sleep(0.4)
        if frame == 0:
            time.sleep(0.6)
            print("\nLegends speak of explorers who descended, never to return...")
            time.sleep(1.8)
            print("You are the latest whisper drifting into the void.")
            time.sleep(1.8)
        if frame == 0:
            time.sleep(1.0)
        time.sleep(0.5)


def trait_selection(player: Player) -> None:
    traits = {
        "1": ("Mind Anchor", "+10 SAN and hardened resolve."),
        "2": ("Quickstep", "+6 STA and swift reflexes."),
        "3": ("Vital Bloom", "+8 HP blossoms within."),
        "4": ("Packrat", "Carry more without strain."),
        "5": ("Seer", "Wider vision and clairvoyance."),
        "6": ("Bulwark", "Stalwart defenses and block chance."),
    }
    print("\nChoose a starting trait:")
    for key, (name, desc) in traits.items():
        print(f"  {key}. {name} - {desc}")
    choice = input("Trait: ").strip()
    name = traits.get(choice, traits["1"])[0]
    player.apply_trait(name)


def create_new_game(seed: Optional[int] = None) -> GameState:
    rng = random.Random(seed)
    player = default_player()
    trait_selection(player)
    dungeon = DungeonMap(floor=player.floor)
    dungeon.generate(rng)
    player.position = dungeon.start_position
    player.floor = dungeon.floor
    dungeon.reveal_around(player.position, player.vision_radius)
    enemies = [enemy_factory(enemy_type, pos) for enemy_type, pos in dungeon.enemy_spawns]
    state = GameState(player=player, dungeon=dungeon, enemies=enemies, rng=rng)
    state.log_event("You descend into the Depths of Ether.")
    return state


def load_game(manager: SaveManager) -> Optional[GameState]:
    loaded = manager.load()
    if not loaded:
        return None
    player, dungeon, enemies, log, event_state = loaded
    state = GameState(player=player, dungeon=dungeon, enemies=enemies, log=log)
    state.event_system.ether_storm_timer = int(event_state.get("ether_storm", 0))
    inventory = event_state.get("merchant_inventory")
    if isinstance(inventory, list):
        state.event_system.merchant_inventory = list(inventory)
    state.event_system.fragment_index = int(event_state.get("memory_index", 0))
    dungeon.reveal_around(player.position, player.vision_radius)
    return state


def attempt_move(state: GameState, dx: int, dy: int) -> None:
    player = state.player
    dungeon = state.dungeon
    target = (player.position[0] + dx, player.position[1] + dy)
    enemy = next((e for e in state.enemies if e.position == target and e.is_alive()), None)
    if enemy:
        messages, player_alive = combat_loop(state, enemy)
        for msg in messages:
            state.log_event(msg)
        if not player_alive:
            return
        state.enemies = [e for e in state.enemies if e.is_alive()]
        return
    if not dungeon.in_bounds(*target) or not dungeon.is_walkable(*target):
        if dungeon.discover_hidden(*target):
            state.log_event("You uncover a hidden door leading deeper in.")
        else:
            state.log_event("You bump into a wall.")
        return
    if player.move(dx, dy, dungeon):
        biome_temp = int(dungeon.biome.get("temperature", 0))
        player.adjust_temperature(biome_temp)
        if target in dungeon.hazards:
            hazard = dungeon.hazards[target]
            if hazard == "gas":
                player.apply_status("poison", 2)
                state.log_event("You cough as toxic gas engulfs you!")
            elif hazard == "cold":
                player.apply_status("freeze", 2)
                state.log_event("A chill wind bites at your bones.")
            elif hazard == "curse":
                player.apply_status("fear", 2)
                state.log_event("A curse prickles along your spine.")
        state.log_event("You move silently through the corridor.")
        gather_items(state)
        trigger_random_event(state)
    else:
        state.log_event("Your path is blocked.")


def gather_items(state: GameState) -> None:
    player = state.player
    items = state.dungeon.take_items(player.position)
    for item in items:
        if player.inventory.add_item(item):
            state.log_event(f"Picked up {item}.")
        else:
            state.log_event(f"Your pack groans under the weight. {item} remains here.")
            state.dungeon.place_item(player.position, item)


def trigger_random_event(state: GameState) -> None:
    rng = state.rng
    chance = 0.22 if state.player.sanity < 25 else 0.15
    if rng.random() < chance:
        messages = state.event_system.trigger_random_event(state.player, rng)
        for message in messages:
            state.log_event(message)
    state.event_system.tick()
    if state.player.sanity < 25:
        if state.player.hallucination_cooldown <= 0:
            phantom = rng.choice([
                "A phantom hunter rushes past and dissolves.",
                "You hear a false alarm bell tolling.",
                "Your shadow detaches then fuses back into you.",
            ])
            state.log_event(phantom)
            state.player.hallucination_cooldown = 6
        else:
            state.player.hallucination_cooldown -= 1


def update_enemies(state: GameState) -> None:
    occupied = {enemy.position for enemy in state.enemies if enemy.is_alive()}
    for enemy in state.enemies:
        if not enemy.is_alive():
            continue
        message = enemy.take_turn(state.dungeon, state.player.position, occupied, state.rng)
        if message:
            state.log_event(message)
        if enemy.position == state.player.position and enemy.is_alive():
            messages, player_alive = combat_loop(state, enemy)
            for msg in messages:
                state.log_event(msg)
            if not player_alive:
                return
    state.enemies = [enemy for enemy in state.enemies if enemy.is_alive()]


def player_attack(player: Player, enemy: Enemy, weapon: Optional[str], rng: random.Random) -> str:
    if not weapon:
        base_attack = player.base_attack
        crit_bonus = 5
        status_effect = None
    else:
        effect = dict(ITEM_LIBRARY.get(weapon, {}).get("effect", {}))
        base_attack = player.base_attack + int(effect.get("attack_bonus", 0))
        crit_bonus = 5 + int(effect.get("crit_bonus", 0))
        status_effect = effect.get("status")
    crit = rng.randint(1, 100) <= crit_bonus
    damage = max(1, base_attack + rng.randint(0, 4))
    if crit:
        damage += int(damage * 0.5)
    dealt = enemy.take_damage(damage)
    if status_effect and rng.random() < 0.35:
        enemy.apply_status(str(status_effect), 3)
    return f"You {'critically ' if crit else ''}strike the {enemy.species} for {dealt} damage."


def combat_loop(state: GameState, enemy: Enemy) -> Tuple[List[str], bool]:
    from ui_console import clear_screen

    rng = state.rng
    player = state.player
    log: List[str] = [f"A {enemy.species} engages you!"]
    defending = False
    while enemy.is_alive() and player.is_alive():
        clear_screen()
        print(f"Enemy: {enemy.species} HP {enemy.hp}/{enemy.max_hp}")
        print(
            f"Player HP {player.hp}/{player.max_hp} STA {player.stamina}/{player.max_stamina} "
            f"SAN {player.sanity}/{player.max_sanity}"
        )
        print("Actions: [1] Melee [2] Ranged [3] Defend [4] Item [5] Run")
        for entry in log[-6:]:
            print(entry)
        choice = input("> ").strip().lower()
        if choice == "1":
            if player.has_status("freeze"):
                log.append("Frozen limbs slow your strike!")
            message = player_attack(player, enemy, player.melee_weapon, rng)
            player.degrade_equipment("melee")
            player.spend_stamina(3)
            log.append(message)
        elif choice == "2" and player.ranged_weapon:
            message = player_attack(player, enemy, player.ranged_weapon, rng)
            player.degrade_equipment("ranged")
            player.spend_stamina(4)
            log.append(message + " (ranged)")
        elif choice == "3":
            defending = True
            log.append("You brace for the next attack.")
        elif choice == "4":
            render_inventory(player)
            item = input("Use which item? (blank to cancel) ").strip()
            if item:
                log.append(player.use_item(item))
        elif choice == "5":
            if rng.random() < 0.45:
                log.append("You slip away from combat.")
                return log, True
            else:
                log.append("The enemy blocks your escape!")
        else:
            log.append("You hesitate, losing precious time!")

        if not enemy.is_alive():
            break

        base_damage, inflicted = enemy.attack_damage(rng)
        mitigation = player.defense + (3 if defending else 0)
        blocked = rng.randint(1, 100) <= player.armor_block_chance
        if blocked:
            mitigation += rng.randint(2, 4)
        damage = max(1, base_damage - mitigation)
        player.hp = max(0, player.hp - damage)
        if blocked:
            log.append("Your armor deflects part of the blow!")
        log.append(f"The {enemy.species} hits you for {damage} damage!")
        player.degrade_armor()
        if inflicted:
            status, duration = inflicted
            player.apply_status(status, duration)
            log.append(f"You suffer {status.title()} for {duration} turns!")
        defending = False
    loot_messages: List[str] = []
    if not enemy.is_alive():
        loot = enemy.roll_loot(rng)
        xp_messages = player.gain_xp(enemy.xp_reward)
        log.extend(xp_messages)
        if loot:
            for item in loot:
                if player.inventory.add_item(item):
                    loot_messages.append(f"Looted {item}.")
                else:
                    state.dungeon.place_item(player.position, item)
                    loot_messages.append(f"No room for {item}; it drops to the ground.")
            log.extend(loot_messages)
        log.append(f"The {enemy.species} is defeated.")
    if not player.is_alive():
        log.append("You collapse as the darkness closes in...")
    return log, player.is_alive()


def stairs_check(state: GameState, manager: SaveManager) -> None:
    if state.player.position == state.dungeon.stairs_position:
        choice = input("A stairway descends. Take it? (y/n) ").strip().lower()
        if choice.startswith("y"):
            next_floor(state, manager)


def next_floor(state: GameState, manager: SaveManager) -> None:
    state.player.floor += 1
    if state.player.floor > 6 and state.player.sanity >= state.player.max_sanity // 2 and state.player.karma >= 5:
        true_ending_cinematic(state)
        return
    new_map = DungeonMap(floor=state.player.floor)
    new_map.generate(state.rng)
    state.player.position = new_map.start_position
    state.dungeon = new_map
    state.enemies = [enemy_factory(kind, pos) for kind, pos in new_map.enemy_spawns]
    state.dungeon.reveal_around(state.player.position, state.player.vision_radius)
    state.log_event(f"You descend to floor {state.player.floor}.")
    manager.save(
        state.player,
        state.dungeon,
        state.enemies,
        state.log,
        {
            "ether_storm": state.event_system.ether_storm_timer,
            "merchant_inventory": state.event_system.merchant_inventory,
            "memory_index": state.event_system.fragment_index,
        },
    )
    state.log_event("The ether remembers your steps (auto-save).")


def check_game_over(state: GameState) -> bool:
    player = state.player
    if state.finale_reached:
        print("\nYou transcend the Depths of Ether, memories intact.")
        return True
    if player.hp <= 0:
        state.log_event("Your body fails. The depths claim another soul.")
        bad_ending(state, reason="body")
        return True
    if player.sanity <= 0:
        state.log_event("Your mind shatters under the ether's whispers.")
        bad_ending(state, reason="mind")
        return True
    return False


def show_help() -> None:
    print("\nControls:")
    print("  WASD - Move")
    print("  I    - Inventory")
    print("  C    - Crafting")
    print("  R    - Rest")
    print("  Z    - Sleep")
    print("  F    - Campfire actions")
    print("  P    - Spend skill points")
    print("  Q    - Save and Quit")
    print("  ?    - Show this help")
    input("Press Enter to continue...")


def spend_skill_points(player: Player) -> str:
    if player.skill_points <= 0:
        return "You have no skill points to spend."
    print("Spend skill points on: hp, stamina, sanity, attack, defense")
    attribute = input("Attribute: ").strip()
    return player.spend_skill_point(attribute)


def campfire_action(state: GameState, manager: SaveManager) -> None:
    position = state.player.position
    dungeon = state.dungeon
    if position in dungeon.campfires:
        print("You stand before a campfire. Options:")
        print("  1. Rest")
        print("  2. Sleep")
        print("  3. Craft")
        print("  4. Save")
        choice = input("Choose: ").strip()
        if choice == "1":
            state.log_event(state.player.rest(at_campfire=True))
            trigger_random_event(state)
            update_enemies(state)
        elif choice == "2":
            state.log_event(state.player.sleep_turn(at_campfire=True))
            trigger_random_event(state)
            update_enemies(state)
        elif choice == "3":
            for msg in state.event_system.attempt_crafting(state.player):
                state.log_event(msg)
        elif choice == "4":
            manager.save(
                state.player,
                state.dungeon,
                state.enemies,
                state.log,
                {
                    "ether_storm": state.event_system.ether_storm_timer,
                    "merchant_inventory": state.event_system.merchant_inventory,
                    "memory_index": state.event_system.fragment_index,
                },
            )
            state.log_event("Campfire sparks preserve your journey.")
    else:
        message = state.event_system.build_campfire(state.player)
        if message:
            dungeon.campfires.add(position)
            state.log_event(message)
        else:
            state.log_event("You lack the supplies to raise a campfire.")


def true_ending_cinematic(state: GameState) -> None:
    state.log_event("You reach the heart of the Ether. Warm light surrounds you.")
    print("\n@ fades into the void...")
    time.sleep(1.2)
    print("The Ether remembers you.")
    time.sleep(1.2)
    print("Visions of those you saved shimmer in the air.")
    state.finale_reached = True
    state.player.hp = 0
    state.player.sanity = 0


def bad_ending(state: GameState, reason: str) -> None:
    if reason == "body":
        print("\nAs your strength fades, you hear the echoes of unfinished stories.")
    else:
        print("\nMadness blossoms and the Ether drinks deeply of your fear.")
    time.sleep(1.0)


def main_loop(state: GameState, manager: SaveManager) -> None:
    running = True
    while running and state.player.is_alive():
        state.dungeon.reveal_around(state.player.position, state.player.vision_radius)
        draw_interface(state.dungeon, state.player, state.enemies, state.log, state.event_system.ether_storm_timer)
        command = input("\nCommand (WASD/I/C/R/Z/F/P/Q/?): ").strip().lower()
        if command in {"w", "a", "s", "d"}:
            offsets = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
            attempt_move(state, *offsets[command])
            update_enemies(state)
            stairs_check(state, manager)
        elif command == "i":
            render_inventory(state.player)
            item = input("Use which item? (blank to cancel) ").strip()
            if item:
                state.log_event(state.player.use_item(item))
        elif command == "c":
            messages = state.event_system.attempt_crafting(state.player)
            for msg in messages:
                state.log_event(msg)
        elif command == "r":
            state.log_event(state.player.rest())
            trigger_random_event(state)
            update_enemies(state)
        elif command == "z":
            state.log_event(state.player.sleep_turn())
            trigger_random_event(state)
            update_enemies(state)
        elif command == "f":
            campfire_action(state, manager)
        elif command == "p":
            state.log_event(spend_skill_points(state.player))
        elif command == "q":
            choice = input("Save game before exiting? (y/n) ").strip().lower()
            if choice.startswith("y"):
                manager.save(
                    state.player,
                    state.dungeon,
                    state.enemies,
                    state.log,
                    {
                        "ether_storm": state.event_system.ether_storm_timer,
                        "merchant_inventory": state.event_system.merchant_inventory,
                        "memory_index": state.event_system.fragment_index,
                    },
                )
                state.log_event("Game saved.")
            running = False
        elif command == "?":
            show_help()
        else:
            state.log_event("Unknown command.")
        if check_game_over(state):
            running = False
    draw_interface(state.dungeon, state.player, state.enemies, state.log, state.event_system.ether_storm_timer)
    print("\nGame over. Thanks for playing!")


def choose_save_slot(manager: SaveManager) -> None:
    print("Select save slot (1-3). Current:", manager.slot)
    choice = input("Slot: ").strip()
    if choice.isdigit():
        manager.set_slot(int(choice))


def show_menu() -> str:
    print("=" * 60)
    print("      THE DEPTHS OF ETHER - ENHANCED EDITION")
    print("=" * 60)
    print("1. New Game")
    print("2. Continue")
    print("3. Select Save Slot")
    print("4. Exit")
    return input("Select option: ").strip()


def main() -> None:
    display_intro()
    manager = SaveManager()
    while True:
        choice = show_menu()
        if choice == "1":
            state = create_new_game()
            main_loop(state, manager)
        elif choice == "2":
            state = load_game(manager)
            if state:
                main_loop(state, manager)
            else:
                print("No save data found for this slot.")
        elif choice == "3":
            choose_save_slot(manager)
        elif choice == "4":
            break
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    main()

