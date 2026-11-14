"""Mémoire anti-redondance du « mot du coach » (déterministe, sans IA).

Chaque jour, les paragraphes publiés (un par période) sont conservés dans un petit fichier JSON du dépôt (garmin/coach_memory.json, 60 jours).
Pour composer le paragraphe du jour, chaque bloc (salutation, accroche, piliers, objectif, état, blague, conclusion…) est choisi parmi les variantes
possibles en minimisant un coût de redondance avec ce qui a déjà été lu : expressions communes et mots significatifs, pondérés par l'ancienneté
(la veille compte le plus, puis la semaine, puis les 2 semaines, puis le mois). À mémoire vide, le comportement reste la rotation habituelle.
Le résultat dépend uniquement des données du jour et de la mémoire : relancer la génération le même jour redonne exactement le même texte."""
import json
import re
from datetime import date
from pathlib import Path

import redondance as R

KEEP_DAYS = 60
# poids selon l'ancienneté (en jours) : la veille est ce qui se remarque le plus
AGE_W = [(1, 14.0), (2, 9.0), (3, 7.0), (7, 5.0), (14, 3.5), (30, 1.5), (60, 0.5)]
SAME_KEY, OTHER_KEY, SAME_DAY = 1.0, 0.35, 0.6


def _w(age):
    for lim, w in AGE_W:
        if age <= lim: return w
    return 0.0


class Memoire:
    def __init__(self, data=None, today=None):
        """data : {"AAAA-MM-JJ": {"1S": texte, …}} ; today : date du jour (les jours postérieurs ou égaux sont ignorés)."""
        self.today = today
        self.entries = []                                   # (âge, clé, texte minuscule)
        self.day = []                                       # paragraphes déjà composés aujourd'hui : (clé, empreinte)
        self._prof = []                                     # empreintes des entrées, alignées sur self.entries
        self._cw = {}                                       # surnoms : coûts déjà calculés
        self._agg = {}                                      # clé -> poids cumulés par mot / expression (calculés une fois)
        for d, per in (data or {}).items():
            try:
                age = (today - date.fromisoformat(d)).days
            except (ValueError, TypeError):
                continue
            if age < 1 or age > KEEP_DAYS or not isinstance(per, dict): continue
            for k, t in per.items():
                if isinstance(t, str) and t:
                    self.entries.append((age, k, " " + " ".join(re.findall(r"[\wàâäçéèêëîïôöùûü]+", t.lower().replace("’", "'"))) + " ")); self._prof.append(R.profile(t))

    def _aggregate(self, key):
        """Poids cumulés : pour chaque racine, expression ou suite de mots, somme des poids (ancienneté x période) des textes qui la contiennent.
        La somme des redondances pondérées d'un candidat avec tous les textes se lit alors en une seule passe sur ses propres éléments."""
        if key in self._agg: return self._agg[key]
        agg = {"w": {}, "c": {}, "t": {}}
        for (age, k, _), q in zip(self.entries, self._prof):
            w = _w(age) * (SAME_KEY if k == key else OTHER_KEY)
            for f in ("w", "c", "t"):
                d = agg[f]
                for x in q[f]: d[x] = d.get(x, 0.0) + w
        self._agg[key] = agg
        return agg

    # --- coût d'un texte candidat -----------------------------------------------------------------
    def cost(self, text, key, extra=()):
        """Redondance pondérée du candidat avec la mémoire, les paragraphes du jour et les blocs déjà choisis dans ce paragraphe (extra)."""
        p = R.profile(text)
        agg = self._aggregate(key)
        nw, ne = len(p["w"]), len(p["c"]) + len(p["t"])
        c = sum(agg["w"].get(x, 0.0) for x in p["w"]) / nw if nw else 0.0
        if ne: c += 2.0 * (sum(agg["c"].get(x, 0.0) for x in p["c"]) + sum(agg["t"].get(x, 0.0) for x in p["t"])) / ne
        for k, q in self.day:
            if k != key: c += 6.0 * SAME_DAY * (R.red_words(p, q) + 2.0 * R.red_expr(p, q))
        for q in extra:
            c += 1.8 * (R.red_words(p, q) + 2.0 * R.red_expr(p, q))
        return c

    def cost_word(self, word, key):
        """Coût d'un surnom ou d'une insulte : nombre pondéré d'apparitions récentes (résultat mémorisé)."""
        ck = (word, key)
        if ck in self._cw: return self._cw[ck]
        pat = " " + " ".join(re.findall(r"[\wàâäçéèêëîïôöùûü]+", word.lower().replace("’", "'"))) + " "
        c = sum(_w(a) * (SAME_KEY if k == key else OTHER_KEY) for a, k, t in self.entries if pat in t)
        self._cw[ck] = c
        return c

    def record_today(self, key, text):
        if text: self.day.append((key, R.profile(text)))


def load(path):
    """Lit le fichier ; tout problème (absent, corrompu) donne une mémoire vide."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def merge(data, today, texts):
    """Ajoute (ou remplace) les textes du jour et ne garde que les KEEP_DAYS derniers jours."""
    out = dict(data or {})
    out[today.isoformat()] = {k: t for k, t in texts.items() if t}
    keep = {}
    for d, v in out.items():
        try:
            if 0 <= (today - date.fromisoformat(d)).days <= KEEP_DAYS: keep[d] = v
        except ValueError:
            continue
    return dict(sorted(keep.items()))


def save(path, data):
    p = Path(path)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)
