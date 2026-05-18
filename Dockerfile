FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/certs
COPY certs/ca.crt certs/cliente.crt certs/cliente.key /app/certs/

COPY sim_node.py .

CMD ["python", "sim_node.py", "-H", "192.168.18.110", "-p", "8883", "-s", "temperatura,umidade,pressao,co2,co,so2,no2", "-m", "-d", "1", "-i", "600"]