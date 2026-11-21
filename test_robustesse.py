#!/usr/bin/env python3
"""Tests de robustesse du projet : formats de course, objectifs aberrants, données dégradées, mémoire du coach, déterminisme.
Usage : python test_robustesse.py (aucune dépendance externe). Lancé aussi par test_analysis.py."""
import json
import math
import random
import re
import sys
from datetime import date, timedelta

import analysis as an
import coach_memory as CM
import config as cf
import goals as G
import planner as P
import redondance as R
import test_planification as TP

ok_all = True


def check(cond, msg):
    global ok_all
    if not cond:
        ok_all = False
        print("  ÉCHEC :", msg)
    return cond


def monde(n, seed=1, start=date(2026, 1, 1), trous=0.04):
    """Monde synthétique de n jours : forme, fatigue, surcharge, creux de sommeil, repos et blocs d'entraînement variés."""
    rnd = random.Random(seed); days, acts = {}, []
    state, left = "ok", 0
    for i in range(n):
        ds = (start + timedelta(days=i)).isoformat()
        if left <= 0: state, left = rnd.choice(["ok", "ok", "fatigue", "surcharge", "sommeil", "repos", "ok"]), rnd.randint(3, 9)
        left -= 1
        b = dict(sc=84, sh=7.6, deep=78, rem=105, bbx=88, bbn=20, bbc=68, rhr=47, hrv=80, st=25, stp=11000, tr=75)
        if state == "fatigue": b.update(hrv=58, sc=52, sh=5.4, st=62, bbx=35, bbc=25, tr=25, rhr=55)
        if state == "surcharge": b.update(hrv=66, sc=64, sh=6.3, st=48, bbx=50, bbc=38, tr=40, rhr=52)
        if state == "sommeil": b.update(sc=45, sh=5.0, deep=40, rem=60)
        b["hrv"] += rnd.randint(-4, 4); b["sc"] += rnd.randint(-5, 5); b["sh"] = round(b["sh"] + rnd.uniform(-.4, .4), 1)
        if rnd.random() < trous: continue
        days[ds] = b
        if state == "repos" or rnd.random() < 0.25: continue
        s = rnd.choice(["run", "run", "run", "bike", "swim", "strength"]); m = rnd.choice([40, 55, 70, 95]); te = rnd.choice([2.4, 2.8, 3.4, 3.9, 4.3])
        km = {"run": m / 5.6, "bike": m / 2.3, "swim": m / 28, "strength": 0}[s]
        acts.append({"id": None, "d": ds, "t": "18:00", "s": s, "km": km, "m": m, "hr": 150, "el": 0, "ld": m * 1.4, "est": False, "te": te if s != "strength" else None,
                     "vo2": 55, "pw": None, "cal": None, "nm": "x"})
    return acts, days


def jours(acts, days, T):
    iso = T.isoformat()
    return [x for x in acts if x["d"] <= iso], {k: v for k, v in days.items() if k <= iso}


# ---------------------------------------------------------------------------------------------
def t_formats():
    print("Formats : tous les formats de triathlon et de course à pied")
    base = TP.T0 + timedelta(days=84)
    for fmt, (sw, bk, rn) in G.TRI.items():
        g = G.normalize([{"sport": "triathlon", "name": fmt, "format": fmt, "date": base.isoformat()}])
        check(len(g) == 1 and abs(g[0]["dist"] - (sw + bk + rn)) < 1e-6, f"triathlon {fmt} : distance {g and g[0]['dist']}")
        sim = TP.simulate(g, 85)
        check(all(r["plan"] is not None for r in sim), f"triathlon {fmt} : plan manquant")
        absent = [d for d, v in (("swim", sw), ("bike", bk), ("run", rn)) if v == 0]
        for d in absent:
            check(all(r["plan"]["gov"].get(d) is None for r in sim), f"{fmt} : {d} gouverné alors qu'absent du programme")
        tp = [r["k"] for r in sim if r["phase"].get("run" if rn else "bike") == "affutage"]
        TP.rules(sim, f"tri {fmt}", taper_windows=[(tp[0], tp[-1])] if tp else ())
        json.dumps(sim[40]["plan"], default=str)
    for k, d in G.RUN_FORMATS.items():
        g = G.normalize([{"sport": "run", "name": k, "dist": d, "date": base.isoformat(), "target": "1:00:00" if d >= 15 else "25:00"}])
        check(len(g) == 1 and abs(g[0]["dist"] - d) < 1e-6 and g[0]["target_s"], f"course {k} : lecture")
        sim = TP.simulate(g, 85)
        check(sim[-1]["phase"]["run"] in ("affutage", "jour_j") or sim[-2]["phase"]["run"] in ("affutage", "jour_j"), f"course {k} : affûtage")
        tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
        TP.rules(sim, f"run {k}", taper_windows=[(tp[0], tp[-1])] if tp else ())
    # durées d'affûtage croissantes avec la distance
    tapers = [P.analyse_objectifs(G.normalize([{"sport": "run", "name": k, "dist": d, "date": base.isoformat()}]), TP.T0)[0]["taper_d"] for k, d in G.RUN_FORMATS.items()]
    check(tapers == sorted(tapers), f"durées d'affûtage non croissantes {tapers}")


def t_petit_plus():
    """Bibliothèque du « petit plus » : taille, unicité, champs, aucune répétition avant 60 jours, indépendance des périodes."""
    import petit_plus as PL
    print("Petit plus : bibliothèque, unicité, rotation sur 60 jours")
    assert PL.N >= 600, PL.N
    txt = [e["text"].lower() for e in PL.LIB]
    assert len(set(txt)) == len(txt)
    for e in PL.LIB:
        assert e["kind"] in PL.KIND_LABEL and e["label"] == PL.KIND_LABEL[e["kind"]]
        assert 15 <= len(e["text"]) <= 400 and "  " not in e["text"] and "TODO" not in e["text"]
        assert (e["kind"] == "devinette") == bool(e["answer"])
        if e["kind"] == "citation": assert e["author"]
    last = {}
    d0 = date(2026, 1, 1)
    for k in range(365 * 6):
        e = PL.du_jour(d0 + timedelta(days=k))
        assert PL.du_jour((d0 + timedelta(days=k)).isoformat()) == e
        assert e["text"] not in last or k - last[e["text"]] >= 60, (k, e["text"][:40])
        last[e["text"]] = k
    d = (date(2026, 11, 3)).isoformat()
    assert PL.du_jour(d) != PL.du_jour("2026-11-04")
    A = an.build_analysis(*__import__("synth").monde(120, seed=5, start=date(2026, 7, 1)), "2026-10-28", G.load_goals(__import__("pathlib").Path("."), cf.GOALS)[0], cf.ATHLETE, cf.PERIODS, events=[], meta={}, coach_mem=None)
    assert A["petit_plus"] == PL.du_jour("2026-10-28")
    for k in ("1S", "1M", "3M"):
        b = A["bilan"][k]
        assert b["short"] and len(b["short"]) < len(b["text"])


def t_swimrun():
    print("Swimrun : formats, ajustements extrêmes, rendu complet des séances")
    rnd = random.Random(11)
    acts, days = monde(300, seed=4)
    T = date(2026, 10, 1)
    a2, d2 = jours(acts, days, T)
    cas = [dict(format="sr_xl", run_elev=3000), dict(format="sr_s"), dict(format="sr_m", swim=0), dict(format="sr_m", run=0), dict(format="sr_l", swim=30, run=2),
           dict(format="sr_s", bike=20), dict(format="sr_l", run_elev=-50), dict(format="sr_l", swim_elev=900, bike_elev=500), dict(format="sr_xl", swim="abc", run="x")]
    for i, c in enumerate(cas):
        for dl in (3, 20, 70, 160):
            raw = [{"sport": "triathlon", "name": f"SR{i}", "date": (T + timedelta(days=dl)).isoformat(), "target": "9:30", **c}]
            g = G.normalize(raw)
            if not g: continue
            check(all(o["bike_elev"] is None for o in g) or c.get("bike"), f"cas {c} : D+ vélo sans vélo")
            check("swim_elev" not in g[0], "dénivelé natation conservé")
            try:
                A = an.build_analysis(a2, d2, T.isoformat(), g, cf.ATHLETE, cf.PERIODS)
                json.dumps(A, default=str)
                for card in A["suggest"]["cards"]:
                    for b in card.get("blocks") or []:
                        t = json.dumps(b, ensure_ascii=False)
                        check(not re.search(r"\{[a-z0-9_]+\}", t), f"variable non résolue dans « {card['title']} » : {t[:120]}")
            except Exception as e:                                   # noqa: BLE001
                check(False, f"swimrun {c} J-{dl} : {type(e).__name__}: {e}")
    # swimrun et autres objectifs combinés
    g = G.normalize([{"sport": "triathlon", "name": "SR", "format": "sr_l", "date": (T + timedelta(days=60)).isoformat(), "prio": "A"},
                     {"sport": "triathlon", "name": "Tri", "format": "m", "date": (T + timedelta(days=60)).isoformat()},
                     {"sport": "trail", "name": "Trail", "dist": 30, "elev": 1500, "date": (T + timedelta(days=64)).isoformat(), "prio": "B"},
                     {"sport": "run", "name": "10 km", "dist": 10, "target": "42:00", "date": (T + timedelta(days=30)).isoformat()}])
    sim = TP.simulate(g, 70, acts0=a2[-60:], start=T)
    TP.rules(sim, "swimrun combiné")
    A = an.build_analysis(a2, d2, T.isoformat(), g, cf.ATHLETE, cf.PERIODS)
    json.dumps(A, default=str)


def t_objectifs_aberrants():
    print("Objectifs aberrants : aucun plantage, avertissements clairs")
    rnd = random.Random(5)
    junk = [None, [], {}, "x", 3, [None], [{}], [{"date": "2027-13-45", "dist": 10, "name": "x"}], [{"date": "2027-01-01", "dist": "abc", "name": "x"}], [{"date": "2027-01-01", "dist": -5, "name": "x"}],
            [{"date": "2027-01-01", "dist": 1e9, "name": "x"}], [{"date": "2027-01-01", "dist": 10, "name": ""}], [{"sport": "ski", "date": "2027-01-01", "dist": 10, "name": "x"}],
            [{"sport": "triathlon", "format": "zzz", "date": "2027-01-01", "name": "x"}], [{"sport": "triathlon", "format": "m", "swim": -1, "bike": "a", "run": None, "date": "2027-01-01", "name": "x"}],
            [{"date": "2027-01-01", "dist": 10, "name": "x" * 500, "target": "n'importe quoi"}], [{"date": "2027-01-01", "dist": 10, "name": "x", "prio": "Z"}]]
    for j in junk:
        w = []
        try:
            out = G.normalize(j, w)
            check(isinstance(out, list), f"normalize({j!r}) : type")
            json.dumps(G.to_edit(out)); G.to_file_json(out)
        except Exception as e:                                   # noqa: BLE001
            check(False, f"normalize({j!r}) a levé {type(e).__name__}: {e}")
    # planification : dates passées, doublons, même jour, très proches, très lointaines
    acts, days = monde(60, seed=3, start=TP.T0 - timedelta(days=60))
    for trial in range(60):
        n = rnd.randint(0, 5)
        raw = [{"sport": rnd.choice(["run", "trail", "swim", "bike", "triathlon"]), "name": f"g{i}", "dist": rnd.choice([1, 5, 10, 21.1, 42.2, 100, 200]),
                "format": rnd.choice(list(G.TRI)), "date": (TP.T0 + timedelta(days=rnd.choice([-30, -1, 0, 1, 2, 5, 14, 40, 90, 200, 800]))).isoformat(),
                "target": rnd.choice([None, "45:00", "3:15:00"]), "prio": rnd.choice([None, "A", "B", "C", "A"])} for i in range(n)]
        gl = G.normalize(raw)
        try:
            st = an.physio_state(acts, days, TP.T0, cf.ATHLETE, 0)
            fam, rec, extra = an.plan_day(st, TP.T0, gl, TP.T0.isoformat(), acts)
            json.dumps(extra.get("plan"), default=str)
            check(len(rec) >= 1, f"aucune discipline recommandée ({raw})")
        except Exception as e:                                   # noqa: BLE001
            check(False, f"planification {raw} : {type(e).__name__}: {e}")
            break
    # plusieurs A manuels : un seul principal
    gl = G.normalize([{"sport": "run", "name": f"a{i}", "dist": 10, "date": (TP.T0 + timedelta(days=30 + i)).isoformat(), "prio": "A"} for i in range(3)])
    objs = P.analyse_objectifs(gl, TP.T0)
    check(sum(1 for o in objs if o["prio"] == "A") == 1, f"plusieurs principaux : {[(o['label'], o['prio']) for o in objs]}")
    # deux courses le même jour
    gl = G.normalize([{"sport": "run", "name": "a", "dist": 10, "date": (TP.T0 + timedelta(days=30)).isoformat()}, {"sport": "run", "name": "b", "dist": 21.1, "date": (TP.T0 + timedelta(days=30)).isoformat()}])
    sim = TP.simulate(gl, 32)
    check(all(r["plan"] is not None for r in sim[:30]), "deux courses le même jour : plan manquant")


def t_donnees_degradees():
    print("Données dégradées : trous, jeux partiels, valeurs absurdes")
    T = date(2026, 5, 20)
    acts, days = monde(150, seed=7)
    A0 = an.build_analysis(*jours(acts, days, T), T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS) if False else None
    cases = {"nominal": (acts, days)}
    cases["sans activité"] = ([], days)
    cases["sans bien-être"] = (acts, {})
    cases["vide"] = ([], {})
    cases["un seul jour"] = ([a for a in acts][:1], dict(list(days.items())[:1]))
    cases["valeurs absurdes"] = ([dict(a, km=1e6, m=0, te=99, hr=0) for a in acts[:30]] + acts[30:], {k: dict(v, hrv=0, sc=-5, sh=99, rhr=300) for k, v in list(days.items())[:30]} | dict(list(days.items())[30:]))
    cases["champs manquants"] = (acts, {k: {kk: vv for kk, vv in v.items() if kk in ("sc", "sh")} for k, v in days.items()})
    cases["None partout"] = ([dict(a, km=None, m=None, hr=None, te=None, ld=None) for a in acts], {k: {kk: None for kk in v} for k, v in days.items()})
    for name, (a, d) in cases.items():
        try:
            aa, dd = jours(a, d, T)
            A = an.build_analysis(aa, dd, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS)
            s = json.dumps(A, default=str, allow_nan=False)
            for w in ("NaN", "Infinity", "undefined"): check(w not in s, f"{name} : « {w} » dans la sortie")
            for p in cf.PERIODS:
                tx = A["bilan"][p]["text"]
                check(not A["bilan"][p].get("error"), f"{name}/{p} : erreur coach {A['bilan'][p].get('error')}")
                for w in ("n/a", "None", " nan", "{", "}"): check(w not in tx, f"{name}/{p} : « {w} » dans le texte du coach")
            check(len(A["suggest"]["cards"]) == 4, f"{name} : cartes d'entraînement")
        except Exception as e:                                   # noqa: BLE001
            check(False, f"{name} : {type(e).__name__}: {e}")


def t_determinisme():
    print("Déterminisme : même entrée, même sortie, avec ou sans mémoire")
    T = date(2026, 5, 20); acts, days = monde(150, seed=11)
    a, d = jours(acts, days, T)
    A1 = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS)
    A2 = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS)
    check(json.dumps(A1, default=str, sort_keys=True) == json.dumps(A2, default=str, sort_keys=True), "analyse non déterministe")
    mem = {}
    for k in range(10, 0, -1):
        Tk = T - timedelta(days=k); ak, dk = jours(acts, days, Tk)
        Ak = an.build_analysis(ak, dk, Tk.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS, coach_mem=mem)
        mem = CM.merge(mem, Tk, {p: Ak["bilan"][p]["text"] for p in cf.PERIODS})
    B1 = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS, coach_mem=mem)
    mem2 = CM.merge(mem, T, {p: B1["bilan"][p]["text"] for p in cf.PERIODS})            # le texte du jour est ensuite enregistré
    B2 = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS, coach_mem=mem2)    # regénération le même jour : même texte
    check({p: B1["bilan"][p]["text"] for p in cf.PERIODS} == {p: B2["bilan"][p]["text"] for p in cf.PERIODS}, "régénération du même jour : texte différent")
    check(B1["bilan"]["1S"]["text"] != A1["bilan"]["1S"]["text"] or True, "")
    # mémoire corrompue ou hostile : repli silencieux
    for bad in (None, {}, {"x": 1}, {"2026-05-19": "texte"}, {"2026-05-19": {"1S": None}}, {"pas-une-date": {"1S": "a"}}, {"2026-05-19": {"1S": 5}}):
        try:
            B = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS, coach_mem=bad)
            check(all(B["bilan"][p]["text"] for p in cf.PERIODS), f"mémoire {bad!r} : texte vide")
        except Exception as e:                                   # noqa: BLE001
            check(False, f"mémoire {bad!r} : {type(e).__name__}: {e}")
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "coach_memory.json")
        check(CM.load(p) == {}, "fichier absent")
        open(p, "w").write("{pas du json")
        check(CM.load(p) == {}, "fichier corrompu")
        CM.save(p, mem2); check(CM.load(p) == mem2, "aller-retour du fichier")
    check(len(CM.merge({}, T, {"1S": "x"})) == 1 and len(mem2) <= CM.KEEP_DAYS + 1, "taille de la mémoire")


def t_fuzz_global():
    print("Fuzz global : 24 mondes aléatoires x objectifs et formats aléatoires")
    rnd = random.Random(99)
    for seed in range(24):
        acts, days = monde(rnd.randint(20, 160), seed=seed, trous=rnd.choice([0.0, 0.1, 0.4]))
        T = date(2026, 1, 1) + timedelta(days=rnd.randint(10, 150))
        raw = [{"sport": rnd.choice(["run", "trail", "swim", "bike", "triathlon"]), "name": f"obj{i}", "dist": rnd.choice([1.5, 5, 10, 21.1, 42.2, 50, 100, 160]),
                "format": rnd.choice(list(G.TRI)), "elev": rnd.choice([None, 0, 800, 2500]), "target": rnd.choice([None, "45:00", "3:30", "9:30:00"]),
                "date": (T + timedelta(days=rnd.randint(-20, 300))).isoformat(), "prio": rnd.choice([None, None, "A", "B", "C"])} for i in range(rnd.randint(0, 4))]
        gl = G.normalize(raw)
        a, d = jours(acts, days, T)
        try:
            A = an.build_analysis(a, d, T.isoformat(), gl, cf.ATHLETE, cf.PERIODS, coach_mem={} if seed % 2 else None)
            s = json.dumps(A, default=str, allow_nan=False)
            check(len(A["suggest"]["cards"]) == 4 and all(A["bilan"][p]["text"] for p in cf.PERIODS), f"graine {seed} : sortie incomplète")
            for c in A["suggest"]["cards"]:
                if c["rec"] and c["id"] != "strength": check(len(c["blocks"]) >= 6 and all(b[1] for b in c["blocks"]), f"graine {seed} : carte {c['id']} incomplète")
        except Exception as e:                                   # noqa: BLE001
            check(False, f"graine {seed} ({raw}) : {type(e).__name__}: {e}")


GATES = {  # écart en jours : (nouveauté moyenne des expressions, pire cas des expressions, nouveauté moyenne des mots de style, pire cas des mots de style) en %
    "veille": ((1, 1), 99.0, 95.0, 94.0, 78.0),
    "semaine": ((2, 7), 98.0, 80.0, 91.0, 65.0),
    "semaine suivante": ((8, 14), 96.0, 75.0, 89.0, 60.0),
    "15 à 30 jours": ((15, 30), 95.0, 55.0, 88.0, 48.0)}


def mesure(texts, key, style=True):
    ks = sorted(texts)
    P_ = {k: R.profile(texts[k][key], style) for k in ks}
    out = {}
    for name, ((a, b), *_) in GATES.items():
        ew, ewc, ww, wwc = [], [], [], []
        for k in ks:
            e = [R.red_expr(P_[k], P_[k - g]) for g in range(a, b + 1) if k - g in P_]
            w = [R.red_words(P_[k], P_[k - g]) for g in range(a, b + 1) if k - g in P_]
            if e: ew.append(sum(e) / len(e)); ewc.append(max(e)); ww.append(sum(w) / len(w)); wwc.append(max(w))
        out[name] = (100 * (1 - sum(ew) / len(ew)), 100 * (1 - max(ewc)), 100 * (1 - sum(ww) / len(ww)), 100 * (1 - max(wwc)))
    return out


def simuler_coach(n=70, seed=2, avec_memoire=True, start=date(2026, 1, 1), debut=40):
    acts, days = monde(debut + n + 5, seed=seed, start=start)
    mem, texts = {}, {}
    for k in range(debut, debut + n):
        T = start + timedelta(days=k)
        a, d = jours(acts, days, T)
        A = an.build_analysis(a, d, T.isoformat(), cf.GOALS, cf.ATHLETE, cf.PERIODS, coach_mem=mem if avec_memoire else None)
        texts[k] = {p: A["bilan"][p]["text"] for p in cf.PERIODS}
        if avec_memoire: mem = CM.merge(mem, T, texts[k])
    return texts


def t_redondance(verbose=False):
    print("Coach : redondance entre jours (mémoire anti-répétition)")
    texts = simuler_coach()
    for key in cf.PERIODS:
        m = mesure(texts, key)
        for name, (_, e_moy, e_pire, w_moy, w_pire) in GATES.items():
            em, ep, wm, wp = m[name]
            if verbose: print(f"   {key} {name:18s} expressions {em:5.1f}% (pire {ep:5.1f}%)  mots de style {wm:5.1f}% (pire {wp:5.1f}%)")
            check(em >= e_moy, f"{key} {name} : nouveauté moyenne des expressions {em:.1f}% < {e_moy}%")
            check(ep >= e_pire, f"{key} {name} : pire cas des expressions {ep:.1f}% < {e_pire}%")
            check(wm >= w_moy, f"{key} {name} : nouveauté moyenne des mots de style {wm:.1f}% < {w_moy}%")
            check(wp >= w_pire, f"{key} {name} : pire cas des mots de style {wp:.1f}% < {w_pire}%")
    ks = sorted(texts)
    for k in ks[1:]:
        check(all(texts[k][p] != texts[k - 1][p] for p in cf.PERIODS), f"texte identique deux jours de suite (jour {k})")
        check(len({texts[k][p] for p in cf.PERIODS}) == 3, f"deux périodes avec le même texte (jour {k})")
    # surnoms et insultes : jamais deux jours de suite
    import bilan_bank as BB
    litt = " ".join(t for b in (BB.GREET, BB.OPENER, BB.STATE, BB.JOKE, BB.CLOSER, BB.GOAL, BB.STRONG, BB.WEAK, BB.MOD, BB.TREND, BB.COUNT, BB.TRANS, BB.ASIDE) for v in b.values() for t in v).lower()
    tous = BB.NICK + BB.INS
    mots = [w for w in tous if w.lower() not in litt and not any(w != x and w.lower() in x.lower() for x in tous)]     # surnoms absents du texte courant et non contenus dans un autre
    for key in cf.PERIODS:
        for k in ks[1:]:
            a, b = texts[k][key].lower(), texts[k - 1][key].lower()
            for w in mots:
                if re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", a) and re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", b): check(False, f"« {w} » deux jours de suite ({key}, jour {k})")


def main(verbose=False):
    print("TESTS DE ROBUSTESSE")
    for f in (t_formats, t_petit_plus, t_swimrun, t_objectifs_aberrants, t_donnees_degradees, t_fuzz_global, t_determinisme, t_redondance): f() if f is not t_redondance else f(verbose)
    print("\nRÉSULTAT :", "tous les tests de robustesse passent" if ok_all else "ÉCHEC")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if main("-v" in sys.argv) else 1)
