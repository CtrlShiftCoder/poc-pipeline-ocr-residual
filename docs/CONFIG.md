# Configuración

Copia `.env.example` → `.env`. Comentarios en español. **Sin secretos en el repo.**

| Variable | Default | Notas |
|----------|---------|-------|
| `AZURE_STORAGE_CONNECTION_STRING` | — | Obligatoria para Blob |
| `AZURE_BLOB_CONTAINER` | `boletas-residuales` | Solo residual |
| `AZURE_BLOB_PREFIX` | vacío | Prefijo opcional |
| `DATABASE_URL` | localhost psycopg2 | SQLAlchemy URL |
| `OCR_WORKERS` | `2` | Concurrencia Stage1 |
| `OCR_MAX_RETRIES` | `3` | Backoff exponencial |
| `OCR_LANG` | `es` | PaddleOCR |
| `OCR_USE_GPU` | `false` | VM CPU típica |
| `MATCH_FUZZY_THRESHOLD` | `85` | RapidFuzz 0–100 |
| `MASTER_CSV_PATH` | `samples/master.csv` | |
| `RESIDUAL_LIST_CSV` | `samples/residual_list.csv` | |
| `EMAIL_ON_MATCH` | `false` | Digest SMTP |
| `EMAIL_DIGEST_SIZE` | `100` | Ítems por correo |
| `SMTP_*` / `EMAIL_FROM` / `EMAIL_TO` | — | Si email activo |
| `LOG_LEVEL` | `INFO` | |

Carga vía `python-dotenv` en `residual_ocr.config.get_settings()`.
