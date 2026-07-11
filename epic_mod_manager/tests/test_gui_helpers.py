"""Tests des fonctions pures de gui.py (pas d'instanciation de App/Tk ici, et
pas de réseau réel : aucune clé API Pixeldrain n'est disponible en CI/local
sans configuration)."""
import zipfile

import gui


def test_extract_pixeldrain_id_from_full_link():
    assert gui._extract_pixeldrain_id("https://pixeldrain.com/u/abc123XY") == "abc123XY"


def test_extract_pixeldrain_id_from_api_link():
    assert gui._extract_pixeldrain_id("https://pixeldrain.com/api/file/abc123XY") == "abc123XY"


def test_extract_pixeldrain_id_from_raw_id():
    assert gui._extract_pixeldrain_id("abc123XY") == "abc123XY"


def test_extract_pixeldrain_id_strips_whitespace():
    assert gui._extract_pixeldrain_id("  abc123XY  ") == "abc123XY"


def test_extract_pixeldrain_id_rejects_invalid_input():
    assert gui._extract_pixeldrain_id("") is None
    assert gui._extract_pixeldrain_id("not a valid link !!") is None


def test_extract_zip_to_folder_round_trip(tmp_path):
    # Simule l'archive que produit steam_lister._write_mods_zip() : un dossier
    # par mod au premier niveau (<id>_<titre>/...), sans réimporter le module
    # steam_lister/gui.py (même nom "gui" que ce module -> collision d'import
    # si les deux étaient chargés dans le même process, voir conftest.py).
    zip_path = tmp_path / "mods_recus.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("111_Mon Mod/Mod.modinfo", "<Mod/>")
        zf.writestr("111_Mon Mod/Text/fr_FR.xml", "<Text/>")
        zf.writestr("222_Autre Mod/Autre.modinfo", "<Mod/>")

    dest = tmp_path / "Mods"
    count = gui._extract_zip_to_folder(zip_path, dest)

    assert count == 2
    assert (dest / "111_Mon Mod" / "Mod.modinfo").exists()
    assert (dest / "111_Mon Mod" / "Text" / "fr_FR.xml").exists()
    assert (dest / "222_Autre Mod" / "Autre.modinfo").exists()
