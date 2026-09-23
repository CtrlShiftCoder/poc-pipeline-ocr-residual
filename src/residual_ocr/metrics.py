"""Métricas agregadas Stage1 / Stage2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from residual_ocr.db import MatchResult, OcrDocument


@dataclass
class PipelineStats:
    total_ocr: int = 0
    pending_match: int = 0
    matched: int = 0
    unmatched: int = 0
    errors: int = 0
    match_strict: int = 0
    match_fallback: int = 0
    match_fuzzy: int = 0
    match_none: int = 0
    avg_ocr_confidence: float | None = None
    match_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_stats(session: Session) -> PipelineStats:
    stats = PipelineStats()
    stats.total_ocr = session.scalar(select(func.count()).select_from(OcrDocument)) or 0

    for status, attr in (
        ("pending_match", "pending_match"),
        ("matched", "matched"),
        ("unmatched", "unmatched"),
        ("error", "errors"),
        ("ocr_done", "pending_match"),
    ):
        count = session.scalar(
            select(func.count()).select_from(OcrDocument).where(OcrDocument.status == status)
        ) or 0
        setattr(stats, attr, getattr(stats, attr) + count)

    avg = session.scalar(select(func.avg(OcrDocument.ocr_confidence)))
    stats.avg_ocr_confidence = float(avg) if avg is not None else None

    for mtype, attr in (
        ("strict", "match_strict"),
        ("fallback", "match_fallback"),
        ("fuzzy", "match_fuzzy"),
        ("none", "match_none"),
    ):
        count = session.scalar(
            select(func.count()).select_from(MatchResult).where(MatchResult.match_type == mtype)
        ) or 0
        setattr(stats, attr, count)

    decided = stats.matched + stats.unmatched
    if decided:
        stats.match_rate = round(100.0 * stats.matched / decided, 2)
    return stats
