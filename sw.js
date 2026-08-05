/* Pocket Python offline cache.
   Caches the app shell and every Pyodide asset the first time it loads,
   so the whole thing works with the network off afterwards. */
const CACHE = "pocketpy-v1";
const SHELL = ["./", "./python-ide.html", "./manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const u = new URL(e.request.url);
  const mine = u.origin === location.origin;
  const runtime = /cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com/.test(u.host);
  if (!mine && !runtime) return;                 // github and pypi stay live
  e.respondWith(
    caches.match(e.request).then(hit => {
      if (hit) return hit;
      return fetch(e.request).then(res => {
        if (res && (res.ok || res.type === "opaque")) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
    })
  );
});

self.addEventListener("message", e => {
  if (e.data === "clear") caches.delete(CACHE);
});
