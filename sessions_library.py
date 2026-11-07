"""Bibliothèque de séances d'endurance et de musculation, 100 % déterministe (aucune IA).

20 familles x 10 séances, plus les familles de planification (sortie longue, affûtage, enchaînements vélo-course). Chaque séance : échauffement, corps de séance, retour au calme, durée de base,
zones cibles (allure / puissance / RPE), objectif physiologique, consignes techniques.
Une séance est modulée par le FAF : durée, nombre de répétitions (reps), charge.

Méthodes de référence (repères généraux, volontairement peu nombreux) :
- Course : allures de Daniels (E facile, M marathon, T seuil, I VMA/intervalles, R répétitions) ; modèle polarisé
  de Seiler (environ 80 % du volume facile, le reste intense) ; périodisation base / construction / spécifique de Friel.
- Vélo : zones de puissance de Coggan en % de la FTP (Z1 < 55, Z2 56-75, Z3 76-90, Z4 91-105, Z5 106-120, Z6 121-150),
  « sweet spot » 88-94 % FTP.
- Natation : vitesse critique de nage (CSS, concept de Wakayoshi) : séries de 100 à 400 m à l'allure CSS.
- Musculation : 4 séries de 5 exercices pour la force générale (format 1 h), travail unilatéral et excentrique
  de prévention pour les sports d'endurance, pliométrie légère pour la raideur musculo-tendineuse."""

LIB = {}
INT_LABEL = {1: "très facile", 2: "endurance", 3: "soutenu", 4: "spécifique", 5: "intense"}


def pace(p):
    """allure en min/km (float) -> 4'12"""
    m = int(p); s = int(round((p - m) * 60))
    if s == 60: m, s = m + 1, 0
    return f"{m}'{s:02d}"


def cs(sec):
    """secondes / 100 m -> 1'30"""
    sec = int(round(sec)); return f"{sec // 60}'{sec % 60:02d}"


FAMDEF = {}


def _mk(disc, key, lvl, ref, warms, cools, zones, rows, start=0):
    return [dict(id=f"{disc}.{key}.{start + i + 1:02d}", disc=disc, fam=key, lvl=lvl, ref=ref, name=r[0], min=r[1],
                 n0=r[2], nmin=r[3], main=r[4], goal=r[5], cue=r[6], tags=frozenset(r[7]) if len(r) > 7 else frozenset(),
                 warm=warms[(start + i) % len(warms)], cool=cools[(start + i) % len(cools)], zones=zones)
            for i, r in enumerate(rows)]


def fam(disc, key, lvl, ref, warms, cools, zones, rows):
    """ref : méthode de référence de la famille (documentation). Chaque ligne : (nom, min, n0, nmin, corps, objectif, consigne[, étiquettes d'épreuve])."""
    FAMDEF[(disc, key)] = (lvl, ref, warms, cools, zones)
    LIB[(disc, key)] = _mk(disc, key, lvl, ref, warms, cools, zones, rows)


def add(disc, key, rows):
    """Enrichit une famille existante (mêmes échauffement, retour au calme et zones)."""
    lvl, ref, warms, cools, zones = FAMDEF[(disc, key)]
    LIB[(disc, key)] += _mk(disc, key, lvl, ref, warms, cools, zones, rows, start=len(LIB[(disc, key)]))


def tag(disc, key, names, tags):
    """Étiquette des séances existantes par leur nom (début de nom accepté)."""
    for s in LIB[(disc, key)]:
        if any(s["name"].startswith(n) for n in names): s["tags"] = frozenset(tags)


def pick(lst, want, k):
    """Choix déterministe d'une séance : celles étiquetées pour l'épreuve visée (doublées) + les séances polyvalentes ; les séances propres à une autre épreuve sont écartées.
    k : entier de rotation (hash fixe + n° du jour) ; deux jours consécutifs ne donnent jamais la même séance."""
    want = set(want or ())
    if want:
        m = [s for s in lst if s["tags"] & want]
        sr = [s for s in m if "swimrun" in s["tags"]] if "swimrun" in want else []          # swimrun : séances propres à l'épreuve favorisées par rapport aux séances de trail génériques
        if len(sr) >= 2: m = sr + sr + [s for s in m if s not in sr]
        elif len(m) >= 2: m = m * 2
        pool = m + [s for s in lst if not s["tags"]]                                          # doublées seulement si elles ne peuvent pas se suivre
        if len(set(s["id"] for s in pool)) >= 2: return pool[k % len(pool)]
    base = [s for s in lst if "swimrun" not in s["tags"]]                                  # séances propres au swimrun (chaussures dans l'eau...) : seulement pour un objectif swimrun
    if "swimrun" not in want and len(base) >= 2: lst = base
    return lst[k % len(lst)]


def _ex(*items):
    return "{n} séries par exercice :\n" + "\n".join(f"{i + 1}. {x}" for i, x in enumerate(items))


# =============================================================================================
# COURSE À PIED
# =============================================================================================
fam("run", "recup", 1, "Daniels E-pace bas ; zone 1 de Seiler",
    ["5 min de marche rapide, mobilité chevilles et hanches", "3 min de marche + 10 rotations de hanches"],
    ["5 min de marche, étirements doux", "5 min de marche + respiration lente"],
    "Très facile : {z1} (RPE 1-2/10), conversation fluide",
    [("Footing de décrassage", 30, 0, 0, "30 min continues à {z1}, terrain plat", "Favoriser la circulation sanguine sans stress mécanique", "Foulée courte, cadence aisée (170 ou plus), aucune accélération."),
     ("Footing et gammes", 35, 0, 0, "25 min à {z1} puis 6 gammes de 20 m (montées de genoux, talons-fesses), marche pour revenir", "Entretenir la coordination sans fatigue", "Rester relâché, épaules basses, gammes sans forcer."),
     ("Marche-course", 35, 4, 2, "{n} × (6 min de trot à {z1} + 2 min de marche)", "Réduire l'impact tout en gardant le geste de course", "Marche active pendant les pauses, ne pas sprinter les trots."),
     ("Footing sur terrain souple", 35, 0, 0, "35 min à {z1} sur herbe ou chemin plat", "Diminuer les chocs articulaires", "Regarder 5 m devant, appuis souples et silencieux."),
     ("Footing et lignes droites souples", 30, 4, 2, "25 min à {z1} puis {n} × 15 s de lignes droites relâchées (récupération 45 s de marche)", "Entretenir la fréquence de foulée sans coût énergétique", "Accélérer à peine, environ 70 % de la vitesse max, jamais à bout de souffle."),
     ("Footing technique cadence", 30, 0, 0, "10 min à {z1}, 10 min en cadence 175-180 pas/min (métronome), 10 min libres", "Améliorer l'économie de course", "Pas courts sous le centre de gravité, buste droit."),
     ("Footing lent et mobilité", 40, 0, 0, "30 min à {z1} puis 10 min de mobilité (hanches, ischios, mollets)", "Soutenir la récupération articulaire", "Ne cherche pas l'allure : montre dans la poche."),
     ("Trot nature à la sensation", 30, 0, 0, "30 min à la sensation (RPE 2/10), sans montre, sur sentier plat", "Retrouver de bonnes sensations", "Choisir le rythme où la respiration reste nasale."),
     ("Footing court avant jour off", 25, 0, 0, "25 min à {z1} puis 3 min d'étirements dynamiques", "Maintenir la routine sans charge", "Arrêter avant l'envie de s'arrêter."),
     ("Footing et éducatifs de pied", 30, 0, 0, "25 min à {z1} puis 4 × 30 s de marche sur talons / sur pointes", "Réactiver la voûte plantaire et les mollets", "Mouvements lents et contrôlés.")])

fam("run", "z2", 2, "Seiler zone 1 (volume facile) ; Daniels E-pace ; phase de base de Friel",
    ["5 min de marche + 5 min de trot progressif", "10 min de trot très facile"],
    ["5 min de marche + étirements", "5 min de trot lent + mobilité"],
    "Endurance fondamentale : {z2} (RPE 3-4/10), respiration nasale possible",
    [("Footing continu 50 min", 50, 0, 0, "50 min continues à {z2}", "Développer la base aérobie et la densité capillaire", "Régularité d'allure, foulée détendue, hydratation avant et après."),
     ("Footing continu 60 min", 60, 0, 0, "60 min continues à {z2}", "Augmenter le volume aérobie", "Garder le même effort du début à la fin."),
     ("Footing continu 70 min", 70, 0, 0, "70 min continues à {z2}", "Développer l'endurance musculaire", "Boire quelques gorgées toutes les 20 min."),
     ("Footing long 80 min", 80, 0, 0, "80 min à {z2}", "Améliorer l'utilisation des graisses à l'effort", "Ne pas forcer en fin de séance."),
     ("Sortie longue 90 min", 90, 0, 0, "90 min à {z2}, ravitaillement à partir de 60 min", "Renforcer la résistance à la fatigue", "S'alimenter (30 à 60 g de glucides par heure au-delà de 75 min)."),
     ("Footing progressif", 60, 0, 0, "45 min à {z2} puis 15 min légèrement plus vite (environ 10 s/km), sous RPE 5/10", "Entraîner la fin de séance sans intensité", "Accélérer en douceur, jamais de coup de rein."),
     ("Footing et lignes droites", 55, 6, 3, "45 min à {z2} puis {n} × 20 s de lignes droites (récupération 40 s de trot)", "Garder la vivacité pendant la phase de volume", "Lignes droites relâchées, genoux hauts."),
     ("Footing vallonné à effort constant", 60, 0, 0, "60 min sur parcours vallonné en gardant un effort constant (RPE 4/10), l'allure varie avec le relief", "Développer la force endurance sans intensité", "Raccourcir la foulée en montée, relâcher en descente."),
     ("Footing en deux blocs", 60, 0, 0, "2 × 30 min à {z2} séparés de 5 min de marche", "Accumuler du volume avec moins de fatigue mentale", "Reprendre à la même allure après la pause."),
     ("Footing négatif 65 min", 65, 0, 0, "65 min : 1re moitié à {z2}, 2e moitié légèrement plus rapide (environ 10 s/km), toujours sous RPE 5/10", "Apprendre à gérer l'allure", "La seconde moitié doit paraître facile.")])

fam("run", "aerobe", 3, "Daniels T-pace ; seuil lactique ; développement aérobie de Friel",
    ["15 min de footing facile + 4 lignes droites", "10 min de trot + éducatifs + 3 lignes droites"],
    ["10 min de footing facile", "10 min de trot lent + étirements"],
    "Seuil : {thr} (RPE 7/10, confortablement dur) ; allure marathon : {mar}",
    [("3 × 10 min au seuil", 60, 3, 2, "{n} × 10 min à {thr}, récupération 2 min 30 de trot", "Relever le seuil lactique", "Régularité : la dernière répétition au même rythme que la première."),
     ("2 × 15 min au seuil", 65, 2, 1, "{n} × 15 min à {thr}, récupération 3 min de trot", "Soutenir le seuil plus longtemps", "Départ prudent sur la première minute."),
     ("20 min continues au seuil", 55, 1, 1, "20 min continues à {thr}", "Habituer l'organisme à l'effort continu au seuil", "Respiration contrôlée, buste relâché."),
     ("4 × 8 min au seuil", 60, 4, 2, "{n} × 8 min à {thr}, récupération 2 min de trot", "Accumuler du temps au seuil avec peu de fatigue", "Garder la même foulée sur chaque répétition."),
     ("5 × 6 min (cruise intervals)", 60, 5, 3, "{n} × 6 min à {thr}, récupération 1 min de trot", "Accumuler du volume au seuil avec des récupérations courtes", "Récupération active, sans s'arrêter."),
     ("30 min à allure semi-marathon", 60, 1, 1, "30 min continues à {thr}", "Développer l'endurance au seuil", "Ne pas partir plus vite que {thr}."),
     ("Progressif 40 min", 60, 1, 1, "40 min progressives : 15 min à {z2}, 15 min à {mar}, 10 min à {thr}", "Entraîner la progressivité et l'économie de course", "Chaque palier plus rapide que le précédent, jamais l'inverse."),
     ("3 × 12 min à allure marathon", 65, 3, 2, "{n} × 12 min à {mar}, récupération 2 min de trot", "Automatiser l'allure marathon", "Détendre les épaules, cadence régulière."),
     ("Pyramide 5-10-15-10-5 min", 70, 1, 1, "5, 10, 15, 10 puis 5 min à {thr}, récupération 2 min de trot entre chaque bloc", "Varier le travail au seuil", "Garder la même allure sur tous les blocs."),
     ("2 × 20 min à allure marathon", 70, 2, 1, "{n} × 20 min à {mar}, récupération 3 min de trot", "Soutenir l'allure marathon sur la durée", "Alimentation et hydratation comme en course.")])

fam("run", "vo2", 5, "Daniels I-pace et R-pace ; stimulation haute intensité du modèle polarisé de Seiler",
    ["20 min de footing, éducatifs, 4 lignes droites", "15 min de trot + gammes + 3 accélérations progressives"],
    ["10-12 min de footing très facile", "10 min de trot lent + marche"],
    "VMA / intervalles : {vma} (RPE 8-9/10) ; récupérations en trot lent ({z1})",
    [("10 × 400 m", 55, 10, 5, "{n} × 400 m à {vma}, récupération 200 m de trot", "Améliorer la VO2max et l'économie à haute vitesse", "Même chrono sur chaque répétition, arrêter si l'allure chute de plus de 5 %."),
     ("6 × 800 m", 60, 6, 3, "{n} × 800 m à {vma}, récupération 400 m de trot", "Soutenir la VO2max plus longtemps", "Départ contrôlé : les 200 premiers mètres comptent."),
     ("5 × 1000 m", 65, 5, 3, "{n} × 1000 m à {vma}, récupération 2 min de trot", "Développer la puissance aérobie maximale", "Regard loin devant, épaules basses."),
     ("8 × 500 m", 60, 8, 4, "{n} × 500 m à {vma}, récupération 200 m de trot", "Entretenir la VMA avec un volume modéré", "Régularité avant vitesse."),
     ("6 × 300 m rapides", 55, 6, 3, "{n} × 300 m à environ 5 s/km plus vite que {vma}, récupération 3 min de marche-trot", "Stimuler la filière anaérobie lactique", "Récupération complète : chaque répétition doit rester rapide."),
     ("2 × 10 × 30''/30''", 55, 10, 6, "2 séries de {n} × (30 s vite à {vma} / 30 s de trot), 4 min de récupération entre les séries", "Accumuler du temps proche de la VO2max", "Les 30 s de trot sont de vraies récupérations."),
     ("4 × 1200 m", 70, 4, 2, "{n} × 1200 m à {vma}, récupération 2 min 30 de trot", "Durcir la VO2max sur des efforts longs", "Rester sous le seuil de douleur : effort 8/10."),
     ("3 × (4 × 200 m)", 60, 4, 3, "3 séries de {n} × 200 m à {vma}, récupération 100 m de trot, 3 min entre les séries", "Travailler la vitesse et la foulée", "Foulée longue et relâchée, pas de crispation."),
     ("15 × 1 min", 55, 15, 8, "{n} × 1 min vite / 1 min de trot", "Développer la capacité à répéter des efforts", "Garder le même rythme sur toutes les répétitions."),
     ("Pyramide 400-800-1200-800-400 m", 65, 1, 1, "400, 800, 1200, 800 puis 400 m à {vma}, récupération égale à la moitié de la durée de l'effort en trot", "Varier la stimulation de la VO2max", "Gérer l'effort, la répétition de 1200 m est la plus exigeante.")])

fam("run", "spec", 4, "Spécificité (allure de course) ; semaines de construction de Friel ; Daniels M et T",
    ["20 min de footing + éducatifs + 3 lignes droites", "15 min de trot + gammes + 2 × 1 min à allure course"],
    ["10 min de footing facile", "10 min de trot lent + étirements"],
    "10 km : {p10} · semi : {thr} · marathon : {mar}",
    [("5 × 2000 m à allure 10 km", 65, 5, 3, "{n} × 2000 m à {p10}, récupération 90 s de trot", "Ancrer l'allure 10 km", "Chrono régulier, respiration maîtrisée."),
     ("4 × 2500 m à allure 10 km", 70, 4, 2, "{n} × 2500 m à {p10}, récupération 2 min de trot", "Soutenir l'allure 10 km sur de longues séquences", "Les derniers 500 m de chaque répétition au même rythme."),
     ("8 × 1000 m à allure 10 km", 65, 8, 5, "{n} × 1000 m à {p10}, récupération 1 min de trot", "Accumuler du volume à l'allure 10 km", "Récupération courte : rester relâché."),
     ("Sortie longue spécifique marathon", 120, 1, 1, "24 km dont 12 km à {mar} (du km 8 au km 20), le reste en endurance", "Spécifique marathon", "Tester alimentation, hydratation et équipement de course."),
     ("2 × 8 km à allure marathon", 85, 2, 1, "{n} × 8 km à {mar}, récupération 3 min de trot", "Automatiser l'allure marathon", "Cadence et foulée stables, aucun excès."),
     ("3 × 5 km à allure marathon", 80, 3, 2, "{n} × 5 km à {mar}, récupération 3 min de trot", "Consolider l'allure marathon avec des coupures", "Rester à l'allure même si les sensations sont bonnes."),
     ("Enchaînement vélo-course (brick)", 80, 1, 1, "45 min de vélo à 75-85 % de la FTP puis 20 min de course à {mar}, transition en moins de 2 min", "Spécifique triathlon : habituer les jambes à courir après le vélo", "Cadence élevée en fin de vélo, foulée courte les 5 premières minutes."),
     ("Progressif long 20 km", 110, 1, 1, "20 km : 10 km à {z2}, 6 km à {mar}, 4 km à {thr}", "Spécifique marathon : finir fort", "Chaque palier plus rapide que le précédent."),
     ("Test 5 km contrôlé", 45, 1, 1, "5 km à effort soutenu mais maîtrisé (environ 5 s/km plus vite que {p10})", "Évaluer la forme actuelle", "Départ prudent, accélération sur le dernier kilomètre."),
     ("4 × 3 km à allure semi-marathon", 70, 4, 2, "{n} × 3 km à {thr}, récupération 1 min 30 de trot", "Développer l'endurance au seuil", "Cadence régulière, buste relâché.")])

fam("run", "trail", 3, "Trail : force-endurance en côte, technique de descente, sortie longue en dénivelé",
    ["15 min de footing en terrain varié + éducatifs", "10 min de marche active + 10 min de trot sur sentier"],
    ["10 min de marche et trot facile", "10 min de trot lent + étirements"],
    "Effort : montées RPE 6-7/10, descentes contrôlées, plat {z2}",
    [("Côtes courtes 8 × 1 min", 60, 8, 4, "{n} × 1 min en côte à 8-10 % (effort 5 km), redescente en trot", "Développer la force et la puissance en montée", "Pas courts, buste incliné, bras actifs."),
     ("Côtes longues 5 × 3 min", 65, 5, 3, "{n} × 3 min en côte à 6-8 %, redescente en trot", "Développer l'endurance en côte", "Garder le même effort du début à la fin de chaque montée."),
     ("Sortie longue trail 18 km, D+ 800 m", 150, 1, 1, "18 km sur sentiers avec 800 m de D+, marche active au-delà de 12 %", "Endurance spécifique trail", "Ne pas partir trop vite sur la première montée."),
     ("Sortie longue trail 22 km, D+ 1000 m", 180, 1, 1, "22 km sur sentiers avec 1000 m de D+, alimentation toutes les 30 min", "Tester l'alimentation et le matériel de course", "Marche en côte raide, relance sur le plat."),
     ("Technique de descente 6 × 2 min", 60, 6, 3, "{n} × 2 min de descente technique à vitesse maîtrisée, remontée en marche", "Renforcer les quadriceps et la technique de descente", "Regard 3 m devant, pas courts, genoux fléchis."),
     ("Fartlek vallonné 45 min", 55, 1, 1, "45 min sur terrain vallonné : alterner 2 min soutenues / 2 min faciles selon le relief", "Varier les rythmes en conditions réelles", "Laisser le relief dicter l'effort."),
     ("Escaliers 10 × 40 s", 55, 10, 5, "{n} × 40 s d'escaliers (une marche sur deux), descente en marchant", "Développer la puissance des jambes", "Appuis francs, poussée par le talon."),
     ("Rando-course 2 h", 120, 1, 1, "2 h en alternant course facile sur le plat et marche rapide en montée", "Accumuler des heures sur les jambes avec peu de choc", "Bâtons si possible pour s'entraîner à les utiliser."),
     ("Bâtons et nutrition 75 min", 75, 3, 2, "75 min dont {n} × 15 min de montée avec bâtons, tester un apport de 40-60 g de glucides par heure", "Préparer le matériel et la stratégie nutritionnelle", "Coordination bras-jambes, poignets souples."),
     ("Boucles montée-descente", 65, 4, 2, "{n} boucles de 6 min de montée soutenue + 4 min de descente à vitesse maîtrisée", "Spécifique trail : alterner effort et récupération active", "Régularité des temps de boucle.")])

# =============================================================================================
# VÉLO (zones de Coggan en % de la FTP)
# =============================================================================================
fam("bike", "recup", 1, "Coggan Z1 ; récupération active",
    ["5 min très souples (moins de 40 % FTP)", "5 min de pédalage progressif"],
    ["5 min de pédalage souple", "5 min de pédalage souple + étirements"],
    "Z1 : {z1w} ; cadence 90-100 tr/min ; RPE 1-2/10",
    [("Pédalage de récupération 45 min", 45, 0, 0, "45 min à {z1w}, terrain plat", "Favoriser la circulation sans stress mécanique", "Cadence fluide, aucune résistance."),
     ("Rouleaux souples 40 min", 40, 0, 0, "40 min à {z1w} sur home-trainer", "Récupérer en environnement contrôlé", "Maintenir la puissance sous le plafond, même si les jambes en veulent plus."),
     ("Sortie plate 60 min", 60, 0, 0, "60 min à {z1w} sur parcours plat", "Entretenir le volume sans fatigue", "Rester sur les plus grands plateaux uniquement si la cadence reste fluide."),
     ("Cadence haute 6 × 1 min", 45, 6, 3, "45 min à {z1w} dont {n} × 1 min à 105-110 tr/min", "Améliorer la souplesse de pédalage", "Bassin stable, pas de rebond sur la selle."),
     ("Souplesse une jambe", 45, 6, 3, "{n} × 1 min une jambe (alternance) à {z1w}, puis 35 min libres à {z1w}", "Améliorer la coordination du coup de pédale", "Éviter la phase morte en haut de pédale."),
     ("Sortie nature 50 min", 50, 0, 0, "50 min à {z1w} sur routes calmes", "Récupération active en plein air", "Regarder le paysage, pas le compteur."),
     ("Vélo et étirement 45 min", 45, 0, 0, "35 min à {z1w} puis 10 min d'étirements (fléchisseurs de hanche, quadriceps)", "Entretenir la mobilité", "Étirements sans douleur."),
     ("Pyramide de cadence 40 min", 40, 0, 0, "40 min à {z1w} avec cadences 85-95-105-95-85 tr/min par paliers de 4 min", "Varier la cadence sans charge", "Garder la puissance constante, seule la cadence change."),
     ("Spin-ups 5 × 30 s", 45, 5, 3, "45 min à {z1w} dont {n} × 30 s de cadence rapide (110 tr/min)", "Réveiller le système neuromusculaire", "Accélérer la cadence, pas la puissance."),
     ("Sortie café 60 min", 60, 0, 0, "60 min à {z1w} sur parcours plat, conversation facile", "Maintenir la routine", "RPE 2/10 du début à la fin.")])

fam("bike", "z2", 2, "Coggan Z2 ; volume facile du modèle polarisé de Seiler ; phase de base de Friel",
    ["10 min progressifs de {z1w} à {z2w}", "10 min à {z1w} + 3 × 30 s de cadence rapide"],
    ["10 min de pédalage souple", "5 min souples + étirements"],
    "Z2 : {z2w} (56-75 % FTP) ; cadence 85-95 tr/min ; RPE 3-4/10",
    [("Z2 90 min", 90, 0, 0, "90 min continues à {z2w}", "Développer la base aérobie", "Puissance régulière, hydratation toutes les 20 min."),
     ("Z2 120 min", 120, 0, 0, "120 min continues à {z2w}", "Augmenter l'endurance de base", "Manger 40 à 60 g de glucides par heure."),
     ("Z2 150 min", 150, 0, 0, "150 min à {z2w}", "Développer la résistance à la fatigue", "Ne pas dépasser le haut de la zone en début de sortie."),
     ("Z2 180 min", 180, 0, 0, "180 min à {z2w}, ravitaillement régulier", "Endurance longue (sortie de week-end)", "Boire, manger, rester sous le seuil même en côte."),
     ("2 × 60 min Z2", 120, 2, 1, "{n} × 60 min à {z2w}, 5 min de pédalage souple entre les blocs", "Accumuler du volume en deux blocs", "Reprendre à la même puissance après la pause."),
     ("Z2 cadence variable 120 min", 120, 0, 0, "120 min à {z2w} en alternant des blocs de 10 min à 85, 95 et 100 tr/min", "Travailler la cadence en endurance", "Garder la puissance constante."),
     ("Z2 vallonné 90 min", 90, 0, 0, "90 min sur parcours vallonné en restant dans {z2w} même en côte", "Contrôler l'effort sur le relief", "Passer les pignons légers avant les côtes."),
     ("Z2 force-endurance 105 min", 105, 3, 2, "105 min à {z2w} dont {n} × 10 min à 60 tr/min en bas de zone (force-endurance)", "Développer la force sans intensité", "Dos stable, jamais de balancement du buste."),
     ("Z2 et sprints 105 min", 105, 6, 3, "105 min à {z2w} dont {n} × 15 s de sprint relâché (récupération 5 min)", "Garder de la vivacité en volume", "Sprint court et frais, pas un effort maximal."),
     ("Z2 progressive 120 min", 120, 0, 0, "120 min : 40 min en bas de {z2w}, 40 min au milieu, 40 min en haut de zone", "Entraîner la progressivité", "Garder la même cadence sur les trois blocs.")])

fam("bike", "aerobe", 3, "Coggan Z3-Z4 ; sweet spot 88-94 % FTP ; développement aérobie",
    ["15 min progressifs + 3 × 1 min à {z3w}", "10 min à {z2w} + 2 × 2 min à {z3w}"],
    ["10 min de pédalage souple", "10 min souples + étirements"],
    "Sweet spot : {ssw} ; tempo : {z3w} ; seuil : {thw} ; FTP de référence {ftp}",
    [("3 × 12 min sweet spot", 90, 3, 2, "{n} × 12 min à {ssw}, récupération 5 min à {z1w}", "Relever la puissance au seuil avec un coût de récupération modéré", "Cadence 85-95 tr/min, position stable."),
     ("2 × 20 min sweet spot", 90, 2, 1, "{n} × 20 min à {ssw}, récupération 5 min à {z1w}", "Soutenir la puissance au seuil", "Départ prudent sur la première minute."),
     ("4 × 10 min sweet spot", 90, 4, 2, "{n} × 10 min à {ssw}, récupération 4 min à {z1w}", "Accumuler du temps au sweet spot", "Même puissance sur chaque répétition."),
     ("3 × 15 min sweet spot", 100, 3, 2, "{n} × 15 min à {ssw}, récupération 5 min à {z1w}", "Développer l'endurance au seuil", "Hydratation à chaque récupération."),
     ("5 × 8 min sweet spot", 85, 5, 3, "{n} × 8 min à {ssw}, récupération 3 min à {z1w}", "Accumuler du volume avec des récupérations courtes", "Garder la nuque et les épaules relâchées."),
     ("Tempo continu 45 min", 80, 1, 1, "45 min continues à {z3w}", "Développer l'endurance musculaire", "Puissance régulière, cadence 85-90 tr/min."),
     ("Over-unders 3 × 12 min", 90, 3, 2, "{n} × 12 min en alternant 2 min à {thw} et 2 min à {z3w}, récupération 5 min à {z1w}", "Entraîner la capacité à encaisser puis éliminer le lactate", "Ne pas s'arrêter pendant les phases « under »."),
     ("2 × 25 min tempo", 100, 2, 1, "{n} × 25 min à {z3w}, récupération 5 min à {z1w}", "Développer l'endurance au tempo", "Position aérodynamique confortable."),
     ("3 × 20 min tempo", 110, 3, 2, "{n} × 20 min à {z3w}, récupération 5 min à {z1w}", "Accumuler du volume en zone 3", "Alimentation régulière."),
     ("2 × 15 min au seuil", 85, 2, 1, "{n} × 15 min à {thw}, récupération 6 min à {z1w}", "Relever la FTP", "Chaque minute compte, pas de départ trop rapide.")])

fam("bike", "vo2", 5, "Coggan Z5-Z6 ; stimulation haute intensité du modèle polarisé de Seiler",
    ["20 min progressifs + 3 × 1 min à {vo2w}", "15 min à {z2w} + 3 × 30 s à {anw}"],
    ["10 min de pédalage très souple", "10 min souples + étirements"],
    "VO2max : {vo2w} (106-120 % FTP) ; anaérobie : {anw} ; récupérations à {z1w}",
    [("5 × 4 min VO2max", 75, 5, 3, "{n} × 4 min à {vo2w}, récupération 4 min à {z1w}", "Développer la puissance aérobie maximale", "Cadence 95-105 tr/min, respiration profonde."),
     ("6 × 3 min VO2max", 75, 6, 3, "{n} × 3 min à {vo2w}, récupération 3 min à {z1w}", "Accumuler du temps proche de la VO2max", "Départ à la puissance cible, sans pic."),
     ("4 × 5 min VO2max", 80, 4, 2, "{n} × 5 min à {vo2w}, récupération 5 min à {z1w}", "Soutenir la VO2max longtemps", "Effort 8-9/10, jamais au-delà."),
     ("8 × 2 min VO2max", 70, 8, 4, "{n} × 2 min à {anw}, récupération 2 min à {z1w}", "Développer la puissance au-dessus de la VO2max", "Garder la même puissance sur la dernière répétition."),
     ("10 × 1 min", 65, 10, 5, "{n} × 1 min à {anw}, récupération 1 min à {z1w}", "Améliorer la tolérance à l'effort court", "Rester sur la selle, cadence élevée."),
     ("30''/30'' en 2 séries", 70, 10, 6, "2 séries de {n} × (30 s à {anw} / 30 s à {z1w}), 5 min de récupération entre les séries", "Accumuler du temps haute intensité", "Respirer par le ventre."),
     ("6 × 30 s lactique", 65, 6, 3, "{n} × 30 s à effort maximal, récupération 4 min à {z1w}", "Stimuler la filière lactique", "Récupération complète entre chaque effort."),
     ("Pyramide 1-2-3-4-3-2-1 min", 75, 1, 1, "1, 2, 3, 4, 3, 2 puis 1 min à {vo2w}, récupération égale à la durée de l'effort à {z1w}", "Varier la stimulation de la VO2max", "Gérer l'effort : le bloc de 4 min est le plus dur."),
     ("3 × (3 × 1 min)", 70, 3, 2, "{n} séries de 3 × 1 min à {anw}, récupération 1 min entre les efforts, 5 min entre les séries", "Répéter des efforts courts intenses", "Qualité avant quantité."),
     ("4 × 4 min et sprint final", 80, 4, 2, "{n} × 4 min à {vo2w}, récupération 4 min à {z1w}, avec un sprint de 10 s en fin de dernière répétition", "Développer la VO2max et la finition", "Garder le sprint pour la fin.")])

fam("bike", "spec", 4, "Spécificité triathlon : position aéro, enchaînement, simulation de course",
    ["15 min progressifs + 3 × 1 min à {z3w}", "10 min à {z2w} + 3 × 30 s de cadence rapide"],
    ["10 min de pédalage souple", "10 min souples + étirements"],
    "Allure course longue distance : {z3w} ; seuil : {thw} ; Z2 : {z2w}",
    [("Brick 60 min vélo + 20 min course", 80, 1, 1, "60 min de vélo (45 min à {z3w}) puis transition et 20 min de course à allure marathon", "Habituer les jambes à courir après le vélo", "Cadence élevée en fin de vélo, foulée courte au début de la course."),
     ("Contre-la-montre 2 × 20 min", 90, 2, 1, "{n} × 20 min à {thw} en position aéro, récupération 6 min à {z1w}", "Travailler la puissance en position aérodynamique", "Position stable, regard loin devant."),
     ("3 × 15 min en position aéro", 90, 3, 2, "{n} × 15 min à {z3w} en position aéro, récupération 5 min à {z1w}", "Confort et puissance en position de course", "Épaules relâchées, respiration profonde."),
     ("Sortie 3 h avec blocs de course", 180, 3, 2, "180 min à {z2w} dont {n} × 20 min à {z3w}", "Simuler la course longue distance", "Alimenter 60 à 90 g de glucides par heure."),
     ("Simulation de transition", 75, 4, 2, "{n} × (10 min à {z3w} + 3 min à {z2w}), avec 2 changements de position aéro / position haute", "Gérer les alternances d'effort", "Boire et manger sur les phases faciles."),
     ("Vallonné type course", 100, 1, 1, "100 min sur parcours vallonné : montées à {thw}, descentes et plat à {z2w}", "Gérer l'effort sur le relief", "Passer la montée en souplesse, éviter les pics de puissance."),
     ("2 h dont 30 min finales soutenues", 120, 1, 1, "90 min à {z2w} puis 30 min à {z3w}", "Apprendre à finir fort", "Fin de séance sans baisse de cadence."),
     ("Aéro endurance 2 × 30 min", 100, 2, 1, "{n} × 30 min à {z2w} (haut de zone) en position aéro, récupération 5 min", "S'habituer à la position sur la durée", "Alterner mains et position pour éviter les tensions."),
     ("Brick court 45 min + 10 min course", 60, 1, 1, "45 min de vélo à {z3w} puis 10 min de course à allure 10 km", "Réveiller la transition sans fatigue excessive", "Réduire la cadence avant de descendre du vélo."),
     ("Technique virages et descentes", 60, 1, 1, "60 min sur parcours sinueux : 6 passages de virages à vitesse progressive et 4 descentes en position basse", "Améliorer la technique de pilotage", "Regard sur la sortie du virage, freinage avant, jamais dedans.")])

# =============================================================================================
# NATATION (allure CSS)
# =============================================================================================
fam("swim", "recup", 1, "Éducatifs techniques ; nage souple",
    ["200 m souples variés (crawl/dos)", "300 m souples + 4 × 25 m d'éducatifs"],
    ["100 m dos souple", "100 m souples tous nages"],
    "Souple : {z1s}/100 m (RPE 2/10), accent sur la glisse et l'allongement",
    [("Technique : rattrapé", 40, 6, 3, "{n} × 100 m en rattrapé (catch-up), repos 20 s", "Allonger la glisse", "Attendre la main avant de démarrer le bras opposé."),
     ("Technique : poings fermés", 40, 8, 4, "{n} × 50 m alternés poings fermés / nage normale, repos 15 s", "Améliorer la sensation d'appui", "Utiliser l'avant-bras pour tirer."),
     ("Technique : 6-3-6", 40, 6, 3, "{n} × 100 m en éducatif 6 battements - 3 mouvements - 6 battements, repos 20 s", "Travailler l'équilibre et la rotation", "Rotation de hanche avant l'épaule."),
     ("Technique : une main", 40, 8, 4, "{n} × 50 m en nage à un bras (alternance), repos 15 s", "Isoler la phase de traction", "Bras inactif devant, tête alignée."),
     ("Technique : respiration bilatérale", 40, 6, 3, "{n} × 100 m en respiration tous les 3 mouvements, repos 20 s", "Équilibrer la nage", "Expirer dans l'eau, pas hors de l'eau."),
     ("Technique : jambes", 35, 8, 4, "{n} × 50 m de battements avec planche, repos 20 s", "Améliorer le battement", "Battements depuis la hanche, chevilles souples."),
     ("Technique : coulée et glisse", 35, 8, 4, "{n} × 25 m en coulée longue après chaque mur puis nage libre", "Optimiser la glisse", "Position hydrodynamique : bras tendus, tête neutre."),
     ("Pull-buoy souple", 40, 6, 3, "{n} × 100 m au pull-buoy, repos 15 s", "Concentrer le travail sur le haut du corps", "Bassin haut, ne pas relever la tête."),
     ("Mix 4 nages souples", 40, 6, 3, "{n} × 100 m en alternant crawl, dos, brasse et papillon facile, repos 20 s", "Varier les appuis articulaires", "Amplitude plus que vitesse."),
     ("Technique : visée tête haute", 35, 6, 3, "{n} × 50 m dont 6 mouvements tête haute puis nage normale, repos 20 s", "Préparer l'orientation en eau libre", "Soulever seulement les yeux.")])

fam("swim", "z2", 2, "Endurance de base ; volume facile du modèle polarisé",
    ["400 m souples (200 crawl + 4 × 50 éducatifs)", "300 m souples + 4 × 50 m progressifs"],
    ["200 m souples", "100 m dos souple"],
    "Endurance : {z2s}/100 m (RPE 3-4/10), respiration régulière",
    [("2000 m continus", 50, 0, 0, "2000 m en continu à {z2s}/100 m", "Développer l'endurance de nage", "Régularité de l'allure, nage longue."),
     ("4 × 500 m", 55, 4, 2, "{n} × 500 m à {z2s}/100 m, repos 20 s", "Accumuler du volume aérobie", "Garder le même nombre de mouvements par longueur."),
     ("3 × 800 m", 60, 3, 2, "{n} × 800 m à {z2s}/100 m, repos 30 s", "Soutenir l'endurance longue", "Vérifier la technique à chaque mur."),
     ("6 × 300 m au pull", 50, 6, 3, "{n} × 300 m au pull-buoy à {z2s}/100 m, repos 20 s", "Développer l'endurance du haut du corps", "Bassin haut, traction longue."),
     ("2400 m continus", 55, 0, 0, "2400 m en continu à {z2s}/100 m", "Augmenter la capacité d'endurance", "Respirer par 3 mouvements."),
     ("5 × 400 m", 55, 5, 3, "{n} × 400 m à {z2s}/100 m, repos 20 s", "Accumuler du volume en blocs courts", "Chronométrer chaque 400 m pour garder la régularité."),
     ("1500 m + 10 × 50 m", 50, 10, 5, "1500 m à {z2s}/100 m puis {n} × 50 m à {z3s}/100 m, repos 15 s", "Finir avec un peu de vitesse", "Allonger la nage sur les 50 m rapides."),
     ("Nage régulière 20 min", 45, 1, 1, "20 min de nage continue à {z2s}/100 m, comptage des longueurs", "Gérer l'effort en continu", "Chronomètre ignoré, sensation seulement."),
     ("1000 m + 4 × 200 m", 55, 4, 2, "1000 m à {z2s}/100 m puis {n} × 200 m à {z3s}/100 m, repos 20 s", "Mélanger endurance et allure soutenue", "Rester relâché."),
     ("Pyramide d'endurance", 55, 1, 1, "200, 300, 400, 300 puis 200 m à {z2s}/100 m, repos 20 s entre les blocs", "Varier la distance des efforts", "Même allure du début à la fin.")])

fam("swim", "aerobe", 3, "Vitesse critique de nage (CSS) ; seuil aérobie",
    ["400 m souples + 4 × 50 m progressifs", "300 m souples + 4 × 25 m éducatifs + 2 × 50 m à {z3s}/100 m"],
    ["200 m souples", "200 m dos souple"],
    "Allure CSS : {css}/100 m (RPE 7/10) ; tempo : {z3s}/100 m ; endurance : {z2s}/100 m",
    [("8 × 100 m à la CSS", 55, 8, 4, "{n} × 100 m à {css}/100 m, repos 15 s", "Relever la vitesse critique", "Départ contrôlé, même chrono sur chaque 100 m."),
     ("5 × 200 m à la CSS", 60, 5, 3, "{n} × 200 m à {css}/100 m, repos 20 s", "Soutenir la CSS sur la durée", "Garder le même nombre de mouvements par longueur."),
     ("3 × 400 m à la CSS", 60, 3, 2, "{n} × 400 m à {css}/100 m, repos 30 s", "Développer l'endurance au seuil", "Les 100 derniers mètres comme les 100 premiers."),
     ("10 × 100 m, repos court", 60, 10, 5, "{n} × 100 m à {css}/100 m, repos 10 s", "Améliorer la capacité à répéter l'effort", "Repos court : respirer profondément."),
     ("4 × 300 m", 60, 4, 2, "{n} × 300 m à {css}/100 m, repos 25 s", "Soutenir l'allure seuil", "Technique stable en fin de série."),
     ("2 × (4 × 150 m)", 60, 4, 2, "2 séries de {n} × 150 m à {css}/100 m, repos 15 s, 1 min entre les séries", "Accumuler du temps au seuil", "Garder le même rythme sur les deux séries."),
     ("20 × 50 m", 55, 20, 10, "{n} × 50 m à {css}/100 m, repos 10 s", "Développer la régularité", "Compter les mouvements par longueur."),
     ("1000 m continus à CSS + 3 s", 50, 1, 1, "1000 m en continu à {z3s}/100 m", "Endurance au seuil", "Nage longue et régulière."),
     ("6 × 200 m au pull à la CSS", 60, 6, 3, "{n} × 200 m au pull-buoy à {css}/100 m, repos 20 s", "Travailler la traction à vitesse seuil", "Garder la glisse même au pull."),
     ("Pyramide 100-200-300-200-100 m", 60, 1, 1, "100, 200, 300, 200 puis 100 m à {css}/100 m, repos 20 s", "Varier la durée des efforts au seuil", "Gérer l'effort : le 300 m est la référence.")])

fam("swim", "vo2", 5, "Sprints et vitesse au-delà de la CSS ; stimulation haute intensité",
    ["500 m souples + 6 × 50 m progressifs + 4 × 25 m rapides", "400 m souples + 8 × 25 m (1 sur 2 rapide)"],
    ["200 m souples", "200 m dos souple"],
    "Vitesse : {z5s}/100 m ou plus rapide (RPE 8-9/10) ; récupération {z1s}/100 m",
    [("12 × 50 m rapides", 50, 12, 6, "{n} × 50 m à {z5s}/100 m, repos 20 s", "Développer la vitesse de nage", "Fréquence élevée, nage longue."),
     ("8 × 75 m rapides", 55, 8, 4, "{n} × 75 m à {z5s}/100 m, repos 25 s", "Soutenir une allure supérieure à la CSS", "Respiration contrôlée, pas d'apnée."),
     ("16 × 25 m sprints", 45, 16, 8, "{n} × 25 m en sprint, repos 15 s", "Travailler la puissance maximale", "Qualité maximale sur chaque 25 m."),
     ("6 × 100 m à CSS - 4 s", 55, 6, 3, "{n} × 100 m à {z5s}/100 m, repos 30 s", "Développer la vitesse soutenue", "Même chrono sur toutes les répétitions."),
     ("10 × 100 m progressifs", 60, 10, 5, "{n} × 100 m : 1er 25 m souple, puis accélération progressive jusqu'à {z5s}/100 m, repos 20 s", "Apprendre à accélérer", "Allonger la nage en accélérant."),
     ("4 × (3 × 50 m)", 55, 4, 2, "{n} séries de 3 × 50 m à {z5s}/100 m, repos 15 s entre les 50 m, 1 min entre les séries", "Répéter des efforts courts intenses", "Qualité d'exécution avant la vitesse."),
     ("5 × 150 m soutenus", 55, 5, 3, "{n} × 150 m à {z5s}/100 m, repos 30 s", "Soutenir la vitesse plus longtemps", "Respiration régulière."),
     ("8 × 50 m lactiques", 50, 8, 4, "{n} × 50 m à effort maximal, repos 60 s", "Stimuler la filière lactique", "Récupération complète."),
     ("20 × 50 m sur 1 min", 60, 20, 10, "{n} × 50 m départ toutes les minutes à {z5s}/100 m", "Améliorer la capacité à répéter des efforts rapides", "Le repos dépend du temps de nage : rester régulier."),
     ("6 × 100 m dégressifs", 55, 6, 3, "{n} × 100 m dégressifs (chaque 100 m plus rapide que le précédent), repos 20 s", "Apprendre à gérer l'accélération", "Dernier 100 m à la vitesse maximale contrôlée.")])

fam("swim", "spec", 4, "Eau libre et triathlon : visée, départ, drafting, nage en conditions de course",
    ["300 m souples + 4 × 50 m avec visée", "200 m souples + 4 × 25 m départ rapide"],
    ["200 m souples", "100 m dos souple"],
    "Eau libre : allure de course ≈ {z3s}/100 m ; départs à {z5s}/100 m",
    [("Eau libre : 20 min continues", 45, 1, 1, "20 min de nage continue avec visée tous les 8 mouvements", "S'habituer à nager sans repères de bassin", "Lever les yeux seulement, garder la rotation."),
     ("3 × 400 m avec visée", 55, 3, 2, "{n} × 400 m à {z3s}/100 m, visée tous les 6 mouvements, repos 30 s", "Combiner allure de course et orientation", "Garder la tête dans l'axe."),
     ("6 × 100 m départs rapides", 50, 6, 3, "{n} × 100 m : 25 m départ rapide ({z5s}/100 m) puis 75 m à {z3s}/100 m, repos 30 s", "Simuler le départ en vague", "Respirer dès le 3e mouvement."),
     ("Drafting 8 × 100 m", 55, 8, 4, "{n} × 100 m en suivant un autre nageur (ou un partenaire) à 50 cm des pieds, repos 20 s", "S'entraîner au drafting", "Rester près sans toucher."),
     ("Test 1500 m", 50, 1, 1, "1500 m en continu à {z3s}/100 m", "Évaluer l'endurance de course", "Gérer l'allure, jamais de sprint en début."),
     ("Eau libre : 2 × 1000 m avec visée", 60, 2, 1, "{n} × 1000 m à {z3s}/100 m avec visée régulière, repos 45 s", "Préparer le triathlon distance olympique", "Régularité de l'allure."),
     ("Simulation 750 m", 40, 1, 1, "750 m en continu à allure de course ({z3s}/100 m)", "Simuler le sprint triathlon", "Premier 100 m contrôlé."),
     ("Nage après effort (fatigue)", 45, 4, 2, "{n} × 200 m à {z3s}/100 m après 10 min d'efforts à sec (pompes, squats), repos 30 s", "Habituer le corps à nager fatigué", "Technique avant vitesse."),
     ("Passage de bouées", 45, 6, 3, "{n} × 150 m avec changements de direction toutes les 25 m, allure {z3s}/100 m", "Travailler les virages en eau libre", "Garder la visée avant le virage."),
     ("1900 m continus", 55, 1, 1, "1900 m en continu à {z3s}/100 m", "Simuler un triathlon distance olympique", "Alimentation de la veille soignée.")])

# =============================================================================================
# MUSCULATION (4 familles) : format habituel 1 h, 5 exercices, 4 séries
# =============================================================================================
_MW = ["8 min de cardio léger (rameur ou vélo) + mobilité dynamique", "5 min de cardio + 2 séries progressives avec charge légère"]
_MC = ["5 min de marche + étirements des groupes sollicités", "5 min de retour au calme + respiration"]
_MZ = "Intensité : {rir} · tempo 2-0-1 · repos {rest}"

fam("strength", "force", 3, "Force générale en 4 séries de 5 exercices ; rotation haut/bas du corps",
    _MW, _MC, _MZ,
    [("Push A", 60, 4, 2, _ex("Développé couché (6-8 reps)", "Développé militaire haltères (8 reps)", "Développé incliné haltères (8-10 reps)", "Élévations latérales (12-15 reps)", "Dips ou extensions triceps poulie (10-12 reps)"),
      "Force du haut du corps (poussée)", "Omoplates serrées, trajectoire contrôlée, pas de rebond."),
     ("Push B", 60, 4, 2, _ex("Développé incliné barre (6-8 reps)", "Développé haltères neutre (8-10 reps)", "Pompes lestées (10 reps)", "Oiseau inversé (12-15 reps)", "Extension triceps au-dessus de la tête (10-12 reps)"),
      "Force et volume de poussée", "Garder les poignets alignés."),
     ("Pull A", 60, 4, 2, _ex("Tractions lestées ou assistées (6-8 reps)", "Rowing barre (8 reps)", "Tirage horizontal (10 reps)", "Face pull (12-15 reps)", "Curl biceps (10-12 reps)"),
      "Force du haut du corps (traction), importante pour la nage", "Tirer avec le dos, pas avec les bras."),
     ("Pull B", 60, 4, 2, _ex("Tirage vertical prise serrée (8 reps)", "Rowing haltère (8-10 reps)", "Tractions australiennes (10 reps)", "Pull-over poulie (12 reps)", "Curl marteau (10-12 reps)"),
      "Volume de traction et de gainage du dos", "Contrôler la phase de retour."),
     ("Legs A", 60, 4, 2, _ex("Squat (6 reps)", "Soulevé de terre roumain (8 reps)", "Fentes marchées (10 reps par jambe)", "Leg curl (10-12 reps)", "Mollets debout (12-15 reps)"),
      "Force des jambes et des chaînes postérieures", "Genoux dans l'axe des pieds, dos neutre."),
     ("Legs B", 60, 4, 2, _ex("Presse à cuisses (8-10 reps)", "Hip thrust (8-10 reps)", "Step-up sur banc (10 reps par jambe)", "Extension de jambes (12 reps)", "Mollets assis (12-15 reps)"),
      "Force des fessiers et des quadriceps, avec moins de charge sur le dos", "Pousser par le talon, contrôler la descente."),
     ("Full body A", 60, 4, 2, _ex("Squat goblet (8-10 reps)", "Développé couché haltères (8-10 reps)", "Rowing haltère (10 reps)", "Soulevé de terre roumain (8 reps)", "Gainage planche (40 s)"),
      "Entretenir toute la chaîne musculaire", "Qualité des mouvements avant la charge."),
     ("Full body B", 60, 4, 2, _ex("Fentes arrière (10 reps par jambe)", "Développé militaire (8 reps)", "Tractions ou tirage (8-10 reps)", "Pont fessier unilatéral (10 reps par jambe)", "Gainage latéral (30 s par côté)"),
      "Entretenir la force avec une charge modérée", "Équilibre entre les côtés gauche et droit."),
     ("Haut du corps", 60, 4, 2, _ex("Développé couché (6-8 reps)", "Tractions (6-8 reps)", "Développé militaire (8 reps)", "Rowing barre (8 reps)", "Gainage anti-rotation (30 s par côté)"),
      "Soutenir la nage et la posture de vélo", "Épaules basses, nuque relâchée."),
     ("Bas du corps spécifique course", 60, 4, 2, _ex("Squat bulgare (8 reps par jambe)", "Soulevé de terre jambes tendues (8 reps)", "Montée de banc lestée (10 reps par jambe)", "Mollets unilatéraux (12 reps par jambe)", "Nordic curl assisté (5-6 reps)"),
      "Renforcer les jambes en unilatéral pour la course", "Contrôle excentrique de 3 secondes sur le nordic curl.")])

fam("strength", "gainage", 2, "Gainage et prévention des blessures : stabilité de hanche, chevilles, épaules, bas du dos",
    _MW, _MC, "Intensité : contrôle et amplitude, jamais de douleur ; 30 à 45 s par exercice ; repos 45 s",
    [("Gainage circuit général", 35, 3, 2, _ex("Planche (40 s)", "Planche latérale (30 s par côté)", "Bird-dog (10 reps par côté)", "Dead bug (10 reps par côté)", "Pont fessier (15 reps)"),
      "Renforcer le tronc", "Bassin neutre, respiration continue."),
     ("Activation fessiers et hanches", 35, 3, 2, _ex("Clamshell avec élastique (15 reps par côté)", "Marche latérale avec élastique (15 pas par côté)", "Pont fessier unilatéral (10 reps par côté)", "Fire hydrant (12 reps par côté)", "Squat avec élastique (12 reps)"),
      "Prévenir les douleurs de genou et de hanche", "Bassin stable, genoux alignés."),
     ("Chevilles et pieds", 30, 3, 2, _ex("Montées sur pointes unilatérales (15 reps)", "Équilibre unipodal yeux fermés (30 s)", "Marche sur talons (20 pas)", "Court-pied, travail de la voûte plantaire (10 reps)", "Sauts de corde souples (45 s)"),
      "Renforcer les structures du pied et de la cheville", "Mouvements lents et contrôlés."),
     ("Épaules du nageur", 30, 3, 2, _ex("Rotation externe avec élastique (15 reps)", "Y-T-W sur banc (8 reps chaque)", "Face pull (15 reps)", "Planche avec toucher d'épaule (10 reps par côté)", "Pompes lentes scapulaires (10 reps)"),
      "Prévenir les tendinopathies de l'épaule", "Omoplates basses, amplitude contrôlée."),
     ("Bas du dos et lombaires", 30, 3, 2, _ex("Superman (10 reps)", "Bird-dog avec pause (10 reps par côté)", "Hyperextension au banc (12 reps)", "Planche (40 s)", "Chat-vache (10 reps)"),
      "Renforcer le bas du dos pour la position aérodynamique", "Mouvement lent, jamais de douleur."),
     ("Anti-rotation", 30, 3, 2, _ex("Pallof press (10 reps par côté)", "Planche avec rotation du tronc (8 reps par côté)", "Bûcheron à la poulie (10 reps par côté)", "Dead bug avec élastique (10 reps par côté)", "Marche avec valise (30 s par côté)"),
      "Stabiliser le tronc contre les rotations", "Garder le bassin immobile."),
     ("Planches variées", 30, 3, 2, _ex("Planche sur les coudes (45 s)", "Planche haute (40 s)", "Planche latérale avec levée de jambe (25 s par côté)", "Planche avec alternance de jambes (10 reps par côté)", "Planche inversée (30 s)"),
      "Endurance de gainage", "Pas de creusement du dos."),
     ("Stabilité unilatérale", 35, 3, 2, _ex("Équilibre unipodal avec rotation du buste (8 reps par côté)", "Squat unilatéral sur banc (8 reps par côté)", "Fente latérale (10 reps par côté)", "Pont fessier unilatéral (10 reps par côté)", "Montée de banc (10 reps par côté)"),
      "Améliorer le contrôle d'un seul appui", "Genou aligné sur le deuxième orteil."),
     ("Copenhague et adducteurs", 30, 3, 2, _ex("Planche latérale Copenhague (20 s par côté)", "Pont fessier adducteurs avec ballon (12 reps)", "Squat sumo (12 reps)", "Gainage latéral (30 s par côté)", "Fente latérale (10 reps par côté)"),
      "Prévenir les douleurs d'aine et de hanche", "Contraction progressive, aucune douleur."),
     ("Tendon d'Achille excentrique", 30, 3, 2, _ex("Descente excentrique sur marche, genou tendu (12 reps)", "Descente excentrique genou fléchi (12 reps)", "Montée sur pointes à deux pieds (15 reps)", "Marche sur pointes (20 pas)", "Équilibre unipodal (30 s)"),
      "Renforcer le complexe soléaire et gastrocnémien", "Descendre en 3 secondes, remonter avec les deux pieds.")])

fam("strength", "plyo", 3, "Force-vitesse et pliométrie légère : raideur musculo-tendineuse, économie de course",
    _MW, _MC, "Intensité : explosivité contrôlée (hauteurs faibles, 5 à 8 reps), repos {rest} complet, qualité avant volume",
    [("Sauts sur box bas", 40, 4, 2, _ex("Saut sur box (40 cm, 5 reps)", "Squat jump (6 reps)", "Sauts à la corde (45 s)", "Fentes sautées (6 reps par jambe)", "Skipping rapide (20 m x 4)"),
      "Développer la puissance des jambes", "Réception silencieuse, genoux alignés."),
     ("Bonds horizontaux", 40, 4, 2, _ex("Bonds alternés sur 20 m (4 reps)", "Saut en longueur sans élan (5 reps)", "Pas bondissants (20 m x 3)", "Sauts pieds joints enchaînés (6 reps)", "Skipping rapide (20 m x 4)"),
      "Améliorer la poussée horizontale", "Temps de contact au sol le plus court possible."),
     ("Kettlebell swings", 40, 4, 2, _ex("Kettlebell swing (12 reps)", "Goblet squat sauté (6 reps)", "Soulevé de terre explosif (5 reps)", "Fentes alternées explosives (6 reps par jambe)", "Gainage dynamique (30 s)"),
      "Développer la puissance de la chaîne postérieure", "Dos neutre, hanches qui pilotent le mouvement."),
     ("Lancers de médecine-ball", 40, 4, 2, _ex("Lancer de médecine-ball au mur (8 reps)", "Lancer au-dessus de la tête (6 reps)", "Rotation explosive (8 reps par côté)", "Squat jump (6 reps)", "Pompes claquées assistées (6 reps)"),
      "Puissance du tronc et des membres supérieurs", "Mouvement explosif, retour contrôlé."),
     ("Corde à sauter et appuis", 35, 4, 2, _ex("Corde à sauter (1 min)", "Double-appuis latéraux (30 s)", "Sauts unipodaux (10 reps par jambe)", "Échelle de rythme (3 passages)", "Skipping rapide (20 m x 4)"),
      "Raideur de cheville et coordination", "Rester sur l'avant-pied, genoux souples."),
     ("Squat jump léger", 40, 4, 2, _ex("Squat jump au poids du corps (6 reps)", "Saut vertical (5 reps)", "Fentes sautées (6 reps par jambe)", "Mollets sautés (10 reps)", "Gainage planche (40 s)"),
      "Réactivité musculaire", "Chaque saut est un effort maximal contrôlé."),
     ("Sprints courts et côte", 40, 8, 4, "{n} × 10 s de sprint en côte douce (récupération 1 min 30 en marchant), puis 3 × 20 m de skipping", "Puissance de poussée", "Départ explosif, buste incliné."),
     ("Sauts unilatéraux", 40, 4, 2, _ex("Saut unilatéral sur place (6 reps par jambe)", "Bonds sur une jambe (10 m x 2 par jambe)", "Fente sautée (6 reps par jambe)", "Step-up explosif (6 reps par jambe)", "Équilibre unipodal (30 s)"),
      "Équilibrer la puissance gauche-droite", "Réception stable avant d'enchaîner."),
     ("Haies basses", 40, 4, 2, _ex("Sauts de haies basses pieds joints (6 reps)", "Sauts de haies basses unipodaux (4 reps par jambe)", "Squat jump (6 reps)", "Skipping rapide (20 m x 4)", "Gainage latéral (30 s par côté)"),
      "Réactivité au sol", "Contact bref, regard loin devant."),
     ("Foulées bondissantes", 35, 4, 2, _ex("Foulées bondissantes (30 m x 4)", "Pas chassés (20 m x 2)", "Sauts de grenouille (5 reps)", "Montées de genoux (20 m x 3)", "Pied-mollet (20 m x 3)"),
      "Économie de course et amplitude", "Poussée complète, retour du pied rapide.")])

fam("strength", "mobilite", 1, "Mobilité et récupération active : amplitude articulaire, détente musculaire",
    ["5 min de marche + respiration", "3 min de cardio léger + rotations articulaires"],
    ["3 min de respiration allongée", "3 min de marche lente"],
    "Intensité : amplitude confortable, jamais de douleur ; 40 à 60 s par position",
    [("Mobilité hanches", 25, 2, 1, "{n} circuits de : 90/90 (60 s par côté), fente basse avec rotation (8 reps par côté), pigeon (60 s par côté), cercles de hanche (10 reps par côté)", "Améliorer l'amplitude de hanche", "Respirer lentement dans chaque position."),
     ("Mobilité chevilles", 20, 2, 1, "{n} circuits de : genou au mur (10 reps par côté), cercles de cheville (10 reps par côté), étirement soléaire (45 s par côté), marche sur pointes/talons (20 pas)", "Améliorer la dorsiflexion", "Talon au sol pendant le genou au mur."),
     ("Mobilité thoracique", 20, 2, 1, "{n} circuits de : rotation en position à quatre pattes (8 reps par côté), enroulé-déroulé (10 reps), ouverture de poitrine au sol (45 s par côté), chat-vache (10 reps)", "Améliorer la rotation du buste, utile en natation et en vélo", "Mouvement lent, regard dans la main."),
     ("Mobilité ischios et mollets", 25, 2, 1, "{n} circuits de : étirement ischios allongé (60 s par côté), fente avant (45 s par côté), chien tête en bas (60 s), roulé de mollet au rouleau (60 s par côté)", "Détendre la chaîne postérieure", "Aucune douleur, juste une tension."),
     ("Routine yoga 25 min", 25, 1, 1, "Enchaînement doux de 25 min : salutation au soleil lente (5 tours), guerrier I et II (45 s par côté), pigeon, posture de l'enfant", "Récupération globale", "Respiration nasale tout au long."),
     ("Auto-massage au rouleau", 25, 1, 1, "Rouleau de massage : mollets, ischios, quadriceps, fessiers, dos (60 s par zone)", "Réduire les tensions musculaires", "Pression modérée, pas de douleur vive."),
     ("Étirements dynamiques post-effort", 20, 2, 1, "{n} circuits de : balancier de jambe (10 reps par côté), fente dynamique (8 reps par côté), cercles de bras (10 reps), talons-fesses en marchant (20 pas)", "Relancer la circulation après l'effort", "Pas de rebond, mouvement fluide."),
     ("Mobilité épaule nageur", 20, 2, 1, "{n} circuits de : cercles de bras (10 reps), étirement de pectoral sur cadre de porte (45 s par côté), rotation externe avec bande (12 reps), planche d'épaule (30 s)", "Préserver l'épaule de la nage", "Omoplates basses."),
     ("Mobilité bas du dos", 20, 2, 1, "{n} circuits de : genoux au buste (45 s), torsion allongée (45 s par côté), chat-vache (10 reps), posture de l'enfant (60 s)", "Détendre le bas du dos et le bassin", "Dos plaqué au sol, respiration profonde."),
     ("Mobilité complète 20 min", 20, 1, 1, "20 min de mobilité enchaînée : cou, épaules, thorax, hanches, genoux, chevilles, 2 minutes par zone", "Entretenir toute la mobilité articulaire", "Un mouvement par articulation, amplitude confortable.")])


# =============================================================================================
# FAMILLES DE PLANIFICATION : sortie longue, affûtage, enchaînements (utilisées par planner.py)
# =============================================================================================
fam("run", "long", 3, "Sortie longue : Daniels (≤ 25 % du volume hebdomadaire, ≤ 150 min) ; Friel (progression en durée) ; Seiler (zone 1-2)",
    ["10 min de marche rapide puis trot très facile", "5 min de marche + 10 min à {z1}"],
    ["10 min de marche, hydratation, étirements doux", "5 min de trot lent puis marche"],
    "Endurance : {z2} (RPE 3-4/10) ; allure marathon : {mar}",
    [("Sortie longue 70 min", 70, 0, 0, "70 min continues à {z2}, terrain plat", "Construire l'endurance aérobie de base", "Régularité d'allure, boire toutes les 20 min."),
     ("Sortie longue 80 min progressive", 80, 0, 0, "60 min à {z2} puis 20 min en accélérant jusqu'à {mar}", "Habituer le corps à finir plus vite qu'il n'a commencé", "Première moitié très facile : le fond se construit sans effort."),
     ("Sortie longue 90 min", 90, 0, 0, "90 min continues à {z2}", "Développer la résistance à la fatigue", "Foulée courte en fin de séance, alimentation de 30 à 60 g de glucides par heure au-delà de 75 min."),
     ("Sortie longue 100 min avec blocs allure marathon", 100, 3, 2, "70 min à {z2} puis {n} × 8 min à {mar} (récupération 2 min à {z1})", "Introduire la spécificité marathon dans la durée", "Les blocs doivent rester contrôlés : jamais au-dessus de {mar}."),
     ("Sortie longue 110 min vallonnée", 110, 0, 0, "110 min à {z2} sur parcours vallonné, montées en foulée courte", "Renforcer l'endurance musculaire des jambes", "Courir à l'effort, pas à l'allure, dans les côtes."),
     ("Sortie longue 120 min", 120, 0, 0, "120 min à {z2}, ravitaillement testé comme en course", "Tester la stratégie d'alimentation et d'hydratation", "Utiliser les mêmes produits que le jour de la compétition."),
     ("Sortie longue 120 min négative", 120, 0, 0, "60 min à {z2} puis 60 min à {z2} haut de zone sans dépasser {mar}", "Apprendre à gérer la deuxième moitié de course", "Si la fatigue monte trop, revenir à {z2} : la séance reste valide."),
     ("Sortie longue 135 min", 135, 0, 0, "135 min à {z2}, dernier quart légèrement plus soutenu", "Préparer la durée de l'effort marathon", "Ne pas dépasser 25 à 30 % du volume de la semaine.")])

fam("run", "taper", 2, "Affûtage : Mujika & Padilla (réduire le volume de 40 à 60 %, garder l'intensité et la fréquence) ; Bosquet 2007",
    ["10 min de trot très facile", "8 min à {z1} + 4 gammes de 20 m"],
    ["5 min de marche", "5 min de trot lent + étirements dynamiques"],
    "Facile : {z2} ; touches courtes à allure de course : {p10} ou {mar}",
    [("Footing 30 min et 5 lignes droites", 30, 5, 3, "25 min à {z2} puis {n} × 15 s de lignes droites relâchées (récupération 45 s de marche)", "Garder la vivacité sans fatigue", "Courir vite mais relâché : 85 % de la vitesse maximale."),
     ("Footing 25 min et 3 × 1 min allure course", 35, 3, 2, "15 min à {z2}, {n} × 1 min à l'allure de la course (récupération 90 s de trot), 5 min à {z1}", "Maintenir le contact avec l'allure cible", "Les 3 minutes d'allure doivent paraître faciles."),
     ("Footing 30 min et éducatifs", 30, 0, 0, "30 min à {z2} avec 6 gammes de 20 m au milieu", "Entretenir la coordination", "Rester frais : arrêter avant la fatigue."),
     ("Footing court, rythme de course", 35, 4, 2, "20 min à {z2} puis {n} × 2 min à l'allure de la course (récupération 2 min à {z1})", "Régler l'allure en dernière semaine", "Allure atteinte sans effort apparent, respiration sous contrôle."),
     ("Footing de veille 20 min", 20, 4, 2, "15 min à {z1} puis {n} × 10 s d'accélérations progressives", "Réveiller les jambes la veille de la compétition", "Pas plus de 20 minutes la veille."),
     ("Footing 40 min facile", 40, 0, 0, "40 min à {z2} bas de zone", "Maintenir le volume réduit sans stress", "Ne pas rattraper les séances manquées pendant l'affûtage.")])

fam("bike", "long", 3, "Sortie longue vélo : Friel (blocs de durée), Coggan (Z2 : 56-75 % FTP) ; ≤ 40 % du volume hebdomadaire",
    ["15 min progressifs de {z1w} à {z2w}", "10 min à {z1w} puis 5 min à {z2w}"],
    ["10 min de pédalage souple", "10 min à {z1w} et étirements"],
    "Endurance : {z2w} (RPE 3-4/10) ; sweet spot : {ssw}",
    [("Sortie longue 2 h", 120, 0, 0, "120 min à {z2w}, cadence 85-95 tr/min", "Développer l'endurance aérobie de base", "Boire une gourde par heure, manger dès 45 min."),
     ("Sortie longue 2 h 30", 150, 0, 0, "150 min à {z2w}, terrain vallonné modéré", "Allonger la durée d'effort tolérée", "Garder la puissance stable, éviter les pics en montée."),
     ("Sortie longue 3 h avec blocs", 180, 3, 2, "180 min à {z2w} dont {n} × 15 min à {ssw}", "Associer durée et stimulus au sweet spot", "Les blocs doivent rester dans la zone contrôlée."),
     ("Sortie longue 3 h régulière", 180, 0, 0, "180 min à {z2w}, nutrition de 60 à 90 g de glucides par heure", "Tester la stratégie de ravitaillement", "Manger avant d'avoir faim."),
     ("Sortie longue 3 h 30", 210, 0, 0, "210 min à {z2w} avec 2 × 20 min à {z3w} en deuxième moitié", "Résister à la fatigue sur très longue durée", "Maintenir la position et la souplesse du haut du corps."),
     ("Sortie longue 4 h", 240, 0, 0, "240 min à {z2w}, les 45 dernières minutes légèrement plus soutenues", "Préparer les épreuves de longue distance", "Rester sous {z3w} sauf à la fin.")])

fam("bike", "taper", 2, "Affûtage vélo : volume réduit de 40 à 60 %, quelques touches d'intensité (Mujika & Padilla)",
    ["10 min progressifs à {z1w}", "10 min à {z1w} + 3 × 20 s de cadence rapide"],
    ["5 min de pédalage souple", "10 min à {z1w}"],
    "Facile : {z2w} ; touches courtes à allure de course : {z3w} ou {thw}",
    [("Sortie souple 45 min", 45, 0, 0, "45 min à {z2w} bas de zone", "Garder la routine sans fatigue", "Jambes légères : tourner les jambes sans forcer."),
     ("Sortie 50 min et 3 × 2 min intenses", 55, 3, 2, "35 min à {z2w} puis {n} × 2 min à {thw} (récupération 3 min à {z1w})", "Maintenir l'intensité sur un volume réduit", "L'effort reste contrôlé, pas de dépassement."),
     ("Sortie 60 min allure course", 60, 2, 1, "40 min à {z2w} puis {n} × 5 min à {z3w} (récupération 3 min)", "Régler la puissance de course", "Allure facile à tenir, jamais au-delà."),
     ("Sortie 40 min et accélérations", 40, 4, 2, "30 min à {z2w} puis {n} × 20 s de relances rapides", "Réveiller les jambes", "Récupérer complètement entre les relances."),
     ("Sortie de veille 30 min", 30, 3, 2, "25 min à {z1w} puis {n} × 15 s à cadence élevée", "Veille de compétition", "Rester frais.")])

fam("bike", "brick", 4, "Enchaînement vélo-course (brick) : Friel, entraînement du triathlète ; transition spécifique",
    ["15 min progressifs de {z1w} à {z2w}", "10 min à {z2w} + 3 × 30 s de cadence rapide"],
    ["5 min de marche et étirements après la course", "10 min de trot lent après la course"],
    "Vélo : {z3w} ; course : allure cible ({p10} ou {mar})",
    [("Brick 45 min vélo + 10 min course", 60, 1, 1, "45 min de vélo dont 25 min à {z3w}, transition rapide puis 10 min de course à {p10}", "Réveiller la transition vélo-course", "Cadence élevée en fin de vélo, foulée courte les 3 premières minutes à pied."),
     ("Brick 60 min vélo + 15 min course", 80, 1, 1, "60 min de vélo (40 min à {z3w}) puis 15 min de course à {mar}", "Habituer les jambes à courir après l'effort vélo", "Les 5 premières minutes à pied servent à retrouver la foulée."),
     ("Brick 75 min vélo + 20 min course", 100, 1, 1, "75 min de vélo à {z3w} puis 20 min de course à allure cible", "Simuler le deuxième tiers d'un triathlon", "Boire et manger sur le vélo, pas à pied."),
     ("Brick 90 min vélo + 30 min course", 125, 1, 1, "90 min de vélo (60 min à {z3w}) puis 30 min de course à {mar}", "Résister à la fatigue sur les distances longues", "Rester régulier : un départ trop rapide à pied se paie ensuite."),
     ("Double brick 2 × (30 + 8 min)", 85, 2, 1, "{n} × (30 min de vélo à {z3w} + 8 min de course à {p10}) avec transition rapide", "Répéter les transitions", "Se concentrer sur la transition : rapide et sans à-coups."),
     ("Brick court 30 min vélo + 5 min course", 40, 1, 1, "30 min de vélo à {z3w} puis 5 min de course à {p10}", "Entretenir la transition sans fatigue", "Séance courte : arrêter avant la fatigue.")])

fam("swim", "long", 3, "Natation continue : endurance de base ; allure CSS (Wakayoshi) pour les séries",
    ["400 m souples dont 4 × 50 m éducatifs", "300 m crawl + 4 × 50 m progressifs"],
    ["200 m souples", "100 m de dos"],
    "Endurance : {z2s}/100 m ; CSS : {css}/100 m",
    [("3000 m continus", 65, 0, 0, "3000 m à {z2s}/100 m, respiration par 3", "Construire l'endurance de nage longue distance", "Nage longue, glisse maximale."),
     ("5 × 600 m", 70, 5, 3, "{n} × 600 m à {z2s}/100 m, repos 20 s", "Accumuler du volume aérobie", "Garder le même nombre de coups de bras par longueur."),
     ("3500 m dont blocs CSS", 75, 3, 2, "1500 m à {z2s}/100 m puis {n} × 400 m à {z3s}/100 m (repos 30 s), 500 m souples", "Tenir l'allure de course sur la durée", "Allure de bloc stable du début à la fin."),
     ("4000 m continus", 80, 0, 0, "4000 m à {z2s}/100 m, un ravitaillement toutes les 1500 m", "Préparer les épreuves longues (3,8 km)", "Rester relâché, ne pas forcer la fin de séance.")])

fam("swim", "taper", 2, "Affûtage natation : volume réduit, quelques longueurs rapides pour garder la sensation d'eau",
    ["300 m souples dont 4 × 50 m éducatifs", "200 m crawl + 4 × 25 m rapides"],
    ["200 m souples", "100 m de dos"],
    "Facile : {z2s}/100 m ; touches courtes : {css}/100 m ou plus rapide",
    [("1500 m souples et accélérations", 35, 4, 2, "1200 m à {z2s}/100 m dont {n} × 50 m rapides (repos 20 s)", "Garder la sensation d'eau", "Allonger la glisse, pas plus."),
     ("1800 m avec 4 × 100 m allure course", 40, 4, 2, "1200 m à {z2s}/100 m puis {n} × 100 m à {css}/100 m (repos 25 s)", "Maintenir l'allure de compétition", "Aisance sur chaque 100 m."),
     ("1200 m technique", 30, 0, 0, "1200 m : 600 m éducatifs, 600 m à {z2s}/100 m", "Peaufiner la technique", "Rester frais, nager propre."),
     ("2000 m décontraction", 40, 0, 0, "2000 m à {z2s}/100 m avec 6 × 25 m rapides", "Entretenir le volume réduit", "Rester sous l'effort maximal."),
     ("Veille 800 m", 20, 4, 2, "600 m souples puis {n} × 25 m rapides", "Veille de compétition", "Courte et facile.")])

# =============================================================================================
# ENRICHISSEMENT : séances étiquetées par type d'épreuve (5k, 10k, semi, marathon, trail, tri, bike, fondo, swim, ow)
# Une séance sans étiquette est polyvalente ; une séance étiquetée est proposée en priorité quand l'objectif qui gouverne la discipline correspond.
# =============================================================================================
tag("run", "aerobe", ["3 × 12 min à allure marathon", "2 × 20 min à allure marathon"], {"marathon", "semi"})
tag("run", "aerobe", ["30 min à allure semi-marathon"], {"semi", "marathon", "10k"})
tag("run", "vo2", ["10 × 400 m", "6 × 300 m", "8 × 500 m", "3 × (4 × 200 m)"], {"5k", "10k"})
tag("run", "vo2", ["15 × 1 min"], {"trail", "marathon"})
tag("run", "spec", ["5 × 2000 m", "4 × 2500 m", "8 × 1000 m"], {"10k"})
tag("run", "spec", ["Test 5 km"], {"5k", "10k"})
tag("run", "spec", ["Sortie longue spécifique marathon", "2 × 8 km", "3 × 5 km", "Progressif long 20 km"], {"marathon"})
tag("run", "spec", ["4 × 3 km à allure semi"], {"semi"})
tag("run", "spec", ["Enchaînement vélo-course"], {"tri"})
tag("run", "trail", [s["name"] for s in LIB[("run", "trail")]], {"trail"})
tag("run", "long", ["Sortie longue 100 min avec blocs", "Sortie longue 135"], {"marathon", "semi"})
tag("run", "long", ["Sortie longue 110 min vallonnée"], {"trail"})
tag("bike", "spec", ["Brick", "Simulation de transition", "Aéro endurance", "3 × 15 min en position aéro"], {"tri"})
tag("bike", "spec", ["Contre-la-montre"], {"tri", "bike"})
tag("bike", "spec", ["Sortie 3 h avec blocs", "Vallonné type course", "2 h dont 30 min"], {"bike", "fondo"})
tag("swim", "spec", ["Eau libre", "Drafting", "Passage de bouées", "Nage après effort"], {"tri", "ow"})
tag("swim", "spec", ["Test 1500 m", "1900 m continus"], {"swim", "tri"})

# ---- course à pied ----
add("run", "z2", [
    ("Footing 45 min et 6 lignes droites", 45, 6, 3, "35 min à {z2} puis {n} × 20 s de lignes droites relâchées, récupération 40 s de marche", "Entretenir la vivacité sans fatigue", "Accélérer progressivement, relâcher en fin de ligne."),
    ("Footing 75 min sur chemins roulants", 75, 0, 0, "75 min à {z2} sur chemins roulants", "Bâtir la base aérobie avec moins de chocs", "Rester en aisance respiratoire.", {"marathon", "semi", "trail"}),
    ("Footing vallonné 60 min, montées marchées", 60, 0, 0, "60 min à {z2} sur parcours vallonné ; les montées raides se marchent d'un pas vif", "Préparer le terrain sans coût musculaire excessif", "Effort constant, jamais en dette d'oxygène.", {"trail"}),
    ("Footing 55 min en cadence", 55, 0, 0, "55 min à {z2}, cadence 175-180 pas/min les 10 dernières minutes de chaque tiers", "Soigner l'économie de course", "Foulée courte, appuis sous le bassin.", {"tri", "5k", "10k"})])
add("run", "aerobe", [
    ("2 × 3 km à allure semi-marathon", 65, 2, 1, "{n} × 3 km à {thr}, récupération 3 min de trot", "Soutenir l'allure semi", "Régularité kilomètre par kilomètre.", {"semi", "10k"}),
    ("6 km de tempo continu", 55, 1, 1, "6 km continus à {thr}", "Relever le seuil en continu", "Départ contrôlé, finir sur le même rythme.", {"10k", "semi"}),
    ("Fartlek seuil 8 × (3 min soutenu + 1 min facile)", 60, 8, 5, "{n} × (3 min à {thr} + 1 min à {z2})", "Travailler le seuil avec des relances", "Récupération active, la respiration redescend.", {"10k", "5k", "tri"}),
    ("10 km progressifs dont 5 km à allure marathon", 75, 1, 1, "5 km à {z2} puis 5 km à {mar}", "Habituer le corps à l'allure marathon sur fatigue", "Aucune accélération avant le 5e kilomètre.", {"marathon"}),
    ("Tempo en faux plat montant 4 × 6 min", 60, 4, 2, "{n} × 6 min à effort seuil sur faux plat montant (3 %), retour en trottinant", "Seuil et force spécifique de côte", "Buste légèrement penché, bras actifs.", {"trail"}),
    ("Seuil court après vélo", 70, 3, 2, "20 min de vélo facile puis {n} × 8 min de course à {thr}, récupération 2 min de trot", "Courir au seuil sur jambes de cycliste", "Cadence haute dès les premières foulées.", {"tri"}),
    ("Alternance 1 km allure 10 km / 1 km allure semi", 65, 4, 3, "{n} × (1 km à {p10} + 1 km à {thr})", "Changer de rythme sans récupération", "Relâcher les épaules à chaque changement.", {"10k", "semi", "5k"}),
    ("3 × 15 min entre allure marathon et seuil", 70, 3, 2, "{n} × 15 min à {mar} puis les 3 dernières minutes à {thr}, récupération 3 min de trot", "Soutenir l'effort long en finissant plus vite", "Les 12 premières minutes très contrôlées.", {"marathon", "semi"})])
add("run", "vo2", [
    ("12 × 200 m vifs", 50, 12, 8, "{n} × 200 m à {vma}, récupération 200 m de trot", "Vitesse et économie de course", "Foulée ample, relâchée, genoux hauts.", {"5k", "10k"}),
    ("8 × 600 m", 55, 8, 5, "{n} × 600 m à {vma}, récupération 90 s de trot", "Développer la VO2max", "Régularité : la dernière répétition égale à la première.", {"5k", "10k"}),
    ("4 × 1600 m entre allure 10 km et VMA", 65, 4, 3, "{n} × 1600 m entre {p10} et {vma}, récupération 2 min 30 de trot", "Allure 5 km sur de longues répétitions", "Rester maître de la respiration.", {"5k"}),
    ("Côtes 10 × 45 s à fond", 50, 10, 6, "{n} × 45 s en côte (6-8 %) à effort 9/10, descente en trottinant", "Puissance et VO2max sans impact", "Pousser avec les hanches, bras puissants.", {"trail", "marathon", "tri"}),
    ("Fartlek à la sensation 40 min", 50, 0, 0, "40 min en alternant des accélérations de 30 s à 3 min à effort 8-9/10 et du trot à {z2}", "Varier les stimuli de VO2max", "Écouter le corps, pas la montre.", {"tri", "trail"}),
    ("12 × 1 min / 1 min", 50, 12, 8, "{n} × (1 min à {vma} + 1 min de trot)", "Temps cumulé élevé à haute intensité", "Départ prudent sur les 3 premières.", {"10k", "semi"}),
    ("6 × 150 m lancés", 45, 6, 4, "{n} × 150 m progressifs jusqu'à {vma}, récupération 1 min 30 de marche", "Vivacité neuromusculaire", "Accélérer sur les 50 premiers mètres, tenir, relâcher.", {"5k", "10k"}),
    ("5 × 600 m sur jambes fatiguées", 55, 5, 3, "20 min de vélo puis {n} × 600 m à {p10}, récupération 2 min de trot", "VO2max après un effort de vélo", "Cadence haute, ne pas s'effondrer en fin de série.", {"tri"})])
add("run", "spec", [
    ("6 × 800 m à allure 5 km", 60, 6, 4, "{n} × 800 m entre {p10} et {vma}, récupération 2 min de trot", "Ancrer l'allure 5 km", "Course régulière, pas de départ en force.", {"5k"}),
    ("3 × 1500 m à allure 5 km", 60, 3, 2, "{n} × 1500 m entre {p10} et {vma}, récupération 3 min de trot", "Soutenir l'allure 5 km", "Dernier 300 m en accélérant légèrement.", {"5k"}),
    ("3 × 3000 m à allure 10 km", 70, 3, 2, "{n} × 3000 m à {p10}, récupération 2 min 30 de trot", "Tenir l'allure 10 km sur la distance", "Respiration rythmée, mâchoire relâchée.", {"10k"}),
    ("2 × 4 km à allure 10 km", 65, 2, 1, "{n} × 4 km à {p10}, récupération 3 min de trot", "Soutenir l'allure sur de grosses séquences", "Les 2 derniers kilomètres, même allure.", {"10k"}),
    ("2 × 5 km à allure semi-marathon", 70, 2, 1, "{n} × 5 km à {thr}, récupération 3 min de trot", "Spécificité semi-marathon", "Allure régulière dès le premier kilomètre.", {"semi"}),
    ("Sortie 16 km dont 10 km à allure semi", 85, 1, 1, "3 km à {z2}, 10 km à {thr}, 3 km à {z2}", "Répéter l'effort de course sur fatigue", "Rester sous {thr} sur les 3 premiers kilomètres du bloc.", {"semi"}),
    ("Sortie 22 km dont 14 km à allure marathon", 125, 1, 1, "4 km à {z2}, 14 km à {mar}, 4 km à {z2}", "Simulation marathon", "Alimentation et hydratation comme en course.", {"marathon"}),
    ("4 × 4 km à allure marathon", 85, 4, 2, "{n} × 4 km à {mar}, récupération 2 min de trot", "Accumuler du temps à allure marathon", "Détendre les épaules, cadence stable.", {"marathon"}),
    ("Sortie marathon 20 km, 10 derniers km à allure course", 110, 1, 1, "10 km à {z2} puis 10 km à {mar}", "Finir fort sur fatigue", "Ne jamais dépasser {mar} avant le 15e km.", {"marathon"}),
    ("3 × (10 min vélo + 5 min course)", 60, 3, 2, "{n} × (10 min de vélo à {z3w} puis 5 min de course à {thr}), sans pause entre les deux", "Habituer le corps aux transitions", "Courir vite dès la sortie du vélo, foulée courte.", {"tri"})])
add("run", "trail", [
    ("Côtes en dents de scie 45 min", 45, 0, 0, "10 min de montée progressive puis 30 min de montées alternant 1 et 3 min soutenues", "Force de côte et variations de rythme", "Pas courts, regard haut.", {"trail"}),
    ("Montée continue 25 min", 50, 1, 1, "25 min de montée à effort soutenu (RPE 7/10), descente tranquille", "Endurance de montée", "Régulier, bâtons si utilisés en course.", {"trail"}),
    ("Sortie longue trail 2 h 45, D+ 1200 m", 165, 0, 0, "165 min à {z2} avec 1200 m de D+, nutrition toutes les 30 min", "Endurance spécifique longue durée", "Marcher les montées raides, relancer dès que le terrain s'adoucit.", {"trail"}),
    ("Descente rapide 8 × 90 s", 55, 8, 5, "{n} × 90 s de descente rapide et contrôlée, remontée en marchant", "Résistance excentrique et technique", "Pieds sous le bassin, genoux souples.", {"trail"}),
    ("Marche rapide en côte et course à plat 60 min", 60, 0, 0, "60 min : montées en marche rapide, plats et descentes en course", "Stratégie de course longue", "Économiser l'énergie dans les montées.", {"trail"}),
    ("Enchaînement côte-descente 6 × 4 min", 60, 6, 4, "{n} × (2 min de montée soutenue + 2 min de descente technique)", "Transitions de rythme et de terrain", "Relâcher dès le sommet.", {"trail"}),
    ("Sortie technique 90 min", 90, 0, 0, "90 min à {z2} sur sentier technique (racines, cailloux)", "Habileté et proprioception", "Regarder 3 foulées devant, pas ses pieds.", {"trail"}),
    ("Escaliers et renforcement dynamique", 50, 8, 5, "{n} × 1 min d'escaliers rapides, récupération 1 min en descendant", "Puissance de jambes", "Poser tout le pied, pousser fort.", {"trail"})])
add("run", "long", [
    ("Sortie longue 65 min en endurance", 65, 0, 0, "65 min continues à {z2}", "Base d'endurance, faible coût musculaire", "Allure confortable, boire au besoin.", {"5k", "tri"}),
    ("Sortie longue 90 min avec 3 × 10 min allure semi", 90, 3, 2, "20 min à {z2}, {n} × 10 min à {thr} (récupération 3 min à {z2}), reste à {z2}", "Endurance et allure semi", "Les blocs au même rythme.", {"semi", "10k"}),
    ("Sortie longue 105 min, finish rapide 15 min", 105, 0, 0, "90 min à {z2} puis 15 min à {mar}", "Finir plus vite qu'au départ", "Aucune accélération avant la dernière minute du 90e.", {"marathon", "semi"}),
    ("Sortie longue 100 min sur chemins", 100, 0, 0, "100 min à {z2} sur chemins, relances libres en côte", "Endurance et proprioception", "Appuis légers.", {"trail"})])
add("run", "taper", [
    ("Footing 20 min et 4 × 20 s allure 5 km", 30, 4, 2, "20 min à {z2} puis {n} × 20 s à {vma}, récupération 1 min de marche", "Garder la vivacité", "Courir relâché.", {"5k", "10k"}),
    ("Footing 30 min et 3 × 2 min allure semi", 40, 3, 2, "20 min à {z2} puis {n} × 2 min à {thr}, récupération 2 min de trot", "Garder la sensation d'allure", "Court et frais.", {"semi", "marathon"}),
    ("Footing 25 min, lignes droites et gammes", 35, 4, 2, "20 min à {z2} puis {n} × 15 s de lignes droites", "Maintenir la coordination", "Jamais à bout de souffle.")])

# ---- cyclisme ----
add("bike", "z2", [
    ("Z2 60 min sur home-trainer", 60, 0, 0, "60 min à {z2w}, cadence 90 tr/min", "Endurance sans dépendre de la météo", "Ventilateur et hydratation à portée."),
    ("Z2 135 min en groupe", 135, 0, 0, "135 min à {z2w}, relais à puissance constante", "Endurance et gestion du peloton", "Rester dans les roues, éviter les à-coups.", {"bike", "fondo"}),
    ("Z2 105 min vallonné", 105, 0, 0, "105 min à {z2w}, montées en restant sous {z3w}", "Endurance avec relief", "Souplesse en haut des côtes.", {"bike", "fondo", "tri"}),
    ("Z2 et 8 accélérations de 20 s", 90, 8, 5, "90 min à {z2w} dont {n} × 20 s à {vo2w}", "Garder la réactivité", "Récupération complète entre les accélérations.", {"bike", "tri"})])
add("bike", "aerobe", [
    ("4 × 15 min tempo", 85, 4, 2, "{n} × 15 min à {z3w}, récupération 5 min à {z1w}", "Développer l'endurance au tempo", "Position stable, cadence 85-90.", {"bike", "tri", "fondo"}),
    ("3 × 20 min sweet spot", 85, 3, 2, "{n} × 20 min à {ssw}, récupération 5 min à {z1w}", "Gros bloc de travail sous le seuil", "Rester sous la puissance cible.", {"bike", "fondo"}),
    ("2 × 20 min au seuil", 75, 2, 1, "{n} × 20 min à {thw}, récupération 8 min à {z1w}", "Relever le seuil fonctionnel", "Régularité de puissance.", {"bike"}),
    ("Over-unders 4 × 10 min", 75, 4, 2, "{n} × 10 min en alternant 2 min à {thw} et 1 min à {z3w}", "Tolérance aux changements d'intensité", "Pas d'à-coups, aller chercher la puissance en douceur.", {"bike", "fondo"}),
    ("Force-endurance 5 × 8 min à basse cadence", 75, 5, 3, "{n} × 8 min à {ssw} à 55-65 tr/min assis, récupération 4 min à {z1w}", "Force spécifique cyclosportive", "Dos gainé, traction régulière.", {"fondo", "tri", "bike"}),
    ("Tempo vallonné 60 min continu", 70, 1, 1, "60 min à {z3w} sur parcours vallonné", "Endurance au tempo avec relief", "Gérer l'effort dans les bosses.", {"fondo", "bike"})])
add("bike", "vo2", [
    ("5 × 5 min VO2max", 65, 5, 3, "{n} × 5 min à {vo2w}, récupération 5 min à {z1w}", "Relever la VO2max", "Premiers 30 s sous contrôle.", {"bike", "fondo"}),
    ("2 × (8 × 20''/10'')", 60, 8, 5, "2 séries de {n} × 20 s à {anw} / 10 s faciles, 5 min entre les séries", "Capacité anaérobie et VO2max", "Départs vifs, puissance stable.", {"bike", "tri"}),
    ("Départs arrêtés 8 × 15 s", 55, 8, 5, "{n} × 15 s de départ arrêté à {anw}, récupération 3 min à {z1w}", "Puissance de relance", "Tirer sur le guidon, hanches en avant.", {"bike", "fondo"}),
    ("Côtes 6 × 3 min", 65, 6, 4, "{n} × 3 min en côte à {vo2w}, descente en récupération", "VO2max en montée", "Cadence 80-90, buste droit.", {"fondo", "bike", "tri"}),
    ("Pyramide 2-4-6-4-2 min", 70, 1, 1, "2, 4, 6, 4 et 2 min à {vo2w}, récupération égale à la moitié du temps d'effort", "Varier les durées de travail", "Rester constant dans chaque bloc.", {"bike"}),
    ("4 × 6 min à 105 %", 65, 4, 3, "{n} × 6 min à {thw}, récupération 4 min à {z1w}", "Pont entre seuil et VO2max", "Cadence libre, régularité.", {"tri", "bike"})])
add("bike", "spec", [
    ("Contre-la-montre 40 min", 70, 1, 1, "40 min à {thw} en position aéro", "Allure de contre-la-montre", "Position stable, regard loin.", {"bike", "tri"}),
    ("Simulation cyclosportive : 3 bosses à allure cible", 200, 3, 2, "3 h 20 de sortie dont {n} bosses de 15 à 25 min à {ssw}, entre elles {z2w}", "Reproduire la gestion d'une cyclosportive", "Boire et manger comme en course.", {"fondo"}),
    ("Bloc montagne 3 × 20 min en montée", 120, 3, 2, "{n} × 20 min de montée à {ssw}, descente en récupération", "Endurance de montée", "Rythme régulier, ne pas partir trop vite.", {"fondo"}),
    ("Départ en peloton : 5 × 30 s puis tempo 10 min", 75, 5, 3, "{n} × 30 s à {anw}, 3 min de récupération, puis 10 min à {z3w}", "Réponse aux attaques et reprise de rythme", "Se placer avant les attaques.", {"fondo", "bike"}),
    ("Allure course triathlon 2 × 25 min en aéro", 95, 2, 1, "{n} × 25 min à {z3w} en position aéro, récupération 5 min", "Allure vélo de triathlon", "Cadence 85-95, ne pas dépasser la cible.", {"tri"}),
    ("Sortie 4 h avec montées à allure cible", 240, 1, 1, "4 h avec 3 montées à {ssw}, le reste à {z2w}", "Spécificité grande distance", "Alimentation toutes les 30 min.", {"fondo"}),
    ("Transition vélo + 3 relances", 80, 3, 2, "60 min à {z2w} puis {n} × 5 min à {thw}, 2 min de récupération, transition fluide", "Simuler les relances de fin de course", "Garder la cadence en reprise.", {"tri", "bike"}),
    ("Course en circuit 6 × 6 min", 75, 6, 4, "{n} × 6 min à {thw} avec 2 min à {z1w} entre, sur boucle courte", "Reproduire les efforts répétés d'un critérium", "Soigner les relances en sortie de virage.", {"bike"})])
add("bike", "long", [
    ("Sortie longue 2 h 45 vallonnée", 165, 0, 0, "165 min à {z2w} sur parcours vallonné", "Endurance et gestion des bosses", "Régularité de puissance.", {"fondo", "bike", "tri"}),
    ("Sortie longue 3 h 15 avec 2 × 30 min tempo", 195, 2, 1, "{n} × 30 min à {z3w}, le reste à {z2w}", "Endurance avec travail tempo", "Boire toutes les 15 min.", {"fondo", "bike", "tri"}),
    ("Sortie longue 3 h 45", 225, 0, 0, "225 min à {z2w}", "Grande endurance", "Manger 60 g de glucides par heure.", {"fondo", "bike"}),
    ("Sortie longue 1 h 45 en endurance", 105, 0, 0, "105 min à {z2w}", "Base d'endurance sans lourdeur", "Pas de bosse à plus de {z3w}.", {"tri", "run"})])
add("bike", "brick", [
    ("Brick 50 min vélo + 12 min course", 62, 0, 0, "50 min à {z3w} puis 12 min de course à allure triathlon", "Sentir la transition rapidement", "Chaussures prêtes, pas de pause.", {"tri"}),
    ("Brick 2 h vélo + 30 min course", 150, 0, 0, "2 h à {z2w} avec 20 min à {z3w} en fin de vélo, puis 30 min de course à {mar}", "Endurance spécifique triathlon long", "Boire et manger sur le vélo.", {"tri"}),
    ("Brick vallonné 60 min + 15 min course", 75, 0, 0, "60 min de vélo vallonné à {z3w} puis 15 min de course à {thr}", "Résistance de jambes en fin de vélo", "Cadence haute sur les premières foulées.", {"tri"})])
add("bike", "taper", [
    ("Sortie 45 min avec 3 × 1 min à allure course", 45, 3, 2, "35 min à {z2w} dont {n} × 1 min à {thw}", "Garder la sensation de vitesse", "Rester frais.", {"bike", "tri"}),
    ("Sortie 35 min cadence élevée", 35, 0, 0, "35 min à {z2w}, cadence 95-100 tr/min", "Entretenir la fluidité", "Pédalage rond.", ),
    ("Sortie 30 min veille de course", 30, 3, 2, "25 min à {z2w} dont {n} × 20 s de relances", "Dernière mise en route", "Sans fatigue résiduelle.", {"bike", "tri"})])

# ---- natation ----
add("swim", "z2", [
    ("1800 m continus en respiration alternée", 40, 0, 0, "1800 m à {z2s}/100 m, respiration 3-5", "Symétrie et endurance", "Même nombre de coups à gauche et à droite."),
    ("10 × 200 m, repos 15 s", 50, 10, 6, "{n} × 200 m à {z2s}/100 m, repos 15 s", "Volume aérobie", "Garder le même chrono sur toute la série."),
    ("2 × 1000 m", 45, 2, 1, "{n} × 1000 m à {z2s}/100 m, repos 40 s", "Endurance continue", "Nager long, glisser.", {"tri", "swim"}),
    ("2000 m avec plaquettes et pull", 50, 0, 0, "500 m crawl, 600 m plaquettes, 500 m pull, 400 m crawl à {z2s}/100 m", "Force de traction", "Coude haut dès l'attaque.")])
add("swim", "aerobe", [
    ("4 × 250 m à la CSS", 55, 4, 3, "{n} × 250 m à {css}/100 m, repos 30 s", "Relever la vitesse critique", "Premier 50 m contrôlé.", {"swim", "tri"}),
    ("3 × 500 m à CSS + 2 s", 60, 3, 2, "{n} × 500 m à {z3s}/100 m, repos 40 s", "Soutenir la CSS longtemps", "Régularité des coups de bras.", {"swim", "tri"}),
    ("12 × 100 m CSS, repos 10 s", 55, 12, 8, "{n} × 100 m à {css}/100 m, repos 10 s", "Seuil avec récupération courte", "Départ à chaque fois du mur.", {"tri", "swim"}),
    ("Descente 4 × 300 m", 50, 4, 3, "{n} × 300 m, chaque 100 m plus rapide que le précédent, repos 30 s", "Progressivité d'allure", "Le dernier 100 m à {css}/100 m.", {"tri", "swim"}),
    ("6 × 150 m avec accélérations de 25 m", 50, 6, 4, "{n} × 150 m à {z3s}/100 m avec 25 m rapides au milieu, repos 20 s", "Changements de rythme", "Reprendre l'allure sans perdre en amplitude.", {"tri"}),
    ("1500 m continus à CSS + 5 s", 45, 0, 0, "1500 m à {z3s}/100 m", "Endurance au seuil", "Nager droit, visée régulière.", {"swim", "tri"})])
add("swim", "vo2", [
    ("8 × 100 m à CSS − 5 s, repos 30 s", 50, 8, 5, "{n} × 100 m à {z5s}/100 m, repos 30 s", "Vitesse maximale aérobie", "Allonger les coups, pas les agiter.", {"swim"}),
    ("5 × 200 m à CSS − 3 s", 55, 5, 3, "{n} × 200 m à {z5s}/100 m, repos 40 s", "Soutenir une allure rapide", "Respiration régulière.", {"swim", "tri"}),
    ("30 × 25 m départs plongés", 50, 30, 20, "{n} × 25 m rapides avec départ plongé, repos 20 s", "Vivacité et départ", "Coulée de 5 m, accélération progressive.", {"swim"}),
    ("Fartlek 12 × (50 vite + 50 facile)", 45, 12, 8, "{n} × (50 m à {z5s}/100 m + 50 m à {z2s}/100 m)", "Alternance d'intensités", "Le 50 vite est rapide, pas désordonné.", {"tri", "swim"})])
add("swim", "spec", [
    ("Eau libre : 2 × 15 min départ en groupe", 40, 2, 1, "{n} × 15 min en eau libre avec départs groupés, repos 3 min", "Gérer le départ et le contact", "Visée tous les 8 à 10 coups.", {"tri", "ow"}),
    ("Eau libre 3 × 800 m", 55, 3, 2, "{n} × 800 m en visée tous les 8 coups, repos 1 min", "Orientation et rythme", "Lever les yeux sans casser le rythme.", {"tri", "ow"}),
    ("Course simulée 1900 m avec bouées", 50, 0, 0, "400 m souples puis 1900 m à {z3s}/100 m avec virages de bouée", "Simuler le bloc nage", "Placement et visée.", {"tri", "ow"}),
    ("Test 400 m + 200 m pour la CSS", 45, 0, 0, "Échauffement long, 400 m maximal régulier, 8 min de récupération, 200 m maximal régulier", "Actualiser la CSS", "Même effort perçu sur les deux tests.", {"swim"}),
    ("3 × 1000 m à allure course", 65, 3, 2, "{n} × 1000 m à {z3s}/100 m, repos 45 s", "Spécificité nage longue", "Garder la technique en fin de série.", {"swim"}),
    ("Adaptation combinaison 1500 m", 50, 0, 0, "1500 m en combinaison à {z3s}/100 m", "S'habituer à la combinaison", "Amplitude de bras accrue.", {"tri", "ow"})])
add("swim", "long", [
    ("4500 m par blocs", 85, 0, 0, "4500 m : 3 × 1500 m à {z2s}/100 m, repos 30 s", "Grande endurance de nage", "Régularité, nutrition légère.", {"swim", "tri"}),
    ("10 × 400 m", 85, 10, 6, "{n} × 400 m à {z2s}/100 m, repos 25 s", "Volume aérobie élevé", "Maintenir le même chrono.", {"swim"}),
    ("3800 m pull et crawl", 75, 0, 0, "3800 m : 1000 m crawl, 1000 m pull, 1000 m crawl, 800 m facile", "Endurance et traction", "Coude haut même en fin de séance.", {"swim", "tri"})])
add("swim", "taper", [
    ("1500 m avec 6 × 50 m allure course", 35, 6, 3, "1200 m à {z2s}/100 m puis {n} × 50 m à {css}/100 m", "Conserver la vitesse", "Aisance dans la vitesse.", {"swim", "tri"}),
    ("1000 m technique et glisse", 30, 0, 0, "1000 m : éducatifs puis crawl à {z2s}/100 m", "Rester fluide", "Longueur de coup avant tout."),
    ("Eau libre 20 min décontraction", 25, 0, 0, "20 min souples en eau libre à {z2s}/100 m", "Reprendre le contact avec l'eau libre", "Visée calme.", {"tri", "ow"})])

# ---------------------------------------------------------------------------------------------
# SWIMRUN : enchaînement natation / course à pied en terrain naturel, avec chaussures de course dans l'eau (étiquette « swimrun »)
# ---------------------------------------------------------------------------------------------
SR = {"swimrun"}
add("swim", "z2", [
    ("Natation avec pull-buoy et chaussures, 2 × 800 m", 40, 2, 1, "{n} × 800 m à {z2s}/100 m avec pull-buoy et plaquettes, chaussures de course aux pieds, repos 40 s", "Habituer le corps à nager chaussé, jambes au repos", "Les chaussures freinent : garder les coups longs et réguliers.", SR | {"ow"}),
    ("Endurance 1500 m avec pull-buoy", 40, 0, 0, "1500 m en continu à {z2s}/100 m, pull-buoy entre les cuisses", "Endurance de nage portée par les bras, comme en swimrun", "Gainage serré, battements très légers.", SR)])
add("swim", "aerobe", [
    ("Swimrun : 4 × 400 m chaussé au seuil", 55, 4, 3, "{n} × 400 m à {z3s}/100 m avec pull-buoy, plaquettes et chaussures, repos 30 s", "Soutenir une allure de seuil sans l'aide des jambes", "Traction énergique, appui sur l'avant-bras.", SR),
    ("Alternance 8 × (100 m pull + 100 m crawl complet)", 50, 8, 5, "{n} × (100 m pull-buoy à {css}/100 m + 100 m crawl libre à {z2s}/100 m)", "Passer du mode « bras seuls » à la nage complète", "Retrouver le rythme de jambes sans à-coup.", SR)])
add("swim", "vo2", [
    ("Relances 10 × 50 m en eau, départs rapides", 45, 10, 6, "{n} × 50 m à {z5s}/100 m avec pull-buoy, repos 25 s", "Vitesse de bras pour sortir vite de l'eau", "Sortie de l'eau en gardant l'élan.", SR)])
add("swim", "spec", [
    ("Swimrun : 6 × (250 m nage + 400 m course)", 70, 6, 3, "{n} × (250 m de nage en eau libre avec pull-buoy et chaussures à {z3s}/100 m, puis 400 m de course à {z2} sans pause)", "Enchaîner nage et course à pied comme en compétition", "Transition en moins de 20 secondes : combinaison descendue à la taille, lunettes sur le front.", SR | {"ow"}),
    ("Swimrun : 5 × (150 m nage + 800 m course)", 65, 5, 3, "{n} × (150 m de nage à {z3s}/100 m en eau libre puis 800 m de course à {z2})", "Gérer la fatigue des jambes après l'eau", "Les premières foulées sont lourdes : foulée courte, pas de précipitation.", SR | {"ow"}),
    ("Eau libre 40 min avec visée et sortie d'eau", 45, 0, 0, "40 min en eau libre à {z2s}/100 m avec visée tous les 6 à 8 coups, sorties et entrées d'eau toutes les 10 min", "Orientation et entrées dans l'eau variées", "Repérer les points de sortie avant de nager.", SR | {"ow"}),
    ("Nage longue 2 × 1000 m en combinaison et chaussures", 55, 2, 1, "{n} × 1000 m à {z3s}/100 m en combinaison, chaussures aux pieds, repos 1 min", "Simuler un grand tronçon à la nage", "Hydratation avant la séance, la combinaison fait transpirer.", SR | {"ow"}),
    ("Courant et vagues : nage de 20 min à effort variable", 40, 0, 0, "20 min en eau libre en alternant 2 min soutenues et 1 min souple, visée fréquente", "Rester efficace avec l'eau qui bouge", "Respiration bilatérale pour voir venir les vagues.", SR | {"ow"})])
add("swim", "long", [
    ("Swimrun : 3000 m continus avec pull-buoy chaussé", 65, 0, 0, "3000 m à {z2s}/100 m avec pull-buoy et chaussures, par blocs de 1000 m, repos 30 s", "Endurance de nage en conditions de swimrun", "Régulier, ne pas laisser les jambes couler.", SR)])
add("swim", "taper", [
    ("Swimrun affûtage : 600 m chaussé + 4 × 25 m vifs", 25, 4, 2, "600 m à {z2s}/100 m avec pull-buoy et chaussures, puis {n} × 25 m vifs", "Garder la sensation d'eau avant la course", "Rester frais, finir avant la fatigue.", SR | {"ow"})])
add("run", "trail", [
    ("Swimrun : course technique 5 × 8 min sur sentier", 60, 5, 3, "{n} × 8 min à effort soutenu sur sentier avec racines et pierres, 2 min de trot entre chaque", "Garder des appuis sûrs avec des chaussures déjà mouillées", "Regarder 3 mètres devant, appuis souples.", SR | {"trail"}),
    ("Swimrun : course avec chaussures mouillées 50 min", 50, 0, 0, "10 min de trempage de chaussures puis 40 min de course à {z2} sur chemin", "S'habituer aux chaussures lourdes d'eau", "Surveiller les frottements, rincer les chaussettes avant le départ.", SR | {"trail"}),
    ("Swimrun : enchaînement 4 × (10 min course + 5 min tirage de bras)", 70, 4, 2, "{n} × (10 min de course à {thr} puis 5 min de tirage de bras élastique ou rameur de bras, sans pause)", "Fatigue des bras avant de courir, comme à la sortie de l'eau", "Reprendre la foulée tout de suite, bassin haut.", SR),
    ("Swimrun : côtes courtes 8 × 1 min après effort de bras", 55, 8, 5, "10 min de tirage élastique puis {n} × 1 min de côte à effort 8/10, descente en trottinant", "Puissance de jambes fatiguées par la nage", "Buste droit, bras actifs.", SR | {"trail"})])
add("run", "long", [
    ("Swimrun : sortie longue 2 h sur terrain varié", 120, 0, 0, "120 min à {z2} sur chemins et sentiers, 10 min de marche active toutes les 40 min, nutrition régulière", "Endurance de course sur terrain varié", "Boire et manger comme en course, par petites quantités.", SR | {"trail"}),
    ("Swimrun : sortie longue 2 h 30 avec relances en fin", 150, 2, 1, "150 min à {z2} dont {n} × 10 min à {thr} sur la dernière heure", "Garder des jambes dans la deuxième moitié de course", "Ne pas partir trop vite.", SR | {"trail"})])
add("run", "aerobe", [
    ("Swimrun : tempo 3 × 12 min sur chemin", 60, 3, 2, "{n} × 12 min à {thr} sur chemin roulant, trot 3 min entre les répétitions", "Seuil sur terrain naturel", "Respiration régulière, pas de coup de rein.", SR)])

add("run", "trail", [
    ("Swimrun : transitions courses courtes 10 × 3 min", 55, 10, 6, "{n} × 3 min à {thr} sur sentier, 1 min de marche entre chaque, comme les enchaînements entre deux tronçons d'eau", "Repartir vite après chaque remise en route", "Relancer en 3 foulées, regard au sol sur le terrain.", SR | {"trail"}),
    ("Swimrun : descentes techniques et berges 45 min", 45, 0, 0, "45 min à {z2} avec 6 descentes de berge ou de talus, pas courts et appuis larges", "Assurer ses appuis sur terrain glissant", "Pieds à plat, ne pas freiner avec les talons.", SR | {"trail"}),
    ("Swimrun : run progressif 6 × 5 min en pieds mouillés", 60, 6, 4, "{n} × 5 min en accélérant de {z2} à {thr}, 90 s de marche entre chaque, chaussures mouillées", "Progressivité d'allure avec des chaussures lourdes", "Ne pas se jeter sur la première minute.", SR | {"trail"}),
    ("Swimrun : bloc 3 × (15 min course + 5 min de nage au bassin)", 80, 3, 2, "{n} × (15 min de course à {z2} puis 5 min de nage pull-buoy et chaussures, sans pause)", "Alterner course et nage à sec pour les jambes", "Rester relâché dans les jambes au moment du changement.", SR)])

# =============================================================================================
# RENDU
# =============================================================================================
def zone_vars(Z, ath, faf):
    """Variables de zones injectées dans les séances (course, vélo, natation, musculation)."""
    v = {}
    if Z:
        e0, e1 = Z["easy"]
        v.update(z1=f"{pace(e1 + 0.5)}/km ou plus lent", z2=f"{pace(e0)}-{pace(e1)}/km", mar=f"{pace(Z['mar'])}/km",
                 thr=f"{pace(Z['semi'])}/km", p10=f"{pace(Z['p10'])}/km", vma=f"{pace(Z['vma'])}/km")
    else:
        v.update(z1="très facile (RPE 1-2/10)", z2="facile (RPE 3-4/10)", mar="allure marathon (RPE 6/10)", thr="seuil (RPE 7/10)",
                 p10="allure 10 km (RPE 8/10)", vma="VMA (RPE 9/10)")
    f = ath["ftp_w"]
    w = lambda a, b: f"{round(f * a)}-{round(f * b)} W"
    v.update(ftp=f"{f} W", z1w=f"moins de {round(f * .55)} W", z2w=w(.56, .75), z3w=w(.76, .90), ssw=w(.88, .94),
             thw=w(.91, 1.05), vo2w=w(1.06, 1.20), anw=w(1.21, 1.50))
    c = ath["swim_css_s_100m"]
    v.update(css=cs(c), z1s=cs(c + 15), z2s=cs(c + 8), z3s=cs(c + 3), z5s=cs(c - 4))
    v["rir"] = ("2-3 répétitions en réserve" if faf >= 0.95 else "3-4 répétitions en réserve" if faf >= 0.8 else "4 répétitions ou plus en réserve, charges réduites d'environ 15 %")
    v["rest"] = "90 s" if faf >= 0.8 else "2 min"
    return v


def round5(x): return int(round(x / 5.0)) * 5


def render(sess, zv, faf, vol=1.0, note=""):
    """Applique le FAF à une séance : durée, répétitions, charge. Retourne un dictionnaire prêt à afficher."""
    scale = max(0.6, min(1.1, faf))
    base = sess["min"]
    vol = max(0.4, min(1.0, vol))
    dur = base if (sess["lvl"] == 1 and vol >= 1) else max(20, round5(base * min(scale, 1.0) * vol))
    n = sess["n0"] if sess["n0"] else None
    if n:
        n = max(sess["nmin"], min(sess["n0"], int(round(sess["n0"] * scale * (1.0 if vol >= 0.85 else max(vol, 0.7))))))
    v = dict(zv, n=n if n else "")
    t = lambda s: s.format_map(_Keep(v))
    adapt = []
    if dur != base: adapt.append(f"durée ajustée de {base} à {dur} min")
    if n and n != sess["n0"]:
        unit = "séries" if sess["disc"] == "strength" else "répétitions"
        adapt.append(f"{n} {unit} au lieu de {sess['n0']}")
    if sess["disc"] == "strength" and faf < 0.95: adapt.append("charges et proximité de l'échec réduites")
    fs = f"{faf:.2f}".replace(".", ",")
    adapt_txt = ((", ".join(adapt)).capitalize() + f" (FAF {fs}).") if adapt else f"Séance maintenue telle que prévue (FAF {fs})."
    if note: adapt_txt += " " + note
    blocks = [["Échauffement", t(sess["warm"])], ["Corps de séance", t(sess["main"])], ["Retour au calme", t(sess["cool"])],
              ["Zones cibles", t(sess["zones"])], ["Objectif physiologique", t(sess["goal"])], ["Consignes techniques", t(sess["cue"])],
              ["Adaptation du jour", adapt_txt]]
    return {"id": sess["id"], "name": sess["name"], "disc": sess["disc"], "fam": sess["fam"], "lvl": sess["lvl"], "dur": dur,
            "dur_base": base, "n": n, "n0": sess["n0"], "blocks": blocks, "meta": f"{dur} min · {INT_LABEL[sess['lvl']]}"}


class _Keep(dict):
    def __missing__(self, k):
        return "{" + k + "}"
