# Azure IoT Hub and Event Grid setup (issue #8)

Issue: [#8 Deploy Azure IoT Hub & Event Grid](https://github.com/akhnafyooga/JagSi/issues/8)

Until Week 6 the watch and the backend met on the public HiveMQ broker: no password,
no encryption, readable and writable by anyone. This moves the device to Azure IoT
Hub. Payloads do not change; only the transport does.

```
ESP32 --MQTT over TLS, X.509 certificate--> Azure IoT Hub
                                               |
                                               | Event Grid (DeviceTelemetry,
                                               |  DeviceConnected/Disconnected)
                                               v
                        POST /api/ingest/eventgrid?key=...  (backend, azure mode)
                                               |
                                bridge.dispatch() -> same handlers as Week 6
                                               |
backend --HTTPS direct method (ack_alert, ping, set_interval, set_motion)--> IoT Hub --> ESP32
```

## What changes, and why

| | Week 6 (public broker) | Week 7 (Azure IoT Hub) |
|---|---|---|
| Encryption | none, port 1883 | TLS 1.2, port 8883; the watch checks Azure's certificate |
| Device identity | anyone can publish as any device | X.509 certificate per device, registered by thumbprint |
| Device to cloud | `jagsi/abal/v1/<id>/<kind>` | `devices/<id>/messages/events/$.ct=application%2Fjson&$.ce=utf-8&type=<kind>` |
| Cloud to device | publish on `.../cmd` | IoT Hub direct method named after the command |
| Did the command arrive? | unknown | yes or no: the device answers the method |
| Online / offline | retained status + Last Will | `DeviceConnected` / `DeviceDisconnected` events, plus the Will |
| Backend connection | MQTT subscriber | none; Event Grid pushes to a webhook |

Two extra protections live in the backend, not in Azure:

- **Webhook key.** Event Grid must call `/api/ingest/eventgrid?key=<JAGSI_EVENTGRID_KEY>`.
  Without it, anyone who finds the URL could post fake telemetry or a fake fall.
- **Device id check.** The device id is taken from IoT Hub's
  `iothub-connection-device-id`, which comes from the authenticated connection. A
  payload whose own `device_id` differs is refused, so one watch cannot report data
  or alerts for another elder.

The backend authenticates to IoT Hub with the `service` policy (ServiceConnect
only). It can invoke direct methods but cannot create or delete devices.

## Cost: read this before choosing the tier

| Tier | Messages per day | Billed in blocks of | Enough for |
|------|------------------|---------------------|------------|
| F1 (free) | 8,000 | **0.5 KB** | about **40 minutes** of the watch running with the motion stream on, about 4.4 hours with it off |
| S1 | 400,000 | 4 KB | all day, every day |

IoT Hub counts a message once for every started block. On F1 a motion window
(about 1.2 kB) is 3 messages, while telemetry, status and events (under 0.5 kB) are
1 each. The watch sends one motion window every second and telemetry every 2 s,
so it uses about 3.5 messages a second, about 12,600 an hour. This was measured on
28 November 2026: the hub's counter matched this calculation exactly (see
[`evidence/azure-iot-hub-2026-11-28.md`](evidence/azure-iot-hub-2026-11-28.md)).
Check it any time with `az iot hub show-quota-metrics -n <hub>`. The counter lags
by a few minutes.

The script defaults to F1. For a demo, run the watch only while presenting, or turn
the motion stream off when it is not needed:

```bash
curl -X POST localhost:8000/api/devices/jagsi-watch-01/command \
     -H 'Content-Type: application/json' -d '{"cmd":"set_motion","enabled":false}'
```

Switch to S1 with `JAGSI_SKU=S1 infra/azure/deploy.sh hub` on a new hub, or in the
portal. Event Grid's first 100,000 operations each month are free.

## Steps

You need the Azure CLI (`az login` done), `openssl` and `python3`.

**1. Create the hub, the device and the secrets**

```bash
infra/azure/deploy.sh hub
```

This creates resource group `jagsi-rg` in `southeastasia`, an IoT hub with a random
suffix, a self-signed EC P-256 certificate for `jagsi-watch-01`, and registers the
device by the certificate's thumbprint.

**Azure for Students:** the subscription has an "Allowed resource deployment
regions" policy, and `southeastasia` is not on it. Pick a region that is both
allowed and offers IoT Hub. On 28 November 2026 that was `japaneast` or
`australiaeast`:

```bash
az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv
JAGSI_LOCATION=japaneast infra/azure/deploy.sh hub
```

New hubs are created with shared access policies switched off
(`disableLocalAuth=true`). The script switches them back on, because the backend
calls direct methods with the `service` policy key. The watch still logs in with
its X.509 certificate only.

It writes:

| File | Contains | Commit? |
|------|----------|---------|
| `infra/azure/out/backend.env` | hub host name, service key, webhook key | **never** |
| `infra/azure/out/jagsi-watch-01.key.pem` | the device private key | **never** |
| `firmware/jagsi-watch/azure_config.h` | host name, certificate and private key for the firmware | **never** |

All three are in `.gitignore`. Re-running the command is safe: it reuses the hub,
the key and the webhook key.

**2. Start the backend in azure mode**

```bash
cd backend
set -a; source ../infra/azure/out/backend.env; set +a
uvicorn app.main:app --port 8000
curl -s localhost:8000/api/health | python3 -m json.tool    # "ingest": "azure"
```

**3. Give the backend a public HTTPS address**

Event Grid can only deliver to a public HTTPS URL. For development, a tunnel is
enough:

```bash
devtunnel host -p 8000 --allow-anonymous      # or: ngrok http 8000
```

**4. Route device messages to the backend**

```bash
infra/azure/deploy.sh eventgrid https://<your-tunnel-url>
```

The script first checks the backend answers at that URL, because Event Grid
validates the endpoint while the subscription is being created.

**5. Run the watch**

Add `azure_config.h` next to `sketch.ino`. In Wokwi, click the file menu, add a file
with exactly that name and paste the generated contents. **Keep that Wokwi project
private**: the file holds the device's private key. When the file is present the
firmware prints `Transport: Azure IoT Hub (TLS + X.509)` on boot.

**6. Check**

```bash
infra/azure/deploy.sh status          # device connectionState should be Connected
curl -s localhost:8000/api/health     # bridge.last_message_at keeps moving
```

Press the SOS button in Wokwi: the alert appears on the dashboard and the serial
monitor prints `[CMD] direct method ack_alert -> 200`.

## Going back to the public broker

Delete `firmware/jagsi-watch/azure_config.h` and start the backend without
`backend.env`. Both default to the Week 6 behaviour.

## Removing everything

```bash
infra/azure/deploy.sh teardown
```

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `[MQTT] waiting for NTP time before TLS...` forever | no internet from Wokwi, or NTP blocked; TLS cannot check certificate dates without the time |
| `[MQTT] failed, state=-2` | TLS handshake failed: wrong host name in `azure_config.h`, or the root certificate changed (see `azure_roots.h`) |
| `[MQTT] failed, state=5` | IoT Hub refused the device: certificate thumbprint does not match; re-run `deploy.sh hub` and paste the new `azure_config.h` |
| `deploy.sh eventgrid` says HTTP 404 | backend not in azure mode: `backend.env` was not loaded |
| HTTP 401 in the backend log | the `key` in the Event Grid URL does not match `JAGSI_EVENTGRID_KEY` |
| Data stops after about 40 minutes | F1 daily message quota used up; see the cost table |
