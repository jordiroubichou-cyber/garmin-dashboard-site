"""Planification stratégique de la préparation : objectifs -> phases -> arbitrage -> séance du jour.

Module 100 % déterministe (aucune IA, aucun hasard) et sans dépendance : il ne lit que les objectifs, l'historique d'activités
et l'état de forme déjà calculé par analysis.py. Les décisions sont expliquées par des indicateurs mesurables.

ARCHITECTURE (six couches, chacune une fonction ou un groupe de fonctions) :
  1. condition physique          -> analysis.physio_state() (FAF, profil, récupération) : fournie en entrée, jamais recalculée ici
  2. objectifs et échéances      -> analyse_objectifs()   classe chaque course (format, poids, durées de blocs), priorité A/B/C
  3. périodisation               -> phase_de()            reprise / développement / intensification / spécificité / affûtage / récupération
  4. arbitrage multi-objectifs   -> gouvernance()         quel objectif gouverne chaque discipline aujourd'hui (et conflits)
  5. séance du jour              -> choisir_famille()     famille de séance, volume, justification ; réconciliée avec la condition physique
  6. cohérence                   -> verifier()            contrôle des règles (affûtage protégé, quota de séances clés, récupération...)

Références générales (peu nombreuses, volontairement) : périodisation en blocs base / construction / spécifique / affûtage (Friel, Bompa) ;
distribution polarisée ≈ 80 % facile / 20 % intense (Seiler) ; affûtage : réduire le volume de 40 à 60 % en gardant intensité et fréquence
(Mujika & Padilla 2003, Bosquet 2007) ; temps de récupération après compétition proportionnel à la distance (Daniels, Pfitzinger) ;
entraînement concurrent : séances clés espacées de 48 h et jamais plus de 2 à 3 séances intenses par semaine (Hickson 1980, Wilson 2012).
"""
from datetime import date, timedelta

DISCS = ("run", "bike", "swim", "strength")
PHASE_FR = {"reprise": "Reprise / mise en jambe", "developpement": "Développement / montée en charge",
            "intensification": "Intensification (développement qualitatif)", "specifique": "Spécificité compétition",
            "affutage": "Affûtage", "jour_j": "Jour de compétition", "recuperation": "Récupération après compétition", "entretien": "Entretien"}
PHASE_RANK = {"jour_j": 0, "affutage": 1, "specifique": 2, "intensification": 3, "developpement": 4, "reprise": 5}
LATE = ("jour_j", "affutage", "specifique", "intensification")
INTENT = {"recup": "récupération active, sans coût mécanique", "z2": "endurance fondamentale (zone 2)",
          "aerobe": "capacité aérobie au seuil / tempo", "vo2": "puissance aérobie maximale (VMA, PMA, VO2max)",
          "spec": "allures spécifiques de la compétition", "long": "endurance de longue durée et résistance à la fatigue",
          "taper": "maintien de la vivacité à volume réduit", "brick": "enchaînement vélo-course", "trail": "spécificité trail (dénivelé)",
          "force": "force et prévention des blessures"}
DISC_NOUN = {"run": "course à pied", "bike": "vélo", "swim": "natation", "strength": "renforcement"}

# classe d'épreuve : (limite haute en distance équivalente, libellé, poids, (développement, intensification, spécificité) en semaines,
#                     jours d'affûtage, jours de récupération après compétition, sortie longue max en minutes)
RUN_T = [(6, "5 km", .35, (3, 2, 1.5), 3, 2, 70), (12, "10 km", .5, (4, 3, 2), 6, 3, 90), (25, "semi-marathon", .7, (5, 3, 3), 9, 6, 110),
         (46, "marathon", 1.0, (7, 3, 4), 16, 12, 135), (80, "ultra 50 km", 1.1, (8, 3, 5), 17, 14, 150), (10 ** 9, "ultra", 1.2, (9, 3, 5), 20, 18, 150)]
BIKE_T = [(50, "vélo court", .35, (3, 2, 1.5), 3, 2, 120), (100, "vélo moyen", .5, (4, 3, 2), 5, 3, 180),
          (160, "vélo long", .7, (6, 3, 3), 7, 5, 210), (10 ** 9, "vélo très long", .9, (8, 3, 4), 10, 7, 240)]
SWIM_T = [(1.0, "natation courte", .25, (2, 1, 1), 2, 1, 0), (2.5, "natation moyenne", .35, (3, 2, 1.5), 3, 2, 0),
          (5, "natation longue", .5, (4, 2, 2), 4, 3, 65), (10 ** 9, "natation très longue", .7, (5, 3, 2), 6, 4, 80)]
TRI_T = [(20, "triathlon XS", .35, (3, 2, 1.5), 3, 2, 90), (40, "triathlon S", .5, (4, 3, 2), 5, 3, 110),
         (75, "triathlon M", .7, (6, 3, 3), 7, 5, 120), (150, "triathlon L", 1.0, (9, 4, 4), 12, 10, 135), (10 ** 9, "triathlon XL", 1.3, (11, 4, 5), 16, 14, 150)]
# swimrun : équivalent-km = course + 3 × natation (en combinaison et chaussures, la nage coûte cher) + D+/100
SWIMRUN_T = [(10, "swimrun XS", .35, (3, 2, 1.5), 3, 2, 90), (22, "swimrun S", .5, (4, 3, 2), 5, 3, 110),
             (42, "swimrun M", .7, (6, 3, 3), 8, 6, 130), (68, "swimrun L", 1.0, (9, 4, 4), 11, 10, 150), (10 ** 9, "swimrun XL", 1.3, (11, 4, 5), 15, 15, 165)]
SHARES = {"run": {"run": .62, "bike": .14, "swim": .09, "strength": .15}, "trail": {"run": .58, "bike": .10, "swim": .05, "strength": .27},
          "triathlon": {"run": .27, "bike": .38, "swim": .20, "strength": .15},
          "swimrun": {"run": .47, "bike": .08, "swim": .30, "strength": .15}, "swim": {"run": .10, "bike": .10, "swim": .65, "strength": .15},
          "bike": {"run": .10, "bike": .66, "swim": .09, "strength": .15}}
PRIO_W = {"A": 3.0, "B": 2.0, "C": 0.5}

# paramètres par phase : séances clés max sur 7 jours (quota), écart minimal entre deux séances clés (jours), volume relatif, budget global de séances clés / 7 j
PH = {"reprise": dict(quota=1, gap=4, vol=.8, budget=1), "developpement": dict(quota=2, gap=2, vol=.9, budget=3),
      "intensification": dict(quota=3, gap=2, vol=.95, budget=4), "specifique": dict(quota=3, gap=2, vol=1.0, budget=4),
      "affutage": dict(quota=1, gap=3, vol=.7, budget=2), "jour_j": dict(quota=0, gap=9, vol=.4, budget=0),
      "recuperation": dict(quota=0, gap=9, vol=.7, budget=0), "entretien": dict(quota=1, gap=4, vol=.9, budget=2)}
# familles de séances clés à faire tourner (rotation selon le nombre de séances clés déjà faites sur 21 jours)
SEQ = {"reprise": ("aerobe",), "developpement": ("aerobe", "long", "aerobe", "vo2"), "intensification": ("vo2", "aerobe", "vo2", "long"),
       "specifique": ("spec", "long", "vo2", "spec"), "affutage": ("taper",), "entretien": ("aerobe", "vo2")}
ALLOWED = {"reprise": {"aerobe"}, "developpement": {"aerobe", "long", "vo2"}, "intensification": {"vo2", "aerobe", "long"},
           "specifique": {"spec", "long", "vo2", "aerobe", "trail", "brick"}, "affutage": {"taper"}, "entretien": {"aerobe", "vo2"}}
LVL = {"recup": 1, "z2": 2, "taper": 2, "aerobe": 3, "long": 3, "trail": 3, "force": 3, "spec": 4, "brick": 4, "vo2": 5}
QUALITY = {"aerobe", "vo2", "spec", "long", "trail", "brick"}
DOWN = {"vo2": "aerobe", "spec": "aerobe", "brick": "aerobe", "trail": "aerobe", "long": "z2", "aerobe": "z2", "taper": "z2", "z2": "recup", "recup": "recup"}


def _d(s):
    return date.fromisoformat(s)


def _fr(s):
    d = _d(s); return f"{d.day:02d}/{d.month:02d}/{d.year}"


# =============================================================================================
# 2. OBJECTIFS ET ÉCHÉANCES
# =============================================================================================
def _classe(g):
    sp, dist = g.get("sport", "run"), float(g.get("dist") or 0)
    if sp == "trail": eq, table = dist + (g.get("elev") or 0) / 100.0, RUN_T      # 100 m de D+ ≈ 1 km à plat
    elif sp == "run": eq, table = dist, RUN_T
    elif sp == "bike": eq, table = dist + (g.get("elev") or 0) / 40.0, BIKE_T
    elif sp == "swim": eq, table = dist, SWIM_T
    elif str(g.get("format") or "").startswith("sr_"):                          # swimrun : natation et course à pied (trail) enchaînées
        sp = "swimrun"; eq, table = float(g.get("run") or 0) + 3.0 * float(g.get("swim") or 0) + (g.get("run_elev") or 0) / 100.0, SWIMRUN_T
    else: eq, table = dist, TRI_T
    row = next(r for r in table if eq <= r[0])
    weight = row[2]
    if sp in ("run", "trail"):                                                 # poids continu : un trail de 30 km pèse moins qu'un marathon
        weight = round(min(1.2, 0.18 + 0.82 * (eq * (1.1 if sp == "trail" else 1.0) / 42.195) ** 0.9), 3)
    disc = {"run": ["run"], "trail": ["run"], "bike": ["bike"], "swim": ["swim"], "triathlon": ["swim", "bike", "run"], "swimrun": ["swim", "run"]}.get(sp, ["run"])
    if sp in ("triathlon", "swimrun"):                                                      # duathlon (sans natation), aquathlon (sans vélo) : seules les disciplines au programme
        legs = {"swim": g.get("swim"), "bike": g.get("bike"), "run": g.get("run")}
        disc = [d for d in disc if legs.get(d) is None or float(legs[d] or 0) > 0] or disc
    return {"kind": sp, "cls": row[1], "weight": weight, "blocks": row[3], "taper_d": row[4], "rec_d": row[5], "long_cap": row[6], "disc": disc, "eq": round(eq, 1)}


def phase_de(o, days_left):
    """Phase de préparation d'un objectif à partir du nombre de jours restants (planification à rebours depuis la date de course)."""
    if days_left == 0: return "jour_j"
    if days_left <= o["taper_d"]: return "affutage"
    dev, inten, spec = o["blocks"]
    wk = (days_left - o["taper_d"]) / 7.0
    if wk <= spec: return "specifique"
    if wk <= spec + inten: return "intensification"
    if wk <= spec + inten + dev: return "developpement"
    return "reprise"


def analyse_objectifs(goals, T):
    """Enrichit chaque objectif : classe, jours restants, priorité (A principal / B intermédiaire / C préparatoire), rôle, phase propre."""
    objs = []
    for g in goals:
        try:
            dl = (_d(g["date"]) - T).days
        except (KeyError, ValueError, TypeError):
            continue
        c = _classe(g)
        objs.append(dict(c, id=g.get("id", g.get("label")), label=g.get("label") or g.get("name") or "objectif", date=g["date"], days_left=dl,
                         target_s=g.get("target_s"), manual=g.get("prio") if g.get("prio") in PRIO_W else None))
    up = [o for o in objs if o["days_left"] >= 0]
    manual_a = [o for o in up if o["manual"] == "A"]
    top = [min(manual_a, key=lambda o: (-o["weight"], o["days_left"]))] if manual_a else ([min(up, key=lambda o: (-o["weight"], o["days_left"]))] if up else [])      # un seul objectif principal
    ids_a = {o["id"] for o in top}
    for o in objs:
        if o["manual"]: o["prio"] = o["manual"] if o["id"] not in ids_a else "A"
        elif o["id"] in ids_a: o["prio"] = "A"
        elif top and o["weight"] >= 0.55 * top[0]["weight"]: o["prio"] = "B"
        elif o["target_s"] and o["weight"] >= 0.3: o["prio"] = "B"          # objectif chiffré : performance intermédiaire
        else: o["prio"] = "C"                                              # compétition préparatoire (sortie spécifique)
        if o["manual"] == "A" and o["id"] not in ids_a: o["prio"] = "B"
    A = top[0] if top else None
    for o in objs:
        o["role"] = {"A": "principal", "B": "secondaire", "C": "préparatoire"}[o["prio"]]
        if o["prio"] == "B" and A and A is not o and 0 <= A["days_left"] - o["days_left"] <= 42:
            o["role"] = "intermédiaire"                                     # course-étape avant l'objectif principal : affûtage et récupération courts
        # ajustement des durées selon le rôle
        k = {"principal": 1.0, "secondaire": .75, "intermédiaire": .45, "préparatoire": .25}[o["role"]]
        o["taper_d"] = int(round(o["taper_d"] * k)) if o["role"] != "préparatoire" else (1 if o["eq"] >= 10 else 0)
        o["rec_d"] = int(round(o["rec_d"] * (1.0 if o["prio"] == "A" else .7 if o["prio"] == "B" else .4)))
        if o["role"] == "intermédiaire": o["rec_d"] = max(1, int(round(o["rec_d"] * .6)))
        o["phase"] = phase_de(o, o["days_left"]) if o["days_left"] >= 0 else ("recuperation" if -o["days_left"] <= o["rec_d"] else "passe")
        o["weeks_left"] = round(o["days_left"] / 7.0, 1)
        o["prep_weeks"] = sum(o["blocks"]) + o["taper_d"] / 7.0
    return sorted(objs, key=lambda o: o["date"])


# =============================================================================================
# 1 bis. HISTORIQUE PAR DISCIPLINE (indicateurs mesurables)
# =============================================================================================
def historique(acts, T):
    out = {d: {"q_days": 99, "q7": 0, "nq21": 0, "long_days": 99, "min14": 0.0, "weeks4": set(), "last_days": 99, "last_q_te": 0.0} for d in DISCS}
    for a in acts:
        try:
            age = (T - _d(a["d"])).days
        except (KeyError, ValueError):
            continue
        if age < 0: continue
        s = a.get("s")
        disc = "run" if s in ("run", "trail") else s if s in DISCS else None
        if not disc: continue
        h = out[disc]
        h["last_days"] = min(h["last_days"], age)
        if age < 14: h["min14"] += a.get("m") or 0
        if age < 28: h["weeks4"].add(age // 7)
        if disc != "strength" and (a.get("te") or 0) >= 3.3:
            if age < h["q_days"]: h["last_q_te"] = a.get("te") or 0.0       # intensité (effet d'entraînement) de la dernière séance clé
            h["q_days"] = min(h["q_days"], age)
            if age < 7: h["q7"] += 1
            if age < 21: h["nq21"] += 1
        km, m = a.get("km") or 0, a.get("m") or 0
        if (disc == "run" and (km >= 16 or m >= 85)) or (disc == "bike" and m >= 120) or (disc == "swim" and km >= 2.8):
            h["long_days"] = min(h["long_days"], age)
    for h in out.values(): h["weeks4"] = len(h["weeks4"])
    out["_any_days"] = min([out[d]["last_days"] for d in DISCS] + [99])
    ages = sorted({(T - _d(a["d"])).days for a in acts if a.get("s") in DISCS and a.get("d") and 0 <= (T - _d(a["d"])).days <= 35})
    out["_resume_age"], out["_gap_len"] = None, 0
    for x, y in zip(ages, ages[1:]):                                          # y est plus ancien que x : trou de y-x-1 jours sans séance
        if y - x - 1 >= 5:
            out["_resume_age"], out["_gap_len"] = x, y - x - 1               # le plus récent des trous
            break
    out["_q7_total"] = sum(out[d]["q7"] for d in ("run", "bike", "swim"))
    return out


# =============================================================================================
# 4. ARBITRAGE ENTRE OBJECTIFS
# =============================================================================================
def gouvernance(objs, disc, hist):
    """Objectif qui gouverne une discipline aujourd'hui. Retourne (objectif|None, phase, notes). Règles :
    1. une récupération après course (A, B) prime, sauf si un affûtage commence avant la fin de la récupération ;
    2. un affûtage / jour J protège la discipline ; 3. à défaut, l'objectif en phase tardive (spécificité, intensification) de plus haute priorité ;
    4. à défaut, l'objectif principal (A) ou le plus lourd, en phase de développement ou de reprise ; 5. sinon : entretien."""
    rel = [o for o in objs if disc in o["disc"]]
    up = [o for o in rel if o["days_left"] >= 0]
    notes = []
    real_up = [o for o in up if o["prio"] != "C"] or up                      # une compétition préparatoire (C) ne gouverne que si rien d'autre
    past = [o for o in rel if o["phase"] == "recuperation"]
    if past and not any(o["phase"] in ("affutage", "jour_j") for o in real_up):
        p = min(past, key=lambda o: -o["days_left"])
        left = p["rec_d"] - (-p["days_left"])
        nxt = min((o for o in real_up), key=lambda o: o["days_left"], default=None)
        if nxt and nxt["prio"] != "C":
            left = min(left, max(0, nxt["days_left"] - nxt["taper_d"]))     # la récupération s'arrête au début de l'affûtage suivant
            if left < p["rec_d"] - (-p["days_left"]): notes.append("récupération raccourcie : prochaine échéance proche")
        if left > 0: return p, "recuperation", notes
    late = [o for o in real_up if o["phase"] in LATE]
    if late:
        o = min(late, key=lambda o: (PHASE_RANK[o["phase"]] if o["phase"] in ("jour_j", "affutage") else 9, -PRIO_W[o["prio"]], o["days_left"]))
        others = [x for x in real_up if x is not o and x["phase"] in LATE]
        if others: notes.append("conflit de planification arbitré en faveur de « " + o["label"] + " » (priorité " + o["prio"] + ")")
        return o, o["phase"], notes
    if real_up:
        o = min(real_up, key=lambda o: (-PRIO_W[o["prio"]], -o["weight"], o["days_left"]))
        return o, o["phase"], notes
    return None, "entretien", notes


def _target_share(objs):
    up = [o for o in objs if o["days_left"] >= 0]
    if not up: return None
    acc = {d: 0.0 for d in DISCS}; tot = 0.0
    for o in up:
        w = PRIO_W[o["prio"]] / (1.0 + max(o["days_left"], 0) / 84.0)
        sh = {d: v for d, v in SHARES[o["kind"]].items() if d == "strength" or d in o["disc"]}      # disciplines absentes du programme : part nulle
        k = sum(sh.values()) or 1.0
        for d, v in sh.items(): acc[d] += w * v / k
        tot += w
    return {d: acc[d] / tot for d in DISCS}


# =============================================================================================
# 5. SÉANCE DU JOUR
# =============================================================================================
def _vol(phase, o):
    p = PH[phase]["vol"]
    if phase == "affutage" and o and o["taper_d"]:
        p = 0.5 + 0.3 * min(1.0, max(0, o["days_left"]) / max(o["taper_d"], 1))      # 80 % en début d'affûtage -> 50 % la veille
    return round(p, 2)


def _quality_pick(disc, phase, o, hist, state_fam):
    seq = list(SEQ.get(phase, ("aerobe",)))
    kind = o["kind"] if o else None
    if disc == "run" and kind in ("trail", "swimrun"): seq = [("trail" if f == "spec" else f) for f in seq]
    if disc == "bike" and kind == "triathlon" and phase == "specifique": seq = ["spec", "brick", "long", "vo2"]
    if disc == "swim": seq = [f for f in seq if f != "long" or (o and o["long_cap"])] or ["aerobe"]
    if disc == "swim" and kind in ("triathlon", "swimrun") and phase == "specifique": seq = ["spec", "aerobe", "spec", "vo2"]      # eau libre, visée, départs en groupe
    if disc == "swim" and kind in ("triathlon", "swimrun") and phase == "intensification": seq = ["aerobe", "spec", "vo2"]
    if disc == "run" and o and not o["long_cap"]: seq = [f for f in seq if f != "long"] or ["aerobe"]
    if disc == "bike" and kind in ("bike", "triathlon") and o and o["weight"] < .5: seq = [f for f in seq if f != "long"] or ["aerobe"]
    h = hist[disc]
    pick = seq[h["nq21"] % len(seq)]
    if phase == "intensification":                                           # alternance : séance de haute intensité / séance aérobie soutenue, sortie longue chaque semaine
        pick = "vo2" if h["last_q_te"] < 3.9 else "aerobe"
        if "long" in seq and h["long_days"] >= 8 and not (disc == "swim"): pick = "long"
    if phase == "specifique" and disc == "swim" and kind in ("triathlon", "swimrun"):       # alternance séance spécifique (eau libre, visée) / séance de seuil
        pick = "spec" if h["last_q_te"] < 3.8 else "aerobe"
    if phase == "specifique" and disc == "bike" and kind == "triathlon":     # alternance sortie longue / enchaînement vélo-course
        pick = "brick" if h["long_days"] <= h["q_days"] else "long"
    if pick == "long" and hist[disc]["long_days"] < 6: pick = next((f for f in seq if f != "long"), "aerobe")     # une sortie longue par semaine maximum
    if phase in ("developpement", "specifique") and "long" in seq and hist[disc]["long_days"] >= 9 and disc in ("run", "bike"): pick = "long"
    if state_fam in ALLOWED.get(phase, ()) and state_fam in QUALITY and state_fam != "long" and phase in ("developpement", "entretien"):
        pick = state_fam                                                     # un déficit identifié par l'analyse de forme (ex. anaérobie) oriente le choix
    if pick == "vo2" and phase == "developpement" and hist[disc]["nq21"] % 4 != 3 and state_fam != "vo2": pick = "aerobe"
    return pick


def choisir_famille(disc, phase, o, hist, state_fam, cap, st):
    """Famille de séance pour une discipline : plan (phase, quotas) réconcilié avec le plafond d'intensité que le corps peut assimiler (cap, niveau 1 à 5)."""
    h, P = hist[disc], PH[phase]
    flags = []
    easy = "recup" if cap <= 1 else "z2"
    due = False
    if phase in ("recuperation", "jour_j"):
        plan = "recup" if (phase == "jour_j" or (o and -o["days_left"] <= max(1, o["rec_d"] // 2))) else "z2"
        flags.append("récupération après compétition" if phase == "recuperation" else "jour de compétition")
    else:
        budget_ok = hist["_q7_total"] < P["budget"] or (h["q7"] == 0 and hist["_q7_total"] < P["budget"] + 1)
        due = h["q7"] < P["quota"] and h["q_days"] >= P["gap"] and budget_ok
        if phase == "affutage" and o and o["days_left"] <= 2: due = False             # pas de séance clé dans les 48 h avant la course
        if due: plan = _quality_pick(disc, phase, o, hist, state_fam)
        else:
            plan = easy
            if h["q7"] >= P["quota"] and P["quota"]: flags.append(f"quota atteint ({h['q7']} séance(s) clé(s) sur 7 jours)")
            elif h["q_days"] < P["gap"] and P["quota"]: flags.append(f"séance clé récente (il y a {h['q_days']} j)")
    final = plan
    while LVL[final] > cap and final in DOWN and DOWN[final] != final: final = DOWN[final]
    if final != plan: flags.append("séance clé décalée : condition physique insuffisante (" + st["profile"].replace("_", " ") + ")")
    return final, plan, due, flags


def session_tags(o, disc):
    """Étiquettes d'épreuve de la discipline : orientent le choix de la séance dans la bibliothèque (séances propres à un 5 km, un marathon, un trail, un triathlon...)."""
    if o is None: return frozenset()
    k, eq = o["kind"], o["eq"]
    if k == "triathlon": return frozenset({"tri", "ow"} if disc == "swim" else {"tri"})
    if k == "swimrun": return frozenset({"swimrun", "ow"} if disc == "swim" else {"swimrun", "trail"} if disc == "run" else set())
    if disc == "run" and k in ("run", "trail"):
        if k == "trail": return frozenset({"trail"})
        return frozenset({"5k"} if eq < 8 else {"10k"} if eq < 16 else {"semi"} if eq < 30 else {"marathon"})
    if disc == "bike" and k == "bike": return frozenset({"bike", "fondo"} if eq >= 100 else {"bike"})
    if disc == "swim" and k == "swim": return frozenset({"swim"})
    return frozenset()


def planifier(acts, T, goals, st, fam_state, cap, D=None):
    """Point d'entrée : retourne la stratégie du jour (None sans objectif à venir ni récupération en cours)."""
    objs = analyse_objectifs(goals, T)
    if not any(o["days_left"] >= 0 or o["phase"] == "recuperation" for o in objs): return None
    hist = historique(acts, T)
    out = {"fam": {}, "vol": {}, "phase": {}, "gov": {}, "notes": {}, "plan_fam": {}, "due": {}, "long_cap": {}, "prog": {}, "bonus": {}, "flags": {}, "tags": {}}
    objs_late = [o for o in objs if o["days_left"] >= 0 and o["prio"] != "C" and o["phase"] in ("affutage", "jour_j")]
    key_late = [o for o in objs if o["days_left"] >= 0 and o["prio"] != "C" and o["phase"] in LATE]
    global_easy = bool(objs_late) or any(o["phase"] == "recuperation" and o["prio"] != "C" and -o["days_left"] <= max(2, o["rec_d"]) for o in objs)
    idle = hist["_any_days"] >= 5                                            # plusieurs jours sans séance : reprise progressive, sans rattrapage
    ra, gl = hist["_resume_age"], hist["_gap_len"]
    resuming = ra is not None and ra < (10 if gl >= 10 else 7)               # fenêtre de reprise qui suit le retour à l'entraînement
    restart = idle or resuming
    easy_restart = idle or (resuming and ra <= 2)                            # 3 premiers jours de retour : uniquement facile
    long_break = max(hist["_any_days"] if idle else 0, gl if resuming else 0) >= 10
    for disc in ("run", "bike", "swim"):
        o, phase, notes = gouvernance(objs, disc, hist)
        support = False
        if o is None and key_late:
            phase, support = "entretien", True                               # discipline hors objectif pendant la phase tardive d'un autre : soutien léger
        if o is not None and phase in ("intensification", "specifique") and hist[disc]["weeks4"] < 2 and o["days_left"] > o["taper_d"]:
            phase = "developpement"; notes.append("niveau récent insuffisant pour l'intensification : consolidation d'abord")   # pas de rattrapage artificiel
        if restart and phase not in ("recuperation", "jour_j", "affutage"):
            if phase in ("developpement", "reprise", "entretien") or long_break: phase = "reprise"
            notes.append((f"{hist['_any_days']} jours sans séance" if idle else f"retour après {gl} jours sans séance") + " : reprise progressive")
        fam_state_d = fam_state.get(disc, "z2")
        cap_d = cap.get(disc, 5)
        if global_easy: cap_d = min(cap_d, 2)
        fam, plan, due, flags = choisir_famille(disc, phase, o, hist, fam_state_d, cap_d, st)
        if o is not None and o not in key_late and key_late and phase in ("reprise", "developpement") and fam in QUALITY:
            if fam != "aerobe" or hist[disc]["q7"] >= 1:                     # maintenir sans concurrencer l'objectif en phase tardive
                fam = "z2"
            flags.append("maintien pendant la phase tardive de « " + key_late[0]["label"] + " »")
        if support and LVL[fam] > 2: fam = "z2"; flags.append("soutien léger pendant la phase tardive d'un autre objectif")
        if easy_restart and LVL[fam] > 2 and phase != "affutage": fam = "z2"
        vol = _vol(phase, o)
        if support: vol = min(vol, .8)
        out["fam"][disc], out["plan_fam"][disc], out["due"][disc] = fam, plan, due
        out["vol"][disc], out["phase"][disc] = vol, phase
        out["gov"][disc] = None if o is None else {"id": o["id"], "label": o["label"], "date": o["date"], "days_left": o["days_left"], "prio": o["prio"], "role": o["role"], "class": o["cls"]}
        out["notes"][disc], out["flags"][disc] = notes, flags
        out["long_cap"][disc] = o["long_cap"] if o else 0
        out["tags"][disc] = sorted(session_tags(o, disc))
        out["prog"][disc] = 0.3 if o is None else max(0.0, min(1.0, 1 - o["weeks_left"] / max(o["prep_weeks"], 1)))
    # renforcement : modulé par la phase la plus tardive
    sp = min((PHASE_RANK.get(out["phase"][d], 9) for d in ("run", "bike", "swim")), default=9)
    out["phase"]["strength"] = "affutage" if any(out["phase"][d] in ("affutage", "jour_j") for d in ("run", "bike", "swim")) else (
        "recuperation" if all(out["phase"][d] == "recuperation" for d in ("run", "bike", "swim")) else "entretien")
    out["fam"]["strength"], out["vol"]["strength"] = "force", (.6 if out["phase"]["strength"] == "affutage" else 1.0)
    # équilibre des disciplines : écart entre la répartition visée par les objectifs et le temps réel sur 14 jours
    share = _target_share(objs)
    tot = sum(hist[d]["min14"] for d in DISCS)
    for d in DISCS:
        b = 0.0
        if share and tot >= 120: b = max(-0.3, min(0.4, 1.0 * (share[d] - hist[d]["min14"] / tot)))
        if d != "strength" and out["phase"][d] in ("recuperation", "jour_j"): b -= 0.3
        if d == "strength" and out["phase"]["strength"] == "affutage": b -= 1.0
        if d != "strength" and out["due"][d] and LVL[out["fam"][d]] >= 3: b += 0.35         # séance clé due et assimilable aujourd'hui
        if d != "strength" and out["phase"][d] == "affutage": b += 0.15
        out["bonus"][d] = round(b, 3)
    out["objs"] = [{"id": o["id"], "label": o["label"], "date": o["date"], "days_left": o["days_left"], "weeks_left": o["weeks_left"], "prio": o["prio"],
                    "role": o["role"], "phase": o["phase"], "kind": o["kind"], "class": o["label"], "weight": o["weight"], "taper_d": o["taper_d"], "rec_d": o["rec_d"]} for o in objs]
    out["share"] = share
    out["hist"] = {d: {k: v for k, v in hist[d].items()} for d in DISCS}
    out["checks"] = verifier(out, hist)
    return out


# =============================================================================================
# 6. COHÉRENCE : règles vérifiées sur la proposition (et correction automatique)
# =============================================================================================
def verifier(pl, hist):
    """Contrôle les règles de cohérence ; corrige la proposition si l'une est violée. Retourne la liste des contrôles."""
    checks = []
    for d in ("run", "bike", "swim"):
        f, ph = pl["fam"][d], pl["phase"][d]
        ok = True
        if ph in ("affutage", "jour_j") and f in ("vo2", "long", "brick", "spec", "trail", "aerobe"): ok = False; pl["fam"][d] = f = "taper" if ph == "affutage" and pl["gov"][d] and pl["gov"][d]["days_left"] > 2 else "z2"
        checks.append(("affûtage protégé", d, ok))
        ok = True
        if ph == "recuperation" and LVL[f] > 2: ok = False; pl["fam"][d] = "z2"
        checks.append(("récupération respectée", d, ok))
        ok = True
        if f in QUALITY and hist[d]["q7"] >= PH[ph]["quota"] and hist[d]["q_days"] < 7 and PH[ph]["quota"]: ok = False; pl["fam"][d] = DOWN[f]
        checks.append(("quota de séances clés", d, ok))
        ok = True
        if f in QUALITY and hist[d]["q_days"] <= 1: ok = False; pl["fam"][d] = DOWN[f]
        checks.append(("48 h entre deux séances clés", d, ok))
    keys = [d for d in ("run", "bike", "swim") if pl["fam"][d] in QUALITY and LVL[pl["fam"][d]] >= 4]
    checks.append(("une seule séance très intense par jour", "all", len(keys) <= 1))
    return checks


def justification(pl, disc, fam):
    """Phrase expliquant pourquoi cette séance aujourd'hui : phase, objectif servi, qualité visée, adaptation."""
    ph, g = pl["phase"].get(disc), (pl["gov"] or {}).get(disc)
    if ph is None: return ""
    ptxt = PHASE_FR[ph]
    if g:
        when = f"J-{g['days_left']}" if g["days_left"] >= 0 else f"J+{-g['days_left']}"
        head = f"{ptxt} · {g['label']} du {_fr(g['date'])} ({when}, objectif {g['role']})"
    else:
        head = f"{ptxt} (aucun objectif ne gouverne cette discipline)"
    s = f"{head} : {INTENT.get(fam, fam)}."
    flags = pl["flags"].get(disc) or []
    notes = pl["notes"].get(disc) or []
    extra = [x for x in (flags + notes) if x]
    if extra: s += " " + "; ".join(extra[:2]).capitalize() + "."
    if ph == "affutage": s += f" Volume réduit à {round(pl['vol'][disc] * 100)} % pour arriver frais en gardant l'intensité."
    return s
