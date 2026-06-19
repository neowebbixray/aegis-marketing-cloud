'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';
import { ArrowRight, BarChart3, Shield, Zap } from 'lucide-react';
import { Button } from '@/components/atoms/button';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace('/dashboard');
    }
  }, [router]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Navbar */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Aegis</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Features
            </a>
            <a href="#about" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              About
            </a>
            <Button variant="ghost" onClick={() => router.push('/login')}>
              Sign In
            </Button>
            <Button onClick={() => router.push('/register')}>
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 py-24 text-center">
        <div className="mx-auto max-w-3xl space-y-6">
          <div className="inline-flex items-center rounded-full border px-4 py-1.5 text-sm font-medium bg-muted">
            ✨ AI-Powered Marketing Platform
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            Transform Your Marketing with{' '}
            <span className="text-primary">Intelligent Automation</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Aegis Marketing Cloud combines AI-driven CRM, campaign automation, and
            multi-channel analytics in one unified platform.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button size="lg" onClick={() => router.push('/register')}>
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => router.push('/login')}>
              Sign In
            </Button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t py-16">
        <div className="container">
          <div className="grid gap-8 md:grid-cols-3">
            <div className="flex flex-col items-center text-center space-y-3 p-6">
              <div className="rounded-full bg-primary/10 p-4">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold">AI-Powered Insights</h3>
              <p className="text-sm text-muted-foreground">
                Leverage machine learning to predict customer behavior and optimize campaigns.
              </p>
            </div>
            <div className="flex flex-col items-center text-center space-y-3 p-6">
              <div className="rounded-full bg-primary/10 p-4">
                <BarChart3 className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold">Multi-Channel Analytics</h3>
              <p className="text-sm text-muted-foreground">
                Unify data from email, social, web, and paid channels in one dashboard.
              </p>
            </div>
            <div className="flex flex-col items-center text-center space-y-3 p-6">
              <div className="rounded-full bg-primary/10 p-4">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold">Enterprise Security</h3>
              <p className="text-sm text-muted-foreground">
                SOC 2 compliant with role-based access control and data encryption at rest.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Aegis Marketing Cloud. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
