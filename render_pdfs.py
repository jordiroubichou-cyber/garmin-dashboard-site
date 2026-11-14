#!/usr/bin/env python3
"""Convertit le dashboard HTML en PDF avec Chromium (Playwright), période 1 semaine glissante :
 - dist/dashboard-complet-1S.pdf : le dashboard intégral, sur une seule page continue
 - dist/graphiques-essentiels-1S.pdf : captures des graphiques clés, mises en page dans un HTML converti en PDF
Désactivé par défaut (mails sans pièce jointe). Pour le réactiver : GD_PDF=1.
Usage : python render_pdfs.py [dist]"""
import base64, os, sys
from datetime import datetime
from pathlib import Path


MARGIN = {"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}


def main():
    if os.environ.get("GD_PDF") != "1":
        print("PDF désactivés (les mails n'ont plus de pièce jointe) : étape ignorée.")
        return
    from playwright.sync_api import sync_playwright      # importé seulement si les PDF sont réactivés
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
    src = dist / "dashboard.html"
    if not src.exists():
        raise SystemExit(f"dashboard.html introuvable dans {dist} : la génération du dashboard a échoué.")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1062, "height": 1400}, device_scale_factor=2, color_scheme="light")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(src.as_uri() + "?p=1S&print=1")
        page.wait_for_selector("body.ready", timeout=30000)
        page.wait_for_timeout(500)
        if errors:
            raise SystemExit("Erreur JavaScript dans le dashboard : " + errors[0])
        # 1) captures des graphiques essentiels
        shots = []
        for el in page.query_selector_all("[data-essential]"):
            shots.append((el.get_attribute("data-title") or "", base64.b64encode(el.screenshot(type="png")).decode()))
        # 2) dashboard complet : une seule page continue, fidèle à l'écran (pas de coupures au milieu des graphiques)
        page.emulate_media(media="screen")
        page.wait_for_timeout(200)
        height = page.evaluate("Math.ceil(document.documentElement.scrollHeight)")
        page.pdf(path=str(dist / "dashboard-complet-1S.pdf"), width="1062px", height=f"{height + 24}px", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}, page_ranges="1")
        # 3) graphiques essentiels : HTML mis en page puis converti en PDF
        today = datetime.now().strftime("%d/%m/%Y")
        figs = "".join(f'<figure><img src="data:image/png;base64,{b}"></figure>' for _, b in shots)
        html = f"""<!doctype html><meta charset="utf-8"><style>
        html{{background:#F5F5F7}}body{{margin:0;padding:26px;font-family:-apple-system,"SF Pro Text","Inter",Helvetica,Arial,sans-serif;color:#1D1D1F;background:#F5F5F7}}
        h1{{font-size:26px;letter-spacing:-.03em;margin:0}}p{{margin:2px 0 14px;color:#86868B;font-size:13px}}
        .g{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}figure{{margin:0;break-inside:avoid}}img{{width:100%;display:block;border-radius:14px}}
        </style><h1>Graphiques essentiels</h1><p>1 semaine glissante · {today}</p><div class="g">{figs}</div>"""
        page2 = ctx.new_page()
        page2.set_content(html)
        page2.wait_for_timeout(300)
        page2.pdf(path=str(dist / "graphiques-essentiels-1S.pdf"), format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    print(f"PDF générés ({len(shots)} graphiques essentiels).")
    # contrôle qualité : les masques de transparence (ombres floues exportées en images) s'affichent en rectangles gris sur iPhone
    for name in ("dashboard-complet-1S.pdf", "graphiques-essentiels-1S.pdf"):
        n = (dist / name).read_bytes().count(b"/SMask")
        print(f"  {name} : {'OK, sans masque de transparence' if n == 0 else f'ATTENTION, {n} masques de transparence'}")


if __name__ == "__main__":
    main()
