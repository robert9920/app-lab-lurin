import os
from functools import lru_cache
from pathlib import PurePosixPath

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from config import settings


@lru_cache
def container():
    url = os.environ["STORAGE_ACCOUNT_URL"]
    if not url.startswith("https://"):
        raise RuntimeError("Blob requiere HTTPS")
    return BlobServiceClient(url, credential=DefaultAzureCredential()).get_container_client(
        os.getenv("STORAGE_CONTAINER", "lab-reports")
    )


def local_path(key):
    if PurePosixPath(key).is_absolute() or ".." in PurePosixPath(key).parts:
        raise ValueError("Clave de archivo inválida")
    root = settings()["upload_dir"]
    path = (root / key).resolve()
    if root not in path.parents:
        raise ValueError("Ruta inválida")
    return path


def put(key, data, content_type="application/pdf"):
    if settings()["storage_mode"] == "azure":
        container().upload_blob(
            key, data, overwrite=False, content_settings=ContentSettings(content_type=content_type)
        )
    else:
        path = local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as file:
            file.write(data)


def get(key):
    if settings()["storage_mode"] == "azure":
        return container().download_blob(key).readall()
    return local_path(key).read_bytes()
