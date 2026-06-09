#!/bin/bash
touch a
mkdir build

arduino-cli compile --fqbn esp32:esp32:esp32 --build-path ./build
sleep 1

mv build/esp.ino.bin .
rm -rf build