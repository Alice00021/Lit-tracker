# ============ Stage 1: Builder ============
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаём venv в /opt/venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем requirements
COPY lit-tracker/requirements.txt .

# Устанавливаем в venv
RUN pip install --no-cache-dir -r requirements.txt

# common-service
COPY common-service /common-service
RUN pip install --no-cache-dir -e /common-service


# ============ Stage 2: Runtime ============
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем venv
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# common-service (для импортов)
COPY --from=builder /common-service /common-service

# Код приложения
COPY lit-tracker/app /app/app
COPY lit-tracker/alembic /app/alembic
COPY lit-tracker/alembic.ini /app/alembic.ini
COPY lit-tracker/scripts /app/scripts
COPY lit-tracker/requirements.txt /app/requirements.txt

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /opt/venv
USER appuser

ENV PYTHONUNBUFFERED=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]