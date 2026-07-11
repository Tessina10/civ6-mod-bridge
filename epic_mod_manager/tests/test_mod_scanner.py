"""Tests de mod_scanner.py (parsing .modinfo, scan du dossier Mods local)."""
from pathlib import Path

import mod_scanner

MODINFO_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Mod id="{id}" version="{version}">
  <Properties>
    <Name>{name}</Name>
  </Properties>
</Mod>
"""


def _write_modinfo(path: Path, name: str, version: str = "1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MODINFO_TEMPLATE.format(id="123", version=version, name=name), encoding="utf-8")


def test_parse_modinfo_extracts_title_and_version(tmp_path):
    modinfo = tmp_path / "test.modinfo"
    _write_modinfo(modinfo, "Mon Super Mod", version="3.0")
    info = mod_scanner._parse_modinfo(modinfo)
    assert info["title"] == "Mon Super Mod"
    assert info["version"] == "3.0"


def test_parse_modinfo_ignores_raw_translation_key(tmp_path):
    modinfo = tmp_path / "test.modinfo"
    _write_modinfo(modinfo, "LOC_MOD_XXX_NAME")
    info = mod_scanner._parse_modinfo(modinfo)
    assert info["title"] is None


def test_parse_modinfo_missing_file_returns_none_fields(tmp_path):
    info = mod_scanner._parse_modinfo(tmp_path / "absent.modinfo")
    assert info == {"title": None, "version": None}


def test_scan_installed_mods_finds_modinfo_at_folder_root(tmp_path):
    mod_folder = tmp_path / "MyMod"
    _write_modinfo(mod_folder / "MyMod.modinfo", "Mon Mod", version="1.2")

    results = mod_scanner.scan_installed_mods(tmp_path)

    assert len(results) == 1
    assert results[0] == {"folder": "MyMod", "title": "Mon Mod", "version": "1.2"}


def test_scan_installed_mods_falls_back_to_nested_subfolder(tmp_path):
    mod_folder = tmp_path / "MyMod"
    _write_modinfo(mod_folder / "nested" / "MyMod.modinfo", "Mod Imbriqué")

    results = mod_scanner.scan_installed_mods(tmp_path)

    assert len(results) == 1
    assert results[0]["title"] == "Mod Imbriqué"


def test_scan_installed_mods_skips_folders_without_modinfo(tmp_path):
    (tmp_path / "NotAMod").mkdir()

    results = mod_scanner.scan_installed_mods(tmp_path)

    assert results == []


def test_scan_installed_mods_uses_folder_name_and_question_mark_as_fallback(tmp_path):
    mod_folder = tmp_path / "MyMod"
    mod_folder.mkdir()
    (mod_folder / "MyMod.modinfo").write_text("<Mod/>", encoding="utf-8")

    results = mod_scanner.scan_installed_mods(tmp_path)

    assert results[0]["title"] == "MyMod"
    assert results[0]["version"] == "?"


def test_scan_installed_mods_missing_folder_returns_empty_list():
    assert mod_scanner.scan_installed_mods(Path("does/not/exist")) == []
