// Offline pack service worker. It does nothing until the person presses "Download offline pack"
// (that is what registers it). Then it keeps a copy of the app files, the calculators' source and the
// in-browser Python runtime, and serves them when there is no network.
const CACHE = "jarvis-offline-v1";
const SAME_OK = (p) => p === "/" || p === "/index.html" || p === "/sw.js" || p.startsWith("/assets/") || p.startsWith("/offline/") || p === "/rural/schemes" || /\.(js|css|svg|png|jpg|ico|woff2|json)$/.test(p);
const CDN_OK = (h) => h === "cdn.jsdelivr.net" || h === "fonts.googleapis.com" || h === "fonts.gstatic.com";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const u = new URL(req.url);
  const same = u.origin === location.origin;
  if (!((same && SAME_OK(u.pathname)) || CDN_OK(u.hostname))) return;
  // Pages and data: the network when it is there (so updates arrive), the saved copy when it is not.
  // Hashed assets and the Python runtime never change under the same URL: saved copy first.
  const networkFirst = same && (u.pathname === "/" || u.pathname === "/index.html" || u.pathname.startsWith("/offline/") || u.pathname === "/rural/schemes");
  e.respondWith(networkFirst ? netFirst(req) : cacheFirst(req));
});

async function netFirst(req) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = (await cache.match(req)) || (new URL(req.url).pathname === "/" ? await cache.match("/index.html") : undefined);
    if (hit) return hit;
    throw err;
  }
}

async function cacheFirst(req) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok || res.type === "opaque") cache.put(req, res.clone());
  return res;
}
