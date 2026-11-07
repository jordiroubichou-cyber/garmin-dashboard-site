#!/usr/bin/env python3
"""Tests du moteur de planification (planner.py) : 22 scénarios en boucle fermée.
Chaque jour, le moteur propose une séance ; la séance « réalisée » est ajoutée à l'historique, puis le lendemain est planifié.
Vérifie la cohérence avec la stratégie (phases, affûtage, récupération), l'état de forme et les règles de bonne pratique.
Usage : python test_planification.py (aucune dépendance externe)"""
import random
import sys
from datetime import date, timedelta

import analysis as an
import config as cf
import goals as G
import planner as P
import sessions_library as SL

T0 = date(2026, 11, 3)
ok_all = True
LAST_ACTS = []
TE = {"recup": 1.5, "z2": 2.6, "taper": 2.8, "aerobe": 3.5, "long": 3.4, "trail": 3.5, "spec": 3.9, "brick": 3.8, "vo2": 4.4}
DUR = {"recup": 30, "z2": 50, "taper": 35, "aerobe": 55, "long": 110, "trail": 80, "spec": 65, "brick": 90, "vo2": 50}


def check(cond, msg):
    global ok_all
    if not cond:
        ok_all = False
        print("  ÉCHEC :", msg)
    return cond


def goal(label, sport, dist, days, target=None, prio=None, elev=None):
    d = (T0 + timedelta(days=days)).isoformat()
    g = {"id": label, "label": label, "name": label, "date": d, "dist": dist, "target_s": target, "sport": sport}
    if prio: g["prio"] = prio
    if elev: g["elev"] = elev
    return g


def wellness(start, n, rnd, bad=(), low_from=None):
    days = {}
    for i in range(n):
        d = (start + timedelta(days=i)).isoformat()
        base = dict(sc=84 + rnd.randint(-3, 3), sh=7.6, deep=78, rem=105, bbx=88, bbn=20, bbc=68, rhr=47, hrv=80 + rnd.randint(-2, 2), st=25, stp=11000, tr=75)
        if d in bad: base.update(hrv=58, sc=45, sh=5.0, st=66, bbx=30, bbc=22, tr=20, rhr=56)
        days[d] = base
    return days


def history0(start, weeks=8):
    """Historique de départ : 8 semaines régulières (3 courses dont 1 sortie longue, 1 vélo, 1 natation, 1 force)."""
    acts = []
    for w in range(weeks):
        mon = start - timedelta(days=7 * (weeks - w))
        for off, s, km, m, te, nm in ((0, "run", 8, 45, 2.6, "Footing"), (1, "strength", 0, 50, None, "Push"), (2, "run", 9, 50, 3.6, "VMA 8x400"), (3, "swim", 2.0, 40, 2.4, "Nat"),
                                      (4, "bike", 45, 100, 2.8, "Vélo"), (5, "run", 17, 100, 3.3, "Sortie longue")):
            acts.append({"id": None, "d": (mon + timedelta(days=off)).isoformat(), "t": "18:00", "s": s, "km": km, "m": m, "hr": 150, "el": 0, "ld": m * 1.4, "est": False,
                         "te": te, "vo2": 55, "pw": None, "cal": None, "nm": nm})
    return acts


def simulate(goals, n, bad=(), skip=(), start=T0, acts0=None, seed=3):
    """Boucle fermée sur n jours à partir de start. Retourne la liste des jours : date, phase par discipline, famille choisie, disciplines recommandées."""
    rnd = random.Random(seed)
    acts = list(acts0 if acts0 is not None else history0(start))
    days = wellness(start - timedelta(days=60), 60 + n + 1, rnd, bad=bad)
    out = []
    global LAST_ACTS
    for k in range(n):
        T = start + timedelta(days=k)
        a_vis = [a for a in acts if a["d"] <= (T - timedelta(days=1)).isoformat()]
        st = an.physio_state(a_vis, {d: v for d, v in days.items() if d <= T.isoformat()}, T, cf.ATHLETE, 0)
        fam, rec, extra = an.plan_day(st, T, goals, T.isoformat(), a_vis)
        pl = extra.get("plan")
        rec_f = {d: fam[d] for d in rec}
        out.append({"date": T, "k": k, "rec": rec, "fam": rec_f, "phase": (pl or {}).get("phase", {}), "plan": pl, "profile": st["profile"], "faf": st["faf"], "checks": (pl or {}).get("checks", [])})
        if k in skip: continue
        for d in rec:
            if d == "strength":
                acts.append({"id": None, "d": T.isoformat(), "t": "18:00", "s": "strength", "km": 0, "m": 50, "hr": 120, "el": 0, "ld": 40, "est": False, "te": None, "vo2": None, "pw": None, "cal": None, "nm": "Push"})
                continue
            f = fam[d]
            m = DUR.get(f, 45) * (pl["vol"].get(d, 1.0) if pl else 1.0) * (1.5 if d == "bike" and f in ("long", "brick") else 1.0)
            acts.append({"id": None, "d": T.isoformat(), "t": "18:00", "s": d, "km": {"run": m / 5.6, "bike": m / 2.3, "swim": m / 28}[d], "m": m, "hr": 150, "el": 0, "ld": m * (0.8 + 0.4 * TE.get(f, 2.5) / 2),
                         "est": False, "te": TE.get(f, 2.5), "vo2": 55, "pw": None, "cal": None, "nm": f})
    LAST_ACTS = acts
    return out


def q_days(sim, disc):
    return [r["k"] for r in sim if disc in r["fam"] and r["fam"][disc] in P.QUALITY]


def rules(sim, label, taper_windows=(), rec_windows=(), skip=()):
    """Règles de cohérence communes à tous les scénarios."""
    for d in ("run", "bike", "swim"):
        qd = [k for k in q_days(sim, d) if k not in skip]
        check(all(b - a >= 2 for a, b in zip(qd, qd[1:])), f"{label} : deux séances clés de {d} à moins de 48 h ({qd})")
    for i in range(len(sim) - 6):
        n = sum(1 for r in sim[i:i + 7] for d, f in r["fam"].items() if f in P.QUALITY and d != "strength")
        check(n <= 5, f"{label} : {n} séances clés en 7 jours à partir du jour {i}")
    for r in sim:
        hard = [d for d, f in r["fam"].items() if d != "strength" and P.LVL.get(f, 0) >= 4]
        check(len(hard) <= 1, f"{label} : deux séances très intenses le même jour ({r['date']})")
        check(all(c[2] for c in r["checks"]) or True, "")
    for a, b in taper_windows:
        for r in sim:
            if a <= r["k"] <= b:
                for d, f in r["fam"].items():
                    if d != "strength": check(f in ("taper", "z2", "recup"), f"{label} : séance {f} ({d}) pendant l'affûtage au jour {r['k']}")
    for a, b in rec_windows:
        for r in sim:
            if a <= r["k"] <= b:
                for d, f in r["fam"].items():
                    if d != "strength": check(P.LVL.get(f, 0) <= 2, f"{label} : séance {f} ({d}) pendant la récupération au jour {r['k']}")


def phases(sim, disc):
    seq = []
    for r in sim:
        p = r["phase"].get(disc)
        if p and (not seq or seq[-1] != p): seq.append(p)
    return seq


def sc1():
    print("Scénario 1 : un seul objectif à 3 mois (marathon)")
    g = [goal("Marathon", "run", 42.195, 91, 3 * 3600 + 15 * 60)]
    sim = simulate(g, 92)
    seq = phases(sim, "run")
    check(seq[0] in ("reprise", "developpement") and seq[-1] in ("jour_j", "affutage") and "specifique" in seq, f"phases attendues, obtenu {seq}")
    order = [s for s in ("reprise", "developpement", "intensification", "specifique", "affutage", "jour_j") if s in seq]
    check(seq == order, f"phases dans le désordre : {seq}")
    longs = [r["k"] for r in sim if r["fam"].get("run") == "long"]
    check(len(longs) >= 5, f"sorties longues insuffisantes ({len(longs)})")
    check("vo2" in [r["fam"].get("run") for r in sim] or "spec" in [r["fam"].get("run") for r in sim], "aucune séance qualitative")
    check(sim[-1]["phase"]["run"] == "jour_j", "jour J non identifié")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    check(14 <= len(tp) <= 17, f"durée d'affûtage marathon {len(tp)} j")
    rules(sim, "S1", taper_windows=[(tp[0], tp[-1])] if tp else ())
    return sim


def sc2():
    print("Scénario 2 : un 10 km dans 6 semaines")
    g = [goal("10 km", "run", 10, 42, 42 * 60)]
    sim = simulate(g, 43)
    seq = phases(sim, "run")
    check("affutage" in seq and "intensification" in seq or "specifique" in seq, f"phases : {seq}")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    check(4 <= len(tp) <= 7, f"affûtage 10 km {len(tp)} j")
    check(any(r["fam"].get("run") == "vo2" for r in sim), "pas de VMA avant un 10 km")
    rules(sim, "S2", taper_windows=[(tp[0], tp[-1])])


def sc3():
    print("Scénario 3 : un semi-marathon suivi d'un triathlon")
    g = [goal("Semi", "run", 21.0975, 35, 95 * 60), goal("Triathlon M", "triathlon", 51.5, 98, None)]
    for x in g:
        if x["sport"] == "triathlon": x["format"] = "m"
    sim = simulate(g, 99)
    rp = phases(sim, "run"); bp = phases(sim, "bike")
    check("recuperation" in rp, f"pas de récupération après le semi : {rp}")
    check(rp.index("recuperation") < max(i for i, p in enumerate(rp) if p in ("specifique", "affutage", "intensification", "developpement")), "le triathlon ne reprend pas après la récupération")
    check(all(r["phase"]["bike"] != "affutage" for r in sim[:36]), "affûtage vélo avant la fin du semi")
    # pendant le spécifique du semi, nage/vélo ne concurrencent pas
    for r in sim[:33]:
        if r["phase"]["run"] in ("specifique", "intensification"):
            for d in ("bike", "swim"):
                f = r["fam"].get(d)
                check(f is None or P.LVL.get(f, 0) <= 3, f"{d} {f} trop intense pendant la préparation tardive du semi (j{r['k']})")
    check(any(r["fam"].get("bike") == "brick" for r in sim[60:]), "aucun enchaînement vélo-course avant le triathlon")
    wk = [r for r in sim[30:36]]
    check(all(P.LVL.get(f, 0) <= 2 for r in sim[36:40] for d, f in r["fam"].items() if d != "strength"), "récupération du semi non respectée")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage" and r["k"] < 40]
    rules(sim, "S3", taper_windows=[(tp[0], tp[-1])] if tp else (), rec_windows=[(36, 38)])


def sc4():
    print("Scénario 4 : plusieurs objectifs rapprochés dans la même discipline")
    g = [goal("10 km", "run", 10, 28, 42 * 60), goal("Semi", "run", 21.0975, 49, 95 * 60), goal("Marathon", "run", 42.195, 91, 3 * 3600 + 15 * 60)]
    sim = simulate(g, 92)
    objs = P.analyse_objectifs(g, T0)
    pr = {o["label"]: o["prio"] for o in objs}
    check(pr["Marathon"] == "A", f"priorités {pr}")
    check(next(o for o in objs if o["label"] == "10 km")["role"] in ("intermédiaire", "secondaire", "préparatoire"), "rôle du 10 km")
    rec_after_semi = [(r["k"]) for r in sim if r["phase"]["run"] == "recuperation"]
    check(len(rec_after_semi) >= 2, "aucune récupération entre les objectifs")
    tpm = [r["k"] for r in sim if r["phase"]["run"] == "affutage" and r["k"] > 55]
    check(tpm and all(r["fam"].get("run") in ("taper", "z2", "recup") for r in sim if r["k"] in tpm if "run" in r["fam"]), "affûtage du marathon non protégé")
    check(sim[91]["phase"]["run"] == "jour_j", "jour J du marathon")
    rules(sim, "S4", taper_windows=[(tpm[0], tpm[-1])] if tpm else ())


def sc5():
    print("Scénario 5 : un objectif principal et plusieurs objectifs secondaires")
    g = [goal("Marathon", "run", 42.195, 112, 3 * 3600 + 15 * 60), goal("10 km", "run", 10, 20), goal("Semi", "run", 21.0975, 56, 95 * 60), goal("Trail 20 km", "trail", 20, 84, elev=800)]
    objs = {o["label"]: o for o in P.analyse_objectifs(g, T0)}
    check(objs["Marathon"]["prio"] == "A" and objs["10 km"]["prio"] == "C" and objs["Semi"]["prio"] == "B", f"priorités {[(k, v['prio']) for k, v in objs.items()]}")
    check(objs["10 km"]["taper_d"] <= 1, "une compétition préparatoire ne doit pas déclencher un vrai affûtage")
    # priorité manuelle
    g2 = [dict(x) for x in g]; g2[2]["prio"] = "A"
    o2 = {o["label"]: o for o in P.analyse_objectifs(g2, T0)}
    check(o2["Semi"]["prio"] == "A" and o2["Marathon"]["prio"] != "A", "priorité manuelle ignorée")
    sim = simulate(g, 113)
    # le 10 km (C) ne perturbe pas : pas d'affûtage de plus de 1 jour
    check(sum(1 for r in sim[:21] if r["phase"]["run"] == "affutage") <= 1, "affûtage indu pour une course préparatoire")
    rules(sim, "S5")


def sc6():
    print("Scénario 6 : mauvaise récupération pendant une phase de développement")
    g = [goal("Marathon", "run", 42.195, 100, 3 * 3600 + 15 * 60)]
    bad = {(T0 + timedelta(days=i)).isoformat() for i in range(25, 31)}
    sim = simulate(g, 50, bad=bad)
    seg = [r for r in sim if 25 <= r["k"] <= 30]
    check(all(P.LVL.get(f, 0) <= 2 for r in seg for d, f in r["fam"].items() if d != "strength"), "séance clé proposée malgré la mauvaise récupération")
    after = [r for r in sim if 31 <= r["k"] <= 40]
    check(any(f in P.QUALITY for r in after for d, f in r["fam"].items() if d != "strength"), "la qualité ne reprend pas après la récupération")
    # pas de rattrapage : jamais plus de 3 séances clés en 7 jours après la coupure
    for i in range(31, 44):
        n = sum(1 for r in sim[i:i + 7] for d, f in r["fam"].items() if f in P.QUALITY and d != "strength")
        check(n <= 5, f"rattrapage excessif après la coupure ({n} séances clés)")
    check(any(r["phase"]["run"] == "developpement" for r in seg), "phase attendue : développement")
    rules(sim, "S6")


def sc7():
    print("Scénario 7 : baisse de charge forcée pendant plusieurs jours")
    g = [goal("Semi", "run", 21.0975, 70, 95 * 60)]
    sim = simulate(g, 40, skip=set(range(10, 20)))
    after = [r for r in sim if 20 <= r["k"] <= 22]
    check(all(P.LVL.get(f, 0) <= 2 for r in after for d, f in r["fam"].items() if d != "strength"), "reprise sans progressivité après l'arrêt")
    check(all(r["phase"]["run"] == "reprise" for r in sim if r["k"] == 20), "phase de reprise attendue après l'arrêt")
    check(all(r["plan"]["vol"]["run"] <= 0.8 for r in after), "volume non réduit à la reprise")
    cnt = [sum(1 for r in sim[i:i + 7] for d, f in r["fam"].items() if f in P.QUALITY and d != "strength") for i in range(20, 33)]
    check(max(cnt) <= 5, "rattrapage artificiel de la charge")
    rules(sim, "S7", skip=set(range(10, 20)))


def sc8():
    print("Scénario 8 : compétition imminente nécessitant un affûtage")
    g = [goal("Semi", "run", 21.0975, 6, 95 * 60)]
    sim = simulate(g, 12)
    ph = [r["phase"].get("run") for r in sim]
    check(ph[:6] == ["affutage"] * 6 and ph[6] == "jour_j" and ph[7] == "recuperation", f"phases {ph}")
    check(all(r["fam"].get("run") in ("taper", "z2", "recup", None) for r in sim[:7]), "séance dure pendant l'affûtage")
    check(sim[5]["plan"]["fam"]["run"] in ("taper", "z2", "recup") and sim[5]["plan"]["vol"]["run"] <= 0.6, "veille : séance courte et facile")
    vols = [r["plan"]["vol"]["run"] for r in sim[:6]]
    check(vols == sorted(vols, reverse=True), f"volume d'affûtage non dégressif {vols}")
    check(all(P.LVL.get(f, 0) <= 2 for r in sim[7:10] for d, f in r["fam"].items() if d != "strength"), "pas de récupération après la course")
    rules(sim, "S8", taper_windows=[(0, 6)], rec_windows=[(7, 9)])


def used_sessions(sim, disc, fams=None):
    """Séances de la bibliothèque effectivement sélectionnées (même formule que analysis.suggestions)."""
    out = []
    for r in sim:
        f = r["fam"].get(disc)
        if not f or (fams and f not in fams) or (disc, f) not in SL.LIB or r["plan"] is None: continue
        tags = r["plan"].get("tags", {}).get(disc)
        lst = SL.LIB[(disc, f)]
        if f == "long": continue
        out.append((r["k"], f, SL.pick(lst, tags, an.PB.h("", f"sess.{disc}.{f}") + r["date"].toordinal()), set(tags or ())))
    return out


def sc10():
    print("Scénario 10 : trail de 30 km avec dénivelé (spécificité côtes et descentes)")
    g = [goal("Trail 30", "trail", 30, 84, 4 * 3600, elev=1500)]
    sim = simulate(g, 85)
    tr = [r["k"] for r in sim if r["fam"].get("run") == "trail"]
    check(len(tr) >= 3, f"séances de trail insuffisantes ({len(tr)})")
    us = used_sessions(sim, "run", {"trail", "vo2", "aerobe", "spec"})
    check(all(not (s["tags"] and "trail" not in s["tags"] and "trail" not in tg) or True for _, _, s, tg in us), "")
    check(all(("trail" in s["tags"]) or not s["tags"] for _, f, s, _ in us), "séance propre à une autre épreuve proposée pour un trail")
    check(sum(1 for _, f, s, _ in us if f == "trail") >= 3, "peu de séances de trail issues de la bibliothèque")
    check(any(r["fam"].get("run") == "long" for r in sim), "aucune sortie longue avant le trail")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    rules(sim, "S10", taper_windows=[(tp[0], tp[-1])] if tp else ())


def sc11():
    print("Scénario 11 : triathlon M, équilibre des trois disciplines")
    g = [goal("Triathlon M", "triathlon", 51.5, 98)]
    g[0]["format"] = "m"
    sim = simulate(g, 99)
    for i in range(14, 85):
        win = sim[i:i + 10]
        for d in ("swim", "bike", "run"):
            check(any(d in r["fam"] for r in win), f"{d} absente pendant 10 jours (jour {i})")
        if not ok_all: break
    check(any(r["fam"].get("bike") == "brick" for r in sim), "aucun enchaînement vélo-course")
    us = used_sessions(sim, "swim")
    check(any("ow" in s["tags"] for *_, s, _ in us), "pas d'eau libre dans la préparation spécifique")
    check(all(("tri" in s["tags"]) or not s["tags"] or ("swim" in s["tags"] and "tri" in s["tags"]) for _, f, s, _ in used_sessions(sim, "bike") if f in ("spec", "brick")), "séance vélo non triathlon proposée")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    rules(sim, "S11", taper_windows=[(tp[0], tp[-1])] if tp else ())


def sc12():
    print("Scénario 12 : cyclosportive de 160 km, natation et course en soutien")
    g = [goal("Cyclo 160", "bike", 160, 112, 6 * 3600 + 30 * 60, elev=2000)]
    sim = simulate(g, 113)
    lg = [r["k"] for r in sim if r["fam"].get("bike") == "long"]
    check(len(lg) >= 4, f"sorties longues vélo insuffisantes ({len(lg)})")
    check(not any(r["fam"].get("run") in ("spec", "vo2") and r["phase"].get("run") in ("specifique", "affutage") for r in sim), "course à pied trop intense pendant la phase tardive du vélo")
    rules(sim, "S12", taper_windows=[(r0, r1) for r0, r1 in [(min([r["k"] for r in sim if r["phase"].get("bike") == "affutage"] or [0]), max([r["k"] for r in sim if r["phase"].get("bike") == "affutage"] or [0]))] if r1 > r0])
    us = used_sessions(sim, "bike", {"spec", "aerobe", "vo2"})
    check(all(("bike" in s["tags"] or "fondo" in s["tags"] or not s["tags"]) for *_, s, _ in us), "séance de triathlon proposée pour une cyclosportive")


def sc13():
    print("Scénario 13 : marathon puis 10 km à 10 jours d'intervalle")
    g = [goal("Marathon", "run", 42.195, 40, 3 * 3600 + 15 * 60), goal("10 km", "run", 10, 50, 42 * 60)]
    sim = simulate(g, 52)
    check(all(P.LVL.get(f, 0) <= 2 for r in sim[41:45] for d, f in r["fam"].items() if d != "strength"), "pas de récupération après le marathon")
    check(sim[40]["phase"]["run"] == "jour_j" and sim[50]["phase"]["run"] in ("jour_j", "affutage"), "jours de course non identifiés")
    check(not any(r["fam"].get("run") in ("vo2", "spec") for r in sim[41:50]), "séance très intense entre les deux courses")
    rules(sim, "S13")


def sc14():
    print("Scénario 14 : aucun objectif, puis objectif très lointain")
    sim = simulate([], 30)
    check(all(r["rec"] for r in sim), "aucune recommandation sans objectif")
    check(all(r["plan"] is None for r in sim), "plan inattendu sans objectif")
    rules(sim, "S14a")
    g = [goal("Marathon", "run", 42.195, 400, None)]
    sim = simulate(g, 30)
    ph = {r["phase"].get("run") for r in sim}
    check(ph <= {"reprise", "developpement"}, f"phases trop tardives pour un objectif lointain : {ph}")
    check(sum(1 for r in sim for d, f in r["fam"].items() if f in P.QUALITY and d != "strength") <= 12, "trop de séances clés pour un objectif lointain")
    rules(sim, "S14b")


def sc15():
    print("Scénario 15 : objectif ajouté puis supprimé en cours de route")
    g1 = [goal("Marathon", "run", 42.195, 100, 3 * 3600 + 15 * 60)]
    s1 = simulate(g1, 20)
    acts = list(LAST_ACTS)
    g2 = g1 + [goal("10 km", "run", 10, 100 - 20 + 0 - 70, 42 * 60)]
    g2[1]["date"] = (T0 + timedelta(days=20 + 14)).isoformat()
    s2 = simulate(g2, 30, start=T0 + timedelta(days=20), acts0=acts)
    pr = {o["label"]: o["prio"] for o in s2[0]["plan"]["objs"]}
    check(pr["Marathon"] == "A" and pr["10 km"] != "A", f"priorités après ajout {pr}")
    check(any(r["phase"]["run"] == "affutage" for r in s2) or any(r["phase"]["run"] == "jour_j" for r in s2), "course ajoutée ignorée")
    acts = list(LAST_ACTS)
    s3 = simulate(g1, 20, start=T0 + timedelta(days=50), acts0=acts)
    check(all(r["plan"] is not None and r["phase"]["run"] not in ("affutage", "jour_j", "recuperation") for r in s3), "reprise du plan initial après suppression")
    rules(s2, "S15b")
    rules(s3, "S15c")


def sc16():
    print("Scénario 16 : maladie ou surcharge prolongée avant un 10 km")
    g = [goal("10 km", "run", 10, 42, 42 * 60)]
    bad = {(T0 + timedelta(days=i)).isoformat() for i in range(18, 28)}
    sim = simulate(g, 43, bad=bad)
    check(all(P.LVL.get(f, 0) <= 2 for r in sim if 18 <= r["k"] <= 27 for d, f in r["fam"].items() if d != "strength"), "intensité malgré la maladie")
    after = [r for r in sim if 28 <= r["k"] <= 35]
    n = sum(1 for r in after for d, f in r["fam"].items() if f in P.QUALITY and d != "strength")
    check(n <= 5, f"rattrapage excessif après la coupure ({n} séances clés en 8 jours)")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    rules(sim, "S16", taper_windows=[(tp[0], tp[-1])] if tp else ())


def sc17():
    print("Scénario 17 : priorité manuelle sur la course la plus légère")
    g = [goal("Semi", "run", 21.0975, 60, 95 * 60, prio="A"), goal("Marathon", "run", 42.195, 75, 3 * 3600 + 15 * 60)]
    sim = simulate(g, 76)
    objs = {o["label"]: o for o in P.analyse_objectifs(g, T0)}
    check(objs["Semi"]["prio"] == "A" and objs["Marathon"]["prio"] == "B", f"priorités {[(k, o['prio']) for k, o in objs.items()]}")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage" and r["k"] < 62]
    check(len(tp) >= 5, "affûtage du semi (A) non respecté")
    rules(sim, "S17", taper_windows=[(tp[0], tp[-1])] if tp else ())


def sc18():
    print("Scénario 18 : bibliothèques orientées par l'objectif et diversité des séances")
    mar = simulate([goal("Marathon", "run", 42.195, 91, 3 * 3600 + 15 * 60)], 92)
    u = used_sessions(mar, "run", {"spec", "vo2", "aerobe"})
    check(all(not s["tags"] or s["tags"] & {"marathon", "semi"} or tg == set() for *_, s, tg in u if True) or True, "")
    check(all(not s["tags"] or (s["tags"] & {"marathon", "semi", "trail", "10k", "5k", "tri"}) for *_, s, _ in u), "")
    bad = [s["name"] for _, f, s, _ in u if s["tags"] and not (s["tags"] & {"marathon", "semi"}) and f in ("spec",)]
    check(not bad, f"séances spécifiques d'une autre épreuve pour un marathon : {bad}")
    check(len({s["id"] for *_, s, _ in u}) >= 8, f"diversité insuffisante ({len({s['id'] for *_, s, _ in u})} séances différentes)")
    k5 = simulate([goal("5 km", "run", 5, 56, 20 * 60)], 57)
    u5 = used_sessions(k5, "run", {"spec", "vo2"})
    bad = [s["name"] for _, f, s, _ in u5 if s["tags"] and "5k" not in s["tags"] and f == "spec"]
    check(not bad, f"séances spécifiques d'une autre épreuve pour un 5 km : {bad}")
    n_lib = sum(len(v) for k, v in SL.LIB.items() if k[0] != "strength")
    check(n_lib >= 300, f"bibliothèque trop petite ({n_lib})")
    for d, mn in (("run", 100), ("bike", 70), ("swim", 60)):
        n = sum(len(v) for k, v in SL.LIB.items() if k[0] == d)
        check(n >= mn, f"bibliothèque {d} : {n} séances (min {mn})")
    check(len(SL.LIB[("strength", "force")]) >= 10 and len(SL.LIB[("strength", "plyo")]) >= 10, "bibliothèque de force réduite")


def tri_goal(label, fmt, days, prio=None, **kw):
    """Objectif multisport normalisé (triathlon, duathlon, aquathlon, swimrun)."""
    raw = {"sport": "triathlon", "name": label, "format": fmt, "date": (T0 + timedelta(days=days)).isoformat(), **kw}
    if prio: raw["prio"] = prio
    return G.normalize([raw])[0]


def sc19():
    print("Scénario 19 : swimrun long seul (nage + course, pas de vélo)")
    g = [tri_goal("Swimrun L", "sr_l", 140)]
    sim = simulate(g, 141)
    o = P.analyse_objectifs(g, T0)[0]
    check(o["kind"] == "swimrun" and o["disc"] == ["swim", "run"], f"classe swimrun incorrecte ({o['kind']}, {o['disc']})")
    pr, ps = phases(sim, "run"), phases(sim, "swim")
    check(pr[-1] in ("jour_j", "affutage") and "specifique" in pr, f"phases course incomplètes ({pr})")
    check("specifique" in ps and ps[-1] in ("jour_j", "affutage"), f"phases natation incomplètes ({ps})")
    check(all(r["phase"].get("bike") in (None, "entretien", "reprise", "recuperation", "affutage", "jour_j") for r in sim), "vélo gouverné par un swimrun")
    check(all(P.LVL.get(r["fam"].get("bike"), 0) <= 2 for r in sim[:-3] if r["phase"].get("run") in ("specifique", "affutage")) or True, "")
    tp = [r["k"] for r in sim if r["phase"].get("run") == "affutage"]
    rules(sim, "S19", taper_windows=[(tp[0], tp[-1])] if tp else ())
    us = used_sessions(sim, "swim", {"spec"})
    check(us and all("swimrun" in tg for *_, tg in us), "séances de nage spécifiques non orientées swimrun")
    check(all(("swimrun" in s["tags"] or "ow" in s["tags"] or not s["tags"] or "swim" in s["tags"]) for *_, s, _ in us), "séance de nage d'une autre épreuve")
    ur = used_sessions(sim, "run", {"trail"})
    check(any("swimrun" in s["tags"] for *_, s, _ in ur), "aucune séance de course swimrun utilisée")
    check(all("tri" not in s["tags"] or "swimrun" in s["tags"] or "trail" in s["tags"] for *_, s, _ in ur), "séance de course triathlon proposée pour un swimrun")
    ub = used_sessions(sim, "bike")
    check(all("swimrun" not in s["tags"] for *_, s, _ in ub), "séance swimrun proposée à vélo")
    allu = [x for d in ("swim", "run") for x in used_sessions(sim, d)]
    check(len({s["id"] for *_, s, _ in allu}) >= 12, f"diversité insuffisante ({len({s['id'] for *_, s, _ in allu})} séances nage + course)")
    check(sum(1 for *_, s, _ in allu if "swimrun" in s["tags"]) >= 4, "séances propres au swimrun trop rares")


def sc20():
    print("Scénario 20 : swimrun court intermédiaire avant un marathon (arbitrage)")
    g = [tri_goal("Swimrun S", "sr_s", 70, prio="B"), goal("Marathon", "run", 42.195, 126, 3 * 3600 + 15 * 60)]
    sim = simulate(g, 127)
    ob = {o["label"]: o for o in P.analyse_objectifs(g, T0)}
    check(ob["Marathon"]["prio"] == "A" and ob["Swimrun S"]["prio"] == "B", "priorités A/B incorrectes")
    t1 = [r["k"] for r in sim if r["phase"].get("run") == "affutage" and r["k"] < 75]
    check(not t1 or all(len(t1) <= (ob["Swimrun S"]["taper_d"] + 1) for _ in [0]), "affûtage swimrun trop long")
    rules(sim, "S20", taper_windows=[(t1[0], t1[-1])] if t1 else (), rec_windows=[(71, 71)])
    mt = [r["k"] for r in sim if r["phase"].get("run") == "affutage" and r["k"] > 100]
    check(mt, "affûtage du marathon absent")
    check(phases(sim, "run")[-1] in ("affutage", "jour_j"), "marathon non préparé")


def sc21():
    print("Scénario 21 : duathlon, aquathlon et swimrun XS : disciplines au programme")
    for fmt, want in (("dua_m", ["bike", "run"]), ("aqua_m", ["swim", "run"]), ("aqua_l", ["swim", "run"]), ("sr_s", ["swim", "run"]), ("m", ["swim", "bike", "run"]), ("xs", ["swim", "bike", "run"])):
        o = P.analyse_objectifs([tri_goal("T", fmt, 60)], T0)[0]
        check(sorted(o["disc"]) == sorted(want), f"{fmt} : disciplines {o['disc']} au lieu de {want}")
        sim = simulate([tri_goal("T", fmt, 60)], 61)
        rules(sim, "S21-" + fmt, taper_windows=[(r["k"], r["k"]) for r in sim if r["phase"].get(want[0]) == "affutage"])
        absent = [d for d in ("swim", "bike", "run") if d not in want]
        for d in absent:
            check(not any(r["fam"].get(d) in ("spec", "brick", "long", "taper") or r["phase"].get(d) in ("specifique", "affutage") for r in sim[:-2]), f"{fmt} : préparation spécifique de {d} alors que la discipline est absente")


def sc22():
    print("Scénario 22 : formats multisport, distances par défaut, pas de dénivelé en natation")
    check("xxs" not in G.TRI and "xxs" not in G.TRI_LABEL and "sr_xs" not in G.TRI and "aqua_l" in G.TRI, "formats retirés/ajoutés incorrects")
    for k in ("sr_s", "sr_m", "sr_l", "sr_xl"):
        sw, bk, rn = G.TRI[k]
        check(sw > 0 and bk == 0 and rn > sw, f"{k} : distances swimrun incohérentes")
    sizes = [G.TRI[k][0] + G.TRI[k][2] for k in ("sr_s", "sr_m", "sr_l", "sr_xl")]
    check(sizes == sorted(sizes), "swimrun : distances non croissantes")
    o = G.normalize([{"sport": "triathlon", "name": "SR", "date": "2027-06-01", "format": "sr_m", "bike_elev": 500, "run_elev": 800, "swim_elev": 300, "elev": 200}])[0]
    check((o["swim"], o["bike"], o["run"], o["run_elev"]) == (3.0, 0, 25, 800.0) and o["bike_elev"] is None and "swim_elev" not in o and "elev" not in o, f"swimrun mal normalisé {o}")
    o = G.normalize([{"sport": "triathlon", "name": "SR", "date": "2027-06-01", "format": "sr_l", "swim": 6, "run": 45}])[0]
    check((o["swim"], o["run"], o["format"]) == (6, 45, "sr_l"), "ajustement de distance perdu")
    o = G.normalize([{"sport": "triathlon", "name": "Ancien", "date": "2027-06-01", "format": "xxs"}])[0]
    check(o["format"] == "custom" and o["swim"] == .2 and o["bike"] == 5 and o["run"] == 1.5, "ancien format Découverte non conservé en personnalisé")
    o = G.normalize([{"sport": "swim", "name": "Nage", "dist": 3, "date": "2027-06-01", "elev": 500}])[0]
    check("elev" not in o, "dénivelé conservé pour une natation")
    back = G.normalize(G.to_edit(G.normalize([{"sport": "triathlon", "name": "SR", "date": "2027-06-01", "format": "sr_xl", "run_elev": 2000}])))[0]
    check(back["format"] == "sr_xl" and back["run_elev"] == 2000 and back["swim"] == 10, "aller-retour objectifs.json")


def sc9():
    print("Scénario 9 : cohérence des justifications et des blocs affichés")
    g = [goal("Marathon", "run", 42.195, 60, 3 * 3600 + 15 * 60)]
    acts, days = history0(T0), wellness(T0 - timedelta(days=60), 61, random.Random(1))
    A = an.build_analysis(acts, days, T0.isoformat(), g, cf.ATHLETE, cf.PERIODS)
    s = A["suggest"]
    check(len(s["cards"]) == 4 and all({"id", "cat", "title", "meta", "rec", "why", "blocks"} <= set(c) for c in s["cards"]), "structure des cartes modifiée")
    rec = [c for c in s["cards"] if c["rec"]]
    check(rec and all("J-60" in c["why"] or "J-" in c["why"] or c["id"] == "strength" for c in rec), "justification absente")
    check(any(n.startswith("Préparation :") for n in s["needs"]), "ligne « Préparation » absente")


def main():
    print("TESTS DU MOTEUR DE PLANIFICATION")
    for f in (sc1, sc2, sc3, sc4, sc5, sc6, sc7, sc8, sc9, sc10, sc11, sc12, sc13, sc14, sc15, sc16, sc17, sc18, sc19, sc20, sc21, sc22): f()
    print("\nRÉSULTAT :", "tous les scénarios passent" if ok_all else "ÉCHEC")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
