FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

# Default: run both API + Celery worker
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8002 & celery -A celery_app worker --loglevel=info -Q market_data --concurrency=4"]
