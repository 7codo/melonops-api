FROM python:3.10-slim

# Install libpq and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first for better caching
COPY pyproject.toml ./
# COPY poetry.lock ./  # Uncomment if you use Poetry

# Install dependencies
RUN pip install --no-cache-dir . uvicorn[standard] gunicorn

# Copy the rest of the code
COPY src ./src

EXPOSE 8000

ENV PYTHONPATH=/app/src
ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["gunicorn", "app.api.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
