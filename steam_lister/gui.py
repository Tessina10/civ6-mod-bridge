"""Interface graphique : lister les mods Civilization VI installés via Steam Workshop
et préparer leur transfert vers un ami utilisant la version Epic Games."""
import json
import re
import tempfile
import threading
import time
import tkinter as tk
import zipfile
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


def _write_mods_zip(path: Path, mods_data: list[dict]) -> None:
    """Zippe les dossiers des mods donnés dans l'archive `path`."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for mod in mods_data:
            mod_folder = Path(mod["path"])
            top_name = f"{mod['id']}_{_sanitize_folder_name(mod['title'])}"
            for file_path in mod_folder.rglob("*"):
                if file_path.is_file():
                    arcname = Path(top_name) / file_path.relative_to(mod_folder)
                    zf.write(file_path, arcname)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lister mes mods Civilization VI (Steam)")
        _center_window(self, 760, 480)
        self.minsize(640, 400)

        self.content_folder: Path | None = None
        self.mods_data: list[dict] = []

        self._build_ui()
        self._auto_detect()

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
        ttk.Button(action_bar, text="Exporter vers fichier...", command=self._export_file).pack(side="left", padx=6)
        ttk.Button(action_bar, text="Copier la liste", command=self._copy_clipboard).pack(side="left")
        self.archive_button = ttk.Button(
            action_bar, text="Créer une archive (.zip)...", command=self._create_archive
        )
        self.archive_button.pack(side="left", padx=6)
        self.send_link_button = ttk.Button(
            action_bar, text="Envoyer à un ami (lien)...", command=self._send_link
        )
        self.send_link_button.pack(side="left")
        ttk.Button(action_bar, text="Paramètres...", command=lambda: self._open_settings_dialog()).pack(
            side="left", padx=6
        )

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
        self.archive_button.state(["disabled"])
        self.status_var.set(
            "Création de l'archive EN COURS, merci de patienter et de ne pas fermer "
            "l'application (peut prendre plusieurs minutes selon la taille des mods)..."
        )

        def worker():
            try:
                _write_mods_zip(Path(path), mods_data)
            except OSError as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    self.status_var.set("")
                    self.archive_button.state(["!disabled"])
                    messagebox.showerror("Erreur", f"Impossible de créer l'archive : {error_message}")
                self.after(0, failed)
                return

            def done():
                self.archive_button.state(["!disabled"])
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

        link_var = tk.StringVar(value=link)
        entry = ttk.Entry(frame, textvariable=link_var, width=52, state="readonly")
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
        self.status_var.set(
            "Compression puis envoi EN COURS, merci de patienter et de ne pas fermer "
            "l'application (peut prendre plusieurs minutes selon la taille des mods)..."
        )

        def worker():
            tmp_path = Path(tempfile.gettempdir()) / f"civ6_mods_pour_ami_{int(time.time())}.zip"
            try:
                _write_mods_zip(tmp_path, mods_data)
                link = pixeldrain_client.upload_file(tmp_path, api_key)
            except (OSError, pixeldrain_client.PixeldrainError) as exc:
                # Python supprime `exc` à la sortie du bloc except : on capture le
                # message dans une variable normale avant de la fermer dans failed().
                error_message = str(exc)
                def failed():
                    self.status_var.set("")
                    self.send_link_button.state(["!disabled"])
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
                self.send_link_button.state(["!disabled"])
                self.status_var.set(f"Lien créé avec {len(mods_data)} mod(s).")
                self._show_link_dialog(link)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
