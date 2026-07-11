# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Deux outils Tkinter indépendants (aucune dépendance externe, stdlib Python
uniquement — y compris pour les appels réseau, via `urllib`) pour partager
des mods Civilization VI entre un ami en version **Steam** et un ami en
version **Epic Games**. Flux principal : upload automatique vers
[Pixeldrain](https://pixeldrain.com) et transmission d'un simple lien ; en
secours, transfert manuel via fichier JSON / presse-papiers / archive `.zip`
que les utilisateurs s'échangent eux-mêmes (mail, Discord, clé USB...).

- `steam_lister/` — tourne côté Steam, scanne le Workshop, upload une
  archive vers Pixeldrain et affiche le lien (ou produit une liste/archive
  locale à envoyer soi-même).
- `epic_mod_manager/` — tourne sur n'importe quelle installation, scanne le
  dossier Mods local, télécharge+installe depuis un lien reçu (ou importe
  une archive locale).

Voir `README.md` (racine) et le README de chaque sous-dossier pour le détail
utilisateur.

## Commandes

Chaque outil est un mini-projet Python autonome, à lancer depuis son propre
dossier (pas de venv/requirements pour l'exécution — stdlib only) :

```
cd steam_lister && python main.py
cd epic_mod_manager && python main.py
```

Build de l'exécutable Windows (PyInstaller, déjà configuré via le `.spec` de
chaque dossier) :

```
cd steam_lister && pyinstaller Civ6ModLister.spec
cd epic_mod_manager && pyinstaller Civ6ModScanner.spec
```

Les binaires sont produits dans `dist/` de chaque dossier.

### Dev : dépendances, lint, tests

Les dépendances de dev (ruff, pytest, pre-commit, pyinstaller) sont listées
dans `requirements-dev.txt` à la racine — installation globale ou dans un
venv au choix, pas de convention imposée (`pip install -r requirements-dev.txt`).

Lint (config dans le `pyproject.toml` racine, règles par défaut ruff, pas de
`ruff format` pour ne pas reformater tout le style existant) :

```
ruff check .
```

Un hook pre-commit (`.pre-commit-config.yaml`, installé via `pre-commit
install`) bloque un commit si `ruff check` échoue.

Tests (pytest) : chaque outil a sa propre suite dans `<dossier>/tests/`, à
lancer **depuis le dossier de l'outil** (pas depuis la racine — voir
ci-dessous) :

```
cd steam_lister && pytest
cd epic_mod_manager && pytest
```

Les tests couvrent uniquement la logique pure et locale : parsing des
`.modinfo` (`mod_scanner.py`), `_extract_pixeldrain_id()` et
`_extract_zip_to_folder()` côté `epic_mod_manager`, `_sanitize_folder_name()`
et `_write_mods_zip()` côté `steam_lister`. Pas de mock du réseau Pixeldrain
réel (pas de clé API en CI) : le flux d'upload/téléchargement n'est pas
testé automatiquement.

⚠️ `steam_lister/mod_scanner.py` et `epic_mod_manager/mod_scanner.py` (idem
pour `gui.py`) portent le **même nom de module** dans deux dossiers
distincts (duplication volontaire, voir plus bas). Chaque `tests/conftest.py`
insère uniquement le dossier de son propre outil dans `sys.path` : lancer
`pytest` à la racine du dépôt collecterait les deux suites dans le même
process et provoquerait des collisions d'import silencieuses. Toujours
lancer les tests dossier par dossier.

## Architecture

Les deux outils suivent la même structure à 3 couches, sans code partagé
entre les deux dossiers (duplication volontaire, chacun reste un exécutable
autonome) :

- `main.py` — point d'entrée trivial, appelle `gui.main()`.
- `gui.py` — classe `App(tk.Tk)` : toute l'UI Tkinter/ttk et les handlers de
  boutons. Les opérations lentes (zip/dézip) tournent dans un
  `threading.Thread` et repassent sur le thread UI via `self.after(0, ...)`
  pour ne pas geler la fenêtre. ⚠️ Piège Python à connaître pour ce motif :
  dans un bloc `except E as exc:`, Python supprime automatiquement `exc` à
  la sortie du bloc. Une closure `def failed(): ...` définie *dans* le bloc
  et planifiée via `self.after(0, failed)` capture `exc` par référence, donc
  `exc` n'existe plus au moment où `failed()` s'exécute réellement
  (`NameError`). Toujours capturer le message dans une variable normale
  d'abord (`error_message = str(exc)`) avant de la fermer dans la closure —
  corrigé aux 4 endroits concernés lors de la mise en place du lint (ruff
  l'a détecté via F821/F841).
- `mod_scanner.py` — lecture des `.modinfo` (XML) : extrait `title`
  (`./Properties/Name`, en ignorant les clés de traduction brutes `LOC_...`)
  et `version` (attribut `version` de la racine).

Spécificité `steam_lister/` : `steam_locator.py` localise le dossier
Workshop Steam de Civ VI (`steamapps/workshop/content/289070`) — priorité au
registre Windows (`HKCU/HKLM ...\Valve\Steam`), sinon chemins par défaut
par OS ; lit aussi `libraryfolders.vdf` pour couvrir les bibliothèques Steam
sur plusieurs disques.

Partage par lien (Pixeldrain), uniquement côté `steam_lister/` — le
téléchargement côté `epic_mod_manager/` n'a besoin d'aucune clé :
- `config.py` — lit/écrit la clé API Pixeldrain dans
  `%APPDATA%/Civ6ModManager/steam_lister_config.json` (fallback
  `Path.home()` hors Windows).
- `pixeldrain_client.py` — `upload_file(path, api_key)` : `PUT` vers
  `https://pixeldrain.com/api/file/` en Basic Auth (`:<api_key>` encodé en
  base64), retourne le lien direct `https://pixeldrain.com/api/file/<id>`.
  Lève `PixeldrainError` sur échec (401 = clé invalide, erreur réseau...).

Côté `epic_mod_manager/gui.py`, pas de module dédié : `_extract_pixeldrain_id()`
parse l'ID depuis un lien complet ou un ID brut (regex), et le téléchargement
se fait par blocs (`urllib.request` + boucle `.read(1 Mo)`) vers un fichier
temporaire avant extraction — pas de chargement de l'archive en mémoire.

### Différence structurelle entre les deux `mod_scanner.py`

Ce sont deux fichiers distincts, pas un module partagé :
- `steam_lister/mod_scanner.py` : scanne un dossier Workshop, où **chaque
  sous-dossier numérique = un ID Workshop** (le nom du dossier fait foi).
- `epic_mod_manager/mod_scanner.py` : scanne un dossier Mods classique, où
  le `.modinfo` peut être à la racine du sous-dossier du mod **ou dans un
  sous-sous-dossier** (`child.glob("*.modinfo")` puis fallback
  `child.glob("*/*.modinfo")`).

### Flux de partage entre les deux outils

1. **Lien Pixeldrain** *(flux recommandé, complet et automatique)* :
   `steam_lister._send_link()` zippe les mods scannés dans un fichier
   temporaire (`_write_mods_zip()`, partagé avec `_create_archive()`),
   l'upload via `pixeldrain_client.upload_file()`, affiche le lien obtenu ;
   `epic_mod_manager._download_and_install()` télécharge ce lien et appelle
   `_extract_zip_to_folder()` (partagé avec `_import_zip()`) pour installer
   directement dans le dossier Mods.
2. **Archive .zip locale** (fonctionnel dans les deux sens, sans réseau) :
   `steam_lister._create_archive()` zippe chaque dossier de mod scanné sous
   `<id>_<titre_nettoyé>/...` vers un fichier choisi par l'utilisateur ;
   `epic_mod_manager._import_zip()` extrait une archive choisie sur le
   disque. Utile en secours si Pixeldrain est indisponible.
3. **Liste JSON** : `steam_lister` exporte `{id, title}` de chaque mod
   scanné vers un `.json`. ⚠️ `epic_mod_manager` n'a actuellement **aucun
   bouton d'import de cette liste** malgré ce que dit le texte affiché côté
   `steam_lister` ("Importer une liste" — fonctionnalité non implémentée côté
   réception, à vérifier/compléter si on retravaille ce flux).
4. **Liens presse-papiers** : `steam_lister` copie des URLs
   `steamcommunity.com/sharedfiles/filedetails/?id=<id>` — usage manuel côté
   Epic (pas d'automatisation dans `epic_mod_manager`).
