"""Игрок и его оружие."""

import pygame

from . import assets
from .entity import DIR_VECTORS, Entity, Vector, direction_name
from .settings import PLAYER_HEARTS, PLAYER_INVULNERABLE, PLAYER_SPEED

WEAPONS = {
    # kind: arc — широкий взмах перед собой, thrust — длинный узкий укол насквозь, bolt — снаряд
    "sword": {"kind": "arc", "damage": 12, "cooldown": 0.36, "reach": 20, "width": 34, "knock": 160},
    "lance": {"kind": "thrust", "damage": 17, "cooldown": 0.52, "reach": 38, "width": 12, "knock": 120},
    "wand": {"kind": "bolt", "damage": 9, "cooldown": 0.40, "speed": 240, "life": 0.85, "knock": 70},
}
WEAPON_ORDER = ("sword", "lance", "wand")


class Player(Entity):
    heavy = False

    def __init__(self, pos):
        super().__init__(pos, 10, 8)
        self.frames = assets.character("player.png")
        self.max_hp = PLAYER_HEARTS * 4  # здоровье в четвертях сердечка
        self.hp = self.max_hp
        self.speed = PLAYER_SPEED
        self.damage_mult = 1.0
        self.cooldown_mult = 1.0
        self.reach_mult = 1.0
        self.knock_mult = 1.0
        self.vampire = 0.0
        self.multishot = False
        self.weapons = ["sword"]
        self.weapon = "sword"
        self.cooldown = 0.0
        self.attack_pose = 0.0
        self.invulnerable = 0.0
        self.aim = Vector(0, 1)
        self.moving = False
        self.level = 1
        self.xp = 0
        self.dead = False

    # --- характеристики ---
    def damage(self):
        return WEAPONS[self.weapon]["damage"] * self.damage_mult

    def heal(self, amount):
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp > before

    def hurt(self, amount, source_pos):
        if self.invulnerable > 0 or self.dead:
            return False
        self.hp = max(0, self.hp - amount)
        self.invulnerable = PLAYER_INVULNERABLE
        self.flash = 0.12
        away = self.pos - Vector(source_pos)
        if away.length_squared() > 0:
            self.knock = away.normalize() * 170
        if self.hp == 0:
            self.dead = True
        return True

    def switch(self, step=1, index=None):
        if index is not None:
            if index < len(self.weapons):
                self.weapon = self.weapons[index]
                return True
            return False
        if len(self.weapons) < 2:
            return False
        i = (self.weapons.index(self.weapon) + step) % len(self.weapons)
        self.weapon = self.weapons[i]
        return True

    def unlock(self, weapon):
        if weapon not in self.weapons:
            self.weapons.append(weapon)
            self.weapons.sort(key=WEAPON_ORDER.index)
            self.weapon = weapon

    # --- кадр ---
    def update(self, dt, move, obstacles):
        self.cooldown = max(0.0, self.cooldown - dt)
        self.attack_pose = max(0.0, self.attack_pose - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.flash = max(0.0, self.flash - dt)

        self.moving = move.length_squared() > 0
        if self.moving:
            move = move.normalize()
            self.aim = Vector(move)
            if self.attack_pose <= 0:
                self.facing = direction_name(move)
            speed = self.speed * (0.45 if self.attack_pose > 0 else 1.0)
            self.move(move * speed * dt, obstacles)
        self.apply_knock(dt, obstacles)
        self.animate(dt)

    def try_attack(self, target=None):
        """Начать атаку. target — точка в мире (курсор) или None (по направлению взгляда)."""
        if self.cooldown > 0 or self.dead:
            return None
        weapon = WEAPONS[self.weapon]
        if target is not None:
            aim = Vector(target) - self.pos
            if aim.length_squared() > 0:
                self.aim = aim.normalize()
        if weapon["kind"] == "bolt":
            direction = Vector(self.aim)
        else:
            self.facing = direction_name(self.aim)
            direction = DIR_VECTORS[self.facing]
        self.facing = direction_name(direction)
        self.cooldown = weapon["cooldown"] * self.cooldown_mult
        self.attack_pose = 0.18
        return direction

    def melee_box(self, direction):
        weapon = WEAPONS[self.weapon]
        reach = weapon["reach"] * self.reach_mult
        width = weapon["width"] * (self.reach_mult if weapon["kind"] == "arc" else 1.0)
        center = self.pos + Vector(0, -4) + direction * (reach / 2 + 4)
        if direction.x:
            box = pygame.Rect(0, 0, reach, width)
        else:
            box = pygame.Rect(0, 0, width, reach)
        box.center = (round(center.x), round(center.y))
        return box

    def animate(self, dt):
        frames = self.frames[self.facing]
        if self.attack_pose > 0:
            image = frames["attack"][0]
        elif self.moving:
            self.anim = (self.anim + dt * 8) % 4
            image = frames["walk"][int(self.anim)]
        else:
            image = frames["walk"][0]
        self.place_image(image, 3)
        if self.invulnerable > 0 and int(self.invulnerable * 20) % 2 and self.flash <= 0:
            self.image = self.image.copy()
            self.image.set_alpha(110)

    def gain_xp(self, amount, need):
        """Возвращает число новых уровней."""
        self.xp += amount
        levels = 0
        while self.xp >= need(self.level):
            self.xp -= need(self.level)
            self.level += 1
            levels += 1
        return levels
