"""Tests RUT Chile DV y extracción."""

from residual_ocr.parse_fields import (
    compute_rut_dv,
    extract_rut,
    format_rut,
    validate_rut,
)


def test_compute_dv_known():
    assert compute_rut_dv("76123456") == "0"
    assert compute_rut_dv("12345678") == "5"
    assert compute_rut_dv("11111111") == "1"
    assert compute_rut_dv("16660132") == "0"


def test_validate_rut_ok():
    assert validate_rut("76.123.456-0")
    assert validate_rut("12345678-5")
    assert validate_rut("11.111.111-1")


def test_validate_rut_bad():
    assert not validate_rut("76.123.456-1")
    assert not validate_rut("123")
    assert not validate_rut("")


def test_format_rut():
    assert format_rut("76.123.456", "0") == "76123456-0"
    assert format_rut("12345678") == "12345678-5"


def test_extract_rut_from_glosa():
    text = "Razon Social SPA\nRUT: 12.345.678-5\nBoleta N 10024568"
    assert extract_rut(text) == "12345678-5"


def test_extract_rut_rejects_invalid_dv():
    text = "RUT 12.345.678-9 sin mas datos"
    assert extract_rut(text) is None
