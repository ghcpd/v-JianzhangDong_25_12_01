FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y zip && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inputs.py .
COPY inputs_backup.py .

# Set secure environment defaults
ENV FLASK_DEBUG=False
ENV FLASK_ENV=production

# Create config directory for update_records
RUN mkdir -p config

EXPOSE 5000

CMD ["python", "inputs.py"]
