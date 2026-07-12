"""Onglet "Envoyer" : scanner les mods Steam Workshop et les envoyer à un ami
via un lien Pixeldrain (ou via les méthodes de partage manuel)."""
import json
import tempfile
import time
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import config
import i18n
import mod_scanner
import steam_locator
import workers
from progress_dialog import ProgressDialog
from settings_dialog import SettingsDialog
from uploads_manager import UploadsManagerDialog


class SendTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.content_folder: Path | None = None
        self.mods_data: list[dict] = []
        self._archive_worker: workers.CreateArchiveWorker | None = None
        self._send_worker: workers.SendLinkWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._background_active = False

        self._build_ui()
        self._auto_detect()
        self._update_api_key_banner()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Bouton "Options avancées" en tout premier, juste sous la barre d'onglets.
        advanced_row = QHBoxLayout()
        self.advanced_button = QPushButton(i18n.tr("menu.advanced"))
        self.advanced_menu = QMenu(self)
        self._populate_advanced_menu()
        self.advanced_button.setMenu(self.advanced_menu)
        advanced_row.addWidget(self.advanced_button)
        advanced_row.addStretch()
        layout.addLayout(advanced_row)

        banner_row = QHBoxLayout()
        self.api_key_banner_label = QLabel(i18n.tr("send.api_key_banner"))
        self.api_key_banner_label.setWordWrap(True)
        banner_row.addWidget(self.api_key_banner_label, stretch=1)
        self.api_key_banner_button = QPushButton(i18n.tr("send.api_key_banner_button"))
        self.api_key_banner_button.clicked.connect(self.open_settings_dialog)
        banner_row.addWidget(self.api_key_banner_button)
        layout.addLayout(banner_row)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(i18n.tr("send.workshop_folder_label")))
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        top_row.addWidget(self.folder_edit, stretch=1)
        self.choose_button = QPushButton(i18n.tr("send.choose_manually"))
        self.choose_button.clicked.connect(self._choose_manual_folder)
        top_row.addWidget(self.choose_button)
        layout.addLayout(top_row)

        action_row = QHBoxLayout()
        self.scan_button = QPushButton(i18n.tr("send.scan"))
        self.scan_button.clicked.connect(self._scan)
        action_row.addWidget(self.scan_button)
        self.send_link_button = QPushButton(i18n.tr("send.send_link"))
        bold_font = QFont()
        bold_font.setBold(True)
        self.send_link_button.setFont(bold_font)
        self.send_link_button.clicked.connect(self._send_link)
        # Désactivé tant qu'aucun scan n'a produit de mods à envoyer, pour guider
        # l'ordre des étapes plutôt que de laisser cliquer puis afficher une erreur.
        self.send_link_button.setEnabled(False)
        action_row.addWidget(self.send_link_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [i18n.tr("send.table_title"), i18n.tr("send.table_id"), i18n.tr("send.table_version")]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.tree, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _auto_detect(self):
        folders = steam_locator.find_workshop_content_folders()
        if folders:
            self.content_folder = folders[0]
            self.folder_edit.setText(str(self.content_folder))
            if len(folders) > 1:
                self.status_label.setText(i18n.tr("send.status_auto_multi", count=len(folders)))
            else:
                self.status_label.setText(i18n.tr("send.status_auto_single"))
        else:
            self.status_label.setText(i18n.tr("send.status_auto_not_found"))

    def _choose_manual_folder(self):
        folder = QFileDialog.getExistingDirectory(self, i18n.tr("send.choose_dialog_title"))
        if folder:
            self.content_folder = Path(folder)
            self.folder_edit.setText(folder)
            self.status_label.setText(i18n.tr("send.status_manual_set"))
            # Le dossier a changé : les mods déjà scannés ne sont plus valables,
            # il faut rescanner avant de pouvoir envoyer à nouveau.
            self.mods_data = []
            self.tree.clear()
            self.send_link_button.setEnabled(False)

    def _scan(self):
        if not self.content_folder or not self.content_folder.exists():
            QMessageBox.critical(self, i18n.tr("common.error"), i18n.tr("send.no_valid_folder"))
            return
        self.mods_data = mod_scanner.scan_workshop_mods(self.content_folder)
        self.tree.clear()
        for mod in self.mods_data:
            self.tree.addTopLevelItem(
                QTreeWidgetItem([mod["title"], mod["id"], mod["version"] or "?"])
            )
        self.status_label.setText(i18n.tr("send.status_scan_result", count=len(self.mods_data)))
        self.send_link_button.setEnabled(bool(self.mods_data))

    def _set_controls_enabled(self, enabled: bool):
        self.choose_button.setEnabled(enabled)
        self.send_link_button.setEnabled(enabled and bool(self.mods_data))

    # --- État "continue en arrière-plan" -----------------------------------------

    def _on_continued_in_background(self):
        self._background_active = True
        self._on_background_message_changed(self._progress_dialog.current_message())

    def _on_background_message_changed(self, message: str):
        if self._background_active:
            self.status_label.setText(i18n.tr("progress.background_status", message=message))

    # --- Menu "Options avancées" ------------------------------------------------

    def _populate_advanced_menu(self):
        pixeldrain_menu = self.advanced_menu.addMenu(i18n.tr("menu.pixeldrain"))
        pixeldrain_menu.addAction(i18n.tr("menu.pixeldrain.api_key"), self.open_settings_dialog)
        pixeldrain_menu.addAction(i18n.tr("menu.pixeldrain.manage_uploads"), self._open_uploads_manager)

        self.advanced_menu.addSeparator()
        manual_menu = self.advanced_menu.addMenu(i18n.tr("menu.manual_sharing"))
        manual_menu.addAction(i18n.tr("menu.manual_sharing.export_json"), self.export_json)
        manual_menu.addAction(i18n.tr("menu.manual_sharing.copy_links"), self.copy_workshop_links)
        manual_menu.addAction(i18n.tr("menu.manual_sharing.create_archive"), self.create_archive)

    def _update_api_key_banner(self):
        has_key = bool(config.load_api_key())
        self.api_key_banner_label.setVisible(not has_key)
        self.api_key_banner_button.setVisible(not has_key)

    def open_settings_dialog(self) -> str | None:
        dialog = SettingsDialog(self)
        result = config.load_api_key() if dialog.exec() else None
        self._update_api_key_banner()
        return result

    def ensure_api_key(self) -> str | None:
        key = config.load_api_key()
        if key:
            return key
        QMessageBox.information(self, i18n.tr("common.info"), i18n.tr("settings.required_info"))
        return self.open_settings_dialog()

    def _open_uploads_manager(self):
        api_key = self.ensure_api_key()
        if not api_key:
            return
        dialog = UploadsManagerDialog(self, api_key)
        dialog.exec()

    def export_json(self):
        if not self.mods_data:
            QMessageBox.information(self, i18n.tr("common.info"), i18n.tr("send.no_scan_yet"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("send.export_dialog_title"), "civ6_mods_export.json", "JSON (*.json)"
        )
        if not path:
            return
        payload = {
            "exported_at": time.time(),
            "mods": [{"id": m["id"], "title": m["title"]} for m in self.mods_data],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.critical(self, i18n.tr("common.error"), i18n.tr("send.export_error", error=str(exc)))
            return
        QMessageBox.information(self, i18n.tr("send.export_done_title"), i18n.tr("send.export_done_message", path=path))

    def copy_workshop_links(self):
        if not self.mods_data:
            QMessageBox.information(self, i18n.tr("common.info"), i18n.tr("send.no_scan_yet"))
            return
        text = "\n".join(
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={m['id']}" for m in self.mods_data
        )
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, i18n.tr("send.copy_done_title"), i18n.tr("send.copy_done_message"))

    def create_archive(self):
        if not self.mods_data:
            QMessageBox.information(self, i18n.tr("common.info"), i18n.tr("send.no_scan_yet"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("send.archive_dialog_title"), "civ6_mods_pour_ami.zip", "ZIP (*.zip)"
        )
        if not path:
            return

        mods_data = list(self.mods_data)
        self._set_controls_enabled(False)
        self._background_active = False
        self._progress_dialog = ProgressDialog(
            self, i18n.tr("send.archive_progress_title"), i18n.tr("send.compressing")
        )
        self._progress_dialog.continued_in_background.connect(self._on_continued_in_background)
        self._progress_dialog.message_changed.connect(self._on_background_message_changed)
        self._archive_worker = workers.CreateArchiveWorker(Path(path), mods_data)
        self._archive_worker.progress.connect(self._progress_dialog.set_progress)
        self._archive_worker.succeeded.connect(lambda p: self._on_archive_succeeded(p, len(mods_data)))
        self._archive_worker.failed.connect(self._on_archive_failed)
        self._progress_dialog.show()
        self._archive_worker.start()

    def _on_archive_succeeded(self, path: str, count: int):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText(i18n.tr("send.archive_done_status", path=path))
        QMessageBox.information(
            self, i18n.tr("send.archive_done_title"), i18n.tr("send.archive_done_message", count=count, path=path)
        )

    def _on_archive_failed(self, message: str):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText("")
        QMessageBox.critical(self, i18n.tr("common.error"), i18n.tr("send.archive_error", error=message))

    # --- Flux principal : envoi par lien ---------------------------------------

    def _send_link(self):
        if not self.mods_data:
            QMessageBox.information(self, i18n.tr("common.info"), i18n.tr("send.no_scan_yet"))
            return
        api_key = self.ensure_api_key()
        if not api_key:
            return

        mods_data = list(self.mods_data)
        tmp_path = Path(tempfile.gettempdir()) / f"civ6_mods_pour_ami_{int(time.time())}.zip"
        self._set_controls_enabled(False)
        self._background_active = False
        self._progress_dialog = ProgressDialog(self, i18n.tr("send.link_progress_title"), i18n.tr("send.compressing"))
        self._progress_dialog.continued_in_background.connect(self._on_continued_in_background)
        self._progress_dialog.message_changed.connect(self._on_background_message_changed)
        self._send_worker = workers.SendLinkWorker(tmp_path, mods_data, api_key)
        self._send_worker.progress.connect(self._progress_dialog.set_progress)
        self._send_worker.phase_changed.connect(self._on_send_phase_changed)
        self._send_worker.succeeded.connect(lambda link: self._on_send_succeeded(link, len(mods_data)))
        self._send_worker.failed.connect(lambda msg: self._on_send_failed(msg, tmp_path))
        self._progress_dialog.show()
        self._send_worker.start()

    def _on_send_phase_changed(self, phase: str):
        if phase == "uploading":
            self._progress_dialog.set_indeterminate()
            self._progress_dialog.set_message(i18n.tr("send.uploading"))

    def _on_send_succeeded(self, link: str, count: int):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText(i18n.tr("send.link_done_status", count=count))
        self._show_link_dialog(link)

    def _on_send_failed(self, message: str, tmp_path: Path):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText("")
        QMessageBox.critical(
            self, i18n.tr("common.error"), i18n.tr("send.link_error", error=message, path=str(tmp_path))
        )

    def _show_link_dialog(self, link: str):
        from link_dialog import LinkDialog
        dialog = LinkDialog(self, link)
        dialog.exec()
