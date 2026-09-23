"""Parsers de campos típicos de boletas chilenas: RUT, monto, n° boleta, fecha."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

# RUT Chile: 7-8 dígitos + DV (0-9 o K)
_RUT_RE = re.compile(
    r"(?i)\b(\d{1,2}[.\s]?\d{3}[.\s]?\d{3}|\d{7,8})\s*[-–]?\s*([0-9Kk])\b"
)
_MONTO_RE = re.compile(
    r"(?i)(?:total|monto|pago|\$|clp)\s*[:.]?\s*\$?\s*([\d.]+(?:,\d{1,2})?|\d+)"
)
_MONTO_PLAIN_RE = re.compile(r"\$\s*([\d.]{3,}(?:,\d{1,2})?)")
_BOLETA_PATTERNS = (
    re.compile(
        r"(?i)(?:boleta|folio)\s+(?:electr[oó]nica\s+)?(?:n[°ºo.\s]*)\s*(\d{4,12})"
    ),
    re.compile(r"(?i)(?:boleta|folio)\s*[:.#]?\s*(\d{4,12})"),
    re.compile(r"(?i)\bn[°ºo]\s*[:.]?\s*(\d{4,12})"),
    re.compile(r"(?i)num(?:ero)?\s*[:.#]?\s*(\d{4,12})"),
)
_FECHA_RE = re.compile(
    r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"
)


def clean_rut_body(raw: str) -> str:
    """Solo dígitos del cuerpo del RUT."""
    return re.sub(r"\D", "", raw)


def compute_rut_dv(body: str) -> str:
    """Dígito verificador módulo 11 (Chile)."""
    digits = clean_rut_body(body)
    if not digits:
        raise ValueError("RUT vacío")
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    for i, ch in enumerate(reversed(digits)):
        total += int(ch) * factors[i % len(factors)]
    remainder = 11 - (total % 11)
    if remainder == 11:
        return "0"
    if remainder == 10:
        return "K"
    return str(remainder)


def validate_rut(rut: str) -> bool:
    """Valida RUT chileno completo (cuerpo-DV)."""
    m = _RUT_RE.search(rut.replace(" ", ""))
    if not m:
        # intentar formato cuerpo-DV ya limpio
        parts = re.split(r"[-–]", rut.strip(), maxsplit=1)
        if len(parts) != 2:
            return False
        body, dv = parts[0], parts[1]
    else:
        body, dv = m.group(1), m.group(2)
    body_digits = clean_rut_body(body)
    if len(body_digits) < 7 or len(body_digits) > 8:
        return False
    return compute_rut_dv(body_digits) == dv.upper()


def format_rut(body: str, dv: str | None = None) -> str:
    """Normaliza a ########-X sin puntos."""
    digits = clean_rut_body(body)
    if dv is None:
        dv = compute_rut_dv(digits)
    return f"{digits}-{dv.upper()}"


def extract_rut(text: str) -> Optional[str]:
    """Extrae el primer RUT válido del texto OCR."""
    for m in _RUT_RE.finditer(text):
        body, dv = m.group(1), m.group(2)
        try:
            if compute_rut_dv(body) == dv.upper():
                return format_rut(body, dv)
        except ValueError:
            continue
    return None


def parse_monto(raw: str) -> Optional[int]:
    """Convierte monto chileno a pesos enteros (sin decimales)."""
    s = raw.strip()
    # 1.234.567,89 o 1234567 o 1.234.567
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # 1234,56
        s = s.replace(",", ".")
    else:
        # puntos como miles: 1.234.567
        parts = s.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) <= 2:
            pass  # decimal con punto
        else:
            s = s.replace(".", "")
    try:
        value = float(s)
    except ValueError:
        return None
    return int(round(value))


def extract_monto(text: str) -> Optional[int]:
    for pattern in (_MONTO_RE, _MONTO_PLAIN_RE):
        m = pattern.search(text)
        if m:
            parsed = parse_monto(m.group(1))
            if parsed is not None and parsed > 0:
                return parsed
    return None


def extract_boleta(text: str) -> Optional[str]:
    for pattern in _BOLETA_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


def extract_fecha(text: str) -> Optional[date]:
    for m in _FECHA_RE.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
        try:
            return date(y, mo, d)
        except ValueError:
            try:
                return date(y, d, mo)  # posible MM/DD
            except ValueError:
                continue
    return None


@dataclass
class ParsedFields:
    rut: Optional[str] = None
    monto: Optional[int] = None
    boleta: Optional[str] = None
    fecha: Optional[date] = None
    glosa: str = ""

    def to_dict(self) -> dict:
        return {
            "rut": self.rut,
            "monto": self.monto,
            "boleta": self.boleta,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "glosa": self.glosa,
        }


def parse_ocr_text(text: str) -> ParsedFields:
    """Extrae campos estructurados desde la glosa OCR."""
    return ParsedFields(
        rut=extract_rut(text),
        monto=extract_monto(text),
        boleta=extract_boleta(text),
        fecha=extract_fecha(text),
        glosa=text.strip(),
    )


def normalize_fecha_str(value: str | date | datetime | None) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    parsed = extract_fecha(str(value))
    return parsed.isoformat() if parsed else str(value).strip() or None
