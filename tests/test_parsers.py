"""Tests parsers monto, boleta, fecha, parse_ocr_text."""

from datetime import date

from residual_ocr.parse_fields import (
    extract_boleta,
    extract_fecha,
    extract_monto,
    parse_monto,
    parse_ocr_text,
)


def test_parse_monto_miles_cl():
    assert parse_monto("15.990") == 15990
    assert parse_monto("1.234.567") == 1234567
    assert parse_monto("8990") == 8990


def test_extract_monto_label():
    assert extract_monto("TOTAL: $15.990") == 15990
    assert extract_monto("Monto pago 25000") == 25000


def test_extract_boleta():
    assert extract_boleta("Boleta N° 10024567") == "10024567"
    assert extract_boleta("Folio: 10024568") == "10024568"


def test_extract_fecha():
    assert extract_fecha("Fecha 15/03/2026") == date(2026, 3, 15)
    assert extract_fecha("18-03-26") == date(2026, 3, 18)


def test_parse_ocr_text_full():
    glosa = """
    COMERCIO LTDA
    RUT 76.123.456-0
    Boleta Electronica N 10024567
    Fecha: 15/03/2026
    TOTAL $15.990
    """
    fields = parse_ocr_text(glosa)
    assert fields.rut == "76123456-0"
    assert fields.boleta == "10024567"
    assert fields.monto == 15990
    assert fields.fecha == date(2026, 3, 15)
    assert "TOTAL" in fields.glosa.upper() or "15.990" in fields.glosa
