"""Threads Qt pour les opérations longues (réseau/disque).

Remplace le pattern Tkinter `threading.Thread` + `self.after(0, ...)` : les
signaux Qt traversent déjà le thread en toute sécurité vers le thread UI,
pas besoin de marshaling manuel.
"""
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

import formatting
import pixeldrain_client

DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class CreateArchiveWorker(QThread):
    progress = Signal(int, int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, path: Path, mods_data: list[dict]):
        super().__init__()
        self.path = path
        self.mods_data = mods_data

    def run(self):
        try:
            formatting.write_mods_zip(self.path, self.mods_data, on_progress=self.progress.emit)
        except OSError as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(str(self.path))


class SendLinkWorker(QThread):
    progress = Signal(int, int)
    phase_changed = Signal(str)  # "uploading"
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, tmp_path: Path, mods_data: list[dict], api_key: str):
        super().__init__()
        self.tmp_path = tmp_path
        self.mods_data = mods_data
        self.api_key = api_key

    def run(self):
        try:
            formatting.write_mods_zip(self.tmp_path, self.mods_data, on_progress=self.progress.emit)
            self.phase_changed.emit("uploading")
            link = pixeldrain_client.upload_file(self.tmp_path, self.api_key)
        except (OSError, pixeldrain_client.PixeldrainError) as exc:
            # L'archive temporaire n'est PAS supprimée ici : elle reste disponible
            # pour inspection en cas d'échec (comportement volontaire).
            self.failed.emit(str(exc))
            return
        try:
            self.tmp_path.unlink()
        except OSError:
            pass
        self.succeeded.emit(link)


class ImportZipWorker(QThread):
    progress = Signal(int, int)
    succeeded = Signal(int, str)  # nombre de mods extraits, dossier cible
    failed = Signal(str)

    def __init__(self, zip_path: Path, folder: Path):
        super().__init__()
        self.zip_path = zip_path
        self.folder = folder

    def run(self):
        try:
            count = formatting.extract_zip_to_folder(self.zip_path, self.folder, on_progress=self.progress.emit)
        except (OSError, zipfile.BadZipFile) as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(count, str(self.folder))


class DownloadInstallWorker(QThread):
    progress = Signal(int, int)
    indeterminate = Signal()     # taille inconnue (pas de Content-Length) : barre animée
    phase_changed = Signal(str)  # "installing"
    succeeded = Signal(int, str)
    failed = Signal(str)

    def __init__(self, download_url: str, tmp_path: Path, folder: Path):
        super().__init__()
        self.download_url = download_url
        self.tmp_path = tmp_path
        self.folder = folder

    def run(self):
        try:
            with (
                urllib.request.urlopen(self.download_url, timeout=pixeldrain_client.TIMEOUT_SECONDS) as response,
                open(self.tmp_path, "wb") as f,
            ):
                total_header = response.headers.get("Content-Length")
                total = int(total_header) if total_header else None
                if total is None:
                    self.indeterminate.emit()
                downloaded = 0
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.progress.emit(downloaded, total)

            self.phase_changed.emit("installing")
            count = formatting.extract_zip_to_folder(self.tmp_path, self.folder, on_progress=self.progress.emit)
        except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
            self.failed.emit(str(exc))
            return
        finally:
            try:
                self.tmp_path.unlink()
            except OSError:
                pass
        self.succeeded.emit(count, str(self.folder))


class RefreshUploadsWorker(QThread):
    succeeded = Signal(list)
    failed = Signal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            files = pixeldrain_client.list_files(self.api_key)
        except pixeldrain_client.PixeldrainError as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(files)


class DeleteUploadsWorker(QThread):
    progress = Signal(int, int)
    succeeded = Signal(int, int)  # (nombre supprimés, nombre en échec)

    def __init__(self, file_ids: list[str], api_key: str):
        super().__init__()
        self.file_ids = file_ids
        self.api_key = api_key

    def run(self):
        succeeded = 0
        failed_count = 0
        total = len(self.file_ids)
        for i, file_id in enumerate(self.file_ids, start=1):
            try:
                pixeldrain_client.delete_file(file_id, self.api_key)
                succeeded += 1
            except pixeldrain_client.PixeldrainError:
                failed_count += 1
            self.progress.emit(i, total)
        self.succeeded.emit(succeeded, failed_count)
