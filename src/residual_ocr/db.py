"""Capa SQLAlchemy / PostgreSQL para persistir OCR y matches."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from residual_ocr.config import Settings, get_settings

logger = logging.getLogger(__name__)

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class OcrDocument(Base):
    """Documento residual tras Stage1 (OCR sin matching)."""

    __tablename__ = "ocr_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blob_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    glosa: Mapped[str] = mapped_column(Text, default="")
    rut: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    monto: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    boleta: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    fecha: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ocr_done", index=True)
    # pending_match | matched | unmatched | error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MatchResult(Base):
    """Resultado de Stage2 matching vs maestro."""

    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocr_document_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    master_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    match_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # strict | fallback | fuzzy | none
    score: Mapped[float] = mapped_column(Float, default=0.0)
    master_rut: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    master_boleta: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    master_monto: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


_engine = None
_SessionLocal = None


def get_engine(settings: Settings | None = None):
    global _engine, _SessionLocal
    settings = settings or get_settings()
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db(settings: Settings | None = None, schema_sql_path: str | None = None) -> None:
    """Crea tablas (ORM) y opcionalmente aplica sql/schema.sql."""
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    if schema_sql_path:
        with open(schema_sql_path, encoding="utf-8") as fh:
            sql = fh.read()
        with engine.begin() as conn:
            for stmt in sql.split(";"):
                chunk = stmt.strip()
                if chunk:
                    conn.execute(text(chunk))
    logger.info("DB inicializada")


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    get_engine(settings)
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_ocr_document(
    session: Session,
    *,
    blob_name: str,
    glosa: str,
    rut: Optional[str],
    monto: Optional[int],
    boleta: Optional[str],
    fecha: Optional[date],
    ocr_confidence: Optional[float],
    status: str = "pending_match",
) -> OcrDocument:
    existing = session.scalar(select(OcrDocument).where(OcrDocument.blob_name == blob_name))
    if existing:
        existing.glosa = glosa
        existing.rut = rut
        existing.monto = monto
        existing.boleta = boleta
        existing.fecha = fecha
        existing.ocr_confidence = ocr_confidence
        existing.status = status
        existing.updated_at = datetime.utcnow()
        return existing
    doc = OcrDocument(
        blob_name=blob_name,
        glosa=glosa,
        rut=rut,
        monto=monto,
        boleta=boleta,
        fecha=fecha,
        ocr_confidence=ocr_confidence,
        status=status,
    )
    session.add(doc)
    session.flush()
    return doc


def list_pending_match(session: Session) -> list[OcrDocument]:
    return list(
        session.scalars(
            select(OcrDocument).where(OcrDocument.status == "pending_match")
        ).all()
    )


def save_match(
    session: Session,
    doc: OcrDocument,
    *,
    match_type: str,
    score: float,
    master_key: Optional[str] = None,
    master_rut: Optional[str] = None,
    master_boleta: Optional[str] = None,
    master_monto: Optional[int] = None,
    details: Optional[str] = None,
) -> MatchResult:
    result = MatchResult(
        ocr_document_id=doc.id,
        master_key=master_key,
        match_type=match_type,
        score=score,
        master_rut=master_rut,
        master_boleta=master_boleta,
        master_monto=master_monto,
        details=details,
    )
    session.add(result)
    doc.status = "matched" if match_type != "none" else "unmatched"
    doc.updated_at = datetime.utcnow()
    session.flush()
    return result


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
