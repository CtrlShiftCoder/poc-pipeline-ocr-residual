# Runbook — operación en Azure VM

## Prerrequisitos

- Ubuntu 22.04+ (Azure VM B2s o superior recomendada)
- Python 3.10+
- PostgreSQL 14+
- Acceso al contenedor Blob residual
- ~4 GB RAM (modelos PaddleOCR)

## Instalación

```bash
git clone https://github.com/CtrlShiftCoder/poc-pipeline-ocr-residual.git
cd poc-pipeline-ocr-residual
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
# Panel opcional:
# pip install -e ".[panel,dev]"
cp .env.example .env
# Editar .env con Blob + DATABASE_URL
```

## Base de datos

```bash
createdb residual_ocr   # o via Azure Database for PostgreSQL
residual-ocr init-db
# opcional SQL explícito:
psql "$DATABASE_URL_PSQL" -f sql/schema.sql
```

## Stage1 — OCR (sin matching)

```bash
# Desde Azure Blob + lista residual:
residual-ocr stage1

# O imágenes locales (dev/demo):
residual-ocr stage1 --local-dir ./data/residual --limit 50 --workers 2
```

## Stage2 — matching

```bash
residual-ocr stage2 --master samples/master.csv
# Con correo (EMAIL_ON_MATCH=true en .env):
residual-ocr stage2 --notify
```

## Métricas y panel

```bash
residual-ocr stats
residual-ocr stats --json
residual-ocr panel --port 8501
```

## Docker

```bash
docker build -t residual-ocr .
docker run --env-file .env residual-ocr stage1 --help
```

## Incidentes frecuentes

| Síntoma | Acción |
|---------|--------|
| `AZURE_STORAGE_CONNECTION_STRING no configurada` | Completar `.env` |
| OOM en Paddle | Bajar `OCR_WORKERS=1` |
| Match rate bajo | Revisar calidad OCR / umbral `MATCH_FUZZY_THRESHOLD` |
| SMTP timeout | `EMAIL_ON_MATCH=false` o revisar firewall 587 |

## Seguridad

- Nunca commitear `.env`
- Usar Managed Identity / SAS de corta vida en producción
- El 70% matched vive en otro contenedor/ruta — no apuntar el prefijo residual ahí
