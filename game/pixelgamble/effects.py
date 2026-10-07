"""Анимации-эффекты, снаряды, подбираемые сердечки, всплывающие надписи."""

import math
import random

import pygame

from . import assets, ui
from .entity import Vector


class Effect(pygame.sprite.Sprite):
    """Проигрывается один раз и исчезает."""

    def __init__(self, frames, pos, fps=16, sort_y=None, anchor="center"):
        super().__init__()
        self.frames, self.fps, self.t = frames, fps, 0.0
        self.pos, self.anchor = Vector(pos), anchor
        self.sort_y = sort_y if sort_y is not None else pos[1]
        self.image = frames[0]
        self.rect = self.image.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})

    def update(self, dt):
        self.t += dt
        i = int(self.t * self.fps)
        if i >= len(self.frames):
            self.kill()
            return
        self.image = self.frames[i]
        self.rect = self.image.get_rect(**{self.anchor: (round(self.pos.x), round(self.pos.y))})


class Particle(pygame.sprite.Sprite):
    def __init__(self, image, pos, velocity, life=0.5):
        super().__init__()
        self.image, self.pos, self.vel, self.life = image, Vector(pos), Vector(velocity), life
        self.rect = image.get_rect(center=pos)
        self.sort_y = pos[1] + 4

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.pos += self.vel * dt
        self.vel *= max(0.0, 1 - 4 * dt)
        self.vel.y += 120 * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))


class Projectile(pygame.sprite.Sprite):
    def __init__(self, frames, pos, velocity, damage, owner, life=1.2, knock=60, radius=4, spin=False):
        super().__init__()
        self.frames, self.pos, self.vel = frames, Vector(pos), Vector(velocity)
        self.damage, self.owner, self.life, self.knock = damage, owner, life, knock
        self.radius, self.spin = radius, spin
        self.t = 0.0
        self.hit = set()
        if not spin:  # спрайт снаряда нарисован летящим вниз — поворачиваем один раз
            angle = -math.degrees(math.atan2(self.vel.y, self.vel.x)) + 90
            self.frames = [pygame.transform.rotate(f, angle) for f in frames]
        self._frame()

    @property
    def sort_y(self):
        return self.pos.y + 6

    def hitbox(self):
        r = self.radius
        return pygame.Rect(round(self.pos.x) - r, round(self.pos.y) - r, r * 2, r * 2)

    def _frame(self):
        self.image = self.frames[int(self.t * 12) % len(self.frames)]
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self, dt):
        self.t += dt
        self.life -= dt
        self.pos += self.vel * dt
        if self.life <= 0:
            self.kill()
            return
        self._frame()


class Heart(pygame.sprite.Sprite):
    """Сердечко: лечит на одно сердце, притягивается к игроку вблизи."""

    LIFETIME = 14.0

    def __init__(self, pos):
        super().__init__()
        self.base = assets.image("items/heart.png")
        self.pos = Vector(pos)
        self.t = random.random() * 3
        self.life = self.LIFETIME
        self.image = self.base
        self.rect = self.image.get_rect(center=pos)

    @property
    def sort_y(self):
        return self.pos.y + 4

    def update(self, dt, player):
        self.t += dt
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        delta = player.pos - self.pos
        if delta.length_squared() < 36 ** 2 and delta.length_squared() > 0:
            self.pos += delta.normalize() * 140 * dt
        bob = math.sin(self.t * 5) * 2
        self.image = self.base
        if self.life < 3 and int(self.life * 8) % 2:
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y + bob)))


class FloatText(pygame.sprite.Sprite):
    """Всплывающая надпись: позиция в мире, рисуется на слое интерфейса."""

    def __init__(self, text, pos, color, size=20, life=0.8):
        super().__init__()
        self.image = ui.outlined(text, size, color).copy()
        self.pos, self.life, self.total = Vector(pos), life, life

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.pos.y -= 22 * dt
        self.image.set_alpha(int(255 * min(1.0, self.life / (self.total * 0.5))))


class Shake:
    def __init__(self):
        self.power = 0.0

    def add(self, power):
        self.power = max(self.power, power)

    def offset(self, dt):
        self.power = max(0.0, self.power - dt * 18)
        if self.power <= 0:
            return Vector()
        return Vector(random.uniform(-1, 1), random.uniform(-1, 1)) * self.power
