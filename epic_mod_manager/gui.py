"""Interface graphique : installer automatiquement les mods reçus par lien, et
scanner le dossier Mods de Civilization VI pour afficher ceux déjà installés."""
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


def _extract_zip_to_folder(zip_path: Path, folder: Path, on_progress=None) -> int:
    """Extrait l'archive `zip_path` dans `folder` et retourne le nombre de mods extraits.
    `on_progress(fait, total)` est appelé après chaque fichier extrait, si fourni."""
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        total = len(infos)
        for i, info in enumerate(infos, start=1):
            zf.extract(info, folder)
            if on_progress:
                on_progress(i, total)
        names = [info.filename for info in infos]
    top_level = {name.split("/")[0] for name in names if name.strip()}
    return len(top_level)


def _center_window(window: tk.Tk, width: int, height: int) -> None:
    """Positionne une fenêtre racine au centre de l'écran."""
    x = (window.winfo_screenwidth() - width) // 2
    y = (window.winfo_screenheight() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def _center_toplevel(window: tk.Toplevel, parent: tk.Misc) -> None:
    """Centre une fenêtre secondaire (dialogue) par rapport à sa fenêtre parente."""
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    x = parent.winfo_x() + (parent.winfo_width() - width) // 2
    y = parent.winfo_y() + (parent.winfo_height() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def _open_progress_dialog(parent: tk.Misc, title: str, message: str):
    """Ouvre une pop-up modale avec un message et une barre de progression.
    Retourne (dialog, progressbar, message_var) ; le worker met à jour ces
    éléments via `parent.after(0, ...)` puis détruit `dialog` à la fin."""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    frame = ttk.Frame(dialog, padding=16)
    frame.pack(fill="both", expand=True)

    message_var = tk.StringVar(value=message)
    ttk.Label(frame, textvariable=message_var, wraplength=360, justify="left").pack(anchor="w", pady=(0, 10))

    progress = ttk.Progressbar(frame, mode="determinate", length=360, maximum=100)
    progress.pack(fill="x")

    _center_toplevel(dialog, parent)
    return dialog, progress, message_var


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
        self.title("Installer des mods Civilization VI")
        _center_window(self, 560, 260)
        self.minsize(500, 240)

        self._installed_window: tk.Toplevel | None = None
        self._installed_tree: ttk.Treeview | None = None

        self._build_menu()
        self._build_ui()
        self._auto_detect()

    def _build_menu(self):
        menubar = tk.Menu(self)
        legacy_menu = tk.Menu(menubar, tearoff=False)
        legacy_menu.add_command(label="Voir les mods installés...", command=self._open_installed_mods_window)
        legacy_menu.add_command(label="Importer un zip local...", command=self._import_zip)
        menubar.add_cascade(label="Options avancées", menu=legacy_menu)
        self.config(menu=menubar)
        self.menubar = menubar

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Dossier des mods :").pack(side="left")
        self.folder_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.folder_var, width=45, state="readonly").pack(
            side="left", padx=6, fill="x", expand=True
        )
        self.choose_button = ttk.Button(top, text="Choisir...", command=self._choose_folder)
        self.choose_button.pack(side="left")

        hero = ttk.Frame(self, padding=(16, 16, 16, 8))
        hero.pack(fill="x")
        ttk.Label(
            hero,
            text="Colle ici le lien reçu de ton ami, puis clique sur Installer :",
        ).pack(anchor="w", pady=(0, 6))
        link_row = ttk.Frame(hero)
        link_row.pack(fill="x")
        self.link_var = tk.StringVar()
        ttk.Entry(link_row, textvariable=self.link_var, font=("TkDefaultFont", 11)).pack(
            side="left", fill="x", expand=True, ipady=4
        )
        style = ttk.Style(self)
        style.configure("Hero.TButton", font=("TkDefaultFont", 11, "bold"))
        self.download_button = ttk.Button(
            hero,
            text="Installer les mods",
            command=self._download_and_install,
            style="Hero.TButton",
        )
        self.download_button.pack(fill="x", pady=(8, 0))

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, padding=8, wraplength=520, justify="left").pack(fill="x")

    def _auto_detect(self):
        folder = _default_mods_folder()
        self.folder_var.set(str(folder))
        if folder.exists():
            self.status_var.set("Dossier détecté automatiquement. Prêt à recevoir des mods.")
        else:
            self.status_var.set(
                "Dossier introuvable à l'emplacement standard. Vérifie le chemin ou "
                "clique sur 'Choisir...' pour le sélectionner manuellement."
            )

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Choisir le dossier Mods de Civilization VI")
        if folder:
            self.folder_var.set(folder)

    def _refresh_installed_tree(self):
        if self._installed_tree is None or not self._installed_tree.winfo_exists():
            return
        folder = Path(self.folder_var.get())
        if not folder.exists():
            return
        mods = mod_scanner.scan_installed_mods(folder)
        self._installed_tree.delete(*self._installed_tree.get_children())
        for mod in mods:
            self._installed_tree.insert("", "end", values=(mod["title"], mod["version"]))

    def _open_installed_mods_window(self):
        if self._installed_window is not None and self._installed_window.winfo_exists():
            self._installed_window.lift()
            self._refresh_installed_tree()
            return

        win = tk.Toplevel(self)
        win.title("Mods installés")
        win.geometry("560x360")
        win.minsize(480, 300)

        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Scanner", command=self._refresh_installed_tree).pack(side="left")

        table_frame = ttk.Frame(win, padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("title", "version")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        tree.heading("title", text="Nom du mod")
        tree.heading("version", text="Version installée")
        tree.column("title", width=380)
        tree.column("version", width=140, anchor="center")
        tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        self._installed_window = win
        self._installed_tree = tree
        _center_toplevel(win, self)
        self._refresh_installed_tree()

    def _set_controls_enabled(self, enabled: bool):
        state = ["!disabled"] if enabled else ["disabled"]
        self.choose_button.state(state)
        self.download_button.state(state)
        self.menubar.entryconfig("Options avancées", state="normal" if enabled else "disabled")

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
        dialog, progress, _message_var = _open_progress_dialog(
            self, "Import en cours", "Extraction de l'archive..."
        )

        def worker():
            def on_progress(done, total):
                percent = (done / total * 100) if total else 0
                self.after(0, lambda: progress.configure(value=percent))

            try:
                count = _extract_zip_to_folder(Path(zip_path), folder, on_progress=on_progress)
            except (OSError, zipfile.BadZipFile) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    dialog.destroy()
                    self._set_controls_enabled(True)
                    self.status_var.set("")
                    messagebox.showerror("Erreur", f"Impossible d'extraire l'archive : {error_message}")
                self.after(0, failed)
                return

            def done():
                dialog.destroy()
                self._set_controls_enabled(True)
                self.status_var.set(f"{count} mod(s) extrait(s) dans : {folder}")
                messagebox.showinfo("Import terminé", f"{count} mod(s) extrait(s) dans :\n{folder}")
                self._refresh_installed_tree()
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
        dialog, progress, message_var = _open_progress_dialog(
            self, "Installation en cours", "Téléchargement en cours..."
        )

        def worker():
            try:
                with urllib.request.urlopen(download_url) as response, open(tmp_path, "wb") as f:
                    total_header = response.headers.get("Content-Length")
                    total = int(total_header) if total_header else None
                    if total is None:
                        self.after(0, lambda: progress.configure(mode="indeterminate"))
                        self.after(0, lambda: progress.start(15))
                    downloaded = 0
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = downloaded / total * 100
                            self.after(0, lambda p=percent: progress.configure(value=p))

                def start_extraction():
                    progress.stop()
                    progress.configure(mode="determinate", value=0)
                    message_var.set("Installation des mods...")
                self.after(0, start_extraction)

                def on_extract_progress(done, extract_total):
                    percent = (done / extract_total * 100) if extract_total else 0
                    self.after(0, lambda: progress.configure(value=percent))

                count = _extract_zip_to_folder(tmp_path, folder, on_progress=on_extract_progress)
            except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    progress.stop()
                    dialog.destroy()
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
                progress.stop()
                dialog.destroy()
                self._set_controls_enabled(True)
                self.link_var.set("")
                self.status_var.set(f"{count} mod(s) extrait(s) dans : {folder}")
                messagebox.showinfo("Import terminé", f"{count} mod(s) extrait(s) dans :\n{folder}")
                self._refresh_installed_tree()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
