"""Арена: пол, деревья, камни, точки появления врагов."""

import random

import pygame

from . import assets
from .settings import TILE

COLS, ROWS = 52, 34
SEED = 2022  # раскладка камней и кустов одна и та же в каждой партии

GROVES = [(9, 7), (11, 8), (40, 6), (42, 7), (8, 25), (10, 26), (41, 24), (39, 25), (25, 5), (26, 27)]
STUMPS = [(17, 12), (34, 12), (17, 22), (34, 22), (25, 16), (21, 9), (30, 25)]


class Prop(pygame.sprite.Sprite):
    """Дерево или камень: рисуется с сортировкой по глубине и мешает проходу."""

    def __init__(self, image, topleft, hitbox, breakable=False):
        super().__init__()
        self.image = image
        self.rect = image.get_rect(topleft=topleft)
        self.hitbox = hitbox
        self.breakable = breakable
        self.sort_y = self.hitbox.bottom


class World:
    def __init__(self):
        self.width, self.height = COLS * TILE, ROWS * TILE
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.props = pygame.sprite.Group()
        edge = 2 * TILE  # толщина кольца деревьев
        self.walls = [pygame.Rect(0, 0, self.width, edge), pygame.Rect(0, self.height - edge, self.width, edge),
                      pygame.Rect(0, 0, edge, self.height), pygame.Rect(self.width - edge, 0, edge, self.height)]
        self.inner = pygame.Rect(2 * TILE, 2 * TILE, self.width - 4 * TILE, self.height - 4 * TILE)
        self.center = pygame.Vector2(self.width / 2, self.height / 2 + TILE)
        self.floor = pygame.Surface((self.width, self.height)).convert()
        self._build()

    def _build(self):
        rnd = random.Random(SEED)
        grass = assets.tile("floor.png", 0, 12)
        decor = [assets.tile("floor.png", c, r) for c, r in ((1, 12), (2, 12), (3, 12), (4, 12), (3, 11))]
        bushes = [assets.tile("nature.png", c, 10) for c in range(4)]
        trees = [assets.tile("nature.png", 0, 0, 2, 2), assets.tile("nature.png", 16, 0, 2, 2),
                 assets.tile("nature.png", 18, 0, 2, 2)]
        rock = assets.tile("nature.png", 7, 12)
        stump = assets.tile("nature.png", 15, 9)

        for y in range(ROWS):
            for x in range(COLS):
                self.floor.blit(grass, (x * TILE, y * TILE))
                if rnd.random() < 0.13:
                    self.floor.blit(rnd.choice(decor), (x * TILE, y * TILE))

        taken = set()

        def tree(cx, cy):
            for dx in (0, 1):
                for dy in (0, 1):
                    taken.add((cx + dx, cy + dy))
            px, py = cx * TILE, cy * TILE
            self.props.add(Prop(rnd.choice(trees), (px, py), pygame.Rect(px + 8, py + 20, 16, 10)))

        # Кольцо деревьев по краю: стена — отдельные прямоугольники self.walls.
        for x in range(0, COLS, 2):
            tree(x, 0)
            tree(x, ROWS - 2)
        for y in range(2, ROWS - 2, 2):
            tree(0, y)
            tree(COLS - 2, y)
        for cx, cy in GROVES:
            tree(cx, cy)

        def free(x, y):
            near_center = abs(x - COLS / 2) < 6 and abs(y - ROWS / 2) < 5
            return (x, y) not in taken and not near_center and 3 <= x < COLS - 3 and 3 <= y < ROWS - 3

        for x, y in STUMPS:
            taken.add((x, y))
            px, py = x * TILE, y * TILE
            self.props.add(Prop(stump, (px, py), pygame.Rect(px + 2, py + 5, 12, 10)))

        placed = 0
        while placed < 26:
            x, y = rnd.randrange(3, COLS - 3), rnd.randrange(3, ROWS - 3)
            if free(x, y):
                taken.add((x, y))
                px, py = x * TILE, y * TILE
                self.props.add(Prop(rock, (px, py), pygame.Rect(px + 2, py + 4, 12, 11), breakable=True))
                placed += 1

        for _ in range(40):
            x, y = rnd.randrange(2, COLS - 2), rnd.randrange(2, ROWS - 2)
            if (x, y) not in taken:
                self.floor.blit(rnd.choice(bushes), (x * TILE, y * TILE))

        self.spawns = []
        for x in range(4, COLS - 4, 5):
            self.spawns += [pygame.Vector2(x * TILE + 8, 3 * TILE), pygame.Vector2(x * TILE + 8, (ROWS - 3) * TILE)]
        for y in range(6, ROWS - 5, 5):
            self.spawns += [pygame.Vector2(3 * TILE, y * TILE + 8), pygame.Vector2((COLS - 3) * TILE, y * TILE + 8)]
        self.spawns = [p for p in self.spawns if not self.blocked(pygame.Rect(p.x - 8, p.y - 6, 16, 12))]

    def obstacles(self):
        return self.walls + [p.hitbox for p in self.props]

    def blocked(self, rect):
        return rect.collidelist(self.walls) != -1 or any(rect.colliderect(p.hitbox) for p in self.props)
