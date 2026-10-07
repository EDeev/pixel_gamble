"""Копирует нужные файлы из набора Ninja Adventure (CC0) в game/assets.

Набор: https://pixel-boy.itch.io/ninja-adventure-asset-pack — архив
«Ninja Adventure - Asset Pack.zip». Звуки перекодируются в OGG (нужен ffmpeg),
потому что браузерная сборка (pygbag) надёжно играет только OGG.

    python tools/import_assets.py "путь/к/Ninja Adventure - Asset Pack"
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "game" / "assets"

IMAGES = {
    "chars/player.png": "Actor/Character/NinjaGreen/SpriteSheet.png",
    "chars/player_face.png": "Actor/Character/NinjaGreen/Faceset.png",
    "chars/ninja.png": "Actor/Character/NinjaGray/SpriteSheet.png",
    "chars/skeleton.png": "Actor/Character/Skeleton/SpriteSheet.png",
    "chars/slime.png": "Actor/Monster/Slime/Slime.png",
    "chars/bat.png": "Actor/Monster/BlueBat/SpriteSheet.png",
    "chars/cyclop_walk.png": "Actor/Boss/DemonCyclop/Walk.png",
    "chars/cyclop_hit.png": "Actor/Boss/DemonCyclop/Hit.png",
    "chars/boss_walk.png": "Actor/Boss/GiantRedSamurai/Walk.png",
    "chars/boss_idle.png": "Actor/Boss/GiantRedSamurai/Idle.png",
    "chars/boss_attack_l.png": "Actor/Boss/GiantRedSamurai/AttackLeft.png",
    "chars/boss_attack_r.png": "Actor/Boss/GiantRedSamurai/AttackRight.png",
    "chars/boss_charge_l.png": "Actor/Boss/GiantRedSamurai/ChargeLeft.png",
    "chars/boss_charge_r.png": "Actor/Boss/GiantRedSamurai/ChargeRight.png",
    "chars/boss_hit.png": "Actor/Boss/GiantRedSamurai/Hit.png",
    "chars/boss_face.png": "Actor/Boss/GiantRedSamurai/Faceset.png",
    "chars/shadow.png": "Actor/Character/Shadow.png",
    "tiles/floor.png": "Backgrounds/Tilesets/TilesetFloor.png",
    "tiles/nature.png": "Backgrounds/Tilesets/TilesetNature.png",
    "fx/arc.png": "FX/Slash/SpriteSheetArc.png",
    "fx/smoke.png": "FX/Smoke/Smoke/SpriteSheet.png",
    "fx/energy_ball.png": "FX/Projectile/EnergyBall.png",
    "fx/shuriken.png": "FX/Projectile/Shuriken.png",
    "fx/rock.png": "FX/Particle/Rock.png",
    "fx/leaf.png": "FX/Particle/Leaf.png",
    "items/heart.png": "Items/Potion/Heart.png",
    "items/sword.png": "Items/Weapons/Sword/Sprite.png",
    "items/lance.png": "Items/Weapons/Lance/Sprite.png",
    "items/wand.png": "Items/Weapons/MagicWand/Sprite.png",
    "items/sword_hand.png": "Items/Weapons/Sword/SpriteInHand.png",
    "items/lance_hand.png": "Items/Weapons/Lance/SpriteInHand.png",
    "items/wand_hand.png": "Items/Weapons/MagicWand/SpriteInHand.png",
    "ui/hearts.png": "Ui/Receptacle/Heart.png",
    "icons/heart.png": "Ui/Skill Icon/Spell/DefenseUpgrade.png",
    "icons/damage.png": "Ui/Skill Icon/Spell/AttackUpgrade.png",
    "icons/speed.png": "Ui/Skill Icon/Items & Weapon/Boot.png",
    "icons/haste.png": "Ui/Skill Icon/Spell/Cut.png",
    "icons/heal.png": "Ui/Skill Icon/Spell/Heal.png",
    "icons/reach.png": "Ui/Skill Icon/Items & Weapon/Hook.png",
    "icons/lance.png": "Ui/Skill Icon/Items & Weapon/Arrow.png",
    "icons/wand.png": "Ui/Skill Icon/Spell/MagicWeapon.png",
    "icons/multishot.png": "Ui/Skill Icon/Items & Weapon/Shuriken.png",
    "icons/vampire.png": "Ui/Skill Icon/Spell/Necromancy.png",
    "icons/knockback.png": "Ui/Skill Icon/Job & Action/Punch.png",
}

SOUNDS = {
    "sword": "Audio/Sounds/Whoosh & Slash/Slash.wav",
    "lance": "Audio/Sounds/Whoosh & Slash/Whoosh.wav",
    "wand": "Audio/Sounds/Magic & Skill/Magic1.wav",
    "enemy_hit": "Audio/Sounds/Hit & Impact/Hit1.wav",
    "enemy_die": "Audio/Sounds/Hit & Impact/Impact3.wav",
    "player_hurt": "Audio/Sounds/Hit & Impact/Hit5.wav",
    "rock_break": "Audio/Sounds/Hit & Impact/Impact2.wav",
    "enemy_shoot": "Audio/Sounds/Whoosh & Slash/Launch.wav",
    "boss_slash": "Audio/Sounds/Whoosh & Slash/Slash5.wav",
    "boss_stomp": "Audio/Sounds/Hit & Impact/Impact5.wav",
    "boss_appear": "Audio/Sounds/Alert/Alert5.wav",
    "heal": "Audio/Sounds/Magic & Skill/Heal.wav",
    "level_up": "Audio/Jingles/LevelUp1.wav",
    "power_up": "Audio/Sounds/Bonus/PowerUp1.wav",
    "wave_start": "Audio/Sounds/Alert/Alert.wav",
    "wave_clear": "Audio/Jingles/Success1.wav",
    "game_over": "Audio/Jingles/GameOver.wav",
    "victory": "Audio/Jingles/Success3.wav",
    "menu_move": "Audio/Sounds/Menu/Move1.wav",
    "menu_accept": "Audio/Sounds/Menu/Accept6.wav",
    "menu_back": "Audio/Sounds/Menu/Cancel2.wav",
    "switch": "Audio/Sounds/Menu/Menu8.wav",
}

MUSIC = {
    "menu": "Audio/Musics/1 - Adventure Begin.ogg",
    "battle": "Audio/Musics/17 - Fight.ogg",
    "boss": "Audio/Musics/28 - Tension.ogg",
}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pack = Path(sys.argv[1])
    if not (pack / "Actor").is_dir():
        sys.exit(f"не похоже на папку набора: {pack}")

    for dest, src in IMAGES.items():
        target = DEST / "images" / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pack / src, target)

    sounds = DEST / "sounds"
    sounds.mkdir(parents=True, exist_ok=True)
    for name, src in SOUNDS.items():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(pack / src),
                        "-c:a", "libvorbis", "-q:a", "4", str(sounds / f"{name}.ogg")], check=True)

    music = DEST / "music"
    music.mkdir(parents=True, exist_ok=True)
    for name, src in MUSIC.items():
        shutil.copyfile(pack / src, music / f"{name}.ogg")

    (DEST / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pack / "Ui/Font/NormalFont.ttf", DEST / "fonts" / "NinjaAdventure.ttf")  # латиница, для заголовка
    shutil.copyfile(pack / "LICENSE.txt", DEST / "LICENSE-ninja-adventure.txt")
    print(f"готово: {len(IMAGES)} картинок, {len(SOUNDS)} звуков, {len(MUSIC)} мелодий")


if __name__ == "__main__":
    main()
