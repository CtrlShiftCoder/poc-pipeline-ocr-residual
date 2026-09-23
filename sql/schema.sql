-- Esquema residual OCR (boletas chilenas)
-- Idempotente: CREATE IF NOT EXISTS

CREATE TABLE IF NOT EXISTS ocr_documents (
    id              SERIAL PRIMARY KEY,
    blob_name       VARCHAR(512) NOT NULL UNIQUE,
    glosa           TEXT NOT NULL DEFAULT '',
    rut             VARCHAR(16),
    monto           INTEGER,
    boleta          VARCHAR(32),
    fecha           DATE,
    ocr_confidence  DOUBLE PRECISION,
    status          VARCHAR(32) NOT NULL DEFAULT 'ocr_done',
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ocr_documents_rut ON ocr_documents (rut);
CREATE INDEX IF NOT EXISTS ix_ocr_documents_boleta ON ocr_documents (boleta);
CREATE INDEX IF NOT EXISTS ix_ocr_documents_status ON ocr_documents (status);

CREATE TABLE IF NOT EXISTS match_results (
    id               SERIAL PRIMARY KEY,
    ocr_document_id  INTEGER NOT NULL REFERENCES ocr_documents(id) ON DELETE CASCADE,
    master_key       VARCHAR(128),
    match_type       VARCHAR(32) NOT NULL,
    score            DOUBLE PRECISION NOT NULL DEFAULT 0,
    master_rut       VARCHAR(16),
    master_boleta    VARCHAR(32),
    master_monto     INTEGER,
    details          TEXT,
    created_at       TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_match_results_ocr_document_id ON match_results (ocr_document_id);
CREATE INDEX IF NOT EXISTS ix_match_results_match_type ON match_results (match_type);

COMMENT ON TABLE ocr_documents IS 'Stage1: OCR residual (~30%); nunca incluye el 70% ya conciliado';
COMMENT ON TABLE match_results IS 'Stage2: strict | fallback | fuzzy | none';
