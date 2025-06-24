# Build stage
FROM python:3.10-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN pip install --prefix=/install --no-cache-dir . uvicorn[standard] gunicorn

# Runtime stage
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=build /install /usr/local
COPY src ./src

RUN adduser --disabled-password appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "app.api.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
