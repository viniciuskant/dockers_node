import socket
import sqlite3
import json
import os
import ssl
import time
import logging
import threading
import OpenSSL.crypto as crypto

import paho.mqtt.client as mqtt

HOST = "0.0.0.0"
PORT = 4815

BROKER = os.getenv("BROKER_HOST", "192.168.18.110")
BROKER_PORT = 8883

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def get_cn_from_cert(cert_path):
    with open(cert_path, "rb") as f:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    subject = cert.get_subject()
    for component in subject.get_components():
        if component[0].decode() == "CN":
            return component[1].decode()
    return None

DEVICE_ID = get_cn_from_cert("/app/certs/cliente.crt")

class MQTTSender:

    def __init__(self):
        self.username = "publisher"
        self._init_db()
        self.db_lock = threading.Lock()

        self.client = mqtt.Client()
        self.client.tls_set(
            ca_certs="/app/certs/ca.crt",
            certfile="/app/certs/cliente.crt",
            keyfile="/app/certs/cliente.key",
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )

        self.running = True
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()

    def _init_db(self):
        os.makedirs("/app/data", exist_ok=True)

        self.conn = sqlite3.connect(
            "/app/data/pending_messages.db",
            check_same_thread=False
        )

        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            payload TEXT,
            sent INTEGER DEFAULT 0
        )
        """)
        self.conn.commit()

    def connect_mqtt(self):
        while True:
            try:
                self.client.connect(BROKER, BROKER_PORT, 60)
                self.client.loop_start()
                logging.info("MQTT conectado")
                return
            except Exception as e:
                logging.error(f"MQTT offline: {e}")
                time.sleep(5)

    def save_pending(self, topic, payload):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO pending_messages(topic, payload)
            VALUES (?, ?)
            """, (topic, payload))
            self.conn.commit()

        logging.warning(
            f"SALVO | topic={topic} | payload={payload}"
        )

    def flush_pending(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            rows = cursor.execute("""
            SELECT id, topic, payload
            FROM pending_messages
            WHERE sent = 0
            """).fetchall()

        for row_id, topic, payload in rows:
            try:
                result = self.client.publish(topic, payload, qos=2)

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    with self.db_lock:
                        cursor = self.conn.cursor()
                        cursor.execute("""
                        UPDATE pending_messages
                        SET sent = 1
                        WHERE id = ?
                        """, (row_id,))
                        self.conn.commit()

                    logging.info(
                        f"FLUSH | topic={topic} | payload={payload}"
                    )

                    time.sleep(1)

            except Exception:
                continue

    def _flush_worker(self):
        while self.running:
            self.flush_pending()
            time.sleep(30 * 60) 

    def publish(self, topic, payload):
        try:
            result = self.client.publish(topic, payload, qos=2)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(
                    f"ENVIADO | topic={topic} | payload={payload}"
                )
            else:
                self.save_pending(topic, payload)

        except Exception:
            self.save_pending(topic, payload)

def main():
    sender = MQTTSender()
    sender.connect_mqtt()


    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )


    server.bind((HOST, PORT))
    server.listen(5)

    logging.info(f"Escutando porta {PORT}")

    try:
        while True:
            conn, addr = server.accept()
            logging.info(f"Conexão: {addr}")

            with conn:
                buffer = ""
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buffer += data.decode()

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        msg = json.loads(line)

                        if 'sensor' in msg:
                            topic = f"nodes/{DEVICE_ID}/{msg['type_msg']}/{msg['sensor']}"
                        else:
                            topic = f"nodes/{DEVICE_ID}/{msg['type_msg']}"

                        payload_message = json.dumps(msg["message"])
                        sender.publish(topic, payload_message)

    except KeyboardInterrupt:
        logging.info("Encerrando...")
        sender.running = False
        sender.flush_thread.join(timeout=2)
        sender.client.loop_stop()
        sender.conn.close()

if __name__ == "__main__":
    main()