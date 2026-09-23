"""Tests render email digest (sin SMTP)."""

from residual_ocr.notifications.email import render_match_digest


def test_render_digest_html():
    html = render_match_digest(
        [
            {
                "blob_name": "a.jpg",
                "rut": "76123456-0",
                "boleta": "10024567",
                "monto": 15990,
                "match_type": "strict",
                "score": 100,
                "master_key": "M-001",
            }
        ],
        title="Prueba digest",
    )
    assert "Prueba digest" in html
    assert "76123456-0" in html
    assert "M-001" in html
    assert "<table" in html


def test_render_empty():
    html = render_match_digest([])
    assert "Sin matches" in html
