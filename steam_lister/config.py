"""Stockage local de la configuration de l'application (clé API Pixeldrain)."""
import json
import os
import platform
from pathlib import Path
from typing import Optional

APP_DIR_NAME = "Civ6ModManager"
CONFIG_FILE_NAME = "steam_lister_config.json"


def _config_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home()
    return base / APP_DIR_NAME


def _config_path() -> Path:
    return _config_dir() / CONFIG_FILE_NAME


def load_api_key() -> Optional[str]:
    path = _config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    key = data.get("pixeldrain_api_key")
    return key or None


def save_api_key(api_key: str) -> None:
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    _config_path().write_text(
        json.dumps({"pixeldrain_api_key": api_key}, indent=2), encoding="utf-8"
    )
