/* Emberline — tirer pour actualiser.
   En haut de la page, tirer vers le bas fait apparaître un cercle discret entre la bannière et le bilan.
   Au-delà du seuil, relâcher recharge la page (dernière version publiée après la synchro). */
(() => {
  if (!("ontouchstart" in window)) return;
  if (document.getElementById("pw")) return;                       // écran du mot de passe

  const THRESHOLD = 72, MAX = 110, RESIST = 0.5, SIZE = 30;
  const css = `
  html,body{overscroll-behavior-y:contain}
  .ptr{height:0;overflow:hidden;display:flex;align-items:center;justify-content:center;pointer-events:none;will-change:height}
  .ptr.back{transition:height .32s cubic-bezier(.2,.9,.3,1)}
  .ptr-c{width:${SIZE}px;height:${SIZE}px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    background:var(--card,#F5F0E8);box-shadow:0 1px 6px rgba(23,19,15,.18),0 0 0 1px var(--line,rgba(127,127,127,.16));
    transform:scale(.7);opacity:0;transition:transform .2s ease,opacity .2s ease}
  .ptr.armed .ptr-c{transform:scale(1.06)!important}
  .ptr-c svg{display:block}
  .ptr.spin svg{animation:ptrspin .8s linear infinite}
  .ptr.spin .ptr-arc{stroke-dasharray:20 62;stroke-dashoffset:0!important;transition:none}
  @keyframes ptrspin{to{transform:rotate(360deg)}}
  .ptr-arc{transition:stroke-dashoffset .05s linear}
  .ptr-msg{position:fixed;left:50%;top:calc(14px + env(safe-area-inset-top));transform:translateX(-50%);z-index:100002;background:#17130F;color:#F5EFE6;
    padding:10px 16px;border-radius:12px;font:500 14px -apple-system,BlinkMacSystemFont,Inter,Arial,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)}`;
  const C = 2 * Math.PI * 13;                                      // périmètre de l'arc (r = 13)

  function mount() {
    const st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
    const box = document.createElement("div"); box.className = "ptr"; box.setAttribute("aria-hidden", "true");
    box.innerHTML = `<div class="ptr-c"><svg width="${SIZE - 8}" height="${SIZE - 8}" viewBox="0 0 32 32">
      <circle cx="16" cy="16" r="13" fill="none" stroke="rgba(127,127,127,.16)" stroke-width="2.4"/>
      <circle class="ptr-arc" cx="16" cy="16" r="13" fill="none" stroke="#CF7230" stroke-width="2.4" stroke-linecap="round"
        stroke-dasharray="${C}" stroke-dashoffset="${C}" transform="rotate(-90 16 16)"/></svg></div>`;
    // juste sous la bannière : après son conteneur direct dans <body> (ex. .hwrap, dont la hauteur est fixée)
    let top = document.querySelector("header.top") || document.querySelector("header");
    while (top && top.parentElement && top.parentElement !== document.body) top = top.parentElement;
    if (top && top.parentNode) top.parentNode.insertBefore(box, top.nextSibling); else document.body.prepend(box);
    return box;
  }

  let box, circle, arc, svg, y0 = 0, x0 = 0, pulling = false, decided = false, dist = 0, busy = false;

  const atTop = () => (window.scrollY || document.documentElement.scrollTop || 0) <= 0;
  const blocked = t => document.body.style.overflow === "hidden" ||
    (t && t.closest && t.closest('[role="dialog"].on, .emn-m, input, textarea, select, .seg, [data-noptr]'));

  function render() {
    const p = Math.min(1, dist / THRESHOLD);
    box.style.height = dist + "px";
    circle.style.opacity = Math.min(1, dist / 30);
    circle.style.transform = `scale(${0.7 + 0.3 * p})`;
    svg.style.transform = `rotate(${p * 270}deg)`;
    arc.style.strokeDashoffset = C * (1 - p * 0.92);
    box.classList.toggle("armed", dist >= THRESHOLD);
  }

  function reset() {
    box.classList.add("back"); dist = 0; render();
    setTimeout(() => { box.classList.remove("back", "spin", "armed"); circle.style.transform = ""; svg.style.transform = ""; }, 340);
  }

  function msg(t) { const m = document.createElement("div"); m.className = "ptr-msg"; m.textContent = t; document.body.appendChild(m); setTimeout(() => m.remove(), 2600); }

  async function refresh() {
    busy = true;
    box.classList.add("back", "spin"); dist = 50; box.style.height = dist + "px"; svg.style.transform = "";
    circle.style.opacity = 1; circle.style.transform = "scale(1)";
    const url = location.href.split("#")[0];
    try {
      const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 9000);
      const r = await fetch(url, { cache: "no-store", signal: ctl.signal });   // met aussi à jour le cache hors ligne
      clearTimeout(to);
      if (!r.ok) throw new Error(r.status);
      location.reload();
    } catch (e) {
      busy = false; reset(); msg("Pas de réseau : la dernière version reste affichée.");
    }
  }

  function start(e) {
    if (busy || e.touches.length !== 1 || !atTop() || blocked(e.target)) { pulling = false; return; }
    pulling = true; decided = false; dist = 0;
    y0 = e.touches[0].clientY; x0 = e.touches[0].clientX;
  }

  function move(e) {
    if (!pulling) return;
    const dy = e.touches[0].clientY - y0, dx = e.touches[0].clientX - x0;
    if (!decided) {
      if (Math.abs(dy) < 8 && Math.abs(dx) < 8) return;
      decided = true;
      if (dy <= 0 || Math.abs(dx) > Math.abs(dy) || !atTop()) { pulling = false; return; }   // geste horizontal ou vers le haut
      box.classList.remove("back");
    }
    if (dy <= 0) { dist = 0; render(); return; }
    e.preventDefault();                                            // bloque le rebond natif pendant le geste
    dist = Math.min(MAX, dy * RESIST);
    render();
  }

  function end() {
    if (!pulling) return;
    pulling = false;
    if (dist >= THRESHOLD) refresh(); else reset();
  }

  function init() {
    box = mount(); circle = box.querySelector(".ptr-c"); arc = box.querySelector(".ptr-arc"); svg = box.querySelector("svg");
    document.addEventListener("touchstart", start, { passive: true });
    document.addEventListener("touchmove", move, { passive: false });
    document.addEventListener("touchend", end, { passive: true });
    document.addEventListener("touchcancel", () => { if (pulling) { pulling = false; reset(); } }, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
