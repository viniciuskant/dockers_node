import socket
import sqlite3
import json
import os
import ssl
import time
import logging

import paho.mqtt.client as mqtt

HOST = "0.0.0.0"
PORT = 4815

BROKER = os.getenv("BROKER_HOST", "192.168.18.110")
BROKER_PORT = 8883

logging.basicConfig(level=logging.INFO)

class MQTTSender:

    def __init__(self):
        self._init_db()
        self.client = mqtt.Client()
        self.client.tls_set(
            ca_certs="/app/certs/ca.crt",
            certfile="/app/certs/cliente.crt",
            keyfile="/app/certs/cliente.key",
            tls_version=ssl.PROTOCOL_TLSv1_2
        )

        self.client.tls_insecure_set(True)

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
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO pending_messages(topic, payload)
        VALUES (?, ?)
        """, (topic, payload))
        self.conn.commit()

    def flush_pending(self):
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
                    cursor.execute("""
                    UPDATE pending_messages
                    SET sent = 1
                    WHERE id = ?
                    """, (row_id,))
                    self.conn.commit()
                    logging.info(f"Flush OK {row_id}")
            except Exception:
                continue

    def publish(self, topic, payload):
        try:
            result = self.client.publish(topic, payload, qos=2)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"Publicado: {topic}")
                self.flush_pending()
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
                    topic = msg["sensor"]
                    sender.publish(topic, line)

if __name__ == "__main__":
    main()