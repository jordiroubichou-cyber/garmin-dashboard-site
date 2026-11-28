"""Lecture tolérante des exports Garmin (notes .md de sync_garmin.py, data.json, CSV).
Fournit load_all(src) -> (activités, jours, stats). Normalement, il n'y a rien à modifier ici.
Jours : sc, sh (heures), deep et rem (minutes, si la montre les fournit), bbx, bbn, bbc, rhr, hrv, st, stp, tr."""
import csv, json, math, re
from collections import defaultdict
from datetime import date

TYPE_COLS = {"type d'activité", "activity type", "activitytype", "type"}

# ---------- utilitaires de lecture tolérante ----------
def lower_items(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield str(k).lower(), v
            if isinstance(v, (dict, list)):
                yield from lower_items(v)
    elif isinstance(o, list):
        for v in o:
            if isinstance(v, (dict, list)):
                yield from lower_items(v)

def index(o):
    idx = {}
    for k, v in lower_items(o):
        idx.setdefault(k, v)
    return idx

def tonum(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    if isinstance(v, str):
        t = v.strip().replace(",", ".").replace("\u202f", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", t):
            return float(t)
    return None

def num(idx, *names):
    for n in names:
        v = idx.get(n)
        if isinstance(v, dict):
            v = v.get("value")
        x = tonum(v)
        if x is not None:
            return x
    return None

def secs(idx, *names):
    for n in names:
        v = idx.get(n)
        if isinstance(v, str) and ":" in v:
            try:
                p = [float(x.replace(",", ".")) for x in v.split(":")]
                return sum(x * 60 ** i for i, x in enumerate(reversed(p)))
            except ValueError:
                continue
        x = tonum(v)
        if x is not None:
            return x
    return None

def first_str(idx, *names):
    for n in names:
        v = idx.get(n)
        if isinstance(v, str) and v:
            return v
    return None

def parse_date(s):
    if not isinstance(s, str):
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

def file_date(name):
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    return None

def sport_of(t):
    t = (t or "").lower()
    if "trail" in t: return "trail"
    if any(x in t for x in ("run", "course", "jogging")): return "run"
    if any(x in t for x in ("cycl", "bik", "vélo", "velo", "ride", "vtt")): return "bike"
    if any(x in t for x in ("swim", "natation", "piscine")): return "swim"
    if any(x in t for x in ("strength", "muscu", "weight", "gym")): return "strength"
    if any(x in t for x in ("walk", "hik", "marche", "rando")): return "walk"
    return "other"

def collect_activities(o, out):
    if isinstance(o, dict):
        k = {str(x).lower() for x in o}
        if "activityid" in k and ({"activitytype", "distance", "duration", "starttimelocal"} & k):
            out.append(o)
            return
        for v in o.values():
            collect_activities(v, out)
    elif isinstance(o, list):
        for v in o:
            collect_activities(v, out)

# ---------- extraction ----------
def parse_activity(rec, kind):
    idx = index(rec)
    start = first_str(idx, "starttimelocal", "startdatetimelocal", "date", "début", "start time")
    d = parse_date(start)
    if not d:
        return None
    typ = first_str(idx, "typekey") or first_str(idx, "activitytype", "type d'activité", "activity type", "type")
    sp = sport_of(typ)
    dist = num(idx, "distance")
    km = (dist / 1000 if kind == "json" else dist) if dist else 0.0
    dur = secs(idx, "duration", "elapsedduration", "durée", "temps", "time") or 0
    hr = num(idx, "averagehr", "avghr", "average heart rate", "fc moyenne", "avg hr")
    el = num(idx, "elevationgain", "total ascent", "dénivelé positif", "ascent") or 0
    ld = num(idx, "activitytrainingload")
    est = False
    if ld is None:
        ld = (dur / 60) * ((hr or 130) / 150) ** 2 * (0.6 if sp == "strength" else 1)
        est = True
    nm = first_str(idx, "activityname", "titre", "title", "nom") or ""
    return {"nm": nm, "id": idx.get("activityid"), "d": d, "t": (start or "")[11:16], "s": sp,
            "km": round(km, 2), "m": round(dur / 60, 1), "hr": hr, "el": round(el),
            "ld": round(ld, 1), "est": est, "te": num(idx, "aerobictrainingeffect"),
            "vo2": num(idx, "vo2maxvalue"), "pw": num(idx, "avgpower", "averagepower"),
            "cal": num(idx, "calories")}

def parse_daily(rec, fdate):
    idx = index(rec)
    d = parse_date(first_str(idx, "calendardate", "date", "jour", "summarydate")) or fdate
    if not d:
        return None, {}
    bbx = num(idx, "bodybatteryhighestvalue", "highestbodybattery", "bb_max", "body_battery_max", "bodybatterymax")
    bbn = num(idx, "bodybatterylowestvalue", "lowestbodybattery", "bb_min", "body_battery_min", "bodybatterymin")
    arr = idx.get("bodybatteryvaluesarray")
    if isinstance(arr, list) and (bbx is None or bbn is None):
        vals = [p[1] for p in arr if isinstance(p, (list, tuple)) and len(p) > 1 and tonum(p[1]) is not None]
        if vals:
            bbx = bbx if bbx is not None else max(vals)
            bbn = bbn if bbn is not None else min(vals)
    sl = secs(idx, "sleeptimeseconds", "totalsleepseconds")
    if sl is None and num(idx, "sleep_hours", "sleephours") is not None:
        sl = num(idx, "sleep_hours", "sleephours") * 3600
    trv = rec.get("training_readiness") if isinstance(rec, dict) else None
    if isinstance(trv, list) and trv and isinstance(trv[0], dict): trv = trv[0].get("score")
    elif isinstance(trv, dict): trv = trv.get("score")
    tr = tonum(trv) if trv is not None else num(idx, "trainingreadiness", "training_readiness")
    m = {"tr": tr, "sc": num(idx, "sleepscore", "sleep_score", "overallscore", "overall"),
         "sh": round(sl / 3600, 2) if sl else None,
         "deep": (round(num(idx, "deepsleepseconds") / 60) if num(idx, "deepsleepseconds") else None),
         "rem": (round(num(idx, "remsleepseconds") / 60) if num(idx, "remsleepseconds") else None),
         "bbx": bbx, "bbn": bbn, "bbc": num(idx, "bodybatterychargedvalue", "bb_charge"),
         "rhr": num(idx, "restingheartrate", "resting_hr", "restinghr", "fc repos"),
         "hrv": num(idx, "lastnightavg", "avgovernighthrv", "hrv"),
         "st": num(idx, "averagestresslevel", "avgstress", "stress"),
         "stp": num(idx, "totalsteps", "steps")}
    return d, {k: v for k, v in m.items() if v is not None}


# ---------- lecture des fichiers Markdown (format sync_garmin.py) ----------
NUM = re.compile(r"-?\d+(?:[.,]\d+)?")

def md_pairs(txt):
    out = []
    for line in txt.splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?\**([^:*]{2,60}?)\**\s*:\s*\**\s*(.*?)\s*$", line)
        if m:
            out.append((m.group(1).strip().lower(), m.group(2).strip()))
    return out

def first_num(v):
    m = NUM.search(v or "")
    return float(m.group(0).replace(",", ".")) if m else None

def dur_s(v):
    v = (v or "").strip().lower()
    if not v or v[0] in "—-–":
        return None
    m = re.match(r"^(\d+):(\d{2}):(\d{2})", v)
    if m: return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m = re.match(r"^(\d+):(\d{2})\b", v)
    if m: return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r"^(\d+[.,]\d+)\s*h", v)
    if m: return float(m.group(1).replace(",", ".")) * 3600
    m = re.match(r"^(\d+)\s*h\s*(\d{1,2})?", v)
    if m: return int(m.group(1)) * 3600 + int(m.group(2) or 0) * 60
    n = first_num(v)
    if n is None: return None
    if "min" in v: return n * 60
    return n if n > 600 else n * 60

def parse_md_daily(txt, fdate):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", txt.splitlines()[0] if txt else "")
    d = m.group(1) if m else fdate
    if not d:
        return None, {}
    r = {}
    for k, v in md_pairs(txt):
        if "resting" in k or "repos" in k: r["rhr"] = first_num(v)
        elif "hrv" in k or "vfc" in k: r["hrv"] = first_num(v)
        elif k.startswith("deep") or "profond" in k: r["deep"] = first_num(v)
        elif k.startswith("rem") or k.startswith("sommeil paradoxal"): r["rem"] = first_num(v)
        elif "sleep" in k or "sommeil" in k:
            h = dur_s(v.split("(")[0])
            if h: r["sh"] = round(h / 3600, 2)
            sc = re.search(r"score\s*([\d.,]+)", v, re.I)
            if sc: r["sc"] = first_num(sc.group(1))
        elif "body" in k or "battery" in k:
            vals = [float(x.replace(",", ".")) for x in NUM.findall(v)]
            if not vals: continue
            if "charged" in k: r["bbc"] = vals[0]
            elif "max" in k and len(vals) >= 2: r["bbx"], r["bbn"] = vals[0], vals[1]
            elif "bbx" not in r: r["bbx"], r["bbn"] = max(vals), min(vals)
        elif "stress" in k: r["st"] = first_num(v)
        elif "steps" in k or "pas" == k: r["stp"] = first_num(v)
        elif "readiness" in k or "préparation" in k: r["tr"] = first_num(v)
    return d, {k: v for k, v in r.items() if v is not None}

def parse_md_activity(txt, fname):
    d = file_date(fname)
    if not d:
        return None
    title = next((l.lstrip("# ").strip() for l in txt.splitlines() if l.startswith("#")), "")
    name = fname.rsplit(".", 1)[0]
    label = f"{title} {name}".lower()
    sp = sport_of(label)
    if sp in ("other", "walk") and re.search(r"endurance|fraction|\d+\s*x\s*\d+|seuil|footing|tempo|\d\s*km", label) \
            and not re.search(r"vélo|velo|cycl|nat|swim|muscu", label):
        sp = "run"
    if sp == "other" and "course" in label: sp = "run"
    v = {}
    for k, val in md_pairs(txt):
        if k == "type":
            t = sport_of(val)
            if t != "other": sp = t
        elif "distance" in k:
            n = first_num(val)
            if n is not None:
                low = val.lower()
                v["km"] = n / 1000 if (re.search(r"\d\s*m\b", low) and "km" not in low) else n
        elif any(x in k for x in ("durée", "duree", "duration", "temps", "time")) and "dur" not in v:
            v["dur"] = dur_s(val)
        elif ("hr" in k or "fc" in k or "cardi" in k) and any(x in k for x in ("avg", "moy", "average")): v["hr"] = first_num(val)
        elif any(x in k for x in ("elev", "dénivel", "denivel", "ascent", "d+")): v["el"] = first_num(val)
        elif "load" in k or "charge" in k: v["ld"] = first_num(val)
        elif "vo2" in k: v["vo2"] = first_num(val)
        elif "power" in k or "puissance" in k: v["pw"] = first_num(val)
        elif "calor" in k: v["cal"] = first_num(val)
        elif "effect" in k or "effet" in k or "aerobic" in k: v["te"] = first_num(val)
        elif k in ("start", "début", "heure", "start time"):
            t = re.search(r"\d{1,2}:\d{2}", val)
            if t: v["t"] = t.group(0)
    km = v.get("km")
    if not km:
        mk = re.search(r"(\d+(?:[.,]\d+)?)\s*km", label)
        km = float(mk.group(1).replace(",", ".")) if mk else 0.0
    dur = v.get("dur") or 0
    hr, ld = v.get("hr"), v.get("ld")
    est = ld is None
    if est:
        ld = (dur / 60) * ((hr or 130) / 150) ** 2 * (0.6 if sp == "strength" else 1)
    nm = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", title).strip()
    return {"nm": nm, "id": None, "d": d, "t": v.get("t", ""), "s": sp, "km": round(km, 2), "m": round(dur / 60, 1),
            "hr": hr, "el": round(v.get("el") or 0), "ld": round(ld, 1), "est": est, "te": v.get("te"),
            "vo2": v.get("vo2"), "pw": v.get("pw"), "cal": v.get("cal"), "_md": True}

def load_all(src):
    acts, daily, stats = [], defaultdict(dict), defaultdict(int)
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        if p.name == "sync_status.json":
            continue
        ext = p.suffix.lower()
        try:
            if ext in (".json", ".jsonl"):
                txt = p.read_text(encoding="utf-8")
                objs = [json.loads(l) for l in txt.splitlines() if l.strip()] if ext == ".jsonl" else [json.loads(txt)]
                kind = "json"
            elif ext == ".csv":
                with p.open(encoding="utf-8-sig", newline="") as f:
                    sample = f.read(4096); f.seek(0)
                    objs = [list(csv.DictReader(f, delimiter=";" if sample.count(";") > sample.count(",") else ","))]
                kind = "csv"
            elif ext == ".md":
                txt = p.read_text(encoding="utf-8")
                stats["fichiers"] += 1
                if p.parent.name == "daily" or txt.lstrip().lower().startswith("# garmin wellness"):
                    d, m = parse_md_daily(txt, file_date(p.name))
                    if d:
                        daily[d].update(m); stats["md_daily"] += 1
                else:
                    a = parse_md_activity(txt, p.name)
                    if a:
                        acts.append(a); stats["md_activités"] += 1
                continue
            elif ext == ".fit":
                stats["fit_ignorés"] += 1
                continue
            else:
                continue
        except Exception:
            stats["erreurs_lecture"] += 1
            continue
        stats["fichiers"] += 1
        fdate = file_date(p.name) or file_date(p.parent.name)
        for obj in objs:
            if kind == "csv":
                if obj and any(k.lower() in TYPE_COLS for k in obj[0]):
                    for r in obj:
                        a = parse_activity(r, "csv")
                        if a: acts.append(a)
                else:
                    for r in obj:
                        d, m = parse_daily(r, fdate)
                        if d: daily[d].update(m)
                continue
            found = []
            collect_activities(obj, found)
            if isinstance(obj, dict) and isinstance(obj.get("wellness"), list):
                for w in obj["wellness"]:
                    if isinstance(w, dict):
                        d, m = parse_daily(w, fdate)
                        if d: daily[d].update(m)
            if found:
                for r in found:
                    a = parse_activity(r, "json")
                    if a: acts.append(a)
            else:
                for r in (obj if isinstance(obj, list) else [obj]):
                    if isinstance(r, dict):
                        d, m = parse_daily(r, fdate)
                        if d: daily[d].update(m)
    seen, uniq = set(), []
    for a in acts:
        key = a["id"] or (a["d"], a["t"], a["s"], a["km"])
        if key not in seen:
            seen.add(key); uniq.append(a)
    uniq.sort(key=lambda a: (a["est"], bool(a.get("_md"))))  # les fiches les plus riches d'abord
    kept = []
    for a in uniq:
        same = lambda b: b["d"] == a["d"] and b["s"] == a["s"] and (
            abs(b["km"] - a["km"]) <= 0.3 if (a["km"] or b["km"]) else abs(b["m"] - a["m"]) <= 3)
        if not any(same(b) for b in kept):
            kept.append(a)
    uniq = kept
    uniq.sort(key=lambda a: (a["d"], a["t"]))
    return uniq, dict(daily), dict(stats)

