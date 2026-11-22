// Host-side stand-ins for the Arduino-ESP32 API, used ONLY by check_sketch.sh
// so g++ can type-check sketch.ino. Nothing here runs on the watch.
#pragma once
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <string>
#include <algorithm>
#include <ctime>
using std::min; using std::max;
typedef std::string String;
typedef uint8_t byte;
typedef bool boolean;
#define F(x) (x)
#define INPUT_PULLUP 2
#define OUTPUT 1
#define LOW 0
#define HIGH 1
#define WIFI_STA 1
#define WL_CONNECTED 3
inline unsigned long millis() { return 0; }
inline void delay(unsigned long) {}
inline int analogRead(int) { return 0; }
inline void analogReadResolution(int) {}
inline void pinMode(int, int) {}
inline int digitalRead(int) { return 1; }
inline void digitalWrite(int, int) {}
inline long map(long x, long a, long b, long c, long d) { return (x - a) * (d - c) / (b - a) + c; }
inline uint32_t esp_random() { return 4; }
inline void configTime(long, int, const char*, const char* = nullptr) {}
struct SerialT {
  void begin(long) {}
  int printf(const char *fmt, ...) __attribute__((format(printf, 2, 3))) { return 0; }
  void println(const char*) {}
  void println() {}
  void print(const char*) {}
} Serial;
struct IPAddress { String toString() const { return "0.0.0.0"; } };
struct WiFiT {
  int status() { return 0; }
  IPAddress localIP() { return {}; }
  int RSSI() { return -60; }
  void mode(int) {}
  void begin(const char*, const char*, int = 0) {}
  void disconnect() {}
} WiFi;
struct TwoWire { void begin(int, int) {} } Wire;
using std::isnan;
#define SENSORS_GRAVITY_STANDARD 9.80665f
#define SENSORS_RADS_TO_DPS 57.29577793f
