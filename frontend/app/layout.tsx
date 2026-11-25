import type { Metadata } from 'next';
import './globals.css';

import { EmergencyAlertsProvider } from '@/components/EmergencyAlertsProvider';
import { elder } from '@/lib/mock-data';

export const metadata: Metadata = {
  title: 'JagSi (Jaga Lansia) — Caregiver Dashboard',
  description:
    'Cloud-connected wearable health monitoring and caregiver companion for elderly individuals.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&amp;family=Geist:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-surface-container-low text-on-surface antialiased">
        {/* One alert WebSocket for the whole app, so the emergency screen shows on every page (#13). */}
        <EmergencyAlertsProvider elderName={elder.name}>
          <div className="min-h-screen bg-background">
            <main className="min-h-screen">{children}</main>

          </div>
        </EmergencyAlertsProvider>
      </body>
    </html>
  );
}
