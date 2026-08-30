const CACHE_NAME = 'abt-pwa-v1';
const STATIC_ASSETS = ['/', '/static/manifest.json', '/static/logo.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});
self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/') || e.request.url.includes('/ws')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});