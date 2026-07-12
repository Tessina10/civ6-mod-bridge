"""Onglet "Recevoir" : installer automatiquement les mods reçus par lien, ou
importer une archive .zip locale."""
import platform
import tempfile
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import formatting
import i18n
import workers
from installed_mods_dialog import InstalledModsDialog
from progress_dialog import ProgressDialog

PIXELDRAIN_DOWNLOAD_TEMPLATE = "https://pixeldrain.com/api/file/{file_id}"


def _default_mods_folder() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path.home() / "Documents" / "My Games" / "Sid Meier's Civilization VI" / "Mods"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Sid Meier's Civilization VI" / "Mods"
    return Path.home() / "My Games" / "Sid Meier's Civilization VI" / "Mods"


class ReceiveTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._download_worker: workers.DownloadInstallWorker | None = None
        self._import_worker: workers.ImportZipWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._installed_dialog: InstalledModsDialog | None = None
        self._background_active = False

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Bouton "Options avancées" en tout premier, juste sous la barre d'onglets.
        advanced_row = QHBoxLayout()
        self.advanced_button = QPushButton(i18n.tr("menu.advanced"))
        self.advanced_menu = QMenu(self)
        self.advanced_menu.addAction(i18n.tr("installed.menu_item"), self.show_installed_mods)
        self.advanced_menu.addAction(i18n.tr("receive.import_menu_item"), self.import_zip)
        self.advanced_button.setMenu(self.advanced_menu)
        advanced_row.addWidget(self.advanced_button)
        advanced_row.addStretch()
        layout.addLayout(advanced_row)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(i18n.tr("receive.folder_label")))
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        top_row.addWidget(self.folder_edit, stretch=1)
        self.choose_button = QPushButton(i18n.tr("send.choose_manually"))
        self.choose_button.clicked.connect(self._choose_folder)
        top_row.addWidget(self.choose_button)
        layout.addLayout(top_row)

        layout.addSpacing(12)
        layout.addWidget(QLabel(i18n.tr("receive.hero_instructions")))

        self.link_edit = QLineEdit()
        layout.addWidget(self.link_edit)

        self.install_button = QPushButton(i18n.tr("receive.install_button"))
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(bold_font.pointSize() + 1)
        self.install_button.setFont(bold_font)
        self.install_button.setMinimumHeight(36)
        self.install_button.clicked.connect(self._download_and_install)
        layout.addWidget(self.install_button)

        layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _auto_detect(self):
        folder = _default_mods_folder()
        self.folder_edit.setText(str(folder))
        if folder.exists():
            self.status_label.setText(i18n.tr("receive.status_ready"))
        else:
            self.status_label.setText(i18n.tr("receive.status_not_found"))

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, i18n.tr("receive.choose_dialog_title"))
        if folder:
            self.folder_edit.setText(folder)

    def _set_controls_enabled(self, enabled: bool):
        self.choose_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)

    # --- État "continue en arrière-plan" -----------------------------------------

    def _on_continued_in_background(self):
        self._background_active = True
        self._on_background_message_changed(self._progress_dialog.current_message())

    def _on_background_message_changed(self, message: str):
        if self._background_active:
            self.status_label.setText(i18n.tr("progress.background_status", message=message))

    def _refresh_installed_dialog_if_open(self):
        if self._installed_dialog is not None and self._installed_dialog.isVisible():
            self._installed_dialog.refresh(self.folder_edit.text())

    # --- Menu "Options avancées" ------------------------------------------------

    def show_installed_mods(self):
        if self._installed_dialog is None:
            self._installed_dialog = InstalledModsDialog(self)
        self._installed_dialog.refresh(self.folder_edit.text())
        self._installed_dialog.show()
        self._installed_dialog.raise_()
        self._installed_dialog.activateWindow()

    def import_zip(self):
        folder_str = self.folder_edit.text().strip()
        if not folder_str:
            QMessageBox.critical(
                self, i18n.tr("receive.missing_folder_title"), i18n.tr("receive.missing_folder_message")
            )
            return

        zip_path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("receive.import_dialog_title"), "", "ZIP (*.zip);;" + i18n.tr("receive.all_files")
        )
        if not zip_path:
            return

        folder = Path(folder_str)
        self._set_controls_enabled(False)
        self._background_active = False
        self._progress_dialog = ProgressDialog(
            self, i18n.tr("receive.import_progress_title"), i18n.tr("receive.extracting")
        )
        self._progress_dialog.continued_in_background.connect(self._on_continued_in_background)
        self._progress_dialog.message_changed.connect(self._on_background_message_changed)
        self._import_worker = workers.ImportZipWorker(Path(zip_path), folder)
        self._import_worker.progress.connect(self._progress_dialog.set_progress)
        self._import_worker.succeeded.connect(self._on_import_succeeded)
        self._import_worker.failed.connect(self._on_import_failed)
        self._progress_dialog.show()
        self._import_worker.start()

    def _on_import_succeeded(self, count: int, folder: str):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText(i18n.tr("receive.done_status", count=count, folder=folder))
        QMessageBox.information(
            self, i18n.tr("receive.done_title"), i18n.tr("receive.done_message", count=count, folder=folder)
        )
        self._refresh_installed_dialog_if_open()

    def _on_import_failed(self, message: str):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText("")
        QMessageBox.critical(self, i18n.tr("common.error"), i18n.tr("receive.import_error", error=message))

    # --- Flux principal : installation depuis un lien ---------------------------

    def _download_and_install(self):
        folder_str = self.folder_edit.text().strip()
        if not folder_str:
            QMessageBox.critical(
                self, i18n.tr("receive.missing_folder_title"), i18n.tr("receive.missing_folder_message")
            )
            return

        file_id = formatting.extract_pixeldrain_id(self.link_edit.text())
        if not file_id:
            QMessageBox.critical(self, i18n.tr("receive.invalid_link_title"), i18n.tr("receive.invalid_link_message"))
            return

        folder = Path(folder_str)
        download_url = PIXELDRAIN_DOWNLOAD_TEMPLATE.format(file_id=file_id)
        tmp_path = Path(tempfile.gettempdir()) / f"civ6_mods_recus_{file_id}.zip"

        self._set_controls_enabled(False)
        self._background_active = False
        self._progress_dialog = ProgressDialog(
            self, i18n.tr("receive.install_progress_title"), i18n.tr("receive.downloading")
        )
        self._progress_dialog.continued_in_background.connect(self._on_continued_in_background)
        self._progress_dialog.message_changed.connect(self._on_background_message_changed)
        self._download_worker = workers.DownloadInstallWorker(download_url, tmp_path, folder)
        self._download_worker.progress.connect(self._progress_dialog.set_progress)
        self._download_worker.indeterminate.connect(self._progress_dialog.set_indeterminate)
        self._download_worker.phase_changed.connect(self._on_download_phase_changed)
        self._download_worker.succeeded.connect(self._on_download_succeeded)
        self._download_worker.failed.connect(self._on_download_failed)
        self._progress_dialog.show()
        self._download_worker.start()

    def _on_download_phase_changed(self, phase: str):
        if phase == "installing":
            self._progress_dialog.set_message(i18n.tr("receive.installing"))
            self._progress_dialog.set_progress(0, 1)

    def _on_download_succeeded(self, count: int, folder: str):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.link_edit.clear()
        self.status_label.setText(i18n.tr("receive.done_status", count=count, folder=folder))
        QMessageBox.information(
            self, i18n.tr("receive.done_title"), i18n.tr("receive.done_message", count=count, folder=folder)
        )
        self._refresh_installed_dialog_if_open()

    def _on_download_failed(self, message: str):
        self._progress_dialog.close()
        self._set_controls_enabled(True)
        self._background_active = False
        self.status_label.setText("")
        QMessageBox.critical(self, i18n.tr("common.error"), i18n.tr("receive.download_error", error=message))
