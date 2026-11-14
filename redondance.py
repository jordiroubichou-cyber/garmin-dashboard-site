"""Mesure de la redondance perceptible entre les paragraphes du coach (aucune dépendance externe).

Deux niveaux, calculés entre un paragraphe du jour et chaque paragraphe antérieur :
  - expressions : part des groupes de mots (propositions de 3 mots ou plus et suites de 3 mots significatifs) déjà lus ;
  - mots        : part des mots significatifs (hors mots-outils, 4 lettres ou plus, racine de 5 lettres) déjà lus.
Nouveauté = 1 - redondance. Un mot-outil (le, de, que…) ne compte jamais : c'est la grammaire, pas du contenu."""
import re

STOP = set("""alors aucun aussi autre avant avec avoir bien cela celle celui cette ceux chaque comme dans donc dont elle elles encore entre était étaient été être fait faire
fois ils leur leurs lors mais même mes moins mon notre nous votre vous ont par pas plus pour puis quand que quel quelle quelles quels qui sans ses son sont sous sur tes
toi ton tous tout toute toutes très une des les aux ces cet cette est sera seras serait soit suis tu te ta ma moi mon ni ou où donc car or ne si se sa ce ça cela celà
y en du de la le l un au à et il on je j m n s t d c qu lui eux elle ceci voici voilà peu trop assez déjà jamais toujours souvent parfois ici là puisque lorsque pendant
depuis vers chez contre malgré selon durant ainsi tant bref""".split())
_WORD = re.compile(r"[a-zàâäçéèêëîïôöùûüœæ]+(?:['’-][a-zàâäçéèêëîïôöùûüœæ]+)*", re.I)


def tokens(text):
    return [w.lower().replace("’", "'") for w in _WORD.findall(text or "")]


def stems(text):
    """Racines (5 premières lettres) des mots significatifs, sans doublon."""
    out = []
    for w in tokens(text):
        for p in re.split(r"['-]", w):
            if len(p) >= 4 and p not in STOP: out.append(p[:5])
    return out


def clauses(text):
    """Propositions normalisées (3 mots ou plus), séparées par la ponctuation."""
    out = set()
    for c in re.split(r"[.!?;:,()…]+", (text or "").lower()):
        w = tokens(c)
        if len(w) >= 3: out.add(" ".join(w))
    return out


def trigrams(text):
    s = stems(text)
    return {tuple(s[i:i + 3]) for i in range(len(s) - 2)}


# Vocabulaire du sujet : mots qui reviennent forcément dans un bilan d'entraînement (la fenêtre, les piliers, les indicateurs, les disciplines).
# Les mesures « mots de style » les écartent : on mesure ce que l'utilisateur perçoit comme une répétition d'écriture (images, tournures, surnoms, verbes).
DOMAINE = set("""semaine semaines mois mois-ci jours jour jordi cette ces dernier derniers période objectif objectifs prédiction prédit prédite visé visée annoncé chrono temps allure
ratio charge charges séance séances entraînement entraînements entraîner course courses courir pied kilomètres kilomètre vélo natation marathon marathonien semi muscu musculation
sommeil dette repos récupération récupérer fatigue forme corps pilier piliers bilan note niveau score volume fréquence régularité progression progrès base base-line
vfc batterie body battery stress cardiaque rythme fréquence puissance zone zones seuil endurance intensité hrv acwr faf état profil""".split())
_DOM = {w[:5] for w in DOMAINE}


def profile(text, style=False):
    """Empreinte précalculée d'un paragraphe. style=True : les mots du sujet (indicateurs, disciplines…) sont écartés des mots comparés."""
    w = stems(text)
    if style: w = [x for x in w if x not in _DOM]
    return {"w": frozenset(w), "c": frozenset(clauses(text)), "t": frozenset(trigrams(text))}


def red_words(a, b):
    return len(a["w"] & b["w"]) / len(a["w"]) if a["w"] else 0.0


def red_expr(a, b):
    """Part des expressions du paragraphe a (propositions + suites de 3 mots significatifs) retrouvées dans b."""
    n = len(a["c"]) + len(a["t"])
    return (len(a["c"] & b["c"]) + len(a["t"] & b["t"])) / n if n else 0.0
