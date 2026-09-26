// CalorieCast Mobile PWA Service Worker
const CACHE_NAME = 'caloriecast-v1.0';

const PRECACHE_ASSETS = [
  '/',
  '/static/index.html',
  '/static/dashboard.html',
  '/static/workouts.html',
  '/static/nutrition.html',
  '/static/ai_agent.html',
  '/static/live.html',
  '/static/predict.html',
  '/static/login.html',
  '/static/admin.html',
  '/static/css/style.css',
  '/static/js/auth.js',
  '/static/js/api.js',
  '/static/js/body_map.js',
  '/static/js/dashboard.js',
  '/static/js/workouts.js',
  '/static/js/nutrition.js',
  '/static/js/ai_agent.js',
  '/static/js/live.js',
  '/static/js/predict.js',
  '/static/js/pwa.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-maskable.png',
  '/static/icons/favicon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Pre-caching offline mobile shell');
      return cache.addAll(PRECACHE_ASSETS).catch(err => {
        console.warn('[ServiceWorker] Some pre-cache assets failed:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[ServiceWorker] Removing old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Bypass WebSockets and uploads
  if (url.protocol.startsWith('ws') || url.pathname.startsWith('/uploads')) {
    return;
  }

  // API Requests: Network-first with cache fallback
  if (url.pathname.startsWith('/workouts') ||
      url.pathname.startsWith('/nutrition') ||
      url.pathname.startsWith('/exercises') ||
      url.pathname.startsWith('/ai') ||
      url.pathname.startsWith('/users')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Static Assets: Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
