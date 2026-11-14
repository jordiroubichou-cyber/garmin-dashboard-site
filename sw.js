/* Emberline — service worker.
   Page (ouverture de l'app) : servie tout de suite depuis le cache, pour que l'intro démarre sans attendre ; la page demande
   elle-même la nouvelle version pendant l'animation (adresse « ?em=net », non interceptée) et met le cache à jour.
   Autres lectures de la page (tirer pour actualiser) : réseau d'abord, cache si hors ligne. Rapport PDF chiffré : idem, gardé avec la page.
   Polices Google (Fraunces) : cache, rafraîchi en arrière-plan.
   Notifications : affiche les messages envoyés à 7 h, 14 h et 21 h par GitHub Actions (send_push.py), le rappel de mobilité de 20 h
   (ouvre l'onglet Mobilité) et le rappel du bilan du soir de 22 h.
   Rien d'autre n'est intercepté. */
const V = "emberline-v4";
const CORE = ["./index.html", "./manifest.webmanifest", "./notif.js", "./ptr.js",
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
    if (r && r.ok) {
      await c.put(key, r.clone());
      // nouvelle page = nouvelle clé du rapport : on garde en cache le rapport chiffré qui va avec (hors ligne)
      if (isPage) e.waitUntil(fetch("./rapport.bin", { cache: "no-store" }).then(x => x.ok && c.put("./rapport.bin", x)).catch(() => {}));
    }
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

async function cacheFirstPage(e, req) {
  const c = await caches.open(V);
  const hit = await c.match(PAGE, { ignoreSearch: true });
  return hit || networkFirst(e, req, true);
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
  if (u.searchParams.get("em") === "net") return;           // la page vérifie elle-même la dernière version
  const isPage = req.mode === "navigate" || /\/(index\.html)?$/.test(u.pathname);
  if (u.pathname.endsWith("/rapport.bin")) { e.respondWith(networkFirst(e, req, false)); return; }
  if (isPage) { e.respondWith(req.mode === "navigate" ? cacheFirstPage(e, req) : networkFirst(e, req, true)); return; }
  if (CORE.some(p => u.pathname.endsWith(p.slice(1)))) e.respondWith(networkFirst(e, req, false));
});

/* ---------- Notifications ---------- */
// iOS exige qu'une notification soit affichée à chaque message reçu (sinon l'abonnement est coupé).
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  const title = d.title || "Emberline";
  const opts = {
    body: d.body || "Ton bilan du jour est prêt.",
    icon: "icon-192.png",
    badge: "icon-192.png",
    tag: d.tag || "bilan-du-jour",           // remplace la notif de la veille au lieu de s'empiler
    renotify: true,
    data: { url: d.url || "./" }
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

// Toucher la notification ouvre (ou ramène au premier plan) Emberline.
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "./", self.registration.scope).href;
  e.waitUntil((async () => {
    const all = await clients.matchAll({ type: "window", includeUncontrolled: true });
    const hash = new URL(url).hash;               // ex. #mob : rappel de mobilité de 20 h -> onglet Mobilité
    for (const c of all) {
      if (c.url.startsWith(self.registration.scope)) { if (hash) c.postMessage({ type: "em-open", hash }); await c.focus(); return; }
    }
    await clients.openWindow(url);
  })());
});
