# Local JagSi onboarding and presentation console

Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY in frontend/.env.local. Enable Google in Supabase Auth and allow the exact frontend URL ending in /setup as a redirect. Keep the Google client secret in Supabase. Restart Next.js after changing its environment.

For a fictional rehearsal set NEXT_PUBLIC_JAGSI_PAIRING_PREVIEW=1 and point NEXT_PUBLIC_JAGSI_API and NEXT_PUBLIC_JAGSI_MCU_API to http://127.0.0.1:8013. Use the same configured watch ID on both sides. Start the local simulated backend with JAGSI_DEMO_CONSOLE=1, JAGSI_LOCAL_VITALS=stable, a dedicated JAGSI_DB_PATH, JAGSI_LOCAL_MCU=1 and JAGSI_CORS_ORIGINS=http://127.0.0.1:3096. Bind to 127.0.0.1:8013 only.

Open /setup on the frontend and /demo-console on the backend. Generate a five-minute single-use pairing code and enter it in setup. The console can pause and resume the stream, switch display bands, and inject fall or SOS alerts to rehearse alert handling. Fall injection exercises the alert flow directly. Model evaluation requires a separate motion replay.

OAuth saves registration fields in Supabase user metadata. Demo codes connect the setup preview to its configured simulated watch. Physical device provisioning, server-side wearer ownership and protected telemetry remain production integration work.
