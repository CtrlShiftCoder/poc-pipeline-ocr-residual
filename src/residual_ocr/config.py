"""Configuración desde variables de entorno / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


@dataclass(frozen=True)
class Settings:
    """Ajustes de runtime del pipeline residual."""

    azure_storage_connection_string: str
    azure_blob_container: str
    azure_blob_prefix: str
    database_url: str
    ocr_workers: int
    ocr_max_retries: int
    ocr_lang: str
    ocr_use_gpu: bool
    match_fuzzy_threshold: int
    master_csv_path: Path
    residual_list_csv: Path
    email_on_match: bool
    email_digest_size: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: str
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Carga settings una sola vez (cache)."""
    return Settings(
        azure_storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
        azure_blob_container=os.getenv("AZURE_BLOB_CONTAINER", "boletas-residuales"),
        azure_blob_prefix=os.getenv("AZURE_BLOB_PREFIX", ""),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://residual:residual@localhost:5432/residual_ocr",
        ),
        ocr_workers=int(os.getenv("OCR_WORKERS", "2")),
        ocr_max_retries=int(os.getenv("OCR_MAX_RETRIES", "3")),
        ocr_lang=os.getenv("OCR_LANG", "es"),
        ocr_use_gpu=_bool(os.getenv("OCR_USE_GPU"), False),
        match_fuzzy_threshold=int(os.getenv("MATCH_FUZZY_THRESHOLD", "85")),
        master_csv_path=Path(os.getenv("MASTER_CSV_PATH", "samples/master.csv")),
        residual_list_csv=Path(os.getenv("RESIDUAL_LIST_CSV", "samples/residual_list.csv")),
        email_on_match=_bool(os.getenv("EMAIL_ON_MATCH"), False),
        email_digest_size=int(os.getenv("EMAIL_DIGEST_SIZE", "100")),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        email_from=os.getenv("EMAIL_FROM", ""),
        email_to=os.getenv("EMAIL_TO", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
