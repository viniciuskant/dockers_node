#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$SCRIPT_DIR/build"

arduino-cli compile  --fqbn esp32:esp32:esp32  --build-path "$SCRIPT_DIR/build"

mv "$SCRIPT_DIR/build/esp.ino.bin" "$SCRIPT_DIR/"
rm -rf "$SCRIPT_DIR/build"