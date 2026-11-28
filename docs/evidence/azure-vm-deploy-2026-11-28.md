# Azure VM deployment record, 28 November 2026

Presentation deployment with fictional data, set up with
[`docs/deploy-azure-vm.md`](../deploy-azure-vm.md). It follows
[`docs/deploy-azure-vm-render.md`](../deploy-azure-vm-render.md), except that
FastAPI runs on the VM because the Render deployment failed.

| Item | Value |
|---|---|
| URL | https://jagsi-demo-90ab.japaneast.cloudapp.azure.com |
| Commit | `db61c26` on `development` (Merge pull request #33) |
| VM | `jagsi-web`, `Standard_B2pts_v2` (ARM64, 1 GB RAM + 2 GB swap), Ubuntu 24.04.5, `japaneast` zone 3, resource group `jagsi-web-rg`, Azure for Students |
| Runtime | Python 3.12.3 (numpy 2.1.3, scikit-learn 1.7.2), Node v22.23.5, npm 10.9.9, Nginx 1.24.0 |
| Services | `jagsi-backend` (uvicorn, 1 worker, `127.0.0.1:8000`), `jagsi-frontend` (`next start`, `127.0.0.1:3000`); both enabled at boot |
| Backend mode | `JAGSI_LOCAL_VITALS=stable`, seed 42, SQLite at `/var/lib/jagsi/jagsi-demo.db` |
| TLS | Let's Encrypt (issuer YE2), expires 2027-02-26, `certbot renew --dry-run` succeeded |
| Supabase | Google provider enabled; frontend built with the project URL and publishable key |

## Results

| # | Check | Result |
|---|---|---|
| 1 | `GET /api/health` over HTTPS | PASS: 200 |
| 2 | Latest telemetry, requested twice | PASS: 13:25:36Z → 13:25:40Z, `simulated: true` |
| 3 | `alerts`, `telemetry/history?limit=60`, `summary`, `local-progress`, `devices` | PASS: all 200; local trend model answers `stable` (0.967, `synthetic-trends-v1`) |
| 4 | Live stream `/api/stream` through Nginx | PASS: `hello`, then a `telemetry` event every ~2 s, no buffering delay |
| 5 | Alert WebSocket `wss://…/ws/alerts` | PASS: `hello`, `ping` → `pong` |
| 6 | Daily brief `POST /api/devices/jagsi-watch-01/daily-brief` | PASS: 200, `source: rules`, `model: JagSi rules`, CORS preflight allows the site origin |
| 7 | CORS for a foreign origin | PASS: no `Access-Control-Allow-Origin` returned |
| 8 | Pages `/`, `/beranda`, `/riwayat`, `/darurat`, `/profil`, `/mcu`, `/setup` | PASS: 200. `/monitoring` 307 → `/beranda#tanda-vital` (by design) |
| 9 | HTTP → HTTPS | PASS: 301 |
| 10 | `/demo-console` not reachable | PASS: 404 on the site (Nginx routes only `/api/` and `/ws/` to FastAPI) and 404 on the backend itself (`JAGSI_DEMO_CONSOLE` unset) |
| 11 | Build-time variables | PASS: API origin and Supabase URL embedded; no `localhost:8000` in the bundle |
| 12 | Supabase Google provider | PASS: `/auth/v1/settings` reports `google: true`; `/auth/v1/authorize?provider=google` redirects to `accounts.google.com` with the Supabase callback |
| 13 | `/setup` shows **Lanjutkan dengan Google** (not "Google belum dikonfigurasi") | PASS |
| 14 | Google sign-in with a test account returns to `/setup` and shows **Akun pengasuh** | **Not yet confirmed**: needs a browser test by a presenter |

Resource use on the VM: `npm ci` 17 s and 290 MB peak, `next build` 37 s and
380 MB peak. With both services running, about 350 MB RAM in use and 90 MB of
swap.

## Issues found during the deployment

- **`npm ci` failed on `development`.** `fbab309` committed a lockfile without
  `@emnapi/core` and `@emnapi/runtime`. Fixed in #33.
- **Render could not be used.** The deployment failed; the Render log was not
  reviewed. A likely cause: the backend pins `numpy==2.1.3`, which does not
  install on Python 3.14 (reproduced on a Mac). CI uses 3.12, so set
  `PYTHON_VERSION=3.12.8` on Render.
- **The guide omits `NEXT_PUBLIC_JAGSI_PROGRESS_SOURCE=local`.** The cloud
  `/progress` route answers 503 without the Supabase mirror. No page calls it at
  `db61c26`, but the variable is set here.
- **B1s was unavailable.** `Standard_B1s` had no capacity in `japaneast`
  (`SkuNotAvailable`), so B2pts_v2 (ARM) is used.
- **The temperature card is labelled `simulated: false`.**
  `telemetry/latest` marks heart rate, SpO₂ and battery as simulated but not body
  temperature, although all values come from the simulator. Not fixed here.

## Not covered

- The Google sign-in round trip (check 14).
- Wokwi, MQTT, the Supabase cloud mirror and the IoT Hub path. The
  [IoT Hub record](azure-iot-hub-2026-11-28.md) covers that path separately.
- Load or multi-user behaviour. Telemetry endpoints have no per-account
  authorization, so use fictional data only.
