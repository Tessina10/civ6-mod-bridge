"""Permet aux tests d'importer les modules locaux (mod_scanner, gui...) sans
faire de epic_mod_manager/ un package installé : on ajoute simplement le
dossier parent au sys.path, comme le fait PyInstaller en exécutant main.py
depuis ce même dossier.

Lance les tests depuis ce dossier (`cd epic_mod_manager && pytest`), pas
depuis la racine du dépôt : steam_lister/ contient des modules de même nom
(mod_scanner.py, gui.py) et les exécuter dans le même process pytest
provoquerait des collisions d'import (voir CLAUDE.md)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
