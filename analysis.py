"""Analyse des données d'entraînement : 100 % déterministe (aucune IA, aucun appel externe, bibliothèque standard).

Même date + mêmes données = exactement la même sortie.

Sections :
  1. Constantes et seuils ajustables (TH, W_STRAIN)
  2. Helpers
  3. Statistiques par période
  4. Prédictions de temps et allures cibles
  5. Piliers et note /20 (fenêtre de 28 jours, et par période 1S/1M/3M : pillars_period)
  6. Corrélations
  7. État physiologique : axes (VFC, sommeil, charge, stress/Body Battery, 3 derniers jours),
     indice de fatigue (strain_index), plafonds, facteur d'ajustement de forme (FAF), diagnostic, cas croisés
  8. Synthèses par période
  9. Entraînement du jour : choix de la discipline et de la séance, modulation par le FAF ;
     musculation = 30 séances Push/Pull/Legs (ppl_program.py), FAF propre à chaque type selon la veille
 10. Fonction principale build_analysis()

Les textes viennent de phrases_bank.py et les séances de sessions_library.py.

FORMULES (transparentes) :
  * Chaque axe produit un score de disponibilité c dans [0, 1] (1 = frais). Axes absents : ignorés, poids renormalisés.
  * ready = somme(poids x c) / somme(poids) avec W_STRAIN ; strain_index = round(100 x (1 - ready)).
  * FAF = clamp(0,5 + 0,65 x ready, 0,5, 1,15), puis plafonné par les règles de veto (VFC très basse, ACWR > 1,5, ...).
  * Sans données exploitables (moins de 2 axes) : profil données_insuffisantes et FAF par défaut prudent.
"""
import math
import re
from datetime import date, timedelta

import bilan_bank as BB
import petit_plus as PP_LIB
import phrases_bank as PB
import planner as PLN
import coach_memory as CM
import ppl_program as PPL
import sessions_library as SL

# =============================================================================================
# 1. CONSTANTES ET SEUILS AJUSTABLES
# =============================================================================================
SPORTS = ["run", "trail", "bike", "swim", "strength", "walk", "other"]
SPORT_FR = {"run": "Course", "trail": "Trail", "bike": "Vélo", "swim": "Natation",
            "strength": "Musculation", "walk": "Marche", "other": "Autre"}
PLAB = {"1S": "1 semaine glissante", "1M": "1 mois glissant", "3M": "3 mois glissants"}

TH = dict(
    acwr_low=0.8, acwr_mid=1.3, acwr_high=1.5,                      # zones du ratio aigu/chronique (7 j / 28 j)
    hrv_hi=1.03, hrv_lo=0.92, hrv_vlo=0.85, hrv_vlo_today=0.80,     # VFC / base : haute, basse, très basse
    sleep_poor_score=55, sleep_poor_h=5.5, sleep_target_h=7.5,      # sommeil
    sleep_debt_warn=1.5, sleep_debt_cap=3.0,                        # dette de sommeil sur 3 nuits (h)
    stress_high=60, bb_low=35, bb_vlow=25, bb_charge_low=40,        # stress moyen et Body Battery
    readiness_vlow=30, readiness_low=45,                            # score de readiness Garmin
    deep_low_pct=13, rem_low_pct=20,                                # repères du sommeil profond et du REM (% de la nuit)
    strain_acute=70, strain_incomplete=50, strain_fresh=30,         # seuils de l'indice de fatigue
    faf_min=0.5, faf_max=1.15, faf_default=0.85,                    # bornes du facteur d'ajustement de forme
    hard_share_high=30, hard_share_low=10,                          # part du temps de course en qualité sur 21 jours (%)
    long_gap_days=10, aero_vol_ratio_min=0.7,                       # déficit aérobie : sortie longue, volume / cible
)
W_STRAIN = {"hrv": 0.28, "sleep": 0.22, "load": 0.22, "sb": 0.14, "recent": 0.14}
FAF_BANDS = [(1.0, "haut", "Plein régime"), (0.85, "normal", "Normal"), (0.7, "prudent", "Prudent"), (0.0, "recup", "Récupération")]
FAM_LVL = {"recup": 1, "z2": 2, "aerobe": 3, "vo2": 5, "spec": 4, "trail": 3, "force": 3, "gainage": 2, "plyo": 3, "mobilite": 1, "long": 3, "taper": 2, "brick": 4}
DISC_FR = {"run": "Course à pied", "swim": "Natation", "bike": "Vélo", "strength": "Musculation"}


# =============================================================================================
# 1 bis. ROBUSTESSE : fraîcheur des données, recalage des seuils, fiabilité des prédictions, repères
# =============================================================================================
TH_DEFAULT = dict(TH)          # seuils d'origine : recalés sur ton historique à chaque génération (calibrate)

def pctl(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)

def calibrate(days, T):
    """Recale quelques seuils sur TON historique (percentiles personnels) quand il y a assez de données ; sinon valeurs par défaut.
    Les seuils sont remis à leurs valeurs d'origine avant chaque calcul : résultat déterministe."""
    TH.clear(); TH.update(TH_DEFAULT)
    info = {"calibrated": False, "lines": [], "n_hrv": 0, "n_sleep": 0}
    cl = lambda v, a, b: max(a, min(b, v))
    iso_T = T.isoformat()
    ds = sorted(d for d in days if d <= iso_T)
    hv = [(d, days[d].get("hrv")) for d in ds if days[d].get("hrv")]
    ratios = []
    for i, (d, v) in enumerate(hv):
        prev = [x for dd, x in hv[:i] if (date.fromisoformat(d) - date.fromisoformat(dd)).days <= 60]
        if len(prev) >= 14: ratios.append(v / mean(prev))
    info["n_hrv"] = len(ratios)
    if len(ratios) >= 25:
        lo_ = cl(round(pctl(ratios, 0.15), 2), 0.88, 0.95)
        TH["hrv_lo"] = lo_
        TH["hrv_vlo"] = cl(round(pctl(ratios, 0.05), 2), 0.80, min(0.88, lo_ - 0.03))
        TH["hrv_hi"] = cl(round(pctl(ratios, 0.80), 2), 1.02, 1.08)
        info["lines"].append(f"VFC « basse » sous {TH['hrv_lo'] * 100:.0f} % de ta base (réglage d'origine : {TH_DEFAULT['hrv_lo'] * 100:.0f} %), « haute » au-dessus de {TH['hrv_hi'] * 100:.0f} %")
    sc = [days[d]["sc"] for d in ds if days[d].get("sc")]
    info["n_sleep"] = len(sc)
    if len(sc) >= 25:
        TH["sleep_poor_score"] = int(cl(round(pctl(sc, 0.15)), 50, 65))
        info["lines"].append(f"Sommeil « mauvais » sous {TH['sleep_poor_score']}/100 (d'origine : {TH_DEFAULT['sleep_poor_score']})")
    stv = [days[d]["st"] for d in ds if days[d].get("st")]
    if len(stv) >= 25:
        TH["stress_high"] = int(cl(round(pctl(stv, 0.85)), 45, 65))
        info["lines"].append(f"Stress « élevé » au-dessus de {TH['stress_high']} (d'origine : {TH_DEFAULT['stress_high']})")
    tr = [days[d]["tr"] for d in ds if days[d].get("tr")]
    if len(tr) >= 25:
        TH["readiness_low"] = int(cl(round(pctl(tr, 0.20)), 35, 55)); TH["readiness_vlow"] = max(20, TH["readiness_low"] - 15)
        info["lines"].append(f"Readiness « basse » sous {TH['readiness_low']} (d'origine : {TH_DEFAULT['readiness_low']})")
    info["calibrated"] = bool(info["lines"])
    return info

def data_freshness(acts, days, T, meta=None):
    """Âge des dernières données (récupération, activités) et état de la dernière synchronisation."""
    meta = meta or {}
    wd = [d for d, v in days.items() if any(v.get(k) is not None for k in ("hrv", "sc", "rhr", "bbx", "st", "tr")) and d <= T.isoformat()]
    lw = max(wd) if wd else None
    la = max((x["d"] for x in acts if x["d"] <= T.isoformat()), default=None)
    age_w = None if lw is None else max(0, (T - date.fromisoformat(lw)).days)
    age_a = None if la is None else max(0, (T - date.fromisoformat(la)).days)
    sync_age = None
    if meta.get("synced_at"):
        try: sync_age = max(0, (T - date.fromisoformat(str(meta["synced_at"])[:10])).days)
        except ValueError: sync_age = None
    sync_ok = meta.get("ok", True) is not False
    level = None
    if age_w is None or age_w >= 4 or (sync_age is not None and sync_age >= 4): level = "alert"
    elif age_w >= 2 or (sync_age is not None and sync_age >= 2) or not sync_ok: level = "warn"
    msg = None
    if level:
        bits = []
        if age_w is None: bits.append("aucune donnée de récupération (sommeil, VFC…) n'a été trouvée")
        elif age_w >= 2: bits.append(f"dernières données de récupération : {date.fromisoformat(lw).strftime('%d/%m/%Y')} ({age_w} jours)")
        if sync_age is not None and sync_age >= 2: bits.append(f"dernière synchronisation Garmin réussie il y a {sync_age} jours")
        if not sync_ok: bits.append("la dernière synchronisation était incomplète" + (f" ({meta['reason']})" if meta.get("reason") else "") + " : les données précédentes ont été conservées")
        msg = "Attention, données datées : " + " · ".join(bits) + ". Les analyses ci-dessous peuvent être en retard sur la réalité."
    return {"level": level, "message": msg, "last_wellness": lw, "age_wellness": age_w, "last_activity": la, "age_activity": age_a,
            "sync_age": sync_age, "sync_ok": sync_ok}

RACE_RE = re.compile(r"course|race|corrida|\b10 ?k\b|semi|marathon|dossard|compet|trail", re.I)

def prediction_check(acts, T, goals):
    """Compare ce que la prédiction annonçait la veille d'une course (10 km, semi, marathon) au temps réellement couru."""
    iso_T = T.isoformat()
    a_sorted = sorted(acts, key=lambda x: x["d"])
    first = a_sorted[0]["d"] if a_sorted else iso_T
    items = []
    for x in a_sorted:
        if x["s"] != "run" or x["d"] >= iso_T or not (x["m"] > 0 and x["km"] > 0): continue
        for key, label, D, dmin, dmax in DISTS:
            if abs(x["km"] - D) / D > 0.04: continue
            if not (RACE_RE.search(x["nm"] or "") or (x["te"] or 0) >= 4.0): continue
            prior = [a for a in a_sorted if a["d"] < x["d"]]
            if len(prior) < 8 or (date.fromisoformat(x["d"]) - date.fromisoformat(first)).days < 42: continue
            vo2 = next((a["vo2"] for a in reversed(prior) if a["vo2"]), None)
            pr = next((r for r in predictions(prior, date.fromisoformat(x["d"]) - timedelta(days=1), goals, vo2) if r["key"] == key), None)
            if not pr or not pr["ret"]: continue
            actual = x["m"] * 60 * (D / x["km"]) ** 1.06          # ramené à la distance exacte
            items.append({"date": x["d"], "label": label, "name": x["nm"] or label, "actual": actual, "pred": pr["ret"],
                          "err": (actual - pr["ret"]) / pr["ret"] * 100})
            break
    items = items[-6:]
    if not items:
        return {"n": 0, "bias": None, "items": [], "note": "Aucune course de référence détectée (10 km, semi ou marathon couru à fond, nommé « course »/« semi »… ou à effet d'entraînement ≥ 4)."}
    bias = sum(i["err"] for i in items) / len(items)
    verdict = ("bien calibrées" if abs(bias) < 1.5 else f"trop optimistes de {abs(bias):.1f} % en moyenne" if bias > 0 else f"trop prudentes de {abs(bias):.1f} % en moyenne").replace(".", ",")
    return {"n": len(items), "bias": bias, "items": items, "note": f"Sur {len(items)} course(s) de référence, les prédictions de la veille étaient {verdict}."}

def build_events(cfg_events, pcheck, T):
    """Repères affichés sur les graphiques : événements de config.py (vacances, blessure…) + courses détectées."""
    out = []
    for e in (cfg_events or []):
        try:
            d = date.fromisoformat(str(e["date"])[:10])
        except (KeyError, ValueError, TypeError):
            continue
        if (T - d).days < 0 or (T - d).days > 400: continue
        out.append({"date": d.isoformat(), "label": str(e.get("label", "Repère"))[:24], "kind": e.get("kind", "autre")})
    for i in (pcheck or {}).get("items", []):
        if (T - date.fromisoformat(i["date"])).days <= 400:
            out.append({"date": i["date"], "label": f"Course {i['label']}", "kind": "course"})
    return sorted(out, key=lambda e: e["date"])


# =============================================================================================
# 2. HELPERS
# =============================================================================================
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None

def f1(x, n=1): return f"{x:.{n}f}".replace(".", ",")

def hms(s):
    s = int(round(s)); h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{h}h{m:02d}'{sec:02d}" if h else f"{m}'{sec:02d}"

def pace(p):
    """allure en min/km (float) -> 4'12"""
    if not p: return "–"
    m = int(p); s = int(round((p - m) * 60))
    if s == 60: m, s = m + 1, 0
    return f"{m}'{s:02d}"

def pct(a, b): return None if not b else (a - b) / b * 100

def sgn(v, n=0): return "" if v is None else f"{v:+.{n}f} %".replace(".", ",")

def wavg(parts):
    """parts = [(poids, valeur|None)] -> moyenne pondérée des valeurs disponibles"""
    p = [(w, v) for w, v in parts if v is not None]
    return sum(w * v for w, v in p) / sum(w for w, _ in p) if p else None

def slope(pts):
    """pente de la régression linéaire (x, y)"""
    n = len(pts)
    if n < 3: return None
    mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx else None

def _series(days, T, key, n, off=0):
    """valeurs de `key` sur n jours se terminant à T - off (du plus ancien au plus récent), None si absent"""
    return [days.get((T - timedelta(days=off + i)).isoformat(), {}).get(key) for i in range(n - 1, -1, -1)]

def _last(days, T, key, back=3):
    for i in range(back):
        v = days.get((T - timedelta(days=i)).isoformat(), {}).get(key)
        if v is not None: return v
    return None


# =============================================================================================
# 3. STATISTIQUES PAR PÉRIODE
# =============================================================================================
def acwr(acts, d_end):
    """Ratio de charge aiguë (7 j) / chronique (28 j). None si l'historique ne couvre pas 28 jours (ratio non fiable)."""
    T = date.fromisoformat(d_end)
    if not acts or (T - date.fromisoformat(min(a["d"] for a in acts))).days < 27: return None
    dl = {}
    for a in acts: dl[a["d"]] = dl.get(a["d"], 0) + a["ld"]
    day = lambda i: (T - timedelta(days=i)).isoformat()
    s7 = sum(dl.get(day(i), 0) for i in range(7)); s28 = sum(dl.get(day(i), 0) for i in range(28))
    return (s7 / 7) / (s28 / 28) if s28 > 0 else None

def rec_mean(days, T, n, key, off=0):
    return mean(_series(days, T, key, n, off))

REC_KEYS = ("sc", "sh", "hrv", "rhr", "bbx", "bbn", "tr", "st", "stp", "deep", "rem")

def period_stats(acts, days, T, n, off=0):
    a = (T - timedelta(days=off + n - 1)).isoformat(); b = (T - timedelta(days=off)).isoformat()
    L = [x for x in acts if a <= x["d"] <= b]
    S = {"n": len(L), "h": sum(x["m"] for x in L) / 60, "ld": sum(x["ld"] for x in L), "sp": {}}
    for s in SPORTS:
        Ls = [x for x in L if x["s"] == s]
        S["sp"][s] = {"n": len(Ls), "h": sum(x["m"] for x in Ls) / 60, "km": sum(x["km"] for x in Ls),
                      "el": sum(x["el"] for x in Ls), "ld": sum(x["ld"] for x in Ls),
                      "pw": mean([x["pw"] for x in Ls if x["pw"]])}
    runs = [x for x in L if x["s"] in ("run", "trail")]
    km = sum(x["km"] for x in runs); mn = sum(x["m"] for x in runs)
    efr = [x for x in runs if x["s"] == "run" and x["hr"] and x["km"] >= 3 and x["m"] > 0]
    hrr = [x for x in runs if x["hr"] and x["m"] > 0]
    S["run"] = {"n": len(runs), "km": km, "h": mn / 60, "pace": (mn / km if km else None),
                "el": sum(x["el"] for x in runs), "longest": max([x["km"] for x in runs] or [0]),
                "hr": (sum(x["hr"] * x["m"] for x in hrr) / sum(x["m"] for x in hrr)) if hrr else None,
                "ef": (sum(x["km"] * 1000 for x in efr) / sum(x["hr"] * x["m"] for x in efr)) if efr else None,
                "ld": sum(x["ld"] for x in runs)}
    S["rec"] = {k: rec_mean(days, T, n, k, off) for k in REC_KEYS}
    S["acwr"] = acwr(acts, b)
    return S


# =============================================================================================
# 4. PRÉDICTIONS ET ALLURES CIBLES
# =============================================================================================
def daniels_time(vdot, D_km):
    """Temps (s) pour une distance donnée à partir d'une VO2max (équations de Daniels)."""
    D = D_km * 1000
    def f(t):
        v = D / t
        vo2 = -4.60 + 0.182258 * v + 0.000104 * v * v
        pc = 0.8 + 0.1894393 * math.exp(-0.012778 * t) + 0.2989558 * math.exp(-0.1932605 * t)
        return vo2 / pc - vdot
    lo, hi = 5.0, 900.0
    if f(lo) < 0 or f(hi) > 0: return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2 * 60

DISTS = [("10k", "10 km", 10.0, 5, 25), ("semi", "Semi-marathon", 21.0975, 8, 30), ("marathon", "Marathon", 42.195, 10, 35)]

def predictions(acts, T, goals, vo2, span=None):
    goals = [g for g in goals if g.get("sport", "run") == "run"]      # seuls les objectifs de course à pied fixent un temps cible
    """Riegel (exposant 1,06) sur les meilleures sorties route récentes + Daniels sur la VO2max ; temps retenu = moyenne."""
    iso = lambda n: (T - timedelta(days=n)).isoformat()
    road = [x for x in acts if x["s"] == "run" and x["m"] > 0 and x["km"] > 0]
    out = []
    for key, label, D, dmin, dmax in DISTS:
        since = iso((span - 1) if span else (83 if key == "10k" else 119))      # span : fenêtre de la période (note par période)
        c = [(x["m"] * 60 * (D / x["km"]) ** 1.06, x) for x in road if dmin <= x["km"] <= dmax and x["d"] >= since]
        rg, src = min(c, key=lambda t: t[0]) if c else (None, None)
        dn = daniels_time(vo2, D) if vo2 else None
        ret = mean([v for v in (rg, dn) if v])
        tgt = next((g["target_s"] for g in goals if abs(g["dist"] - D) < 0.5 and g["target_s"]), None)
        out.append({"key": key, "label": label, "dist": D, "riegel": rg, "daniels": dn, "ret": ret, "target": tgt,
                    "gap": (ret - tgt) if (ret and tgt) else None,
                    "src": (f"{src['nm'] or 'sortie'} · {src['d'][8:]}/{src['d'][5:7]} · {f1(src['km'])} km" if src else None)})
    return out

def zones(preds, goals):
    goals = [g for g in goals if g.get("sport", "run") == "run"]
    """Allures cibles dérivées des objectifs (sinon des prédictions)."""
    def p_of(key):
        g = next((x for x in goals if x["id"] == key and x["target_s"]), None)
        if g: return g["target_s"] / 60 / g["dist"]
        r = next((x for x in preds if x["key"] == key), None)
        return (r["ret"] / 60 / r["dist"]) if r and r["ret"] else None
    p10, pm = p_of("10k"), p_of("marathon")
    if not (p10 or pm): return None
    if not p10: p10 = pm * (10 / 42.195) ** -0.06
    if not pm: pm = p10 * (42.195 / 10) ** 0.06
    semi = p10 * (21.0975 / 10) ** 0.06
    return {"p10": p10, "semi": semi, "mar": pm, "easy": (pm + 50 / 60, pm + 80 / 60), "vma": p10 - 12 / 60,
            "list": [
                {"n": "Endurance fondamentale", "p": f"{pace(pm + 50 / 60)}–{pace(pm + 80 / 60)}", "u": "footings, récupération, volume"},
                {"n": "Allure marathon", "p": pace(pm), "u": "blocs spécifiques marathon"},
                {"n": "Seuil / semi-marathon", "p": pace(semi), "u": "tempo, 3 × 10'"},
                {"n": "Allure 10 km", "p": pace(p10), "u": "séances spécifiques 10 km"},
                {"n": "VMA / intervalles courts", "p": pace(p10 - 12 / 60), "u": "200–600 m, 30/30"}]}


# =============================================================================================
# 5. PILIERS ET NOTE /20
# =============================================================================================
def score_label(v):
    return "Excellent" if v >= 17 else "Très bon" if v >= 14 else "Solide" if v >= 11 else "À consolider" if v >= 8 else "À reconstruire"

def sleep_comp(sc, sh, deep_pct, rem_pct):
    """Disponibilité liée au sommeil, 0..1 : score (55 %), durée (30 %), phases profond/REM (15 %)."""
    stages = mean([clamp(deep_pct / TH["deep_low_pct"]) if deep_pct is not None else None,
                   clamp(rem_pct / TH["rem_low_pct"]) if rem_pct is not None else None])
    return wavg([(0.55, clamp((sc - 50) / 40) if sc is not None else None),
                 (0.30, clamp((sh - 5.5) / 2.5) if sh else None), (0.15, stages)])

def stage_pcts(deep, rem, sh):
    if not sh: return None, None
    return (deep / (sh * 60) * 100 if deep else None), (rem / (sh * 60) * 100 if rem else None)

def pillars(acts, days, T, goals, ath, preds, vo2):
    iso = lambda n: (T - timedelta(days=n)).isoformat()
    S28 = period_stats(acts, days, T, 28)
    runs = [x for x in acts if x["s"] in ("run", "trail")]
    P = []
    ps, lines = [], []
    for r in preds:
        if r["target"] and r["ret"]:
            ratio = r["ret"] / r["target"]
            ps.append(clamp(1 - (ratio - 1) / 0.2))
            lines.append(f"{r['label']} : {hms(r['ret'])} prédit pour {hms(r['target'])} visé ({(ratio - 1) * 100:+.1f} %)".replace(".", ","))
    P.append({"key": "pred", "name": "Prédictions de performance", "score": 4 * mean(ps) if ps else None,
              "lines": lines or ["Pas assez de sorties récentes pour prédire un temps"]})
    km4 = S28["run"]["km"] / 4
    reg = sum(1 for i in range(4) if len([x for x in runs if iso(7 * i + 6) <= x["d"] <= iso(7 * i)]) >= 3) / 4
    long6 = max([x["km"] for x in runs if x["d"] >= iso(41)] or [0])
    sc = wavg([(.35, clamp(km4 / ath["weekly_km_target"])), (.2, reg), (.25, clamp(long6 / ath["long_run_target_km"])),
               (.2, clamp((vo2 - 45) / 12) if vo2 else None)])
    est = " · ".join(f"{r['label'].replace('Semi-marathon', 'Semi')} {hms(r['ret'])}" for r in preds if r["ret"])
    P.append({"key": "run", "name": "Performances en course à pied", "score": None if sc is None else 4 * sc,
              "lines": [f"Volume : {f1(km4)} km/sem sur 4 semaines (cible {ath['weekly_km_target']})",
                        f"Régularité : {int(reg * 4)}/4 semaines avec au moins 3 sorties",
                        f"Sortie longue max (6 sem.) : {f1(long6)} km (cible {ath['long_run_target_km']})",
                        f"VO2max : {vo2:.0f}" if vo2 else "VO2max : n/a", f"Temps estimés : {est}" if est else "Temps estimés : n/a"]})
    ac = S28["acwr"]
    acs = None if ac is None else clamp(1 if TH["acwr_low"] <= ac <= TH["acwr_mid"] else (ac - 0.5) / 0.3 if ac < TH["acwr_low"] else (1.8 - ac) / 0.5)
    wl = [sum(x["ld"] for x in acts if iso(7 * i + 6) <= x["d"] <= iso(7 * i)) for i in range(4)]
    m = mean(wl); cv = (math.sqrt(sum((v - m) ** 2 for v in wl) / 4) / m) if m else None
    lsc = wavg([(.7, acs), (.3, clamp(1 - cv / 0.4) if cv is not None else None)])
    P.append({"key": "load", "name": "Charge d'entraînement", "score": None if lsc is None else 4 * lsc,
              "lines": [f"Ratio aigu/chronique : {f1(ac, 2)} (zone idéale 0,8–1,3)" if ac else "Ratio aigu/chronique : n/a",
                        f"Charge des 4 dernières semaines : {', '.join(f'{v:.0f}' for v in wl[::-1])}",
                        f"Régularité de la charge : {'n/a' if cv is None else f'variation {cv * 100:.0f} %'}"]})
    r14 = period_stats(acts, days, T, 14)["rec"]
    hb = rec_mean(days, T, 60, "hrv", 14); rb = rec_mean(days, T, 60, "rhr", 14)
    hrvr = r14["hrv"] / hb if r14["hrv"] and hb else None
    rhrd = r14["rhr"] - rb if r14["rhr"] is not None and rb is not None else None
    dp, rp = stage_pcts(r14["deep"], r14["rem"], r14["sh"])
    slp = sleep_comp(r14["sc"], r14["sh"], dp, rp)
    rs = wavg([(1, slp), (1, clamp((hrvr - 0.85) / 0.15) if hrvr else None), (1, clamp(1 - rhrd / 6) if rhrd is not None else None),
               (1, clamp((r14["bbx"] - 50) / 40) if r14["bbx"] else None), (1, clamp((r14["tr"] - 30) / 50) if r14["tr"] else None)])
    rl = [f"Sommeil : {r14['sc']:.0f}/100, {f1(r14['sh'])} h" if r14["sc"] is not None and r14["sh"] else "Sommeil : n/a"]
    if dp is not None and rp is not None: rl.append(f"Phases : profond {dp:.0f} % · REM {rp:.0f} % de la nuit")
    rl += [f"VFC : {r14['hrv']:.0f} ms ({(hrvr - 1) * 100:+.0f} % vs base 60 j)" if hrvr else "VFC : n/a",
           f"FC repos : {r14['rhr']:.0f} bpm ({'stable' if abs(rhrd) < 0.5 else f'{rhrd:+.1f}'.replace('.', ',')} vs base)" if rhrd is not None else "FC repos : n/a",
           f"Body Battery max : {r14['bbx']:.0f} · Readiness : {r14['tr']:.0f}" if r14["bbx"] and r14["tr"] else "Body Battery / Readiness : n/a"]
    P.append({"key": "rec", "name": "Récupération et état physique", "score": None if rs is None else 4 * rs, "lines": rl})
    sw = S28["sp"]["strength"]["n"] / 4; cw = (S28["sp"]["bike"]["n"] + S28["sp"]["swim"]["n"]) / 4
    div = sum(1 for s in ("run", "bike", "swim", "strength") if S28["sp"][s]["n"] > 0 or (s == "run" and S28["sp"]["trail"]["n"] > 0)) / 4
    P.append({"key": "cross", "name": "Musculation, multisport et cross-training",
              "score": 4 * (.4 * clamp(sw / ath["strength_per_week"]) + .4 * clamp(cw / ath["cross_per_week"]) + .2 * div),
              "lines": [f"Musculation : {f1(sw)} séance(s)/sem (cible {ath['strength_per_week']})",
                        f"Vélo + natation : {f1(cw)} séance(s)/sem (cible {f1(ath['cross_per_week'])})",
                        f"Disciplines pratiquées sur 28 jours : {int(div * 4)}/4"]})
    ctx = {"km4": km4, "reg": reg, "long6": long6, "acwr": ac, "hrvr": hrvr, "rhrd": rhrd, "r14": r14}
    return P, ctx

def pillars_period(acts, days, T, goals, ath, vo2_all, n):
    """Mêmes 5 piliers, calculés sur une période glissante de n jours (7, 30 ou 90) : la note /20 évolue avec la période.
    Volume et sorties/semaine ramenés à la semaine, ratio de charge moyenné sur la période, base VFC/FC repos = 60 jours AVANT la période."""
    iso = lambda k: (T - timedelta(days=k)).isoformat()
    S = period_stats(acts, days, T, n)
    W, nb = n / 7.0, max(1, min(12, n // 7))
    win = [x for x in acts if iso(n - 1) <= x["d"] <= iso(0)]
    runs = [x for x in win if x["s"] in ("run", "trail")]
    vo2 = next((x["vo2"] for x in reversed(win) if x["vo2"]), None) or vo2_all
    preds = predictions(acts, T, goals, vo2, span=n)
    P, ps, lines = [], [], []
    for r in preds:
        if r["target"] and r["ret"]:
            ratio = r["ret"] / r["target"]
            ps.append(clamp(1 - (ratio - 1) / 0.2))
            lines.append(f"{r['label']} : {hms(r['ret'])} prédit pour {hms(r['target'])} visé ({(ratio - 1) * 100:+.1f} %)".replace(".", ","))
    P.append({"key": "pred", "name": "Prédictions de performance", "score": 4 * mean(ps) if ps else None,
              "lines": lines or ["Pas assez de sorties récentes pour prédire un temps"]})
    kmw = S["run"]["km"] / W
    reg = sum(1 for i in range(nb) if len([x for x in runs if iso(7 * i + 6) <= x["d"] <= iso(7 * i)]) >= 3) / nb
    long_ = max([x["km"] for x in runs] or [0])
    sc = wavg([(.35, clamp(kmw / ath["weekly_km_target"])), (.2, reg), (.25, clamp(long_ / ath["long_run_target_km"])),
               (.2, clamp((vo2 - 45) / 12) if vo2 else None)])
    est = " · ".join(f"{r['label'].replace('Semi-marathon', 'Semi')} {hms(r['ret'])}" for r in preds if r["ret"])
    P.append({"key": "run", "name": "Performances en course à pied", "score": None if sc is None else 4 * sc,
              "lines": [f"Volume : {f1(kmw)} km/sem sur la période (cible {ath['weekly_km_target']})",
                        f"Régularité : {int(round(reg * nb))}/{nb} semaine(s) avec au moins 3 sorties",
                        f"Sortie la plus longue : {f1(long_)} km (cible {ath['long_run_target_km']})",
                        f"VO2max : {vo2:.0f}" if vo2 else "VO2max : n/a", f"Temps estimés : {est}" if est else "Temps estimés : n/a"]})
    step = 1 if n <= 30 else 3
    acs_l = []
    for k in range(0, n, step):
        a_ = acwr(acts, iso(k))
        if a_ is not None: acs_l.append((a_, clamp(1 if TH["acwr_low"] <= a_ <= TH["acwr_mid"] else (a_ - 0.5) / 0.3 if a_ < TH["acwr_low"] else (1.8 - a_) / 0.5)))
    ac = mean([a for a, _ in acs_l]); acs = mean([c for _, c in acs_l])
    wl = [sum(x["ld"] for x in acts if iso(7 * i + 6) <= x["d"] <= iso(7 * i)) for i in range(nb)]
    m = mean(wl); cv = (math.sqrt(sum((v - m) ** 2 for v in wl) / len(wl)) / m) if (m and len(wl) >= 2) else None
    lsc = wavg([(.7, acs), (.3, clamp(1 - cv / 0.4) if cv is not None else None)])
    P.append({"key": "load", "name": "Charge d'entraînement", "score": None if lsc is None else 4 * lsc,
              "lines": [f"Ratio aigu/chronique moyen : {f1(ac, 2)} (zone idéale 0,8–1,3)" if ac else "Ratio aigu/chronique : n/a (historique insuffisant)",
                        f"Charge par semaine ({len(wl)} dernière(s)) : {', '.join(f'{v:.0f}' for v in wl[::-1])}",
                        f"Régularité de la charge : {'n/a' if cv is None else f'variation {cv * 100:.0f} %'}"]})
    r_ = S["rec"]
    hb = rec_mean(days, T, 60, "hrv", n) or rec_mean(days, T, max(60, n), "hrv")
    rb = rec_mean(days, T, 60, "rhr", n) or rec_mean(days, T, max(60, n), "rhr")
    hrvr = r_["hrv"] / hb if r_["hrv"] and hb else None
    rhrd = r_["rhr"] - rb if r_["rhr"] is not None and rb is not None else None
    dp, rp = stage_pcts(r_["deep"], r_["rem"], r_["sh"])
    slp = sleep_comp(r_["sc"], r_["sh"], dp, rp)
    rs = wavg([(1, slp), (1, clamp((hrvr - 0.85) / 0.15) if hrvr else None), (1, clamp(1 - rhrd / 6) if rhrd is not None else None),
               (1, clamp((r_["bbx"] - 50) / 40) if r_["bbx"] else None), (1, clamp((r_["tr"] - 30) / 50) if r_["tr"] else None)])
    rl = [f"Sommeil : {r_['sc']:.0f}/100, {f1(r_['sh'])} h" if r_["sc"] is not None and r_["sh"] else "Sommeil : n/a"]
    if dp is not None and rp is not None: rl.append(f"Phases : profond {dp:.0f} % · REM {rp:.0f} % de la nuit")
    rl += [f"VFC : {r_['hrv']:.0f} ms ({(hrvr - 1) * 100:+.0f} % vs base 60 j)" if hrvr else "VFC : n/a",
           f"FC repos : {r_['rhr']:.0f} bpm ({'stable' if abs(rhrd) < 0.5 else f'{rhrd:+.1f}'.replace('.', ',')} vs base)" if rhrd is not None else "FC repos : n/a",
           f"Body Battery max : {r_['bbx']:.0f} · Readiness : {r_['tr']:.0f}" if r_["bbx"] and r_["tr"] else "Body Battery / Readiness : n/a"]
    P.append({"key": "rec", "name": "Récupération et état physique", "score": None if rs is None else 4 * rs, "lines": rl})
    sw = S["sp"]["strength"]["n"] / W; cw = (S["sp"]["bike"]["n"] + S["sp"]["swim"]["n"]) / W
    div = sum(1 for s_ in ("run", "bike", "swim", "strength") if S["sp"][s_]["n"] > 0 or (s_ == "run" and S["sp"]["trail"]["n"] > 0)) / 4
    P.append({"key": "cross", "name": "Musculation, multisport et cross-training",
              "score": 4 * (.4 * clamp(sw / ath["strength_per_week"]) + .4 * clamp(cw / ath["cross_per_week"]) + .2 * div),
              "lines": [f"Musculation : {f1(sw)} séance(s)/sem (cible {ath['strength_per_week']})",
                        f"Vélo + natation : {f1(cw)} séance(s)/sem (cible {f1(ath['cross_per_week'])})",
                        f"Disciplines pratiquées sur la période : {int(div * 4)}/4"]})
    ok = [p["score"] for p in P if p["score"] is not None]
    total = sum(ok) / (4 * len(ok)) * 20 if ok else None
    return {"score": total, "label": score_label(total) if total is not None else "", "pillars": P,
            "acwr_mean": ac, "hrvr": hrvr, "rhrd": rhrd, "preds": preds}      # valeurs de la période, réutilisées par synthesis()


# =============================================================================================
# 6. CORRÉLATIONS
# =============================================================================================
def pearson(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pts)
    if n < 10: return None, n
    mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    if sxx == 0 or syy == 0: return None, n
    return sxy / math.sqrt(sxx * syy), n

def correlations(acts, days, T):
    ds = [(T - timedelta(days=i)).isoformat() for i in range(89, -1, -1)]
    dl = {}
    for a in acts: dl[a["d"]] = dl.get(a["d"], 0) + a["ld"]
    prev = lambda d, k=1: (date.fromisoformat(d) - timedelta(days=k)).isoformat()
    g = lambda d, k: days.get(d, {}).get(k)
    load1 = lambda d: dl.get(prev(d), 0) if (prev(d) in dl or d in days) else None
    load3 = lambda d: sum(dl.get(prev(d, k), 0) for k in (1, 2, 3))
    defs = [("Charge de la veille", "VFC de la nuit", [load1(d) for d in ds], [g(d, "hrv") for d in ds], "neg",
             "la VFC baisse après les grosses journées d'entraînement", "la VFC ne baisse pas après les grosses journées : bonne tolérance à la charge"),
            ("Charge de la veille", "score de sommeil", [load1(d) for d in ds], [g(d, "sc") for d in ds], "neg",
             "le sommeil se dégrade après les grosses charges", "le sommeil résiste aux grosses charges"),
            ("Charge des 3 derniers jours", "readiness", [load3(d) for d in ds], [g(d, "tr") for d in ds], "neg",
             "la readiness baisse quand la charge s'accumule", "la readiness reste stable malgré la charge"),
            ("Score de sommeil", "readiness du lendemain", [g(prev(d), "sc") for d in ds], [g(d, "tr") for d in ds], "pos",
             "une bonne nuit se traduit par une meilleure readiness le lendemain", "la readiness dépend peu du sommeil de la veille"),
            ("Sommeil profond", "VFC de la nuit", [g(d, "deep") for d in ds], [g(d, "hrv") for d in ds], "pos",
             "plus de sommeil profond va avec une VFC plus haute", "la VFC dépend peu du sommeil profond"),
            ("Stress moyen de la veille", "VFC de la nuit", [g(prev(d), "st") for d in ds], [g(d, "hrv") for d in ds], "neg",
             "un stress élevé la veille réduit la VFC", "le stress de la veille pèse peu sur la VFC")]
    out = []
    for a, b, xs, ys, sign, txt_hit, txt_no in defs:
        r, n = pearson(xs, ys)
        if r is None: continue
        strength = "net" if abs(r) >= 0.5 else "modéré" if abs(r) >= 0.3 else "faible"
        expected = (r < 0) if sign == "neg" else (r > 0)
        rs = f"{r:.2f}".replace(".", ",")
        out.append({"a": a, "b": b, "r": round(r, 2), "n": n, "strength": strength,
                    "text": (f"{txt_hit} (lien {strength}, r = {rs}, {n} jours)." if abs(r) >= 0.3 and expected
                             else f"{txt_no} (lien {strength}, r = {rs}, {n} jours)." if abs(r) < 0.3
                             else f"relation inattendue entre {a.lower()} et {b} (r = {rs}, {n} jours) : à surveiller.")})
    return out


# =============================================================================================
# 7. ÉTAT PHYSIOLOGIQUE : axes, strain_index, FAF, diagnostic, cas croisés
# =============================================================================================
ANA_RE = re.compile(r"vma|vo2|30\s*/\s*30|\b\d+\s*x\s*(100|150|200|300|400|500|600)\s*m?\b|\b\d+\s*x\s*\d+\s*['’]", re.I)
PCT_VMA_RE = re.compile(r"\d+\s*%\s*vma", re.I)
TEMPO_RE = re.compile(r"tempo|seuil|\d+\s*x\s*\d{4}|allure|progressi|pyramid|\d+\s*x\s*\d+\s*km|côte|cote", re.I)
LEGS_RE = re.compile(r"jambe|leg|squat|cuisse|fessier|mollet", re.I)

def run_kind(x):
    """easy / long / tempo / ana, d'après le nom de la séance, le Training Effect et la distance."""
    nm = x.get("nm") or ""
    if PCT_VMA_RE.search(nm): return "tempo"
    if ANA_RE.search(nm): return "ana"
    if TEMPO_RE.search(nm) or (x.get("te") and x["te"] >= 4.0 and x["km"] < 16): return "tempo"
    if x["km"] >= 16: return "long"
    return "easy"

def intensity(a):
    """facile / modéré / dur pour une séance (toutes disciplines)."""
    k = run_kind(a) if a["s"] in ("run", "trail") else None
    if (a.get("te") or 0) >= 3.5 or a["ld"] >= 150 or k in ("ana", "tempo") or (k == "long" and a["km"] >= 20): return "dur"
    if a["ld"] >= 70 or (a.get("te") or 0) >= 2.5: return "modéré"
    return "facile"

def leg_stress(a):
    """séance qui sollicite fortement les jambes (impact ou charge musculaire)"""
    if a["s"] in ("run", "trail"): return run_kind(a) != "easy" or a["km"] >= 12
    if a["s"] == "bike": return a["ld"] >= 120
    if a["s"] == "strength": return bool(LEGS_RE.search(a.get("nm") or ""))
    return False

def hrv_axis(days, T):
    """VFC du jour vs base (moyenne des jours T-66 à T-7), tendance sur 7 jours et pente."""
    cur = _last(days, T, "hrv", 2)
    base_vals = [v for v in _series(days, T, "hrv", 60, off=7) if v is not None]
    base = mean(base_vals) if len(base_vals) >= 6 else None
    s7 = _series(days, T, "hrv", 7)
    last7 = [v for v in s7 if v is not None]
    m7 = mean(last7)
    r7 = m7 / base if (m7 and base) else None
    rt = cur / base if (cur and base) else None
    pts = [(i, v) for i, v in enumerate(s7) if v is not None]
    sl = slope(pts) if len(pts) >= 4 and base else None
    state = None
    if r7 is not None or rt is not None:
        x = r7 if r7 is not None else rt
        state = ("très_basse" if (x <= TH["hrv_vlo"] or (rt is not None and rt <= TH["hrv_vlo_today"])) else
                 "basse" if x <= TH["hrv_lo"] else "haute" if x >= TH["hrv_hi"] else "stable")
    comp = None
    if r7 is not None or rt is not None:
        parts = [(0.6, r7 - 1 if r7 is not None else None), (0.4, rt - 1 if rt is not None else None)]
        comp = clamp(0.65 + wavg(parts) * 3.5)
    return {"val": cur, "base": base, "r7": r7, "rt": rt, "slope_pct_day": (sl / base * 100) if (sl is not None and base) else None, "state": state, "comp": comp}

def sleep_axis(days, T):
    sc = _last(days, T, "sc", 2); sh = _last(days, T, "sh", 2)
    deep = _last(days, T, "deep", 2); rem = _last(days, T, "rem", 2)
    dp, rp = stage_pcts(deep, rem, sh)
    sh3 = [v for v in _series(days, T, "sh", 3) if v is not None]
    debt = sum(max(0.0, TH["sleep_target_h"] - v) for v in sh3) if sh3 else None
    return {"score": sc, "h": sh, "deep": deep, "rem": rem, "deep_pct": dp, "rem_pct": rp, "debt": debt, "comp": sleep_comp(sc, sh, dp, rp)}

def load_axis(acts, T):
    ac = acwr(acts, T.isoformat())
    dl = {}
    for a in acts: dl[a["d"]] = dl.get(a["d"], 0) + a["ld"]
    day = lambda i: (T - timedelta(days=i)).isoformat()
    l7 = sum(dl.get(day(i), 0) for i in range(7)); lp7 = sum(dl.get(day(i), 0) for i in range(7, 14))
    zone, fatigue = None, None
    if ac is not None:
        if ac < TH["acwr_low"]: zone, fatigue = "sous_entraînement", 0.1
        elif ac <= TH["acwr_mid"]: zone, fatigue = "zone_douce", 0.25 + (ac - 0.8) / 0.5 * 0.25
        elif ac <= TH["acwr_high"]: zone, fatigue = "surcharge", 0.55 + (ac - 1.3) / 0.2 * 0.25
        else: zone, fatigue = "surmenage", min(1.0, 0.85 + (ac - 1.5) * 0.3)
    return {"acwr": ac, "zone": zone, "l7": l7, "lp7": lp7, "comp": None if fatigue is None else clamp(1 - fatigue)}

def stress_bb_axis(days, T):
    st = mean(_series(days, T, "st", 3)); bbx = _last(days, T, "bbx", 2); bbc = _last(days, T, "bbc", 2)
    c_st = clamp((60 - st) / 40) if st is not None else None
    c_bb = wavg([(.6, clamp((bbx - 40) / 50) if bbx is not None else None), (.4, clamp(bbc / 70) if bbc is not None else None)])
    return {"stress": st, "bb": bbx, "bb_charge": bbc, "readiness": _last(days, T, "tr", 2), "comp": wavg([(.5, c_st), (.5, c_bb)])}

def recent_axis(acts, T):
    """Les 3 derniers jours : discipline et intensité de chaque séance (aujourd'hui, hier, avant-hier)."""
    iso = lambda i: (T - timedelta(days=i)).isoformat()
    w = (0.5, 1.0, 0.6)
    days3, load_w = [], 0.0
    for i in range(3):
        L = [x for x in acts if x["d"] == iso(i)]
        for x in L: x["_i"] = intensity(x)
        days3.append(L); load_w += w[i] * sum(x["ld"] for x in L)
    chronic = sum(x["ld"] for x in acts if iso(27) <= x["d"] <= iso(0)) / 28
    ratio = load_w / (chronic * sum(w)) if chronic > 0 else None
    flat = [x for L in days3 for x in L]
    hard72 = [x for x in flat if x["_i"] == "dur"]
    comp = None
    if ratio is not None:
        comp = clamp(1 - 0.3 * ratio - 0.15 * max(0.0, ratio - 1) - (0.15 if len(hard72) >= 2 else 0.0))
    return {"days": days3, "ratio": ratio, "n_hard72": len(hard72),
            "hard_24h": any(x["_i"] == "dur" for L in days3[:2] for x in L),
            "legs_24h": any(leg_stress(x) for L in days3[:2] for x in L), "legs72": sum(1 for x in flat if leg_stress(x)),
            "run_hard24": any(x["s"] in ("run", "trail") and x["_i"] == "dur" for L in days3[:2] for x in L),
            "bike_hard24": any(x["s"] == "bike" and x["_i"] == "dur" for L in days3[:2] for x in L), "comp": comp}

def veto_caps(hrv, sl, ld, sb, rc):
    """Plafonds du FAF : liste de (nom, plafond, explication)."""
    caps = []
    r7, rt = hrv["r7"], hrv["rt"]
    if (r7 is not None and r7 <= TH["hrv_vlo"]) or (rt is not None and rt <= TH["hrv_vlo_today"]):
        caps.append(("VFC très basse", 0.75, f"VFC à {((rt if rt is not None else r7) - 1) * 100:+.0f} % de ta base"))
    elif r7 is not None and r7 <= TH["hrv_lo"]:
        caps.append(("VFC basse", 0.90, f"VFC sur 7 jours à {(r7 - 1) * 100:+.0f} % de ta base"))
    ac = ld["acwr"]
    if ac is not None and ac > TH["acwr_high"]: caps.append(("Ratio de charge > 1,5", 0.70, f"ratio aigu/chronique à {f1(ac, 2)}"))
    elif ac is not None and ac > TH["acwr_mid"]: caps.append(("Ratio de charge > 1,3", 0.90, f"ratio aigu/chronique à {f1(ac, 2)}"))
    if (sl["score"] is not None and sl["score"] < TH["sleep_poor_score"]) or (sl["h"] is not None and sl["h"] < TH["sleep_poor_h"]):
        caps.append(("Sommeil dégradé", 0.80, "score ou durée de sommeil trop bas"))
    elif sl["debt"] is not None and sl["debt"] >= TH["sleep_debt_cap"]:
        caps.append(("Dette de sommeil", 0.85, f"{f1(sl['debt'])} h de déficit sur 3 nuits"))
    if sb["stress"] is not None and sb["bb"] is not None and sb["stress"] > TH["stress_high"] and sb["bb"] < TH["bb_low"]:
        caps.append(("Stress élevé et Body Battery bas", 0.80, f"stress {sb['stress']:.0f}, Body Battery {sb['bb']:.0f}"))
    elif sb["bb"] is not None and sb["bb"] < TH["bb_vlow"]:
        caps.append(("Body Battery très bas", 0.85, f"Body Battery à {sb['bb']:.0f}"))
    tr = sb["readiness"]
    if tr is not None and tr < TH["readiness_vlow"]: caps.append(("Readiness très basse", 0.70, f"readiness Garmin à {tr:.0f}"))
    elif tr is not None and tr < TH["readiness_low"]: caps.append(("Readiness basse", 0.90, f"readiness Garmin à {tr:.0f}"))
    if rc["n_hard72"] >= 2: caps.append(("Deux séances dures en 72 h", 0.95, "pas de nouvelle séance dure"))
    return caps

def faf_band(faf):
    for lo, key, label in FAF_BANDS:
        if faf >= lo: return key, label

def cross_cases(hrv, sl, ld, sb):
    """Détection de cas croisés (signaux contradictoires ou combinés)."""
    out = []
    st, sc, tr = hrv["state"], sl["score"], sb["readiness"]
    if st == "haute" and (sc is not None and sc < 65): out.append("hrv_haute_sommeil_mauvais")
    if st in ("basse", "très_basse") and (sc is not None and sc >= 80): out.append("hrv_basse_sommeil_bon")
    if ld["zone"] == "zone_douce" and st in ("basse", "très_basse"): out.append("acwr_douce_hrv_basse")
    if ld["zone"] in ("surcharge", "surmenage") and st == "haute": out.append("acwr_haut_hrv_haute")
    if sb["stress"] is not None and sb["bb"] is not None and sb["stress"] > 45 and sb["bb"] < 50: out.append("stress_haut_bb_bas")
    if sl["h"] is not None and sl["h"] < 6.0 and sb["bb"] is not None and sb["bb"] >= 70: out.append("sommeil_court_bb_ok")
    if ld["zone"] in ("surcharge", "surmenage") and sc is not None and sc >= 80: out.append("charge_haute_sommeil_bon")
    if tr is not None and st is not None and ((tr >= 65 and st in ("basse", "très_basse")) or (tr <= 35 and st == "haute")): out.append("readiness_hrv_divergence")
    if sl["deep_pct"] is not None and sl["deep_pct"] < TH["deep_low_pct"] - 3: out.append("sommeil_profond_bas")
    if sl["rem_pct"] is not None and sl["rem_pct"] < TH["rem_low_pct"] - 4: out.append("rem_bas")
    return out

def training_needs(acts, T, ath, km4):
    """Besoins aérobie / anaérobie à partir des 21 derniers jours de course."""
    iso = lambda n: (T - timedelta(days=n)).isoformat()
    runs = [x for x in acts if x["s"] in ("run", "trail")]
    for x in runs: x["_k"] = run_kind(x)
    r21 = [x for x in runs if x["d"] >= iso(20)]
    n_ana = sum(1 for x in r21 if x["_k"] == "ana"); n_tempo = sum(1 for x in r21 if x["_k"] == "tempo")
    easy = sum(x["m"] for x in r21 if x["_k"] in ("easy", "long")); hard = sum(x["m"] for x in r21 if x["_k"] in ("ana", "tempo"))
    hs = hard / (easy + hard) * 100 if (easy + hard) else 0.0
    last = lambda L: max([x["d"] for x in L], default=None)
    dq, dlong = last([x for x in runs if x["_k"] in ("ana", "tempo")]), last([x for x in runs if x["_k"] == "long"])
    since = lambda d: (T - date.fromisoformat(d)).days if d else 99
    ds = {"run": since(last(runs)), "bike": since(last([x for x in acts if x["s"] == "bike"])),
          "swim": since(last([x for x in acts if x["s"] == "swim"])), "strength": since(last([x for x in acts if x["s"] == "strength"]))}
    vol = km4 / ath["weekly_km_target"]
    deficit_aero = (vol < TH["aero_vol_ratio_min"]) or (hs > TH["hard_share_high"] and len(r21) >= 4) or (since(dlong) >= TH["long_gap_days"] and vol < 1.0)
    deficit_ana = (n_ana == 0) and vol >= TH["aero_vol_ratio_min"]
    return {"n_ana": n_ana, "n_tempo": n_tempo, "hard_share": hs, "ds_q": since(dq), "ds_long": since(dlong), "ds": ds, "vol_ratio": vol,
            "n_runs21": len(r21), "deficit_aero": deficit_aero, "deficit_ana": deficit_ana}

def physio_state(acts, days, T, ath, km4):
    hrv, sl, ld, sb, rc = hrv_axis(days, T), sleep_axis(days, T), load_axis(acts, T), stress_bb_axis(days, T), recent_axis(acts, T)
    comps = {"hrv": hrv["comp"], "sleep": sl["comp"], "load": ld["comp"], "sb": sb["comp"], "recent": rc["comp"]}
    n_axes = sum(1 for k in ("hrv", "sleep", "load", "sb") if comps[k] is not None)
    poor = n_axes < 2
    ready = None if poor else wavg([(W_STRAIN[k], comps[k]) for k in comps])
    strain = None if ready is None else int(round((1 - ready) * 100))
    caps = veto_caps(hrv, sl, ld, sb, rc)
    base = TH["faf_default"] if ready is None else TH["faf_min"] + 0.65 * ready
    faf = round(max(TH["faf_min"], min(TH["faf_max"], min([base] + [c[1] for c in caps]))), 2)
    tn = training_needs(acts, T, ath, km4)
    cross = cross_cases(hrv, sl, ld, sb)
    # --- profil dominant (ordre de priorité) ---
    muscular = (ld["zone"] == "surcharge") or rc["legs72"] >= 2 or any(x["s"] in ("run", "trail") and x["km"] >= 18 for x in rc["days"][1])
    hrv_low = hrv["state"] in ("basse", "très_basse")
    tags = []
    if poor:
        profile = "données_insuffisantes"
    elif strain >= TH["strain_acute"] or (ld["acwr"] or 0) > TH["acwr_high"] or (hrv["state"] == "très_basse" and ((sl["comp"] if sl["comp"] is not None else 1) < 0.5 or (sb["comp"] if sb["comp"] is not None else 1) < 0.4)):
        profile = "fatigue_aiguë"
    elif muscular and not hrv_low and (ld["zone"] in ("surcharge", "zone_douce") or rc["legs72"] >= 2):
        profile = "surcharge_musculaire"
    elif strain >= TH["strain_incomplete"] or hrv_low or (sl["debt"] or 0) >= TH["sleep_debt_warn"] or (sb["bb_charge"] is not None and sb["bb_charge"] < TH["bb_charge_low"]):
        profile = "récupération_incomplète"
    elif (ld["acwr"] is not None and 1.0 <= ld["acwr"] <= TH["acwr_mid"] and (hrv["r7"] or 0) >= 1.0 and (sl["comp"] or 0) >= 0.6 and ld["lp7"] > 0 and ld["l7"] >= 1.05 * ld["lp7"]):
        profile = "assimilation_réussie"
    elif strain <= TH["strain_fresh"] and (ld["acwr"] is None or TH["acwr_low"] <= ld["acwr"] <= TH["acwr_mid"]) and hrv["state"] in (None, "haute", "stable"):
        profile = "déficit_aérobie" if tn["deficit_aero"] else "déficit_anaérobie" if tn["deficit_ana"] else "forme_optimale"
        if profile != "forme_optimale": tags.append("forme_optimale")
    else:
        profile = "déficit_aérobie" if tn["deficit_aero"] else "déficit_anaérobie" if tn["deficit_ana"] else "maintien"
    return {"hrv": hrv, "sleep": sl, "load": ld, "sb": sb, "recent": rc, "comps": comps, "ready": ready, "strain": strain,
            "caps": caps, "faf": faf, "faf_base": round(base, 2), "needs": tn, "cross": cross, "profile": profile, "tags": tags, "poor": poor}

def phrase_vars(st):
    """Variables injectables dans les banques de phrases (None si la donnée manque)."""
    hrv, sl, ld, sb = st["hrv"], st["sleep"], st["load"], st["sb"]
    p = hrv["rt"] if hrv["rt"] is not None else hrv["r7"]
    g = lambda v, n=0: None if v is None else f"{v:.{n}f}"
    return {"hrv_val": g(hrv["val"]), "hrv_baseline": g(hrv["base"]), "hrv_pct": None if p is None else f"{(p - 1) * 100:+.0f} %",
            "sleep_score": g(sl["score"]), "sleep_h": None if sl["h"] is None else f1(sl["h"]), "deep_pct": g(sl["deep_pct"]), "rem_pct": g(sl["rem_pct"]),
            "load_7d": g(ld["l7"]), "acwr": None if ld["acwr"] is None else f1(ld["acwr"], 2), "strain_index": st["strain"],
            "body_battery": g(sb["bb"]), "bb_charge": g(sb["bb_charge"]), "stress_avg": g(sb["stress"]), "faf": f1(st["faf"], 2),
            "readiness": g(sb["readiness"])}


# =============================================================================================
# 8. SYNTHÈSES PAR PÉRIODE
# =============================================================================================
CROSS_GOOD = {"acwr_haut_hrv_haute", "charge_haute_sommeil_bon"}

def synthesis(key, n, S, Sp, st, ctx, preds, goals, ath, T, D, PP=None, acts=()):
    """Synthèse de la période. Tout est calculé sur la fenêtre choisie (n jours) et la fenêtre est rappelée dans le texte ;
    seuls les signaux « Aujourd'hui » (diagnostic, cas croisés, dette de sommeil) restent ceux du jour."""
    PP = PP or {}
    iso = lambda k: (T - timedelta(days=k)).isoformat()
    win = f"sur {PLAB[key]}"
    lc = lambda t: t[0].lower() + t[1:] if len(t) > 1 and t[1].islower() else t      # « Aujourd'hui : les… » (sans majuscule parasite)
    L = lambda rule, salt, **v: PB.pick(PB.LINES[rule], D, f"{key}:{salt}", v)
    r = S["run"]
    preds = PP.get("preds") or preds
    rp = Sp["run"] if Sp else {"km": 0, "pace": None, "ef": None}
    weeks = n / 7
    d_h = pct(S["h"], Sp["h"]) if Sp else None
    d_km = pct(r["km"], rp["km"]) if Sp else None
    head = (f"Sur {PLAB[key]} : {S['n']} séance(s), {f1(S['h'])} h d'entraînement"
            f"{' (' + sgn(d_h) + ' vs période précédente)' if d_h is not None else ''}. "
            f"Course : {r['n']} sortie(s), {f1(r['km'])} km"
            f"{' à ' + pace(r['pace']) + '/km' if r['pace'] else ''}"
            f"{' (' + sgn(d_km) + ')' if d_km is not None else ''}.")
    good, bad, focus = [], [], []
    kmw = r["km"] / weeks
    if kmw >= 0.9 * ath["weekly_km_target"]: good.append(L("vol_good", "vol", kmw=f1(kmw), target=ath["weekly_km_target"]))
    elif kmw < 0.5 * ath["weekly_km_target"]: bad.append(L("vol_bad", "vol", kmw=f1(kmw), target=ath["weekly_km_target"]))
    if d_km is not None and d_km >= 10 and rp["km"] > 0: good.append(L("delta_up", "dkm", d=f"{d_km:.0f}"))
    if d_km is not None and d_km <= -25 and rp["km"] > 0: bad.append(L("delta_down", "dkm", d=f"{abs(d_km):.0f}"))
    rpw = r["n"] / weeks
    if rpw >= 3: good.append(L("regular_good", "reg", rpw=f1(rpw)))
    elif rpw < 2: bad.append(L("regular_bad", "reg", rpw=f1(rpw)))
    if rp["pace"] and r["pace"] and (rp["pace"] - r["pace"]) / rp["pace"] >= 0.02: good.append(L("pace_good", "pace", d=f"{(rp['pace'] - r['pace']) * 60:.0f}"))
    if r["ef"] and rp["ef"] and r["ef"] / rp["ef"] >= 1.02: good.append(L("ef_good", "ef", d=f"{(r['ef'] / rp['ef'] - 1) * 100:.0f}"))
    if r["ef"] and rp["ef"] and r["ef"] / rp["ef"] <= 0.97: bad.append(L("ef_bad", "ef", d=f"{(r['ef'] / rp['ef'] - 1) * 100:.0f}"))
    ac = PP.get("acwr_mean")
    if ac is not None:
        rule = ("acwr_sous" if ac < TH["acwr_low"] else "acwr_douce" if ac <= TH["acwr_mid"] else "acwr_surcharge" if ac <= TH["acwr_high"] else "acwr_surmenage")
        (good if rule == "acwr_douce" else bad).append(L(rule, "acwr", acwr=f1(ac, 2)).rstrip(".") + f" · ratio moyen {win}.")
    rc = S["rec"]
    r7 = PP.get("hrvr")
    if r7 is not None:
        pc = f"{(r7 - 1) * 100:+.0f} %"
        hw = f" · VFC moyenne {win}, base : 60 jours précédents"
        if r7 >= 1.0: good.append(L("hrv_good", "hrv", pct=pc).rstrip(".") + hw + ".")
        elif r7 <= TH["hrv_lo"]: bad.append(L("hrv_bad", "hrv", pct=pc).rstrip(".") + hw + ".")
    if rc["sc"] is not None:
        if rc["sc"] >= 80: good.append(L("sleep_good", "sleep", score=f"{rc['sc']:.0f}"))
        elif rc["sc"] < 70: bad.append(L("sleep_bad", "sleep", score=f"{rc['sc']:.0f}"))
    if (st["sleep"]["debt"] or 0) >= TH["sleep_debt_warn"]: bad.append("Aujourd'hui : " + lc(L("sleep_debt", "debt", debt=f1(st["sleep"]["debt"]))))
    dp, rp_ = stage_pcts(rc["deep"], rc["rem"], rc["sh"])
    if dp is not None and rp_ is not None:
        if dp >= TH["deep_low_pct"] and rp_ >= TH["rem_low_pct"]: good.append(L("stages_good", "stages", deep_pct=f"{dp:.0f}", rem_pct=f"{rp_:.0f}"))
        elif dp < TH["deep_low_pct"] - 2 or rp_ < TH["rem_low_pct"] - 3: bad.append(L("stages_bad", "stages", deep_pct=f"{dp:.0f}", rem_pct=f"{rp_:.0f}"))
    if rc["st"] is not None:
        if rc["st"] >= 50: bad.append(L("stress_bad", "stress", stress=f"{rc['st']:.0f}"))
        elif rc["st"] <= 30: good.append(L("stress_good", "stress", stress=f"{rc['st']:.0f}"))
    if rc["bbx"] is not None:
        if rc["bbx"] < 60: bad.append(L("bb_bad", "bb", bb=f"{rc['bbx']:.0f}"))
        elif rc["bbx"] >= 80: good.append(L("bb_good", "bb", bb=f"{rc['bbx']:.0f}"))
    rhrd = PP.get("rhrd")
    if rhrd is not None and rhrd >= 3: bad.append(f"FC de repos en hausse de {f1(rhrd)} bpm {win} par rapport à la base des 60 jours précédents : la récupération est à surveiller.")
    wr = [x for x in acts if iso(n - 1) <= x["d"] <= iso(0) and x["s"] in ("run", "trail")]
    if len(wr) >= 3:
        easy = sum(x["m"] for x in wr if run_kind(x) in ("easy", "long")); hard = sum(x["m"] for x in wr if run_kind(x) in ("ana", "tempo"))
        hs_v = hard / (easy + hard) * 100 if (easy + hard) else 0.0; hs = f"{hs_v:.0f}"
        pw_ = f" · intensité {win}, {len(wr)} sorties"
        if hs_v > TH["hard_share_high"]: bad.append(L("polar_bad", "polar", hs=hs).rstrip(".") + pw_ + ".")
        elif hs_v < TH["hard_share_low"]: bad.append(L("polar_low", "polar", hs=hs).rstrip(".") + pw_ + ".")
        else: good.append(L("polar_good", "polar", hs=hs).rstrip(".") + pw_ + ".")
    sw = S["sp"]["strength"]["n"] / weeks
    if sw >= 1.5: good.append(L("str_good", "str", sw=f1(sw)))
    else: bad.append(L("str_bad", "str", sw=f1(sw), target=ath["strength_per_week"]))
    cross = S["sp"]["bike"]["n"] + S["sp"]["swim"]["n"]
    if cross >= 1: good.append(L("cross_good", "cross", bike=S["sp"]["bike"]["n"], swim=S["sp"]["swim"]["n"]))
    else: bad.append(L("cross_bad", "cross"))
    v = phrase_vars(st)         # signaux du jour : identiques pour toutes les périodes, annoncés « Aujourd'hui »
    for c in st["cross"][:3]:
        (good if c in CROSS_GOOD else bad).append("Aujourd'hui : " + lc(PB.pick(PB.CROSS[c], D, f"cross:{c}", v)))
    head += " Aujourd'hui : " + lc(PB.pick(PB.DIAG[st["profile"]]["head"], D, "diag.head", v))
    for p in preds:
        if p["ret"] and p["target"]:
            g = p["gap"]
            focus.append(f"{p['label']} : prédiction {hms(p['ret'])} pour {hms(p['target'])} visé ({'objectif à portée' if g <= 0 else hms(g) + ' à gagner'}) · base : sorties et VO2max {win}.")
        elif p["ret"]:
            focus.append(f"{p['label']} : prédiction {hms(p['ret'])} · base : sorties et VO2max {win}.")
    nxt = next((g for g in goals if date.fromisoformat(g["date"]) >= T), None)
    if nxt: focus.append(f"Prochaine échéance : {nxt['label']} dans {(date.fromisoformat(nxt['date']) - T).days} jours.")
    if r["longest"]: focus.append(f"Sortie la plus longue : {f1(r['longest'])} km · D+ cumulé {r['el']} m.")
    return {"head": head, "good": good or ["Pas de point fort marquant sur cette période."],
            "bad": bad or ["Aucun point faible notable sur cette période."], "focus": focus}


# =============================================================================================
# 8 bis. « LE MOT DU COACH » : paragraphe de synthèse humoristique (bibliothèque bilan_bank.py)
# =============================================================================================
def bilan_signals(key, n, PP, st, S, Sp, goals, T, fresh=None):
    """Résume en quelques signaux (période + état du jour) ce dont bilan_bank.compose() a besoin."""
    weeks = n / 7.0
    f = lambda v, d=1: None if v is None else f1(v, d)
    pil = {p["key"]: {"score": p["score"], "name": p["name"]} for p in PP.get("pillars", [])}
    r, rc = S["run"], S["rec"]
    # objectif : prochaine course avec prédiction ET temps visé, sinon n'importe quelle prédiction chiffrée
    preds = [p for p in (PP.get("preds") or []) if p.get("ret")]
    nxt = next((g for g in goals if date.fromisoformat(g["date"]) >= T), None)
    pick = next((p for p in preds if p.get("target") and nxt and abs(p["dist"] - nxt["dist"]) < 0.5 and nxt.get("sport", "run") == "run"), None) or next((p for p in preds if p.get("target")), None)
    goal = {}
    if pick:
        gap = pick["ret"] - pick["target"]
        goal = {"ret": pick["ret"], "target": pick["target"], "glabel": pick["label"].replace(" ", "\u00a0"), "gret": hms(pick["ret"]), "gtarget": hms(pick["target"]),
                "ggap": hms(abs(gap)), "gpct": f"{abs(gap) / pick['target'] * 100:.0f}"}
    hrvr = PP.get("hrvr")
    hrv_p = None if hrvr is None else f"{(hrvr - 1) * 100:+.0f} %"
    v0 = phrase_vars(st)
    vars_ = {"strain": v0["strain_index"], "faf": v0["faf"], "hrv_pct": v0["hrv_pct"], "sleep_score": v0["sleep_score"], "sleep_h": v0["sleep_h"],
             "acwr": v0["acwr"], "bb": v0["body_battery"], "sleep_debt": f((st["sleep"]["debt"] or 0), 1), "hrv_pct_p": hrv_p,
             "stress": None if rc["st"] is None else f"{rc['st']:.0f}"}
    pvars = {"pred": {k: goal.get(k) for k in ("glabel", "gret", "gtarget")},
             "run": {"kmw": f(r["km"] / weeks), "long_km": f(r["longest"])},
             "load": {"acwr": f(PP.get("acwr_mean"), 2)},
             "rec": {"sleep_h": f(rc["sh"]), "hrv_pct": hrv_p},
             "cross": {"sw": f(S["sp"]["strength"]["n"] / weeks), "cw": f((S["sp"]["bike"]["n"] + S["sp"]["swim"]["n"]) / weeks)}}
    mod = None
    if (st["sleep"]["debt"] or 0) >= TH["sleep_debt_warn"]: mod = "debt"
    elif hrvr is not None and hrvr <= TH["hrv_lo"]: mod = "hrv_low"
    elif rc["st"] is not None and rc["st"] >= 50: mod = "stress"
    elif hrvr is not None and hrvr >= TH["hrv_hi"] and st["profile"] not in BB.STATE_KO: mod = "hrv_good"
    elif rc["bbx"] is not None and rc["bbx"] < 60:
        mod = "bb_low"; vars_["bb"] = f"{rc['bbx']:.0f}"
    trend, dkm = None, None
    if Sp and Sp["run"]["km"] > 0:
        d = pct(r["km"], Sp["run"]["km"])
        trend = "up" if d >= 10 else "down" if d <= -15 else "flat"
        dkm = f"{abs(d):.0f}"
        vars_["dkm"] = dkm
    ac_m = PP.get("acwr_mean")
    fr = fresh or {}
    if fr.get("level"):
        vars_["sdays"] = str(fr.get("age_wellness") if fr.get("age_wellness") is not None else fr.get("sync_age") or "plusieurs")
        vars_["sdate"] = None if not fr.get("last_wellness") else date.fromisoformat(fr["last_wellness"]).strftime("%d/%m")
    return {"stale": fr.get("level"), "score": PP.get("score"), "profile": st["profile"], "pillars": pil, "load_dir": None if ac_m is None else ("high" if ac_m > TH["acwr_mid"] else "low"), "pillar_vars": pvars, "goal": goal, "vars": vars_, "mod": mod,
            "trend": trend, "days_to_race": None if not nxt else (date.fromisoformat(nxt["date"]) - T).days,
            "vars_race": {"rlabel": None if not nxt else nxt["label"]}}


def bilan_text(key, n, PP, st, S, Sp, goals, T, D, fresh=None, mem=None):
    """Paragraphe du coach pour une période ; ne fait jamais échouer l'analyse (texte vide en cas d'erreur)."""
    try:
        sig = bilan_signals(key, n, PP, st, S, Sp, goals, T, fresh)
        sig["vars"].update(sig.pop("vars_race"))
        out = BB.compose(sig, D, key, mem)
        if mem is not None: mem.record_today(key, out["text"])
        return out
    except Exception as e:          # noqa: BLE001 : le dashboard doit toujours se générer
        return {"text": "", "short": "", "parts": [], "scenario": {}, "error": f"{type(e).__name__}: {e}"}


# =============================================================================================
# 9. ENTRAÎNEMENT DU JOUR
# =============================================================================================
STR_TYPES = {"push": re.compile(r"pecto|pect|épaule|epaule|push|triceps|poussée", re.I),
             "pull": re.compile(r"\bdos\b|pull|biceps|tirage|traction", re.I),
             "legs": re.compile(r"jambe|leg|squat|cuisse|fessier|mollet", re.I)}
# indices des séances de la famille « force » (sessions_library) par type de rotation
STR_LABEL = {"push": "Push (pecs, épaules, triceps)", "pull": "Pull (dos, biceps)", "legs": "Legs (jambes)"}

def strength_plan(acts, T, rc, prof):
    """Prochaine séance de force : rotation Push -> Pull -> Legs d'après les noms des dernières séances.
    Une séance au nom générique (« Musculation ») compte comme la suivante de la rotation. Sans aucun nom reconnu :
    rotation calendaire. Les jambes sont reportées si elles sont déjà sollicitées."""
    order = ["push", "pull", "legs"]
    pos, seen, generic = None, [], 0
    for a in [a for a in acts if a["s"] == "strength"][-9:]:
        k = next((k for k, rx in STR_TYPES.items() if rx.search(a.get("nm") or "")), None)
        if k:
            pos, generic = order.index(k), 0
            seen.append(k)
        elif pos is not None:
            pos, generic = (pos + 1) % 3, generic + 1
    nxt = order[(pos + 1) % 3] if pos is not None else order[T.toordinal() % 3]
    legs_busy = rc["legs_24h"] or rc["legs72"] >= 2 or prof in ("surcharge_musculaire", "fatigue_aiguë", "récupération_incomplète")
    skipped = False
    if nxt == "legs" and legs_busy:
        skipped = True
        last_idx = {t: max([i for i, k in enumerate(seen) if k == t], default=-1) for t in ("push", "pull")}
        nxt = min(("push", "pull"), key=lambda t: last_idx[t])
    return nxt, skipped, (seen, generic)


def strength_hist(acts, T):
    """Séances de musculation récentes : liste de (jours écoulés, type push|pull|legs|None), la plus récente d'abord.
    Une séance au nom générique compte comme la suivante de la rotation (même règle que strength_plan)."""
    order, pos, out = ["push", "pull", "legs"], None, []
    for a in [a for a in acts if a["s"] == "strength"][-9:]:
        k = next((k for k, rx in STR_TYPES.items() if rx.search(a.get("nm") or "")), None)
        if k: pos = order.index(k)
        elif pos is not None: pos = (pos + 1) % 3; k = order[pos]
        out.append(((T - date.fromisoformat(a["d"])).days, k))
    return out[::-1]

def big_swim(x): return x["s"] == "swim" and (x["m"] >= 45 or x["km"] >= 2.0 or x["ld"] >= 70)
def mid_swim(x): return x["s"] == "swim" and (x["m"] >= 30 or x["km"] >= 1.2)
def big_bike(x): return x["s"] == "bike" and (x["ld"] >= 120 or x["km"] >= 60 or x["m"] >= 120)
def mid_bike(x): return x["s"] == "bike" and (x["ld"] >= 70 or x["m"] >= 75)

def type_loads(st, acts, T):
    """FAF propre à chaque type de séance (Push / Pull / Legs) : le FAF global, plafonné selon ce qui a été fait hier et avant-hier.
    Jambes : grosse sortie vélo ou course exigeante, ou jambes déjà travaillées en musculation -> séance allégée.
    Pecs, dos, épaules : grosse séance de natation, ou même groupe musculaire travaillé il y a moins de 48 h -> allégé.
    Retourne {type: {"faf", "why": [textes]}}."""
    rc, prof, faf = st["recent"], st["profile"], st["faf"]
    recent = rc["days"][0] + rc["days"][1]        # aujourd'hui (si déjà fait) et hier
    d2 = rc["days"][2]
    hist = strength_hist(acts, T)
    cap = {t: [] for t in ("push", "pull", "legs")}          # (plafond, texte)
    def add(t, c, txt): cap[t].append((c, txt))
    # --- jambes ---
    if any(k == "legs" and d <= 1 for d, k in hist): add("legs", 0.50, "jambes déjà travaillées en musculation il y a moins de 48 h")
    elif any(k == "legs" and d == 2 for d, k in hist): add("legs", 0.80, "séance de jambes il y a 2 jours")
    if any(big_bike(x) for x in recent): add("legs", 0.65, "grosse sortie vélo hier : jambes à ménager")
    elif any(mid_bike(x) for x in recent): add("legs", 0.80, "sortie vélo conséquente hier")
    if any(x["s"] in ("run", "trail") and leg_stress(x) for x in recent): add("legs", 0.65, "course exigeante ou longue hier : jambes à ménager")
    elif any(leg_stress(x) for x in d2): add("legs", 0.90, "séance éprouvante pour les jambes il y a 2 jours")
    if rc["legs72"] >= 2: add("legs", 0.65, "deux séances à forte contrainte pour les jambes en 72 h")
    if prof == "surcharge_musculaire": add("legs", 0.60, "profil de surcharge musculaire")
    # --- haut du corps ---
    if any(big_swim(x) for x in recent):
        add("pull", 0.65, "grosse séance de natation hier : dos et épaules déjà sollicités")
        add("push", 0.70, "grosse séance de natation hier : épaules déjà sollicitées")
    elif any(mid_swim(x) for x in recent):
        add("pull", 0.85, "séance de natation hier : dos et épaules un peu sollicités")
        add("push", 0.90, "séance de natation hier : épaules un peu sollicitées")
    elif any(big_swim(x) for x in d2): add("pull", 0.90, "grosse natation il y a 2 jours")
    for t in ("push", "pull"):
        if any(k == t and d <= 1 for d, k in hist): add(t, 0.60, f"{t.capitalize()} déjà travaillé il y a moins de 48 h")
        elif any(k == t and d == 2 for d, k in hist): add(t, 0.85, f"{t.capitalize()} travaillé il y a 2 jours")
    if prof == "fatigue_aiguë":
        for t in cap: add(t, 0.60, "fatigue aiguë : séance courte et sans échec musculaire")
    out = {}
    for t, L in cap.items():
        f = round(max(TH["faf_min"], min([faf] + [c for c, _ in L])), 2)
        why = [txt[0].upper() + txt[1:] for c, txt in sorted(L) if c <= faf][:3]
        if not why: why = ["Aucune contrainte particulière liée aux derniers jours : volume complet selon ta forme."] if f >= 0.95 else [f"Volume ajusté à ton FAF de {f1(f, 2)}."]
        out[t] = {"faf": f, "why": why}
    return out

def choose_default(nxt, loads):
    """Type proposé par défaut : le prochain de la rotation s'il est assez frais (FAF du type >= 0,8), sinon le suivant, sinon le plus frais."""
    order = ["push", "pull", "legs"]
    pref = [order[(order.index(nxt) + k) % 3] for k in range(3)]
    for t in pref:
        if loads[t]["faf"] >= 0.8: return t
    return max(pref, key=lambda t: (loads[t]["faf"], -pref.index(t)))

def muscu_block(acts, T, st):
    nxt, skipped, (seen, generic) = strength_plan(acts, T, st["recent"], st["profile"])
    loads = type_loads(st, acts, T)
    t = choose_default(nxt, loads)
    lab = lambda x: PPL.TYPES[x][0]
    reason = (f"Rotation Push → Pull → Legs : après « {lab(seen[-1])} », le suivant est {lab(nxt)}." if seen else f"Rotation de départ : {lab(nxt)}.")
    if skipped: reason += " Les jambes sont reportées : elles ont été sollicitées ces derniers jours."
    if t != nxt: reason += f" {lab(nxt)} est allégé par tes derniers jours, donc {lab(t)} passe en premier."
    reason += f" {lab(t)} proposé à {PPL.level_of(loads[t]['faf']).lower()} (FAF du type {f1(loads[t]['faf'], 2)})."
    return PPL.muscu_payload(T, loads, t, reason)

def strength_card_blocks(m):
    t = m["default"]; T_ = m["types"][t]; s = T_["sessions"][T_["today_n"] - 1]
    ex = "\n".join(f"{e['i']}. {e['name']} : {e['sets']} × {e['reps']} {e['unit']} · repos {e['rest']}" for e in s["ex"])
    return s, [["Objectif", T_["sub"]], ["Échauffement", " ".join(T_["warmup"]["phases"])], ["Exercices", ex],
               ["Adaptation à ta forme", T_["effort"] + " " + " ".join(T_["why"])], ["Progression", m["guide"][0]]]

def plan_day(st, T, goals, D, acts):
    """Choisit la famille de séance par discipline (selon profil, FAF, 3 derniers jours) et classe les disciplines."""
    faf, prof, rc, tn = st["faf"], st["profile"], st["recent"], st["needs"]
    quality_ok = faf >= 0.95 and not rc["hard_24h"] and rc["n_hard72"] < 2 and prof not in ("fatigue_aiguë", "récupération_incomplète", "surcharge_musculaire")
    mid_ok = faf >= 0.8 and prof != "fatigue_aiguë"
    nxt = next((g for g in goals if date.fromisoformat(g["date"]) >= T), None)
    left = (date.fromisoformat(nxt["date"]) - T).days if nxt else 999
    stype, skipped, seen = strength_plan(acts, T, rc, prof)

    def family(disc):
        if disc == "strength": return "force"      # musculation = programme Push/Pull/Legs, volume modulé par le FAF de chaque type
        if faf < 0.65 or prof == "fatigue_aiguë": return "recup"
        if prof == "surcharge_musculaire": return "recup" if disc == "run" else "z2"
        if prof == "récupération_incomplète": return "recup" if faf < 0.75 else "z2"
        if prof == "déficit_anaérobie": f = "vo2" if quality_ok else ("aerobe" if mid_ok and not rc["hard_24h"] else "z2")
        elif prof == "déficit_aérobie": f = "aerobe" if (mid_ok and faf >= 0.9 and not rc["hard_24h"] and PB.h(D, f"aero.{disc}") % 3 == 0) else "z2"
        elif prof == "assimilation_réussie": f = "spec" if quality_ok else ("aerobe" if mid_ok and not rc["hard_24h"] else "z2")
        elif prof == "forme_optimale": f = ("vo2" if tn["n_ana"] <= tn["n_tempo"] else "aerobe") if quality_ok else ("aerobe" if mid_ok and not rc["hard_24h"] else "z2")
        elif prof == "maintien": f = "aerobe" if (mid_ok and not rc["hard_24h"] and PB.h(D, f"m.{disc}") % 2 == 0) else "z2"
        else: f = "z2"
        # contraintes : jamais deux fois la même contrainte de suite
        if f in ("vo2", "spec", "aerobe") and rc["hard_24h"]: f = "z2"
        if disc == "run" and f in ("vo2", "spec") and (rc["legs_24h"] or rc["run_hard24"]): f = "aerobe" if mid_ok and not rc["hard_24h"] else "z2"
        if disc == "run" and f == "spec" and nxt and nxt["id"] == "trail" and left <= 60: f = "trail"
        return f

    def cap_level(disc):
        """Plafond d'intensité assimilable aujourd'hui (1 récupération … 5 séance très intense), d'après le profil, le FAF et les 3 derniers jours."""
        if faf < 0.65 or prof == "fatigue_aiguë": return 1
        if prof == "surcharge_musculaire": return 1 if disc == "run" else 2
        if prof == "récupération_incomplète": return 1 if faf < 0.75 else 2
        lvl = 5 if quality_ok else (3 if mid_ok and not rc["hard_24h"] else 2)
        if rc["hard_24h"]: lvl = min(lvl, 2)
        if disc == "run" and (rc["legs_24h"] or rc["run_hard24"]): lvl = min(lvl, 3)
        return lvl

    fam = {d: family(d) for d in ("run", "swim", "bike", "strength")}
    # stratégie de préparation (planner.py) : objectifs -> phase -> famille de séance, réconciliée avec l'état de forme ci-dessus (plafond)
    try:
        plan = PLN.planifier(acts, T, goals, st, dict(fam), {d: cap_level(d) for d in ("run", "swim", "bike")}, D)
    except Exception:                      # le moteur de planification ne doit jamais empêcher le dashboard de se générer
        plan = None
    if plan:
        for d in ("run", "swim", "bike"): fam[d] = plan["fam"][d]
    base = {"run": 1.0, "bike": 0.8, "swim": 0.75, "strength": 0.65}
    score = {}
    for d in base:
        s = base[d] + 0.12 * min(tn["ds"][d], 4)
        if d == "run":
            if rc["run_hard24"]: s -= 0.9
            elif tn["ds"]["run"] <= 1: s -= 0.2
            if prof in ("surcharge_musculaire", "fatigue_aiguë"): s -= 0.6
        elif d == "bike":
            if rc["bike_hard24"]: s -= 0.7
            if prof == "surcharge_musculaire": s += 0.15
        elif d == "swim":
            if tn["ds"]["swim"] <= 1: s -= 0.3
            if prof in ("surcharge_musculaire", "fatigue_aiguë", "récupération_incomplète"): s += 0.3
        else:
            if tn["ds"]["strength"] <= 1: s -= 1.0
            elif tn["ds"]["strength"] == 2: s -= 0.4
            if tn["ds"]["strength"] >= 4 and faf >= 0.85: s += 0.3
            if fam["strength"] == "plyo" and rc["legs_24h"]: s -= 0.5
        if plan: s += plan["bonus"].get(d, 0.0)
        score[d] = s + (PB.h(D, "rank." + d) % 1000) / 1e5     # départage déterministe
    order = sorted(score, key=score.get, reverse=True)
    rec = [order[0]]
    sec = order[1]
    lv = lambda d: FAM_LVL[fam[d]]
    if score[sec] >= score[order[0]] - 0.45 and (sec == "strength" or lv(order[0]) <= 2 or lv(sec) <= 2) and not (lv(order[0]) >= 4 and lv(sec) >= 3):
        rec.append(sec)
    return fam, rec, {"stype": stype, "skipped": skipped, "seen": seen, "plan": plan}

def suggestions(acts, days, T, goals, ath, Z, preds, ctx, st, D):
    v = phrase_vars(st)
    faf, prof = st["faf"], st["profile"]
    fam, rec, extra = plan_day(st, T, goals, D, acts)
    plan = extra.get("plan")
    band, band_label = faf_band(faf)
    zv = SL.zone_vars(Z, ath, faf)
    cards = []
    muscu = muscu_block(acts, T, st)
    for d in ("run", "swim", "bike", "strength"):
        if d == "strength":      # musculation : séance du programme Push/Pull/Legs (30 séances), voir muscu_block()
            ps, blocks = strength_card_blocks(muscu)
            tl = muscu["types"][muscu["default"]]
            why = PB.pick(PB.CUES[band], D, "cue.strength", dict(v, dur=ps["min"], dur_base=ps["min"])) if d in rec else ""
            why = (why + " " if why else "") + muscu["reason"]
            if plan and d in rec and plan["phase"].get("strength") == "affutage": why += " Affûtage en cours : séance de force réduite, sans fatigue résiduelle."
            cards.append({"id": d, "cat": DISC_FR[d], "title": f"{tl['label']} {ps['n']:02d} · {ps['title']}",
                          "meta": f"{ps['min']} min · {len(ps['ex'])} exercices · {tl['level']}", "rec": d in rec, "why": why, "blocks": blocks, "_dur": ps["min"]})
            continue
        if (d, fam[d]) not in SL.LIB: fam[d] = "z2"
        lst = SL.LIB[(d, fam[d])]
        vol, note = 1.0, ""
        if plan and fam[d] == "long":      # sortie longue : durée croissante avec l'avancement de la préparation, plafonnée par la distance de l'objectif
            cap = plan["long_cap"].get(d) or 10 ** 9
            ls = sorted([s_ for s_ in lst if s_["min"] <= cap] or lst[:1], key=lambda s_: s_["min"])
            want = set(plan.get("tags", {}).get(d) or ())
            fit = [s_ for s_ in ls if not s_["tags"] or s_["tags"] & want] if want else ls     # séances propres à une autre épreuve écartées
            ls = fit if len(fit) >= 3 else ls
            sess = ls[int(round(plan["prog"].get(d, 0.3) * (len(ls) - 1)))]
        else:
            want = plan.get("tags", {}).get(d) if plan else None
            sess = SL.pick(lst, want, PB.h("", f"sess.{d}.{fam[d]}") + T.toordinal())      # décalage fixe + n° du jour ; séances de l'épreuve visée en priorité
        if plan:
            vol = plan["vol"].get(d, 1.0)
            if vol < 1.0 and plan["phase"].get(d) in ("affutage", "reprise", "recuperation", "jour_j"):
                note = f"Phase « {PLN.PHASE_FR[plan['phase'][d]].lower()} » : volume à {round(vol * 100)} % du volume de référence."
        r = SL.render(sess, zv, faf, vol=vol, note=note)
        why = ""
        if d in rec:
            why = PB.pick(PB.CUES[band], D, f"cue.{d}", dict(v, dur=r["dur"], dur_base=r["dur_base"]))
            if plan:
                jt = PLN.justification(plan, d, fam[d])
                if jt: why = (why + " " if why else "") + jt
        cat = "Trail" if fam[d] == "trail" else DISC_FR[d]
        cards.append({"id": d, "cat": cat, "title": r["name"], "meta": r["meta"], "rec": d in rec, "why": why, "blocks": r["blocks"], "_dur": r["dur"]})
    rc, hrv, sl, ld, sb = st["recent"], st["hrv"], st["sleep"], st["load"], st["sb"]
    context = []
    for i, lab in enumerate(["Aujourd'hui", "Hier", "Avant-hier"]):
        L = rc["days"][i]
        context.append(f"{lab} : " + (" + ".join(f"{SPORT_FR[x['s']].lower()} {f1(x['km']) + ' km' if x['km'] else str(round(x['m'])) + ' min'} ({x['_i']}, charge {x['ld']:.0f})" for x in L) if L else "repos"))
    if hrv["val"] is not None and hrv["base"]:
        sl_txt = ""
        if hrv["slope_pct_day"] is not None:
            sl_txt = ", tendance en hausse" if hrv["slope_pct_day"] > 0.8 else ", tendance en baisse" if hrv["slope_pct_day"] < -0.8 else ", tendance stable"
        m7 = f", moyenne 7 jours à {(hrv['r7'] - 1) * 100:+.0f} %{sl_txt}" if hrv["r7"] else ""
        context.append(f"VFC : {hrv['val']:.0f} ms pour une base de {hrv['base']:.0f} ms ({v['hrv_pct']}){m7}")
    else:
        context.append("VFC : non disponible (ou historique insuffisant pour calculer une base)")
    if sl["score"] is not None or sl["h"] is not None:
        ph = f" · profond {sl['deep_pct']:.0f} %, REM {sl['rem_pct']:.0f} %" if sl["deep_pct"] is not None and sl["rem_pct"] is not None else ""
        scs = f"score {sl['score']:.0f}/100" if sl["score"] is not None else "score n/a"
        context.append(f"Sommeil : {scs} · {f1(sl['h']) + ' h' if sl['h'] else 'durée n/a'}{ph}")
    else:
        context.append("Sommeil : non synchronisé")
    zl = {"sous_entraînement": "sous-entraînement", "zone_douce": "zone douce", "surcharge": "surcharge", "surmenage": "surmenage"}
    context.append(f"Charge : ratio aigu/chronique {f1(ld['acwr'], 2)} ({zl[ld['zone']]}) · {ld['l7']:.0f} sur 7 jours" if ld["acwr"] else "Charge : historique insuffisant")
    if sb["stress"] is not None and sb["bb"] is not None:
        context.append(f"Stress moyen {sb['stress']:.0f} · Body Battery max {sb['bb']:.0f}" + (f", recharge {sb['bb_charge']:.0f}" if sb["bb_charge"] is not None else ""))
    else:
        context.append("Stress / Body Battery : partiels")
    context.append(f"Indice de fatigue {st['strain']}/100 · FAF {f1(faf, 2)} ({band_label.lower()})" if st["strain"] is not None else f"FAF {f1(faf, 2)} (par défaut, données insuffisantes)")
    tn = st["needs"]
    needs = []
    if tn["n_ana"] == 0: needs.append("Anaérobie : aucune séance de vitesse (VMA) sur 21 jours.")
    if tn["n_tempo"] == 0: needs.append("Seuil : aucune séance tempo ou seuil sur 21 jours.")
    if tn["ds_long"] >= TH["long_gap_days"]:
        needs.append(f"Endurance longue : dernière sortie longue il y a {tn['ds_long']} jours." if tn["ds_long"] < 99 else "Endurance longue : aucune sortie longue (16 km ou plus) enregistrée.")
    if tn["hard_share"] > TH["hard_share_high"] and tn["n_runs21"] >= 4: needs.append(f"Trop d'intensité : {tn['hard_share']:.0f} % du temps de course sur 21 jours (visé : environ 20 %), privilégier l'endurance.")
    if tn["vol_ratio"] < TH["aero_vol_ratio_min"]: needs.append(f"Volume : {tn['vol_ratio'] * 100:.0f} % de la cible hebdomadaire de course.")
    if not needs: needs.append("Équilibre aérobie / anaérobie correct sur 21 jours : poursuivre la rotation endurance, seuil, vitesse.")
    for c in st["cross"][:3]: needs.append(PB.pick(PB.CROSS[c], D, f"needs.cross.{c}", v))
    if plan:
        up = [o for o in plan["objs"] if o["days_left"] >= 0]
        if up:
            main = next((o for o in up if o["prio"] == "A"), up[0])
            nxt_o = min(up, key=lambda o: o["days_left"])
            line = f"Préparation : {main['label']} dans {main['days_left']} jours ({PLN.PHASE_FR[main['phase']].lower()})"
            if nxt_o is not main: line += f" ; prochaine échéance : {nxt_o['label']} dans {nxt_o['days_left']} jours (objectif {nxt_o['role']})"
            needs.append(line + ".")
    needs.append(PB.pick(PB.DIAG[prof]["advice"], D, "diag.advice", v))
    for name, cap, txt in sorted(st["caps"], key=lambda c: c[1])[:2]: needs.append(f"Plafond du FAF à {f1(cap, 2)} : {name.lower()} ({txt}).")
    for key, msg in (("hrv", "VFC non disponible : le diagnostic repose sur les autres indicateurs."), ("sleep", "Sommeil non disponible : le diagnostic repose sur les autres indicateurs.")):
        if st["comps"][key] is None: needs.append(msg)
    chosen = [c for c in cards if c["rec"]]
    decision = f"Séance retenue : {chosen[0]['title']} ({chosen[0]['cat'].lower()}, {chosen[0]['_dur']} min), adaptée au FAF de {f1(faf, 2)}."
    if len(chosen) > 1: decision += f" En complément : {chosen[1]['title']} ({chosen[1]['cat'].lower()}, {chosen[1]['_dur']} min)."
    why = PB.pick(PB.DIAG[prof]["head"], D, "diag.head", v) + " " + decision
    headline = " + ".join(f"{c['cat']} : {c['title']}" for c in chosen)
    for c in cards: c.pop("_dur", None)
    return {"context": context, "needs": needs, "why": why, "rec": rec, "headline": headline, "cards": cards, "hard_share": tn["hard_share"], "muscu": muscu, "plan": plan}


# =============================================================================================
# 10. POINT D'ENTRÉE
# =============================================================================================
def sanitize(acts, days):
    """Garde-fou d'entrée : valeurs numériques absentes ou invalides -> 0 pour les champs de volume ; activités sans date valide ignorées ;
    valeurs de bien-être non numériques (texte, NaN, infini) -> absentes. Les données de la montre ne doivent jamais faire échouer l'analyse."""
    def num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    out = []
    for x in acts or []:
        if not isinstance(x, dict): continue
        try:
            date.fromisoformat(str(x.get("d"))[:10])
        except ValueError:
            continue
        y = dict(x)
        for k in ("km", "m", "hr", "el", "ld"):
            if not num(y.get(k)): y[k] = 0
        for k in ("te", "vo2", "pw", "cal"):
            if y.get(k) is not None and not num(y.get(k)): y[k] = None
        y.setdefault("s", "other")
        out.append(y)
    dd = {}
    for k, v in (days or {}).items():
        if isinstance(v, dict): dd[k] = {kk: (vv if (vv is None or num(vv)) else None) for kk, vv in v.items()}
    return out, dd


def build_analysis(acts, days, today, goals, ath, periods, events=None, meta=None, coach_mem=None):
    T = date.fromisoformat(today)
    acts, days = sanitize(acts, days)
    calib = calibrate(days, T)                     # seuils personnalisés (avant tout calcul)
    fresh = data_freshness(acts, days, T, meta)
    pcheck = prediction_check(acts, T, goals)
    vo2 = next((x["vo2"] for x in reversed(acts) if x["vo2"]), None)
    first = min([x["d"] for x in acts] + list(days.keys()) + [today])
    preds = predictions(acts, T, goals, vo2)
    Z = zones(preds, goals)
    P, ctx = pillars(acts, days, T, goals, ath, preds, vo2)
    ok = [p for p in P if p["score"] is not None]
    total = sum(p["score"] for p in ok) / (4 * len(ok)) * 20 if ok else None
    st = physio_state(acts, days, T, ath, ctx["km4"])
    pillars_p = {key: pillars_period(acts, days, T, goals, ath, vo2, n) for key, n in periods.items()}      # note /20 et piliers par période
    stats, synth, bilan = {}, {}, {}
    mem = CM.Memoire(coach_mem, T) if coach_mem is not None else None        # mémoire anti-redondance (None : rotation seule)
    for key, n in periods.items():
        S = period_stats(acts, days, T, n)
        has_prev = (T - timedelta(days=2 * n - 1)).isoformat() >= first
        Sp = period_stats(acts, days, T, n, off=n) if has_prev else None
        stats[key] = {"cur": S, "prev": Sp}
        synth[key] = synthesis(key, n, S, Sp, st, ctx, preds, goals, ath, T, today, pillars_p[key], acts)
        bilan[key] = bilan_text(key, n, pillars_p[key], st, S, Sp, goals, T, today, fresh, mem)
    gl = [dict(g, left=(date.fromisoformat(g["date"]) - T).days) for g in goals]
    for g in gl:
        r = next((p for p in preds if abs(p["dist"] - g["dist"]) < 0.5 and g.get("sport", "run") == "run"), None)
        g["pred"] = r["ret"] if r else None
    sug = suggestions(acts, days, T, goals, ath, Z, preds, ctx, st, today)
    band, band_label = faf_band(st["faf"])
    v = phrase_vars(st)
    rnd = lambda x: None if x is None else (round(x, 3) if isinstance(x, float) else x)
    coach = {"profile": st["profile"], "profile_label": PB.PROFILE_LABEL[st["profile"]], "tags": st["tags"],
             "head": PB.pick(PB.DIAG[st["profile"]]["head"], today, "diag.head", v), "strain_index": st["strain"],
             "form_index": None if st["strain"] is None else 100 - st["strain"], "faf": st["faf"], "faf_base": st["faf_base"],
             "faf_band": band, "faf_label": band_label, "caps": [{"name": c[0], "cap": c[1], "text": c[2]} for c in st["caps"]],
             "comps": {k: (None if c is None else round(c, 2)) for k, c in st["comps"].items()}, "cross": st["cross"],
             "hrv": {k: rnd(x) for k, x in st["hrv"].items() if k != "comp"},
             "sleep": {k: rnd(x) for k, x in st["sleep"].items() if k != "comp"},
             "acwr": rnd(st["load"]["acwr"]), "acwr_zone": st["load"]["zone"], "stress": rnd(st["sb"]["stress"]), "body_battery": st["sb"]["bb"]}
    return {"today": today, "vo2": vo2, "score": total, "score_label": score_label(total) if total is not None else "",
            "pillars": P, "pillars_p": pillars_p, "preds": preds, "zones": Z, "stats": stats, "synth": synth, "bilan": bilan, "petit_plus": PP_LIB.du_jour(T), "goals": gl, "fresh": fresh, "calib": calib, "pred_check": pcheck, "events": build_events(events, pcheck, T),
            "corr": correlations(acts, days, T), "suggest": sug,
            "ctx": {"hrvr": ctx["hrvr"], "acwr": ctx["acwr"], "km4": ctx["km4"], "long6": ctx["long6"]}, "coach": coach}
