"""Окно, главный цикл и экраны: меню, настройки, управление, итоги партии."""

import math

import pygame

from . import assets, save, ui
from .game import Game
from .i18n import Lang
from .settings import FPS, GOLD, GREY, HEIGHT, RED, SCREEN_H, SCREEN_W, TITLE, VERSION, WAVES_TOTAL, WEB, WHITE, WIDTH
from .world import World


class Backdrop:
    """Арена, медленно проплывающая за меню."""

    def __init__(self):
        self.world = World()
        self.t = 0.0

    def draw(self, view, dt):
        self.t += dt
        max_x, max_y = self.world.width - WIDTH, self.world.height - HEIGHT
        ox = round(max_x / 2 + math.sin(self.t * 0.07) * max_x / 2)
        oy = round(max_y / 2 + math.sin(self.t * 0.05) * max_y / 2)
        view.blit(self.world.floor, (-ox, -oy))
        for prop in sorted(self.world.props, key=lambda p: p.sort_y):
            view.blit(prop.image, prop.rect.move(-ox, -oy))
        ui.dim(view, 110)


class Scene:
    """Экран: мир рисуется в маленький view, интерфейс — поверх на screen."""

    def __init__(self, app):
        self.app = app

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw_world(self, view, dt):
        self.app.backdrop.draw(view, dt)

    def draw_ui(self, screen):
        pass


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        items = [("play", app.lang("play")), ("controls", app.lang("controls")), ("settings", app.lang("settings"))]
        if not WEB:
            items.append(("quit", app.lang("quit")))
        self.menu = ui.Menu(items, (SCREEN_W // 2, 344))
        app.audio.music("menu")

    def handle(self, event):
        choice = self.menu.handle(event, self.app.audio)
        if choice == "play":
            self.app.new_game()
        elif choice == "controls":
            self.app.scene = ControlsScene(self.app)
        elif choice == "settings":
            self.app.scene = SettingsScene(self.app)
        elif choice == "quit":
            self.app.running = False

    def draw_ui(self, screen):
        lang = self.app.lang
        bob = round(math.sin(self.app.backdrop.t * 2) * 4)
        title = ui.text(screen, "PIXEL GAMBLE", (SCREEN_W // 2, 112 + bob), 64, GOLD, "center", face="title")
        ui.text(screen, lang("subtitle"), (SCREEN_W // 2, 176), ui.SMALL, WHITE, "center")
        hero = ui.big(assets.image("chars/player_face.png"))
        screen.blit(hero, hero.get_rect(midright=(title.left - 24, 112 - bob)))
        boss = ui.big(assets.image("chars/boss_face.png"))
        screen.blit(boss, boss.get_rect(midleft=(title.right + 24, 112 + bob)))
        if self.app.data["best"]:
            ui.text(screen, lang("best", score=self.app.data["best"]), (SCREEN_W // 2, 216), ui.SMALL, GOLD, "center")
        self.menu.draw(screen)
        ui.text(screen, lang("credits"), (SCREEN_W // 2, SCREEN_H - 8), ui.SMALL, GREY, "midbottom")
        ui.text(screen, f"v{VERSION}", (SCREEN_W - 8, SCREEN_H - 8), ui.SMALL, GREY, "bottomright")


class ControlsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.menu = ui.Menu([("back", app.lang("back"))], (SCREEN_W // 2, SCREEN_H - 56))

    def handle(self, event):
        back = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.menu.handle(event, self.app.audio) == "back" or back:
            self.app.scene = MenuScene(self.app)

    def draw_ui(self, screen):
        rect = pygame.Rect(140, 36, SCREEN_W - 280, SCREEN_H - 120)
        ui.panel(screen, rect)
        ui.text(screen, self.app.lang("controls"), (SCREEN_W // 2, 70), ui.LARGE, GOLD, "center")
        for i, line in enumerate(self.app.lang("controls_text")):
            ui.text(screen, line, (rect.left + 36, 104 + i * 30), ui.SMALL, WHITE)
        self.menu.draw(screen)


class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.build()

    def build(self, index=0):
        lang, data = self.app.lang, self.app.data
        items = [("music", lang("music", value=round(data["music"] * 100))),
                 ("sounds", lang("sounds", value=round(data["sounds"] * 100))),
                 ("lang", lang("language"))]
        if not WEB:
            items.append(("fullscreen", lang("fullscreen", value=lang("on") if data["fullscreen"] else lang("off"))))
        items.append(("back", lang("back")))
        self.menu = ui.Menu(items, (SCREEN_W // 2, 300), width=380)
        self.menu.index = index

    def change(self, key, step):
        data = self.app.data
        if key in ("music", "sounds"):
            data[key] = round(min(1.0, max(0.0, data[key] + 0.1 * step)), 1)
            self.app.audio.set_volumes(data["music"], data["sounds"])
            self.app.audio.play("menu_move")
        elif key == "lang":
            self.app.lang.toggle()
            data["lang"] = self.app.lang.code
        elif key == "fullscreen":
            self.app.toggle_fullscreen()
        save.store(data)
        self.build(self.menu.index)

    def handle(self, event):
        key = self.menu.items[self.menu.index][0]
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            if key != "back":
                self.change(key, -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scene = MenuScene(self.app)
            return
        choice = self.menu.handle(event, self.app.audio)
        if choice == "back":
            self.app.scene = MenuScene(self.app)
        elif choice in ("music", "sounds"):
            # Enter/клик по громкости — шаг вверх по кругу 0…100%
            if self.app.data[choice] >= 1.0:
                self.app.data[choice] = -0.1
            self.change(choice, 1)
        elif choice:
            self.change(choice, 1)

    def draw_ui(self, screen):
        ui.text(screen, self.app.lang("settings"), (SCREEN_W // 2, 140), ui.LARGE, GOLD, "center")
        self.menu.draw(screen)
        ui.text(screen, "<  >", (SCREEN_W // 2, SCREEN_H - 60), ui.SMALL, GREY, "center")


class PlayScene(Scene):
    def __init__(self, app, game):
        super().__init__(app)
        self.game = game

    def handle(self, event):
        self.game.handle(event)

    def update(self, dt):
        self.game.update(dt, self.app.bot.controls(self.game) if self.app.bot else None)

    def draw_world(self, view, dt):
        self.game.draw_world(view, dt)

    def draw_ui(self, screen):
        self.game.draw_ui(screen)


class ResultsScene(Scene):
    def __init__(self, app, game):
        super().__init__(app)
        self.victory = game.result == "victory"
        self.record = game.score > app.data["best"]
        if self.record:
            app.data["best"] = game.score
            save.store(app.data)
        minutes, seconds = divmod(int(game.time), 60)
        lang = app.lang
        self.rows = [(lang("stat_wave"), f"{game.wave}/{WAVES_TOTAL}"), (lang("stat_kills"), game.kills),
                     (lang("stat_level"), game.player.level), (lang("stat_time"), f"{minutes}:{seconds:02d}"),
                     (lang("stat_score"), game.score)]
        self.menu = ui.Menu([("again", lang("again")), ("to_menu", lang("to_menu"))], (SCREEN_W // 2, 444))
        app.audio.music("menu")

    def handle(self, event):
        choice = self.menu.handle(event, self.app.audio)
        if choice == "again":
            self.app.new_game()
        elif choice == "to_menu":
            self.app.to_menu()

    def draw_ui(self, screen):
        lang = self.app.lang
        title = lang("victory") if self.victory else lang("game_over")
        ui.text(screen, title, (SCREEN_W // 2, 72), ui.HUGE, GOLD if self.victory else RED, "center")
        rect = pygame.Rect(SCREEN_W // 2 - 220, 124, 440, 240)
        ui.panel(screen, rect)
        for i, (label, value) in enumerate(self.rows):
            y = rect.top + 24 + i * 40
            ui.text(screen, label, (rect.left + 28, y), ui.SMALL, WHITE)
            ui.text(screen, value, (rect.right - 28, y), ui.SMALL, GOLD, "topright")
        if self.record:
            ui.text(screen, lang("new_record"), (SCREEN_W // 2, rect.bottom + 20), ui.SMALL, GOLD, "center")
        self.menu.draw(screen)


class App:
    def __init__(self, bot=None):
        pygame.init()
        try:
            pygame.mixer.init()
        except (pygame.error, NotImplementedError):  # нет звуковой карты или SDL_mixer
            pass
        self.data = save.load()
        self.bot = bot
        flags = 0 if WEB else pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.view = pygame.Surface((WIDTH, HEIGHT)).convert()
        pygame.display.set_caption(TITLE)
        pygame.display.set_icon(assets.image("chars/player_face.png"))
        if self.data["fullscreen"] and not WEB and not bot:
            pygame.display.toggle_fullscreen()
        self.clock = pygame.time.Clock()
        self.audio = assets.Audio(self.data["music"], self.data["sounds"])
        self.lang = Lang(self.data["lang"])
        self.backdrop = Backdrop()
        self.running = True
        self.scene = MenuScene(self)
        self.game = None

    def new_game(self):
        self.game = Game(self, rng=self.bot.rng if self.bot else None)
        self.scene = PlayScene(self, self.game)

    def to_menu(self):
        self.game = None
        self.scene = MenuScene(self)

    def show_results(self, game):
        self.scene = ResultsScene(self, game)

    def toggle_fullscreen(self):
        if WEB:
            return
        try:
            pygame.display.toggle_fullscreen()
            self.data["fullscreen"] = not self.data["fullscreen"]
        except pygame.error:
            pass

    def frame(self, dt=None):
        if dt is None:
            dt = min(self.clock.tick(FPS) / 1000, 1 / 20)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                save.store(self.data)
            elif event.type in (pygame.WINDOWFOCUSLOST,) and isinstance(self.scene, PlayScene) and not self.bot:
                self.game.paused = self.game.paused or not self.game.result
            else:
                self.scene.handle(event)
        if self.bot:
            self.bot.drive(self)
        self.scene.update(dt)
        self.scene.draw_world(self.view, dt)
        pygame.transform.scale(self.view, self.screen.get_size(), self.screen)
        self.scene.draw_ui(self.screen)
        pygame.display.flip()
