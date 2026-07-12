"""Interface graphique : lister les mods Civilization VI installés via Steam Workshop
et préparer leur transfert vers un ami utilisant la version Epic Games."""
import json
import re
import tempfile
import threading
import time
import tkinter as tk
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import config
import mod_scanner
import pixeldrain_client
import steam_locator

PIXELDRAIN_API_KEYS_URL = "https://pixeldrain.com/user/api_keys"


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


def _sanitize_folder_name(name: str) -> str:
    """Nettoie un titre de mod pour en faire un nom de dossier valide dans l'archive."""
    name = re.sub(r"[^\w\-. ]", "_", name).strip()
    name = name.rstrip("_").strip()
    return name or "mod"


def _format_size(num_bytes: int) -> str:
    """Formate une taille en octets en chaîne lisible (Ko/Mo/Go)."""
    size = float(num_bytes)
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def _format_upload_date(date_upload: str) -> str:
    """Formate une date ISO 8601 renvoyée par l'API Pixeldrain en chaîne lisible."""
    try:
        return datetime.fromisoformat(date_upload).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return date_upload or "?"


def _collect_mod_files(mods_data: list[dict]) -> list[tuple[Path, Path]]:
    """Liste (chemin réel, chemin dans l'archive) de tous les fichiers des mods donnés."""
    entries = []
    for mod in mods_data:
        mod_folder = Path(mod["path"])
        top_name = f"{mod['id']}_{_sanitize_folder_name(mod['title'])}"
        for file_path in mod_folder.rglob("*"):
            if file_path.is_file():
                arcname = Path(top_name) / file_path.relative_to(mod_folder)
                entries.append((file_path, arcname))
    return entries


def _write_mods_zip(path: Path, mods_data: list[dict], on_progress=None) -> None:
    """Zippe les dossiers des mods donnés dans l'archive `path`.
    `on_progress(fait, total)` est appelé après chaque fichier écrit, si fourni."""
    entries = _collect_mod_files(mods_data)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (file_path, arcname) in enumerate(entries, start=1):
            zf.write(file_path, arcname)
            if on_progress:
                on_progress(i, len(entries))


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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lister mes mods Civilization VI (Steam)")
        _center_window(self, 760, 480)
        self.minsize(640, 400)

        self.content_folder: Path | None = None
        self.mods_data: list[dict] = []

        self._uploads_window: tk.Toplevel | None = None
        self._uploads_tree: ttk.Treeview | None = None
        self._uploads_api_key: str | None = None

        self._build_menu()
        self._build_ui()
        self._auto_detect()

    def _build_menu(self):
        menubar = tk.Menu(self)

        advanced_menu = tk.Menu(menubar, tearoff=False)

        pixeldrain_menu = tk.Menu(advanced_menu, tearoff=False)
        pixeldrain_menu.add_command(label="Clé API...", command=lambda: self._open_settings_dialog())
        pixeldrain_menu.add_command(label="Gérer mes envois...", command=self._open_manage_uploads_window)
        advanced_menu.add_cascade(label="Pixeldrain", menu=pixeldrain_menu)

        advanced_menu.add_separator()

        manual_sharing_menu = tk.Menu(advanced_menu, tearoff=False)
        manual_sharing_menu.add_command(label="Exporter en JSON...", command=self._export_file)
        manual_sharing_menu.add_command(label="Copier les liens Workshop", command=self._copy_clipboard)
        manual_sharing_menu.add_command(label="Créer une archive .zip...", command=self._create_archive)
        advanced_menu.add_cascade(label="Partage manuel", menu=manual_sharing_menu)

        menubar.add_cascade(label="Options avancées", menu=advanced_menu)

        self.config(menu=menubar)
        self.menubar = menubar

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Dossier Workshop détecté :").pack(side="left")
        self.folder_var = tk.StringVar(value="(non détecté)")
        ttk.Entry(top, textvariable=self.folder_var, width=55, state="readonly").pack(
            side="left", padx=6, fill="x", expand=True
        )
        ttk.Button(top, text="Choisir manuellement...", command=self._choose_manual_folder).pack(side="left")

        action_bar = ttk.Frame(self, padding=8)
        action_bar.pack(fill="x")
        ttk.Button(action_bar, text="Scanner", command=self._scan).pack(side="left")
        self.send_link_button = ttk.Button(
            action_bar, text="Envoyer à un ami (lien)...", command=self._send_link
        )
        self.send_link_button.pack(side="left", padx=6)

        table_frame = ttk.Frame(self, padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("title", "id", "version")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text="Nom du mod")
        self.tree.heading("id", text="ID Workshop")
        self.tree.heading("version", text="Version locale")
        self.tree.column("title", width=380)
        self.tree.column("id", width=120, anchor="center")
        self.tree.column("version", width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, padding=8).pack(fill="x")

    def _auto_detect(self):
        folders = steam_locator.find_workshop_content_folders()
        if folders:
            self.content_folder = folders[0]
            self.folder_var.set(str(self.content_folder))
            if len(folders) > 1:
                self.status_var.set(
                    f"{len(folders)} bibliothèques Steam contiennent des mods Civ VI ; "
                    "la première a été sélectionnée (utilise 'Choisir manuellement' pour changer)."
                )
            else:
                self.status_var.set("Dossier détecté automatiquement. Clique sur 'Scanner'.")
        else:
            self.status_var.set(
                "Dossier Workshop introuvable automatiquement. Utilise 'Choisir manuellement' "
                "et sélectionne .../steamapps/workshop/content/289070"
            )

    def _choose_manual_folder(self):
        folder = filedialog.askdirectory(title="Choisir le dossier steamapps/workshop/content/289070")
        if folder:
            self.content_folder = Path(folder)
            self.folder_var.set(folder)
            self.status_var.set("Dossier défini manuellement. Clique sur 'Scanner'.")

    def _scan(self):
        if not self.content_folder or not self.content_folder.exists():
            messagebox.showerror("Erreur", "Aucun dossier Workshop valide sélectionné.")
            return
        self.mods_data = mod_scanner.scan_workshop_mods(self.content_folder)
        self.tree.delete(*self.tree.get_children())
        for mod in self.mods_data:
            self.tree.insert("", "end", values=(mod["title"], mod["id"], mod["version"] or "?"))
        self.status_var.set(f"{len(self.mods_data)} mod(s) trouvé(s).")

    def _export_file(self):
        if not self.mods_data:
            messagebox.showinfo("Info", "Lance d'abord un scan.")
            return
        path = filedialog.asksaveasfilename(
            title="Exporter la liste des mods",
            defaultextension=".json",
            filetypes=[("Fichier JSON", "*.json")],
            initialfile="civ6_mods_export.json",
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
            messagebox.showerror("Erreur", f"Impossible d'écrire le fichier : {exc}")
            return
        messagebox.showinfo(
            "Export réussi",
            f"Liste exportée vers :\n{path}\n\n"
            "Ce fichier liste les ID Workshop de tes mods, à titre d'inventaire ou pour "
            "un usage manuel — il n'y a pas encore de bouton d'import automatique côté "
            "Epic Games. Pour un transfert automatique, utilise plutôt "
            "'Envoyer à un ami (lien)...'.",
        )

    def _copy_clipboard(self):
        if not self.mods_data:
            messagebox.showinfo("Info", "Lance d'abord un scan.")
            return
        text = "\n".join(
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={m['id']}" for m in self.mods_data
        )
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo(
            "Copié",
            "La liste des liens Workshop a été copiée dans le presse-papiers.\n"
            "Ton ami peut la coller directement dans 'Ajouter plusieurs...' de son application "
            "(par exemple via Discord ou un message).",
        )

    def _create_archive(self):
        if not self.mods_data:
            messagebox.showinfo("Info", "Lance d'abord un scan.")
            return
        path = filedialog.asksaveasfilename(
            title="Créer une archive à envoyer à ton ami",
            defaultextension=".zip",
            filetypes=[("Archive ZIP", "*.zip")],
            initialfile="civ6_mods_pour_ami.zip",
        )
        if not path:
            return

        mods_data = list(self.mods_data)
        self.menubar.entryconfig("Options avancées", state="disabled")
        dialog, progress, _message_var = _open_progress_dialog(
            self, "Création de l'archive", "Compression des mods..."
        )

        def worker():
            def on_progress(done, total):
                percent = (done / total * 100) if total else 0
                self.after(0, lambda: progress.configure(value=percent))

            try:
                _write_mods_zip(Path(path), mods_data, on_progress=on_progress)
            except OSError as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    dialog.destroy()
                    self.status_var.set("")
                    self.menubar.entryconfig("Options avancées", state="normal")
                    messagebox.showerror("Erreur", f"Impossible de créer l'archive : {error_message}")
                self.after(0, failed)
                return

            def done():
                dialog.destroy()
                self.menubar.entryconfig("Options avancées", state="normal")
                self.status_var.set(f"Archive créée : {path}")
                messagebox.showinfo(
                    "Archive créée",
                    f"Archive créée avec {len(mods_data)} mod(s) :\n{path}\n\n"
                    "Envoie ce fichier à ton ami (mail, Discord, clé USB...). Il pourra "
                    "l'importer directement avec le bouton 'Importer un zip...' de son application.",
                )
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _open_settings_dialog(self) -> str | None:
        """Ouvre une fenêtre modale pour saisir/mettre à jour la clé API Pixeldrain.
        Retourne la clé enregistrée, ou None si l'utilisateur a annulé."""
        dialog = tk.Toplevel(self)
        dialog.title("Paramètres")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Clé API Pixeldrain (nécessaire pour envoyer un lien à ton ami) :",
            wraplength=380,
            justify="left",
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=f"À générer gratuitement sur : {PIXELDRAIN_API_KEYS_URL}",
            wraplength=380,
            justify="left",
            foreground="#555",
        ).pack(anchor="w", pady=(2, 8))

        key_var = tk.StringVar(value=config.load_api_key() or "")
        entry = ttk.Entry(frame, textvariable=key_var, width=48, show="*")
        entry.pack(fill="x")
        entry.focus_set()

        result: dict = {"key": None}

        def on_save():
            value = key_var.get().strip()
            if not value:
                messagebox.showerror("Clé manquante", "Merci de coller une clé API.", parent=dialog)
                return
            config.save_api_key(value)
            result["key"] = value
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        button_bar = ttk.Frame(frame)
        button_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(button_bar, text="Annuler", command=on_cancel).pack(side="right")
        ttk.Button(button_bar, text="Enregistrer", command=on_save).pack(side="right", padx=6)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        _center_toplevel(dialog, self)
        self.wait_window(dialog)
        return result["key"]

    def _ensure_api_key(self) -> str | None:
        key = config.load_api_key()
        if key:
            return key
        messagebox.showinfo(
            "Clé API requise",
            "Pour envoyer un lien à ton ami, il faut d'abord renseigner une clé API "
            "Pixeldrain (gratuite).",
        )
        return self._open_settings_dialog()

    def _show_link_dialog(self, link: str):
        dialog = tk.Toplevel(self)
        dialog.title("Lien créé")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Transmets ce lien à ton ami (Discord, message...). Il pourra le coller "
            "directement dans le champ prévu de son application pour installer les mods "
            "automatiquement.",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        # Référence gardée sur self : une StringVar purement locale serait détruite
        # par Python dès la fin de cette méthode (elle ne bloque pas comme
        # _open_settings_dialog), ce qui viderait visuellement le champ.
        self._link_dialog_var = tk.StringVar(value=link)
        entry = ttk.Entry(frame, textvariable=self._link_dialog_var, width=52, state="readonly")
        entry.pack(fill="x")

        def copy_link():
            self.clipboard_clear()
            self.clipboard_append(link)

        button_bar = ttk.Frame(frame)
        button_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(button_bar, text="Fermer", command=dialog.destroy).pack(side="right")
        ttk.Button(button_bar, text="Copier le lien", command=copy_link).pack(side="right", padx=6)

        _center_toplevel(dialog, self)

    def _send_link(self):
        if not self.mods_data:
            messagebox.showinfo("Info", "Lance d'abord un scan.")
            return

        api_key = self._ensure_api_key()
        if not api_key:
            return

        mods_data = list(self.mods_data)
        self.send_link_button.state(["disabled"])
        self.menubar.entryconfig("Options avancées", state="disabled")
        dialog, progress, message_var = _open_progress_dialog(
            self, "Envoi en cours", "Compression des mods..."
        )

        def worker():
            tmp_path = Path(tempfile.gettempdir()) / f"civ6_mods_pour_ami_{int(time.time())}.zip"

            def on_zip_progress(done, total):
                percent = (done / total * 100) if total else 0
                self.after(0, lambda: progress.configure(value=percent))

            try:
                _write_mods_zip(tmp_path, mods_data, on_progress=on_zip_progress)

                def switch_to_upload():
                    progress.configure(mode="indeterminate")
                    progress.start(15)
                    message_var.set(
                        "Envoi vers Pixeldrain en cours (durée variable selon ta connexion)..."
                    )
                self.after(0, switch_to_upload)

                link = pixeldrain_client.upload_file(tmp_path, api_key)
            except (OSError, pixeldrain_client.PixeldrainError) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    progress.stop()
                    dialog.destroy()
                    self.status_var.set("")
                    self.send_link_button.state(["!disabled"])
                    self.menubar.entryconfig("Options avancées", state="normal")
                    messagebox.showerror(
                        "Erreur",
                        f"Impossible d'envoyer les mods : {error_message}\n\n"
                        f"L'archive temporaire a été conservée pour inspection :\n{tmp_path}",
                    )
                self.after(0, failed)
                return

            try:
                tmp_path.unlink()
            except OSError:
                pass

            def done():
                progress.stop()
                dialog.destroy()
                self.send_link_button.state(["!disabled"])
                self.menubar.entryconfig("Options avancées", state="normal")
                self.status_var.set(f"Lien créé avec {len(mods_data)} mod(s).")
                self._show_link_dialog(link)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _open_manage_uploads_window(self):
        if self._uploads_window is not None and self._uploads_window.winfo_exists():
            self._uploads_window.lift()
            self._refresh_uploads_list()
            return

        api_key = self._ensure_api_key()
        if not api_key:
            return

        win = tk.Toplevel(self)
        win.title("Gérer mes envois Pixeldrain")
        win.geometry("640x400")
        win.minsize(560, 320)

        action_bar = ttk.Frame(win, padding=8)
        action_bar.pack(fill="x")
        self._uploads_refresh_button = ttk.Button(
            action_bar, text="Rafraîchir", command=self._refresh_uploads_list
        )
        self._uploads_refresh_button.pack(side="left")
        self._uploads_delete_selection_button = ttk.Button(
            action_bar, text="Supprimer la sélection", command=lambda: self._delete_uploads(selection_only=True)
        )
        self._uploads_delete_selection_button.pack(side="left", padx=6)
        self._uploads_delete_all_button = ttk.Button(
            action_bar, text="Tout supprimer", command=lambda: self._delete_uploads(selection_only=False)
        )
        self._uploads_delete_all_button.pack(side="left")

        table_frame = ttk.Frame(win, padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("name", "size", "date")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        tree.heading("name", text="Nom")
        tree.heading("size", text="Taille")
        tree.heading("date", text="Date d'envoi")
        tree.column("name", width=320)
        tree.column("size", width=100, anchor="center")
        tree.column("date", width=150, anchor="center")
        tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        self._uploads_status_var = tk.StringVar(value="")
        ttk.Label(win, textvariable=self._uploads_status_var, padding=8).pack(fill="x")

        self._uploads_window = win
        self._uploads_tree = tree
        self._uploads_api_key = api_key
        _center_toplevel(win, self)
        self._refresh_uploads_list()

    def _set_uploads_controls_enabled(self, enabled: bool):
        state = ["!disabled"] if enabled else ["disabled"]
        self._uploads_refresh_button.state(state)
        self._uploads_delete_selection_button.state(state)
        self._uploads_delete_all_button.state(state)

    def _refresh_uploads_list(self):
        if self._uploads_tree is None or not self._uploads_tree.winfo_exists():
            return
        self._set_uploads_controls_enabled(False)
        self._uploads_status_var.set("Chargement de la liste...")
        api_key = self._uploads_api_key

        def worker():
            try:
                files = pixeldrain_client.list_files(api_key)
            except pixeldrain_client.PixeldrainError as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    self._set_uploads_controls_enabled(True)
                    self._uploads_status_var.set("")
                    messagebox.showerror(
                        "Erreur", f"Impossible de récupérer la liste des envois : {error_message}"
                    )
                self.after(0, failed)
                return

            def done():
                self._set_uploads_controls_enabled(True)
                self._uploads_tree.delete(*self._uploads_tree.get_children())
                for f in files:
                    self._uploads_tree.insert(
                        "", "end", iid=f["id"],
                        values=(f["name"], _format_size(f["size"]), _format_upload_date(f.get("date_upload", ""))),
                    )
                self._uploads_status_var.set(f"{len(files)} fichier(s) sur le compte.")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _delete_uploads(self, selection_only: bool):
        if self._uploads_tree is None or not self._uploads_tree.winfo_exists():
            return

        if selection_only:
            ids = list(self._uploads_tree.selection())
            if not ids:
                messagebox.showinfo(
                    "Info", "Sélectionne au moins un fichier dans la liste.", parent=self._uploads_window
                )
                return
            question = f"Supprimer les {len(ids)} fichier(s) sélectionné(s) ?\n\nCette action est irréversible."
        else:
            ids = list(self._uploads_tree.get_children())
            if not ids:
                messagebox.showinfo("Info", "Aucun fichier à supprimer.", parent=self._uploads_window)
                return
            question = f"Supprimer TOUS les fichiers envoyés ({len(ids)}) ?\n\nCette action est irréversible."

        if not messagebox.askyesno("Confirmer la suppression", question, parent=self._uploads_window):
            return

        api_key = self._uploads_api_key
        self._set_uploads_controls_enabled(False)
        dialog, progress, _message_var = _open_progress_dialog(
            self._uploads_window, "Suppression en cours", f"Suppression de {len(ids)} fichier(s)..."
        )

        def worker():
            succeeded = 0
            failed_count = 0
            for i, file_id in enumerate(ids, start=1):
                try:
                    pixeldrain_client.delete_file(file_id, api_key)
                    succeeded += 1
                except pixeldrain_client.PixeldrainError:
                    failed_count += 1
                percent = i / len(ids) * 100
                self.after(0, lambda p=percent: progress.configure(value=p))

            def done():
                dialog.destroy()
                self._set_uploads_controls_enabled(True)
                if failed_count:
                    messagebox.showwarning(
                        "Suppression terminée",
                        f"{succeeded} fichier(s) supprimé(s), {failed_count} échec(s).",
                        parent=self._uploads_window,
                    )
                else:
                    messagebox.showinfo(
                        "Suppression terminée",
                        f"{succeeded} fichier(s) supprimé(s).",
                        parent=self._uploads_window,
                    )
                self._refresh_uploads_list()
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
