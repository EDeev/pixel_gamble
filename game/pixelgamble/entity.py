"""Базовая сущность: позиция, столкновения, отбрасывание, вспышка при попадании."""

import pygame

from . import assets

Vector = pygame.Vector2


def direction_name(vec):
    """Ближайшее из четырёх направлений спрайта."""
    if abs(vec.x) > abs(vec.y):
        return "right" if vec.x > 0 else "left"
    return "down" if vec.y >= 0 else "up"


DIR_VECTORS = {"down": Vector(0, 1), "up": Vector(0, -1), "left": Vector(-1, 0), "right": Vector(1, 0)}


class Entity(pygame.sprite.Sprite):
    def __init__(self, pos, hit_w, hit_h):
        super().__init__()
        self.pos = Vector(pos)
        self.hitbox = pygame.Rect(0, 0, hit_w, hit_h)
        self.hitbox.center = (round(self.pos.x), round(self.pos.y))
        self.knock = Vector()
        self.flash = 0.0
        self.facing = "down"
        self.anim = 0.0
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

    @property
    def sort_y(self):
        return self.hitbox.bottom

    def move(self, delta, obstacles):
        """Сдвиг с упором в препятствия: сначала по X, потом по Y."""
        for axis in (0, 1):
            if not delta[axis]:
                continue
            before = self.hitbox.copy()
            self.pos[axis] += delta[axis]
            self.hitbox.center = (round(self.pos.x), round(self.pos.y))
            hits = self.hitbox.collidelistall(obstacles)
            for i in hits:
                wall = obstacles[i]
                if before.colliderect(wall):
                    self.push_out(wall)  # уже стояли внутри — упор по направлению шага выкинул бы насквозь
                elif axis == 0:
                    if delta.x > 0:
                        self.hitbox.right = wall.left
                    else:
                        self.hitbox.left = wall.right
                elif delta.y > 0:
                    self.hitbox.bottom = wall.top
                else:
                    self.hitbox.top = wall.bottom
            if hits:  # дробную часть позиции сбрасываем только при упоре
                self.pos.update(self.hitbox.center)

    def steer(self, direction, distance, obstacles, dt):
        """Шаг с обходом препятствий: если прямо упёрлись — пробуем в обход и держим выбранную сторону."""
        self.detour_time = max(0.0, getattr(self, "detour_time", 0.0) - dt)
        if self.detour_time > 0:
            direction = direction.rotate(self.detour)
        start = Vector(self.pos)
        self.move(direction * distance, obstacles)
        if distance <= 0 or self.pos.distance_to(start) > distance * 0.4:
            return direction
        side = getattr(self, "detour_side", 1)
        for angle in (45 * side, -45 * side, 90 * side, -90 * side, 135 * side, -135 * side):
            self.pos.update(start)
            self.hitbox.center = (round(start.x), round(start.y))
            self.move(direction.rotate(angle) * distance, obstacles)
            if self.pos.distance_to(start) > distance * 0.4:
                self.detour, self.detour_time = angle, 0.6
                self.detour_side = 1 if angle > 0 else -1
                return direction.rotate(angle)
        return direction

    def push_out(self, wall):
        """Вытолкнуть из препятствия по кратчайшему пути."""
        box = self.hitbox
        shifts = [(wall.left - box.right, 0), (wall.right - box.left, 0),
                  (0, wall.top - box.bottom), (0, wall.bottom - box.top)]
        dx, dy = min(shifts, key=lambda s: abs(s[0]) + abs(s[1]))
        box.move_ip(dx, dy)

    def keep_inside(self, area):
        """Страховка: не выходить за пределы арены."""
        if not area.contains(self.hitbox):
            self.hitbox.clamp_ip(area)
            self.pos.update(self.hitbox.center)

    def apply_knock(self, dt, obstacles):
        if self.knock.length_squared() > 1:
            self.move(self.knock * dt, obstacles)
            self.knock *= max(0.0, 1 - 10 * dt)
        else:
            self.knock.update(0, 0)

    def place_image(self, image, offset_y=0):
        self.image = assets.white(image) if self.flash > 0 else image
        self.rect = self.image.get_rect(midbottom=(self.hitbox.centerx, self.hitbox.bottom + offset_y))

    def distance_to(self, other):
        return self.pos.distance_to(other.pos)

    def direction_to(self, other):
        delta = other.pos - self.pos
        return delta.normalize() if delta.length_squared() > 0 else Vector()
