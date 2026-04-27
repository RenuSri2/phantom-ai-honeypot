# PHANTOM Layer 2 - Company Bible
FROM python:3.11-slim AS builder
WORKDIR /build
COPY layer2_bible/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY layer2_bible/ .
COPY shared/event_bus.py /app/event_bus.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "540", "layer2_company_bible:app"]
