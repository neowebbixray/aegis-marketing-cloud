import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from '@/components/providers';
import { PWARegistration } from '@/components/pwa-registration';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: {
    default: 'Aegis Marketing Cloud',
    template: '%s | Aegis Marketing Cloud',
  },
  description:
    'Enterprise marketing platform with AI-powered CRM, campaign automation, and multi-channel analytics.',
  keywords: ['marketing', 'CRM', 'automation', 'AI', 'analytics'],
  authors: [{ name: 'Aegis Marketing Cloud' }],
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Aegis MC',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'Aegis Marketing Cloud',
    title: 'Aegis Marketing Cloud',
    description:
      'Enterprise marketing platform with AI-powered CRM, campaign automation, and multi-channel analytics.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
        <PWARegistration />
      </body>
    </html>
  );
}
