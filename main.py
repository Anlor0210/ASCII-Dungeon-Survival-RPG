"""Entry point for The Depths of Ether (MVP6)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from enemy_ai import Enemy, enemy_factory
from event_system import EventSystem
from map_gen import DungeonMap
from player import Player, default_player
from save_load import SaveManager
from ui_console import draw_interface, render_inventory


@dataclass
class GameState:
    player: Player
    dungeon: DungeonMap
    enemies: List[Enemy]
    log: List[str] = field(default_factory=list)
    event_system: EventSystem = field(default_factory=EventSystem)
    rng: random.Random = field(default_factory=random.Random)

    def log_event(self, message: str) -> None:
        self.log.append(message)
        if len(self.log) > 100:
            self.log = self.log[-100:]


def create_new_game(seed: Optional[int] = None) -> GameState:
    rng = random.Random(seed)
    player = default_player()
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
    state.event_system.ether_storm_timer = event_state.get("ether_storm", 0)
    dungeon.reveal_around(player.position, player.vision_radius)
    return state


def attempt_move(state: GameState, dx: int, dy: int) -> None:
    player = state.player
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
    if not state.dungeon.in_bounds(*target) or not state.dungeon.is_walkable(*target):
        state.log_event("You bump into a wall.")
        return
    if player.move(dx, dy, state.dungeon):
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
            state.log_event(f"No room for {item}. It remains on the ground.")
            state.dungeon.place_item(player.position, item)


def trigger_random_event(state: GameState) -> None:
    rng = state.rng
    if rng.random() < 0.15:
        messages = state.event_system.trigger_random_event(state.player, rng)
        for message in messages:
            state.log_event(message)
    state.event_system.tick()


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


def combat_loop(state: GameState, enemy: Enemy) -> Tuple[List[str], bool]:
    from ui_console import clear_screen

    rng = state.rng
    player = state.player
    log: List[str] = [f"A {enemy.species} engages you!"]
    defending = False
    while enemy.is_alive() and player.is_alive():
        clear_screen()
        print(f"Enemy: {enemy.species} HP {enemy.hp}")
        print(f"Player HP {player.hp}/{player.max_hp} STA {player.stamina}/{player.max_stamina} SAN {player.sanity}/{player.max_sanity}")
        print("Actions: [A]ttack, [D]efend, [I]tem, [R]un")
        for entry in log[-5:]:
            print(entry)
        choice = input("> ").strip().lower()
        if choice == "a":
            damage = max(1, player.attack + rng.randint(0, 3))
            dealt = enemy.take_damage(damage)
            log.append(f"You strike the {enemy.species} for {dealt} damage.")
        elif choice == "d":
            defending = True
            log.append("You brace for the next attack.")
        elif choice == "i":
            render_inventory(player)
            item = input("Use which item? (blank to cancel) ").strip()
            if item:
                log.append(player.use_item(item))
        elif choice == "r":
            if rng.random() < 0.4:
                log.append("You slip away from combat.")
                return log, True
            else:
                log.append("The enemy blocks your escape!")
        else:
            log.append("You hesitate, losing precious time!")

        if not enemy.is_alive():
            break

        # Enemy turn
        base_damage = enemy.attack_damage(rng)
        mitigation = player.defense + (2 if defending else 0)
        damage = max(1, base_damage - mitigation)
        player.hp = max(0, player.hp - damage)
        log.append(f"The {enemy.species} hits you for {damage} damage!")
        if enemy.species == "Ghost":
            player.sanity = max(0, player.sanity - 2)
            log.append("Its chilling touch erodes your sanity (-2 SAN).")
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


def stairs_check(state: GameState) -> None:
    if state.player.position == state.dungeon.stairs_position:
        choice = input("A stairway descends. Take it? (y/n) ").strip().lower()
        if choice.startswith("y"):
            next_floor(state)


def next_floor(state: GameState) -> None:
    state.player.floor += 1
    new_map = DungeonMap(floor=state.player.floor)
    new_map.generate(state.rng)
    state.player.position = new_map.start_position
    state.dungeon = new_map
    state.enemies = [enemy_factory(kind, pos) for kind, pos in new_map.enemy_spawns]
    state.dungeon.reveal_around(state.player.position, state.player.vision_radius)
    state.log_event(f"You descend to floor {state.player.floor}.")


def check_game_over(state: GameState) -> bool:
    player = state.player
    if player.hp <= 0:
        state.log_event("Your body fails. The depths claim another soul.")
        return True
    if player.sanity <= 0:
        state.log_event("Your mind shatters under the ether's whispers.")
        return True
    return False


def show_help() -> None:
    print("\nControls:")
    print("  WASD - Move")
    print("  I    - Inventory")
    print("  C    - Crafting")
    print("  R    - Rest")
    print("  Q    - Save and Quit")
    print("  ?    - Show this help")
    input("Press Enter to continue...")


def main_loop(state: GameState, manager: SaveManager) -> None:
    running = True
    while running and state.player.is_alive():
        state.dungeon.reveal_around(state.player.position, state.player.vision_radius)
        draw_interface(state.dungeon, state.player, state.enemies, state.log, state.event_system.ether_storm_timer)
        command = input("\nCommand (WASD/I/C/R/Q/?): ").strip().lower()
        if command in {"w", "a", "s", "d"}:
            offsets = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
            attempt_move(state, *offsets[command])
            update_enemies(state)
            stairs_check(state)
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
        elif command == "q":
            choice = input("Save game before exiting? (y/n) ").strip().lower()
            if choice.startswith("y"):
                manager.save(
                    state.player,
                    state.dungeon,
                    state.enemies,
                    state.log,
                    {"ether_storm": state.event_system.ether_storm_timer},
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


def show_menu() -> str:
    print("=" * 50)
    print("      THE DEPTHS OF ETHER")
    print("=" * 50)
    print("1. New Game")
    print("2. Continue")
    print("3. Exit")
    return input("Select option: ").strip()


def main() -> None:
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
                print("No save data found.")
        elif choice == "3":
            break
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    main()
