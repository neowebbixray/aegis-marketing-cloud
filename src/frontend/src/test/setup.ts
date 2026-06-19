import '@testing-library/jest-dom/vitest';

// jsdom defaults to 'about:blank' which makes window.location.origin === 'null'.
// The api client uses `new URL(path, window.location.origin)` to build fetch URLs,
// so we need a proper origin.
import { vi } from 'vitest';

if (typeof window !== 'undefined') {
  // Preserve the original descriptor so we can restore it if needed
  Object.defineProperty(window, 'location', {
    value: new URL('http://localhost:3000'),
    writable: true,
    configurable: true,
  });
}
