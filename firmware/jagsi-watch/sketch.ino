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
 *   - Publishes raw motion windows (30 samples @ 10 Hz = 3 s, 1 s hop) so the
 *     fall classifier from issue #9 can score them. Telemetry alone is not
 *     enough: it carries one sample per message, the model needs all 30.
 *   - Subscribes to a command topic (ping, set_interval, set_motion, ack_alert).
 *
 * Topic and payload rules: see docs/mqtt-contract.md
 * Sensor pins and what is real vs simulated: see docs/hardware-bom.md
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

#include "motion_window.h"

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

// Motion window for the fall classifier (backend/ml/schema.py)
// These four values MUST match SAMPLE_RATE_HZ, WINDOW_SECONDS, HOP_SECONDS and
// WINDOW_SIZE in backend/ml/schema.py. If the model is retrained at a different
// rate, change it here too or every feature the classifier computes is wrong.
#define MOTION_SAMPLE_RATE_HZ   10
#define MOTION_WINDOW_SIZE      30      // 10 Hz * 3.0 s
#define MOTION_HOP_MS           1000    // 1.0 s hop -> windows overlap by 2 s
#define MOTION_LATE_SAMPLE_MS   150     // a gap longer than this = a dropped sample

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
char topicMotion[64];
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

// Rolling buffer of the last MOTION_WINDOW_SIZE motion samples. One slot per
// 10 Hz sample; once it is full every hop publishes the newest 30 samples.
// Implementation and host-side unit tests live in motion_window.h.
MotionWindow<MOTION_WINDOW_SIZE> motionWindow;
uint32_t motionSeq = 0;
uint16_t motionDropped = 0;           // late samples since the last window
unsigned long lastMotionSampleMs = 0; // uptime of the newest sample
unsigned long lastMotionPublishMs = 0;
bool motionEnabled = true;            // "set_motion" can turn this off

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
// Gyroscope only needs 0.1 deg/s; one decimal keeps the motion window payload
// inside the MQTT buffer.
double round1(float x) { return (double)lroundf(x * 10.0f) / 10.0; }

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

// Stores the current IMU reading in the rolling window buffer. Called once per
// 10 Hz sample, straight after readImu(), so the buffer always holds the most
// recent MOTION_WINDOW_SIZE samples in chronological order.
void pushMotionSample() {
  if (!mpuOk) return;

  unsigned long now = millis();
  if (lastMotionSampleMs != 0) {
    unsigned long gap = now - lastMotionSampleMs;
    if (gap > MOTION_LATE_SAMPLE_MS) {
      // The loop was held up (reconnect, blocking sensor read). Count the
      // samples we never took, so the backend can reject a window whose
      // spacing is no longer a clean 10 Hz.
      motionDropped += (uint16_t)((gap - SENSOR_SAMPLE_MS) / SENSOR_SAMPLE_MS);
    }
  }
  lastMotionSampleMs = now;

  MotionSample m;
  m.ax = v.ax; m.ay = v.ay; m.az = v.az;
  m.gx = v.gx; m.gy = v.gy; m.gz = v.gz;
  motionWindow.push(m);
}

// Publishes the newest MOTION_WINDOW_SIZE samples, oldest first, as a compact
// array of [ax, ay, az, gx, gy, gz]. The backend feeds this straight into
// FallClassifier.predict_window(). See docs/mqtt-contract.md section 3.5.
void publishMotionWindow() {
  // Oldest first. Returns false until 30 samples have been collected.
  static MotionSample window[MOTION_WINDOW_SIZE];
  if (!motionWindow.snapshot(window)) return;

  char ts[25] = "";
  if (!isoTimeNow(ts, sizeof(ts))) ts[0] = '\0';

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["seq"] = ++motionSeq;
  putTime(doc, "ts", ts);
  // Uptime of the OLDEST sample in this window, so the backend can line the
  // window up against the telemetry stream.
  doc["t0_ms"] = lastMotionSampleMs - (unsigned long)(MOTION_WINDOW_SIZE - 1) * SENSOR_SAMPLE_MS;
  doc["sample_rate_hz"] = MOTION_SAMPLE_RATE_HZ;
  doc["window_size"] = MOTION_WINDOW_SIZE;
  doc["dropped"] = motionDropped;
  doc["sim"] = true;

  JsonArray s = doc["s"].to<JsonArray>();
  for (uint8_t i = 0; i < MOTION_WINDOW_SIZE; i++) {
    const MotionSample &m = window[i];
    JsonArray row = s.add<JsonArray>();
    row.add(round2(m.ax));
    row.add(round2(m.ay));
    row.add(round2(m.az));
    row.add(round1(m.gx));
    row.add(round1(m.gy));
    row.add(round1(m.gz));
  }

  // Static so a ~1.2 kB payload does not sit on the loop task stack.
  static char buf[1600];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  if (n == 0 || n >= sizeof(buf) - 1) {
    Serial.println(F("[MOTION] payload too big, not sent"));
    return;
  }
  if (mqtt.publish(topicMotion, (const uint8_t *)buf, n, false)) {
    Serial.printf("[MOTION] -> window %lu (%u bytes, %u dropped)\n",
                  (unsigned long)motionSeq, (unsigned)n, motionDropped);
    motionDropped = 0;
  } else {
    Serial.println(F("[MOTION] publish FAILED"));
  }
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
  doc["motion_enabled"] = motionEnabled;
  doc["sample_rate_hz"] = MOTION_SAMPLE_RATE_HZ;
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
  } else if (strcmp(cmd, "set_motion") == 0) {
    // Lets the backend stop the 10 Hz window stream when the classifier is not
    // running, since it is by far the heaviest traffic the device produces.
    motionEnabled = doc["enabled"] | true;
    Serial.printf("[CMD] motion windows %s\n", motionEnabled ? "ON" : "OFF");
    publishStatus();
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
  snprintf(topicMotion, sizeof(topicMotion), TOPIC_BASE "%s/motion", DEVICE_ID);

  setupSensors();
  readSimulatedVitals();
  readImu();
  v.peakG = 0;

  WiFi.mode(WIFI_STA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(2048);     // a 30-sample motion window is ~1.2 kB
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
    pushMotionSample();
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

  if (mqtt.connected() && motionEnabled && now - lastMotionPublishMs >= MOTION_HOP_MS) {
    lastMotionPublishMs = now;
    publishMotionWindow();
  }
}
