FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DB_PATH=/tmp/ferrostats.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Al iniciar el contenedor en Cloud Run, asegura que la base de datos se inicialice y arranque uvicorn
CMD ["sh", "-c", "python3 -m app.db.seed_loader && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
