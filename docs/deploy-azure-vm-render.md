# Deploy JagSi with Azure VM, Render and Supabase

Baseline commit is `67c177a` on `development`. This is a fictional-data presentation deployment. The frontend runs on an Ubuntu VM managed by the team. FastAPI generates simulated readings on Render. Supabase handles Google sign-in. Wokwi, MQTT configuration and the cloud mirror are unnecessary for this smoke test.

> **Deployed variant (28 November 2026):** the Render deployment failed, so FastAPI runs on the same Azure VM behind Nginx. See [`deploy-azure-vm.md`](deploy-azure-vm.md) for that runbook and [`evidence/azure-vm-deploy-2026-11-28.md`](evidence/azure-vm-deploy-2026-11-28.md) for the record. The steps below still apply when Render is used.

## 1. Choose the frontend hostname

Choose an HTTPS hostname you control, such as `jagsi.example.com`. Reserve it now so Render and Supabase can use it. If using a private rehearsal, restrict access separately at the hosting layer. Use fictional records throughout because the current FastAPI telemetry endpoints lack per-account authorization.

## 2. Deploy FastAPI on Render

Create a Python Web Service from the JagSi repository. Select `development` and set Root Directory to `backend`.

| Setting | Value |
| --- | --- |
| Build Command | `pip install -r requirements.txt -r requirements-demo.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port "$PORT"` |
| Health Check Path | `/api/health` |

Set these environment variables. Replace the example frontend hostname with yours.

~~~dotenv
PYTHON_VERSION=3.12.8
JAGSI_LOCAL_VITALS=stable
JAGSI_LOCAL_VITALS_SEED=42
JAGSI_DEVICE_ID=jagsi-watch-01
JAGSI_DB_PATH=/tmp/jagsi-demo.db
JAGSI_CORS_ORIGINS=https://jagsi.example.com
~~~

`PYTHON_VERSION` matches CI. The backend pins `numpy==2.1.3`, which does not install on Python 3.14. Use one API worker so only one simulated producer runs. SQLite in /tmp is disposable. Record the Render HTTPS URL after deployment. [Render FastAPI guide](https://render.com/docs/deploy-fastapi) · [Render free service limits](https://render.com/docs/free)

## 3. Configure Supabase and Google

In Google Auth Platform, use a Web application OAuth client. Set the authorized JavaScript origin to your frontend HTTPS origin and the authorized redirect URI to the callback shown on the Supabase Google provider page. Add presentation accounts as test users if your Google OAuth app is in Testing. In Supabase, enable the Google provider and save its Client ID and Client Secret. In Authentication → URL Configuration, set the Site URL to the frontend origin and add the exact URL `https://jagsi.example.com/setup` to Redirect URLs. Copy the Supabase project URL and publishable key for step 4. [Google sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-google) · [Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)

## 4. Deploy the frontend on the Azure VM

1. Create an Ubuntu VM with SSH key authentication and a public IP. Restrict inbound TCP 22 to your IP. Allow inbound TCP 80 and 443 for the reverse proxy. Point your hostname's DNS A record to the VM public IP.
2. Connect as `azureuser`. Install Git, Node.js 22 with npm, and Nginx. Confirm `node --version` and `npm --version`. Use a read-only deploy key if repository access requires authentication.
3. Clone the project and prepare the production environment.

~~~bash
git clone --branch development https://github.com/akhnafyooga/JagSi.git
cd JagSi/frontend
git rev-parse HEAD
nano .env.local
~~~

~~~dotenv
NEXT_PUBLIC_JAGSI_API=https://YOUR-RENDER-SERVICE.onrender.com
NEXT_PUBLIC_JAGSI_DEVICE_ID=jagsi-watch-01
NEXT_PUBLIC_JAGSI_PROGRESS_SOURCE=local
NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_YOUR_KEY
~~~

4. Build with `npm ci` and `npm run build`. Use `command -v npm` to find the executable. Create `/etc/systemd/system/jagsi-frontend.service` and adjust the paths and user as needed.

~~~ini
[Unit]
Description=JagSi Next.js frontend
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/JagSi/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port 3000
Restart=on-failure

[Install]
WantedBy=multi-user.target
~~~

5. Run `sudo systemctl daemon-reload` and `sudo systemctl enable --now jagsi-frontend`. Configure the Nginx virtual host with your domain as `server_name` and `proxy_pass http://127.0.0.1:3000;` inside `location /`. Forward Host and X-Forwarded-Proto. Run `sudo nginx -t` before reloading. Issue an HTTPS certificate for the domain using Certbot's Nginx workflow. Rebuild after changing any NEXT_PUBLIC values. [Azure VM quickstart](https://learn.microsoft.com/en-us/azure/azure-linux/quick-create-vm-portal) · [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting) · [Certbot](https://certbot.eff.org/)

## 5. Verify the rehearsal

1. Open the Render `/api/health` endpoint, then request `/api/devices/jagsi-watch-01/telemetry/latest` twice a few seconds apart. Check that the timestamp advances and the readings are simulated.
2. Open the Azure HTTPS site at `/beranda`. In DevTools, check that latest readings and history return success and the daily-brief POST passes CORS. Click **Perbarui ringkasan** and check the simulated evidence and source label. This deployment expects the labeled `rules` fallback unless the local LLM runtime, base weights and adapter are provisioned on Render.
3. Open `/setup` and test Google sign-in. Confirm the callback returns to the Azure hostname and the caregiver form loads. The current pairing and MCU scan flows require the local preview. Use `/beranda` directly for the hosted simulated telemetry demo.
4. Record both deployment URLs, the Git SHA, and the observed results. Test the first request after an idle period before presenting because Render free services can sleep.

Hosted MCU upload, remote presentation controls, physical watch provisioning and per-account telemetry authorization remain separate release gates. Supabase Postgres can be added for hosted history after the SQLite mirror has been configured and verified. The rehearsal above reads history from the API's local SQLite database.
