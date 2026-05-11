// Room By Room PWA service worker.
//
// Strategy: NETWORK-FIRST for all same-origin GET requests.
//   - Every request tries the network first; on success the response is
//     cached for offline fallback. On network failure (offline / DNS / 5xx)
//     the cached copy is served instead.
//   - This keeps active development friction-free: edits land within one
//     refresh, no need to bump CACHE_VERSION or clear site data when a
//     source file changes. The PWA still works offline because the cache
//     fills up as the user browses online.
//   - APP_SHELL is precached on install so the very first offline visit
//     after install has something to serve. Subsequent online visits keep
//     it fresh.
//   - Cross-origin requests (the AllSpeak runtime CDN, MQTT broker WS) are
//     pass-through — no caching, no interception.

const CACHE_VERSION = 'rbr-v1-26051201';
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
    './resources/webson/device-room-pill.json',
    './resources/webson/system-sheet.json',
    './resources/webson/outside-sheet.json',
    './resources/webson/info-sheet.json',
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
    './resources/icon/sensor.svg',
    './resources/icon/snowflake.svg',
    './resources/icon/info.svg',
    './resources/icon/edit.svg'
];

// Install: fetch every app-shell asset with cache: 'reload' so we bypass the
// HTTP cache AND the previously-installed SW's fetch handler. If we just used
// cache.addAll() it would default to cache: 'default' and the old SW would
// intercept these fetches and serve them from its OLD cache — meaning a SW
// version bump would happily populate the new cache with stale content and
// nothing would ever escape. cache: 'reload' forces network.
self.addEventListener('install', event => {
    event.waitUntil((async () => {
        const cache = await caches.open(CACHE_NAME);
        await Promise.all(APP_SHELL.map(async url => {
            const res = await fetch(url, { cache: 'reload' });
            if (res && res.ok) await cache.put(url, res);
        }));
        await self.skipWaiting();
    })());
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

    // Network-first for every same-origin request. On a successful network
    // response, refresh the cache copy (so the next offline load gets the
    // latest known-good version). On network failure, fall back to whatever
    // the cache has for this URL — `ignoreSearch: true` strips the `?v=...`
    // query so the cache match isn't defeated by per-load timestamp busts.
    event.respondWith((async () => {
        try {
            const res = await fetch(req);
            if (res && res.status === 200 && res.type === 'basic') {
                const copy = res.clone();
                const cache = await caches.open(CACHE_NAME);
                cache.put(req, copy);
            }
            return res;
        } catch (err) {
            const cached = await caches.match(req, { ignoreSearch: true });
            if (cached) return cached;
            throw err;
        }
    })());
});
