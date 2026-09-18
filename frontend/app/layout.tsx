import type { Metadata } from 'next';
import './globals.css';

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
      <body className="bg-bg text-text min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
