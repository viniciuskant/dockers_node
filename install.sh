#!/bin/bash

set -e

TARGET_DIR="$HOME/dockers_node"
HISTORY_DIR="$HOME/history"
TEMP_DIR="/tmp/update_docker_temp/extract"

ENV_FILE="$TEMP_DIR/.env"

source "$ENV_FILE"

COMPOSE_FILE="$TARGET_DIR/docker-compose.yml"

ROLLBACK_NEEDED=false

rollback() {
    ERROR_CODE=$?

    if [ "$ROLLBACK_NEEDED" = true ]; then
        echo "ERRO DETECTADO - EXECUTANDO ROLLBACK"

        if [ -f "$HISTORY_DIR/last/docker-compose.yml" ]; then

            rm -rf "$TARGET_DIR"
            mkdir -p "$TARGET_DIR"

            cp -r "$HISTORY_DIR/last/"* "$TARGET_DIR/" || true
            cp -r "$HISTORY_DIR/last/".env "$TARGET_DIR/" || true

            cd "$TARGET_DIR"

            docker-compose down || true
            docker-compose up -d --build
        fi
    fi

    exit $ERROR_CODE
}

trap rollback ERR

echo "HOSTNAME=$HOSTNAME"
echo "VERSION_DOCKER=$VERSION_DOCKER"

# Backup
echo "CRIANDO BACKUP"

rm -rf "$HISTORY_DIR/last"
mkdir -p "$HISTORY_DIR/last"

cp -rf "$TARGET_DIR/"* "$HISTORY_DIR/last/" || true
cp -rf "$TARGET_DIR/".env "$HISTORY_DIR/last/" || true

# Atualiza arquivos
rm -rf "$TARGET_DIR" 2>/dev/null || true
mkdir -p "$TARGET_DIR"

cp -r "$TEMP_DIR/"* "$TARGET_DIR/"
cp "$TEMP_DIR/.env" "$TARGET_DIR/"

# Certificados
mkdir -p "$TARGET_DIR/certs/"
mkdir -p "$TARGET_DIR/data/"

cp "$HOME/ca.crt" "$TARGET_DIR/certs/"
cp "$HOME/cliente.crt" "$TARGET_DIR/certs/"
cp "$HOME/cliente.key" "$TARGET_DIR/certs/"


# subindo stack
cd "$TARGET_DIR"
ROLLBACK_NEEDED=true
docker-compose down || true

#!/bin/bash

docker-compose up -d sender

PORT=$(docker port mqtt-sender-${HOSTNAME}-${VERSION_DOCKER} 4815/tcp | cut -d: -f2)

printf '\nSENDER_PORT=%s\n' "$PORT" >> ./sender/.env
printf '\nexport SENDER_PORT=%s\n' "$PORT" >> .env

docker-compose up -d simulator

# validacao
docker ps | grep "mqtt-sender-${HOSTNAME}-${VERSION_DOCKER}" >/dev/null
docker ps | grep "simulator-${HOSTNAME}-${VERSION_DOCKER}" >/dev/null

ROLLBACK_NEEDED=false

exit 0