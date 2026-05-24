FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY .env .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/certs
RUN mkdir -p /app/data

COPY mqtt_sender_service.py .

CMD ["python", "mqtt_sender_service.py"]