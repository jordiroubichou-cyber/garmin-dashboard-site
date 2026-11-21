#!/usr/bin/env python3
"""Tests de analysis.py : 4 scénarios synthétiques (forme optimale, fatigue aiguë, surcharge, données manquantes),
déterminisme, compatibilité avec le template et rendu complet des séances.
Usage : python test_analysis.py   (aucune dépendance externe)"""
import json
import random
import re
import sys
from datetime import date, timedelta

import analysis as an
import config as cf

TODAY = "2026-10-28"
T = date.fromisoformat(TODAY)
KEYS_SUGGEST = {"context", "needs", "why", "rec", "headline", "cards", "muscu"}
KEYS_TOP = {"today", "vo2", "score", "score_label", "pillars", "preds", "zones", "stats", "synth", "goals", "corr", "suggest", "coach", "pillars_p"}


def iso(i): return (T - timedelta(days=i)).isoformat()

def act(i, s, km, m, ld, nm, te=None, hr=150, el=0, vo2=None):
    return {"id": None, "d": iso(i), "t": "18:00", "s": s, "km": km, "m": m, "hr": hr, "el": el, "ld": ld, "est": False,
            "te": te, "vo2": vo2, "pw": None, "cal": None, "nm": nm}

def base_week(i0):
    """Semaine type dont le lundi est à l'indice i0 (jours avant aujourd'hui)."""
    return [act(i0 - 1, "run", 10.0, 40, 100, "Nice - 10 x 400m", te=4.2, vo2=55),
            act(i0 - 3, "run", 9.0, 50, 65, "Nice - 50 min endurance", te=2.8),
            act(i0 - 4, "run", 7.0, 40, 50, "Nice - 40 min footing", te=2.5),
            act(i0 - 5, "bike", 50.0, 110, 90, "Cannes Cyclisme sur route", te=3.0),
            act(i0 - 6, "run", 18.0, 100, 110, "Nice - sortie longue", te=3.4),
            act(i0, "strength", 0, 55, 40, "Pectoraux épaules"), act(i0 - 2, "swim", 2.0, 40, 45, "Nat piscine")]

def world(kind, seed):
    rnd = random.Random(seed)
    acts, days = [], {}
    for w in range(12, -1, -1):          # 13 semaines types, la séance du jour n'existe pas encore (synchro de 6 h)
        acts += base_week(w * 7 + 3)
    acts = [a for a in acts if a["d"] <= iso(1)]
    for i in range(89, -1, -1):
        days[iso(i)] = {"sc": 84 + rnd.randint(-4, 4), "sh": round(7.6 + rnd.uniform(-.4, .4), 2), "deep": 78 + rnd.randint(-8, 8), "rem": 105 + rnd.randint(-10, 10),
                        "bbx": 88 + rnd.randint(-5, 5), "bbn": 20, "bbc": 68 + rnd.randint(-6, 6), "rhr": 47 + rnd.randint(-1, 1), "hrv": 80 + rnd.randint(-3, 3),
                        "st": 25 + rnd.randint(-4, 4), "stp": 11000, "tr": 75 + rnd.randint(-5, 5)}
    if kind == "optimale":
        for i in range(0, 7): days[iso(i)]["hrv"] = 85 + rnd.randint(-1, 1); days[iso(i)]["sc"] = 88
    elif kind == "fatigue":
        for i in range(1, 8): acts.append(act(i, "run" if i % 2 == 0 else "bike", 12.0, 70, 170, "Nice - 6 x 1000m", te=4.5))
        for i in range(0, 7):
            days[iso(i)].update(hrv=62 + rnd.randint(-2, 2), sc=50, sh=5.2, st=64, bbx=32, bbc=25, tr=22)
    elif kind == "surcharge":
        acts = [a for a in acts if a["d"] <= iso(7)]
        acts += [act(7, "run", 10.0, 45, 110, "Nice - 10 x 400m", te=4.0), act(6, "bike", 90.0, 200, 200, "Cannes Cyclisme"), act(5, "run", 12.0, 60, 140, "Nice - 3x2000 seuil", te=4.0),
                 act(4, "run", 14.0, 75, 130, "Footing long", te=3.5), act(3, "bike", 80.0, 170, 190, "Cannes Cyclisme"), act(2, "strength", 0, 60, 90, "Jambes squat"),
                 act(1, "run", 20.0, 115, 190, "Sortie longue 20 km", te=4.0)]
        for i in range(0, 7): days[iso(i)].update(hrv=80 + rnd.randint(-2, 2), sc=82, tr=68)
    elif kind == "manquantes":
        acts = [act(2, "run", 8.0, 45, 70, "Footing"), act(5, "swim", 1.5, 35, 40, "Nat")]
        days = {iso(1): {"stp": 8000}}
    return acts, days

EXPECT = {"optimale": ("forme_optimale", (0.95, 1.15)), "fatigue": ("fatigue_aiguë", (0.5, 0.7)),
          "surcharge": ("surcharge_musculaire", (0.5, 0.9)), "manquantes": ("données_insuffisantes", (0.85, 0.85))}

def build(kind, seed=1):
    acts, days = world(kind, seed)
    return an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)

def check_structure(A, kind):
    assert KEYS_TOP <= set(A), f"clés manquantes : {KEYS_TOP - set(A)}"
    assert KEYS_SUGGEST <= set(A["suggest"])
    for p in cf.PERIODS: assert {"head", "good", "bad", "focus"} <= set(A["synth"][p]) and all(isinstance(x, str) for x in A["synth"][p]["good"] + A["synth"][p]["bad"])
    assert len(A["suggest"]["cards"]) == 4 and any(c["rec"] for c in A["suggest"]["cards"])
    for c in A["suggest"]["cards"]:
        assert len(c["blocks"]) == (5 if c["id"] == "strength" else 7), c["title"]
        txt = " ".join(b[1] for b in c["blocks"]) + c["title"] + c["why"] + c["meta"]
        assert not re.search(r"[{}]", txt) and "n/a" not in txt and "None" not in txt, (kind, c["title"], txt[:200])
    check_muscu(A["suggest"]["muscu"])
    for p in cf.PERIODS:
        PP = A["pillars_p"][p]
        assert len(PP["pillars"]) == 5 and (PP["score"] is None or 0 <= PP["score"] <= 20) and all(x["lines"] for x in PP["pillars"]), p
        assert "None" not in " ".join(l for x in PP["pillars"] for l in x["lines"]) and "nan" not in " ".join(l for x in PP["pillars"] for l in x["lines"]).lower()
    alltxt = json.dumps(A, ensure_ascii=False)
    assert "NaN" not in alltxt and "None" not in A["suggest"]["why"]
    json.dumps(A, allow_nan=False, default=str)


def check_muscu(m):
    """30 séances (10 par type), séance du jour dans le type par défaut, aucun texte à trous."""
    assert m["default"] in ("push", "pull", "legs") and set(m["types"]) == {"push", "pull", "legs"}
    for t, T_ in m["types"].items():
        assert len(T_["sessions"]) == 10 and 1 <= T_["today_n"] <= 10 and 0.5 <= T_["faf"] <= 1.15 and T_["why"] and len(T_["warmup"]["phases"]) == 3, t
        for s in T_["sessions"]:
            assert s["ex"] and 20 <= s["min"] <= 75, (s["id"], s["min"])
            txt = " ".join([s["title"], s["effort"]] + [e["name"] + e["note"] + e["why"] + e["rest"] + e["reps"] for e in s["ex"]])
            assert not re.search(r"[{}]", txt) and "None" not in txt and "NaN" not in txt, s["id"]


def test_muscu():
    """Programme PPL : 158 exercices conservés, adaptation du type selon la veille, variété d'un jour à l'autre."""
    import ppl_program as P
    full = P.render_program(1.1)
    n_ex = sum(len(s["ex"]) for t in full for s in full[t]["sessions"])
    assert n_ex == 158 and len(P.PROGRAM) == 30, n_ex
    mins = [s["min"] for t in full for s in full[t]["sessions"]]
    assert 50 <= min(mins) and max(mins) <= 70, (min(mins), max(mins))
    low = P.render_program(0.55)
    assert all(len(s["ex"]) <= 3 and all(e["sets"] <= 2 for e in s["ex"]) for t in low for s in low[t]["sessions"])
    acts, days = world("optimale", 1)
    base = [a for a in acts if a["s"] != "strength" and a["d"] <= iso(3)]
    def muscu_for(extra, hist=()):
        A = an.build_analysis(base + list(extra) + list(hist), days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
        return A["suggest"]["muscu"]
    free = muscu_for([])
    assert all(free["types"][t]["faf"] >= 0.95 for t in free["types"]), {t: free["types"][t]["faf"] for t in free["types"]}
    bike = muscu_for([act(1, "bike", 90.0, 200, 190, "Cannes Cyclisme sur route")])
    assert bike["types"]["legs"]["faf"] <= 0.65 and bike["default"] != "legs", ("vélo hier", bike["types"]["legs"]["faf"], bike["default"])
    assert bike["types"]["legs"]["level"] in ("Allégé", "Léger") and any("vélo" in w for w in bike["types"]["legs"]["why"])
    swim = muscu_for([act(1, "swim", 3.0, 70, 90, "Nat piscine 3000 m")])
    assert swim["types"]["pull"]["faf"] <= 0.65 and swim["types"]["push"]["faf"] <= 0.7 and swim["default"] == "legs", (swim["types"]["pull"]["faf"], swim["default"])
    pushy = muscu_for([], [act(1, "strength", 0, 55, 60, "Push pecs épaules")])
    assert pushy["types"]["push"]["faf"] <= 0.6 and pushy["default"] != "push", pushy["default"]
    run = muscu_for([act(1, "run", 16.0, 90, 140, "Nice - 16 km")])
    assert run["types"]["legs"]["faf"] <= 0.65, run["types"]["legs"]["faf"]
    # variété : pour chaque type, jamais la même séance deux jours de suite, et les 10 séances défilent
    prev, seen = None, {t: set() for t in ("push", "pull", "legs")}
    for k in range(30):
        d = (T + timedelta(days=k)).isoformat()
        m = an.build_analysis(acts, days, d, cf.GOALS, cf.ATHLETE, cf.PERIODS)["suggest"]["muscu"]
        cur = {t: m["types"][t]["today_n"] for t in m["types"]}
        if prev: assert all(cur[t] != prev[t] for t in cur), (d, cur, prev)
        for t in cur: seen[t].add(cur[t])
        prev = cur
    assert all(len(v) == 10 for v in seen.values()), {t: len(v) for t, v in seen.items()}
    print("OK  musculation PPL : 30 séances / 158 exercices, durée 50-70 min, jambes allégées après grosse sortie vélo ou course,")
    print("    dos/pecs allégés après grosse natation ou même groupe < 48 h, 10 séances qui défilent sans répétition (30 jours)")


def test_periodes():
    """La note /20 et les 5 piliers sont calculés par période (1S, 1M, 3M) et évoluent avec elle."""
    acts, days = world("fatigue", 1)
    A = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
    sc = {p: A["pillars_p"][p]["score"] for p in cf.PERIODS}
    assert all(v is not None for v in sc.values()) and len({round(v, 1) for v in sc.values()}) == 3, sc
    assert sc["1S"] < sc["3M"], sc          # semaine de fatigue : la note de la semaine est plus basse que celle du trimestre
    print("OK  note /20 par période : " + " · ".join(f"{p} {sc[p]:.1f}" for p in sc) + " (fatigue récente : 1 sem. < 3 mois)")


def test_rotation():
    """La musculation suit la rotation Push -> Pull -> Legs, reporte les jambes si elles sont chargées, et aucune discipline
    ne propose deux jours de suite la même séance."""
    acts, days = world("optimale", 1)
    # historique : push puis pull, jambes disponibles -> prochaine = legs
    base = [a for a in acts if a["s"] != "strength"]
    hist = [act(9, "strength", 0, 55, 60, "Pectoraux épaules"), act(5, "strength", 0, 55, 60, "Dos biceps")]
    sess = [a for a in base + hist if a["d"] <= iso(3)]       # aucune contrainte jambes récente
    st = an.physio_state(sess, days, T, cf.ATHLETE, 40.0)
    nxt, skipped, (seen, generic) = an.strength_plan(sess, T, st["recent"], "maintien")
    assert nxt == "legs" and not skipped and seen == ["push", "pull"], (nxt, skipped, seen)
    # jambes chargées hier -> report, haut du corps
    sess2 = sess + [act(1, "run", 15.0, 80, 120, "Nice - sortie 15 km")]
    st2 = an.physio_state(sess2, days, T, cf.ATHLETE, 40.0)
    nxt2, skipped2, _ = an.strength_plan(sess2, T, st2["recent"], "maintien")
    assert nxt2 in ("push", "pull") and skipped2, (nxt2, skipped2)
    # séances au nom générique : la rotation avance quand même
    gen = [act(9, "strength", 0, 55, 60, "Pectoraux épaules"), act(6, "strength", 0, 55, 60, "Musculation"), act(3, "strength", 0, 55, 60, "Musculation")]
    n3, _, (s3, g3) = an.strength_plan([a for a in base if a["d"] <= iso(3)] + gen, T, st["recent"], "maintien")
    assert s3 == ["push"] and g3 == 2 and n3 == "push", (n3, s3, g3)      # push -> (pull) -> (legs) -> push
    # variété : jamais deux jours de suite la même séance, pour chaque discipline
    prev = None
    for k in range(30):
        d = (T + timedelta(days=k)).isoformat()
        A = an.build_analysis(acts, days, d, cf.GOALS, cf.ATHLETE, cf.PERIODS)
        cur = {c["id"]: c["title"] for c in A["suggest"]["cards"]}
        if prev: assert all(cur[i] != prev[i] for i in cur), (d, [i for i in cur if cur[i] == prev[i]], cur)
        prev = cur
    print("OK  rotation Push/Pull/Legs, report des jambes, noms génériques, aucune séance répétée deux jours de suite (30 jours)")

def test_fiabilite():
    """Fraîcheur des données, bandeau d'alerte, recalage des seuils, fiabilité des prédictions, repères, garde-fous de la synchro."""
    import json, tempfile, gzip
    from pathlib import Path
    import sync_garmin as sg, garmin_data as gd
    acts, days = world("optimale", 1)
    # 1) fraîcheur : données à jour -> pas d'alerte ; données vieilles de 3 jours -> warn ; 6 jours -> alert ; synchro incomplète -> warn
    A = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
    assert A["fresh"]["level"] is None, A["fresh"]
    d3 = (T + timedelta(days=3)).isoformat(); d6 = (T + timedelta(days=6)).isoformat()
    assert an.build_analysis(acts, days, d3, cf.GOALS, cf.ATHLETE, cf.PERIODS)["fresh"]["level"] == "warn"
    assert an.build_analysis(acts, days, d6, cf.GOALS, cf.ATHLETE, cf.PERIODS)["fresh"]["level"] == "alert"
    Am = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS, meta={"ok": False, "reason": "test", "synced_at": TODAY + "T04:00:00Z"})
    assert Am["fresh"]["level"] == "warn" and "incomplète" in Am["fresh"]["message"]
    assert an.build_analysis([], {}, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)["fresh"]["level"] == "alert"
    # le coach parle de la montre quand les données sont datées
    assert any(w in Am["bilan"]["1S"]["text"].lower() for w in ("montre", "synchro", "donnée")) and Am["bilan"]["1S"]["text"] != A["bilan"]["1S"]["text"]
    # 2) recalage des seuils : déterministe, remis à zéro à chaque génération, borné
    a1 = an.calibrate(days, T); th1 = dict(an.TH)
    a2 = an.calibrate(days, T); assert th1 == dict(an.TH) and a1["lines"] == a2["lines"]
    assert 0.88 <= an.TH["hrv_lo"] <= 0.95 and an.TH["hrv_vlo"] <= an.TH["hrv_lo"] - 0.03 + 1e-9 and 1.02 <= an.TH["hrv_hi"] <= 1.08
    assert an.calibrate({}, T)["calibrated"] is False and an.TH == an.TH_DEFAULT
    # 3) fiabilité des prédictions : une course simulée (10 km nommé « Course ») 20 jours avant la date, avec assez d'historique
    acts2 = list(acts) + [act(20, "run", 10.0, 44.0, 120, "Course 10 km", te=4.5, hr=172)]
    pc = an.prediction_check(acts2, T, cf.GOALS)
    assert pc["n"] >= 1 and pc["items"][-1]["label"] == "10 km" and pc["bias"] is not None and pc["note"]
    assert an.prediction_check(acts, T, cf.GOALS)["n"] >= 0
    assert an.prediction_check([], T, cf.GOALS)["n"] == 0
    ev = an.build_events([{"date": iso(5), "label": "Vacances", "kind": "vacances"}, {"date": "pas une date"}, {"date": iso(900), "label": "trop vieux"}], pc, T)
    assert [e["kind"] for e in ev].count("vacances") == 1 and any(e["kind"] == "course" for e in ev) and all(e["label"] != "trop vieux" for e in ev)
    Ae = an.build_analysis(acts2, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS, events=[{"date": iso(5), "label": "Vacances", "kind": "vacances"}])
    assert Ae["events"] and Ae["pred_check"]["n"] >= 1
    # 4) garde-fous de la synchronisation Garmin
    full = [{"date": iso(i), "stats": {"restingHeartRate": 50}, "sleep": {"x": 1}, "hrv": None, "body_battery": None, "stress": None, "training_readiness": None} for i in range(10)]
    empty = [{"date": iso(i), "stats": None, "sleep": None, "hrv": None, "body_battery": None, "stress": None, "training_readiness": None} for i in range(10)]
    acts_ok = [{"activityName": "Run", "startTimeLocal": iso(i) + " 07:00:00", "duration": 3000, "distance": 8000, "activityType": {"typeKey": "running"}} for i in range(4)]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "garmin"
        sg.write_files_sink(acts_ok, full, out)
        st = json.loads((out / "sync_status.json").read_text()); assert st["ok"] and not st["kept_previous"]
        good = (out / "data.json").read_text()
        note = (out / "daily" / f"{iso(0)}.md").read_text()
        sg.write_files_sink([], empty, out)                       # synchro vide : ne doit rien écraser
        st = json.loads((out / "sync_status.json").read_text())
        assert st["ok"] is False and st["kept_previous"] and "précédemment" in st["reason"] or "activité" in st["reason"], st
        assert (out / "data.json").read_text() == good and (out / "daily" / f"{iso(0)}.md").read_text() == note
        assert list((out / "backup").glob("data-*.json.gz")), "sauvegarde hebdomadaire manquante"
        assert json.loads(gzip.decompress(next((out / "backup").glob("*.gz")).read_bytes()))["wellness"]
        acts_l, days_l, _ = gd.load_all(out)                      # sync_status.json et sauvegardes ne sont pas lues comme des données
        assert len(acts_l) >= 1 and days_l
    # 5) synchro courte (3 jours) : fusion avec l'historique, jamais d'écrasement
    import sync_garmin as sg, tempfile, pathlib
    od = pathlib.Path(tempfile.mkdtemp()) / "g"
    hist = [{"date": iso(i), "stats": {"restingHeartRate": 50 + i}, "sleep": {"x": 1}, "hrv": None, "body_battery": None, "stress": None, "training_readiness": None} for i in range(30)]
    sg.write_files_sink([{"activityId": i, "startTimeLocal": iso(i) + " 07:00:00", "activityName": "Run"} for i in range(0, 30, 2)], hist, od)
    short = [{"date": iso(i), "stats": {"restingHeartRate": 99}, "sleep": {"x": 1}, "hrv": None, "body_battery": None, "stress": None, "training_readiness": None} for i in range(3)]
    sg.write_files_sink([{"activityId": 0, "startTimeLocal": iso(0) + " 07:00:00", "activityName": "Run"}], short, od)
    dd = json.loads((od / "data.json").read_text())
    assert len(dd["wellness"]) == 30 and dd["wellness"][0]["stats"]["restingHeartRate"] == 99 and dd["wellness"][10]["stats"]["restingHeartRate"] == 60
    assert len(dd["activities"]) == 15, len(dd["activities"])
    print("OK  fiabilité : alertes de données datées, seuils recalés (bornés, déterministes), contrôle des prédictions, repères, synchro protégée (sauvegarde + refus d'écraser)")


def test_bilan():
    """Bibliothèque « Le mot du coach » : syntaxe des phrases, scénarios, ton, fenêtres, déterminisme, robustesse."""
    import string, bilan_bank as BB
    # 1) toutes les phrases : variables autorisées uniquement, non vides
    n_tpl = 0
    def walk(name, b):
        nonlocal n_tpl
        if isinstance(b, dict):
            for k, v in b.items(): walk(name, v)
        else:
            for tpl in b:
                n_tpl += 1
                f = {x for _, x, _, _ in string.Formatter().parse(tpl) if x}
                assert tpl.strip() and f <= BB.ALLOWED[name], (name, tpl, f - BB.ALLOWED[name])
    for name, b in (("STALE", BB.STALE), ("ASIDE", BB.ASIDE), ("GREET", BB.GREET), ("TRANS", BB.TRANS), ("JOKE", BB.JOKE), ("OPENER", BB.OPENER), ("STRONG", BB.STRONG), ("WEAK", BB.WEAK), ("BALANCED", BB.BALANCED), ("BEST_LOW", BB.BEST_LOW),
                    ("WORST_HIGH", BB.WORST_HIGH), ("GOAL", BB.GOAL), ("STATE", BB.STATE), ("MOD", BB.MOD), ("CLOSER", BB.CLOSER),
                    ("TREND", BB.TREND), ("COUNT", BB.COUNT)):
        walk(name, b)
    assert n_tpl == sum(BB.library_size().values()) and n_tpl >= 850, n_tpl
    assert set(BB.GREET) == {"lo", "mid", "hi", "ko"} and set(BB.JOKE) == set(BB.CLOSER) and set(BB.TRANS) == {"pilier", "goal", "state", "closer"}
    assert set(BB.OPENER) == {"tres_bas", "bas", "moyen", "bon", "tres_bon", "elite"}
    assert set(BB.STATE) == set(PB_PROFILES()), "un profil sans phrases d'état"
    assert {f"{a}_{b}" for a in ("hi", "mid", "lo") for b in ("ok", "ko", "neutral")} == set(BB.CLOSER)
    assert set(BB.STRONG) == {"pred", "run", "load", "rec", "cross"} and set(BB.WEAK) == {"pred", "run", "load_low", "load_high", "rec", "cross"}
    # 2) textes générés sur les 4 scénarios x 3 périodes : propres, adaptés à la fenêtre, sans insulte quand l'état est mauvais
    bad_words = ("n/a", "None", " nan", "{", "}", " ,", ",,", " .", "  ")
    for kind in ("optimale", "fatigue", "surcharge", "manquantes"):
        acts, days = world(kind, 1)
        A = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
        texts = {}
        for p in cf.PERIODS:
            b = A["bilan"][p]
            assert not b.get("error") and b["text"], (kind, p, b.get("error"))
            for w in bad_words: assert w not in b["text"], (kind, p, w, b["text"])
            assert b["text"][-1] in ".!?…", b["text"][-30:]
            assert 30 <= len(b["text"].split()) <= 260, len(b["text"].split())
            if A["coach"]["profile"] in BB.NO_INSULT_PROFILES:
                for w in BB.INS: assert w not in b["text"], (kind, p, w)
            texts[p] = b["text"]
        assert len(set(texts.values())) == 3, "le paragraphe doit changer avec la période"
        assert all(BB.WIN[p] in texts[p] for p in cf.PERIODS), f"fenêtre non rappelée dans le texte ({kind})"
    # 3) déterminisme et variété sur 30 jours
    acts, days = world("optimale", 1)
    A1 = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
    A2 = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS)
    assert A1["bilan"] == A2["bilan"]
    var = {an.bilan_text("1M", 30, A1["pillars_p"]["1M"], an.physio_state(acts, days, T, cf.ATHLETE, 0), an.period_stats(acts, days, T, 30), None, cf.GOALS, T, (T + timedelta(days=k)).isoformat())["text"] for k in range(30)}
    assert len(var) >= 28, len(var)
    # 3 bis) rotation : pas de répétition rapprochée pour un scénario stable (aucune variante ne revient avant épuisement de la banque)
    sigr = {"score": 12.0, "profile": "maintien", "load_dir": "low", "trend": "up", "days_to_race": 80, "mod": "hrv_low",
            "pillars": {k: {"score": (3.4 if k == "run" else 1.2 if k == "cross" else 2.2), "name": k} for k in ("pred", "run", "load", "rec", "cross")},
            "pillar_vars": {k: {"kmw": "30,0", "long_km": "20,0", "acwr": "1,10", "sleep_h": "7,0", "hrv_pct": "+3 %", "sw": "1,0", "cw": "1,0", "glabel": "10 km", "gret": "42'00", "gtarget": "41'00"} for k in ("pred", "run", "load", "rec", "cross")},
            "goal": {"ret": 102.0, "target": 100.0, "glabel": "10 km", "gret": "42'00", "gtarget": "41'00", "ggap": "0'40", "gpct": "2"},
            "vars": {"strain": 40, "faf": "0,9", "hrv_pct": "+2 %", "sleep_score": "80", "sleep_h": "7,5", "acwr": "1,10", "bb": "70", "dkm": "12", "hrv_pct_p": "-5 %", "rlabel": "Marathon"}}
    for blk, n_expect in (("OPENER", 14), ("STATE", 11), ("JOKE", 11), ("CLOSER", 10)):
        seen = [next(p[2] for p in BB.compose(sigr, (T + timedelta(days=k)).isoformat(), "1M")["parts"] if p[0] == blk) for k in range(n_expect)]
        assert len(set(seen)) == n_expect, (blk, n_expect, len(set(seen)))
    greets = [BB.compose(sigr, (T + timedelta(days=k)).isoformat(), "1M")["parts"][0][2] for k in range(14)]
    assert len(set(greets)) >= 13, len(set(greets))
    paras = {BB.compose(sigr, (T + timedelta(days=k)).isoformat(), "1M")["text"] for k in range(60)}
    assert len(paras) == 60
    assert len({BB.compose(sigr, TODAY, k)["text"] for k in ("1S", "1M", "3M")}) == 3     # 3 périodes le même jour : 3 textes différents
    # 4) balayage synthétique : toutes les combinaisons de scénarios composent sans erreur
    count = 0
    pk = ("pred", "run", "load", "rec", "cross")
    for sc_ in (2, 6, 8, 11, 13.5, 15, 17, 19):
        for prof in PB_PROFILES():
            for ld in ("low", "high"):
                for tr in (None, "up", "down", "flat"):
                    for gp in (None, 0.95, 1.02, 1.06, 1.2):
                        for best, worst in (("pred", "cross"), ("run", "rec"), ("load", "run"), ("rec", "pred"), ("cross", "load")):
                            sig = {"score": sc_, "profile": prof, "load_dir": ld, "trend": tr, "days_to_race": 100 if tr else None, "mod": None,
                                   "pillars": {k: {"score": (3.8 if k == best else 0.4 if k == worst else 2.0), "name": k} for k in pk},
                                   "pillar_vars": {k: {"kmw": "30,0", "long_km": "20,0", "acwr": "1,10", "sleep_h": "7,0", "hrv_pct": "+3 %", "sw": "1,0", "cw": "1,0",
                                                       "glabel": "10 km", "gret": "42'00", "gtarget": "41'00"} for k in pk},
                                   "goal": {} if gp is None else {"ret": 100 * gp, "target": 100, "glabel": "10 km", "gret": "42'00", "gtarget": "41'00", "ggap": "0'40", "gpct": "2"},
                                   "vars": {"strain": 40, "faf": "0,9", "hrv_pct": "+2 %", "sleep_score": "80", "sleep_h": "7,5", "acwr": "1,10", "bb": "70", "dkm": "12",
                                            "sleep_debt": "2,0", "hrv_pct_p": "-5 %", "stress": "55", "rlabel": "Marathon"}}
                            r = BB.compose(sig, TODAY, "1M")
                            assert r["text"] and "{" not in r["text"] and "n/a" not in r["text"], r
                            if prof in BB.NO_INSULT_PROFILES:
                                for w in BB.INS: assert w not in r["text"], (prof, w)
                            count += 1
    for m in BB.MOD:
        r = BB.compose({"score": 12, "profile": "maintien", "mod": m, "pillars": {}, "vars": {"sleep_debt": "2,0", "hrv_pct_p": "-5 %", "stress": "55", "bb": "50"}}, TODAY, "1S")
        assert r["text"]
    # 5) robustesse : signaux vides / données manquantes
    r = BB.compose({}, TODAY, "3M"); assert r["text"] and "{" not in r["text"]
    r = BB.compose({"score": None, "profile": None}, TODAY, "1S"); assert r["text"]
    # 6) nombre de textes possibles sur un parcours typique (pools réels)
    sz = [len(BB.OPENER["bon"]), len(BB.STRONG["pred"]), len(BB.WEAK["load_low"]), len(BB.GOAL["close"]), len(BB.STATE["maintien"]),
          len(BB.MOD["hrv_low"]), len(BB.CLOSER["mid_neutral"]), len(BB.TREND["up"])]
    typ = 1
    for x in sz: typ *= x
    typ *= len(BB.NICK) ** 3
    print(f"OK  mot du coach : {n_tpl} phrases, {len(BB.NICK)} surnoms, {len(BB.INS)} insultes ; {count} scénarios synthétiques sans erreur ; "
          f"~{typ:,} paragraphes possibles sur un parcours type".replace(",", " "))


def PB_PROFILES():
    import phrases_bank as PB
    return list(PB.PROFILE_LABEL)


def test_objectifs():
    import goals as G, json, tempfile, pathlib
    g = G.from_config(cf.GOALS)
    assert len(g) == 3 and [x["date"] for x in g] == sorted(x["date"] for x in g), "objectifs : défauts repris de config (3, triés par date)"
    assert {x["id"] for x in g} >= {"10k", "marathon"}, "objectifs : ids 10k / marathon conservés"
    assert G.parse_time("3h15") == G.parse_time("3:15:00") == 11700 and G.parse_time("") is None and G.parse_time("abc") is None, "temps : 3h15 = 3:15:00 = 11700 s"
    w = []
    n = G.normalize([{"sport": "trail", "name": "B", "dist": "20,5", "target": "", "date": "2027-03-01"}, {"sport": "run", "name": "A", "dist": 10, "target": "0:45:00", "date": "2027-01-01"},
                     {"name": "", "dist": 5, "date": "2027-01-01"}, {"name": "X", "dist": "oups", "date": "2027-01-01"}, {"name": "Y", "dist": 5, "date": "pas-une-date"}], w)
    assert [x["label"] for x in n] == ["A", "B"] and len(w) == 3, "objectifs : tri chronologique + entrées invalides ignorées"
    d = pathlib.Path(tempfile.mkdtemp())
    assert G.load_goals(d, cf.GOALS)[2] == "config.py", "objectifs : sans fichier -> config.py"
    (d / "objectifs.json").write_text(G.to_file_json(n), encoding="utf-8")
    L = G.load_goals(d, cf.GOALS)
    assert L[2] == "objectifs.json" and len(L[0]) == 2 and L[0][0]["target_s"] == 2700, "objectifs : lecture de objectifs.json"
    (d / "objectifs.json").write_text("{pas du json", encoding="utf-8")
    assert G.load_goals(d, cf.GOALS)[2] == "config.py" and G.load_goals(d, cf.GOALS)[1], "objectifs : fichier corrompu -> repli sur config"
    A = an.build_analysis([], {}, TODAY, n, cf.ATHLETE, cf.PERIODS); check_structure(A, "objectifs triathlon/trail")
    mix = G.normalize([{"sport": "triathlon", "name": "Tri L", "format": "l", "date": "2027-06-01", "target": "5:30"}, {"sport": "triathlon", "name": "Perso", "format": "custom", "swim": 2, "bike": 100, "run": 15, "bike_elev": 900, "date": "2027-07-01"},
                       {"sport": "bike", "name": "Fondo", "dist": 120, "elev": 2500, "date": "2027-05-01", "target": "4:30"}, {"sport": "swim", "name": "Traversée", "dist": 3, "date": "2027-08-01"}, {"sport": "run", "name": "10 km", "dist": 10, "date": "2027-01-24", "target": "42:00"}])
    assert [x["sport"] for x in mix] == ["run", "bike", "triathlon", "triathlon", "swim"]
    tl = next(x for x in mix if x["name"] == "Tri L")
    assert tl["format"] == "l" and abs(tl["dist"] - 113.0) < 0.01 and tl["target_s"] == 19800
    assert next(x for x in mix if x["name"] == "Fondo")["target_s"] == 16200 and next(x for x in mix if x["name"] == "Perso")["bike_elev"] == 900
    assert G.normalize(json.loads(G.to_file_json(mix))["goals"]) == mix, "aller-retour fichier"
    A2 = an.build_analysis([], {}, TODAY, mix, cf.ATHLETE, cf.PERIODS); check_structure(A2, "objectifs multi-sports")
    assert all(g["pred"] is None for g in A2["goals"] if g["sport"] != "run")
    print("OK  objectifs : lecture, tri, validation, repli, 5 sports (triathlon XS-XL / personnalisé)")

def main():
    ok = True
    print(f"{'scénario':<11} {'profil':<24} {'strain':>6} {'FAF':>5}  séances recommandées")
    for kind, (prof, (lo, hi)) in EXPECT.items():
        A = build(kind)
        check_structure(A, kind)
        c = A["coach"]
        rec = " + ".join(f"{x['cat']} : {x['title']} ({x['meta']})" for x in A["suggest"]["cards"] if x["rec"])
        flag = "OK " if (c["profile"] == prof and lo <= c["faf"] <= hi) else "KO "
        ok &= flag == "OK "
        print(f"{flag}{kind:<8} {c['profile']:<24} {str(c['strain_index']):>6} {c['faf']:>5.2f}  {rec}")
        print(f"            attendu : {prof}, FAF dans [{lo}, {hi}] ; plafonds : {[x['name'] for x in c['caps']] or 'aucun'}")
    # déterminisme : mêmes données et même date -> même sortie
    a = json.dumps(build("optimale"), default=str, sort_keys=True); b = json.dumps(build("optimale"), default=str, sort_keys=True)
    print("OK " if a == b else "KO ", "déterminisme : deux exécutions identiques")
    ok &= a == b
    # la date change le choix de séance (variété) sans changer le diagnostic
    acts, days = world("optimale", 1)
    titles = set()
    for k in range(6):
        d2 = (T + timedelta(days=0)).isoformat()
        A = an.build_analysis(acts, days, d2, cf.GOALS, cf.ATHLETE, cf.PERIODS)
        titles.add(tuple(c["title"] for c in A["suggest"]["cards"]))
        # décale seulement le sel par la date (simulation) : on appelle la sélection sur d'autres dates
        break
    import phrases_bank as PB
    variants = {PB.pick(PB.DIAG["forme_optimale"]["head"], (T + timedelta(days=k)).isoformat(), "diag.head", {"strain_index": 12, "hrv_val": "85", "hrv_baseline": "80", "hrv_pct": "+6 %", "acwr": "1,05", "sleep_score": "88", "body_battery": "90", "faf": "1,10", "stress_avg": "25", "load_7d": "400"}) for k in range(30)}
    print("OK " if len(variants) >= 6 else "KO ", f"variété des phrases : {len(variants)} variantes distinctes sur 30 jours")
    ok &= len(variants) >= 6
    # données manquantes : aucune exception avec des jeux partiels
    for drop in ("hrv", "sc", "deep", "rem", "bbx", "st", "tr"):
        acts, days = world("optimale", 1)
        for d in days.values(): d.pop(drop, None)
        A = an.build_analysis(acts, days, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS); check_structure(A, f"sans {drop}")
    A = an.build_analysis([], {}, TODAY, cf.GOALS, cf.ATHLETE, cf.PERIODS); check_structure(A, "vide")
    print("OK  robustesse : jeux partiels (sans VFC, sommeil, phases, Body Battery, stress, readiness) et jeu vide")
    test_rotation()
    test_muscu()
    test_periodes()
    test_bilan()
    test_fiabilite()
    test_objectifs()
    import test_planification, test_robustesse
    plan_ok = test_planification.main()
    rob_ok = test_robustesse.main()
    ok = ok and plan_ok and rob_ok
    print("\nRÉSULTAT :", "tous les tests passent" if ok else "ÉCHEC")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
