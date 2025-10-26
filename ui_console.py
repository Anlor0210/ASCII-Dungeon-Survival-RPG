"""Console UI helpers for The Depths of Ether."""
from __future__ import annotations

import os
from typing import Iterable, List, Sequence

from enemy_ai import Enemy
from map_gen import DungeonMap, TILE_UNKNOWN
from player import Player


BORDER = "+" + "-" * 70 + "+"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def render_map(dungeon: DungeonMap, player: Player, enemies: Sequence[Enemy]) -> List[str]:
    lines: List[str] = []
    visible = dungeon.visible.copy()
    visible.add(player.position)
    enemy_positions = {enemy.position: enemy for enemy in enemies if enemy.is_alive()}
    for y in range(dungeon.height):
        row_chars: List[str] = []
        for x in range(dungeon.width):
            pos = (x, y)
            if pos == player.position:
                row_chars.append("@")
                continue
            if pos in enemy_positions and pos in visible:
                row_chars.append(enemy_positions[pos].symbol)
                continue
            if pos in visible:
                row_chars.append(dungeon.get_tile(x, y))
            elif pos in dungeon.revealed:
                row_chars.append(" ")
            else:
                row_chars.append(TILE_UNKNOWN)
        lines.append("".join(row_chars))
    return lines


def render_hud(player: Player, floor: int, storm_turns: int) -> List[str]:
    status = [
        f"HP {player.hp}/{player.max_hp}",
        f"STA {player.stamina}/{player.max_stamina}",
        f"SAN {player.sanity}/{player.max_sanity}",
        f"HGR {player.hunger}/{player.max_hunger}",
        f"LV {player.level}",
        f"XP {player.xp}/{player.xp_to_next}",
        f"Floor {floor}",
        f"Time {player.time_spent}",
    ]
    if storm_turns > 0:
        status.append(f"Ether Storm: {storm_turns} turns")
    joined = " | ".join(status)
    return [BORDER, f"| {joined:<68} |", BORDER]


def render_log(log: Sequence[str], max_entries: int = 6) -> List[str]:
    entries = list(log)[-max_entries:]
    output = [" Event Log ".center(72, "-")]
    for entry in entries:
        output.append(entry[:72])
    output.append("-" * 72)
    return output


def render_inventory(player: Player) -> None:
    print("\nInventory:")
    if not player.inventory.items:
        print("  (empty)")
        return
    for item in player.inventory.list_items():
        print(f"  {item.name} x{item.quantity}")


def prompt_action(prompt: str, options: Iterable[str]) -> str:
    opts = list(options)
    while True:
        choice = input(prompt).strip().lower()
        if choice in opts:
            return choice
        print(f"Choose from: {', '.join(opts)}")


def draw_interface(dungeon: DungeonMap, player: Player, enemies: Sequence[Enemy], log: Sequence[str], storm_turns: int) -> None:
    clear_screen()
    for line in render_hud(player, dungeon.floor, storm_turns):
        print(line)
    for line in render_map(dungeon, player, enemies):
        print(line)
    for line in render_log(log):
        print(line)
