/**
 * Phase 8: Progressive Web App — Service Worker
 *
 * Strategy:
 *   - Static assets  → cache-first (serve from cache, fall back to network)
 *   - API requests   → network-first (serve from network, fall back to cache)
 *   - Other          → network-only
 *
 * Versioning: bump CACHE_NAME when deploying new static assets so old caches
 * are evicted during the `activate` event.
 */

const CACHE_NAME = 'web-platform-v1';

// Core assets cached on install so the app shell loads offline
const PRECACHE_ASSETS = [
  '/static/index.html',
  '/static/app.js',
  '/static/manifest.json',
  '/static/locales/en.json',
  '/static/locales/es.json',
  '/static/locales/fr.json',
];

// ── Lifecycle events ───────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // Use individual requests so a single failed asset doesn't abort install
      Promise.allSettled(PRECACHE_ASSETS.map((url) => cache.add(url)))
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch handler ──────────────────────────────────────────────────────────────

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only intercept same-origin GET requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // API calls — network-first, no caching of responses
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    event.respondWith(
      fetch(request).catch(
        () =>
          new Response(
            JSON.stringify({ error: 'You appear to be offline.' }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' },
            }
          )
      )
    );
    return;
  }

  // Static assets — cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          })
      )
    );
    return;
  }
});
