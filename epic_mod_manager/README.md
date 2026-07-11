# Scanner de mods Civilization VI (versions installées)

Petit utilitaire qui scanne un dossier Mods de Civilization VI (typiquement
la version **Epic Games**, mais ça marche pour n'importe quelle installation)
et affiche le nom et la version locale de chaque mod installé, en lisant son
fichier `.modinfo`.

## Installation

Aucune dépendance externe requise (uniquement la bibliothèque standard de
Python).

```
python main.py
```

## Utilisation

1. Au lancement, l'application propose le chemin standard du dossier Mods
   (`Documents\My Games\Sid Meier's Civilization VI\Mods` sous Windows).
   Vérifie qu'il est correct ou choisis-en un autre avec "Choisir...".
2. Clique sur **"Scanner"** : la liste des mods installés s'affiche, avec
   leur nom et leur version locale (telle que déclarée par l'auteur dans son
   fichier `.modinfo`, ou "?" si absente).
3. Si un ami en version Steam t'a envoyé un **lien** (via "Envoyer à un ami
   (lien)..." dans son outil "Lister mes mods Civilization VI (Steam)"),
   colle-le dans le champ **"Lien reçu"** et clique sur **"Télécharger et
   installer"** : le fichier est téléchargé puis extrait automatiquement
   dans le dossier Mods, sans rien à faire de plus. Aucun compte requis de
   ton côté.
4. Si ton ami t'a envoyé une **archive .zip** directement (créée avec
   "Créer une archive (.zip)..."), clique sur **"Importer un zip..."** et
   sélectionne le fichier reçu : les mods qu'il contient sont extraits
   directement dans le dossier Mods, sans passer par le Workshop.

## Limitation

Seuls les sous-dossiers contenant un fichier `.modinfo` sont détectés. Un mod
mal installé (fichiers directement à la racine du dossier Mods, sans
sous-dossier) ne sera pas repéré.
