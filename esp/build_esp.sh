#!/bin/bash

TARGET_DIR="${1:-.}"

BUILD_DIR="$TARGET_DIR/build"

mkdir -p "$BUILD_DIR"

arduino-cli compile  --fqbn esp32:esp32:esp32  --build-path "$BUILD_DIR"  "$TARGET_DIR"

mv "$BUILD_DIR"/*.bin "$TARGET_DIR/"
rm -rf "$BUILD_DIR"