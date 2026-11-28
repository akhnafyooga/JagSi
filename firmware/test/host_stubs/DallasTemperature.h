#pragma once
#define DEVICE_DISCONNECTED_C -127
using DeviceAddress = uint8_t[8];
struct DallasTemperature {
  explicit DallasTemperature(OneWire*) {}
  void begin() {}
  int getDeviceCount() { return 1; }
  bool getAddress(DeviceAddress, int) { return true; }
  void setWaitForConversion(bool) {}
  void setResolution(DeviceAddress, uint8_t) {}
  void requestTemperatures() {}
  void requestTemperaturesByAddress(DeviceAddress) {}
  float getTempC(DeviceAddress) { return 36.5f; }
  float getTempCByIndex(int) { return 36.5f; }
};
