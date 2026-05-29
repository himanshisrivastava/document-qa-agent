# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim

# Non-root user for security
RUN useradd --create-home --no-log-init appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy the application package
COPY app/ ./app/

# /data is the mount point for the document volume.
# Pre-create it and give ownership to the app user.
RUN mkdir /data && chown appuser:appuser /data

USER appuser

EXPOSE 8000

# DOCUMENT_DIR tells settings where to read/write document.txt
ENV DOCUMENT_DIR=/data

# Disable output buffering so logs appear in docker logs immediately
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
