"""Fenêtre principale : onglets Envoyer/Recevoir, avec le sélecteur de langue
dans leur coin (général, indépendant de l'onglet actif). Le bouton "Options
avancées" vit dans chaque onglet (voir send_tab.py/receive_tab.py) plutôt
qu'ici, pour qu'il apparaisse juste sous la barre d'onglets et non tout en
bas de la fenêtre (un QTabWidget occupe tout l'espace vertical disponible :
un widget ajouté après lui dans un layout se retrouve poussé au bas de la
fenêtre, pas juste sous la barre d'onglets)."""
from PySide6.QtWidgets import QComboBox, QMainWindow, QTabWidget

import i18n
from receive_tab import ReceiveTab
from send_tab import SendTab

SEND_TAB_INDEX = 0
RECEIVE_TAB_INDEX = 1

_LANGUAGE_LABELS = {"fr": "Français", "en": "English"}

# Garde une référence vers la fenêtre courante pour que Python ne la libère pas
# pendant un changement de langue à chaud (voir _change_language).
_current_window = None


class MainWindow(QMainWindow):
    def __init__(
        self,
        initial_tab: int = SEND_TAB_INDEX,
        initial_send_folder: str = "",
        initial_receive_folder: str = "",
    ):
        super().__init__()
        self.setWindowTitle(i18n.tr("app.title"))
        self.resize(760, 520)

        self.send_tab = SendTab()
        self.receive_tab = ReceiveTab()
        if initial_send_folder:
            self.send_tab.folder_edit.setText(initial_send_folder)
        if initial_receive_folder:
            self.receive_tab.folder_edit.setText(initial_receive_folder)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.send_tab, i18n.tr("tab.send"))
        self.tabs.addTab(self.receive_tab, i18n.tr("tab.receive"))
        self.tabs.setCurrentIndex(initial_tab)
        self._build_language_selector()
        self.setCentralWidget(self.tabs)

    def _build_language_selector(self):
        self.language_combo = QComboBox()
        for code, label in _LANGUAGE_LABELS.items():
            self.language_combo.addItem(label, userData=code)
        current_index = list(_LANGUAGE_LABELS.keys()).index(i18n.current_language())
        self.language_combo.setCurrentIndex(current_index)
        # Connecté après avoir positionné l'index initial, pour ne pas déclencher
        # un changement de langue "fantôme" pendant la construction de la fenêtre.
        self.language_combo.currentIndexChanged.connect(
            lambda index: self._change_language(self.language_combo.itemData(index))
        )
        self.tabs.setCornerWidget(self.language_combo)

    def _change_language(self, language: str):
        if language == i18n.current_language():
            return
        i18n.set_language(language)

        global _current_window
        new_window = MainWindow(
            initial_tab=self.tabs.currentIndex(),
            initial_send_folder=self.send_tab.folder_edit.text(),
            initial_receive_folder=self.receive_tab.folder_edit.text(),
        )
        # Affiche la nouvelle fenêtre AVANT de fermer l'ancienne : il ne doit
        # jamais y avoir zéro fenêtre visible, sinon Qt quitte l'application
        # (quitOnLastWindowClosed).
        new_window.show()
        _current_window = new_window
        self.close()
