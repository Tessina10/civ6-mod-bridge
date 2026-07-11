# Lister mes mods Civilization VI (Steam)

Petit utilitaire à exécuter **sur le PC qui a la version Steam** de
Civilization VI. Il scanne les mods souscrits via le Steam Workshop et
permet d'en exporter la liste (ou de la copier) pour la transmettre à un
ami qui a la version Epic Games — celui-ci pourra ensuite l'importer
directement dans son "Gestionnaire de mods Civilization VI (Epic Games)".

## Pourquoi ce dossier spécifique ?

Sous Steam, les mods souscrits via le Workshop ne sont **pas** copiés dans
`Documents/My Games/.../Mods` : ils restent dans la bibliothèque Steam, à
l'emplacement :
```
<bibliothèque Steam>/steamapps/workshop/content/289070/<id_du_mod>/
```
C'est ce dossier que cet outil recherche et scanne automatiquement.

## Installation

Aucune dépendance externe requise (uniquement la bibliothèque standard de
Python).

```
python main.py
```

## Utilisation

1. Au lancement, l'application tente de détecter automatiquement le
   dossier Workshop de Civ VI (via le registre Windows / les emplacements
   Steam par défaut, en tenant compte de plusieurs bibliothèques Steam
   si tu en as plusieurs sur des disques différents). Si la détection
   échoue, clique sur "Choisir manuellement..." et navigue jusqu'à
   `.../steamapps/workshop/content/289070`.

2. Clique sur **"Scanner"** : la liste de tes mods installés s'affiche
   avec leur nom, leur ID Workshop et leur version locale (si l'auteur du
   mod l'a renseignée dans son fichier `.modinfo`).

3. Pour transmettre les mods à ton ami, plusieurs options :
   - **"Envoyer à un ami (lien)..."** *(recommandé)* : zippe les mods
     scannés, les envoie automatiquement sur [Pixeldrain](https://pixeldrain.com)
     (hébergement gratuit) et affiche un lien à copier-coller. Ton ami n'a
     plus qu'à coller ce lien dans le champ "Lien reçu" de son application
     et cliquer sur "Télécharger et installer" : tout le téléchargement,
     l'extraction et le rangement se font automatiquement, sans fichier à
     s'échanger à la main. Nécessite une clé API Pixeldrain gratuite (voir
     "Configurer l'envoi par lien" ci-dessous).
   - **"Créer une archive (.zip)..."** : zippe directement les dossiers de
     tous les mods scannés (chacun renommé `<id>_<titre>` pour éviter les
     collisions) dans un seul fichier `.zip` à envoyer à ton ami toi-même
     (mail, Discord, clé USB...). Celui-ci pourra cliquer sur "Importer un
     zip..." dans son application pour l'extraire. Utile si tu préfères ne
     pas passer par un hébergeur tiers, ou en secours si Pixeldrain est
     indisponible.
   - **"Exporter vers fichier..."** : crée un fichier `.json` à envoyer à
     ton ami avec la liste (id + titre) de tes mods.
   - **"Copier la liste"** : copie une liste de liens Steam Workshop dans
     le presse-papiers, à coller directement dans le champ
     "Ajouter plusieurs..." de son application (pratique pour un simple
     copier-coller via un message).

## Configurer l'envoi par lien (Pixeldrain)

1. Crée un compte gratuit sur https://pixeldrain.com (bouton "Register").
2. Une fois connecté, va sur https://pixeldrain.com/user/api_keys et
   génère une clé API.
3. Clique sur **"Paramètres..."** dans l'application, colle la clé, puis
   "Enregistrer". Elle est stockée localement (pas besoin de la ressaisir
   au prochain lancement) et n'est utilisée que pour l'upload — ton ami
   n'a besoin d'aucun compte pour télécharger.
4. Les fichiers envoyés via Pixeldrain sont conservés 60 jours (le délai
   est prolongé à chaque téléchargement), jusqu'à 20 Go par fichier en
   version gratuite.

## Limitation

Seuls les mods réellement souscrits via le Steam Workshop sont détectés
(ceux avec un ID numérique). Un mod installé manuellement (fichiers copiés
à la main, sans passer par le Workshop) n'a pas d'ID Workshop et ne peut
donc pas être transmis par cet outil.
