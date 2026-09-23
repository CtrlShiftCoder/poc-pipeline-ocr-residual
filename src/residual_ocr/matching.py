"""Matching en capas: estricto → fallback → RapidFuzz fuzzy.

Solo contra el maestro CSV; el residual (~30%) nunca incluye el 70% ya conciliado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from rapidfuzz import fuzz, process

from residual_ocr.config import Settings, get_settings
from residual_ocr.parse_fields import format_rut, validate_rut

logger = logging.getLogger(__name__)


@dataclass
class MasterRow:
    key: str
    rut: Optional[str] = None
    boleta: Optional[str] = None
    monto: Optional[int] = None
    fecha: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchOutcome:
    match_type: str  # strict | fallback | fuzzy | none
    score: float
    master: Optional[MasterRow] = None
    details: str = ""


def _norm_rut(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().upper().replace(".", "")
    if not s:
        return None
    if "-" not in s and len(s) >= 8:
        s = f"{s[:-1]}-{s[-1]}"
    if validate_rut(s):
        body, dv = s.rsplit("-", 1)
        return format_rut(body, dv)
    return s


def _norm_boleta(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def _norm_monto(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(round(float(str(value).replace(".", "").replace(",", "."))))
    except ValueError:
        return None


def load_master(path: str | Path) -> list[MasterRow]:
    """Carga CSV maestro. Columnas esperadas: rut,boleta,monto,fecha[,key]."""
    path = Path(path)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = {c.lower().strip(): c for c in df.columns}
    rows: list[MasterRow] = []
    for idx, row in df.iterrows():
        rut = _norm_rut(row[cols["rut"]]) if "rut" in cols else None
        boleta = _norm_boleta(row[cols["boleta"]]) if "boleta" in cols else None
        monto = _norm_monto(row[cols["monto"]]) if "monto" in cols else None
        fecha = None
        if "fecha" in cols:
            fecha = str(row[cols["fecha"]]).strip() or None
        key = str(row[cols["key"]]).strip() if "key" in cols else f"row-{idx}"
        rows.append(
            MasterRow(
                key=key,
                rut=rut,
                boleta=boleta,
                monto=monto,
                fecha=fecha,
                raw={c: row[c] for c in df.columns},
            )
        )
    logger.info("Maestro cargado: %s filas desde %s", len(rows), path)
    return rows


class Matcher:
    """Matching en 3 capas contra el maestro en memoria."""

    def __init__(
        self,
        master: list[MasterRow],
        fuzzy_threshold: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        settings = settings or get_settings()
        self.master = master
        self.fuzzy_threshold = (
            fuzzy_threshold
            if fuzzy_threshold is not None
            else settings.match_fuzzy_threshold
        )
        self._by_boleta: dict[str, list[MasterRow]] = {}
        self._by_rut: dict[str, list[MasterRow]] = {}
        self._fuzzy_choices: dict[str, MasterRow] = {}
        for m in master:
            if m.boleta:
                self._by_boleta.setdefault(m.boleta, []).append(m)
            if m.rut:
                self._by_rut.setdefault(m.rut, []).append(m)
            # clave fuzzy: boleta|rut|monto
            label = f"{m.boleta or ''}|{m.rut or ''}|{m.monto or ''}"
            self._fuzzy_choices[label] = m

    def match(
        self,
        *,
        rut: Optional[str],
        boleta: Optional[str],
        monto: Optional[int],
        fecha: Optional[str] = None,
    ) -> MatchOutcome:
        rut_n = _norm_rut(rut) if rut else None
        boleta_n = _norm_boleta(boleta) if boleta else None

        # 1) Estricto: boleta + rut (+ monto si ambos tienen)
        if boleta_n and boleta_n in self._by_boleta:
            for cand in self._by_boleta[boleta_n]:
                if rut_n and cand.rut and cand.rut != rut_n:
                    continue
                if monto is not None and cand.monto is not None and cand.monto != monto:
                    continue
                if rut_n and cand.rut == rut_n:
                    return MatchOutcome(
                        match_type="strict",
                        score=100.0,
                        master=cand,
                        details="boleta+rut(+monto)",
                    )

        # 2) Fallback: boleta sola, o rut+monto, o rut+fecha
        if boleta_n and boleta_n in self._by_boleta:
            cand = self._by_boleta[boleta_n][0]
            return MatchOutcome(
                match_type="fallback",
                score=90.0,
                master=cand,
                details="boleta",
            )
        if rut_n and rut_n in self._by_rut and monto is not None:
            for cand in self._by_rut[rut_n]:
                if cand.monto == monto:
                    return MatchOutcome(
                        match_type="fallback",
                        score=88.0,
                        master=cand,
                        details="rut+monto",
                    )
        if rut_n and rut_n in self._by_rut and fecha:
            for cand in self._by_rut[rut_n]:
                if cand.fecha and cand.fecha[:10] == str(fecha)[:10]:
                    return MatchOutcome(
                        match_type="fallback",
                        score=85.0,
                        master=cand,
                        details="rut+fecha",
                    )

        # 3) Fuzzy RapidFuzz sobre etiqueta boleta|rut|monto
        query = f"{boleta_n or ''}|{rut_n or ''}|{monto or ''}"
        if self._fuzzy_choices and query.strip("|"):
            hit = process.extractOne(
                query,
                list(self._fuzzy_choices.keys()),
                scorer=fuzz.token_set_ratio,
            )
            if hit and hit[1] >= self.fuzzy_threshold:
                return MatchOutcome(
                    match_type="fuzzy",
                    score=float(hit[1]),
                    master=self._fuzzy_choices[hit[0]],
                    details=f"rapidfuzz={hit[1]:.1f}",
                )

        return MatchOutcome(match_type="none", score=0.0, master=None, details="sin match")
