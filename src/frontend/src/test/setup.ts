import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// jsdom defaults to 'about:blank' which makes window.location.origin === 'null'.
// The api client uses `new URL(path, window.location.origin)` to build fetch URLs,
// so we need a proper origin.
if (typeof window !== 'undefined') {
  // jsdom's location has no href setter; replace with a minimal mock
  // that allows href writes (needed by the 401 redirect handler).
  const loc: Partial<Location> = {
    href: 'http://localhost:3000',
    origin: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    hostname: 'localhost',
    port: '3000',
    pathname: '/',
    search: '',
    hash: '',
    ancestorOrigins: [] as unknown as DOMStringList,
    assign: vi.fn(),
    reload: vi.fn(),
    replace: vi.fn(),
  };
  Object.defineProperty(window, 'location', {
    value: loc,
    writable: true,
    configurable: true,
  });
}

// Mock fetch globally for API tests
export const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);