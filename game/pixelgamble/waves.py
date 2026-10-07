"""Состав волн и очередь появления врагов."""

import random

from .settings import MAX_ALIVE, SPAWN_SAFE_RADIUS

WAVES = [
    {"slime": 8},
    {"slime": 10, "bat": 5},
    {"slime": 8, "ninja": 6},
    {"bat": 8, "ninja": 7, "skeleton": 3},
    {"slime": 10, "ninja": 6, "skeleton": 5, "cyclop": 1},
    {"bat": 10, "ninja": 9, "skeleton": 6},
    {"slime": 14, "bat": 8, "skeleton": 5, "cyclop": 2},
    {"ninja": 12, "skeleton": 8, "bat": 8, "cyclop": 1},
    {"slime": 10, "bat": 8, "ninja": 12, "skeleton": 8, "cyclop": 3},
    {"boss": 1},
]


def hp_multiplier(wave):
    return 1 + 0.08 * (wave - 1)


class Spawner:
    def __init__(self, wave, rng=random):
        self.wave = wave
        plan = []
        for kind, count in WAVES[wave - 1].items():
            plan += [kind] * count
        rng.shuffle(plan)
        # тяжёлые враги — во второй половине волны, чтобы начало было разогревом
        plan.sort(key=lambda k: k == "cyclop")
        self.queue = plan
        self.total = len(plan)
        self.timer = 0.6
        self.rng = rng

    def done(self):
        return not self.queue

    def update(self, dt, alive, player_pos, spawn_points):
        """Возвращает список (вид, точка) для появления в этом кадре."""
        self.timer -= dt
        out = []
        if self.queue and self.timer <= 0 and alive < MAX_ALIVE:
            self.timer = max(0.35, 1.3 - 0.08 * self.wave) * self.rng.uniform(0.7, 1.3)
            far = [p for p in spawn_points if p.distance_to(player_pos) > SPAWN_SAFE_RADIUS] or spawn_points
            group = 1 if self.queue[0] in ("cyclop", "boss") else min(len(self.queue), self.rng.choice((1, 1, 2, 3)))
            point = self.rng.choice(far)
            for _ in range(group):
                out.append((self.queue.pop(0), point + (self.rng.uniform(-10, 10), self.rng.uniform(-10, 10))))
        return out
