"""Analyse du dossier Mods de Civilization VI : liste les mods installés et leur version locale."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


def _parse_modinfo(modinfo_path: Path) -> Dict[str, Optional[str]]:
    """Extrait le nom affiché et la version déclarée par l'auteur d'un fichier .modinfo."""
    info: Dict[str, Optional[str]] = {"title": None, "version": None}
    try:
        tree = ET.parse(modinfo_path)
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


def scan_installed_mods(mods_folder: Path) -> List[Dict]:
    """Scanne le dossier Mods et retourne, pour chaque sous-dossier contenant
    un fichier .modinfo, son nom et sa version locale."""
    results: List[Dict] = []
    if not mods_folder.exists():
        return results

    for child in sorted(mods_folder.iterdir()):
        if not child.is_dir():
            continue
        modinfo_files = list(child.glob("*.modinfo")) or list(child.glob("*/*.modinfo"))
        if not modinfo_files:
            continue
        info = _parse_modinfo(modinfo_files[0])
        results.append({
            "folder": child.name,
            "title": info["title"] or child.name,
            "version": info["version"] or "?",
        })
    return results
