# Deploy JagSi on one Azure VM

This runbook puts the JagSi frontend and backend on one Ubuntu VM in Azure. It is
the setup used for the 28 November 2026 presentation deployment
([record](evidence/azure-vm-deploy-2026-11-28.md)). It follows
[`deploy-azure-vm-render.md`](deploy-azure-vm-render.md), except that FastAPI runs
on the VM instead of Render.

It uses fictional data only. The backend generates simulated readings
(`JAGSI_LOCAL_VITALS`), and the telemetry endpoints have no per-account
authorization. Do not send real health data to it.

```
browser ──HTTPS──> Nginx (443, Let's Encrypt)
                     ├── /api/, /ws/ ──> FastAPI   127.0.0.1:8000  (jagsi-backend.service)
                     └── everything else ──> Next.js 127.0.0.1:3000  (jagsi-frontend.service)
Google sign-in on /setup: browser ──> Supabase Auth ──> Google ──> back to /setup
```

## Why one VM instead of Render

- **One origin.** The browser calls `https://<host>/api/...` on the page's own
  origin, so CORS and mixed-content problems do not arise. The alert WebSocket
  becomes `wss://<host>/ws/alerts` automatically.
- **No sleep.** Render's free web services stop when idle, and the simulated
  feed stops with them. The VM keeps running.
- **SQLite survives restarts.** It lives in `/var/lib/jagsi` instead of `/tmp` on
  an ephemeral disk.
- **Python 3.12.** Ubuntu 24.04 ships Python 3.12, the version CI uses. The
  backend pins `numpy==2.1.3`, which does not install on Python 3.14. If you
  deploy to Render, set `PYTHON_VERSION=3.12.8`.

## Cost (Azure for Students)

| Resource | Size | Notes |
|---|---|---|
| VM | `Standard_B2pts_v2`: ARM64, 2 vCPU, 1 GB RAM | Listed with B1s in Azure's 750 free hours a month. About $6 a month otherwise |
| OS disk | Premium SSD 64 GB (P6) | Free-services allowance for 12 months |
| Public IP | Standard, static | A few dollars a month |

`Standard_B1s` had no capacity in `japaneast` on 28 November 2026
(`SkuNotAvailable`). B2pts_v2 was the only small size available, in zone 3. The
student subscription only allows `japaneast`, `indiasouthcentral`,
`indonesiacentral`, `malaysiawest` and `australiaeast`. Check with:

```bash
az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv
az vm list-skus -l japaneast --zone --resource-type virtualMachines \
  --query "[?starts_with(name,'Standard_B')].{size:name, zones:locationInfo[0].zones, restricted:length(restrictions)}" -o table
```

To stop paying for the VM while it is not needed, deallocate it. The static IP
and the host name stay the same:

```bash
az vm deallocate -g jagsi-web-rg -n jagsi-web    # stop
az vm start      -g jagsi-web-rg -n jagsi-web    # start again; services start on boot
```

## 1. Create the VM

From a machine with the Azure CLI (`az login` done). Use your own public IP for
SSH and your own DNS label. The label becomes
`<label>.japaneast.cloudapp.azure.com`.

```bash
RG=jagsi-web-rg; L=japaneast; MYIP=$(curl -s https://api.ipify.org)
ssh-keygen -t ed25519 -N "" -C jagsi-azure-vm -f ~/.ssh/jagsi_azure

az group create -n $RG -l $L
az network nsg create -g $RG -n jagsi-web-nsg
az network nsg rule create -g $RG --nsg-name jagsi-web-nsg -n ssh-my-ip --priority 100 \
  --access Allow --protocol Tcp --direction Inbound \
  --source-address-prefixes $MYIP/32 --destination-port-ranges 22
az network nsg rule create -g $RG --nsg-name jagsi-web-nsg -n http-https --priority 110 \
  --access Allow --protocol Tcp --direction Inbound \
  --source-address-prefixes Internet --destination-port-ranges 80 443
az network public-ip create -g $RG -n jagsi-web-ip --sku Standard \
  --allocation-method Static --dns-name jagsi-demo-90ab
az vm create -g $RG -n jagsi-web \
  --image Canonical:ubuntu-24_04-lts:server-arm64:latest \
  --size Standard_B2pts_v2 --zone 3 \
  --admin-username azureuser --ssh-key-values ~/.ssh/jagsi_azure.pub \
  --public-ip-address jagsi-web-ip --nsg jagsi-web-nsg \
  --storage-sku Premium_LRS --os-disk-size-gb 64
```

SSH is open only to the IPs in the `ssh-my-ip` rule. Some networks change your
public IP between nearby addresses. If `ssh` times out, check
`curl https://api.ipify.org` and add the new address:

```bash
az network nsg rule update -g jagsi-web-rg --nsg-name jagsi-web-nsg -n ssh-my-ip \
  --source-address-prefixes <old-ip>/32 <new-ip>/32
```

## 2. Prepare the server

`ssh -i ~/.ssh/jagsi_azure azureuser@<host>`, then:

```bash
# 2 GB swap: the VM has 1 GB RAM; next build peaks at about 380 MB, npm ci at about 290 MB
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab

sudo apt-get update
sudo apt-get install -y git nginx certbot python3-certbot-nginx python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh && sudo -E bash /tmp/nodesource_setup.sh
sudo apt-get install -y nodejs
node --version; command -v npm      # v22.x, /usr/bin/npm

git clone --branch development https://github.com/akhnafyooga/JagSi.git ~/JagSi
```

## 3. Backend (FastAPI, simulated readings)

```bash
cd ~/JagSi/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-demo.txt

sudo install -d -o azureuser -g azureuser -m 750 /var/lib/jagsi
sudo install -d -m 755 /etc/jagsi
sudo tee /etc/jagsi/backend.env >/dev/null <<'ENV'
JAGSI_LOCAL_VITALS=stable
JAGSI_LOCAL_VITALS_SEED=42
JAGSI_DEVICE_ID=jagsi-watch-01
JAGSI_DB_PATH=/var/lib/jagsi/jagsi-demo.db
JAGSI_CORS_ORIGINS=https://jagsi-demo-90ab.japaneast.cloudapp.azure.com
ENV
sudo chown root:azureuser /etc/jagsi/backend.env && sudo chmod 640 /etc/jagsi/backend.env
```

`/etc/systemd/system/jagsi-backend.service`:

```ini
[Unit]
Description=JagSi FastAPI backend (simulated vitals)
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/JagSi/backend
EnvironmentFile=/etc/jagsi/backend.env
ExecStart=/home/azureuser/JagSi/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Keep `--workers 1`: each worker would start its own simulated producer.

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now jagsi-backend
curl -s 127.0.0.1:8000/api/health
```

`/api/health` reports `"ingest": "mqtt"` even in simulated mode. The MQTT
bridge is not started when `JAGSI_LOCAL_VITALS` is set, so this can be ignored.

## 4. Frontend (Next.js)

`~/JagSi/frontend/.env.local`. It is git-ignored. Next.js embeds these values at
build time, so rebuild after any change.

```dotenv
NEXT_PUBLIC_JAGSI_API=https://jagsi-demo-90ab.japaneast.cloudapp.azure.com
NEXT_PUBLIC_JAGSI_DEVICE_ID=jagsi-watch-01
NEXT_PUBLIC_JAGSI_PROGRESS_SOURCE=local
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_<key>
```

- `NEXT_PUBLIC_JAGSI_API` is the site's own origin, because Nginx forwards
  `/api/` and `/ws/`.
- `NEXT_PUBLIC_JAGSI_PROGRESS_SOURCE=local`: this deployment has no Supabase
  mirror, so the cloud `/progress` route answers 503, while `/local-progress`
  works. No page calls `fetchProgress` at `db61c26`, but set it so a future page
  uses the right route.
- Only the **publishable** Supabase key belongs here. The `sb_secret_` /
  service-role key and the Google client secret never go in the frontend.

```bash
cd ~/JagSi/frontend
npm ci && npm run build
```

`/etc/systemd/system/jagsi-frontend.service`:

```ini
[Unit]
Description=JagSi Next.js frontend
After=network.target jagsi-backend.service

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/JagSi/frontend
Environment=NODE_ENV=production
Environment=NEXT_TELEMETRY_DISABLED=1
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port 3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now jagsi-frontend
```

## 5. Nginx and HTTPS

`/etc/nginx/sites-available/jagsi`, before Certbot:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name jagsi-demo-90ab.japaneast.cloudapp.azure.com;

    location /api/ {
        client_max_body_size 15m;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Only `/api/` and `/ws/` go to FastAPI. Its `/demo-console` routes stay
unreachable from outside. Next.js has no `/api` or `/ws` routes of its own at
`db61c26`. Check again if the frontend adds route handlers.

```bash
sudo ln -sf /etc/nginx/sites-available/jagsi /etc/nginx/sites-enabled/jagsi
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d jagsi-demo-90ab.japaneast.cloudapp.azure.com \
  --non-interactive --agree-tos --register-unsafely-without-email --redirect
sudo certbot renew --dry-run
```

Certbot adds the 443 server block and the HTTP→HTTPS redirect, and renews
through `certbot.timer`. `--register-unsafely-without-email` keeps personal
addresses out of Let's Encrypt. Use `-m <team address>` instead if you want
expiry notices.

## 6. Supabase and Google sign-in

Same as [`deploy-azure-vm-render.md`](deploy-azure-vm-render.md) step 3, with
the VM host name:

- **Google OAuth client (Web application).** Authorized JavaScript origin
  `https://<host>`. Authorized redirect URI: the callback on Supabase's Google
  provider page (`https://<project-ref>.supabase.co/auth/v1/callback`). While the
  app is in Testing, add presenters as test users.
- **Supabase → Authentication → URL Configuration.** Site URL `https://<host>`.
  Redirect URLs: `https://<host>/setup`. If `/setup` is missing from the list,
  Supabase silently sends users to the Site URL instead.

To check from the command line that the provider is on and the flow reaches
Google:

```bash
curl -s "https://<project-ref>.supabase.co/auth/v1/settings" -H "apikey: sb_publishable_<key>"   # "google": true
curl -s -o /dev/null -w "%{redirect_url}\n" \
  "https://<project-ref>.supabase.co/auth/v1/authorize?provider=google&redirect_to=https://<host>/setup" \
  -H "apikey: sb_publishable_<key>"                                                              # accounts.google.com/...
```

## 7. Verify

```bash
H=https://jagsi-demo-90ab.japaneast.cloudapp.azure.com
curl -s -o /dev/null -w "%{http_code}\n" $H/api/health                       # 200
curl -s $H/api/devices/jagsi-watch-01/telemetry/latest                         # "simulated": true; run twice, timestamp advances
for p in alerts?limit=20 devices/jagsi-watch-01/telemetry/history?limit=60 devices/jagsi-watch-01/summary devices/jagsi-watch-01/local-progress; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "$H/api/$p"; done             # all 200
curl -s -N -m 6 $H/api/stream                                                  # event: telemetry every ~2 s
curl -s -X POST $H/api/devices/jagsi-watch-01/daily-brief -H "Content-Type: application/json" -d '{}'   # "source": "rules"
for p in / /beranda /riwayat /darurat /profil /mcu /setup; do curl -s -o /dev/null -w "%{http_code} $p\n" $H$p; done   # 200
```

`/monitoring` answers 307. It redirects to `/beranda#tanda-vital` on purpose.

Then, in a private browser window: `/beranda` shows changing simulated readings,
**Perbarui ringkasan** returns the labelled rule-based summary, and on `/setup`
**Lanjutkan dengan Google** with a test account returns to `/setup` and shows
**Akun pengasuh**.

## Update to a newer commit

```bash
cd ~/JagSi && git pull --ff-only && git log --oneline -1
cd backend && .venv/bin/pip install -r requirements.txt -r requirements-demo.txt && sudo systemctl restart jagsi-backend
cd ../frontend && npm ci && npm run build && sudo systemctl restart jagsi-frontend
```

## Logs and troubleshooting

```bash
sudo systemctl status jagsi-backend jagsi-frontend --no-pager
sudo journalctl -u jagsi-backend -n 50 --no-pager
sudo journalctl -u jagsi-frontend -n 50 --no-pager
sudo tail -n 50 /var/log/nginx/error.log
```

| Symptom | Likely cause |
|---|---|
| 502 Bad Gateway | `jagsi-frontend` (for pages) or `jagsi-backend` (for `/api/`) is not running; check the journal |
| Readings do not change | backend stopped, or more than one worker; `curl .../telemetry/latest` twice |
| "Google belum dikonfigurasi" on `/setup` | Supabase values missing from `.env.local`, or the build ran before they were added: rebuild |
| Google returns to the wrong page | Supabase Redirect URLs lacks `https://<host>/setup` |
| `npm ci` says package.json and package-lock.json are out of sync | the lockfile was not regenerated after a dependency change (fixed in #33); run `npm install` locally and commit the lockfile |
| `ssh` times out | your public IP changed; update the `ssh-my-ip` rule |
| Browser shows a certificate from another issuer | software on that computer inspects HTTPS (e.g. parental-control apps). Check from another device; the server's certificate is Let's Encrypt |

## Remove everything

```bash
az group delete -n jagsi-web-rg      # VM, disk, IP, firewall; the host name is released
```

The IoT Hub from issue #8 is in a separate resource group (`jagsi-rg`, see
[`azure-setup.md`](azure-setup.md)) and is not affected.


### Enable hosted MCU scanning

Install OpenCV's system dependency with `sudo apt-get install -y libgl1`.
From the backend directory, install the OCR packages with
`.venv/bin/pip install -r requirements-mcu.txt`.
In `/etc/jagsi/backend.env`, set `JAGSI_HOSTED_MCU=1` and use the same
`JAGSI_SUPABASE_URL` and `JAGSI_SUPABASE_PUBLISHABLE_KEY` as hosted pairing.
Apply the API upload limit shown in the Nginx configuration to the active HTTPS
server, then validate with `sudo nginx -t` and reload Nginx.
Rebuild and restart the frontend and restart `jagsi-backend`.
Leave `NEXT_PUBLIC_JAGSI_MCU_API` unset for the same-origin Azure deployment.
A POST to /api/mcu/extract without a session should return HTTP 401.
Sign in and scan a sample PNG to confirm the review table displays extracted rows.
