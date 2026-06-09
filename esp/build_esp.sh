#!/bin/bash

mkdir build

arduino-cli compile --fqbn esp32:esp32:esp32 --build-path ./build

mv build/esp.ino.bin .
rm -rf build