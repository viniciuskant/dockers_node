FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator_node.py .
COPY .env .

CMD ["python", "simulator_node.py", "-s", "temperatura,umidade,pressao,co2", "-i", "60"]