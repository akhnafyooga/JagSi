"""Fake JagSi watch over Azure IoT Hub (issue #8).

Same messages and behaviour as fake_device.py, but connected the way the
firmware connects in Azure mode:

  - MQTT over TLS on port 8883, X.509 client certificate, no password
  - username  <hub host>/<device id>/?api-version=2021-04-12
  - sends on  devices/<id>/messages/events/$.ct=application%2Fjson&$.ce=utf-8&type=<kind>
  - commands arrive as direct methods on $iothub/methods/POST/<name>/?$rid=<id>
    and are answered on $iothub/methods/res/<status>/?$rid=<id>

Uses the certificate that infra/azure/deploy.sh generated. Example, from the repo root:

    python tools/azure_fake_device.py \
        --host "$(grep HOSTNAME infra/azure/out/backend.env | cut -d= -f2)" \
        --cert infra/azure/out/jagsi-watch-01.cert.pem \
        --key  infra/azure/out/jagsi-watch-01.key.pem \
        --device-id jagsi-watch-01 --count 15 --sos-at 3 --fall-at 8

Every message counts against the hub's daily quota (F1: 8,000 a day).
"""

import argparse
import json
import ssl
import urllib.parse

import paho.mqtt.client as mqtt

import fake_device

EVENTS_FMT = "devices/{dev}/messages/events/$.ct=application%2Fjson&$.ce=utf-8&type={kind}"
METHODS_PREFIX = "$iothub/methods/POST/"
API_VERSION = "2021-04-12"


def azure_topic(device_id, kind):
    return EVENTS_FMT.format(dev=device_id, kind=kind)


# fake_device.run() publishes its goodbye through the module-level topic().
fake_device.topic = azure_topic


class AzureFakeDevice(fake_device.FakeDevice):
    def __init__(self, args):
        super().__init__(args)
        self.methods = []
        # IoT Hub requires the client id to be exactly the device id.
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.dev,
                                  protocol=mqtt.MQTTv311)
        self.client.username_pw_set(f"{args.host}/{self.dev}/?api-version={API_VERSION}")
        self.client.tls_set(certfile=args.cert, keyfile=args.key, cert_reqs=ssl.CERT_REQUIRED,
                            tls_version=ssl.PROTOCOL_TLS_CLIENT)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[azure] connect failed: {reason_code}")
            return
        client.subscribe(METHODS_PREFIX + "#", qos=0)   # IoT Hub delivers methods at QoS 0
        self.publish_status()
        print(f"[azure] {self.dev} connected to {self.a.host}:{self.a.port} (TLS, X.509)")
        self.connected.set()

    def on_message(self, client, userdata, msg):
        if not msg.topic.startswith(METHODS_PREFIX):
            print(f"[azure] ignored message on {msg.topic}")
            return
        name, _, query = msg.topic[len(METHODS_PREFIX):].partition("/")
        rid = urllib.parse.parse_qs(query.lstrip("?")).get("$rid", [""])[0]
        try:
            payload = json.loads(msg.payload or b"{}")
        except ValueError:
            payload = {}
        cmd = {"cmd": name, **(payload if isinstance(payload, dict) else {})}
        self.methods.append(cmd)
        msg.payload = json.dumps(cmd).encode()
        super().on_message(client, userdata, msg)        # same handling as the MQTT fake
        client.publish(f"$iothub/methods/res/200/?$rid={rid}", json.dumps({"ok": True}), qos=0)
        print(f"[azure] direct method {name} -> 200")

    def publish(self, kind, payload, retain=False):
        # IoT Hub has no retained messages; QoS 1 so the hub confirms each send.
        self.client.publish(azure_topic(self.dev, kind), json.dumps(payload), qos=1)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Fake JagSi watch over Azure IoT Hub", add_help=False)
    ap.add_argument("--cert", required=True, help="device certificate (PEM)")
    ap.add_argument("--key", required=True, help="device private key (PEM)")
    own, rest = ap.parse_known_args(argv)
    args = fake_device.parse_args(rest)
    if args.host == "broker.hivemq.com":
        raise SystemExit("--host must be the IoT hub host name, e.g. <hub>.azure-devices.net")
    if args.port == 1883:
        args.port = 8883
    args.cert, args.key = own.cert, own.key
    return args


if __name__ == "__main__":
    dev = AzureFakeDevice(parse_args())
    result = dev.run()
    print("[azure] RESULT", json.dumps({**result, "methods": dev.methods}))
