"""Константы игры: экран, мир, баланс."""

import sys
from pathlib import Path

WEB = sys.platform == "emscripten"
BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "assets"

# Мир рисуется в маленьком «пиксельном» разрешении и масштабируется в 2 раза,
# интерфейс — поверх, в разрешении экрана (так текст остаётся чётким).
WIDTH, HEIGHT = 480, 270
SCALE = 2
SCREEN_W, SCREEN_H = WIDTH * SCALE, HEIGHT * SCALE
FPS = 60
TILE = 16
TITLE = "Pixel Gamble"
VERSION = "2.0.0"

# Цвета интерфейса
WHITE = (255, 255, 255)
BLACK = (20, 16, 24)
GOLD = (255, 214, 92)
RED = (230, 72, 72)
GREEN = (120, 220, 110)
BLUE = (110, 180, 255)
GREY = (150, 150, 160)
PANEL = (44, 32, 40)
PANEL_LIGHT = (92, 64, 70)
PANEL_EDGE = (16, 10, 16)

# Игрок. Здоровье считается в четвертях сердечка, как в классических Zelda.
PLAYER_HEARTS = 3
PLAYER_MAX_HEARTS = 8
PLAYER_SPEED = 92
PLAYER_INVULNERABLE = 0.9

# Опыт до следующего уровня: XP_BASE + XP_STEP * (уровень - 1)
XP_BASE = 12
XP_STEP = 8

WAVES_TOTAL = 10
WAVE_BREAK = 2.5          # пауза перед выбором улучшения
SPAWN_SAFE_RADIUS = 110   # враги не появляются вплотную к игроку
MAX_ALIVE = 10            # одновременно живых врагов (кроме босса)
HEART_DROP_CHANCE = 0.07
