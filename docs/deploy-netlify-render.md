# Deploy JagSi with Netlify and Render

This runbook targets the school demo with simulated readings. Netlify hosts the Next.js app. Render runs FastAPI, the MQTT listener and the trained models. The Supabase mirror supplies cloud history and the vital-trend model's 60-reading window.

## 1. Create the Render backend

Create a Python Web Service from the JagSi repository. Choose a branch containing the intended backend and model artifacts. Set its root directory to `backend`.

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt -r requirements-demo.txt` |
| Start command for the API | `uvicorn app.main:app --host 0.0.0.0 --port "$PORT"` |
| Health check | `/api/health` |
| CORS | Set `JAGSI_CORS_ORIGINS` to the exact Netlify origin, such as `https://jagsi.netlify.app` |

Set the broker address, port, topic prefix, device ID and credentials in Render. Match the device configuration and use a dedicated demo topic. The current bridge configuration uses ordinary MQTT. Verify TLS support in both firmware and backend before pointing them at a TLS-only broker. [MQTT contract](mqtt-contract.md)

For the hosted trend path, apply the Supabase schema and configure `JAGSI_CLOUD_DSN`, `JAGSI_SOURCE_ID` and `JAGSI_TREND_MODEL` using the cloud guide. Set `JAGSI_DB_PATH` to a writable SQLite path. Deploy the mirror command `python -m demo.cloud` alongside Uvicorn under a process supervisor in the **same Render service** so both processes read the same SQLite file. The API start command above starts only Uvicorn. An independently deployed worker does not share the API's local disk. With a persistent disk, place SQLite under its mount path and preserve the source UUID across restarts. [Cloud setup](cloud-inference.md) · [Render disks](https://render.com/docs/disks)

## 2. Create the Netlify frontend

Import the same repository, set the base directory to `frontend`, and use Next.js framework detection with `npm run build`. Before building, set `NEXT_PUBLIC_JAGSI_API` to the Render HTTPS origin and `NEXT_PUBLIC_JAGSI_DEVICE_ID` to the matching device. Redeploy after changing either value. Keep the database connection string and MQTT credentials in Render's backend environment. The browser connects directly to Render over HTTPS for data and WSS for alerts. [Next.js on Netlify](https://docs.netlify.com/build/frameworks/framework-setup-guides/nextjs/overview/)

## 3. Verify the deployed demo

1. Check Render's `/api/health` and confirm the broker is connected and the fall classifier is loaded.
2. Open the Netlify app and start Wokwi. Vary a reading and verify that Monitoring shows the selected device. Wait for 60 valid mirrored readings and confirm `/progress` and the AI card report the same window.
3. Trigger simulated SOS and fall separately. Acknowledge an event and reload to verify its status. Stop the feed and confirm the summary changes to stale. Reconnect and confirm recovery.
4. Restart the backend. Check whether alert state and history survive, and record the actual result with the deployment URLs and commit SHA.

Use simulated data only. Render free web services can sleep and have an ephemeral local filesystem. A paid backend with a persistent disk is needed for the current SQLite staging design if the service must keep receiving readings while the dashboard is closed and retain local records across restarts. [Render free limits](https://render.com/docs/free)
