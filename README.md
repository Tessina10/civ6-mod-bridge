# Civ 6 Mod Manager

Deux petits outils complémentaires pour partager et installer des mods
Civilization VI entre un ami en version **Steam** et un ami en version
**Epic Games**.

## [steam_lister/](steam_lister/) — "Lister mes mods Civilization VI (Steam)"

À exécuter sur le PC qui a la version **Steam**. Scanne les mods souscrits
via le Steam Workshop et permet de les envoyer automatiquement à un ami en
version Epic Games via un simple lien (upload sur Pixeldrain), ou de zipper
les fichiers manuellement / d'exporter une liste JSON / des liens Workshop
à transmettre soi-même.

## [epic_mod_manager/](epic_mod_manager/) — "Scanner de mods (versions installées)"

À exécuter sur n'importe quelle installation (Epic Games ou Steam). Scanne
le dossier Mods du jeu et affiche le nom et la version locale de chaque mod
déjà installé, en lisant son fichier `.modinfo`. Permet de coller le lien
reçu de `steam_lister` pour télécharger et installer les mods
automatiquement, ou d'importer directement une archive `.zip` reçue à la
main.

Note : le téléchargement automatique via SteamCMD a été abandonné — le
Workshop de Civilization VI nécessite une clé de déchiffrement liée à un
compte Steam possédant réellement le jeu, ce qui rend le login anonyme
inutilisable pour ce jeu.

Voir le README de chaque dossier pour les instructions détaillées.

## Développement

Aucune dépendance runtime (stdlib Python uniquement). Les dépendances de dev
(lint, tests, build) sont listées dans `requirements-dev.txt` :

```
pip install -r requirements-dev.txt
ruff check .                          # lint
cd steam_lister && pytest             # tests de steam_lister
cd epic_mod_manager && pytest         # tests de epic_mod_manager
```

Voir `CLAUDE.md` pour le détail de l'architecture et des conventions.

## Licence

Ce projet est distribué sous licence [MIT](LICENSE) : utilisation, modification
et redistribution libres (y compris commerciales), à condition de conserver la
mention de copyright d'origine.
