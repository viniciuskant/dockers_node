import json
from datetime import datetime, timezone
import socket
import time
import json
import random
import argparse
import os


HOST = "0.0.0.0"

SENDER_PORT = os.getenv("SENDER_PORT")
if SENDER_PORT is None:
    raise EnvironmentError("Variável SENDER_PORT não definida")
SENDER_PORT = int (SENDER_PORT)

SENDER_HOST = os.getenv("SENDER_HOST")
if SENDER_HOST is None:
    raise EnvironmentError("Variável SENDER_HOST não definida")

SENSORES = [
    "temperatura", "umidade", "pressao",
    "co2", "co", "so2", "no2",
    "ozonio", "pm25"
]

SENSOR_CONFIGS = {
    "temperatura": {"min": -10, "max": 45, "unit": "°C", "decimals": 1},
    "umidade": {"min": 0, "max": 100, "unit": "%", "decimals": 1},
    "pressao": {"min": 950, "max": 1050, "unit": "hPa", "decimals": 1},
    "co2": {"min": 300, "max": 2000, "unit": "ppm", "decimals": 0},
    "co": {"min": 0, "max": 50, "unit": "ppm", "decimals": 1},
    "so2": {"min": 0, "max": 20, "unit": "ppm", "decimals": 1},
    "no2": {"min": 0, "max": 30, "unit": "ppm", "decimals": 1},
    "ozonio": {"min": 0, "max": 10, "unit": "ppm", "decimals": 2},
    "pm25": {"min": 0, "max": 500, "unit": "µg/m3", "decimals": 0},
}

def build_payload(sensor_name, value, type_msg):
    payload = {
        "type_msg": type_msg,
        "sensor": sensor_name,
        "message": {
            "valor": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    if value is None:
        payload["message"]["mensagem_erro"] = "Falha na leitura do sensor"

    return json.dumps(payload)

class SensorSimulator:

    def __init__(self, error_rate=0.0):
        self.error_rate = error_rate

    def generate_value(self, sensor_name):

        if random.random() < self.error_rate:
            return None

        cfg = SENSOR_CONFIGS[sensor_name]

        return round(
            random.uniform(cfg["min"], cfg["max"]),
            cfg["decimals"]
        )

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--sensors", default="temperatura")
    parser.add_argument("-i", "--interval", type=float, default=2)
    parser.add_argument("-e", "--error", type=float, default=0.0)

    args = parser.parse_args()

    sensors = [
        s.strip()
        for s in args.sensors.split(",")
        if s.strip() in SENSORES
    ]

    simulator = SensorSimulator(args.error)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while True:
        try:
            client.connect((SENDER_HOST, SENDER_PORT))
            break
        except:
            print("Aguardando sender...")
            time.sleep(2)

    while True:

        for sensor in sensors:

            value = simulator.generate_value(sensor)
            type_msg = "data"
            payload = build_payload(sensor, value, type_msg)

            client.sendall((payload + "\n").encode())

            print(f"Enviado ao sender: {sensor}")

        time.sleep(args.interval)

if __name__ == "__main__":
    main()