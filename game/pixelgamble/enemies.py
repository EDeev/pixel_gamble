"""Враги: слайм, летучая мышь, ниндзя, скелет-метатель, демон-циклоп."""

import math
import random

from . import assets
from .entity import Entity, Vector, direction_name

KINDS = {
    "slime": {"hp": 22, "speed": 34, "contact": 1, "xp": 3, "score": 30, "hit": (12, 8)},
    "bat": {"hp": 12, "speed": 80, "contact": 1, "xp": 3, "score": 35, "hit": (10, 8)},
    "ninja": {"hp": 38, "speed": 54, "contact": 1, "xp": 6, "score": 60, "hit": (10, 8)},
    "skeleton": {"hp": 28, "speed": 42, "contact": 1, "xp": 7, "score": 70, "hit": (10, 8)},
    "cyclop": {"hp": 150, "speed": 27, "contact": 3, "xp": 22, "score": 250, "hit": (24, 12)},
}

SPAWN_TIME = 0.7


class Enemy(Entity):
    boss = False
    flying = False
    heavy = False

    def __init__(self, kind, pos, hp_mult=1.0):
        data = KINDS[kind]
        super().__init__(pos, *data["hit"])
        self.kind = kind
        self.max_hp = self.hp = data["hp"] * hp_mult
        self.speed = data["speed"] * random.uniform(0.9, 1.1)
        self.contact = data["contact"]
        self.xp, self.score = data["xp"], data["score"]
        self.state, self.timer = "spawn", SPAWN_TIME
        self.cooldown = random.uniform(0.5, 1.5)
        self.dir = Vector()
        self.load_frames()

    # --- общая часть ---
    @property
    def active(self):
        return self.state != "spawn"

    def load_frames(self):
        self.frames = assets.monster(f"{self.kind}.png")

    def hurt(self, amount, source_pos, knock):
        if not self.active:
            return False
        self.hp -= amount
        self.flash = 0.1
        away = self.pos - Vector(source_pos)
        if away.length_squared() > 0:
            self.knock = away.normalize() * knock * (0.25 if self.heavy else 1.0)
        return True

    def update(self, dt, game):
        self.flash = max(0.0, self.flash - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        obstacles = game.walls if self.flying else game.obstacles
        if self.state == "spawn":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "move"
        else:
            self.think(dt, game, obstacles)
        self.apply_knock(dt, obstacles)
        self.animate(dt)

    def chase(self, dt, game, obstacles, speed=None, direction=None):
        direction = direction if direction is not None else self.direction_to(game.player)
        if direction.length_squared():
            self.facing = direction_name(direction)
            self.steer(direction, (speed or self.speed) * dt, obstacles, dt)
        self.dir = direction

    def think(self, dt, game, obstacles):
        self.chase(dt, game, obstacles)

    def animate(self, dt):
        if self.state == "spawn":
            self.image = assets.image("chars/shadow.png") if self.timer < SPAWN_TIME * 0.6 else self.image
            self.rect = self.image.get_rect(center=self.hitbox.center)
            return
        self.anim = (self.anim + dt * 7) % 4
        self.place_image(self.frames[self.facing]["walk"][int(self.anim)], 3)


class Slime(Enemy):
    pass


class Bat(Enemy):
    """Летает зигзагом и не замечает камней."""

    flying = True

    def think(self, dt, game, obstacles):
        to_player = self.direction_to(game.player)
        side = Vector(-to_player.y, to_player.x) * math.sin(self.anim * 2.2 + id(self) % 7) * 0.9
        direction = to_player + side
        self.chase(dt, game, obstacles, direction=direction.normalize() if direction.length_squared() else to_player)


class Ninja(Enemy):
    """Подбегает, замахивается и делает быстрый выпад."""

    def load_frames(self):
        self.frames = assets.character("ninja.png")

    def think(self, dt, game, obstacles):
        player = game.player
        if self.state == "move":
            self.chase(dt, game, obstacles)
            if self.distance_to(player) < 30 and self.cooldown <= 0:
                self.state, self.timer = "windup", 0.4
                self.dir = self.direction_to(player)
                self.facing = direction_name(self.dir)
        elif self.state == "windup":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "strike", 0.16
                game.audio.play("sword")
        elif self.state == "strike":
            self.timer -= dt
            self.move(self.dir * 230 * dt, obstacles)
            if self.hitbox.inflate(6, 6).colliderect(player.hitbox):
                game.damage_player(2, self.pos)
            if self.timer <= 0:
                self.state, self.cooldown = "move", 1.1

    def animate(self, dt):
        if self.state in ("windup", "strike"):
            self.place_image(self.frames[self.facing]["attack"][0], 3)
            if self.state == "windup" and int(self.timer * 30) % 2:
                self.image = assets.white(self.image)
            return
        super().animate(dt)


class Skeleton(Enemy):
    """Держит дистанцию и метает сюрикены."""

    def load_frames(self):
        self.frames = assets.character("skeleton.png")

    def think(self, dt, game, obstacles):
        player = game.player
        dist = self.distance_to(player)
        to_player = self.direction_to(player)
        cornered = not game.world.inner.inflate(-56, -56).collidepoint(self.pos)
        if dist < 85 and not cornered:
            direction = -to_player
        elif dist < 85:  # у края арены не пятится, а уходит вбок к центру
            side = Vector(-to_player.y, to_player.x)
            if side.dot(game.world.center - self.pos) < 0:
                side = -side
            direction = side
        elif dist > 150:
            direction = to_player
        else:
            direction = Vector(-to_player.y, to_player.x) * (1 if id(self) % 2 else -1) * 0.6
        self.chase(dt, game, obstacles, direction=direction)
        self.facing = direction_name(to_player)
        if self.cooldown <= 0 and dist < 220:
            self.cooldown = random.uniform(2.0, 2.8)
            game.enemy_shot(self.pos + Vector(0, -6), to_player * 115, 1)


class Cyclop(Enemy):
    """Медленный и живучий: предупреждает и бросается тараном."""

    heavy = True

    def load_frames(self):
        walk = assets.strip("chars/cyclop_walk.png", 50)
        hit = assets.strip("chars/cyclop_hit.png", 50)
        self.frames = {"right": walk, "left": assets.flipped(walk), "hit": hit, "hit_left": assets.flipped(hit)}

    def think(self, dt, game, obstacles):
        player = game.player
        if self.state == "move":
            self.chase(dt, game, obstacles)
            if self.distance_to(player) < 120 and self.cooldown <= 0:
                self.state, self.timer = "windup", 0.65
                self.dir = self.direction_to(player)
        elif self.state == "windup":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = "charge", 0.7
                game.audio.play("boss_stomp")
                game.shake.add(2)
        elif self.state == "charge":
            self.timer -= dt
            before = Vector(self.pos)
            self.move(self.dir * 190 * dt, obstacles)
            stuck = self.pos.distance_squared_to(before) < 0.5
            if self.timer <= 0 or stuck:
                self.state, self.cooldown = "move", 2.4

    def animate(self, dt):
        if self.state == "spawn":
            return super().animate(dt)
        left = self.dir.x < 0
        if self.state == "windup":
            frames = self.frames["hit_left" if left else "hit"]
            image = frames[int(self.timer * 12) % len(frames)]
        else:
            self.anim = (self.anim + dt * (14 if self.state == "charge" else 7)) % 6
            image = self.frames["left" if left else "right"][int(self.anim)]
        self.place_image(image, 9)


CLASSES = {"slime": Slime, "bat": Bat, "ninja": Ninja, "skeleton": Skeleton, "cyclop": Cyclop}


def make(kind, pos, hp_mult=1.0):
    return CLASSES[kind](kind, pos, hp_mult)
