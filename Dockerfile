FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY sql ./sql
COPY samples ./samples

RUN pip install --no-cache-dir -e ".[dev]"

ENV OCR_WORKERS=2 \
    OCR_MAX_RETRIES=3 \
    EMAIL_ON_MATCH=false \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["residual-ocr"]
CMD ["--help"]
