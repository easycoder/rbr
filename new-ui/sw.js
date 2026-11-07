// Room By Room PWA service worker.
//
// Strategy: NETWORK-FIRST for all same-origin GET requests.
//   - Every request tries the network first; on success the response is
//     cached for offline fallback. On network failure (offline / DNS / 5xx)
//     the cached copy is served instead.
//   - This keeps active development friction-free: edits land within one
//     refresh, so CACHE_VERSION does not need bumping for every source edit.
//     Bump it when the *shape* of the shell changes — an old cached script
//     paired with a new layout raises errors such as a missing element. A
//     bump forces install to precache the current shell and activate to drop
//     the old cache. The PWA still works offline because the cache fills up
//     as the user browses online.
//   - APP_SHELL is precached on install so the very first offline visit
//     after install has something to serve. Subsequent online visits keep
//     it fresh.
//   - The two cross-origin scripts the app boots from (the AllSpeak runtime
//     and the MQTT client) are cached the same way — network-first, cache
//     fallback — and precached on install as well. Without them a reload that
//     lands with no network renders an empty page with no script left to
//     recover it, which is exactly the state a phone wakes up into. A CDN
//     hiccup during install is tolerated, so it cannot block a service-worker
//     update; the next load that reaches the CDN fills the cache.
//   - Every other cross-origin request (the MQTT broker WebSocket) is
//     pass-through — no caching, no interception.

const CACHE_VERSION = 'rbr-v1-2611071508';
const CACHE_NAME = `rbr-cache-${CACHE_VERSION}`;

// The bare URLs: index.html pins the runtime with a `?v=` query, and matching
// on origin + path leaves that pin free to change without editing this file.
// The cache itself is keyed by the full requested URL, so a changed pin misses
// and fetches the new build; `ignoreSearch` is only the offline fallback.
const CDN_SCRIPTS = [
    'https://allspeak.ai/dist/allspeak.js',
    'https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js'
];

function isCdnScript(url) {
    return CDN_SCRIPTS.indexOf(url.origin + url.pathname) >= 0;
}

const APP_SHELL = [
    './',
    './index.html',
    './manifest.webmanifest',
    './icons/icon-192.png',
    './icons/icon-512.png',
    './resources/css/tokens.css',
    './resources/allspeak/shell.allspeak',
    './resources/json/seed-rooms.json',
    './resources/webson/layout.json',
    './resources/webson/top-bar.json',
    './resources/webson/summary-card.json',
    './resources/webson/room-row.json',
    './resources/webson/sheet.json',
    './resources/webson/menu-sheet.json',
    './resources/webson/journal-sheet.json',
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
    './resources/icon/edit.svg',
    './resources/icon/edit-text.png',
    './resources/icon/advance.svg'
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
        // The boot scripts, as above. A failure here must not fail the install:
        // online the app still boots, and the next load that reaches the CDN
        // caches it through the fetch handler.
        await Promise.all(CDN_SCRIPTS.map(async url => {
            try {
                const res = await fetch(url, { cache: 'reload' });
                if (res && (res.ok || res.type === 'opaque')) await cache.put(url, res);
            } catch (err) { /* offline install — any earlier cached copy stands */ }
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

// Network-first for the CDN boot scripts too. Online, the response refreshes
// the cache (so a CDN update is picked up); offline, the last copy that worked
// is served and the app can at least boot and keep retrying the broker.
async function serveCdnScript(req) {
    try {
        const res = await fetch(req);
        if (res && (res.ok || res.type === 'opaque')) {
            const copy = res.clone();
            const cache = await caches.open(CACHE_NAME);
            cache.put(req, copy);
        }
        return res;
    } catch (err) {
        const cached = (await caches.match(req)) || (await caches.match(req, { ignoreSearch: true }));
        if (cached) return cached;
        throw err;
    }
}

self.addEventListener('fetch', event => {
    const req = event.request;
    const url = new URL(req.url);

    // The two boot scripts are cross-origin but must survive an offline start.
    if (req.method === 'GET' && isCdnScript(url)) {
        event.respondWith(serveCdnScript(req));
        return;
    }

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
