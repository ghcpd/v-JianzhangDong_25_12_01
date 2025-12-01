FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
# Set default environment values
ENV FLASK_APP=input.py
EXPOSE 5000
CMD ["python", "-m", "pytest", "-q", "tests/test_input.py"]
