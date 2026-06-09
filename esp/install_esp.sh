#!/bin/bash

set -e

FILE_ESP="esp/esp.ino.bin"
MAX_RETRIES=3
ESPTOOL_BAUD=115200
ESP_FLASH_ADDR=0x10000

# Função para encontrar ESP32
find_esp32_port() {
    for porta in /dev/ttyUSB* /dev/ttyACM* /dev/ttyS*; do
        if [ -e "$porta" ]; then
            echo "Usando porta: $porta" >&2
            echo "$porta"
            return
        fi
    done
}

# Verificar esptool
if command -v esptool &> /dev/null; then
    CMD_ESPTOOL="esptool"
elif command -v esptool.py &> /dev/null; then
    CMD_ESPTOOL="esptool.py"
else
    echo "ERRO: esptool não encontrado."
    exit 1
fi

PORTA_ESP=$(find_esp32_port)

if [ -z "$PORTA_ESP" ]; then
    echo "ERRO: Nenhum ESP32 encontrado"
    echo "Portas disponíveis:"
    ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  Nenhuma porta serial encontrada"
    exit 1
fi

echo "SUCESSO: ESP32 localizado na porta: $PORTA_ESP"

echo "Liberando porta $PORTA_ESP..."
if command -v fuser &> /dev/null; then
    sudo fuser -k "$PORTA_ESP" 2>/dev/null || true
else
    echo "AVISO: fuser não disponível, pulando liberação da porta"
fi

sleep 1

# Gravação com retry
SUCCESS=false
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$SUCCESS" = false ]; do
    echo "=== Tentativa $((RETRY_COUNT+1)) de $MAX_RETRIES ==="
    
    if $CMD_ESPTOOL --chip esp32 --port "$PORTA_ESP" --baud $ESPTOOL_BAUD \
        --before default_reset --after hard_reset write_flash \
        $ESP_FLASH_ADDR "$FILE_ESP"; then
        
        echo "SUCESSO: Gravação completada!"
        SUCCESS=true
        
        sleep 2
        
        # Verificação pós-gravação
        echo "Verificando ESP32 após gravação..."
        if timeout 5s $CMD_ESPTOOL --port "$PORTA_ESP" chip_id >/dev/null 2>&1; then
            echo "ESP32 respondendo corretamente após gravação"
        else
            echo "AVISO: ESP32 não responde após gravação (pode ser normal durante reboot)"
        fi
    else
        echo "ERRO: Falha na tentativa $((RETRY_COUNT+1))"
        RETRY_COUNT=$((RETRY_COUNT+1))
        
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Aguardando 5 segundos antes da próxima tentativa..."
            sleep 5
            
            # Reset na porta
            sudo fuser -k "$PORTA_ESP" 2>/dev/null || true
            sleep 1
        fi
    fi
done

if [ "$SUCCESS" = false ]; then
    echo "ERRO FATAL: Falha após $MAX_RETRIES tentativas"
    exit 1
fi

echo "ESP32 atualizado!"

exit 0