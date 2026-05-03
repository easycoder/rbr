// Room By Room PWA service worker.
//
// Strategy:
//   - App-shell static assets (HTML, CSS, .as, webson, icons) are cache-first
//     so the page loads offline. Cache name carries a version that bumps with
//     each deploy; old caches are purged on activate.
//   - credentials.json is network-first (fall back to cache) so deploy-time
//     config changes take effect on the next online visit.
//   - Cross-origin requests (the AllSpeak runtime CDN, MQTT broker WS) are
//     pass-through — no caching, no interception.

const CACHE_VERSION = 'rbr-v1-26050308';
const CACHE_NAME = `rbr-cache-${CACHE_VERSION}`;

const APP_SHELL = [
    './',
    './index.html',
    './manifest.webmanifest',
    './icons/icon-192.png',
    './icons/icon-512.png',
    './resources/css/tokens.css',
    './resources/as/shell.as',
    './resources/json/seed-rooms.json',
    './resources/webson/layout.json',
    './resources/webson/top-bar.json',
    './resources/webson/summary-card.json',
    './resources/webson/room-row.json',
    './resources/webson/sheet.json',
    './resources/webson/menu-sheet.json',
    './resources/webson/profile-sheet.json',
    './resources/webson/profile-row.json',
    './resources/webson/calendar-pill.json',
    './resources/webson/schedule-editor.json',
    './resources/webson/schedule-period.json',
    './resources/webson/sched-profile-pill.json',
    './resources/webson/about-sheet.json',
    './resources/webson/device-editor.json',
    './demo-map.json',
    './resources/icon/app-icon.svg',
    './resources/icon/boost.svg',
    './resources/icon/calendar.svg',
    './resources/icon/chevron.svg',
    './resources/icon/clock.svg',
    './resources/icon/close.svg',
    './resources/icon/flame.svg',
    './resources/icon/house.svg',
    './resources/icon/off.svg',
    './resources/icon/offline.svg',
    './resources/icon/on.svg',
    './resources/icon/sensor.svg'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k.startsWith('rbr-cache-') && k !== CACHE_NAME)
                .map(k => caches.delete(k))
        )).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const req = event.request;
    const url = new URL(req.url);

    // Only handle same-origin GET. Everything else passes through.
    if (req.method !== 'GET' || url.origin !== self.location.origin) return;

    // Network-first for credentials so a re-deploy takes effect immediately.
    if (url.pathname.endsWith('/credentials.json')) {
        event.respondWith(
            fetch(req).then(res => {
                const copy = res.clone();
                caches.open(CACHE_NAME).then(c => c.put(req, copy));
                return res;
            }).catch(() => caches.match(req))
        );
        return;
    }

    // Cache-first for everything else under our scope. The `?v=` cat now
    // cache-busting query is stripped during match so subsequent loads with
    // different timestamps still hit the cache.
    event.respondWith(
        caches.match(req, { ignoreSearch: true }).then(cached => {
            if (cached) return cached;
            return fetch(req).then(res => {
                if (res && res.status === 200 && res.type === 'basic') {
                    const copy = res.clone();
                    caches.open(CACHE_NAME).then(c => c.put(req, copy));
                }
                return res;
            });
        })
    );
});
