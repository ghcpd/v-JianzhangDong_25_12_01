# Minimal reproducible environment
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./
ENV FLASK_DEBUG=0 \
    DB_FILE=appdata.db \
    CONFIG_DIR=/app/config \
    ALLOWED_NOTIFY_HOSTS=localhost,127.0.0.1

CMD ["python", "auto_test.py"]
