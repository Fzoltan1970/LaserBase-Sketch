import json
import sys
from pathlib import Path

# -------------------------------------------------
# Hol fut a program
# -------------------------------------------------
def app_dir():
    """EXE mappa (portable adat helye)"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def bundle_dir():
    """Beépített erőforrások helye (json fordítások)"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


# -------------------------------------------------
# CONFIG (portable — exe mellett marad)
# -------------------------------------------------
CONFIG_FILE = app_dir() / "config.json"


def _load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"language": "hu"}


def _save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


_cfg = _load_config()
LANG = _cfg.get("language", "hu")


# -------------------------------------------------
# TRANSLATIONS (EXE-be csomagolva)
# -------------------------------------------------
LANG_DIR = bundle_dir() / "lang"
_cache = {}


def _load_lang(lang):
    if lang in _cache:
        return _cache[lang]

    file = LANG_DIR / f"{lang}.json"

    if not file.exists():
        _cache[lang] = {}
        return _cache[lang]

    with open(file, "r", encoding="utf-8") as f:
        _cache[lang] = json.load(f)

    return _cache[lang]


def tr(key):
    return _load_lang(LANG).get(key, key)


# -------------------------------------------------
# PUBLIC API
# -------------------------------------------------
def set_language(new_lang):
    global LANG
    LANG = new_lang
    _cfg["language"] = new_lang
    _save_config(_cfg)
