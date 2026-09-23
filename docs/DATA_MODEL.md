# Modelo de datos

## `ocr_documents` (Stage1)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | serial PK | |
| blob_name | varchar(512) unique | Path en Blob / archivo local |
| glosa | text | Texto OCR completo |
| rut | varchar(16) | Normalizado `########-X` |
| monto | int | Pesos CLP enteros |
| boleta | varchar(32) | Folio numérico |
| fecha | date | Fecha documento |
| ocr_confidence | float | Promedio scores Paddle |
| status | varchar | `pending_match` / `matched` / `unmatched` / `error` / `ocr_done` |
| created_at / updated_at | timestamp | |

## `match_results` (Stage2)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | serial PK | |
| ocr_document_id | FK | → ocr_documents |
| master_key | varchar | Clave fila maestro |
| match_type | varchar | `strict` / `fallback` / `fuzzy` / `none` |
| score | float | 0–100 |
| master_rut / master_boleta / master_monto | | Snapshot maestro |
| details | text | Motivo (ej. `boleta+rut`) |
| created_at | timestamp | |

## CSV maestro (`samples/master.csv`)

Columnas: `key,rut,boleta,monto,fecha`

## Lista residual (`samples/residual_list.csv`)

Columnas: `blob_name` (o `archivo` / `file`)
