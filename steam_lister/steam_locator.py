"""Localisation de l'installation Steam et du dossier Workshop de Civilization VI.

Sous Steam, les mods souscrits via le Workshop sont stockés directement dans :
    <bibliothèque Steam>/steamapps/workshop/content/289070/<id_du_mod>/
(et non dans le dossier Documents/My Games/... utilisé par les mods manuels).
Ce module tente de retrouver ce dossier automatiquement, sur toutes les
bibliothèques Steam configurées (pas seulement l'installation par défaut).
"""
import platform
import re
from pathlib import Path
from typing import List, Optional

CIV6_APP_ID = "289070"


def _default_steam_paths() -> List[Path]:
    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates += [
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
        ]
    elif system == "Darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "Steam")
    else:
        candidates += [
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".steam" / "steam",
        ]
    return [c for c in candidates if c.exists()]


def find_steam_install_path() -> Optional[Path]:
    """Essaie le registre Windows en priorité, puis les emplacements par défaut."""
    if platform.system() == "Windows":
        try:
            import winreg
            keys_to_try = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ]
            for hive, subkey, value_name in keys_to_try:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        value, _ = winreg.QueryValueEx(key, value_name)
                        p = Path(value)
                        if p.exists():
                            return p
                except OSError:
                    continue
        except ImportError:
            pass

    for p in _default_steam_paths():
        return p
    return None


def parse_library_folders(steam_path: Path) -> List[Path]:
    """Lit steamapps/libraryfolders.vdf pour retrouver toutes les bibliothèques Steam
    (utile si les jeux/mods sont installés sur un autre disque que Steam lui-même)."""
    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return libraries
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return libraries
    for match in re.finditer(r'"path"\s*"([^"]+)"', text):
        raw = match.group(1).replace("\\\\", "\\")
        p = Path(raw)
        if p.exists() and p not in libraries:
            libraries.append(p)
    return libraries


def find_workshop_content_folders(app_id: str = CIV6_APP_ID) -> List[Path]:
    """Retourne tous les dossiers steamapps/workshop/content/<app_id> existants,
    tous emplacements de bibliothèque confondus."""
    steam_path = find_steam_install_path()
    if not steam_path:
        return []
    libraries = parse_library_folders(steam_path)
    found = []
    for lib in libraries:
        candidate = lib / "steamapps" / "workshop" / "content" / app_id
        if candidate.exists():
            found.append(candidate)
    return found
