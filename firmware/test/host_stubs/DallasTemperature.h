#pragma once
#define DEVICE_DISCONNECTED_C -127
struct DallasTemperature { explicit DallasTemperature(OneWire*) {} void begin() {} int getDeviceCount() { return 1; } void setWaitForConversion(bool) {} void requestTemperatures() {} float getTempCByIndex(int) { return 36.5f; } };
