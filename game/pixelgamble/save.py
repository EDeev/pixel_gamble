"""Рекорд и настройки: файл в профиле пользователя или localStorage в браузере."""

import json
import os
import sys
from pathlib import Path

from .settings import WEB

DEFAULTS = {"best": 0, "music": 0.5, "sounds": 0.7, "lang": "ru", "fullscreen": False}
KEY = "pixel_gamble"


def _path():
    if os.environ.get("PIXEL_GAMBLE_SAVE"):
        return Path(os.environ["PIXEL_GAMBLE_SAVE"])
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "pixel_gamble" / "save.json"


def load():
    data = dict(DEFAULTS)
    try:
        if WEB:
            import platform
            raw = platform.window.localStorage.getItem(KEY)
        else:
            path = _path()
            raw = path.read_text(encoding="utf-8") if path.exists() else None
        if raw:
            data.update({k: v for k, v in json.loads(raw).items() if k in DEFAULTS})
    except Exception:  # испорченный файл или недоступное хранилище — играем с настройками по умолчанию
        pass
    return data


def store(data):
    raw = json.dumps({k: data[k] for k in DEFAULTS})
    try:
        if WEB:
            import platform
            platform.window.localStorage.setItem(KEY, raw)
        else:
            path = _path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw, encoding="utf-8")
    except Exception:
        pass
