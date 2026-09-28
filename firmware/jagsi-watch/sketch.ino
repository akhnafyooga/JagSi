/*
 * JagSi (Jaga Lansia) - Wearable firmware, Sprint 1
 * Issue #6: Program MQTT pub/sub data pipeline
 *
 * What this does:
 *   - Reads the sensors (10 Hz):
 *       MPU6050  -> accelerometer + gyroscope (motion vectors, fall rule)
 *       DS18B20  -> body temperature
 *       2 potentiometers -> heart rate and SpO2 (stand-in for MAX30102,
 *                           because Wokwi has no MAX30102 part)
 *       1 potentiometer  -> battery level (simulation only)
 *       Push button      -> manual SOS
 *   - Publishes telemetry, events and status to an MQTT broker as JSON.
 *   - Subscribes to a command topic (ping, set_interval, ack_alert).
 *
 * Topic and payload rules: see docs/mqtt-contract.md
 *
 * Board: ESP32 DevKit (Arduino core). Runs on Wokwi (wokwi.com).
 * Libraries: PubSubClient, ArduinoJson (v7), Adafruit MPU6050,
 *            Adafruit Unified Sensor, OneWire, DallasTemperature
 */

#include <WiFi.h>
#include <Wire.h>
#include <time.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ------------------------------------------------------------------
// Settings (change here)
// ------------------------------------------------------------------
#define FW_VERSION      "0.1.0"
#define DEVICE_ID       "jagsi-watch-01"      // = WEARABLE_DEVICE.device_id

#define WIFI_SSID       "Wokwi-GUEST"         // Wokwi's virtual Wi-Fi
#define WIFI_PASSWORD   ""
#define WIFI_CHANNEL    6                     // Wokwi-GUEST is on channel 6 (faster connect)

#define MQTT_HOST       "broker.hivemq.com"   // public test broker (dummy data only!)
#define MQTT_PORT       1883
#define TOPIC_BASE      "jagsi/abal/v1/"

// Pins
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22
#define PIN_ONEWIRE     4     // DS18B20 data
#define PIN_SOS_BUTTON  18    // button to GND, internal pull-up
#define PIN_ALERT_LED   26    // blinks while an alert is not yet acknowledged
#define PIN_POT_HR      34    // heart rate (simulated)
#define PIN_POT_SPO2    35    // SpO2 (simulated)
#define PIN_POT_BATT    32    // battery level (simulated)

// Timing
#define SENSOR_SAMPLE_MS        100     // 10 Hz sensor sampling
#define TEMP_READ_MS            1000    // DS18B20 read every 1 s
#define DEFAULT_TELEMETRY_MS    2000    // publish telemetry every 2 s
#define MIN_TELEMETRY_MS        1000
#define MAX_TELEMETRY_MS        60000
#define WIFI_RETRY_MS           10000
#define MQTT_RETRY_MS           5000
#define ALERT_RESEND_MS         5000    // re-send an event until "ack_alert"
#define ALERT_MAX_ATTEMPTS      5
#define FALL_COOLDOWN_MS        10000
#define DEBOUNCE_MS             50

// Temporary fall rule (the ML model from issue #9 will replace this)
#define FALL_THRESHOLD_G        2.5f

// Simulated vital sign ranges (potentiometer 0..4095 -> range)
#define HR_MIN   40
#define HR_MAX   180
#define SPO2_MIN 80.0f
#define SPO2_MAX 100.0f

// ------------------------------------------------------------------
// Global objects and state
// ------------------------------------------------------------------
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);
Adafruit_MPU6050  mpu;
OneWire           oneWire(PIN_ONEWIRE);
DallasTemperature tempSensor(&oneWire);

char topicTelemetry[64];
char topicEvent[64];
char topicStatus[64];
char topicCmd[64];
char clientId[40];
char bootId[9];            // random per boot, makes event_id unique

bool mpuOk = false;
bool tempOk = false;

// Latest sensor values
struct Vitals {
  int   heartRate = 0;
  float spo2 = 0;
  float bodyTemp = NAN;    // NAN = no reading
  int   battery = 0;
  float ax = 0, ay = 0, az = 0;     // g
  float gx = 0, gy = 0, gz = 0;     // deg/s
  float peakG = 0;                  // highest |a| since last telemetry
} v;

unsigned long telemetryIntervalMs = DEFAULT_TELEMETRY_MS;
unsigned long lastSampleMs = 0, lastTempMs = 0, lastTelemetryMs = 0;
unsigned long lastWifiTryMs = 0, lastMqttTryMs = 0, lastFallMs = 0;
uint32_t telemetrySeq = 0;
uint32_t eventSeq = 0;
bool fallArmed = true;     // true = a new fall may be detected

// SOS button (debounced)
int sosStableState = HIGH;
int sosLastReading = HIGH;
unsigned long sosLastChangeMs = 0;

// Alerts waiting for "ack_alert"
#define MAX_PENDING_ALERTS 4
struct PendingAlert {
  bool active = false;
  char eventId[48];
  char alertType[16];
  char ts[25];              // time of the event, kept the same on every re-send
  unsigned long uptimeMs = 0;
  float peakG = 0;
  int heartRate = 0;
  float spo2 = 0;
  float bodyTemp = NAN;
  uint8_t attempts = 0;
  unsigned long lastSendMs = 0;
} pending[MAX_PENDING_ALERTS];

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------
double round2(float x) { return (double)lroundf(x * 100.0f) / 100.0; }

// Writes "2026-09-28T12:00:00Z" into buf. Returns false if time is not synced yet.
bool isoTimeNow(char *buf, size_t len) {
  time_t now = time(nullptr);
  if (now < 1700000000) return false;          // NTP not synced yet
  struct tm t;
  gmtime_r(&now, &t);
  strftime(buf, len, "%Y-%m-%dT%H:%M:%SZ", &t);
  return true;
}

void putTime(JsonDocument &doc, const char *key, const char *isoOrEmpty) {
  if (isoOrEmpty[0]) doc[key] = isoOrEmpty;
  else doc[key] = nullptr;
}

void putNullableFloat(JsonVariant dst, float x) {
  if (isnan(x)) dst.set(nullptr);
  else dst.set(round2(x));
}

bool publishJson(const char *topic, JsonDocument &doc, bool retained) {
  char buf[768];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  if (n == 0 || n >= sizeof(buf) - 1) {
    Serial.println(F("[MQTT] payload too big, not sent"));
    return false;
  }
  bool ok = mqtt.publish(topic, (const uint8_t *)buf, n, retained);
  Serial.printf("[MQTT] %s %s (%u bytes)\n", ok ? "->" : "FAILED", topic, (unsigned)n);
  return ok;
}

// ------------------------------------------------------------------
// Sensors
// ------------------------------------------------------------------
void setupSensors() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  mpuOk = mpu.begin();
  if (mpuOk) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);   // big enough to see a fall impact
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println(F("[SENSOR] MPU6050 OK"));
  } else {
    Serial.println(F("[SENSOR] MPU6050 NOT FOUND - check wiring"));
  }

  tempSensor.begin();
  tempOk = tempSensor.getDeviceCount() > 0;
  tempSensor.setWaitForConversion(false);   // do not block the loop for 750 ms
  if (tempOk) {
    tempSensor.requestTemperatures();
    Serial.println(F("[SENSOR] DS18B20 OK"));
  } else {
    Serial.println(F("[SENSOR] DS18B20 NOT FOUND - body_temperature will be null"));
  }

  pinMode(PIN_SOS_BUTTON, INPUT_PULLUP);
  pinMode(PIN_ALERT_LED, OUTPUT);
  digitalWrite(PIN_ALERT_LED, LOW);
  analogReadResolution(12);                 // 0..4095
}

void readSimulatedVitals() {
  // TODO (real hardware): replace with MAX30102 readings.
  v.heartRate = map(analogRead(PIN_POT_HR), 0, 4095, HR_MIN, HR_MAX);
  v.spo2 = SPO2_MIN + (SPO2_MAX - SPO2_MIN) * analogRead(PIN_POT_SPO2) / 4095.0f;
  v.battery = map(analogRead(PIN_POT_BATT), 0, 4095, 0, 100);
}

void readImu() {
  if (!mpuOk) return;
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);
  v.ax = a.acceleration.x / SENSORS_GRAVITY_STANDARD;   // m/s^2 -> g
  v.ay = a.acceleration.y / SENSORS_GRAVITY_STANDARD;
  v.az = a.acceleration.z / SENSORS_GRAVITY_STANDARD;
  v.gx = g.gyro.x * SENSORS_RADS_TO_DPS;                // rad/s -> deg/s
  v.gy = g.gyro.y * SENSORS_RADS_TO_DPS;
  v.gz = g.gyro.z * SENSORS_RADS_TO_DPS;
  float mag = sqrtf(v.ax * v.ax + v.ay * v.ay + v.az * v.az);
  if (mag > v.peakG) v.peakG = mag;
}

void readTemperature() {
  if (!tempOk) return;
  float c = tempSensor.getTempCByIndex(0);
  v.bodyTemp = (c == DEVICE_DISCONNECTED_C) ? NAN : c;
  tempSensor.requestTemperatures();          // start the next conversion
}

// ------------------------------------------------------------------
// Alerts (SOS + fall)
// ------------------------------------------------------------------
void raiseAlert(const char *type, float peakG) {
  int slot = -1;
  for (int i = 0; i < MAX_PENDING_ALERTS; i++) {
    if (!pending[i].active) { slot = i; break; }
  }
  if (slot < 0) {                            // all full: overwrite the oldest
    slot = 0;
    for (int i = 1; i < MAX_PENDING_ALERTS; i++) {
      if (pending[i].uptimeMs < pending[slot].uptimeMs) slot = i;
    }
  }
  PendingAlert &p = pending[slot];
  p.active = true;
  snprintf(p.eventId, sizeof(p.eventId), "%s-%s-%lu", DEVICE_ID, bootId, (unsigned long)++eventSeq);
  strlcpy(p.alertType, type, sizeof(p.alertType));
  if (!isoTimeNow(p.ts, sizeof(p.ts))) p.ts[0] = '\0';
  p.uptimeMs = millis();
  p.peakG = peakG;
  p.heartRate = v.heartRate;
  p.spo2 = v.spo2;
  p.bodyTemp = v.bodyTemp;
  p.attempts = 0;
  p.lastSendMs = 0;
  Serial.printf("[ALERT] %s raised (%s)\n", type, p.eventId);
}

bool sendAlert(PendingAlert &p) {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["event_id"] = p.eventId;
  putTime(doc, "ts", p.ts);
  doc["uptime_ms"] = p.uptimeMs;
  doc["alert_type"] = p.alertType;
  doc["status"] = "unresolved";
  doc["attempt"] = p.attempts + 1;
  doc["accel_peak_g"] = round2(p.peakG);
  JsonObject vit = doc["vitals"].to<JsonObject>();
  vit["heart_rate"] = p.heartRate;
  vit["spo2"] = round2(p.spo2);
  putNullableFloat(vit["body_temperature"].to<JsonVariant>(), p.bodyTemp);
  return publishJson(topicEvent, doc, false);
}

// Sends new alerts and re-sends old ones that were not acknowledged.
void serviceAlerts() {
  bool anyActive = false;
  unsigned long now = millis();
  for (int i = 0; i < MAX_PENDING_ALERTS; i++) {
    PendingAlert &p = pending[i];
    if (!p.active) continue;
    anyActive = true;
    if (!mqtt.connected()) continue;         // keep it, send after reconnect
    if (p.attempts > 0 && now - p.lastSendMs < ALERT_RESEND_MS) continue;
    if (sendAlert(p)) {
      p.attempts++;
      p.lastSendMs = now;
      if (p.attempts >= ALERT_MAX_ATTEMPTS) {
        Serial.printf("[ALERT] %s: no ack after %d sends, giving up\n", p.eventId, ALERT_MAX_ATTEMPTS);
        p.active = false;
      }
    }
  }
  // LED blinks while something is waiting for an ack
  digitalWrite(PIN_ALERT_LED, anyActive ? ((now / 250) % 2) : LOW);
}

void checkSosButton() {
  int reading = digitalRead(PIN_SOS_BUTTON);
  if (reading != sosLastReading) {
    sosLastChangeMs = millis();
    sosLastReading = reading;
  }
  if (millis() - sosLastChangeMs > DEBOUNCE_MS && reading != sosStableState) {
    sosStableState = reading;
    if (sosStableState == LOW) {             // pressed
      raiseAlert("manual_sos", v.peakG);
    }
  }
}

void checkFall() {
  if (!mpuOk) return;
  float mag = sqrtf(v.ax * v.ax + v.ay * v.ay + v.az * v.az);
  if (fallArmed && mag >= FALL_THRESHOLD_G && millis() - lastFallMs > FALL_COOLDOWN_MS) {
    lastFallMs = millis();
    fallArmed = false;                       // wait until movement is normal again
    raiseAlert("fall_detected", mag);
  } else if (!fallArmed && mag < FALL_THRESHOLD_G) {
    fallArmed = true;
  }
}

// ------------------------------------------------------------------
// Telemetry + status
// ------------------------------------------------------------------
void publishTelemetry() {
  char ts[25] = "";
  if (!isoTimeNow(ts, sizeof(ts))) ts[0] = '\0';

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["seq"] = ++telemetrySeq;
  putTime(doc, "ts", ts);
  doc["uptime_ms"] = millis();
  doc["heart_rate"] = v.heartRate;
  doc["spo2"] = round2(v.spo2);
  putNullableFloat(doc["body_temperature"].to<JsonVariant>(), v.bodyTemp);
  JsonObject a = doc["accel"].to<JsonObject>();
  a["x"] = round2(v.ax); a["y"] = round2(v.ay); a["z"] = round2(v.az);
  JsonObject g = doc["gyro"].to<JsonObject>();
  g["x"] = round2(v.gx); g["y"] = round2(v.gy); g["z"] = round2(v.gz);
  doc["accel_peak_g"] = round2(v.peakG);
  doc["battery_level"] = v.battery;
  doc["sim"] = true;

  if (publishJson(topicTelemetry, doc, false)) {
    v.peakG = 0;                             // start a new peak window
  }
}

void publishStatus() {
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["state"] = "online";
  doc["fw"] = FW_VERSION;
  doc["battery_level"] = v.battery;
  doc["rssi"] = WiFi.RSSI();
  doc["ip"] = WiFi.localIP().toString();
  doc["interval_ms"] = telemetryIntervalMs;
  publishJson(topicStatus, doc, true);       // retained
}

// ------------------------------------------------------------------
// Commands from the cloud (subscribe)
// ------------------------------------------------------------------
void onMqttMessage(char *topic, byte *payload, unsigned int length) {
  Serial.printf("[MQTT] <- %s: %.*s\n", topic, (int)length, (const char *)payload);
  if (strcmp(topic, topicCmd) != 0) return;

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.printf("[CMD] bad JSON: %s\n", err.c_str());
    return;
  }
  const char *cmd = doc["cmd"] | "";

  if (strcmp(cmd, "ping") == 0) {
    publishStatus();
  } else if (strcmp(cmd, "set_interval") == 0) {
    long ms = doc["ms"] | 0L;
    if (ms >= MIN_TELEMETRY_MS && ms <= MAX_TELEMETRY_MS) {
      telemetryIntervalMs = ms;
      Serial.printf("[CMD] telemetry interval = %ld ms\n", ms);
      publishStatus();
    } else {
      Serial.printf("[CMD] interval %ld ms out of range\n", ms);
    }
  } else if (strcmp(cmd, "ack_alert") == 0) {
    const char *id = doc["event_id"] | "";
    for (int i = 0; i < MAX_PENDING_ALERTS; i++) {
      if (pending[i].active && strcmp(pending[i].eventId, id) == 0) {
        pending[i].active = false;
        Serial.printf("[ALERT] %s acknowledged\n", id);
      }
    }
  } else {
    Serial.printf("[CMD] unknown command '%s'\n", cmd);
  }
}

// ------------------------------------------------------------------
// Wi-Fi + MQTT connection (non-blocking, retries in the background)
// ------------------------------------------------------------------
void maintainWifi() {
  static bool wasConnected = false;
  if (WiFi.status() == WL_CONNECTED) {
    if (!wasConnected) {
      wasConnected = true;
      Serial.printf("[WIFI] connected, IP %s\n", WiFi.localIP().toString().c_str());
      configTime(0, 0, "pool.ntp.org", "time.google.com");   // UTC
    }
    return;
  }
  if (wasConnected) {
    wasConnected = false;
    Serial.println(F("[WIFI] lost connection"));
  }
  if (lastWifiTryMs == 0 || millis() - lastWifiTryMs > WIFI_RETRY_MS) {
    lastWifiTryMs = millis();
    Serial.println(F("[WIFI] connecting..."));
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL);
  }
}

void maintainMqtt() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }
  if (lastMqttTryMs != 0 && millis() - lastMqttTryMs < MQTT_RETRY_MS) return;
  lastMqttTryMs = millis();

  char will[64];
  snprintf(will, sizeof(will), "{\"device_id\":\"%s\",\"state\":\"offline\"}", DEVICE_ID);
  Serial.printf("[MQTT] connecting to %s:%d as %s...\n", MQTT_HOST, MQTT_PORT, clientId);
  if (mqtt.connect(clientId, topicStatus, 1, true, will)) {
    Serial.println(F("[MQTT] connected"));
    mqtt.subscribe(topicCmd, 1);
    publishStatus();
  } else {
    Serial.printf("[MQTT] failed, state=%d (retry in %d s)\n", mqtt.state(), MQTT_RETRY_MS / 1000);
  }
}

// ------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println(F("\n=== JagSi watch firmware " FW_VERSION " ==="));

  snprintf(bootId, sizeof(bootId), "%08lx", (unsigned long)esp_random());
  snprintf(clientId, sizeof(clientId), "%s-%s", DEVICE_ID, bootId);   // unique per run
  snprintf(topicTelemetry, sizeof(topicTelemetry), TOPIC_BASE "%s/telemetry", DEVICE_ID);
  snprintf(topicEvent, sizeof(topicEvent), TOPIC_BASE "%s/event", DEVICE_ID);
  snprintf(topicStatus, sizeof(topicStatus), TOPIC_BASE "%s/status", DEVICE_ID);
  snprintf(topicCmd, sizeof(topicCmd), TOPIC_BASE "%s/cmd", DEVICE_ID);

  setupSensors();
  readSimulatedVitals();
  readImu();
  v.peakG = 0;

  WiFi.mode(WIFI_STA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(1024);     // default 256 bytes is too small for our JSON
  mqtt.setKeepAlive(15);        // broker sends the "offline" will after ~22 s of silence
}

void loop() {
  unsigned long now = millis();

  maintainWifi();
  maintainMqtt();

  if (now - lastSampleMs >= SENSOR_SAMPLE_MS) {
    lastSampleMs = now;
    readSimulatedVitals();
    readImu();
    checkFall();
  }
  if (now - lastTempMs >= TEMP_READ_MS) {
    lastTempMs = now;
    readTemperature();
  }
  checkSosButton();
  serviceAlerts();

  if (mqtt.connected() && now - lastTelemetryMs >= telemetryIntervalMs) {
    lastTelemetryMs = now;
    publishTelemetry();
  }
}
