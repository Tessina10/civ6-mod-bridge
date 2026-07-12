"""Boîte de dialogue pour saisir/mettre à jour la clé API Pixeldrain."""
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

import config
import i18n
import pixeldrain_client


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("settings.title"))
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(i18n.tr("settings.api_key_label")))
        hint = QLabel(i18n.tr("settings.api_key_hint", url=pixeldrain_client.API_KEYS_PAGE_URL))
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(True)
        layout.addWidget(hint)

        self.key_edit = QLineEdit(config.load_api_key() or "")
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setMinimumWidth(360)
        layout.addWidget(self.key_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Save).setText(i18n.tr("common.save"))
        button_box.button(QDialogButtonBox.Cancel).setText(i18n.tr("common.cancel"))
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_save(self):
        value = self.key_edit.text().strip()
        if not value:
            QMessageBox.critical(self, i18n.tr("settings.missing_key_title"), i18n.tr("settings.missing_key_message"))
            return
        config.save_api_key(value)
        self.accept()
