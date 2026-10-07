"""Партия: волны, бой, улучшения между волнами, камера и интерфейс."""

import math
import random

import pygame

from . import assets, enemies, ui, upgrades
from .boss import Boss
from .effects import Effect, FloatText, Heart, Particle, Projectile, Shake
from .entity import Vector
from .player import WEAPONS, Player
from .settings import (
    BLUE,
    GOLD,
    GREEN,
    GREY,
    HEART_DROP_CHANCE,
    HEIGHT,
    RED,
    SCALE,
    SCREEN_H,
    SCREEN_W,
    WAVE_BREAK,
    WAVES_TOTAL,
    WHITE,
    WIDTH,
    XP_BASE,
    XP_STEP,
)
from .waves import Spawner, hp_multiplier
from .world import World

# поворот спрайта взмаха (нарисован для удара вниз) под направление удара
ARC_ANGLES = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): -90}


def xp_needed(level):
    return XP_BASE + XP_STEP * (level - 1)


class Game:
    def __init__(self, app, start_wave=1, rng=None):
        self.app, self.audio, self.lang = app, app.audio, app.lang
        self.rng = rng or random.Random()
        self.world = World()
        self.walls = self.world.walls
        self.obstacles = self.world.obstacles()
        self.player = Player(self.world.center)
        self.enemies = pygame.sprite.Group()
        self.shots = pygame.sprite.Group()        # снаряды игрока
        self.enemy_shots = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.hearts = pygame.sprite.Group()
        self.texts = pygame.sprite.Group()
        self.shake = Shake()
        self.camera = Vector(self.player.pos) - Vector(WIDTH / 2, HEIGHT / 2)
        self.clamp_camera()
        self.drawn_offset = (0, 0)

        self.wave = start_wave
        self.taken = {}
        self.kills = 0
        self.score = 0
        self.log = []        # (волна, секунд на волну, здоровье в конце) — для проверок баланса
        self.time = 0.0
        self.wave_time = 0.0
        self.boss = None
        self.result = None   # "dead" / "victory" — когда партия закончилась
        self.end_timer = 0.0
        self.offer = []
        self.card = 0
        self.paused = False
        self.pause_menu = ui.Menu([("resume", self.lang("resume")), ("to_menu", self.lang("to_menu"))],
                                  (SCREEN_W // 2, 300))

        self.smoke = assets.strip("fx/smoke.png", 32)
        self.arc = assets.strip("fx/arc.png", 38)
        self.ball = assets.strip("fx/energy_ball.png", 16)
        self.shuriken = assets.strip("fx/shuriken.png", 16)
        self.rock_bits = assets.strip("fx/rock.png", 16)
        self.shadow = assets.image("chars/shadow.png").copy()
        self.shadow.set_alpha(120)
        self.big_shadow = pygame.transform.scale_by(self.shadow, 2)
        self.big_shadow.set_alpha(120)
        self.start_wave()

    # ------------------------------------------------------------------ волны
    def start_wave(self):
        self.state, self.timer = "intro", 1.8
        self.spawner = Spawner(self.wave, self.rng)
        self.wave_time = 0.0
        self.audio.music("boss" if self.wave == WAVES_TOTAL else "battle")
        self.audio.play("boss_appear" if self.wave == WAVES_TOTAL else "wave_start")

    def finish_wave(self):
        self.log.append((self.wave, round(self.wave_time, 1), self.player.hp))
        bonus = 100 * self.wave + max(0, int(90 - self.wave_time)) * 3
        self.score += bonus
        self.texts.add(FloatText(f"+{bonus}", self.player.pos + (0, -30), GOLD, 20, 1.4))
        if self.wave == WAVES_TOTAL:
            self.end("victory")
            return
        self.state, self.timer = "clear", WAVE_BREAK
        self.audio.play("wave_clear")

    def open_upgrades(self):
        self.offer = upgrades.offer(self.player, self.taken, self.wave + 1, self.rng)
        self.card = 0
        self.state = "upgrade" if self.offer else "next"

    def choose(self, index):
        if 0 <= index < len(self.offer):
            upgrades.apply(self.offer[index], self.player, self.taken)
            self.audio.play("power_up")
            self.wave += 1
            self.start_wave()

    def end(self, result):
        if self.result:
            return
        self.result = result
        self.end_timer = 2.0
        if result == "victory":
            self.score += 2000 + self.player.hp * 50
            self.audio.play("victory")
        else:
            self.audio.play("game_over")
            self.effects.add(Effect(self.smoke, self.player.pos + (0, -6), 12))
        self.audio.fadeout(1500)

    # ------------------------------------------------------------ для врагов
    def damage_player(self, amount, source_pos):
        if self.result:
            return False
        if self.player.hurt(amount, source_pos):
            self.audio.play("player_hurt")
            self.shake.add(3)
            if self.player.dead:
                self.end("dead")
            return True
        return False

    def enemy_shot(self, pos, velocity, damage):
        self.enemy_shots.add(Projectile(self.shuriken, pos, velocity, damage, "enemy", life=2.6, radius=3, spin=True))
        self.audio.play("enemy_shoot")

    def summon(self, kinds, near):
        for kind in kinds:
            angle = self.rng.random() * math.tau
            pos = Vector(near) + Vector(math.cos(angle), math.sin(angle)) * 40
            pos.x = min(max(pos.x, self.world.inner.left + 8), self.world.inner.right - 8)
            pos.y = min(max(pos.y, self.world.inner.top + 8), self.world.inner.bottom - 8)
            self.add_enemy(kind, pos)

    def add_enemy(self, kind, pos):
        if kind == "boss":
            enemy = Boss(pos)
            self.boss = enemy
        else:
            enemy = enemies.make(kind, pos, hp_multiplier(self.wave))
        self.enemies.add(enemy)
        self.effects.add(Effect(self.smoke, (pos[0], pos[1] - 4), 10))

    # ------------------------------------------------------------- события
    def handle(self, event):
        if self.paused:
            choice = self.pause_menu.handle(event, self.audio)
            if choice == "resume" or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p)):
                self.paused = False
            elif choice == "to_menu":
                self.app.to_menu()
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p) and not self.result:
                self.paused = True
                self.pause_menu.index = 0
                self.audio.play("menu_back")
            elif self.state == "upgrade":
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3):
                    self.choose({pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_KP1: 0,
                                 pygame.K_KP2: 1, pygame.K_KP3: 2}[event.key])
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.card = (self.card - 1) % len(self.offer)
                    self.audio.play("menu_move")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.card = (self.card + 1) % len(self.offer)
                    self.audio.play("menu_move")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self.choose(self.card)
            elif event.key in (pygame.K_q, pygame.K_TAB):
                if self.player.switch(1):
                    self.audio.play("switch")
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                if self.player.switch(index=event.key - pygame.K_1):
                    self.audio.play("switch")
        elif event.type == pygame.MOUSEWHEEL and self.state != "upgrade":
            if self.player.switch(-1 if event.y > 0 else 1):
                self.audio.play("switch")
        elif self.state == "upgrade" and event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(ui.card_rects(len(self.offer))):
                if rect.collidepoint(event.pos):
                    self.card = i
        elif self.state == "upgrade" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(ui.card_rects(len(self.offer))):
                if rect.collidepoint(event.pos):
                    self.choose(i)

    def read_controls(self):
        """Движение и атака с клавиатуры/мыши (бот подменяет этот метод)."""
        keys = pygame.key.get_pressed()
        move = Vector((keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
                      (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]))
        mouse = pygame.mouse.get_pressed()[0] and pygame.mouse.get_focused()
        attack = mouse or keys[pygame.K_SPACE] or keys[pygame.K_j]
        target = Vector(pygame.mouse.get_pos()) / SCALE + self.camera if mouse else None
        return move, attack, target

    # ------------------------------------------------------------- кадр
    def update(self, dt, controls=None):
        if self.paused:
            return
        if self.result:
            self.end_timer -= dt
            dt *= 0.35  # замедление в конце партии
            if self.end_timer <= 0:
                self.app.show_results(self)
                return
        self.time += dt
        self.wave_time += dt

        move, attack, target = controls or self.read_controls()
        busy = self.state == "upgrade" or self.result
        if busy:
            move, attack = Vector(), False
        self.player.update(dt, move, self.obstacles)
        if attack:
            self.attack(target)

        if self.state == "intro":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "fight"
        elif self.state == "fight":
            alive = sum(1 for e in self.enemies if not e.boss)
            for kind, pos in self.spawner.update(dt, alive, self.player.pos, self.world.spawns):
                self.add_enemy(kind, pos)
            if self.spawner.done() and not self.enemies and not self.result:
                self.finish_wave()
        elif self.state == "clear":
            self.timer -= dt
            if self.timer <= 0:
                self.open_upgrades()
        elif self.state == "next":
            self.wave += 1
            self.start_wave()

        for enemy in list(self.enemies):
            enemy.update(dt, self)
        self.separate()
        for actor in [self.player, *self.enemies]:
            actor.keep_inside(self.world.inner)
        self.contact_damage()
        self.update_shots(dt)
        self.effects.update(dt)
        self.texts.update(dt)
        for heart in list(self.hearts):
            heart.update(dt, self.player)
            if heart.alive() and heart.rect.colliderect(self.player.hitbox.inflate(6, 10)):
                if self.player.heal(4):  # при полном здоровье сердечко остаётся лежать
                    self.audio.play("heal")
                    heart.kill()
        self.follow(dt)

    def attack(self, target):
        direction = self.player.try_attack(target)
        if direction is None:
            return
        player = self.player
        weapon = WEAPONS[player.weapon]
        self.audio.play(player.weapon)
        if weapon["kind"] == "bolt":
            spread = (-14, 0, 14) if player.multishot else (0,)
            for angle in spread:
                vel = direction.rotate(angle) * weapon["speed"]
                start = player.pos + Vector(0, -6) + direction * 6
                damage = player.damage() * (1.0 if angle == 0 else 0.6)  # боковые заряды слабее
                self.shots.add(Projectile(self.ball, start, vel, damage, "player", weapon["life"],
                                          weapon["knock"] * player.knock_mult))
            return
        box = player.melee_box(direction)
        self.melee_effect(direction, box, weapon["kind"])
        for enemy in list(self.enemies):
            body = enemy.hitbox.inflate(6, 12).move(0, -5)
            if box.colliderect(body) and enemy.hurt(player.damage(), player.pos, weapon["knock"] * player.knock_mult):
                self.on_enemy_hit(enemy)
        for prop in list(self.world.props):
            if prop.breakable and box.colliderect(prop.hitbox):
                self.break_rock(prop)

    def melee_effect(self, direction, box, kind):
        if kind == "arc":
            angle = ARC_ANGLES[(round(direction.x), round(direction.y))]
            frames = [pygame.transform.rotate(f, angle) for f in self.arc]
            self.effects.add(Effect(frames, box.center, 34, sort_y=box.centery + 10))
        else:
            image = assets.image("items/lance_hand.png")
            angle = -math.degrees(math.atan2(direction.y, direction.x)) - 90
            spear = pygame.transform.rotate(pygame.transform.flip(image, False, True), angle)
            hand = self.player.pos + Vector(0, -5)
            effect = Effect([spear] * 5, hand + direction * 16, 30, sort_y=self.player.sort_y + 1)
            effect.thrust = (Vector(hand), direction)
            self.effects.add(effect)
            quarter = ARC_ANGLES[(round(direction.x), round(direction.y))]
            tip = [pygame.transform.rotate(f, quarter) for f in self.arc[2:]]
            self.effects.add(Effect(tip, box.center + direction * 6, 40, sort_y=box.centery + 10))

    def on_enemy_hit(self, enemy):
        self.audio.play("enemy_hit")
        if enemy.hp <= 0:
            self.kill_enemy(enemy)

    def kill_enemy(self, enemy):
        enemy.kill()
        self.kills += 1
        self.score += enemy.score
        self.effects.add(Effect(self.smoke, enemy.hitbox.center, 14))
        self.audio.play("enemy_die")
        if enemy.boss:
            self.boss = None
            self.shake.add(5)
            for other in list(self.enemies):
                other.kill()
                self.effects.add(Effect(self.smoke, other.hitbox.center, 14))
            return
        levels = self.player.gain_xp(enemy.xp, xp_needed)
        if levels:
            self.player.damage_mult *= 1.02 ** levels
            self.player.heal(3 * levels)
            self.audio.play("level_up")
            self.texts.add(FloatText(self.lang("level_up"), self.player.pos + (0, -24), GOLD, 20, 1.2))
        if self.player.vampire and self.rng.random() < self.player.vampire:
            if self.player.heal(1):
                self.texts.add(FloatText("+", self.player.pos + (0, -18), GREEN))
        chance = 0.5 if enemy.kind == "cyclop" else HEART_DROP_CHANCE
        if self.rng.random() < chance:
            self.hearts.add(Heart(enemy.pos))

    def break_rock(self, prop):
        prop.kill()
        self.obstacles = self.world.obstacles()
        self.audio.play("rock_break")
        self.score += 5
        for _ in range(6):
            angle = self.rng.random() * math.tau
            self.effects.add(Particle(self.rng.choice(self.rock_bits), prop.hitbox.center,
                                      Vector(math.cos(angle), math.sin(angle) - 0.8) * self.rng.uniform(30, 70)))
        if self.rng.random() < 0.2:
            self.hearts.add(Heart(prop.hitbox.center))

    def separate(self):
        """Враги не слипаются в одну точку."""
        crowd = [e for e in self.enemies if e.active and not e.boss]
        for i, a in enumerate(crowd):
            for b in crowd[i + 1:]:
                delta = a.pos - b.pos
                dist2 = delta.length_squared()
                if 0 < dist2 < 144:
                    push = delta.normalize() * (12 - math.sqrt(dist2)) * 0.5
                    a.move(push, self.walls if a.flying else self.obstacles)
                    b.move(-push, self.walls if b.flying else self.obstacles)

    def contact_damage(self):
        player = self.player
        for enemy in self.enemies:
            if enemy.active and enemy.hitbox.colliderect(player.hitbox.inflate(2, 2)):
                damage = enemy.contact
                if getattr(enemy, "state", "") in ("charge", "dash"):
                    damage += 1
                self.damage_player(damage, enemy.pos)

    def update_shots(self, dt):
        self.shots.update(dt)
        self.enemy_shots.update(dt)
        for shot in list(self.shots):
            box = shot.hitbox()
            for enemy in self.enemies:
                if enemy.active and box.colliderect(enemy.hitbox.inflate(6, 12).move(0, -5)):
                    if enemy.hurt(shot.damage, shot.pos - shot.vel.normalize() * 8, shot.knock):
                        self.on_enemy_hit(enemy)
                    shot.kill()
                    break
            if not shot.alive():
                continue
            if box.collidelist(self.walls) != -1:
                shot.kill()
                continue
            for prop in self.world.props:
                if box.colliderect(prop.hitbox):
                    if prop.breakable:
                        self.break_rock(prop)
                    shot.kill()
                    break
        for shot in list(self.enemy_shots):
            box = shot.hitbox()
            if box.colliderect(self.player.hitbox.inflate(2, 6)):
                self.damage_player(shot.damage, shot.pos)
                shot.kill()
            elif box.collidelist(self.obstacles) != -1:
                shot.kill()

    # ------------------------------------------------------------- камера
    def clamp_camera(self):
        self.camera.x = min(max(self.camera.x, 0), self.world.width - WIDTH)
        self.camera.y = min(max(self.camera.y, 0), self.world.height - HEIGHT)

    def follow(self, dt):
        goal = self.player.pos - Vector(WIDTH / 2, HEIGHT / 2)
        self.camera += (goal - self.camera) * min(1.0, dt * 8)
        self.clamp_camera()

    # ------------------------------------------------------------- рисование
    def draw_world(self, view, dt):
        shake = self.shake.offset(dt)
        ox, oy = round(self.camera.x - shake.x), round(self.camera.y - shake.y)
        self.drawn_offset = (ox, oy)
        view.blit(self.world.floor, (-ox, -oy))
        area = pygame.Rect(ox - 48, oy - 48, WIDTH + 96, HEIGHT + 96)

        actors = [e for e in self.enemies if e.active]
        if not self.player.dead:
            actors.append(self.player)
        for actor in actors:
            shadow = self.big_shadow if actor.heavy else self.shadow
            view.blit(shadow, shadow.get_rect(center=(actor.hitbox.centerx - ox, actor.hitbox.bottom - oy)))

        drawables = [p for p in self.world.props if area.colliderect(p.rect)]
        drawables += [e for e in self.enemies if area.colliderect(e.rect)]
        drawables += list(self.hearts) + list(self.shots) + list(self.enemy_shots) + list(self.effects)
        if not self.player.dead:
            drawables.append(self.player)
        for sprite in sorted(drawables, key=lambda s: s.sort_y):
            thrust = getattr(sprite, "thrust", None)
            if thrust:  # копьё выдвигается вперёд за время удара
                base, direction = thrust
                pos = base + direction * (8 + 18 * min(1.0, sprite.t * 10))
                rect = sprite.image.get_rect(center=(round(pos.x), round(pos.y)))
                view.blit(sprite.image, rect.move(-ox, -oy))
            else:
                view.blit(sprite.image, sprite.rect.move(-ox, -oy))

    def draw_ui(self, screen):
        lang, player = self.lang, self.player
        ox, oy = self.drawn_offset
        for sprite in self.texts:
            pos = ((sprite.pos.x - ox) * SCALE, (sprite.pos.y - oy) * SCALE)
            screen.blit(sprite.image, sprite.image.get_rect(center=(round(pos[0]), round(pos[1]))))

        ui.hearts(screen, player, (12, 10))
        ui.text(screen, lang("level", n=player.level), (12, 46), ui.SMALL, GOLD)
        ui.bar(screen, (80, 52, 128, 12), player.xp / xp_needed(player.level), BLUE)
        ui.weapon_slots(screen, player, (12, SCREEN_H - 66))
        if len(player.weapons) > 1:
            ui.text(screen, "Q", (12 + len(player.weapons) * 44 + 4, SCREEN_H - 40), ui.SMALL, GREY)

        ui.text(screen, lang("wave", n=self.wave, total=WAVES_TOTAL), (SCREEN_W // 2, 10), ui.SMALL, WHITE, "midtop")
        if self.state == "fight" and not self.boss:
            left = len(self.spawner.queue) + len(self.enemies)
            ui.text(screen, lang("enemies_left", n=left), (SCREEN_W // 2, 34), ui.SMALL, GREY, "midtop")
        ui.text(screen, f"{self.score:,}".replace(",", " "), (SCREEN_W - 12, 10), ui.SMALL, GOLD, "topright")

        if self.boss and self.boss.alive():
            rect = pygame.Rect(SCREEN_W // 2 - 220, SCREEN_H - 40, 440, 18)
            ui.bar(screen, rect, max(0.0, self.boss.hp / self.boss.max_hp), RED)
            ui.text(screen, lang("boss_name"), (SCREEN_W // 2, rect.top - 4), ui.SMALL, WHITE, "midbottom")
            face = ui.big(assets.image("chars/boss_face.png"))
            screen.blit(face, face.get_rect(midright=(rect.left - 8, rect.centery - 12)))

        middle = (SCREEN_W // 2, SCREEN_H // 2 - 60)
        if self.state == "intro":
            label = lang("boss_wave") if self.wave == WAVES_TOTAL else lang("wave_big", n=self.wave)
            ui.text(screen, label, middle, ui.HUGE, GOLD, "center")
        elif self.state == "clear":
            ui.text(screen, lang("wave_clear"), middle, ui.LARGE, GREEN, "center")
        elif self.state == "upgrade":
            ui.dim(screen, 140)
            ui.text(screen, lang("choose"), (SCREEN_W // 2, 80), ui.LARGE, GOLD, "center")
            ui.cards(screen, self.offer, lang, self.card)
            ui.text(screen, lang("choose_hint"), (SCREEN_W // 2, SCREEN_H - 52), ui.SMALL, GREY, "center")
        if self.result:
            label = lang("victory") if self.result == "victory" else lang("game_over")
            ui.text(screen, label, middle, ui.HUGE, GOLD if self.result == "victory" else RED, "center")
        if self.paused:
            ui.dim(screen, 150)
            ui.text(screen, lang("pause"), (SCREEN_W // 2, 200), ui.LARGE, WHITE, "center")
            self.pause_menu.draw(screen)
