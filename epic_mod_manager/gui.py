"""Interface graphique : scanner le dossier Mods de Civilization VI et afficher
le nom et la version locale de chaque mod installé."""
import platform
import re
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

import mod_scanner

PIXELDRAIN_DOWNLOAD_TEMPLATE = "https://pixeldrain.com/api/file/{file_id}"
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def _extract_pixeldrain_id(link: str) -> str | None:
    """Accepte un lien Pixeldrain complet ou un ID brut, retourne l'ID ou None."""
    link = link.strip()
    if not link:
        return None
    match = re.search(r"pixeldrain\.com/(?:api/file|u)/([A-Za-z0-9]+)", link)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", link):
        return link
    return None


def _extract_zip_to_folder(zip_path: Path, folder: Path) -> int:
    """Extrait l'archive `zip_path` dans `folder` et retourne le nombre de mods extraits."""
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        zf.extractall(folder)
    top_level = {name.split("/")[0] for name in names if name.strip()}
    return len(top_level)


def _default_mods_folder() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path.home() / "Documents" / "My Games" / "Sid Meier's Civilization VI" / "Mods"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Sid Meier's Civilization VI" / "Mods"
    return Path.home() / "My Games" / "Sid Meier's Civilization VI" / "Mods"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scanner de mods Civilization VI (versions installées)")
        self.geometry("640x420")
        self.minsize(560, 360)

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Dossier des mods :").pack(side="left")
        self.folder_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.folder_var, width=55).pack(side="left", padx=6, fill="x", expand=True)
        self.choose_button = ttk.Button(top, text="Choisir...", command=self._choose_folder)
        self.choose_button.pack(side="left")

        action_bar = ttk.Frame(self, padding=8)
        action_bar.pack(fill="x")
        self.scan_button = ttk.Button(action_bar, text="Scanner", command=self._scan)
        self.scan_button.pack(side="left")
        self.import_button = ttk.Button(action_bar, text="Importer un zip...", command=self._import_zip)
        self.import_button.pack(side="left", padx=6)

        link_bar = ttk.Frame(self, padding=(8, 0, 8, 8))
        link_bar.pack(fill="x")
        ttk.Label(link_bar, text="Lien reçu :").pack(side="left")
        self.link_var = tk.StringVar()
        ttk.Entry(link_bar, textvariable=self.link_var, width=45).pack(
            side="left", padx=6, fill="x", expand=True
        )
        self.download_button = ttk.Button(
            link_bar, text="Télécharger et installer", command=self._download_and_install
        )
        self.download_button.pack(side="left")

        table_frame = ttk.Frame(self, padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("title", "version")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text="Nom du mod")
        self.tree.heading("version", text="Version installée")
        self.tree.column("title", width=420)
        self.tree.column("version", width=140, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, padding=8).pack(fill="x")

    def _auto_detect(self):
        folder = _default_mods_folder()
        self.folder_var.set(str(folder))
        if folder.exists():
            self.status_var.set("Dossier détecté automatiquement. Clique sur 'Scanner'.")
        else:
            self.status_var.set(
                "Dossier introuvable à l'emplacement standard. Vérifie le chemin ou "
                "clique sur 'Choisir...' pour le sélectionner manuellement."
            )

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Choisir le dossier Mods de Civilization VI")
        if folder:
            self.folder_var.set(folder)

    def _scan(self):
        folder = Path(self.folder_var.get())
        if not folder.exists():
            messagebox.showerror("Erreur", "Ce dossier n'existe pas.")
            return
        mods = mod_scanner.scan_installed_mods(folder)
        self.tree.delete(*self.tree.get_children())
        for mod in mods:
            self.tree.insert("", "end", values=(mod["title"], mod["version"]))
        self.status_var.set(f"{len(mods)} mod(s) trouvé(s) avec un fichier .modinfo.")

    def _set_controls_enabled(self, enabled: bool):
        state = ["!disabled"] if enabled else ["disabled"]
        self.choose_button.state(state)
        self.scan_button.state(state)
        self.import_button.state(state)
        self.download_button.state(state)

    def _import_zip(self):
        folder_str = self.folder_var.get().strip()
        if not folder_str:
            messagebox.showerror("Dossier manquant", "Choisis d'abord le dossier Mods de Civilization VI.")
            return

        zip_path = filedialog.askopenfilename(
            title="Choisir l'archive de mods reçue",
            filetypes=[("Archive ZIP", "*.zip"), ("Tous les fichiers", "*.*")],
        )
        if not zip_path:
            return

        folder = Path(folder_str)
        self._set_controls_enabled(False)
        self.status_var.set(
            "Extraction EN COURS, merci de patienter et de ne pas fermer l'application "
            "(peut prendre un moment selon la taille de l'archive)..."
        )

        def worker():
            try:
                count = _extract_zip_to_folder(Path(zip_path), folder)
            except (OSError, zipfile.BadZipFile) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    self._set_controls_enabled(True)
                    self.status_var.set("")
                    messagebox.showerror("Erreur", f"Impossible d'extraire l'archive : {error_message}")
                self.after(0, failed)
                return

            def done():
                self._set_controls_enabled(True)
                self.status_var.set(f"{count} mod(s) extrait(s) dans : {folder}")
                messagebox.showinfo("Import terminé", f"{count} mod(s) extrait(s) dans :\n{folder}")
                self._scan()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _download_and_install(self):
        folder_str = self.folder_var.get().strip()
        if not folder_str:
            messagebox.showerror("Dossier manquant", "Choisis d'abord le dossier Mods de Civilization VI.")
            return

        file_id = _extract_pixeldrain_id(self.link_var.get())
        if not file_id:
            messagebox.showerror(
                "Lien invalide",
                "Colle le lien complet reçu de ton ami (ou juste son identifiant Pixeldrain).",
            )
            return

        folder = Path(folder_str)
        download_url = PIXELDRAIN_DOWNLOAD_TEMPLATE.format(file_id=file_id)
        tmp_path = Path(tempfile.gettempdir()) / f"civ6_mods_recus_{file_id}.zip"
        self._set_controls_enabled(False)
        self.status_var.set(
            "Téléchargement EN COURS, merci de patienter et de ne pas fermer l'application "
            "(peut prendre un moment selon la taille de l'archive)..."
        )

        def worker():
            try:
                with urllib.request.urlopen(download_url) as response, open(tmp_path, "wb") as f:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                count = _extract_zip_to_folder(tmp_path, folder)
            except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    self._set_controls_enabled(True)
                    self.status_var.set("")
                    messagebox.showerror(
                        "Erreur", f"Impossible de télécharger ou d'extraire l'archive : {error_message}"
                    )
                self.after(0, failed)
                return
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

            def done():
                self._set_controls_enabled(True)
                self.link_var.set("")
                self.status_var.set(f"{count} mod(s) extrait(s) dans : {folder}")
                messagebox.showinfo("Import terminé", f"{count} mod(s) extrait(s) dans :\n{folder}")
                self._scan()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
