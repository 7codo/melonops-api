FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
COPY src ./src

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

ENV PYTHONPATH=/app/src

CMD ["python", "src/app/api/main.py"]