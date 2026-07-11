"""Tests de mod_scanner.py (parsing .modinfo, scan du dossier Workshop)."""
from pathlib import Path

import mod_scanner

MODINFO_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Mod id="{id}" version="{version}">
  <Properties>
    <Name>{name}</Name>
  </Properties>
</Mod>
"""


def _write_modinfo(folder: Path, name: str, version: str = "1") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "test.modinfo").write_text(
        MODINFO_TEMPLATE.format(id="123", version=version, name=name), encoding="utf-8"
    )


def test_parse_modinfo_extracts_title_and_version(tmp_path):
    _write_modinfo(tmp_path, "Mon Super Mod", version="2.1")
    info = mod_scanner._parse_modinfo(tmp_path)
    assert info["title"] == "Mon Super Mod"
    assert info["version"] == "2.1"


def test_parse_modinfo_ignores_raw_translation_key(tmp_path):
    _write_modinfo(tmp_path, "LOC_MOD_XXX_NAME")
    info = mod_scanner._parse_modinfo(tmp_path)
    assert info["title"] is None


def test_parse_modinfo_missing_file_returns_none_fields(tmp_path):
    info = mod_scanner._parse_modinfo(tmp_path)
    assert info == {"title": None, "version": None}


def test_scan_workshop_mods_uses_folder_name_as_id(tmp_path):
    mod_folder = tmp_path / "2859491234"
    _write_modinfo(mod_folder, "Un Mod Workshop", version="1.0")
    (tmp_path / "not_a_mod_id").mkdir()  # dossier non numérique, doit être ignoré

    results = mod_scanner.scan_workshop_mods(tmp_path)

    assert len(results) == 1
    mod = results[0]
    assert mod["id"] == "2859491234"
    assert mod["title"] == "Un Mod Workshop"
    assert mod["version"] == "1.0"


def test_scan_workshop_mods_falls_back_to_id_when_no_title(tmp_path):
    mod_folder = tmp_path / "42"
    mod_folder.mkdir()

    results = mod_scanner.scan_workshop_mods(tmp_path)

    assert results[0]["title"] == "42"


def test_scan_workshop_mods_missing_folder_returns_empty_list():
    assert mod_scanner.scan_workshop_mods(Path("does/not/exist")) == []
