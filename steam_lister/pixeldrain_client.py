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
MAX_REDIRECTS = 5


class PixeldrainError(Exception):
    """Erreur lors d'un appel à l'API Pixeldrain."""


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
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
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
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PixeldrainError("Clé API invalide ou refusée par Pixeldrain (erreur 401).") from exc
        raise PixeldrainError(f"Erreur Pixeldrain ({exc.code}) : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise PixeldrainError(f"Impossible de contacter Pixeldrain : {exc.reason}") from exc

    return payload.get("files", [])


def delete_file(file_id: str, api_key: str) -> None:
    """Supprime un fichier du compte. Ne fonctionne que si le compte en est propriétaire."""
    request = urllib.request.Request(
        FILE_URL_TEMPLATE.format(file_id=file_id), method="DELETE", headers=_auth_header(api_key)
    )
    try:
        urllib.request.urlopen(request).close()
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise PixeldrainError("Ce fichier n'appartient pas à ce compte (erreur 403).") from exc
        raise PixeldrainError(f"Erreur Pixeldrain ({exc.code}) : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise PixeldrainError(f"Impossible de contacter Pixeldrain : {exc.reason}") from exc
