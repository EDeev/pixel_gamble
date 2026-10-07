"""Босс финальной волны — Красный самурай. Три фазы по уровню здоровья."""

import math
import random

import pygame

from . import assets
from .enemies import Enemy
from .entity import Entity, Vector

BOSS_HP = 2600
# в кадрах 96×96 ноги нарисованы выше нижнего края, чем в кадрах 96×48 — опускаем их до тени
FEET = {"attack": 15, "charge": 19}


class Boss(Enemy):
    boss = True
    heavy = True

    def __init__(self, pos, hp_mult=1.0):
        Entity.__init__(self, pos, 30, 16)  # минуя Enemy.__init__: босса нет в таблице KINDS
        self.kind = "boss"
        self.max_hp = self.hp = BOSS_HP * hp_mult
        self.speed = 34
        self.contact = 2
        self.xp, self.score = 0, 3000
        self.state, self.timer = "spawn", 1.4
        self.cooldown = 1.5
        self.dash_cooldown = 4.0
        self.summon_cooldown = 6.0
        self.burst_cooldown = 5.0
        self.dir = Vector()
        self.side = "right"
        self.phase = 1
        self.slash_hit = False
        self.load_frames()

    def load_frames(self):
        self.frames = {
            "walk": assets.strip("chars/boss_walk.png", 96),
            "idle": assets.strip("chars/boss_idle.png", 96),
            "hit": assets.strip("chars/boss_hit.png", 96),
            "attack_left": assets.strip("chars/boss_attack_l.png", 96),
            "attack_right": assets.strip("chars/boss_attack_r.png", 96),
            "charge_left": assets.strip("chars/boss_charge_l.png", 96),
            "charge_right": assets.strip("chars/boss_charge_r.png", 96),
        }

    @property
    def active(self):
        return self.state not in ("spawn", "roar")

    def hurt(self, amount, source_pos, knock):
        if not self.active:
            return False
        self.hp -= amount
        self.flash = 0.08
        new_phase = 1 if self.hp > self.max_hp * 0.6 else 2 if self.hp > self.max_hp * 0.3 else 3
        if new_phase > self.phase and self.hp > 0:
            self.phase = new_phase
            self.state, self.timer = "roar", 1.0
        return True

    def slash_box(self):
        box = pygame.Rect(0, 0, 58, 44)
        if self.side == "right":
            box.midleft = (self.hitbox.centerx - 6, self.hitbox.centery - 12)
        else:
            box.midright = (self.hitbox.centerx + 6, self.hitbox.centery - 12)
        return box

    def burst(self, game, count):
        start = random.random() * math.tau
        for i in range(count):
            angle = start + math.tau * i / count
            game.enemy_shot(self.pos + Vector(0, -10), Vector(math.cos(angle), math.sin(angle)) * 95, 1)
        game.audio.play("enemy_shoot")

    def think(self, dt, game, obstacles):
        player = game.player
        dist = self.distance_to(player)
        to_player = self.direction_to(player)
        self.dash_cooldown -= dt
        self.summon_cooldown -= dt
        self.burst_cooldown -= dt
        if to_player.x:
            facing_side = "right" if to_player.x > 0 else "left"
        else:
            facing_side = self.side

        if self.state == "roar":
            self.timer -= dt
            game.shake.add(1.5)
            if self.timer <= 0:
                self.state = "move"
                game.audio.play("boss_appear")
            return

        if self.state == "move":
            self.side = facing_side
            speed = self.speed * (1.3 if self.phase == 3 else 1.0)
            if dist > 34:
                self.chase(dt, game, obstacles, speed=speed)
            if dist < 52 and self.cooldown <= 0:
                self.state, self.timer = "slash_windup", 0.45
            elif self.phase >= 2 and dist > 90 and self.dash_cooldown <= 0:
                self.state, self.timer = "dash_windup", 0.6
                self.dir = Vector(to_player)
            elif self.phase == 3 and self.summon_cooldown <= 0:
                self.summon_cooldown = 9.0
                game.summon(["ninja", "bat", "bat"], self.pos)
            elif self.phase == 3 and self.burst_cooldown <= 0:
                self.burst_cooldown = 5.0
                self.burst(game, 12)
        elif self.state == "slash_windup":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer, self.slash_hit = "slash", 0.36, False
                game.audio.play("boss_slash")
        elif self.state == "slash":
            self.timer -= dt
            if not self.slash_hit and self.timer < 0.28 and self.slash_box().colliderect(player.hitbox):
                self.slash_hit = game.damage_player(3, self.pos)
            if self.timer <= 0:
                self.state, self.cooldown = "move", 1.3 if self.phase < 3 else 0.9
        elif self.state == "dash_windup":
            self.timer -= dt
            self.side = "right" if self.dir.x >= 0 else "left"
            if self.timer <= 0:
                self.state, self.timer = "dash", 0.55
                game.audio.play("boss_stomp")
        elif self.state == "dash":
            self.timer -= dt
            before = Vector(self.pos)
            self.move(self.dir * 260 * dt, obstacles)
            if self.timer <= 0 or self.pos.distance_squared_to(before) < 0.5:
                self.state, self.dash_cooldown = "move", 4.5 if self.phase == 2 else 3.2
                game.shake.add(3)
                self.burst(game, 8)

    def animate(self, dt):
        self.anim += dt
        if self.state == "spawn":
            self.image = assets.white(self.frames["idle"][0]) if int(self.timer * 10) % 2 else self.frames["idle"][0]
            self.rect = self.image.get_rect(midbottom=(self.hitbox.centerx, self.hitbox.bottom + 4))
            return
        if self.state == "roar":
            frames = self.frames["hit"]
        elif self.state in ("slash_windup", "dash_windup"):
            frames = self.frames[f"charge_{self.side}"]
            image = frames[min(len(frames) - 1, int(self.anim * 9) % len(frames))]
            self.place_image(image, FEET["charge"])
            if self.state == "dash_windup" and int(self.timer * 20) % 2:
                self.image = assets.white(image)
            return
        elif self.state == "slash":
            frames = self.frames[f"attack_{self.side}"]
            image = frames[min(len(frames) - 1, int((0.36 - self.timer) / 0.36 * len(frames)))]
            self.place_image(image, FEET["attack"])
            return
        elif self.state == "dash":
            frames = self.frames["walk"]
        else:
            frames = self.frames["walk"] if self.dir.length_squared() else self.frames["idle"]
        speed = 18 if self.state == "dash" else 9
        image = frames[int(self.anim * speed) % len(frames)]
        self.place_image(image, 4)
