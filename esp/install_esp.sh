#!/bin/bash
#
# Script para gravação do firmware no ESP32-S3 usando esptool.py
#
# Para evitar digitar a senha do sudo e permitir o uso do script sem senha:
#
#    Adicionar o usuário ao grupo dialout (acesso à porta serial sem sudo):
#    sudo usermod -a -G dialout $USER
#    (depois reinicie a sessão)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

PORT="${1:-/dev/ttyACM0}"

echo "Gravando firmware na porta $PORT"

# Tenta liberar a porta
if command -v fuser &> /dev/null; then
    echo "Liberando porta $PORT..."
    fuser -k "$PORT" 2>/dev/null || true
    sleep 1
fi

esptool --chip esp32s3 --port "$PORT" --baud 460800 \
  write-flash \
  0x0 bootloader.bin \
  0x8000 partition-table.bin \
  0x10000 esp_sensor_simulator.bin

echo "Gravação concluída"