FROM python:3.10-slim

# Install libpq and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .

COPY src ./src

RUN pip install --no-cache-dir . uvicorn[standard] gunicorn

EXPOSE 8000

ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=8000

ENV DATABASE_URL=""
ENV GOOGLE_CLIENT_ID=""
ENV GOOGLE_CLIENT_SECRET=""
ENV GOOGLE_API_KEY=""
ENV AZURE_INFERENCE_CREDENTIAL=""
ENV AZURE_INFERENCE_ENDPOINT=""

CMD ["gunicorn", "app.api.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
