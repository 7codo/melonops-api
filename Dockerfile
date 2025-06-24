FROM python:3.10-slim


WORKDIR /app

COPY pyproject.toml ./

COPY src ./src

EXPOSE 8000

ENV PYTHONPATH=/app/src

