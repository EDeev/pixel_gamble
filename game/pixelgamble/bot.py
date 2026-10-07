"""Автоигрок для проверок без окна (CI) и записи GIF: не идеален, но доходит далеко."""

import random

from .app import MenuScene, PlayScene, ResultsScene
from .entity import Vector
from .player import WEAPONS


class Bot:
    def __init__(self, seed=1, restart=False):
        self.rng = random.Random(seed)
        self.restart = restart
        self.finished = []      # итоги сыгранных партий
        self.stuck_time = 0.0
        self.escape = Vector()
        self.escape_time = 0.0
        self.last_pos = None
        self.last_foe, self.last_hp, self.no_progress = None, 0, 0.0

    def drive(self, app):
        scene = app.scene
        if isinstance(scene, MenuScene):
            app.new_game()
        elif isinstance(scene, ResultsScene):
            if not self.finished or self.finished[-1] is not scene:
                self.finished.append(scene)
                if self.restart:
                    app.new_game()
        elif isinstance(scene, PlayScene) and scene.game.state == "upgrade":
            scene.game.choose(self.pick(scene.game.offer))

    def pick(self, offer):
        order = ("wand", "heart", "damage", "haste", "heal", "lance", "multishot", "speed", "reach", "vampire",
                 "knockback")
        return min(range(len(offer)), key=lambda i: order.index(offer[i]))

    def controls(self, game, dt=1 / 60):
        player = game.player
        foes = [e for e in game.enemies if e.active]
        move = Vector()
        target = None

        # здоровье на исходе — к ближайшему сердечку
        if game.hearts and player.hp <= player.max_hp // 2:
            heart = min(game.hearts, key=lambda h: h.pos.distance_squared_to(player.pos))
            move = heart.pos - player.pos

        if foes:
            foe = min(foes, key=lambda e: e.pos.distance_squared_to(player.pos))
            delta = foe.pos - player.pos
            dist = delta.length()
            ranged = WEAPONS[player.weapon]["kind"] == "bolt"
            want = 70 if ranged else (20 if player.weapon == "sword" else 30)
            if not move:
                if dist > want + 6:
                    move = delta
                elif dist < want - 12 or foe.boss:
                    move = -delta + Vector(-delta.y, delta.x) * 0.8
            if dist < (130 if ranged else want + 14):
                target = foe.pos
            # стреляем, а урона нет (мешает камень) — подходим с другой стороны
            if target is not None and foe is self.last_foe and foe.hp >= self.last_hp:
                self.no_progress += dt
            else:
                self.no_progress = 0.0
            self.last_foe, self.last_hp = foe, foe.hp
            if self.no_progress > 2.5:
                move = Vector(delta).rotate(70 * getattr(self, "side", 1))
            if player.weapon != "wand" and "wand" in player.weapons and len(foes) > 3:
                player.switch(index=player.weapons.index("wand"))

        for shot in game.enemy_shots:
            to_me = player.pos - shot.pos
            if to_me.length_squared() < 40 ** 2 and shot.vel.dot(to_me) > 0:
                move = Vector(-shot.vel.y, shot.vel.x)
                break

        # упёрся в дерево или камень — обходим вбок, каждый раз с другой стороны
        if self.escape_time > 0:
            self.escape_time -= dt
            move = self.escape
        elif move and self.last_pos is not None and player.pos.distance_squared_to(self.last_pos) < 0.05:
            self.stuck_time += dt
            if self.stuck_time > 0.25:
                self.side = -getattr(self, "side", 1)
                self.escape = Vector(move).rotate(80 * self.side)
                self.escape_time, self.stuck_time = 0.6 + self.rng.random() * 0.4, 0.0
        else:
            self.stuck_time = 0.0
        self.last_pos = Vector(player.pos)
        return move, target is not None, target
