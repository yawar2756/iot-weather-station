// GPCA Weather Station - Service Worker (v2)
// Rules:
//   * Pages (HTML)     -> network first, cached copy only if offline
//   * /api/*           -> never cached, except latest/history as an offline fallback
//   * /static + CDNs   -> stale-while-revalidate (fast, but updates on the next visit)
// Bump VERSION whenever you want every visitor's old caches wiped.

const VERSION = 'v3';
const STATIC_CACHE = `gpca-weather-static-${VERSION}`;
const PAGE_CACHE = `gpca-weather-pages-${VERSION}`;
const API_CACHE = `gpca-weather-api-${VERSION}`;
const KNOWN_CACHES = [STATIC_CACHE, PAGE_CACHE, API_CACHE];

const STATIC_ASSETS = [
  '/static/css/main.css',
  '/static/css/index.css',
  '/static/css/dashboard.css',
  '/static/css/about.css',
  '/static/js/index.js',
  '/static/js/dashboard.js',
  '/static/js/about.js',
  '/static/favicon.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.js'
];

const OFFLINE_FALLBACK_API = ['/api/latest', '/api/history'];
const CDN_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      // one bad asset must not block the whole install
      .then((cache) => Promise.allSettled(STATIC_ASSETS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.filter((n) => !KNOWN_CACHES.includes(n)).map((n) => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === location.origin;
  if (!sameOrigin && !CDN_HOSTS.includes(url.hostname)) return;

  if (sameOrigin && url.pathname.startsWith('/api/')) {
    if (OFFLINE_FALLBACK_API.some((p) => url.pathname.startsWith(p))) {
      event.respondWith(networkFirstApi(request));
    }
    return; // everything else under /api (export, seed...) goes straight to the network
  }

  if (request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html')) {
    event.respondWith(networkFirstPage(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirstPage(request) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    return cached || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
  }
}

async function networkFirstApi(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'Offline', device_status: 'Offline' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  const refresh = fetch(request)
    .then((response) => {
      if (response && (response.ok || response.type === 'opaque')) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);
  if (cached) return cached;
  return (await refresh) || new Response('Offline', { status: 503 });
}

self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});
