#!/usr/bin/env bash
# Type-checks sketch.ino on a normal PC, in both transports, without a board or
# the ESP32 toolchain (issue #8). The Arduino and sensor APIs are replaced by the
# small stand-ins in host_stubs/; ArduinoJson is the real library.
#
#   firmware/test/check_sketch.sh /path/to/ArduinoJson/src
#
# It catches typos, wrong types and a broken #if branch. It does NOT prove the
# firmware runs: that still needs Wokwi or the board.
set -euo pipefail
AJ="${1:?usage: check_sketch.sh <ArduinoJson/src>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SK="$HERE/../jagsi-watch"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp "$SK/sketch.ino" "$TMP/sketch.cpp"
cp "$SK/motion_window.h" "$SK/azure_roots.h" "$SK/azure_method.h" "$TMP/"
FLAGS=(-std=gnu++17 -fsyntax-only -Wall -Wextra -Werror -Wno-unused-parameter
       -include "$HERE/host_stubs/arduino_stub.h" -I "$HERE/host_stubs" -I "$AJ" -I "$TMP")

echo "== public broker build =="
g++ "${FLAGS[@]}" "$TMP/sketch.cpp"
echo "== Azure IoT Hub build =="
cp "$SK/azure_config.example.h" "$TMP/azure_config.h"
g++ "${FLAGS[@]}" "$TMP/sketch.cpp"
echo "sketch.ino type-checks in both transports"
