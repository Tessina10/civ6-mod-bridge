"""Tests des fonctions pures de gui.py (pas d'instanciation de App/Tk ici :
uniquement la logique métier, sans ouvrir de fenêtre)."""
import zipfile

import gui


def test_sanitize_folder_name_replaces_invalid_characters():
    # ':' '/' '*' '!' sont hors de [\w\-. ] -> remplacés par '_', puis les '_'
    # finaux sont retirés par rstrip("_") dans l'implémentation.
    assert gui._sanitize_folder_name("Mod: Special/Édition*!") == "Mod_ Special_Édition"


def test_sanitize_folder_name_empty_result_falls_back_to_mod():
    assert gui._sanitize_folder_name("///") == "mod"


def test_write_mods_zip_creates_expected_archive_layout(tmp_path):
    mod_folder = tmp_path / "source" / "111"
    mod_folder.mkdir(parents=True)
    (mod_folder / "Mod.modinfo").write_text("<Mod/>", encoding="utf-8")
    (mod_folder / "Text").mkdir()
    (mod_folder / "Text" / "fr_FR.xml").write_text("<Text/>", encoding="utf-8")

    mods_data = [{"id": "111", "title": "Mon Mod", "path": str(mod_folder)}]
    zip_path = tmp_path / "out.zip"

    gui._write_mods_zip(zip_path, mods_data)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert "111_Mon Mod/Mod.modinfo" in names
    assert "111_Mon Mod/Text/fr_FR.xml" in names
