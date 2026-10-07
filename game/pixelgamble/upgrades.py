"""Улучшения между волнами: три случайные карточки, игрок выбирает одну."""

import random

from .settings import PLAYER_MAX_HEARTS

# id: (максимум раз за партию, с какой волны предлагать); иконка — images/icons/<id>.png
POOL = {
    "heart": (4, 1),
    "damage": (4, 1),
    "speed": (3, 1),
    "haste": (3, 1),
    "heal": (99, 2),
    "reach": (3, 1),
    "lance": (1, 2),
    "wand": (1, 3),
    "multishot": (1, 4),
    "vampire": (2, 3),
    "knockback": (2, 2),
}


def available(player, taken, wave):
    result = []
    for key, (limit, from_wave) in POOL.items():
        if taken.get(key, 0) >= limit or wave < from_wave:
            continue
        if key == "heal" and player.hp >= player.max_hp:
            continue
        if key == "heart" and player.max_hp >= PLAYER_MAX_HEARTS * 4:
            continue
        if key == "multishot" and "wand" not in player.weapons:
            continue
        result.append(key)
    return result


def offer(player, taken, wave, rng=random):
    keys = available(player, taken, wave)
    # новое оружие показываем охотнее: оно меняет то, как играется партия
    weights = [3 if k in ("lance", "wand") else 1 for k in keys]
    picked = []
    while keys and len(picked) < 3:
        k = rng.choices(keys, weights)[0]
        i = keys.index(k)
        keys.pop(i)
        weights.pop(i)
        picked.append(k)
    return picked


def apply(key, player, taken):
    taken[key] = taken.get(key, 0) + 1
    if key == "heart":
        player.max_hp += 4
        player.heal(4)
    elif key == "damage":
        player.damage_mult *= 1.15
    elif key == "speed":
        player.speed *= 1.12
    elif key == "haste":
        player.cooldown_mult *= 0.88
    elif key == "heal":
        player.heal(player.max_hp)
    elif key == "reach":
        player.reach_mult *= 1.2
    elif key in ("lance", "wand"):
        player.unlock(key)
    elif key == "multishot":
        player.multishot = True
    elif key == "vampire":
        player.vampire += 0.12
    elif key == "knockback":
        player.knock_mult *= 1.4
