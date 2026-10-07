"""Pixel Gamble — точка входа (рабочий стол и браузерная сборка pygbag).

    python main.py                       обычная игра
    python main.py --bot --frames 6000   автоигрок без участия человека (для проверок)
"""

import argparse
import asyncio
import sys

# в браузерной сборке (pygame-ce) подмодули сами не подгружаются — импортируем явно
import pygame.font  # noqa: F401
import pygame.image  # noqa: F401
import pygame.mask  # noqa: F401
import pygame.sprite  # noqa: F401
import pygame.transform  # noqa: F401

try:
    import pygame.mixer  # noqa: F401
except ImportError:  # без SDL_mixer игра просто молчит
    pass

from pixelgamble.app import App


def parse_args():
    parser = argparse.ArgumentParser(description="Pixel Gamble")
    parser.add_argument("--bot", action="store_true", help="играет автоигрок")
    parser.add_argument("--frames", type=int, default=0, help="остановиться через N кадров")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--wave", type=int, default=1, help="начать с волны N (для проверок)")
    parser.add_argument("--fast", action="store_true", help="без ожидания кадров: фиксированный шаг 1/60")
    parser.add_argument("--record", help="записать GIF (нужен Pillow)")
    return parser.parse_args([] if sys.platform == "emscripten" else None)


async def main():
    args = parse_args()
    bot = None
    if args.bot:
        from pixelgamble.bot import Bot
        bot = Bot(args.seed)
    app = App(bot)
    if args.wave > 1:
        app.new_game()
        app.game.wave = args.wave
        app.game.start_wave()
    recorder = None
    if args.record:
        from pixelgamble.record import Recorder
        recorder = Recorder(args.record)
    frame = 0
    while app.running:
        app.frame(1 / 60 if args.fast else None)
        if recorder:
            recorder.capture(app.screen, frame)
        frame += 1
        if bot and args.fast and frame % 3600 == 0 and app.game:  # раз в минуту игрового времени
            g = app.game
            foes = [(e.kind, e.state, round(e.pos.x), round(e.pos.y)) for e in g.enemies]
            print(f"[{frame}] wave={g.wave} state={g.state} hp={g.player.hp} queue={len(g.spawner.queue)} "
                  f"player=({round(g.player.pos.x)},{round(g.player.pos.y)}) foes={foes[:6]}", flush=True)
        if args.frames and frame >= args.frames:
            break
        if bot and bot.finished:
            break
        await asyncio.sleep(0)
    if recorder:
        recorder.save()
    if bot:
        game = app.game
        result = bot.finished[-1] if bot.finished else None
        outcome = "running" if result is None else "victory" if result.victory else "dead"
        print(f"frames={frame} wave={game.wave if game else '-'} kills={game.kills if game else 0} "
              f"score={game.score if game else 0} result={outcome}")
        if game:
            print("waves:", game.log, "level:", game.player.level, "weapons:", game.player.weapons,
                  "upgrades:", game.taken)


asyncio.run(main())
