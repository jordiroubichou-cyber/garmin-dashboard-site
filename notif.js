/* Emberline — activation des notifications « bilan du jour ».
   Affiche un bouton tant que cet appareil n'est pas abonné, puis enregistre l'abonnement
   dans le dépôt GitHub (fichier push_subscriptions.json) avec le jeton déjà mémorisé par le dashboard.
   Sans jeton : l'abonnement s'affiche, à coller dans le secret GitHub PUSH_SUBSCRIPTION.
   Pour réafficher le bouton : ouvrir le dashboard avec #notifs à la fin de l'adresse. */
(() => {
  const VAPID_PUBLIC = "BFEOF52H0KHA21j2woIVl-C3fbg0ML-KF4LcZrls4bE_-J-NWA0UU6CeqLZSveC0BF7IezH1IapLkdgNamVv3dw";
  const REPO = "jordiroubichou-cyber/garmin-dashboard", BRANCH = "main", FILE = "push_subscriptions.json";
  const KEY_DONE = "em_push_endpoint";

  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
  if (location.protocol === "file:") return;
  if (document.getElementById("pw")) return;                 // écran du mot de passe : on attend le dashboard

  const ls = { get: k => { try { return localStorage.getItem(k) || ""; } catch (_) { return ""; } },
               set: (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} } };
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const forced = location.hash === "#notifs";
  if (isIOS && !standalone && !forced) return;               // sur iPhone, seules les apps de l'écran d'accueil reçoivent des notifs

  const b64u = s => { const p = "=".repeat((4 - s.length % 4) % 4); const r = atob((s + p).replace(/-/g, "+").replace(/_/g, "/"));
                      return Uint8Array.from(r, c => c.charCodeAt(0)); };
  const utf8b64 = s => btoa(unescape(encodeURIComponent(s)));
  const b64utf8 = s => decodeURIComponent(escape(atob(s.replace(/\s/g, ""))));

  const css = `
  .emn{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom));transform:translateX(-50%);z-index:99999;
    display:flex;align-items:center;gap:10px;padding:13px 20px;border:0;border-radius:999px;background:#17130F;color:#F5EFE6;
    font:600 15px -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Arial,sans-serif;box-shadow:0 0 0 2px #CF7230,0 10px 30px -8px rgba(207,114,48,.6);cursor:pointer;white-space:nowrap}
  .emn svg{flex:none}.emn-x{margin-left:4px;opacity:.6;font-size:18px;line-height:1;padding:0 2px}
  .emn-m{position:fixed;inset:0;z-index:100000;background:rgba(23,19,15,.55);display:flex;align-items:flex-end;justify-content:center}
  .emn-c{background:#F5F0E8;color:#17130F;width:min(520px,100%);border-radius:24px 24px 0 0;padding:22px 20px calc(22px + env(safe-area-inset-bottom));
    font:15px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Arial,sans-serif}
  @media(prefers-color-scheme:dark){.emn-c{background:#24201C;color:#F5F0E8}}
  .emn-c h3{margin:0 0 8px;font-size:18px}.emn-c textarea{width:100%;box-sizing:border-box;height:120px;border-radius:12px;padding:10px;font:12px ui-monospace,Menlo,monospace;border:1.5px solid rgba(127,127,127,.35);background:transparent;color:inherit}
  .emn-c .row{display:flex;gap:10px;margin-top:12px}.emn-c button{flex:1;padding:12px;border:0;border-radius:12px;font-weight:700;font-size:15px;cursor:pointer}
  .emn-c .pri{background:#CF7230;color:#17130F}.emn-c .sec{background:rgba(127,127,127,.18);color:inherit}
  .emn-t{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom));transform:translateX(-50%);z-index:100001;background:#17130F;color:#F5EFE6;
    padding:12px 18px;border-radius:14px;font:600 14px -apple-system,BlinkMacSystemFont,Inter,Arial,sans-serif;box-shadow:0 0 0 2px #CF7230}`;
  const bell = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#CF7230" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>';

  function toast(msg, ms = 3500) { const t = document.createElement("div"); t.className = "emn-t"; t.textContent = msg; document.body.appendChild(t); setTimeout(() => t.remove(), ms); }

  async function ghSave(sub) {
    const tok = ls.get("gd_token");
    if (!tok) return false;
    const H = { Accept: "application/vnd.github+json", Authorization: "Bearer " + tok, "X-GitHub-Api-Version": "2022-11-28" };
    const url = `https://api.github.com/repos/${REPO}/contents/${FILE}`;
    let list = [], sha;
    const g = await fetch(url + "?ref=" + BRANCH, { headers: H, cache: "no-store" });
    if (g.ok) { const j = await g.json(); sha = j.sha; try { list = JSON.parse(b64utf8(j.content)); } catch (_) { list = []; } }
    else if (g.status !== 404) throw new Error("GitHub " + g.status);
    if (!Array.isArray(list)) list = [list];
    const me = sub.toJSON();
    me.device = (isIOS ? "iPhone/iPad" : navigator.platform || "appareil") + " · " + new Date().toISOString().slice(0, 10);
    list = list.filter(s => s && s.endpoint && s.endpoint !== me.endpoint).concat([me]).slice(-5);
    const body = { message: "Notifications : abonnement de cet appareil", branch: BRANCH, content: utf8b64(JSON.stringify(list, null, 2) + "\n") };
    if (sha) body.sha = sha;
    const p = await fetch(url, { method: "PUT", headers: { ...H, "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!p.ok) throw new Error("GitHub " + p.status);
    return true;
  }

  function manual(sub) {
    const m = document.createElement("div"); m.className = "emn-m";
    m.innerHTML = `<div class="emn-c" role="dialog" aria-label="Abonnement aux notifications"><h3>Dernière étape</h3>
      <p>Copie ce texte et colle-le dans le secret GitHub <b>PUSH_SUBSCRIPTION</b> du dépôt <i>garmin-dashboard</i>.</p>
      <textarea readonly>${JSON.stringify(sub.toJSON())}</textarea>
      <div class="row"><button class="pri" type="button" data-a="copy">Copier</button><button class="sec" type="button" data-a="ok">C'est fait</button></div></div>`;
    document.body.appendChild(m);
    m.querySelector("[data-a=copy]").onclick = async () => { const ta = m.querySelector("textarea"); ta.select();
      try { await navigator.clipboard.writeText(ta.value); } catch (_) { document.execCommand("copy"); } toast("Copié ✓"); };
    m.querySelector("[data-a=ok]").onclick = () => { ls.set(KEY_DONE, sub.endpoint); m.remove(); toast("Notifications activées ✓"); };
  }

  async function enable(btn) {
    btn.disabled = true;
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { toast("Notifications refusées. Réglages iPhone › Notifications › Emberline pour les autoriser."); btn.disabled = false; return; }
      await navigator.serviceWorker.register("sw.js");
      const reg = await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64u(VAPID_PUBLIC) });
      btn.remove();
      let saved = false;
      try { saved = await ghSave(sub); } catch (e) { console.warn("Emberline notifs :", e); }
      if (saved) { ls.set(KEY_DONE, sub.endpoint); toast("Notifications activées ✓ Rendez-vous demain matin."); }
      else manual(sub);
    } catch (e) {
      console.warn("Emberline notifs :", e); btn.disabled = false; toast("Activation impossible : " + (e.message || e));
    }
  }

  async function init() {
    let sub = null;
    try { const reg = await navigator.serviceWorker.getRegistration(); sub = reg ? await reg.pushManager.getSubscription() : null; } catch (_) {}
    const done = Notification.permission === "granted" && sub && ls.get(KEY_DONE) === sub.endpoint;
    if (done && !forced) return;
    if (!forced && ls.get("em_push_later") === new Date().toISOString().slice(0, 10)) return;   // « plus tard » : on ne redemande pas aujourd'hui
    const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "emn";
    btn.innerHTML = `${bell}<span>Activer les notifications</span><span class="emn-x" role="button" aria-label="Plus tard">&times;</span>`;
    btn.addEventListener("click", e => {
      if (e.target.classList.contains("emn-x")) { e.stopPropagation(); ls.set("em_push_later", new Date().toISOString().slice(0, 10)); btn.remove(); return; }
      enable(btn);
    });
    document.body.appendChild(btn);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
