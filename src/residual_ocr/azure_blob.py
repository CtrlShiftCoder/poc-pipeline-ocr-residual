"""Cliente Azure Blob para descargar imágenes residuales."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from azure.storage.blob import BlobServiceClient

from residual_ocr.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BlobClient:
    """Wrapper delgado sobre azure-storage-blob."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.azure_storage_connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING no configurada. "
                "Copie .env.example a .env y complete las credenciales."
            )
        self._svc = BlobServiceClient.from_connection_string(
            self.settings.azure_storage_connection_string
        )
        self._container = self._svc.get_container_client(
            self.settings.azure_blob_container
        )

    def list_blob_names(self, prefix: str | None = None) -> Iterator[str]:
        """Lista nombres de blob bajo el prefijo residual."""
        pfx = prefix if prefix is not None else self.settings.azure_blob_prefix
        for blob in self._container.list_blobs(name_starts_with=pfx or None):
            name = blob.name
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf", ".webp")):
                yield name

    def download_to_path(self, blob_name: str, dest: Path) -> Path:
        """Descarga un blob a disco local."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        client = self._container.get_blob_client(blob_name)
        with open(dest, "wb") as fh:
            stream = client.download_blob()
            stream.readinto(fh)
        logger.debug("Descargado %s -> %s", blob_name, dest)
        return dest

    def download_bytes(self, blob_name: str) -> bytes:
        """Descarga contenido en memoria."""
        client = self._container.get_blob_client(blob_name)
        return client.download_blob().readall()
