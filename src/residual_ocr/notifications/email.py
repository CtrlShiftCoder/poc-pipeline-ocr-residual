"""Envío de digest de matches por SMTP + plantillas Jinja2."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from residual_ocr.config import Settings, get_settings

logger = logging.getLogger(__name__)

_TEMPLATES = Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
    )


def render_match_digest(
    matches: Sequence[dict[str, Any]],
    *,
    title: str = "Digest de matches residual OCR",
) -> str:
    """Renderiza HTML del digest (testeable sin SMTP)."""
    env = get_jinja_env()
    tmpl = env.get_template("match_digest.html.j2")
    return tmpl.render(title=title, matches=list(matches), count=len(matches))


def send_match_digest(
    matches: Sequence[dict[str, Any]],
    settings: Settings | None = None,
) -> bool:
    """Envía digest si EMAIL_ON_MATCH=true. Retorna False si está deshabilitado."""
    settings = settings or get_settings()
    if not settings.email_on_match:
        logger.info("EMAIL_ON_MATCH=false — no se envía correo")
        return False
    if not settings.smtp_host or not settings.email_to or not settings.email_from:
        raise ValueError("SMTP_HOST / EMAIL_FROM / EMAIL_TO requeridos para enviar")

    # Digest por lotes
    size = max(1, settings.email_digest_size)
    batch = list(matches)[:size]
    html = render_match_digest(batch)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[residual-ocr] {len(batch)} matches"
    msg["From"] = settings.email_from
    msg["To"] = settings.email_to
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.email_from, [settings.email_to], msg.as_string())
    logger.info("Digest enviado a %s (%s items)", settings.email_to, len(batch))
    return True
