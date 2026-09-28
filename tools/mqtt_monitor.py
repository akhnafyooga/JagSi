"""JagSi MQTT monitor (the "cloud side" for Sprint 1).

Subscribes to all JagSi topics, checks every message against the contract,
prints it, and saves telemetry/events to CSV files. With --ack it also answers
every alert with an "ack_alert" command (like the backend will do later).

Examples:
    python mqtt_monitor.py                         # watch everything
    python mqtt_monitor.py --ack --csv-dir logs    # watch, ack alerts, save CSV
    python mqtt_monitor.py --cmd '{"cmd":"ping"}'  # send one command to the device
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from jagsi_schema import TOPIC_BASE, VALIDATORS, split_topic, topic

TELEMETRY_COLUMNS = ["received_at", "device_id", "seq", "ts", "heart_rate", "spo2",
                     "body_temperature", "accel_x", "accel_y", "accel_z",
                     "gyro_x", "gyro_y", "gyro_z", "accel_peak_g", "battery_level"]
EVENT_COLUMNS = ["received_at", "device_id", "event_id", "ts", "alert_type", "status",
                 "attempt", "accel_peak_g", "heart_rate", "spo2", "body_temperature"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CsvLog:
    def __init__(self, path, columns):
        new = not os.path.exists(path)
        self.f = open(path, "a", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=columns)
        if new:
            self.w.writeheader()

    def write(self, row):
        self.w.writerow(row)
        self.f.flush()


class Monitor:
    def __init__(self, args):
        self.args = args
        self.stats = {"telemetry": 0, "event": 0, "status": 0, "invalid": 0}
        self.acked = set()
        self.tel_log = self.evt_log = None
        if args.csv_dir:
            os.makedirs(args.csv_dir, exist_ok=True)
            self.tel_log = CsvLog(os.path.join(args.csv_dir, "telemetry.csv"), TELEMETRY_COLUMNS)
            self.evt_log = CsvLog(os.path.join(args.csv_dir, "events.csv"), EVENT_COLUMNS)

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"jagsi-monitor-{os.getpid()}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # --- MQTT callbacks ---------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[monitor] connect failed: {reason_code}")
            return
        sub = f"{TOPIC_BASE}/{self.args.device}/#"
        client.subscribe(sub, qos=1)
        print(f"[monitor] connected to {self.args.host}:{self.args.port}, subscribed to {sub}")
        if self.args.cmd:
            self.send_cmd(self.args.device if self.args.device != "+" else "jagsi-watch-01",
                          json.loads(self.args.cmd))

    def on_message(self, client, userdata, msg):
        device, kind = split_topic(msg.topic)
        if kind == "cmd":
            print(f"[{now_iso()}] CMD    {device}: {msg.payload.decode(errors='replace')}")
            return
        if kind not in VALIDATORS:
            return
        try:
            data = json.loads(msg.payload)
        except ValueError:
            self.stats["invalid"] += 1
            print(f"[{now_iso()}] INVALID JSON on {msg.topic}: {msg.payload[:80]!r}")
            return

        problems = VALIDATORS[kind](data)
        if problems:
            self.stats["invalid"] += 1
            print(f"[{now_iso()}] INVALID {kind} from {device}: {'; '.join(problems)}")
            return
        self.stats[kind] += 1
        getattr(self, f"handle_{kind}")(device, data, msg.retain)

    # --- handlers ----------------------------------------------------------
    def handle_telemetry(self, device, d, retained):
        t = d["body_temperature"]
        print(f"[{now_iso()}] TELEM  {device} #{d['seq']:<5} HR {d['heart_rate']} bpm | "
              f"SpO2 {d['spo2']} % | Temp {t if t is not None else '-'} C | "
              f"peak {d['accel_peak_g']} g | batt {d['battery_level']} %")
        if self.tel_log:
            a, g = d["accel"], d["gyro"]
            self.tel_log.write({
                "received_at": now_iso(), "device_id": d["device_id"], "seq": d["seq"], "ts": d["ts"],
                "heart_rate": d["heart_rate"], "spo2": d["spo2"], "body_temperature": t,
                "accel_x": a["x"], "accel_y": a["y"], "accel_z": a["z"],
                "gyro_x": g["x"], "gyro_y": g["y"], "gyro_z": g["z"],
                "accel_peak_g": d["accel_peak_g"], "battery_level": d["battery_level"]})

    def handle_event(self, device, d, retained):
        dup = " (re-send)" if d["event_id"] in self.acked else ""
        print(f"[{now_iso()}] !!! ALERT {d['alert_type'].upper()} from {device} "
              f"id={d['event_id']} attempt={d['attempt']}{dup} vitals={d['vitals']}")
        if self.evt_log:
            v = d["vitals"]
            self.evt_log.write({
                "received_at": now_iso(), "device_id": d["device_id"], "event_id": d["event_id"],
                "ts": d["ts"], "alert_type": d["alert_type"], "status": d["status"],
                "attempt": d["attempt"], "accel_peak_g": d["accel_peak_g"],
                "heart_rate": v.get("heart_rate"), "spo2": v.get("spo2"),
                "body_temperature": v.get("body_temperature")})
        if self.args.ack:
            self.send_cmd(device, {"cmd": "ack_alert", "event_id": d["event_id"]})
            self.acked.add(d["event_id"])

    def handle_status(self, device, d, retained):
        tag = " (retained)" if retained else ""
        print(f"[{now_iso()}] STATUS {device}: {d['state']}{tag} {json.dumps(d)}")

    # --- commands ----------------------------------------------------------
    def send_cmd(self, device, cmd: dict):
        t = topic(device, "cmd")
        self.client.publish(t, json.dumps(cmd), qos=1)
        print(f"[{now_iso()}] -> {t}: {json.dumps(cmd)}")

    def run(self):
        self.client.connect(self.args.host, self.args.port, keepalive=30)
        try:
            if self.args.seconds:
                self.client.loop_start()
                time.sleep(self.args.seconds)
                self.client.loop_stop()
            else:
                self.client.loop_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.client.disconnect()
            print(f"[monitor] stopped. counts: {self.stats}")
        return self.stats


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="JagSi MQTT monitor")
    ap.add_argument("--host", default="broker.hivemq.com")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--device", default="+", help="device_id to watch ('+' = all)")
    ap.add_argument("--ack", action="store_true", help="auto-acknowledge alerts")
    ap.add_argument("--csv-dir", default=None, help="folder to save telemetry.csv and events.csv")
    ap.add_argument("--cmd", default=None, help='send one JSON command, e.g. \'{"cmd":"ping"}\'')
    ap.add_argument("--seconds", type=float, default=0, help="stop after N seconds (0 = run forever)")
    return ap.parse_args(argv)


if __name__ == "__main__":
    Monitor(parse_args()).run()
