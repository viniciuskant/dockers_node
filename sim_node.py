import argparse
import random
import time
import json
import signal
import sys
import logging
import os
import ssl  #
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

SENSORES = ["temperatura", "umidade", "pressao", "co2", "co", "so2", "no2", "ozonio", "pm25"]

SENSOR_CONFIGS = {
    "temperatura": {"min": -10, "max": 45, "unit": "°C", "decimals": 1},
    "umidade": {"min": 0, "max": 100, "unit": "%", "decimals": 1},
    "pressao": {"min": 950, "max": 1050, "unit": "hPa", "decimals": 1},
    "co2": {"min": 300, "max": 2000, "unit": "ppm", "decimals": 0},
    "co": {"min": 0, "max": 50, "unit": "ppm", "decimals": 1},
    "so2": {"min": 0, "max": 20, "unit": "ppm", "decimals": 1},
    "no2": {"min": 0, "max": 30, "unit": "ppm", "decimals": 1},
    "ozonio": {"min": 0, "max": 10, "unit": "ppm", "decimals": 2},
    "pm25": {"min": 0, "max": 500, "unit": "µg/m³", "decimals": 0},
}

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

class MQTTSensorSimulator:
    def __init__(self, broker_host, broker_port=8883, error_rate=0.0, mac_count=1):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.error_rate = error_rate
        self.mac_count = mac_count
        self.device_macs = self._generate_macs(mac_count)
        self.client = None
        self.running = True

        self.last_values = {}
        self.directions = {}
        self.steps_remaining = {}

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _is_docker(self):
        return os.path.exists("/.dockerenv")

    def _get_certs_paths(self):
        if self._is_docker():
            # arquivos mapeados para a pasta /app/certs/
            base_path = "/app/certs"
        else:
            # fora do container, busca diretamente na home do usuário atual
            base_path = os.path.expanduser("~")

        return {
            "ca": os.path.join(base_path, "ca.crt"),
            "cert": os.path.join(base_path, "cliente.crt"),
            "key": os.path.join(base_path, "cliente.key")
        }

    def _get_device_mac(self):
        if self._is_docker():
            mac = os.getenv("DEVICE_MAC")
            if mac:
                return mac.strip().lower()

        interfaces = ["eth0", "enp0s3", "ens33", "wlan0", "wlp2s0"]
        for iface in interfaces:
            path = f"/sys/class/net/{iface}/address"
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        mac = f.read().strip().lower()
                    if mac and mac != "00:00:00:00:00:00":
                        return mac
                except:
                    pass
        return None

    def _generate_macs(self, count):
        macs = [self._get_device_mac()]
        for _ in range(count - 1):
            mac_bytes = [random.randint(0x00, 0xff) for _ in range(6)]
            mac = ':'.join(f'{b:02x}' for b in mac_bytes)
            macs.append(mac)
        return macs

    def _get_random_mac(self):
        return random.choice(self.device_macs)

    def _signal_handler(self, signum, frame):
        logging.info("Encerrando simulador...")
        self.running = False
        if self.client:
            self.client.disconnect()
        sys.exit(0)

    def _generate_sensor_value(self, mac, sensor_name):
        if random.random() < self.error_rate:
            return None

        cfg = SENSOR_CONFIGS[sensor_name]
        min_val = cfg["min"]
        max_val = cfg["max"]
        range_val = max_val - min_val

        max_step_normal = range_val * 0.05
        max_step_peak = range_val * 0.2

        if mac not in self.last_values:
            self.last_values[mac] = {}
            self.directions[mac] = {}
            self.steps_remaining[mac] = {}

        last = self.last_values[mac].get(sensor_name)

        if last is None:
            new_val = round(random.uniform(min_val, max_val), cfg["decimals"])
            self.last_values[mac][sensor_name] = new_val
            self.directions[mac][sensor_name] = random.choice(['up', 'down'])
            self.steps_remaining[mac][sensor_name] = random.randint(15, 30)
            return new_val

        if self.steps_remaining[mac].get(sensor_name, 0) <= 0:
            current_dir = self.directions[mac].get(sensor_name, 'up')
            if random.random() < 0.1:
                self.directions[mac][sensor_name] = 'down' if current_dir == 'up' else 'up'
            self.steps_remaining[mac][sensor_name] = random.randint(15, 30)

        is_peak = random.random() < 0.2
        max_step = max_step_peak if is_peak else max_step_normal

        direction = self.directions[mac][sensor_name]
        if direction == 'up':
            delta = random.uniform(0, max_step)
        else:
            delta = random.uniform(-max_step, 0)

        new_val = last + delta

        if new_val > max_val:
            new_val = max_val
            self.directions[mac][sensor_name] = 'down'
            self.steps_remaining[mac][sensor_name] = random.randint(15, 30)
        elif new_val < min_val:
            new_val = min_val
            self.directions[mac][sensor_name] = 'up'
            self.steps_remaining[mac][sensor_name] = random.randint(15, 30)

        new_val = round(new_val, cfg["decimals"])
        self.last_values[mac][sensor_name] = new_val
        self.steps_remaining[mac][sensor_name] -= 1

        return new_val

    def _create_mqtt_message(self, sensor_name, value, mac):
        topic = sensor_name
        payload = {
            "mac": mac,
            "message": {
                "valor": value,
                "unidade": SENSOR_CONFIGS[sensor_name]["unit"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "modelo_sensor": "AA000",
                "status": "ok" if value is not None else "error"
            }
        }
        if value is None:
            payload["message"]["mensagem_erro"] = "Falha na leitura do sensor"
        return topic, json.dumps(payload)

    def _send_message(self, mac, sensor_name):
        if not self.client:
            logging.warning("Cliente MQTT não conectado")
            return

        value = self._generate_sensor_value(mac, sensor_name)
        topic, payload = self._create_mqtt_message(sensor_name, value, mac)

        try:
            result = self.client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"MAC {mac[-5:]} | {topic}: {value if value is not None else 'ERRO'}")
            else:
                logging.error(f"Erro ao publicar (código {result.rc})")
        except Exception as e:
            logging.error(f"Erro ao enviar: {e}")

    def _send_device_batch(self, mac, sensors_list):
        for sensor in sensors_list:
            if not self.running:
                break
            self._send_message(mac, sensor)
            time.sleep(0.05)

    def connect(self):
        self.client = mqtt.Client()

        paths = self._get_certs_paths()
        
        if not (os.path.exists(paths["ca"]) and os.path.exists(paths["cert"]) and os.path.exists(paths["key"])):
            logging.error(f"Certificados não encontrados nos caminhos calculados: {paths}")
            return False

        try:
            # Configura os certificados no canal seguro
            self.client.tls_set(
                ca_certs=paths["ca"],
                certfile=paths["cert"],
                keyfile=paths["key"],
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            # desativa a validação do hostname apenas se o CN do certificado do seu servidor 
            # não bater exatamente com o IP dele (teste local)
            self.client.tls_insecure_set(True) 
            
        except Exception as tls_err:
            logging.error(f"Falha ao carregar configurações TLS/mTLS: {tls_err}")
            return False

        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            logging.info(f"Conectado com mTLS seguro ao broker {self.broker_host}:{self.broker_port}")
            logging.info(f"Dispositivos simulados: {len(self.device_macs)} MACs")
            return True
        except Exception as e:
            logging.error(f"Erro ao conectar com segurança mTLS: {e}")
            return False

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logging.info("Desconectado do broker")

    def send_single_sensor(self, sensor_name, interval=1):
        logging.info(f"Modo SINGLE: enviando '{sensor_name}' a cada {interval}s")
        while self.running:
            mac = self._get_random_mac()
            self._send_message(mac, sensor_name)
            time.sleep(interval)

    def send_multiple_sensors_per_device(self, sensors_list, interval=1):
        logging.info(f"Modo MULTI: {len(sensors_list)} sensores por dispositivo, intervalo {interval}s")
        while self.running:
            for mac in self.device_macs:
                if not self.running:
                    break
                logging.debug(f"Enviando lote para {mac[-5:]}")
                self._send_device_batch(mac, sensors_list)
            time.sleep(interval)

    def send_batch(self, total_messages, sensors_list, interval=1):
        logging.info(f"Enviando {total_messages} mensagens aleatórias...")
        sent = 0
        while sent < total_messages and self.running:
            mac = self._get_random_mac()
            sensor = random.choice(sensors_list)
            self._send_message(mac, sensor)
            sent += 1
            logging.info(f"Progresso: {sent}/{total_messages}")
            time.sleep(interval)
        logging.info("Envio concluído")

def main():
    parser = argparse.ArgumentParser(description="Simulador de sensores MQTT")
    parser.add_argument("-H", "--host", default="localhost", help="Host do broker MQTT")
    parser.add_argument("-p", "--port", type=int, default=8883, help="Porta do broker MQTT")
    parser.add_argument("-s", "--sensors", default="temperatura,umidade", help="Lista de sensores separados por vírgula")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Intervalo entre mensagens (segundos)")
    parser.add_argument("-e", "--error", type=float, default=0.0, help="Taxa de erro (0.0 a 1.0)")
    parser.add_argument("-d", "--devices", type=int, default=1, help="Número de dispositivos (MACs) simulados")
    parser.add_argument("-b", "--batch", type=int, default=0, help="Envia exatamente N mensagens e encerra")
    parser.add_argument("-m", "--multi", action="store_true", help="Modo multi-dispositivo: cada dispositivo envia todos os sensores em lote")

    args = parser.parse_args()

    sensor_list = [s.strip() for s in args.sensors.split(",") if s.strip() in SENSORES]
    if not sensor_list:
        logging.error(f"Nenhum sensor válido. Opções: {', '.join(SENSORES)}")
        sys.exit(1)

    simulator = MQTTSensorSimulator(args.host, args.port, args.error, args.devices)

    if not simulator.connect():
        sys.exit(1)

    try:
        if args.batch > 0:
            simulator.send_batch(args.batch, sensor_list, args.interval)
        elif args.multi:
            simulator.send_multiple_sensors_per_device(sensor_list, args.interval)
        else:
            simulator.send_single_sensor(sensor_list[0], args.interval)
    except KeyboardInterrupt:
        logging.info("Interrompido pelo usuário")
    finally:
        simulator.disconnect()

if __name__ == "__main__":
    main()