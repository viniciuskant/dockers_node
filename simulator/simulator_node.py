import json
from datetime import datetime, timezone
import socket
import time
import json
import random
import argparse
import os
import logging
import serial
import glob

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

HOST = "0.0.0.0"

SENDER_PORT = os.getenv("SENDER_PORT")
if SENDER_PORT is None:
    raise EnvironmentError("Variável SENDER_PORT não definida")
SENDER_PORT = int(SENDER_PORT)

SENDER_HOST = os.getenv("SENDER_HOST")
if SENDER_HOST is None:
    raise EnvironmentError("Variável SENDER_HOST não definida")

def find_serial_port():
    patterns = ["/dev/ttyACM*", "/dev/ttyUSB*"]
    for pattern in patterns:
        ports = glob.glob(pattern)
        for port in ports:
            try:
                ser = serial.Serial(port, 115200, timeout=0.3)
                ser.close()
                return port
            except:
                continue
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sensors", default="temperatura")
    parser.add_argument("-i", "--interval", type=float, default=2)
    parser.add_argument("-e", "--error", type=float, default=0.0)
    args = parser.parse_args()

    serial_port = None
    while serial_port is None:
        serial_port = find_serial_port()
        if serial_port is None:
            logger.info("Aguardando dispositivo serial em /dev/ttyACM* ou /dev/ttyUSB*...")
            time.sleep(2)
    logger.info(f"Conectando ao dispositivo serial: {serial_port}")
    ser = serial.Serial(serial_port, 115200, timeout=0.3)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            client.connect((SENDER_HOST, SENDER_PORT))
            logger.info(f"Conectado ao sender {SENDER_HOST}:{SENDER_PORT}")
            break
        except:
            logger.info(f"Aguardando sender ({SENDER_HOST}:{SENDER_PORT})...")
            time.sleep(2)

    while True:
        try:
            ser.reset_input_buffer()
            ser.write(b"readSensors\n")
            logger.info("Comando 'readSensors' enviado")

            while True:
                line = ser.readline().decode().strip()
                if not line:
                    break

                try:
                    data = json.loads(line)

                    data.pop("timestamp", None)
                    data["timestamp"] = datetime.now(timezone.utc).isoformat()

                    message = json.dumps(data)

                    client.sendall((message + "\n").encode())
                    logger.info(f"Enviado ao sender: {message[:100]}")

                except json.JSONDecodeError:
                    logger.warning(f"Linha não é JSON válido: {line}")
        except serial.SerialException as e:
            logger.error(f"Erro na serial: {e}. Tentando reabrir...")
            ser.close()
            time.sleep(2)
            while True:
                serial_port = find_serial_port()
                if serial_port:
                    try:
                        ser = serial.Serial(serial_port, 115200, timeout=0.3)
                        logger.info(f"Reconectado na serial {serial_port}")
                        break
                    except:
                        pass
                time.sleep(2)

if __name__ == "__main__":
    main()