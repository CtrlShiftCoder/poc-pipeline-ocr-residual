"""Panel Streamlit opcional para revisar residuales y matches."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from residual_ocr.db import MatchResult, OcrDocument, session_scope
from residual_ocr.metrics import collect_stats

st.set_page_config(page_title="Residual OCR — Boletas CL", layout="wide")
st.title("Pipeline OCR residual — boletas chilenas")
st.caption("Solo residual (~30% no conciliado). Stage1 OCR + Stage2 matching.")

try:
    with session_scope() as session:
        stats = collect_stats(session)
        docs = session.query(OcrDocument).order_by(OcrDocument.id.desc()).limit(500).all()
        matches = session.query(MatchResult).order_by(MatchResult.id.desc()).limit(500).all()
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo conectar a la DB: {exc}")
    st.info("Configure DATABASE_URL en .env")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("OCR total", stats.total_ocr)
c2.metric("Matched", stats.matched)
c3.metric("Unmatched", stats.unmatched)
c4.metric("Match rate %", stats.match_rate if stats.match_rate is not None else "—")

st.subheader("Documentos OCR")
if docs:
    df = pd.DataFrame(
        [
            {
                "id": d.id,
                "blob": d.blob_name,
                "rut": d.rut,
                "boleta": d.boleta,
                "monto": d.monto,
                "fecha": d.fecha,
                "status": d.status,
                "conf": d.ocr_confidence,
            }
            for d in docs
        ]
    )
    st.dataframe(df, use_container_width=True)
else:
    st.write("Sin documentos.")

st.subheader("Matches")
if matches:
    mf = pd.DataFrame(
        [
            {
                "id": m.id,
                "ocr_id": m.ocr_document_id,
                "type": m.match_type,
                "score": m.score,
                "master_key": m.master_key,
                "details": m.details,
            }
            for m in matches
        ]
    )
    st.dataframe(mf, use_container_width=True)
