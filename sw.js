/* Emberline — service worker.
   Page : réseau d'abord (toujours la dernière version), cache si hors ligne.
   Polices Google (Fraunces) : cache, rafraîchi en arrière-plan.
   Rien d'autre n'est intercepté. */
const V = "emberline-v1";
const CORE = ["./index.html", "./manifest.webmanifest",
  "./icon-180.png", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png", "./favicon-32.png"];
const FONTS = "emberline-fonts";

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== V && k !== FONTS).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// La page (« / » ou « /index.html », avec ou sans paramètres) est rangée sous une seule clé.
const PAGE = "./index.html";
async function networkFirst(e, req, isPage) {
  const c = await caches.open(V);
  const key = isPage ? PAGE : req;
  const net = fetch(req, { cache: "no-store" }).then(async r => {
    if (r && r.ok) await c.put(key, r.clone());
    return r;
  });
  e.waitUntil(net.catch(() => {}));                       // la mise en cache se termine même si le cache a répondu avant
  const cached = await c.match(key, { ignoreSearch: true });
  if (!cached) return net.catch(() => Response.error());
  // Réseau lent ou coupé (métro, 4G faible) : la dernière version connue s'affiche après 4 s.
  const slow = new Promise(res => setTimeout(() => res(cached), 4000));
  const fresh = net.then(r => (r && r.ok) ? r : cached, () => cached);
  return Promise.race([fresh, slow]);
}

async function fontCache(req) {
  const c = await caches.open(FONTS);
  const hit = await c.match(req);
  const net = fetch(req).then(r => { if (r && (r.ok || r.type === "opaque")) c.put(req, r.clone()); return r; })
                        .catch(() => undefined);
  return hit || (await net) || Response.error();
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.hostname === "fonts.googleapis.com" || u.hostname === "fonts.gstatic.com") {
    e.respondWith(fontCache(req)); return;
  }
  if (u.origin !== self.location.origin) return;
  const isPage = req.mode === "navigate" || /\/(index\.html)?$/.test(u.pathname);
  if (isPage) { e.respondWith(networkFirst(e, req, true)); return; }
  if (CORE.some(p => u.pathname.endsWith(p.slice(1)))) e.respondWith(networkFirst(e, req, false));
});
