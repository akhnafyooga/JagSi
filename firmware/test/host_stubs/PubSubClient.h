#pragma once
#include <functional>
class PubSubClient {
 public:
  template <class C> explicit PubSubClient(C&) {}
  void setServer(const char*, uint16_t) {}
  void setCallback(void (*)(char*, uint8_t*, unsigned int)) {}
  bool setBufferSize(uint16_t) { return true; }
  void setKeepAlive(uint16_t) {}
  void setSocketTimeout(uint16_t) {}
  bool connect(const char*, const char*, uint8_t, bool, const char*) { return true; }
  bool connect(const char*, const char*, const char*, const char*, uint8_t, bool, const char*) { return true; }
  bool publish(const char*, const char*) { return true; }
  bool publish(const char*, const uint8_t*, unsigned int, bool) { return true; }
  bool subscribe(const char*, uint8_t = 0) { return true; }
  bool connected() { return true; }
  bool loop() { return true; }
  int state() { return 0; }
};
struct WiFiClient {};
