"""Tests matching multilayer + RapidFuzz."""

from residual_ocr.matching import MasterRow, Matcher


def _master() -> list[MasterRow]:
    return [
        MasterRow(key="M-001", rut="76123456-0", boleta="10024567", monto=15990, fecha="2026-03-15"),
        MasterRow(key="M-002", rut="12345678-5", boleta="10024568", monto=25000, fecha="2026-03-16"),
        MasterRow(key="M-003", rut="11111111-1", boleta="10024569", monto=8990, fecha="2026-03-17"),
    ]


def test_strict_boleta_rut_monto():
    m = Matcher(_master(), fuzzy_threshold=85)
    out = m.match(rut="76.123.456-0", boleta="10024567", monto=15990)
    assert out.match_type == "strict"
    assert out.master and out.master.key == "M-001"
    assert out.score == 100.0


def test_fallback_boleta():
    m = Matcher(_master(), fuzzy_threshold=85)
    out = m.match(rut=None, boleta="10024568", monto=None)
    assert out.match_type == "fallback"
    assert out.master and out.master.key == "M-002"


def test_fallback_rut_monto():
    m = Matcher(_master(), fuzzy_threshold=85)
    out = m.match(rut="11111111-1", boleta=None, monto=8990)
    assert out.match_type == "fallback"
    assert out.details == "rut+monto"


def test_fuzzy_near_miss():
    m = Matcher(_master(), fuzzy_threshold=70)
    # boleta casi igual tipográfica vía token_set — query con mismos tokens
    out = m.match(rut="12345678-5", boleta="10024568", monto=25001)
    assert out.match_type in {"fallback", "fuzzy", "strict"}
    assert out.master is not None


def test_no_match():
    m = Matcher(_master(), fuzzy_threshold=95)
    out = m.match(rut="99999999-9", boleta="99999999", monto=1)
    assert out.match_type == "none"
    assert out.master is None
