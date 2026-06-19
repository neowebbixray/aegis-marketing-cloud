'use client';

import { useEffect } from 'react';

/**
 * PWA service worker registration component.
 * Registers the service worker in production builds for offline support.
 */
export function PWARegistration() {
  useEffect(() => {
    if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          console.log('SW registered:', reg.scope);
        })
        .catch((err) => {
          console.warn('SW registration failed:', err);
        });
    }
  }, []);

  return null;
}
