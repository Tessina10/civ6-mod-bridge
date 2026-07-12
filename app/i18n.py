"""Internationalisation minimale : dictionnaire de traductions FR/EN (pas de
toolchain Qt Linguist, volontairement simple pour 2 langues maintenues en solo)."""
from typing import Optional

from PySide6.QtCore import QLocale

import config

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("fr", "en")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "fr": {
        "app.title": "Civ6 Mod Bridge",
        "tab.send": "Envoyer",
        "tab.receive": "Recevoir",
        "menu.advanced": "Options avancées",
        "menu.pixeldrain": "Pixeldrain",
        "menu.pixeldrain.api_key": "Clé API...",
        "menu.pixeldrain.manage_uploads": "Gérer mes envois...",
        "menu.manual_sharing": "Partage manuel",
        "menu.manual_sharing.export_json": "Exporter en JSON...",
        "menu.manual_sharing.copy_links": "Copier les liens Workshop",
        "menu.manual_sharing.create_archive": "Créer une archive .zip...",
        "common.cancel": "Annuler",
        "common.close": "Fermer",
        "common.save": "Enregistrer",
        "common.error": "Erreur",
        "common.info": "Info",
        "send.workshop_folder_label": "Dossier Workshop détecté :",
        "send.choose_manually": "Choisir manuellement...",
        "send.choose_dialog_title": "Choisir le dossier steamapps/workshop/content/289070",
        "send.status_manual_set": "Dossier défini manuellement. Clique sur 'Scanner'.",
        "send.scan": "Scanner",
        "send.send_link": "Envoyer à un ami (lien)...",
        "send.table_title": "Nom du mod",
        "send.table_id": "ID Workshop",
        "send.table_version": "Version locale",
        "send.status_auto_multi": (
            "{count} bibliothèques Steam contiennent des mods Civ VI ; la première a été sélectionnée."
        ),
        "send.status_auto_single": "Dossier détecté automatiquement. Clique sur 'Scanner'.",
        "send.status_auto_not_found": (
            "Dossier Workshop introuvable automatiquement. Utilise 'Choisir manuellement...'."
        ),
        "send.no_valid_folder": "Aucun dossier Workshop valide sélectionné.",
        "send.status_scan_result": "{count} mod(s) trouvé(s).",
        "send.no_scan_yet": "Lance d'abord un scan.",
        "send.api_key_banner": (
            "Aucune clé Pixeldrain configurée — nécessaire pour envoyer un lien à ton ami."
        ),
        "send.api_key_banner_button": "Configurer...",
        "send.export_dialog_title": "Exporter la liste des mods",
        "send.export_error": "Impossible d'écrire le fichier : {error}",
        "send.export_done_title": "Export réussi",
        "send.export_done_message": "Liste exportée vers :\n{path}",
        "send.copy_done_title": "Copié",
        "send.copy_done_message": "La liste des liens Workshop a été copiée dans le presse-papiers.",
        "send.archive_dialog_title": "Créer une archive à envoyer à ton ami",
        "send.archive_progress_title": "Création de l'archive",
        "send.compressing": "Compression des mods...",
        "send.archive_done_status": "Archive créée : {path}",
        "send.archive_done_title": "Archive créée",
        "send.archive_done_message": "Archive créée avec {count} mod(s) :\n{path}",
        "send.archive_error": "Impossible de créer l'archive : {error}",
        "send.link_progress_title": "Envoi en cours",
        "send.uploading": "Envoi vers Pixeldrain en cours (durée variable selon ta connexion)...",
        "send.link_done_status": "Lien créé avec {count} mod(s).",
        "send.link_error": (
            "Impossible d'envoyer les mods : {error}\n\n"
            "L'archive temporaire a été conservée pour inspection :\n{path}"
        ),
        "link_dialog.title": "Lien créé",
        "link_dialog.message": (
            "Transmets ce lien à ton ami (Discord, message...). Il pourra le coller directement "
            "dans le champ prévu de son application pour installer les mods automatiquement."
        ),
        "link_dialog.copy": "Copier le lien",
        "settings.title": "Paramètres",
        "settings.api_key_label": "Clé API Pixeldrain (nécessaire pour envoyer un lien à ton ami) :",
        "settings.api_key_hint": "À générer gratuitement sur : {url}",
        "settings.missing_key_title": "Clé manquante",
        "settings.missing_key_message": "Merci de coller une clé API.",
        "settings.required_info": (
            "Pour envoyer un lien à ton ami, il faut d'abord renseigner une clé API Pixeldrain (gratuite)."
        ),
        "progress.background_button": "Continuer en arrière-plan",
        "progress.background_status": "{message} (toujours en cours en arrière-plan)",
        "receive.folder_label": "Dossier des mods :",
        "receive.choose_dialog_title": "Choisir le dossier Mods de Civilization VI",
        "receive.hero_instructions": "Colle ici le lien reçu de ton ami, puis clique sur Installer :",
        "receive.install_button": "Installer les mods",
        "receive.status_ready": "Dossier détecté automatiquement. Prêt à recevoir des mods.",
        "receive.status_not_found": (
            "Dossier introuvable à l'emplacement standard. Vérifie le chemin ou clique sur 'Choisir...'."
        ),
        "receive.missing_folder_title": "Dossier manquant",
        "receive.missing_folder_message": "Choisis d'abord le dossier Mods de Civilization VI.",
        "receive.invalid_link_title": "Lien invalide",
        "receive.invalid_link_message": (
            "Colle le lien complet reçu de ton ami (ou juste son identifiant Pixeldrain)."
        ),
        "receive.install_progress_title": "Installation en cours",
        "receive.downloading": "Téléchargement en cours...",
        "receive.installing": "Installation des mods...",
        "receive.done_title": "Import terminé",
        "receive.done_message": "{count} mod(s) extrait(s) dans :\n{folder}",
        "receive.done_status": "{count} mod(s) extrait(s) dans : {folder}",
        "receive.download_error": "Impossible de télécharger ou d'extraire l'archive : {error}",
        "receive.import_menu_item": "Importer un zip local...",
        "receive.import_dialog_title": "Choisir l'archive de mods reçue",
        "receive.all_files": "Tous les fichiers",
        "receive.import_progress_title": "Import en cours",
        "receive.extracting": "Extraction de l'archive...",
        "receive.import_error": "Impossible d'extraire l'archive : {error}",
        "installed.title": "Mods installés",
        "installed.col_version": "Version installée",
        "installed.menu_item": "Voir les mods installés...",
        "uploads.title": "Gérer mes envois Pixeldrain",
        "uploads.refresh": "Rafraîchir",
        "uploads.delete_selection": "Supprimer la sélection",
        "uploads.delete_all": "Tout supprimer",
        "uploads.col_name": "Nom",
        "uploads.col_size": "Taille",
        "uploads.col_date": "Date d'envoi",
        "uploads.loading": "Chargement de la liste...",
        "uploads.count": "{count} fichier(s) sur le compte.",
        "uploads.list_error": "Impossible de récupérer la liste des envois : {error}",
        "uploads.select_at_least_one": "Sélectionne au moins un fichier dans la liste.",
        "uploads.nothing_to_delete": "Aucun fichier à supprimer.",
        "uploads.confirm_title": "Confirmer la suppression",
        "uploads.confirm_delete_selection": (
            "Supprimer les {count} fichier(s) sélectionné(s) ?\n\nCette action est irréversible."
        ),
        "uploads.confirm_delete_all": (
            "Supprimer TOUS les fichiers envoyés ({count}) ?\n\nCette action est irréversible."
        ),
        "uploads.deleting_title": "Suppression en cours",
        "uploads.deleting_message": "Suppression de {count} fichier(s)...",
        "uploads.delete_done_title": "Suppression terminée",
        "uploads.delete_done_all": "{succeeded} fichier(s) supprimé(s).",
        "uploads.delete_done_partial": "{succeeded} fichier(s) supprimé(s), {failed} échec(s).",
    },
    "en": {
        "app.title": "Civ6 Mod Bridge",
        "tab.send": "Send",
        "tab.receive": "Receive",
        "menu.advanced": "Advanced options",
        "menu.pixeldrain": "Pixeldrain",
        "menu.pixeldrain.api_key": "API key...",
        "menu.pixeldrain.manage_uploads": "Manage my uploads...",
        "menu.manual_sharing": "Manual sharing",
        "menu.manual_sharing.export_json": "Export as JSON...",
        "menu.manual_sharing.copy_links": "Copy Workshop links",
        "menu.manual_sharing.create_archive": "Create a .zip archive...",
        "common.cancel": "Cancel",
        "common.close": "Close",
        "common.save": "Save",
        "common.error": "Error",
        "common.info": "Info",
        "send.workshop_folder_label": "Detected Workshop folder:",
        "send.choose_manually": "Choose manually...",
        "send.choose_dialog_title": "Choose the steamapps/workshop/content/289070 folder",
        "send.status_manual_set": "Folder set manually. Click 'Scan'.",
        "send.scan": "Scan",
        "send.send_link": "Send to a friend (link)...",
        "send.table_title": "Mod name",
        "send.table_id": "Workshop ID",
        "send.table_version": "Local version",
        "send.status_auto_multi": (
            "{count} Steam libraries contain Civ VI mods; the first one was selected."
        ),
        "send.status_auto_single": "Folder detected automatically. Click 'Scan'.",
        "send.status_auto_not_found": (
            "Workshop folder not found automatically. Use 'Choose manually...'."
        ),
        "send.no_valid_folder": "No valid Workshop folder selected.",
        "send.status_scan_result": "{count} mod(s) found.",
        "send.no_scan_yet": "Run a scan first.",
        "send.api_key_banner": (
            "No Pixeldrain API key configured — needed to send a link to your friend."
        ),
        "send.api_key_banner_button": "Configure...",
        "send.export_dialog_title": "Export mod list",
        "send.export_error": "Could not write the file: {error}",
        "send.export_done_title": "Export successful",
        "send.export_done_message": "List exported to:\n{path}",
        "send.copy_done_title": "Copied",
        "send.copy_done_message": "The list of Workshop links was copied to the clipboard.",
        "send.archive_dialog_title": "Create an archive to send to your friend",
        "send.archive_progress_title": "Creating archive",
        "send.compressing": "Compressing mods...",
        "send.archive_done_status": "Archive created: {path}",
        "send.archive_done_title": "Archive created",
        "send.archive_done_message": "Archive created with {count} mod(s):\n{path}",
        "send.archive_error": "Could not create the archive: {error}",
        "send.link_progress_title": "Sending",
        "send.uploading": "Uploading to Pixeldrain (duration varies with your connection)...",
        "send.link_done_status": "Link created with {count} mod(s).",
        "send.link_error": (
            "Could not send the mods: {error}\n\nThe temporary archive was kept for inspection:\n{path}"
        ),
        "link_dialog.title": "Link created",
        "link_dialog.message": (
            "Send this link to your friend (Discord, message...). They can paste it directly "
            "into the field of their app to install the mods automatically."
        ),
        "link_dialog.copy": "Copy link",
        "settings.title": "Settings",
        "settings.api_key_label": "Pixeldrain API key (needed to send a link to your friend):",
        "settings.api_key_hint": "Generate one for free at: {url}",
        "settings.missing_key_title": "Missing key",
        "settings.missing_key_message": "Please paste an API key.",
        "settings.required_info": (
            "To send a link to your friend, you first need to set up a free Pixeldrain API key."
        ),
        "progress.background_button": "Continue in background",
        "progress.background_status": "{message} (still running in the background)",
        "receive.folder_label": "Mods folder:",
        "receive.choose_dialog_title": "Choose the Civilization VI Mods folder",
        "receive.hero_instructions": "Paste the link you received from your friend here, then click Install:",
        "receive.install_button": "Install mods",
        "receive.status_ready": "Folder detected automatically. Ready to receive mods.",
        "receive.status_not_found": (
            "Folder not found at the standard location. Check the path or click 'Choose...'."
        ),
        "receive.missing_folder_title": "Missing folder",
        "receive.missing_folder_message": "Choose the Civilization VI Mods folder first.",
        "receive.invalid_link_title": "Invalid link",
        "receive.invalid_link_message": (
            "Paste the full link you received from your friend (or just its Pixeldrain ID)."
        ),
        "receive.install_progress_title": "Installing",
        "receive.downloading": "Downloading...",
        "receive.installing": "Installing mods...",
        "receive.done_title": "Import complete",
        "receive.done_message": "{count} mod(s) extracted to:\n{folder}",
        "receive.done_status": "{count} mod(s) extracted to: {folder}",
        "receive.download_error": "Could not download or extract the archive: {error}",
        "receive.import_menu_item": "Import a local zip...",
        "receive.import_dialog_title": "Choose the received mod archive",
        "receive.all_files": "All files",
        "receive.import_progress_title": "Importing",
        "receive.extracting": "Extracting archive...",
        "receive.import_error": "Could not extract the archive: {error}",
        "installed.title": "Installed mods",
        "installed.col_version": "Installed version",
        "installed.menu_item": "View installed mods...",
        "uploads.title": "Manage my Pixeldrain uploads",
        "uploads.refresh": "Refresh",
        "uploads.delete_selection": "Delete selection",
        "uploads.delete_all": "Delete all",
        "uploads.col_name": "Name",
        "uploads.col_size": "Size",
        "uploads.col_date": "Upload date",
        "uploads.loading": "Loading the list...",
        "uploads.count": "{count} file(s) on the account.",
        "uploads.list_error": "Could not retrieve the upload list: {error}",
        "uploads.select_at_least_one": "Select at least one file in the list.",
        "uploads.nothing_to_delete": "No file to delete.",
        "uploads.confirm_title": "Confirm deletion",
        "uploads.confirm_delete_selection": (
            "Delete the {count} selected file(s)?\n\nThis action is irreversible."
        ),
        "uploads.confirm_delete_all": (
            "Delete ALL uploaded files ({count})?\n\nThis action is irreversible."
        ),
        "uploads.deleting_title": "Deleting",
        "uploads.deleting_message": "Deleting {count} file(s)...",
        "uploads.delete_done_title": "Deletion complete",
        "uploads.delete_done_all": "{succeeded} file(s) deleted.",
        "uploads.delete_done_partial": "{succeeded} file(s) deleted, {failed} failure(s).",
    },
}

_current_language: Optional[str] = None


def detect_system_language() -> str:
    """Détecte la langue du système via Qt ; repli sur l'anglais si non supportée."""
    name = QLocale.system().name()  # ex. "fr_FR", "en_US"
    lang = name.split("_")[0].lower() if name else ""
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def current_language() -> str:
    global _current_language
    if _current_language is None:
        saved = config.load_language()
        _current_language = saved if saved in SUPPORTED_LANGUAGES else detect_system_language()
    return _current_language


def set_language(language: str) -> None:
    global _current_language
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Langue non supportée : {language}")
    _current_language = language
    config.save_language(language)


def tr(key: str, **kwargs) -> str:
    """Traduit `key` dans la langue courante. Repli sur l'anglais puis sur la clé
    elle-même si absente, pour ne jamais planter sur une traduction manquante."""
    lang_dict = TRANSLATIONS.get(current_language(), {})
    text = lang_dict.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
