"""Fixtures compartidas — settings de test sin tocar Azure real."""

import os

import pytest


@pytest.fixture(autouse=True)
def _test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("OCR_WORKERS", "1")
    monkeypatch.setenv("OCR_MAX_RETRIES", "2")
    monkeypatch.setenv("EMAIL_ON_MATCH", "false")
    # invalidar cache de settings
    from residual_ocr.config import get_settings
    from residual_ocr import db as dbmod

    get_settings.cache_clear()
    dbmod.reset_engine()
    yield
    get_settings.cache_clear()
    dbmod.reset_engine()
