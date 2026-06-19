import Link from 'next/link';
import { BarChart3, WifiOff } from 'lucide-react';
import { Button } from '@/components/atoms/button';

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4">
      <div className="rounded-lg bg-primary p-3 mb-6">
        <BarChart3 className="h-10 w-10 text-primary-foreground" />
      </div>
      <WifiOff className="h-16 w-16 text-muted-foreground mb-4" />
      <h1 className="text-2xl font-bold mb-2">You&apos;re Offline</h1>
      <p className="text-muted-foreground text-center max-w-md mb-8">
        Aegis Marketing Cloud requires an internet connection. Some features
        may be limited until you reconnect.
      </p>
      <Button asChild>
        <Link href="/dashboard">Try Again</Link>
      </Button>
    </div>
  );
}
