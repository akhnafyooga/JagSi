#pragma once
enum { MPU6050_RANGE_8_G, MPU6050_RANGE_500_DEG, MPU6050_BAND_21_HZ };
struct vec { float x, y, z; };
struct sensors_event_t { vec acceleration; vec gyro; float temperature; };
struct Adafruit_MPU6050 { bool begin() { return true; } void setAccelerometerRange(int) {} void setGyroRange(int) {} void setFilterBandwidth(int) {} bool getEvent(sensors_event_t*, sensors_event_t*, sensors_event_t*) { return true; } };
