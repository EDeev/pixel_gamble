"""Загрузка и нарезка ресурсов: спрайты, звуки, музыка, шрифты."""

import pygame

from .settings import ASSETS, TILE

DIRECTIONS = ("down", "up", "left", "right")  # порядок столбцов в листах Ninja Adventure

_images = {}


def image(name):
    if name not in _images:
        _images[name] = pygame.image.load(str(ASSETS / "images" / name)).convert_alpha()
    return _images[name]


def strip(name, frame_w, frame_h=None):
    """Кадры, идущие в один ряд."""
    sheet = image(name)
    frame_h = frame_h or sheet.get_height()
    return [sheet.subsurface((x, 0, frame_w, frame_h)) for x in range(0, sheet.get_width() - frame_w + 1, frame_w)]


def grid(name, size=16):
    sheet = image(name)
    return [[sheet.subsurface((x, y, size, size)) for x in range(0, sheet.get_width(), size)]
            for y in range(0, sheet.get_height(), size)]


def character(name):
    """Лист персонажа 4×7: столбцы — направления, строки 0-3 — шаги, строка 4 — удар."""
    rows = grid(f"chars/{name}")
    return {d: {"walk": [rows[r][c] for r in range(4)], "attack": [rows[4][c]]}
            for c, d in enumerate(DIRECTIONS)}


def monster(name):
    """Лист монстра 4×4: столбцы — направления, строки — кадры движения."""
    rows = grid(f"chars/{name}")
    return {d: {"walk": [rows[r][c] for r in range(4)]} for c, d in enumerate(DIRECTIONS)}


def tile(sheet, col, row, w=1, h=1):
    return image(f"tiles/{sheet}").subsurface((col * TILE, row * TILE, w * TILE, h * TILE))


def flipped(frames):
    return [pygame.transform.flip(f, True, False) for f in frames]


_white = {}


def white(surface):
    """Белый силуэт спрайта для вспышки при попадании."""
    key = id(surface)
    if key not in _white:
        mask = pygame.mask.from_surface(surface)
        _white[key] = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    return _white[key]


_fonts = {}


FONTS = {"text": "Tiny5-Regular.ttf", "title": "NinjaAdventure.ttf"}  # у второго только латиница


def font(size, face="text"):
    key = (size, face)
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(str(ASSETS / "fonts" / FONTS[face]), size)
    return _fonts[key]


class Audio:
    """Звуки и музыка. Если звуковой карты нет, игра просто молчит."""

    VOLUMES = {"enemy_hit": 0.5, "sword": 0.5, "lance": 0.5, "wand": 0.45, "enemy_shoot": 0.4,
               "menu_move": 0.4, "switch": 0.5, "enemy_die": 0.55, "rock_break": 0.5}

    def __init__(self, music=0.5, sounds=0.7):
        self.music_volume = music
        self.sound_volume = sounds
        try:
            self.enabled = pygame.mixer.get_init() is not None
        except NotImplementedError:
            self.enabled = False
        self.sounds = {}
        self.track = None
        if self.enabled:
            for path in sorted((ASSETS / "sounds").glob("*.ogg")):
                self.sounds[path.stem] = pygame.mixer.Sound(str(path))

    def play(self, name):
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(self.sound_volume * self.VOLUMES.get(name, 0.7))
            sound.play()

    def music(self, track):
        if not self.enabled or track == self.track:
            return
        self.track = track
        try:
            pygame.mixer.music.load(str(ASSETS / "music" / f"{track}.ogg"))
            pygame.mixer.music.set_volume(self.music_volume * 0.6)
            pygame.mixer.music.play(-1, fade_ms=600)
        except pygame.error:
            self.track = None

    def fadeout(self, ms):
        if self.enabled:
            pygame.mixer.music.fadeout(ms)
            self.track = None

    def set_volumes(self, music, sounds):
        self.music_volume, self.sound_volume = music, sounds
        if self.enabled:
            pygame.mixer.music.set_volume(music * 0.6)
