"""Objectifs de course : lecture/validation du fichier objectifs.json (écrit par la sous-page « MàJ des objectifs » du dashboard).
Format du fichier : {"version": 1, "goals": [{"sport": "run|trail|triathlon", "name": "10 km", "dist": 10.0, "target": "0:42:00", "date": "2027-01-24"}]}
Si le fichier est absent ou illisible, on retombe sur config.GOALS (objectifs par défaut). Les objectifs sont toujours triés par date."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

SPORTS = {"run": "Course à pied", "trail": "Trail", "swim": "Natation", "bike": "Cyclisme", "triathlon": "Triathlon"}
# Formats multisport : distances usuelles (natation, vélo, course à pied) en km.
# Triathlon (XS à XL), duathlon (sans natation), aquathlon (sans vélo), swimrun (natation et course enchaînées, sans vélo ; la natation totale et la course totale cumulent tous les tronçons).
TRI = {"xs": (0.4, 10, 2.5), "s": (0.75, 20, 5), "m": (1.5, 40, 10), "l": (1.9, 90, 21.1), "xl": (3.8, 180, 42.2),
       "dua_s": (0, 20, 7.5), "dua_m": (0, 40, 15), "dua_l": (0, 60, 20), "aqua_s": (0.75, 0, 5), "aqua_m": (1.5, 0, 10), "aqua_l": (2.5, 0, 15),
       "sr_s": (1.0, 0, 12), "sr_m": (3.0, 0, 25), "sr_l": (5.0, 0, 40), "sr_xl": (10.0, 0, 65)}
TRI_LABEL = {"xs": "XS (super sprint)", "s": "S (sprint)", "m": "M (olympique)", "l": "L (70.3)", "xl": "XL (Ironman)",
             "dua_s": "Duathlon S", "dua_m": "Duathlon M", "dua_l": "Duathlon L", "aqua_s": "Aquathlon S", "aqua_m": "Aquathlon M", "aqua_l": "Aquathlon L",
             "sr_s": "Swimrun S", "sr_m": "Swimrun M", "sr_l": "Swimrun L", "sr_xl": "Swimrun XL", "custom": "Personnalisé"}
# anciens formats d'objectifs déjà enregistrés : conservés comme « personnalisés » avec leurs distances d'origine
TRI_LEGACY = {"xxs": (0.2, 5, 1.5), "sr_xs": (0.5, 0, 6)}


def tri_family(fmt):
    """-> « swimrun », « duathlon », « aquathlon » ou « triathlon » selon le format."""
    f = str(fmt or "")
    return "swimrun" if f.startswith("sr_") else "duathlon" if f.startswith("dua_") else "aquathlon" if f.startswith("aqua_") else "triathlon"


# Distances usuelles en course à pied (km) proposées en un clic
RUN_FORMATS = {"1500m": 1.5, "3k": 3.0, "5k": 5.0, "10k": 10.0, "15k": 15.0, "10mi": 16.0934, "20k": 20.0, "semi": 21.0975, "30k": 30.0, "marathon": 42.195, "50k": 50.0, "100k": 100.0}


def _num(v, default=None):
    try:
        x = float(str(v).replace(",", "."))
        return x if x >= 0 else default
    except (TypeError, ValueError):
        return default
GOALS_FILE = "objectifs.json"
DEFAULT_GITHUB = {"repo": "jordiroubichou-cyber/garmin-dashboard", "workflow": "daily.yml", "branch": "main",
                  "goals_path": GOALS_FILE, "sync_days": 3}


def parse_time(v, hm=False):
    """hm=True : « 2:30 » = 2 h 30 (épreuves longues). Sinon « 42:00 » (min:s), « 3:15:00 » (h:min:s), « 3h15 », « 42 » (minutes) ou un nombre de secondes -> secondes (None si vide/invalide)."""
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v) if v > 0 else None
    t = str(v).strip().lower().replace("h", ":").replace("'", ":").replace("\"", "").replace(",", ".")
    t = re.sub(r":+$", "", t)
    parts = t.split(":")
    try:
        nums = [float(x) for x in parts]
    except ValueError:
        return None
    if len(nums) == 1: sec = nums[0] * 60                       # « 42 » = 42 minutes
    elif len(nums) == 2: sec = nums[0] * 3600 + nums[1] * 60 if hm or "h" in str(v).lower() else nums[0] * 60 + nums[1]
    elif len(nums) == 3: sec = nums[0] * 3600 + nums[1] * 60 + nums[2]
    else: return None
    return int(round(sec)) if sec > 0 else None


def fmt_time(sec):
    if not sec: return ""
    sec = int(sec); return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def _gid(sport, name, dist, used):
    if sport == "run":
        for key, D in (("10k", 10.0), ("semi", 21.0975), ("marathon", 42.195)):
            if abs(dist - D) <= 0.3 and key not in used: return key
    base = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", f"{sport}-{name}".lower()).encode("ascii", "ignore").decode()).strip("-") or sport
    gid, k = base, 2
    while gid in used: gid, k = f"{base}-{k}", k + 1
    return gid


def normalize(raw, warnings=None):
    """Liste brute -> objectifs valides triés par date, au format attendu par l'analyse (id, label, date, dist, target_s, sport + détails)."""
    warnings = warnings if warnings is not None else []
    out, used = [], set()
    if not isinstance(raw, (list, tuple)):
        if raw not in (None, "", {}): warnings.append("liste d'objectifs illisible, ignorée")
        raw = []
    for i, g in enumerate(raw):
        if not isinstance(g, dict):
            warnings.append(f"objectif n°{i + 1} ignoré (format inattendu)"); continue
        try:
            sport = g.get("sport") if g.get("sport") in SPORTS else "run"
            name = str(g.get("name") or g.get("label") or "").strip()[:60]
            d = date.fromisoformat(str(g["date"])[:10]).isoformat()
            extra = {}
            if sport == "triathlon":
                fmt = str(g.get("format") or "m").lower()
                base = TRI.get(fmt) or TRI_LEGACY.get(fmt) or (0, 0, 0)
                fmt = fmt if fmt in TRI else "custom"
                # les valeurs fournies (si présentes) ajustent les distances par défaut du format
                sw, bk, rn = (_num(g.get("swim"), base[0]), _num(g.get("bike"), base[1]), _num(g.get("run"), base[2]))
                be, re_ = _num(g.get("bike_elev")), _num(g.get("run_elev"))
                if not bk: be = None                                  # pas de vélo (aquathlon, swimrun) : pas de dénivelé vélo
                if not rn: re_ = None
                # aucune donnée de dénivelé pour la natation (le dénivelé ne concerne que le vélo et la course)
                dist = round(sw + bk + rn, 3)
                extra = {"format": fmt, "swim": sw, "bike": bk, "run": rn, "bike_elev": be, "run_elev": re_}
            else:
                dist = float(str(g["dist"]).replace(",", "."))
                el = _num(g.get("elev"))
                if el is not None and sport != "swim": extra = {"elev": el}
            if not name or not (0 < dist <= 1000): raise ValueError("nom ou distance invalide")
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            warnings.append(f"objectif n°{i + 1} ignoré ({e})"); continue
        tgt = g.get("target", g.get("target_s"))
        ts = parse_time(tgt, hm=(sport != "run" and not (sport == "swim" and dist < 4)) or (sport == "run" and dist >= 15))
        if tgt not in (None, "") and ts is None: warnings.append(f"objectif « {name} » : temps visé illisible, ignoré")
        gid = _gid(sport, name, dist, used); used.add(gid)
        if g.get("prio") in ("A", "B", "C"): extra["prio"] = g["prio"]          # importance choisie ; absente = automatique
        out.append({"id": gid, "label": name, "name": name, "date": d, "dist": dist, "target_s": ts, "sport": sport, **extra})
    return sorted(out, key=lambda x: (x["date"], x["dist"]))


def from_config(cfg_goals):
    """config.GOALS (ancien format) -> mêmes objectifs normalisés (sport déduit du libellé)."""
    raw = [{"sport": "trail" if "trail" in str(g.get("label", "")).lower() else "run", "name": g.get("label"), "dist": g.get("dist"),
            "target": g.get("target_s"), "date": g.get("date")} for g in cfg_goals]
    return normalize(raw)


def load_goals(root, cfg_goals):
    """-> (objectifs, avertissements, source). root : dossier du projet contenant éventuellement objectifs.json."""
    warnings = []
    p = Path(root) / GOALS_FILE
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            raw = data.get("goals") if isinstance(data, dict) else data
            goals = normalize(raw, warnings)
            if goals or raw == []:
                return goals, warnings, GOALS_FILE
            warnings.append("aucun objectif valide dans objectifs.json : objectifs par défaut utilisés")
        except (OSError, ValueError) as e:
            warnings.append(f"objectifs.json illisible ({type(e).__name__}) : objectifs par défaut utilisés")
    return from_config(cfg_goals), warnings, "config.py"


def to_file_json(goals):
    """Objectifs normalisés -> contenu du fichier objectifs.json."""
    return json.dumps({"version": 1, "goals": to_edit(goals)}, ensure_ascii=False, indent=2) + "\n"


def to_edit(goals):
    """Objectifs normalisés -> liste éditable / sérialisable (sport, name, dist, target, date + détails du sport)."""
    keys = ("format", "swim", "bike", "run", "bike_elev", "run_elev", "elev", "prio")
    return [{"sport": x["sport"], "name": x["name"], "dist": x["dist"], "target": fmt_time(x["target_s"]), "date": x["date"],
             **{k: x[k] for k in keys if x.get(k) is not None}} for x in goals]
