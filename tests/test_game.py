"""Проверки без окна: SDL_VIDEODRIVER=dummy, автоигрок вместо человека."""

import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
GAME = Path(__file__).resolve().parent.parent / "game"
sys.path.insert(0, str(GAME))

import pytest  # noqa: E402
from pixelgamble import save, upgrades  # noqa: E402
from pixelgamble.app import App, PlayScene, ResultsScene  # noqa: E402
from pixelgamble.bot import Bot  # noqa: E402
from pixelgamble.game import Game  # noqa: E402
from pixelgamble.player import Player  # noqa: E402
from pixelgamble.waves import WAVES, Spawner  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PIXEL_GAMBLE_SAVE", str(tmp_path / "save.json"))
    return App(Bot(seed=3))


def run(app, frames):
    for _ in range(frames):
        app.frame(1 / 60)


def test_bot_clears_first_waves(app):
    run(app, 60 * 60)  # минута игрового времени
    game = app.game
    assert game.kills >= 10
    assert game.wave >= 2
    assert game.log and game.log[0][0] == 1


def test_menus_render(app):
    app.bot = None
    for scene in ("controls", "settings"):
        app.to_menu()
        app.scene.menu.index = [i for i, _ in app.scene.menu.items].index(scene)
        app.scene.handle(_key("return"))
        run(app, 3)
    app.lang.toggle()
    run(app, 3)


def test_boss_goes_through_phases(app):
    app.new_game()
    game = app.game
    game.wave = 10
    game.start_wave()
    game.player.invulnerable = 10 ** 6  # проверяем босса, а не умение бота уворачиваться
    run(app, 60 * 6)
    assert game.boss is not None
    boss = game.boss
    for phase in (2, 3):
        boss.state = "move"
        boss.hurt(boss.max_hp * 0.4, game.player.pos, 0)
        assert boss.phase == phase
        run(app, 60 * 3)
    boss.state = "move"
    boss.hurt(boss.max_hp * 2, game.player.pos, 0)
    game.on_enemy_hit(boss)
    run(app, 2)
    assert game.boss is None and game.result == "victory"
    run(app, 60 * 6)
    assert isinstance(app.scene, ResultsScene)
    assert app.data["best"] == game.score > 2000


def test_death_shows_results(app):
    app.new_game()
    game = app.game
    game.player.invulnerable = 0
    game.damage_player(game.player.max_hp, game.player.pos)
    assert game.result == "dead"
    run(app, 60 * 6)
    assert isinstance(app.scene, ResultsScene)


def test_upgrades_apply(app):
    app.new_game()
    player, taken = app.game.player, {}
    for key in upgrades.POOL:
        upgrades.apply(key, player, taken)
    assert player.weapons == ["sword", "lance", "wand"]
    assert player.max_hp == 16 and player.hp == player.max_hp
    assert player.multishot and player.damage_mult > 1
    offer = upgrades.offer(player, {}, 1, random.Random(1))
    assert len(offer) == 3 and len(set(offer)) == 3


def test_every_wave_spawns_its_plan():
    for number, plan in enumerate(WAVES, start=1):
        spawner = Spawner(number, random.Random(number))
        assert spawner.total == sum(plan.values())
        spawned = []
        points = [pygame_vector(500, 500), pygame_vector(40, 40)]
        while not spawner.done():
            spawned += spawner.update(1.0, 0, pygame_vector(0, 0), points)
        assert sorted(k for k, _ in spawned) == sorted(k for k, c in plan.items() for _ in range(c))


def test_save_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PIXEL_GAMBLE_SAVE", str(tmp_path / "s.json"))
    data = save.load()
    assert data["best"] == 0
    data.update(best=1234, lang="en")
    save.store(data)
    assert save.load()["best"] == 1234 and save.load()["lang"] == "en"
    (tmp_path / "s.json").write_text("{broken", encoding="utf-8")
    assert save.load()["best"] == 0


def test_player_dies_once(app):
    player = Player((100, 100))
    assert player.hurt(5, (90, 100))
    assert not player.hurt(5, (90, 100))  # неуязвимость после удара
    player.invulnerable = 0
    player.hurt(100, (90, 100))
    assert player.dead and player.hp == 0


def test_rock_breaks(app):
    app.new_game()
    game = app.game
    rock = next(p for p in game.world.props if p.breakable)
    before = len(game.obstacles)
    game.break_rock(rock)
    assert len(game.obstacles) == before - 1


def pygame_vector(x, y):
    import pygame
    return pygame.Vector2(x, y)


def _key(name):
    import pygame
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.key.key_code(name), mod=0, unicode="")


def test_play_scene_is_active(app):
    run(app, 2)
    assert isinstance(app.scene, PlayScene) and isinstance(app.game, Game)


def test_entity_never_tunnels_through_walls(app):
    app.new_game()
    game = app.game
    player = game.player
    wall = game.walls[2]  # левая стена
    player.pos.update(wall.right - 2, 300)  # стоим чуть внутри стены
    player.hitbox.center = (round(player.pos.x), round(player.pos.y))
    for step in ((3, 0), (-3, 0), (0, 3), (3, 3)):
        player.move(pygame_vector(*step), game.obstacles)
        assert player.hitbox.left >= wall.right - 1


def test_slow_movement_accumulates(app):
    app.new_game()
    player = app.game.player
    start = player.pos.x
    for _ in range(60):
        player.move(pygame_vector(0.3, 0), [])
    assert player.pos.x - start > 15
