#!/bin/bash

BASE_DIR="$(pwd)"
CERT_DIR="$BASE_DIR/certificados"
SIMULACAO_DIR="$BASE_DIR/simulacao"
VERSION_DOCKER="2.1.0_simulacao"
MQTT_PORT="8883"
BROKER_HOST="100.117.53.35"

# cria rede global única
docker network inspect global_iot_network >/dev/null 2>&1 || \
    docker network create --driver bridge --subnet=172.30.0.0/16 global_iot_network

mkdir -p "$SIMULACAO_DIR"

#template do docker-compose.yml (sem ports, com rede externa)
cat > "$SIMULACAO_DIR/docker-compose.template.yml" << 'EOF'
services:
  sender:
    build:
      context: ./sender
      dockerfile: Dockerfile
    container_name: mqtt-sender-${HOSTNAME}-${VERSION_DOCKER}
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./certs:/app/certs
    environment:
      VERSION_DOCKER: ${VERSION_DOCKER}
      BROKER_HOST: ${BROKER_HOST}
      MQTT_PORT: ${MQTT_PORT}
    networks:
      - iot_network

  simulator:
    build:
      context: ./simulator
      dockerfile: Dockerfile
    container_name: simulator-${HOSTNAME}-${VERSION_DOCKER}
    restart: unless-stopped
    environment:
      SENDER_HOST: mqtt-sender-${HOSTNAME}-${VERSION_DOCKER}
      SENDER_PORT: 4815
    depends_on:
      - sender
    networks:
      - iot_network

networks:
  iot_network:
    external: true
    name: global_iot_network
EOF

for node in "$CERT_DIR"/*; do
  if [ -d "$node" ]; then
    node_name=$(basename "$node")
    echo ">>> Processando $node_name ..."

    work_dir="$SIMULACAO_DIR/$node_name"
    mkdir -p "$work_dir"

    cp -r "$BASE_DIR/sender" "$work_dir/"
    cp -r "$BASE_DIR/simulator" "$work_dir/"
    cp "$SIMULACAO_DIR/docker-compose.template.yml" "$work_dir/docker-compose.yml"

    mkdir -p "$work_dir/data"
    ln -sfn "$node" "$work_dir/certs"

    cd "$work_dir"

    export HOSTNAME="$node_name"
    export VERSION_DOCKER="$VERSION_DOCKER"
    export MQTT_PORT="$MQTT_PORT"
    export BROKER_HOST="$BROKER_HOST"

    docker-compose up -d --build

    cd "$BASE_DIR"
  fi
done
