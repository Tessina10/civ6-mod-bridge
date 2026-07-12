"""Client minimal pour l'API Pixeldrain (upload de fichier)."""
import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UPLOAD_URL = "https://pixeldrain.com/api/file/"
FILE_URL_TEMPLATE = "https://pixeldrain.com/api/file/{file_id}"
USER_FILES_URL = "https://pixeldrain.com/api/user/files"
API_KEYS_PAGE_URL = "https://pixeldrain.com/user/api_keys"
MAX_REDIRECTS = 5
# Timeout pour les appels légers (listing, suppression) : évite qu'une connexion
# acceptée mais qui ne répond jamais laisse la pop-up de progression figée
# indéfiniment.
TIMEOUT_SECONDS = 30
# `socket.sendall()` (utilisé sous le capot pour envoyer le corps d'un PUT)
# applique le timeout à la durée totale de l'envoi, pas par appel bloquant :
# avec TIMEOUT_SECONDS un envoi de plusieurs Mo sur une connexion modeste
# dépasse la limite et échoue en plein milieu ("write operation timed out"),
# constaté en test avec une vraie archive de mods. Un timeout beaucoup plus
# généreux est donc nécessaire spécifiquement pour l'upload.
UPLOAD_TIMEOUT_SECONDS = 600


class PixeldrainError(Exception):
    """Erreur lors d'un appel à l'API Pixeldrain."""


def _read_json(response) -> dict:
    try:
        return json.loads(response.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PixeldrainError(f"Réponse Pixeldrain illisible : {exc}") from exc


def _auth_header(api_key: str) -> dict:
    token = base64.b64encode(f":{api_key}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def upload_file(path: Path, api_key: str) -> str:
    """Upload un fichier sur Pixeldrain et retourne son lien de téléchargement direct."""
    headers = {**_auth_header(api_key), "Content-Type": "application/octet-stream"}
    data = path.read_bytes()
    # Comme curl -T (utilisé dans la doc officielle), on met le nom du fichier
    # dans l'URL : un PUT sur l'URL nue sans nom de fichier échoue (405).
    url = UPLOAD_URL + urllib.parse.quote(path.name)

    # urllib ne suit pas automatiquement les redirections 307/308 sur les
    # requêtes PUT (elle ne le fait que pour GET/HEAD) : Pixeldrain redirige
    # pourtant l'upload vers un autre serveur, donc on suit nous-mêmes.
    for _ in range(MAX_REDIRECTS):
        request = urllib.request.Request(url, method="PUT", headers=headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT_SECONDS) as response:
                payload = _read_json(response)
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise PixeldrainError("Redirection Pixeldrain sans URL de destination.") from exc
                url = urllib.parse.urljoin(url, location)
                continue
            if exc.code == 401:
                raise PixeldrainError("Clé API invalide ou refusée par Pixeldrain (erreur 401).") from exc
            raise PixeldrainError(f"Erreur Pixeldrain ({exc.code}) : {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise PixeldrainError(f"Impossible de contacter Pixeldrain : {exc.reason}") from exc
        except OSError as exc:
            # Ex. timeout de lecture en cours de réponse, une fois les en-têtes déjà
            # reçus (URLError ne couvre que l'échec de connexion/requête initiale).
            raise PixeldrainError(f"Erreur réseau avec Pixeldrain : {exc}") from exc
    else:
        raise PixeldrainError("Trop de redirections lors de l'envoi vers Pixeldrain.")

    file_id = payload.get("id")
    if not file_id:
        raise PixeldrainError(f"Réponse inattendue de Pixeldrain : {payload}")
    return FILE_URL_TEMPLATE.format(file_id=file_id)


def list_files(api_key: str) -> list[dict]:
    """Retourne la liste des fichiers déjà envoyés sur le compte (jusqu'à 50000)."""
    request = urllib.request.Request(USER_FILES_URL, method="GET", headers=_auth_header(api_key))
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = _read_json(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PixeldrainError("Clé API invalide ou refusée par Pixeldrain (erreur 401).") from exc
        raise PixeldrainError(f"Erreur Pixeldrain ({exc.code}) : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise PixeldrainError(f"Impossible de contacter Pixeldrain : {exc.reason}") from exc
    except OSError as exc:
        raise PixeldrainError(f"Erreur réseau avec Pixeldrain : {exc}") from exc

    return payload.get("files", [])


def delete_file(file_id: str, api_key: str) -> None:
    """Supprime un fichier du compte. Ne fonctionne que si le compte en est propriétaire."""
    request = urllib.request.Request(
        FILE_URL_TEMPLATE.format(file_id=file_id), method="DELETE", headers=_auth_header(api_key)
    )
    try:
        urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS).close()
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise PixeldrainError("Ce fichier n'appartient pas à ce compte (erreur 403).") from exc
        raise PixeldrainError(f"Erreur Pixeldrain ({exc.code}) : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise PixeldrainError(f"Impossible de contacter Pixeldrain : {exc.reason}") from exc
    except OSError as exc:
        raise PixeldrainError(f"Erreur réseau avec Pixeldrain : {exc}") from exc
