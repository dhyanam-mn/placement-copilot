import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { HealthBanner } from '@/components/HealthBanner';

export const metadata: Metadata = {
  title: 'Placement Copilot',
  description: 'A quiet, multi-agent job-search assistant for VIT students.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-text min-h-screen antialiased flex flex-col">
        <HealthBanner />
        <div className="flex flex-1 min-h-screen">
          <Sidebar />
          <main className="flex-1 p-8 lg:p-12 overflow-y-auto max-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
