# Azure IoT Hub and Event Grid: live check, 28 November 2026 (issue #8)

Deliverable: configured cloud ingestion endpoint, with MQTT authentication by
certificate. Setup steps are in [`docs/azure-setup.md`](../azure-setup.md).

## What was deployed

| Item | Value |
|------|-------|
| Subscription | Azure for Students |
| Resource group | `jagsi-rg`, region `japaneast` (the student policy does not allow `southeastasia`) |
| IoT hub | `jagsi-abal-c47128`, tier **F1** (free, 8,000 messages a day), state Active |
| Device | `jagsi-watch-01`, X.509 self-signed EC P-256, registered by SHA-1 thumbprint |
| Event Grid | subscription `jagsi-backend` on the hub: `DeviceTelemetry`, `DeviceConnected`, `DeviceDisconnected`, webhook `/api/ingest/eventgrid?key=…`, state Succeeded |
| Backend | `JAGSI_INGEST=azure`, local, public HTTPS through a temporary Cloudflare quick tunnel |

Secrets (device private key, `service` policy key, webhook key) stay in
`infra/azure/out/` and `firmware/jagsi-watch/azure_config.h`, which are in `.gitignore`.

## Path checked

```
tools/azure_fake_device.py --TLS 8883, X.509--> IoT Hub --Event Grid--> backend /api/ingest/eventgrid
backend --HTTPS direct method (service policy)--> IoT Hub --> device answers 200
```

The test device is `tools/fake_device.py` with the firmware's Azure transport:
client id = device id, username `<host>/<id>/?api-version=2021-04-12`, events on
`devices/<id>/messages/events/$.ct=application%2Fjson&$.ce=utf-8&type=<kind>`,
commands on `$iothub/methods/POST/#`.

## Results

| # | Check | Result |
|---|-------|--------|
| 1 | Device connects with its certificate only (no password, no SAS) | PASS: CONNACK Success |
| 2 | Telemetry reaches the backend through Event Grid | PASS: 31 sent, 31 counted by the backend |
| 3 | Motion windows are scored by the fall classifier | PASS: 53 scored, 0 rejected |
| 4 | SOS event → alert → `ack_alert` direct method → device stops re-sending | PASS: acknowledged on attempt 1 (twice, in two runs) |
| 5 | Fall event → alert → `ack_alert` | PASS: acknowledged on attempt 1. The classifier's own alert was suppressed as a duplicate of the device alert, as designed |
| 6 | `ping`, `set_interval` (3000 ms), `set_motion` false/true as direct methods | PASS: device answered 200 to each, status updated |
| 7 | Command to an offline device | PASS: API answers "device did not answer the direct method" (IoT Hub 404103), no false success |
| 8 | Event Grid deliveries | PASS: 99 of 99 webhook calls answered 200, 0 messages rejected |
| 9 | Device state follows connect / disconnect | PASS: `offline` after the device disconnected |
| 10 | Hub TLS chain trusted by the firmware's roots only (`azure_roots.h`) | PASS: `*.azure-devices.net` → MSFT RS256 CA-1 → DigiCert Global Root G2, `Verify return code: 0 (ok)` |

## Quota

`az iot hub show-quota-metrics` after the three runs: **210 of 8,000** messages
used. A reading taken a few minutes earlier showed 107, because the counter lags.

F1 counts in **0.5 KB blocks**. Measured payload sizes:

| Message | Size | F1 messages |
|---------|------|-------------|
| motion window (30 samples) | 1,233 B | 3 |
| telemetry | 281 B | 1 |
| event | 275 B | 1 |
| status | 190 B | 1 |

The runs sent 53 motion windows × 3 + 31 telemetry + 3 events + 10 status + 7
direct methods = **210**, exactly the hub's counter.

At the firmware's default rates (motion every 1 s, telemetry every 2 s) that is
about 3.5 messages a second, about 12,600 an hour. **F1 lasts about 38 minutes of
continuous running a day**, or about 4.4 hours with the motion stream off. The
earlier figure of about 1.5 hours in `docs/azure-setup.md` and `deploy.sh` left
out the 0.5 KB metering. Both are now corrected. Turn the motion stream off
between demos (`set_motion` false), or use S1 (4 KB blocks) for longer runs.

## Issues found and fixed

- The F1 quota estimate was off by more than half (see Quota above). Corrected in
  `docs/azure-setup.md` and `deploy.sh`.
- New hubs come with shared access policies disabled (`disableLocalAuth=true`).
  `deploy.sh hub` failed to register the device (`401002 … disabling Sas
  authentication`). The script now turns them back on, because the backend's
  direct methods need the `service` key. The device still uses X.509 only.
- The Azure for Students region policy rejects the default `southeastasia`.
  `docs/azure-setup.md` now explains how to choose an allowed region.

## Observed once, not reproduced

The first direct method after the hub was created failed in the backend with
`CERTIFICATE_VERIFY_FAILED` (TLS to `<hub>.azure-devices.net:443`). Every later
call worked. So did 40 separate TLS handshakes afterwards, 20 with the certifi CA
bundle and 20 with the system store. All presented the chain above. Probably a
hub that had only just been provisioned. Watch the backend log for it during the
demo.

## Not covered by this check

- The real firmware on Wokwi or an ESP32 with `azure_config.h`. The test device
  speaks the same protocol, but the sketch itself was not run against the hub
  here.
- The Event Grid webhook points at a temporary tunnel URL. When the tunnel
  restarts, run `infra/azure/deploy.sh eventgrid https://<new-url>` again.
