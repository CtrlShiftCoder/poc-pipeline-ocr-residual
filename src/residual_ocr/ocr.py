"""Motor OCR (PaddleOCR) con reintentos y backoff."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from residual_ocr.config import Settings, get_settings
from residual_ocr.preprocess import preprocess_bytes, preprocess_for_ocr

logger = logging.getLogger(__name__)

# Lazy singleton — evita cargar modelos en import (tests mockean run_ocr)
_engine: Any = None


@dataclass
class OcrResult:
    """Salida de OCR para una imagen."""

    text: str
    lines: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw: Any = None


def _get_paddle(settings: Settings | None = None) -> Any:
    global _engine
    if _engine is not None:
        return _engine
    settings = settings or get_settings()
    from paddleocr import PaddleOCR  # import lazy

    _engine = PaddleOCR(
        use_angle_cls=True,
        lang=settings.ocr_lang,
        use_gpu=settings.ocr_use_gpu,
        show_log=False,
    )
    return _engine


def _paddle_to_result(raw: Any) -> OcrResult:
    lines: list[str] = []
    scores: list[float] = []
    if not raw:
        return OcrResult(text="", lines=[], confidence=0.0, raw=raw)
    # PaddleOCR retorna list[list[[box], (text, score)]]
    page = raw[0] if isinstance(raw, list) and raw else []
    for item in page or []:
        try:
            txt, score = item[1][0], float(item[1][1])
        except (IndexError, TypeError, ValueError):
            continue
        if txt and str(txt).strip():
            lines.append(str(txt).strip())
            scores.append(score)
    conf = sum(scores) / len(scores) if scores else 0.0
    return OcrResult(text="\n".join(lines), lines=lines, confidence=conf, raw=raw)


def run_ocr(
    image_path: str | None = None,
    image_bytes: bytes | None = None,
    settings: Settings | None = None,
    engine_factory: Callable[[], Any] | None = None,
) -> OcrResult:
    """Ejecuta OCR con reintentos/backoff. Tests inyectan engine_factory mock."""
    settings = settings or get_settings()
    retries = max(1, settings.ocr_max_retries)
    last_err: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            if image_bytes is not None:
                processed = preprocess_bytes(image_bytes)
            elif image_path is not None:
                processed = preprocess_for_ocr(image_path)
            else:
                raise ValueError("Debe indicar image_path o image_bytes")

            if engine_factory is not None:
                engine = engine_factory()
                raw = engine.ocr(processed, cls=True)
            else:
                engine = _get_paddle(settings)
                raw = engine.ocr(processed, cls=True)
            return _paddle_to_result(raw)
        except Exception as exc:  # noqa: BLE001 — reintento genérico de IO/OCR
            last_err = exc
            wait = min(2 ** (attempt - 1), 30)
            logger.warning(
                "OCR intento %s/%s falló: %s — backoff %ss",
                attempt,
                retries,
                exc,
                wait,
            )
            if attempt < retries:
                time.sleep(wait)
    assert last_err is not None
    raise last_err


def reset_engine() -> None:
    """Libera singleton (útil en tests)."""
    global _engine
    _engine = None
