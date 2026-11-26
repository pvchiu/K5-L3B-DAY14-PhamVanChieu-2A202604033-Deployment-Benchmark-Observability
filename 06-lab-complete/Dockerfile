# ── Stage 1: Builder ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Cài đặt dependencies vào /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ───────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Tạo non-root user
RUN useradd -m -u 1000 appuser

# Copy installed packages từ builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY --chown=appuser:appuser . /app

# Chuyển sang non-root user
USER appuser

# Định cấu hình cổng mặc định
ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + str(os.environ.get('PORT', 8000)) + '/health')"

# Uvicorn chạy với PID 1 qua exec để nhận SIGTERM khi container dừng
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
