"""CLI Click: stage1, stage2, stats, panel, init-db."""

from __future__ import annotations

import csv
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Optional

import click

from residual_ocr import __version__
from residual_ocr.config import get_settings


def _setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@click.group()
@click.version_option(__version__, prog_name="residual-ocr")
def main() -> None:
    """Pipeline OCR residual boletas chilenas (Stage1 OCR + Stage2 matching)."""
    _setup_logging()


@main.command("init-db")
@click.option("--schema", "schema_path", type=click.Path(exists=True), default=None)
def init_db_cmd(schema_path: Optional[str]) -> None:
    """Crea tablas PostgreSQL."""
    from residual_ocr.db import init_db

    init_db(schema_sql_path=schema_path)
    click.echo("Base de datos inicializada.")


def _load_residual_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    names: list[str] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        field = None
        if reader.fieldnames:
            lower = {f.lower(): f for f in reader.fieldnames}
            field = lower.get("blob_name") or lower.get("archivo") or lower.get("file") or reader.fieldnames[0]
        for row in reader:
            if field and row.get(field):
                names.append(row[field].strip())
    return names


def _process_one_blob(blob_name: str, local_dir: Path, use_blob: bool) -> dict:
    """OCR + parse + upsert. Aislado para thread pool."""
    from residual_ocr.db import session_scope, upsert_ocr_document
    from residual_ocr.ocr import run_ocr
    from residual_ocr.parse_fields import parse_ocr_text

    log = logging.getLogger("residual_ocr.stage1")
    try:
        image_bytes = None
        image_path = None
        if use_blob:
            from residual_ocr.azure_blob import BlobClient

            client = BlobClient()
            image_bytes = client.download_bytes(blob_name)
        else:
            image_path = str(local_dir / blob_name)
        result = run_ocr(image_path=image_path, image_bytes=image_bytes)
        fields = parse_ocr_text(result.text)
        with session_scope() as session:
            doc = upsert_ocr_document(
                session,
                blob_name=blob_name,
                glosa=fields.glosa,
                rut=fields.rut,
                monto=fields.monto,
                boleta=fields.boleta,
                fecha=fields.fecha,
                ocr_confidence=result.confidence,
                status="pending_match",
            )
            doc_id = doc.id
        return {
            "blob_name": blob_name,
            "ok": True,
            "id": doc_id,
            "rut": fields.rut,
            "boleta": fields.boleta,
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo Stage1 %s: %s", blob_name, exc)
        try:
            from residual_ocr.db import session_scope, upsert_ocr_document

            with session_scope() as session:
                upsert_ocr_document(
                    session,
                    blob_name=blob_name,
                    glosa=str(exc),
                    rut=None,
                    monto=None,
                    boleta=None,
                    fecha=None,
                    ocr_confidence=None,
                    status="error",
                )
        except Exception:  # noqa: BLE001
            log.exception("No se pudo persistir error para %s", blob_name)
        return {"blob_name": blob_name, "ok": False, "error": str(exc)}


@main.command()
@click.option("--local-dir", type=click.Path(file_okay=False), default=None, help="Imágenes locales (sin Azure)")
@click.option("--limit", type=int, default=None, help="Máximo de blobs a procesar")
@click.option("--workers", type=int, default=None, help="Override OCR_WORKERS")
def stage1(local_dir: Optional[str], limit: Optional[int], workers: Optional[int]) -> None:
    """Stage1: OCR + persistir glosa/campos. NO hace matching."""
    settings = get_settings()
    n_workers = workers or settings.ocr_workers
    residual_path = settings.residual_list_csv
    names = _load_residual_names(residual_path)

    use_blob = local_dir is None
    local_path = Path(local_dir) if local_dir else Path(".")

    if not names and use_blob:
        from residual_ocr.azure_blob import BlobClient

        names = list(BlobClient().list_blob_names())
    elif not names and local_dir:
        names = [
            p.name
            for p in local_path.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
        ]

    if limit:
        names = names[:limit]

    if not names:
        click.echo("No hay residuales para procesar.", err=True)
        sys.exit(1)

    click.echo(f"Stage1 OCR: {len(names)} residuales, workers={n_workers}")
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=max(1, n_workers)) as pool:
        futures = {
            pool.submit(_process_one_blob, name, local_path, use_blob): name for name in names
        }
        for fut in as_completed(futures):
            out = fut.result()
            if out.get("ok"):
                ok += 1
                click.echo(f"  OK {out['blob_name']} rut={out.get('rut')} boleta={out.get('boleta')}")
            else:
                fail += 1
                click.echo(f"  ERR {out['blob_name']}: {out.get('error')}", err=True)
    click.echo(f"Stage1 listo: ok={ok} fail={fail}")


@main.command()
@click.option("--master", "master_path", type=click.Path(exists=True), default=None)
@click.option("--notify/--no-notify", default=None, help="Override EMAIL_ON_MATCH")
def stage2(master_path: Optional[str], notify: Optional[bool]) -> None:
    """Stage2: matching en capas vs CSV maestro (strict → fallback → fuzzy)."""
    from residual_ocr.db import list_pending_match, save_match, session_scope
    from residual_ocr.matching import Matcher, load_master
    from residual_ocr.notifications.email import send_match_digest

    settings = get_settings()
    path = Path(master_path) if master_path else settings.master_csv_path
    master = load_master(path)
    matcher = Matcher(master, settings=settings)

    digest: list[dict] = []
    matched = unmatched = 0
    with session_scope() as session:
        pending = list_pending_match(session)
        click.echo(f"Stage2 matching: {len(pending)} documentos pending_match")
        for doc in pending:
            fecha_str = doc.fecha.isoformat() if isinstance(doc.fecha, date) else None
            outcome = matcher.match(
                rut=doc.rut, boleta=doc.boleta, monto=doc.monto, fecha=fecha_str
            )
            master_row = outcome.master
            save_match(
                session,
                doc,
                match_type=outcome.match_type,
                score=outcome.score,
                master_key=master_row.key if master_row else None,
                master_rut=master_row.rut if master_row else None,
                master_boleta=master_row.boleta if master_row else None,
                master_monto=master_row.monto if master_row else None,
                details=outcome.details,
            )
            if outcome.match_type != "none":
                matched += 1
                digest.append(
                    {
                        "blob_name": doc.blob_name,
                        "rut": doc.rut,
                        "boleta": doc.boleta,
                        "monto": doc.monto,
                        "match_type": outcome.match_type,
                        "score": outcome.score,
                        "master_key": master_row.key if master_row else "",
                    }
                )
            else:
                unmatched += 1
            click.echo(
                f"  {doc.blob_name} -> {outcome.match_type} ({outcome.score:.1f}) {outcome.details}"
            )

    do_notify = settings.email_on_match if notify is None else notify
    if do_notify and digest:
        send_match_digest(digest)
    click.echo(f"Stage2 listo: matched={matched} unmatched={unmatched}")


@main.command()
@click.option("--json", "as_json", is_flag=True, default=False)
def stats(as_json: bool) -> None:
    """Muestra métricas Stage1/Stage2."""
    import json as json_lib

    from residual_ocr.db import session_scope
    from residual_ocr.metrics import collect_stats

    with session_scope() as session:
        s = collect_stats(session)
    if as_json:
        click.echo(json_lib.dumps(s.to_dict(), ensure_ascii=False, indent=2))
    else:
        for k, v in s.to_dict().items():
            click.echo(f"{k}: {v}")


@main.command()
@click.option("--port", default=8501, show_default=True)
def panel(port: int) -> None:
    """Lanza panel Streamlit (requiere extra [panel])."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        click.echo("Instale el extra: pip install 'residual-ocr[panel]'", err=True)
        sys.exit(1)
    import subprocess

    panel_path = Path(__file__).with_name("panel.py")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(panel_path), "--server.port", str(port)],
        check=False,
    )


if __name__ == "__main__":
    main()
