"""Pop-up de progression réutilisable pour les opérations longues (compression,
envoi, téléchargement, extraction, suppression en masse)."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

import i18n


class ProgressDialog(QDialog):
    # Émis quand l'utilisateur clique sur "Continuer en arrière-plan" (la pop-up
    # se ferme mais l'opération continue) : permet à l'onglet appelant d'afficher
    # un état persistant ailleurs (voir SendTab/ReceiveTab).
    continued_in_background = Signal()
    # Émis à chaque changement de message (voir set_message), pour que ce même
    # état persistant reste à jour si la phase change après le passage en fond.
    message_changed = Signal(str)

    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        # Pas de bouton X ni d'aide contextuelle dans la barre de titre : un X
        # laisserait croire qu'il annule l'opération, alors qu'il ne fait que
        # cacher la pop-up (voir bouton explicite ci-dessous).
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        button_row.addStretch()
        background_button = QPushButton(i18n.tr("progress.background_button"))
        background_button.clicked.connect(self._continue_in_background)
        button_row.addWidget(background_button)
        layout.addLayout(button_row)

    def _continue_in_background(self) -> None:
        self.continued_in_background.emit()
        self.close()

    def current_message(self) -> str:
        return self.message_label.text()

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)
        self.message_changed.emit(message)

    def set_progress(self, done: int, total: int) -> None:
        if total:
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(done / total * 100))

    def set_indeterminate(self) -> None:
        self.progress_bar.setRange(0, 0)  # idiome Qt pour une barre "occupée" animée

    # Volontairement pas de blocage de la fermeture (Échap ou bouton "Continuer en
    # arrière-plan") : une première version bloquait tout, ce qui a figé l'appli
    # entière si la pop-up ne se fermait pas automatiquement comme prévu (aucune
    # échappatoire possible). Fermer cette pop-up n'interrompt pas l'opération en
    # cours (elle continue en fond) ; le résultat (succès ou erreur) s'affichera
    # quand même à la fin via une boîte de dialogue séparée. Le bouton X natif a
    # été retiré (setWindowFlags) car son affordance standard ("annuler") ne
    # correspondait pas à ce comportement réel.
