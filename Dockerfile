# ── Stage: build dependencies ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Build tools needed for some wheels
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first (much smaller than the default CUDA build),
# then install the rest of the dependencies.
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir \
        torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: final slim runtime image ─────────────────────────────────────────
FROM python:3.12-slim

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source only (no tests, no docs)
COPY app/ ./app/

# HuggingFace cache lives inside the container; mount a volume in production
# to avoid re-downloading the model on every restart.
ENV HF_HOME=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface && chown appuser /app/.cache/huggingface

USER appuser

ENV PORT=8000

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
