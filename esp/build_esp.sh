#!/bin/bash

set -e

source $HOME/esp/esp-idf/export.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

idf.py set-target esp32s3
idf.py build > /dev/null

mkdir -p ../firmware_esp
cp build/bootloader/bootloader.bin ../firmware_esp/
cp build/partition_table/partition-table.bin ../firmware_esp/
cp build/esp_sensor_simulator.bin ../firmware_esp/
cp build/flash_args ../firmware_esp/
cp install_esp.sh ../firmware_esp/

rm -rf build dependencies.lock managed_components sdkconfig.old sdkconfig 2>/dev/null
