"""Analyse des dossiers de mods Workshop de Civilization VI."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


def _parse_modinfo(mod_folder: Path) -> Dict[str, Optional[str]]:
    """Cherche un fichier .modinfo dans le dossier du mod et tente d'en extraire
    le nom affiché et la version déclarée par l'auteur."""
    info: Dict[str, Optional[str]] = {"title": None, "version": None}
    modinfo_files = list(mod_folder.glob("*.modinfo"))
    if not modinfo_files:
        return info
    try:
        tree = ET.parse(modinfo_files[0])
        root = tree.getroot()
        info["version"] = root.attrib.get("version")
        name_el = root.find("./Properties/Name")
        if name_el is not None and name_el.text:
            text = name_el.text.strip()
            # Ignore les clés de traduction brutes (ex: LOC_MOD_XXX_NAME)
            if text and not text.startswith("LOC_"):
                info["title"] = text
    except (ET.ParseError, OSError):
        pass
    return info


def scan_workshop_mods(content_folder: Path) -> List[Dict]:
    """Scanne un dossier steamapps/workshop/content/289070 et liste les mods présents.

    Chaque sous-dossier numérique correspond directement à un ID de Workshop.
    """
    results: List[Dict] = []
    if not content_folder.exists():
        return results

    for child in sorted(content_folder.iterdir()):
        if not child.is_dir() or not child.name.isdigit():
            continue
        info = _parse_modinfo(child)
        try:
            mtime = child.stat().st_mtime
        except OSError:
            mtime = None
        results.append({
            "id": child.name,
            "title": info["title"] or child.name,
            "version": info["version"],
            "path": str(child),
            "mtime": mtime,
        })
    return results
