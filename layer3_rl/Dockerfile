# PHANTOM Layer 3 - RL Agent
FROM python:3.11-slim AS builder
WORKDIR /build
COPY layer3_rl/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY layer3_rl/ .
COPY shared/event_bus.py /app/event_bus.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "60", "layer3_rl_agent:app"]
