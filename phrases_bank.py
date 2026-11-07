"""Banques de phrases (français) du dashboard : 100 % déterministes, sans IA ni appel externe.

Sélection : index = int(md5(date + sel).hexdigest(), 16) % n, avec un sel différent par bloc de texte
pour éviter les choix corrélés. Même date + mêmes données = même texte.
Variables injectables : {hrv_val} {hrv_baseline} {hrv_pct} {sleep_score} {sleep_h} {deep_pct} {rem_pct}
{load_7d} {acwr} {strain_index} {body_battery} {bb_charge} {stress_avg} {faf} {readiness} ...
Une variante qui référence une variable absente (donnée manquante) est écartée automatiquement.

Cohérence de ton : chaque profil a un registre propre (prudent pour la fatigue, motivant pour la forme,
pédagogique pour les déficits). Les variantes d'un même profil varient le style (factuel, pédagogique,
motivant, prudent) sans jamais contredire le diagnostic."""
import hashlib
import string


def h(date_str, salt):
    return int(hashlib.md5((date_str + salt).encode("utf-8")).hexdigest(), 16)


def _fields(tpl):
    return {f for _, f, _, _ in string.Formatter().parse(tpl) if f}


class _Safe(dict):
    def __missing__(self, k):
        return "n/a"


def fmt(tpl, vars_):
    return tpl.format_map(_Safe({k: ("n/a" if v is None else v) for k, v in (vars_ or {}).items()}))


def pick(variants, date_str, salt, vars_=None):
    """Variante choisie par hash parmi celles dont toutes les variables sont disponibles."""
    vars_ = vars_ or {}
    ok = [v for v in variants if all(vars_.get(f) not in (None, "") for f in _fields(v))]
    pool = ok or [v for v in variants if not _fields(v)] or list(variants)
    return fmt(pool[h(date_str, salt) % len(pool)], vars_)


# ---------------------------------------------------------------------------------------------
# DIAGNOSTIC : 9 profils x (10 variantes « head » + 10 variantes « advice »)
# ---------------------------------------------------------------------------------------------
DIAG = {
    # Registre : prudent, factuel, pédagogique. Jamais de ton « motivation à fond ».
    "fatigue_aiguë": {
        "head": [
            "Indice de fatigue à {strain_index}/100 : les signaux convergent vers une fatigue aiguë, la priorité du jour est de récupérer.",
            "Ta VFC de {hrv_val} ms se situe sous ta base de {hrv_baseline} ms ({hrv_pct}) : le système nerveux est sollicité, mieux vaut lever le pied.",
            "Avec un ratio de charge de {acwr}, la charge récente dépasse nettement ce que ton organisme a l'habitude d'encaisser.",
            "Le sommeil ({sleep_score}/100, {sleep_h} h) n'a pas permis de compenser la charge accumulée : le corps demande du repos.",
            "Plusieurs marqueurs sont au rouge en même temps (VFC, charge, récupération) : ce n'est pas le moment de chercher de la performance.",
            "Body Battery à {body_battery} et stress moyen de {stress_avg} : les réserves d'énergie sont basses, une séance exigeante coûterait plus qu'elle ne rapporterait.",
            "Une fatigue aiguë n'est pas un échec : c'est la conséquence normale d'un bloc chargé, et elle se résorbe en 24 à 72 h si on lui laisse la place.",
            "Les indicateurs physiologiques sont cohérents entre eux : fatigue marquée, séance du jour à orienter vers la récupération.",
            "Charge de {load_7d} sur 7 jours : au-dessus de ta zone habituelle, la fatigue observée est cohérente avec ce volume.",
            "Facteur d'ajustement de forme à {faf} : la séance du jour est volontairement réduite pour protéger la suite de ta préparation.",
        ],
        "advice": [
            "Privilégie une séance très facile ou un jour de repos complet ; vise 8 h de sommeil ce soir.",
            "Hydratation, repas riches en glucides et en protéines, et coucher tôt valent mieux qu'une séance de plus aujourd'hui.",
            "Si tu t'entraînes, reste en zone 1 et arrête-toi à la moindre sensation de lourdeur inhabituelle.",
            "Évite toute intensité et toute séance de jambes pendant 24 à 48 h, le temps que la VFC remonte.",
            "Une séance de mobilité ou de natation très souple favorise la récupération sans ajouter de contrainte mécanique.",
            "Mesure ta VFC et ton sommeil demain matin : si les deux remontent, tu pourras reprendre progressivement.",
            "L'adaptation se construit pendant le repos : cette pause fait partie de l'entraînement.",
            "Allège aussi le reste de la journée (stress, déplacements, écrans tardifs) pour aider le système nerveux à se réguler.",
            "Si la fatigue persiste plus de trois jours malgré le repos, allège la semaine entière.",
            "Garde la séance courte, sans objectif de chrono, et privilégie les sensations de fluidité.",
        ],
    },
    # Registre : motivant et factuel.
    "forme_optimale": {
        "head": [
            "Indice de fatigue à {strain_index}/100 : tous les voyants sont au vert, tu es dans une très bonne fenêtre pour t'entraîner.",
            "VFC à {hrv_val} ms pour une base de {hrv_baseline} ms ({hrv_pct}) : le système nerveux est bien disponible.",
            "Ratio de charge de {acwr} : tu progresses dans la zone idéale, assez de charge pour s'adapter sans excès.",
            "Sommeil à {sleep_score}/100 et Body Battery à {body_battery} : la récupération a été excellente, profites-en.",
            "Les signaux de récupération, de charge et de sommeil sont alignés : c'est le moment de placer une séance de qualité.",
            "Forme au beau fixe : ton organisme a bien assimilé les dernières séances.",
            "Facteur d'ajustement de forme à {faf} : la séance du jour peut être réalisée telle que prévue, voire avec un peu d'ambition.",
            "Peu de fatigue, un stress contenu ({stress_avg}) et une bonne récupération : les conditions sont réunies pour progresser.",
            "Charge de {load_7d} sur 7 jours bien digérée : la fraîcheur actuelle permet de viser une séance exigeante de qualité.",
            "Ton corps répond bien : garde cette régularité, c'est elle qui construit la performance sur la durée.",
        ],
        "advice": [
            "Place ta séance la plus exigeante de la semaine aujourd'hui et soigne l'échauffement.",
            "Profite de cette fraîcheur pour viser la qualité plutôt que la quantité : peu de répétitions, bien exécutées.",
            "Reste discipliné sur les allures cibles : la forme ne doit pas te pousser à partir trop vite.",
            "Alimente-toi bien avant la séance (glucides 2 à 3 h avant) pour exploiter pleinement ton potentiel.",
            "Termine par un vrai retour au calme et une collation de récupération dans l'heure qui suit.",
            "Si les sensations sont excellentes, tu peux ajouter une répétition, jamais plus d'une.",
            "Note tes sensations après la séance : elles t'aideront à repérer ce qui fonctionne le mieux pour toi.",
            "Garde le lendemain facile : une bonne journée d'entraînement s'ancre grâce à une récupération soignée.",
            "Profite de cette fenêtre pour valider une séance clé de ta préparation.",
            "Ne grille pas ta forme : une seule séance de qualité par jour, le reste en endurance.",
        ],
    },
    # Registre : pédagogique et prudent. Le système nerveux va bien, ce sont les structures qui saturent.
    "surcharge_musculaire": {
        "head": [
            "Ratio de charge à {acwr} : tes muscles et tes tendons encaissent plus que ta base ne l'autorise, même si la VFC reste correcte.",
            "Le système nerveux semble disponible (VFC à {hrv_val} ms), mais l'accumulation mécanique des derniers jours laisse présager des jambes lourdes.",
            "Plusieurs séances à fort impact dans les derniers jours : la fatigue est surtout musculaire et articulaire.",
            "Charge de {load_7d} sur 7 jours : l'organisme tient, mais les structures (muscles, tendons) sont les premières à saturer.",
            "Un ratio supérieur à 1,3 est une zone d'attention : on peut continuer à s'entraîner en changeant la nature de la contrainte.",
            "La forme cardio-respiratoire est présente, c'est la capacité de tes jambes à absorber les chocs qui limite aujourd'hui.",
            "Indice de fatigue à {strain_index}/100 : modéré, mais concentré sur le bas du corps.",
            "Mieux vaut éviter d'ajouter de l'impact aujourd'hui : on garde le travail aérobie sans solliciter davantage les jambes.",
            "Facteur d'ajustement de forme à {faf} : séance du jour orientée vers une discipline porteuse (natation, vélo souple).",
            "Le corps prévient avant de casser : la surcharge musculaire se gère très bien par un changement de discipline.",
        ],
        "advice": [
            "Remplace la course par de la natation technique ou du vélo souple pour conserver le volume sans impact.",
            "Ajoute 10 minutes de mobilité (hanches, mollets, ischios) et, si possible, un auto-massage au rouleau.",
            "Évite les séances de jambes en musculation pendant 48 h : travaille plutôt le haut du corps ou le gainage.",
            "Surveille les douleurs localisées (tendon d'Achille, genou, tibia) : elles justifient un jour de repos complet.",
            "Réduis la densité des séances dures de la semaine : deux séances à impact, pas trois.",
            "L'eau et le sommeil restent tes meilleurs alliés pour la réparation des tissus.",
            "Après deux jours de décharge mécanique, tu pourras reprendre une séance de qualité en course.",
            "Garde une cadence de pédalage élevée et des charges légères pour entretenir la circulation sans fatiguer les muscles.",
            "Soigne l'apport en protéines et en hydratation pour aider la réparation musculaire.",
            "Profite de cette décharge mécanique pour travailler la technique de nage ou de pédalage.",
        ],
    },
    # Registre : factuel et pédagogique.
    "maintien": {
        "head": [
            "Indice de fatigue à {strain_index}/100 : situation équilibrée, ni fraîcheur particulière ni fatigue marquée.",
            "VFC à {hrv_val} ms, proche de ta base de {hrv_baseline} ms : l'organisme est stable.",
            "Ratio de charge de {acwr} : la charge est cohérente avec ce que tu supportes habituellement.",
            "Sommeil à {sleep_score}/100 et stress moyen de {stress_avg} : la récupération est correcte sans être exceptionnelle.",
            "Les indicateurs sont dans leur zone habituelle : c'est une phase de consolidation.",
            "Aucun signal d'alerte, aucun signal d'exception : une journée pour entretenir le rythme.",
            "Facteur d'ajustement de forme à {faf} : séance du jour dans la continuité des précédentes.",
            "Charge de {load_7d} sur 7 jours en phase avec ton volume habituel : on maintient le cap.",
            "L'état de forme est stable, ce qui laisse de la place à une séance de développement modérée.",
            "Entre deux blocs de travail, un jour de maintien est précieux : il garde la dynamique sans creuser la fatigue.",
        ],
        "advice": [
            "Privilégie une séance d'endurance ou de tempo modérée, sans chercher la limite.",
            "Garde de la marge : termine la séance en ayant l'impression d'avoir pu faire un peu plus.",
            "Alterne les types d'effort au fil de la semaine pour ne pas répéter la même contrainte.",
            "C'est un bon jour pour travailler la technique (nage, cadence de pédalage, foulée).",
            "Soigne le sommeil des deux prochaines nuits pour préparer la séance de qualité suivante.",
            "Écoute tes sensations dès l'échauffement : si elles sont bonnes, tu peux tenir le haut de la fourchette.",
            "Ajoute un peu de gainage ou de mobilité en fin de séance, c'est un investissement à long terme.",
            "Reste régulier : la progression vient de la répétition de semaines équilibrées.",
            "Évite d'empiler fatigue et intensité aujourd'hui, mieux vaut garder du jus pour la suite.",
            "Profite d'une journée sans enjeu pour t'hydrater et t'alimenter correctement.",
        ],
    },
    # Registre : motivant et pédagogique.
    "assimilation_réussie": {
        "head": [
            "Ratio de charge de {acwr} avec une VFC à {hrv_val} ms : la charge récente est bien assimilée et ta forme progresse.",
            "La VFC remonte au-dessus de sa base ({hrv_pct}) malgré une charge de {load_7d} sur 7 jours : signe d'une bonne adaptation.",
            "Ton organisme absorbe le travail : charge en hausse, VFC stable ou haute, sommeil de qualité.",
            "C'est exactement le schéma attendu d'un bloc réussi : on charge, on récupère, on s'adapte.",
            "Sommeil à {sleep_score}/100 et indice de fatigue à {strain_index}/100 : les dernières séances ont porté leurs fruits.",
            "Tu es dans la zone où la progression se construit : charge suffisante, fatigue maîtrisée.",
            "Facteur d'ajustement de forme à {faf} : l'assimilation est réussie, tu peux enchaîner avec une séance spécifique.",
            "Les signaux physiologiques valident ton bloc d'entraînement récent : bon travail de régularité.",
            "La charge a augmenté sans dégrader la récupération : c'est la marque d'une progression bien dosée.",
            "Les adaptations se mettent en place : le moment est bon pour consolider avec une séance de développement.",
        ],
        "advice": [
            "Capitalise : une séance spécifique ou de développement aérobie va transformer cette bonne assimilation en performance.",
            "Garde la même dynamique de charge sur 2 à 3 jours puis prévois une semaine plus légère pour ancrer les gains.",
            "Ne cherche pas à accélérer la montée en charge : la régularité vaut mieux qu'un pic.",
            "Soigne l'alimentation de récupération : c'est elle qui transforme l'effort en adaptation.",
            "Profite de cette assimilation pour valider une séance clé à allure de course.",
            "Maintiens le sommeil à ce niveau : il est probablement la clé de ta bonne tolérance.",
            "Reste vigilant sur les premières sensations de lourdeur : l'assimilation peut basculer en fatigue si on force.",
            "Ajoute un peu de force-vitesse ou de gainage pour solidifier les gains.",
            "Une séance de qualité aujourd'hui, un jour facile demain : le schéma classique reste le meilleur.",
            "Note ce bloc réussi : il te servira de modèle pour construire les prochains.",
        ],
    },
    # Registre : pédagogique et factuel. Base aérobie à construire avant d'ajouter de l'intensité.
    "déficit_aérobie": {
        "head": [
            "La base aérobie est le maillon faible : le volume en endurance reste en dessous de ce que ta préparation demande.",
            "Trop d'intensité par rapport au volume facile : la répartition de l'entraînement est inversée, il manque de la base.",
            "Indice de fatigue à {strain_index}/100 : tu peux t'entraîner, et c'est l'endurance qui doit passer en priorité.",
            "Charge de {load_7d} sur 7 jours : le volume est insuffisant pour soutenir les objectifs, surtout sur les longues distances.",
            "Sans une base aérobie solide, la progression en vitesse plafonne : c'est le chantier prioritaire.",
            "La sortie longue manque à l'appel depuis plusieurs jours : l'endurance de fond demande de la répétition.",
            "Facteur d'ajustement de forme à {faf} : la fenêtre est bonne pour construire du volume en zone 2.",
            "Le volume hebdomadaire est sous la cible : ajouter de l'endurance facile est le levier le plus rentable.",
            "Les séances intenses sont déjà présentes, c'est le socle aérobie qui doit désormais monter en puissance.",
            "Un moteur aérobie plus large profite à toutes les disciplines : course, vélo et natation.",
        ],
        "advice": [
            "Fais de ce créneau une séance d'endurance fondamentale, à une allure qui reste conversationnelle.",
            "Vise environ 80 % de ton volume en zone 1-2 (modèle polarisé) et limite l'intensité à deux séances par semaine.",
            "Allonge progressivement la sortie longue, de 5 à 10 % par semaine.",
            "Les séances faciles ne sont pas du temps perdu : elles construisent mitochondries et capillaires.",
            "Pense à t'alimenter et t'hydrater pendant les séances de plus de 75 minutes.",
            "Ajoute une séance de vélo en zone 2 pour augmenter le volume aérobie sans surcharger les jambes.",
            "Ralentis volontairement : une endurance trop rapide se transforme en séance moyenne qui fatigue sans développer.",
            "Planifie la sortie longue dans les prochains jours et protège-la en gardant la veille facile.",
            "Une bonne endurance se construit sur plusieurs semaines : l'important est la régularité.",
            "Contrôle l'allure en début de séance : la tentation de partir trop vite est le piège classique de l'endurance.",
        ],
    },
    # Registre : pédagogique et motivant.
    "déficit_anaérobie": {
        "head": [
            "Aucune séance de vitesse ou de VO2max récemment : la base est là, il manque une stimulation de haute intensité.",
            "Indice de fatigue à {strain_index}/100 : tu es suffisamment frais pour réintroduire de l'intensité.",
            "VFC à {hrv_val} ms pour une base de {hrv_baseline} ms : le système nerveux est prêt pour une séance rapide.",
            "Les séances à haute intensité se font rares : sans stimulation, la VO2max et l'économie de course stagnent.",
            "L'endurance est en place ; c'est le moment de la compléter avec du travail à VMA.",
            "Ratio de charge de {acwr} : il y a de la marge pour intégrer une séance exigeante sans risque de surcharge.",
            "Facteur d'ajustement de forme à {faf} : le bon créneau pour travailler la vitesse.",
            "Un peu de vitesse rend les allures de course plus faciles : c'est ce qui manque à ton profil récent.",
            "L'entraînement polarisé suppose quelques séances vraiment intenses, absentes ces dernières semaines.",
            "Réintroduire du fractionné court donnera du relief à ta préparation et réveillera la foulée.",
        ],
        "advice": [
            "Choisis un fractionné court (200 à 600 m) à allure VMA, avec de vraies récupérations.",
            "Soigne un échauffement long : au moins 20 minutes, avec éducatifs et lignes droites.",
            "Garde la qualité avant la quantité : arrête la série si l'allure chute de plus de 5 %.",
            "Place cette séance sur un jour frais, avec une veille facile et un lendemain léger.",
            "Reste sur une seule séance intense par semaine pour commencer, puis passe à deux si tout va bien.",
            "Pense à bien t'hydrater et à manger des glucides avant la séance, la qualité en dépend.",
            "Mélange VMA courte et séance plus longue de seuil pour couvrir tout le spectre.",
            "Les récupérations sont aussi importantes que les efforts : respecte-les pour garder la vitesse.",
            "Sur le vélo, des intervalles de 3 à 5 minutes à haute intensité développent la VO2max sans impact.",
            "Après la séance, prends 24 h de récupération facile avant de remettre de l'intensité.",
        ],
    },
    # Registre : prudent et pédagogique.
    "récupération_incomplète": {
        "head": [
            "Indice de fatigue à {strain_index}/100 : ton corps n'a pas encore récupéré complètement des dernières séances.",
            "VFC à {hrv_val} ms sous ta base de {hrv_baseline} ms ({hrv_pct}) : la récupération est en cours mais incomplète.",
            "Le sommeil ({sleep_score}/100, {sleep_h} h) laisse un déficit de récupération qui s'accumule discrètement.",
            "Body Battery à {body_battery} : la recharge nocturne n'a pas été suffisante pour repartir à plein régime.",
            "Rien d'alarmant, mais plusieurs signaux invitent à la prudence : mieux vaut éviter l'intensité aujourd'hui.",
            "La charge est correcte (ratio {acwr}), c'est la récupération qui est en retard sur la charge.",
            "Facteur d'ajustement de forme à {faf} : séance modulée à la baisse pour laisser le corps finir son travail de réparation.",
            "Stress moyen de {stress_avg} : le stress de la vie quotidienne pèse sur la récupération au même titre que l'entraînement.",
            "Une récupération incomplète se rattrape facilement avec une ou deux journées plus douces.",
            "Le corps assimile encore le travail passé : une séance trop dure maintenant retarderait l'adaptation.",
        ],
        "advice": [
            "Réduis la durée de la séance d'un quart et reste en zone 2, sans intensité.",
            "Ajoute 30 à 45 minutes de sommeil ce soir : c'est le moyen le plus efficace de rattraper le retard.",
            "Évite l'alcool et les repas tardifs, qui dégradent la qualité du sommeil profond.",
            "Prévois une séance technique (natation, cadence de pédalage) plutôt qu'un effort intense.",
            "Surveille ta VFC dans les 2 prochains jours : un retour vers ta base valide la reprise.",
            "Mange suffisamment de glucides : un déficit énergétique ralentit la récupération.",
            "Garde l'intensité pour un jour où la VFC et le sommeil seront de nouveau au vert.",
            "Une courte séance de mobilité ou de marche active favorise la récupération sans la perturber.",
            "Reporte la séance de qualité prévue d'un jour : la performance y gagnera.",
            "Respecte la règle simple : jamais deux jours durs d'affilée tant que la VFC reste basse.",
        ],
    },
    # Registre : factuel et prudent.
    "données_insuffisantes": {
        "head": [
            "Les données de récupération disponibles sont trop partielles pour établir un diagnostic précis aujourd'hui.",
            "Certaines mesures (VFC, sommeil ou charge) manquent : l'analyse se limite aux indicateurs disponibles.",
            "Sans VFC ni sommeil synchronisés, la recommandation du jour reste volontairement prudente.",
            "Les synchronisations récentes sont incomplètes : le diagnostic sera plus fiable dès que les données seront à jour.",
            "Peu d'indicateurs exploitables aujourd'hui : on s'en tient à une séance modérée et à tes sensations.",
            "Aucun voyant d'alerte n'est visible, mais l'absence de mesures empêche de confirmer ton état de forme.",
            "Facteur d'ajustement de forme fixé à {faf} faute de données complètes.",
            "Le diagnostic complet nécessite au moins deux indicateurs parmi VFC, sommeil, charge et Body Battery.",
            "Pense à porter ta montre la nuit : sommeil et VFC alimentent directement l'analyse.",
            "En l'absence de mesures récentes, ce sont tes sensations qui deviennent le meilleur indicateur.",
        ],
        "advice": [
            "Vérifie la synchronisation de ta montre avec Garmin Connect avant la prochaine analyse.",
            "Choisis une séance d'endurance modérée et ajuste selon tes sensations dès l'échauffement.",
            "Évite l'intensité tant que tu ne disposes pas d'au moins deux indicateurs de récupération.",
            "Note ton ressenti (jambes, motivation, sommeil) : c'est utile quand les mesures manquent.",
            "Reste sur un format que tu maîtrises, sans nouveauté ni charge importante.",
            "Si tu te sens bien, tu peux monter légèrement l'intensité en cours de séance, jamais l'inverse.",
            "Programme une séance courte plutôt qu'une longue : tu pourras toujours en faire plus.",
            "Dès que les données sont de retour, l'analyse affinera automatiquement la recommandation.",
            "Pas de séance de force maximale ni de VO2max sans données de récupération fiables.",
            "Garde des repères simples : respiration facile, aucune douleur, fin de séance avec de la réserve.",
        ],
    },
}

PROFILE_LABEL = {
    "fatigue_aiguë": "Fatigue aiguë", "forme_optimale": "Forme optimale", "surcharge_musculaire": "Surcharge musculaire",
    "maintien": "Maintien", "assimilation_réussie": "Assimilation réussie", "déficit_aérobie": "Déficit aérobie",
    "déficit_anaérobie": "Déficit anaérobie", "récupération_incomplète": "Récupération incomplète",
    "données_insuffisantes": "Données insuffisantes",
}

# ---------------------------------------------------------------------------------------------
# CAS CROISÉS : signaux contradictoires ou combinés entre deux axes
# ---------------------------------------------------------------------------------------------
CROSS = {
    "hrv_haute_sommeil_mauvais": [
        "VFC haute ({hrv_val} ms) mais sommeil dégradé ({sleep_score}/100) : le système nerveux semble disponible, la récupération reste à confirmer ; une bonne VFC ne compense pas une nuit courte.",
        "Ta VFC est bonne alors que la nuit a été courte ({sleep_h} h) : profite-en pour une séance modérée, sans intensité prolongée.",
        "Signal contradictoire : VFC élevée, sommeil médiocre. Sur la durée, le manque de sommeil finit par peser sur la VFC : surveille les prochains jours.",
        "Bonne VFC ({hrv_val} ms) malgré un sommeil à {sleep_score}/100 : le corps compense pour l'instant ; garde de la marge sur l'intensité.",
        "Le sommeil est le point faible du jour alors que la VFC est solide : cible une nuit plus longue plutôt que de réduire la charge.",
    ],
    "hrv_basse_sommeil_bon": [
        "VFC basse ({hrv_val} ms pour {hrv_baseline} ms) malgré un bon sommeil ({sleep_score}/100) : la cause n'est pas la nuit, pense à la charge cumulée, au stress ou à un début d'infection.",
        "Sommeil correct mais VFC en retrait : ce schéma révèle souvent une fatigue accumulée ou un stress extérieur, à surveiller 48 h.",
        "Ta nuit était bonne mais la VFC reste basse ({hrv_val} ms) : le système nerveux est encore sollicité, ne te fie pas qu'au ressenti de sommeil.",
        "Contraste notable : bon sommeil et VFC basse. Garde l'intensité en réserve et réévalue demain.",
    ],
    "acwr_douce_hrv_basse": [
        "Ratio de charge raisonnable ({acwr}) mais VFC basse ({hrv_val} ms) : la charge n'explique pas tout, d'autres facteurs (stress, sommeil, santé) pèsent.",
        "La zone de charge est favorable, pourtant la VFC est en retrait : privilégie la prudence malgré un ratio rassurant.",
        "Charge dans la zone douce mais récupération en retard : réduis l'intensité plutôt que le volume.",
        "Un ratio de {acwr} n'empêche pas la fatigue : seul l'ensemble des indicateurs compte.",
    ],
    "acwr_haut_hrv_haute": [
        "Charge élevée (ratio {acwr}) mais VFC haute ({hrv_val} ms) : ton organisme tolère bien cette charge, reste vigilant sur la durée.",
        "VFC solide malgré un ratio élevé : bon signe d'adaptation, sans pour autant justifier de forcer davantage.",
        "Le ratio de charge dépasse la zone idéale ({acwr}) mais la récupération suit : prolonge ce bloc avec prudence, pas plus de deux ou trois jours.",
        "Bonne tolérance à la charge actuelle : conserve le volume mais évite de cumuler de nouvelles séances intenses.",
    ],
    "stress_haut_bb_bas": [
        "Stress élevé ({stress_avg}) et Body Battery bas ({body_battery}) : le stress consomme tes réserves, l'entraînement s'y ajoute.",
        "Quand le stress moyen grimpe à {stress_avg}, la recharge nocturne s'en ressent : prévois une séance courte et facile.",
        "Tes réserves d'énergie sont basses ({body_battery}) dans un contexte de stress marqué : choisis la sobriété.",
        "Stress et fatigue se cumulent : une séance douce, de la marche et une soirée calme valent mieux qu'une séance intense.",
    ],
    "sommeil_court_bb_ok": [
        "Nuit courte ({sleep_h} h) mais Body Battery correct ({body_battery}) : tu tiens, sans réserve pour de l'intensité longue.",
        "Le sommeil manque mais l'énergie est là : une séance modérée est possible, rattrape la dette de sommeil ce soir.",
        "Dette de sommeil sans chute d'énergie : ne confonds pas disponibilité du jour et capacité de récupération.",
    ],
    "charge_haute_sommeil_bon": [
        "Charge soutenue (ratio {acwr}) compensée par un sommeil de qualité ({sleep_score}/100) : le sommeil fait son travail de récupération.",
        "Bon sommeil malgré une charge élevée : c'est un facteur protecteur, à préserver absolument.",
        "Ton sommeil ({sleep_score}/100) amortit la charge actuelle : un point fort de ta préparation.",
    ],
    "readiness_hrv_divergence": [
        "Le score Garmin de readiness ({readiness}) et ta VFC ({hrv_val} ms) ne racontent pas la même histoire : fie-toi à la tendance sur plusieurs jours plus qu'à un seul indicateur.",
        "Divergence entre readiness ({readiness}) et VFC : chacun intègre des signaux différents, privilégie la prudence si l'un des deux est bas.",
        "Les indicateurs sont discordants aujourd'hui : décision à prendre sur tes sensations dès l'échauffement.",
    ],
    "sommeil_profond_bas": [
        "Sommeil profond court ({deep_pct} % de la nuit, repère habituel 13 à 23 %) : la réparation physique est probablement incomplète.",
        "Peu de sommeil profond cette nuit ({deep_pct} %) : c'est la phase de la récupération musculaire, ménage les jambes aujourd'hui.",
        "Le sommeil profond ne représente que {deep_pct} % de la nuit : évite la séance de force maximale ou de fractionné.",
    ],
    "rem_bas": [
        "Sommeil paradoxal (REM) réduit ({rem_pct} % de la nuit, repère habituel 20 à 25 %) : la récupération cognitive et la coordination peuvent en pâtir.",
        "Peu de REM cette nuit ({rem_pct} %) : privilégie une séance simple, sans technique complexe.",
        "REM à {rem_pct} % de la nuit : un peu court, souvent lié à un coucher tardif ou à la fatigue.",
    ],
}

# ---------------------------------------------------------------------------------------------
# CONSIGNES DU JOUR, selon la bande du facteur d'ajustement de forme (FAF)
# ---------------------------------------------------------------------------------------------
CUES = {
    "haut": [
        "FAF à {faf} : séance maintenue à {dur} min telle que prévue, sans réduction.",
        "Tu es en forme : applique la séance à pleine intensité, mais vise la qualité d'exécution plutôt que le chrono.",
        "Avec un FAF de {faf}, tu peux viser le haut de la fourchette des allures, sans dépasser la dernière répétition.",
        "Conditions favorables ({faf}) : concentre-toi sur la technique et la régularité des répétitions.",
        "Séance complète à {dur} min : démarre prudemment, la forme se confirme souvent dans la première moitié.",
        "Feu vert (FAF {faf}) : la dernière répétition doit ressembler à la première.",
    ],
    "normal": [
        "FAF à {faf} : séance quasiment inchangée, {dur} min au lieu de {dur_base} min.",
        "Forme correcte : applique la séance en restant au milieu de la fourchette d'intensité.",
        "Avec un FAF de {faf}, garde une petite marge : arrête-toi une répétition avant l'échec.",
        "Ajustement léger ({dur_base} → {dur} min) pour tenir compte de ta récupération actuelle.",
        "Séance à {dur} min : écoute tes sensations dès l'échauffement et module si besoin.",
        "FAF {faf} : bon équilibre entre stimulation et récupération pour la séance du jour.",
    ],
    "prudent": [
        "FAF à {faf} : durée réduite de {dur_base} à {dur} min et intensité abaissée d'un cran.",
        "Ta récupération n'est pas complète (FAF {faf}) : mieux vaut une séance plus courte et bien faite.",
        "Avec un FAF de {faf}, la séance est allégée ({dur} min) : l'objectif est d'entretenir sans fatiguer.",
        "Séance modulée à {dur} min : reste dans la partie basse de la fourchette d'intensité.",
        "Sommeil à {sleep_score}/100 et VFC à {hrv_val} ms : le corps demande de la modération, tu as raison d'écouter.",
        "FAF {faf} : ajuste en direct, si l'échauffement est lourd, raccourcis encore.",
    ],
    "recup": [
        "FAF à {faf} : séance de récupération uniquement, {dur} min maximum, aucun effort intense.",
        "Le corps a besoin de récupérer (FAF {faf}) : garde la séance courte et sans objectif de performance.",
        "Avec un FAF de {faf}, la meilleure séance est celle qui te laisse plus frais qu'avant.",
        "Aujourd'hui, la progression passe par le repos : {dur} min de séance douce suffisent.",
        "FAF {faf} : tu peux aussi remplacer la séance par du repos complet, sans culpabilité.",
        "Priorité à la récupération : respire facilement, arrête au moindre inconfort.",
    ],
}

# ---------------------------------------------------------------------------------------------
# LIGNES DE SYNTHÈSE (points forts / points à améliorer), 2 à 3 variantes par règle
# ---------------------------------------------------------------------------------------------
LINES = {
    "vol_good": ["Volume de course solide : {kmw} km/semaine, au niveau de la cible ({target}).",
                 "Le kilométrage hebdomadaire ({kmw} km) est conforme à l'objectif de {target} km : une base solide.",
                 "{kmw} km de course par semaine : le volume est en phase avec la préparation."],
    "vol_bad": ["Volume de course faible : {kmw} km/semaine pour une cible de {target}.",
                "Le kilométrage ({kmw} km/semaine) reste sous l'objectif de {target} km : il faut remonter progressivement.",
                "Avec {kmw} km par semaine, le volume est en retrait sur la cible de {target} km."],
    "delta_up": ["Kilométrage en hausse de {d} % par rapport à la période précédente.",
                 "Progression du volume de course : +{d} % sur la période précédente.",
                 "La charge de course augmente ({d} %) : bonne dynamique, à garder maîtrisée."],
    "delta_down": ["Kilométrage en baisse de {d} % par rapport à la période précédente.",
                   "Le volume de course recule de {d} % : à vérifier si c'est un choix (affûtage, récupération) ou une contrainte.",
                   "Moins de course ({d} % de kilomètres) que sur la période précédente."],
    "regular_good": ["Régularité : {rpw} sorties de course par semaine.",
                     "Belle régularité avec {rpw} sorties par semaine.",
                     "Rythme d'entraînement stable : {rpw} sorties de course hebdomadaires."],
    "regular_bad": ["Régularité insuffisante : {rpw} sortie(s) de course par semaine.",
                    "Seulement {rpw} sortie(s) par semaine : la régularité est le premier levier de progression.",
                    "Trop peu de sorties ({rpw} par semaine) pour installer les adaptations."],
    "pace_good": ["Allure moyenne plus rapide de {d} s/km.",
                  "Gain de {d} s/km sur l'allure moyenne : la forme s'affine.",
                  "Tu cours {d} s/km plus vite qu'avant, à effort comparable ou inférieur."],
    "ef_good": ["Efficacité aérobie en progrès ({d} %).",
                "Meilleure économie de course : +{d} % de mètres par battement.",
                "Le rapport vitesse / fréquence cardiaque s'améliore de {d} %."],
    "ef_bad": ["Efficacité aérobie en recul ({d} %) : fatigue ou chaleur possibles.",
               "Moins de mètres par battement ({d} %) : la fatigue pèse sur l'économie de course.",
               "L'efficacité aérobie baisse de {d} % : à surveiller si la tendance se confirme."],
    "acwr_sous": ["Ratio de charge à {acwr} (< 0,8) : sous-entraînement, la charge récente est inférieure à ta base ; adapté à une récupération, pas à une progression.",
                  "Charge aiguë faible (ratio {acwr}) : désentraînement ou affûtage, à assumer si c'est voulu.",
                  "Le ratio {acwr} sous 0,8 traduit une période allégée : les adaptations ne progressent plus sans nouvelle stimulation."],
    "acwr_douce": ["Charge bien dosée : ratio {acwr}, dans la zone douce (0,8–1,3).",
                   "Ratio aigu/chronique de {acwr} : tu progresses dans la zone la plus favorable.",
                   "Zone douce confirmée (ratio {acwr}) : assez de charge pour s'adapter, pas assez pour s'user."],
    "acwr_surcharge": ["Ratio de charge à {acwr} (1,3–1,5) : zone de surcharge, attention aux jambes lourdes et aux petites blessures.",
                       "La charge aiguë dépasse la base ({acwr}) : réduire l'intensité dans les 2 à 3 jours.",
                       "Ratio {acwr} : surcharge modérée, à compenser par un jour de décharge."],
    "acwr_surmenage": ["Ratio de charge à {acwr} (> 1,5) : surmenage, risque élevé de fatigue et de blessure ; prévoir une semaine allégée.",
                       "Charge aiguë très élevée (ratio {acwr}) : priorité à la récupération.",
                       "Le ratio {acwr} indique un pic de charge : mieux vaut ralentir que prolonger."],
    "hrv_good": ["VFC {pct} par rapport à ta base : le système nerveux est disponible.",
                 "Tendance de VFC favorable ({pct} vs base) : bon signe de récupération.",
                 "VFC stable ou haute ({pct}) : l'organisme absorbe bien la charge."],
    "hrv_bad": ["VFC {pct} par rapport à ta base : signe de fatigue accumulée, à surveiller.",
                "Tendance de VFC en recul ({pct}) : le système nerveux est sollicité.",
                "VFC à {pct} de ta base : prudence sur l'intensité."],
    "sleep_good": ["Sommeil de qualité : score moyen {score}/100.",
                   "Score de sommeil moyen de {score}/100 : récupération nocturne solide.",
                   "Nuits régulières ({score}/100 en moyenne) : un point fort."],
    "sleep_bad": ["Sommeil : score moyen {score}/100, un levier de progression.",
                  "Un score de sommeil de {score}/100 limite la récupération.",
                  "Sommeil à améliorer ({score}/100 en moyenne) : c'est la récupération la moins chère."],
    "sleep_debt": ["Dette de sommeil estimée à {debt} h sur les 3 dernières nuits.",
                   "Trois nuits cumulent un déficit de {debt} h par rapport à 7 h 30 : à rattraper.",
                   "Déficit de sommeil de {debt} h sur 3 nuits : la récupération en pâtit."],
    "stages_good": ["Architecture du sommeil équilibrée : {deep_pct} % de sommeil profond et {rem_pct} % de REM.",
                    "Sommeil profond ({deep_pct} %) et REM ({rem_pct} %) dans les repères : récupération physique et cognitive assurées."],
    "stages_bad": ["Sommeil profond ou REM sous les repères ({deep_pct} % et {rem_pct} %) : la qualité de la nuit limite la récupération.",
                   "Architecture du sommeil perfectible : {deep_pct} % de profond, {rem_pct} % de REM."],
    "stress_good": ["Stress modéré ({stress}) : bonne disponibilité mentale.",
                    "Niveau de stress bas ({stress}) : favorable à la récupération."],
    "stress_bad": ["Stress moyen élevé ({stress}) : il pèse sur la récupération.",
                   "Stress à {stress} : l'impact de la vie quotidienne sur ta récupération n'est pas négligeable."],
    "bb_bad": ["Body Battery maximal moyen de {bb} : la recharge nocturne est incomplète.",
               "Body Battery plafonné à {bb} : tu repars rarement à pleine charge."],
    "bb_good": ["Body Battery maximal moyen de {bb} : bonne recharge nocturne.",
                "Tu repars chaque jour avec une bonne réserve d'énergie (Body Battery {bb})."],
    "str_good": ["Musculation régulière ({sw} séance(s)/semaine).",
                 "{sw} séance(s) de musculation par semaine : bon soutien pour la prévention des blessures."],
    "str_bad": ["Musculation sous la cible ({sw} séance(s)/semaine pour {target}).",
                "Pas assez de renforcement ({sw}/semaine) : à compléter pour solidifier les articulations."],
    "cross_good": ["Cross-training présent : {bike} sortie(s) vélo, {swim} natation.",
                   "Vélo et natation complètent bien la course ({bike} + {swim} séances)."],
    "cross_bad": ["Aucune séance de vélo ou de natation sur la période.",
                  "Pas de cross-training sur la période : un peu de vélo ou de natation soulagerait les jambes."],
    "polar_bad": ["{hs} % du temps de course en intensité : trop dense, vise environ 20 %.",
                  "Intensité trop présente ({hs} % du temps de course) : la base aérobie en souffre."],
    "polar_low": ["Seulement {hs} % du temps de course en qualité : un peu d'intensité manque.",
                  "Peu d'intensité récente ({hs} % du temps de course) : à réintroduire progressivement."],
    "polar_good": ["Répartition d'intensité cohérente avec un modèle polarisé ({hs} % du temps de course en qualité).",
                   "{hs} % du temps de course en qualité : proche du 80/20 recommandé."],
}
