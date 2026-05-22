#!/bin/bash

set -e

TARGET_DIR="$HOME/dockers_node"
HISTORY_DIR="$HOME/history"
TEMP_DIR="/tmp/update_docker_temp/extract"

source "$TEMP_DIR/.env"

NEW_SENDER="mqtt-sender-${HOSTNAME}-${VERSION_DOCKER}"
NEW_SIMULATOR="simulator-${HOSTNAME}-${VERSION_DOCKER}"

OLD_SENDER=$(docker ps -a --format '{{.Names}}' | grep '^mqtt-sender-' | head -n1 || true)
OLD_SIMULATOR=$(docker ps -a --format '{{.Names}}' | grep '^simulator-' | head -n1 || true)

ROLLBACK_NEEDED=false

rollback() {
    ERROR_CODE=$?

    if [ "$ROLLBACK_NEEDED" = true ]; then
        echo "ERRO DETECTADO - EXECUTANDO ROLLBACK"

        if [ ! -z "$OLD_SENDER" ]; then
            docker start "$OLD_SENDER" || true
        fi

        if [ ! -z "$OLD_SIMULATOR" ]; then
            docker start "$OLD_SIMULATOR" || true
        fi
    fi

    exit $ERROR_CODE
}

trap rollback ERR

echo "OLD_SENDER=$OLD_SENDER"
echo "OLD_SIMULATOR=$OLD_SIMULATOR"

# Backup
rm -rf "$HISTORY_DIR/last"
mkdir -p "$HISTORY_DIR/last"

cp -rf "$TARGET_DIR/"* "$HISTORY_DIR/last/" || true

# Atualiza arquivos
rm -rf "$TARGET_DIR/" 2>/dev/null || true
mkdir -p "$TARGET_DIR/"

cp -r "$TEMP_DIR/"* "$TARGET_DIR"

# Certificados
mkdir -p "$TARGET_DIR/certs/"
mkdir -p "$TARGET_DIR/data/"

cp "$HOME/ca.crt" "$TARGET_DIR/certs/"
cp "$HOME/cliente.crt" "$TARGET_DIR/certs/"
cp "$HOME/cliente.key" "$TARGET_DIR/certs/"

cd "$TARGET_DIR"

# Rede
docker network inspect iot_network >/dev/null 2>&1 || \
docker network create iot_network

echo "BUILD IMAGES"

docker build -t "$NEW_SENDER" ./sender
docker build -t "$NEW_SIMULATOR" ./simulator

# A partir daqui rollback será necessário
ROLLBACK_NEEDED=true

echo "PARANDO CONTAINERS ANTIGOS"

if [ ! -z "$OLD_SIMULATOR" ]; then
    docker stop "$OLD_SIMULATOR"
fi

if [ ! -z "$OLD_SENDER" ]; then
    docker stop "$OLD_SENDER"
fi

echo "START NEW SENDER"

docker run -d \
  --name "$NEW_SENDER" \
  --restart unless-stopped \
  -p 4815:4815 \
  -v "$TARGET_DIR/data:/app/data" \
  -v "$TARGET_DIR/certs:/app/certs" \
  -e BROKER_HOST="$SERVER" \
  --network iot_network \
  "$NEW_SENDER"

sleep 10

docker ps | grep "$NEW_SENDER" >/dev/null

echo "START NEW SIMULATOR"

docker run -d \
  --name "$NEW_SIMULATOR" \
  --restart unless-stopped \
  -e DEVICE_MAC="$DEVICE_MAC" \
  -e SENDER_HOST="$NEW_SENDER" \
  --network iot_network \
  "$NEW_SIMULATOR"

sleep 10

docker ps | grep "$NEW_SIMULATOR" >/dev/null

echo "REMOVENDO ANTIGOS"

if [ ! -z "$OLD_SENDER" ] && [ "$OLD_SENDER" != "$NEW_SENDER" ]; then
    docker rm -f "$OLD_SENDER" || true
fi

if [ ! -z "$OLD_SIMULATOR" ] && [ "$OLD_SIMULATOR" != "$NEW_SIMULATOR" ]; then
    docker rm -f "$OLD_SIMULATOR" || true
fi

ROLLBACK_NEEDED=false

echo "DEPLOY FINALIZADO"

exit 0
