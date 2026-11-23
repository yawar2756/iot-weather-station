// GPCA Weather Station - Service Worker
// Provides offline support and caching for the dashboard

const CACHE_NAME = 'gpca-weather-v2';
const STATIC_CACHE = 'gpca-weather-static-v2';
const API_CACHE = 'gpca-weather-api-v2';

// Assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/about',
  '/static/css/main.css',
  '/static/favicon.png',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// API endpoints to cache with network-first strategy
const API_ENDPOINTS = [
  '/api/latest',
  '/api/history'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache with appropriate strategy
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests (except known CDNs)
  if (url.origin !== location.origin &&
      !url.href.includes('fonts.googleapis.com') &&
      !url.href.includes('cdnjs.cloudflare.com') &&
      !url.href.includes('cdn.jsdelivr.net')) {
    return;
  }

  // HTML pages - Network First (to ensure users get the latest UI)
  if (event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }

  // API endpoints - Network First
  if (API_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint))) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }

  // Static assets - Cache First, fallback to network
  event.respondWith(cacheFirstStrategy(event.request));
});

// Network First Strategy - for API data
async function networkFirstStrategy(request) {
  const cache = await caches.open(API_CACHE);

  try {
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // Network failed - try cache
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      // Add header to indicate offline data (Response headers are immutable,
      // so build a new Response instead of mutating the clone)
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-Offline', 'true');
      const body = await cachedResponse.clone().text();
      return new Response(body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers,
      });
    }

    // No cache - return offline page or error
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'No cached data available',
        device_status: 'Offline'
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Cache First Strategy - for static assets
async function cacheFirstStrategy(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const response = await fetch(request);

    if (response.ok) {
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // For HTML pages, return a basic offline page
    if (request.headers.get('accept')?.includes('text/html')) {
      return caches.match('/') || new Response('Offline', { status: 503 });
    }

    return new Response('Offline', { status: 503 });
  }
}

// Background sync for data upload (future enhancement)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-weather-data') {
    event.waitUntil(syncWeatherData());
  }
});

async function syncWeatherData() {
  // Placeholder for future: sync pending data when online
  console.log('[SW] Background sync triggered');
}

// Push notifications (future enhancement)
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.message || 'Weather alert',
    icon: '/static/favicon.png',
    badge: '/static/favicon.png',
    vibrate: [200, 100, 200],
    tag: 'weather-alert',
    requireInteraction: true,
    actions: [
      { action: 'view', title: 'View Dashboard' },
      { action: 'dismiss', title: 'Dismiss' }
    ],
    data: { url: '/dashboard' }
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'GPCA Weather Alert', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Focus existing window if open
          for (const client of clientList) {
            if (client.url.includes('/dashboard') && 'focus' in client) {
              return client.focus();
            }
          }
          // Open new window
          return clients.openWindow('/dashboard');
        })
    );
  }
});

// Message handler for communication with main thread
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }

  if (event.data === 'getCacheStatus') {
    event.ports[0].postMessage({
      staticCache: STATIC_CACHE,
      apiCache: API_CACHE
    });
  }
});

console.log('[SW] Service Worker loaded');