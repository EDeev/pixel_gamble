"""Элементы интерфейса в экранных координатах (960×540): текст, панели, меню, сердечки, карточки."""

import pygame

from . import assets
from .settings import BLACK, GOLD, GREY, PANEL, PANEL_EDGE, PANEL_LIGHT, SCALE, SCREEN_H, SCREEN_W, WHITE

# размеры шрифта: Tiny5 чёткий на кратных 10
SMALL, MEDIUM, LARGE, HUGE = 20, 30, 40, 60

_text_cache = {}


def outlined(value, size, color, outline=(20, 16, 24), face="text"):
    """Текст с контуром — читается на любом фоне. Результат кэшируется."""
    key = (value, size, color, outline, face)
    image = _text_cache.get(key)
    if image is None:
        font = assets.font(size, face)
        base = font.render(value, False, color)
        edge = font.render(value, False, outline)
        w = max(2, size // 10)
        image = pygame.Surface((base.get_width() + 2 * w, base.get_height() + 2 * w), pygame.SRCALPHA)
        for dx in (0, w, 2 * w):
            for dy in (0, w, 2 * w):
                image.blit(edge, (dx, dy))
        image.blit(base, (w, w))
        if len(_text_cache) > 600:
            _text_cache.clear()
        _text_cache[key] = image
    return image


def text(surface, value, pos, size=SMALL, color=WHITE, anchor="topleft", face="text"):
    image = outlined(str(value), size, color, face=face)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def big(image, factor=SCALE):
    return pygame.transform.scale_by(image, factor)


def panel(surface, rect, color=PANEL, edge=PANEL_EDGE, light=PANEL_LIGHT):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, edge, rect, border_radius=6)
    pygame.draw.rect(surface, light, rect.inflate(-4, -4), border_radius=5)
    pygame.draw.rect(surface, color, rect.inflate(-8, -8), border_radius=4)


def dim(surface, alpha=150):
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((10, 8, 14, alpha))
    surface.blit(shade, (0, 0))


class Menu:
    """Вертикальный список кнопок: стрелки/WS, Enter/пробел, мышь."""

    def __init__(self, items, center, width=300, gap=40):
        self.items = items  # [(id, подпись)]
        self.center = center
        self.width, self.gap = width, gap
        self.index = 0

    def rects(self):
        top = self.center[1] - (len(self.items) * self.gap) // 2
        return [pygame.Rect(self.center[0] - self.width // 2, top + i * self.gap, self.width, self.gap - 8)
                for i in range(len(self.items))]

    def handle(self, event, audio):
        """Возвращает id выбранной кнопки или None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.items)
                audio.play("menu_move")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.items)
                audio.play("menu_move")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                audio.play("menu_accept")
                return self.items[self.index][0]
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rects()):
                if rect.collidepoint(event.pos) and i != self.index:
                    self.index = i
                    audio.play("menu_move")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects()):
                if rect.collidepoint(event.pos):
                    self.index = i
                    audio.play("menu_accept")
                    return self.items[i][0]
        return None

    def draw(self, surface):
        for i, (rect, (_, label)) in enumerate(zip(self.rects(), self.items, strict=True)):
            active = i == self.index
            panel(surface, rect, color=(86, 58, 52) if active else PANEL)
            text(surface, label, rect.center, SMALL, GOLD if active else WHITE, "center")
            if active:
                text(surface, ">", (rect.left - 12, rect.centery), SMALL, GOLD, "midright")


_hearts = None


def hearts(surface, player, pos):
    global _hearts
    if _hearts is None:
        _hearts = [big(f) for f in assets.strip("ui/hearts.png", 16)]  # пусто, 1/4, 1/2, 3/4, целое
    x, y = pos
    for i in range(player.max_hp // 4):
        quarters = max(0, min(4, player.hp - i * 4))
        surface.blit(_hearts[quarters], (x + i * 26, y))


def bar(surface, rect, ratio, color, back=(40, 30, 40)):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, BLACK, rect)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(surface, back, inner)
    if ratio > 0:
        pygame.draw.rect(surface, color, (inner.x, inner.y, round(inner.width * min(1.0, ratio)), inner.height))


def weapon_slots(surface, player, pos):
    x, y = pos
    for i, weapon in enumerate(player.weapons):
        rect = pygame.Rect(x + i * 44, y, 40, 52)
        active = weapon == player.weapon
        panel(surface, rect, color=(86, 58, 52) if active else PANEL, light=GOLD if active else PANEL_LIGHT)
        icon = big(assets.image(f"items/{weapon}.png"))
        surface.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 2)))
        text(surface, i + 1, (rect.right - 3, rect.bottom + 2), SMALL, GREY, "bottomright")


def card_rects(count=3):
    w, h, gap = 232, 240, 24
    left = SCREEN_W // 2 - (count * w + (count - 1) * gap) // 2
    return [pygame.Rect(left + i * (w + gap), SCREEN_H // 2 - h // 2 + 20, w, h) for i in range(count)]


def cards(surface, keys, lang, selected):
    for i, (key, rect) in enumerate(zip(keys, card_rects(len(keys)), strict=True)):
        if i == selected:
            rect = rect.move(0, -6)
        active = i == selected
        panel(surface, rect, color=(86, 58, 52) if active else PANEL, light=GOLD if active else PANEL_LIGHT)
        icon = big(assets.image(f"icons/{key}.png"), 3)
        surface.blit(icon, icon.get_rect(center=(rect.centerx, rect.top + 64)))
        title, desc = lang.upgrade(key)
        text(surface, title, (rect.centerx, rect.top + 118), SMALL, GOLD, "midtop")
        for j, line in enumerate(wrap(desc, 20)):
            text(surface, line, (rect.centerx, rect.top + 152 + j * 22), SMALL, WHITE, "midtop")
        text(surface, i + 1, (rect.centerx, rect.bottom - 8), SMALL, GREY, "midbottom")


def wrap(value, width):
    words, lines, line = value.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines
