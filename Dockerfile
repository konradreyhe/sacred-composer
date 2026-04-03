FROM python:3.11-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY sacred_composer/ sacred_composer/
COPY api.py .

ENV PORT=8000
EXPOSE ${PORT}

CMD uvicorn api:app --host 0.0.0.0 --port $PORT
