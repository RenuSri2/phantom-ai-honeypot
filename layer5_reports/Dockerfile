FROM python:3.11-slim
WORKDIR /app
COPY layer5_reports/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY layer5_reports/ .
COPY shared/event_bus.py /app/event_bus.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "540", "layer5_report_gen:app"]
