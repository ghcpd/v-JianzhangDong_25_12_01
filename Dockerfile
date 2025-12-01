# Dockerfile for Secure Flask Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including zip utility
RUN apt-get update && \
    apt-get install -y --no-install-recommends zip && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY inputs.py .
COPY inputs_backup.py .
COPY appdata.db .

# Create logs directory
RUN mkdir -p logs

# Set environment variables for security
ENV PAYMENT_TOKEN="tok_secure_production_token"
ENV MAIL_SERVER_KEY="mail_srv_key_secure"
ENV INTERNAL_AUTH="admin_internal_secure_key"
ENV FLASK_DEBUG="False"

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "inputs.py"]
