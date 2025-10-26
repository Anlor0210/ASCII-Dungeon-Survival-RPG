"""Console user interface helpers for The Depths of Ether MVP7."""

from __future__ import annotations

import os
from itertools import zip_longest
from typing import Iterable, List, Sequence

from enemy_ai import Enemy
from map_gen import DungeonMap, TILE_UNKNOWN
from player import Player


COLOR_RESET = "\033[0m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[34m"
COLOR_YELLOW = "\033[33m"
COLOR_GREEN = "\033[32m"
COLOR_PURPLE = "\033[35m"


BORDER = "+" + "-" * 90 + "+"


def color_text(text: str, color: str) -> str:
    if not os.getenv("ANSI_COLORS_DISABLED"):
        return f"{color}{text}{COLOR_RESET}"
    return text


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def render_map(dungeon: DungeonMap, player: Player, enemies: Sequence[Enemy]) -> List[str]:
    lines: List[str] = []
    visible = set(dungeon.visible)
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
                glyph = enemy_positions[pos].symbol
                if enemy_positions[pos].boss:
                    glyph = color_text(glyph, COLOR_PURPLE)
                row_chars.append(glyph)
                continue
            if pos in visible:
                row_chars.append(dungeon.tile_glyph(x, y))
            elif pos in dungeon.revealed:
                row_chars.append(" ")
            else:
                row_chars.append(TILE_UNKNOWN)
        lines.append("".join(row_chars))
    return lines


def render_hud(player: Player, dungeon: DungeonMap, storm_turns: int) -> List[str]:
    weight = player.inventory.total_weight()
    capacity = player.carry_capacity
    hp_color = COLOR_RED if player.hp <= player.max_hp // 3 else COLOR_GREEN
    san_color = COLOR_PURPLE if player.sanity <= player.max_sanity // 3 else COLOR_BLUE
    status_line = (
        f"HP {player.hp}/{player.max_hp}"
        f" | STA {player.stamina}/{player.max_stamina}"
        f" | SAN {player.sanity}/{player.max_sanity}"
        f" | HGR {player.hunger}/{player.max_hunger}"
        f" | FAT {player.fatigue}/{player.max_fatigue}"
    )
    status_line = status_line.replace(
        f"HP {player.hp}/{player.max_hp}", color_text(f"HP {player.hp}/{player.max_hp}", hp_color)
    )
    status_line = status_line.replace(
        f"SAN {player.sanity}/{player.max_sanity}",
        color_text(f"SAN {player.sanity}/{player.max_sanity}", san_color),
    )
    aux_line = (
        f"Floor {dungeon.floor} ({dungeon.biome.get('name', 'Unknown')})"
        f" | XP {player.xp}/{player.xp_to_next}"
        f" | LV {player.level}"
        f" | Karma {player.karma}"
        f" | Temp {player.temperature}"
        f" | Weight {weight:.1f}/{capacity:.1f}"
    )
    if storm_turns > 0:
        aux_line += color_text(f" | Ether Storm {storm_turns}", COLOR_YELLOW)
    return [BORDER, f"| {status_line:<88} |", f"| {aux_line:<88} |", BORDER]


def render_status_panel(player: Player) -> List[str]:
    lines = [" Status ".center(30, "-")]
    if player.status_effects:
        for status, turns in player.status_effects.items():
            lines.append(f" {status.title():<12} {turns:>3}t")
    else:
        lines.append(" Calm")
    if player.skill_points:
        lines.append(f" Skill Points: {player.skill_points}")
    if player.traits:
        lines.append(" Trait: " + ", ".join(player.traits))
    return lines


def render_log(log: Sequence[str], max_entries: int = 9) -> List[str]:
    entries = list(log)[-max_entries:]
    output = [" Event Log ".center(40, "-")]
    for entry in entries:
        output.append(entry[:40])
    output.append("-" * 40)
    return output


def render_inventory(player: Player) -> None:
    print("\nInventory:")
    if not player.inventory.items:
        print("  (empty)")
        return
    for item in player.inventory.list_items():
        weight = player.inventory.item_weight(item.name)
        print(f"  {item.name} x{item.quantity} (wt {weight:.1f})")
    if player.melee_weapon:
        print(f"Equipped melee: {player.melee_weapon} ({player.melee_durability} durability)")
    if player.ranged_weapon:
        print(f"Equipped ranged: {player.ranged_weapon} ({player.ranged_durability} durability)")
    if player.armor:
        print(f"Armor: {player.armor} ({player.armor_durability} durability)")


def prompt_action(prompt: str, options: Iterable[str]) -> str:
    opts = list(options)
    while True:
        choice = input(prompt).strip().lower()
        if choice in opts:
            return choice
        print(f"Choose from: {', '.join(opts)}")


def draw_interface(
    dungeon: DungeonMap,
    player: Player,
    enemies: Sequence[Enemy],
    log: Sequence[str],
    storm_turns: int,
) -> None:
    clear_screen()
    hud_lines = render_hud(player, dungeon, storm_turns)
    map_lines = render_map(dungeon, player, enemies)
    log_lines = render_log(log)
    status_lines = render_status_panel(player)
    for line in hud_lines:
        print(line)
    combined_panel = []
    for map_line, log_line in zip_longest(map_lines, log_lines, fillvalue=""):
        combined_panel.append(f"{map_line:<60} {log_line}")
    print("\n".join(combined_panel))
    print("\n".join(status_lines))

