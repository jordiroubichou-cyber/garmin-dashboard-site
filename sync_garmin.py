#!/usr/bin/env python3
"""
sync_garmin.py — pull your own Garmin Connect data (activities + wellness)
into plain-English markdown notes + a data.json file.

Built on the open-source python-garminconnect library by cyberjunky:
https://github.com/cyberjunky/python-garminconnect

Usage:
    python sync_garmin.py --login                  # one-time login, saves a token
    python sync_garmin.py --dry-run                 # test: print, don't write files (30 days)
    python sync_garmin.py --days 3 --sink files --out ./garmin
    python sync_garmin.py --export-ci-token         # for GitHub Actions users only

Your password is only ever typed into a hidden terminal prompt (getpass).
It is never stored, never logged, never printed. The login token Garmin
issues (valid ~1 year) is saved locally under ~/.garmin-ai/tokens so you
don't have to log in again.
"""

import argparse
import base64
import gzip
import getpass
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOKEN_DIR = Path.home() / ".garmin-ai" / "tokens"


def die(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def get_client(require_hidden_input: bool = False):
    """Return an authenticated garminconnect.Garmin client, using the saved token if present."""
    try:
        from garminconnect import Garmin
        from garminconnect.exceptions import (
            GarminConnectAuthenticationError,
            GarminConnectConnectionError,
            GarminConnectTooManyRequestsError,
        )
    except ImportError:
        die("garminconnect is not installed. Run: pip install -r requirements.txt")

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Try restoring a saved session first — no password needed if this works.
    #    Réseau pas encore prêt au réveil du Mac / erreur passagère : on réessaie avant d'abandonner.
    for attempt in range(3):
        try:
            client = Garmin()
            client.login(str(TOKEN_DIR))
            return client
        except GarminConnectTooManyRequestsError as e:
            die(
                "Garmin is rate-limiting this connection right now (429). "
                "Wait a while (or switch network) before retrying.\n"
                f"Details: {e}"
            )
        except GarminConnectConnectionError:
            if attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            if not sys.stdin.isatty():
                die("Connexion à Garmin impossible après 3 essais (réseau ou service indisponible).")
            break
        except (GarminConnectAuthenticationError, FileNotFoundError):
            break  # no valid saved session — fall through to interactive login

    if not sys.stdin.isatty():
        die("Session Garmin absente ou expirée : relance `python sync_garmin.py --login` "
            "dans un terminal puis régénère le secret (--export-ci-token).")

    if require_hidden_input and not sys.stdin.isatty():
        die("This terminal can't hide your password input. Run this from a real terminal window.")

    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password (hidden, not stored): ")

    # The MFA code must be supplied as a callback given to the Garmin() constructor,
    # not passed into login() after the fact.
    client = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("Enter the 2FA code Garmin sent you: ").strip(),
    )
    try:
        client.login(str(TOKEN_DIR))
    except GarminConnectTooManyRequestsError as e:
        die(
            "Garmin is rate-limiting this connection right now (429). "
            "Don't retry immediately — wait a while, or switch network, then try again.\n"
            f"Details: {e}"
        )
    except GarminConnectAuthenticationError as e:
        die(f"Login failed — check your email/password/2FA code and try again.\nDetails: {e}")

    print(f"Logged in. Session token saved to {TOKEN_DIR} (kept local, never printed).")
    return client


def fetch_range(client, days: int):
    today = datetime.now().date()
    start = today - timedelta(days=days)
    wellness = []

    # Fetch activities by date range (more reliable than "last N activities"
    # when several sessions per day are logged).
    activities = client.get_activities_by_date(start.isoformat(), today.isoformat())

    for i in range(days):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        day_data = {"date": d_str}
        for key, fn in [
            ("sleep", lambda: client.get_sleep_data(d_str)),
            ("hrv", lambda: client.get_hrv_data(d_str)),
            ("stats", lambda: client.get_stats(d_str)),
            ("body_battery", lambda: client.get_body_battery(d_str, d_str)),
            ("stress", lambda: client.get_stress_data(d_str)),
            ("training_readiness", lambda: client.get_training_readiness(d_str)),
        ]:
            try:
                day_data[key] = fn()
            except Exception:
                day_data[key] = None
        wellness.append(day_data)
        time.sleep(1)  # short pause to limit the risk of a 429 rate limit

    return activities, wellness


def day_has_data(day: dict) -> bool:
    return any(day.get(k) not in (None, {}, []) for k in ("stats", "sleep", "hrv", "body_battery", "stress", "training_readiness"))


def write_daily_note(day: dict, out_dir: Path):
    d = day["date"]
    if not day_has_data(day):
        return False        # jour vide (limite Garmin, montre non synchronisée) : on ne remplace pas une bonne note par une note vide
    stats = day.get("stats") or {}
    sleep = day.get("sleep") or {}
    hrv = day.get("hrv") or {}
    bb = day.get("body_battery") or []
    stress = day.get("stress") or {}
    tr = day.get("training_readiness") or {}

    def g(dct, *keys, default="—"):
        for k in keys:
            if isinstance(dct, dict) and k in dct and dct[k] is not None:
                return dct[k]
        return default

    resting_hr = g(stats, "restingHeartRate")

    # HRV comes back nested under "hrvSummary".
    hrv_summary = hrv.get("hrvSummary", hrv) if isinstance(hrv, dict) else {}
    hrv_val = g(hrv_summary, "lastNightAvg", "weeklyAvg")

    # Sleep comes back nested under "dailySleepDTO".
    daily_sleep = sleep.get("dailySleepDTO", sleep) if isinstance(sleep, dict) else {}
    sleep_hrs = g(daily_sleep, "sleepTimeSeconds")
    sleep_hrs = round(sleep_hrs / 3600, 1) if isinstance(sleep_hrs, (int, float)) else "—"
    sleep_scores = daily_sleep.get("sleepScores", {}) if isinstance(daily_sleep, dict) else {}
    overall_score = sleep_scores.get("overall", {}) if isinstance(sleep_scores, dict) else {}
    sleep_score = overall_score.get("value") if isinstance(overall_score, dict) else None
    def _min(v):
        return round(v / 60) if isinstance(v, (int, float)) and v > 0 else "—"
    deep_min = _min(g(daily_sleep, "deepSleepSeconds", default=None))
    rem_min = _min(g(daily_sleep, "remSleepSeconds", default=None))
    bb_start = bb[0].get("bodyBatteryValuesArray", [[None, None]])[0][1] if bb and isinstance(bb, list) else "—"
    bb_end = bb[-1].get("bodyBatteryValuesArray", [[None, None]])[-1][1] if bb and isinstance(bb, list) else "—"
    bb_vals = [p[1] for blk in (bb if isinstance(bb, list) else []) if isinstance(blk, dict)
               for p in blk.get("bodyBatteryValuesArray", []) if len(p) > 1 and p[1] is not None]
    bb_max = max(bb_vals) if bb_vals else "—"
    bb_min = min(bb_vals) if bb_vals else "—"
    bb_charged = bb[0].get("charged", "—") if bb and isinstance(bb, list) and isinstance(bb[0], dict) else "—"
    stress_avg = g(stress, "avgStressLevel")
    steps = g(stats, "totalSteps")
    readiness = g(tr, "score") if isinstance(tr, dict) else (tr[0].get("score") if isinstance(tr, list) and tr else "—")

    note = f"""# Garmin wellness {d}
- Resting HR: {resting_hr} bpm
- HRV (overnight): {hrv_val} ms
- Sleep: {sleep_hrs} h (score {sleep_score if sleep_score is not None else "—"})
- Deep sleep: {deep_min} min
- REM sleep: {rem_min} min
- Body battery: {bb_start} -> {bb_end}
- Body battery max/min: {bb_max} / {bb_min}
- Body battery charged: {bb_charged}
- Stress (avg): {stress_avg}
- Steps: {steps}
- Training readiness: {readiness}
"""
    (out_dir / "daily").mkdir(parents=True, exist_ok=True)
    (out_dir / "daily" / f"{d}.md").write_text(note, encoding="utf-8")
    return True


def write_activity_note(a: dict, out_dir: Path):
    name = a.get("activityName", "Activity")
    date = a.get("startTimeLocal", "unknown")[:10]
    a_type = a.get("activityType", {}).get("typeKey", "unknown")
    duration_min = round(a.get("duration", 0) / 60, 1)
    distance_km = round(a.get("distance", 0) / 1000, 2) if a.get("distance") else "—"
    avg_hr = a.get("averageHR", "—")
    calories = a.get("calories", "—")
    elev = a.get("elevationGain", "—")
    load = a.get("activityTrainingLoad")
    load = round(load, 1) if isinstance(load, (int, float)) else "—"
    te = a.get("aerobicTrainingEffect", "—")
    vo2 = a.get("vO2MaxValue", "—")
    power = a.get("avgPower", "—")
    start = (a.get("startTimeLocal") or "")[11:16] or "—"

    safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip().replace(" ", "-")
    filename = f"{date}-{safe_name or a_type}.md"

    note = f"""# {name} ({date})
- Type: {a_type}
- Duration: {duration_min} min
- Distance: {distance_km} km
- Avg HR: {avg_hr} bpm
- Calories: {calories}
- Elevation gain: {elev} m
- Training load: {load}
- Aerobic TE: {te}
- VO2max: {vo2}
- Avg power: {power} W
- Start: {start}
"""
    (out_dir / "activities").mkdir(parents=True, exist_ok=True)
    (out_dir / "activities" / filename).write_text(note, encoding="utf-8")


def _count_days_with_data(wellness) -> int:
    return sum(1 for d in wellness if day_has_data(d))


def merge_with_previous(prev, activities, wellness, keep_days=400):
    """Fusionne la fenêtre récupérée avec l'historique déjà stocké : une synchro courte (ex. 3 jours, lancée à la main)
    ne doit jamais effacer le reste. Les jours/activités récupérés remplacent leurs anciennes versions ; un jour récupéré
    vide ne remplace pas un jour déjà renseigné. Historique limité à keep_days jours."""
    new_days = {d.get("date"): d for d in wellness if d.get("date")}
    old_days = {d.get("date"): d for d in (prev.get("wellness") or []) if isinstance(d, dict) and d.get("date")}
    for k, d in new_days.items():
        if day_has_data(d) or k not in old_days or not day_has_data(old_days[k]):
            old_days[k] = d
    days = [old_days[k] for k in sorted(old_days, reverse=True)][:keep_days]
    def akey(a):
        return a.get("activityId") or (a.get("startTimeLocal"), a.get("activityName"))
    acts = {akey(a): a for a in (prev.get("activities") or []) if isinstance(a, dict)}
    for a in activities:
        acts[akey(a)] = a
    acts = sorted(acts.values(), key=lambda a: a.get("startTimeLocal") or "", reverse=True)
    cut = days[-1].get("date", "") if days else ""
    return [a for a in acts if (a.get("startTimeLocal") or "")[:10] >= cut], days


def write_files_sink(activities, wellness, out_dir: Path):
    """Écrit les notes et data.json avec 3 protections : sauvegarde hebdomadaire compressée, refus d'écraser par un jeu
    nettement plus pauvre que le précédent, et fichier d'état sync_status.json lu par le dashboard (bandeau « données datées »)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "data.json"
    prev = None
    if target.exists():
        try:
            prev = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = None
    n_new = _count_days_with_data(wellness)
    status = {"synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "ok": True, "reason": "", "activities": len(activities),
              "days": len(wellness), "days_with_data": n_new, "kept_previous": False}
    keep_previous = False
    if prev and isinstance(prev, dict):
        dates = {d.get("date") for d in wellness}
        prev_days = [d for d in (prev.get("wellness") or []) if d.get("date") in dates]
        n_prev = _count_days_with_data(prev_days)
        prev_acts = [a for a in (prev.get("activities") or []) if (a.get("startTimeLocal") or "")[:10] >= min(dates, default="")]
        if n_prev >= 5 and n_new < 0.5 * n_prev:
            keep_previous = True
            status["reason"] = f"{n_new} jour(s) de données reçus contre {n_prev} précédemment"
        elif len(prev_acts) >= 3 and not activities:
            keep_previous = True
            status["reason"] = f"aucune activité reçue alors que {len(prev_acts)} étaient connues"
        # sauvegarde hebdomadaire (un fichier compressé par semaine ISO, 6 conservés)
        iso = datetime.now().isocalendar()
        bdir = out_dir / "backup"
        bfile = bdir / f"data-{iso[0]}-W{iso[1]:02d}.json.gz"
        if not bfile.exists():
            bdir.mkdir(parents=True, exist_ok=True)
            bfile.write_bytes(gzip.compress(target.read_bytes()))
            for old in sorted(bdir.glob("data-*.json.gz"))[:-6]:
                old.unlink()
    n_notes = 0
    for day in wellness:
        n_notes += 1 if write_daily_note(day, out_dir) else 0
    for a in activities:
        write_activity_note(a, out_dir)
    if keep_previous:
        status["ok"] = False; status["kept_previous"] = True
        print(f"ATTENTION : synchronisation incomplète ({status['reason']}) : data.json précédent conservé.")
    else:
        if prev and isinstance(prev, dict):
            activities, wellness = merge_with_previous(prev, activities, wellness)
        target.write_text(json.dumps({"activities": activities, "wellness": wellness}, indent=2, default=str), encoding="utf-8")
    (out_dir / "sync_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"Wrote {n_notes} daily notes ({len(wellness) - n_notes} jour(s) vide(s) ignoré(s)) and {len(activities)} activity notes to {out_dir}/")


def send_to_supabase(activities, wellness):
    import requests

    url = os.environ.get("GARMIN_INGEST_URL")
    secret = os.environ.get("GARMIN_INGEST_SECRET")
    if not url:
        die("Set GARMIN_INGEST_URL (and GARMIN_INGEST_SECRET) as environment variables first.")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    resp = requests.post(url, json={"activities": activities, "wellness": wellness}, headers=headers, timeout=30)
    resp.raise_for_status()
    print(f"Sent to {url} — status {resp.status_code}")


def export_ci_token():
    if not TOKEN_DIR.exists():
        die("No saved token found. Run --login first.")
    payload = {}
    for f in TOKEN_DIR.glob("*"):
        payload[f.name] = base64.b64encode(f.read_bytes()).decode()
    out_path = Path("garmin-ci-token.txt")
    out_path.write_text(base64.b64encode(json.dumps(payload).encode()).decode(), encoding="utf-8")
    print(f"Wrote {out_path}. Paste its contents into your GARMIN_TOKEN_B64 GitHub secret, then delete this file.")


def main():
    p = argparse.ArgumentParser(description="Sync your Garmin Connect data to local files.")
    p.add_argument("--login", action="store_true", help="Do the one-time interactive login.")
    p.add_argument("--days", type=int, default=30, help="How many days back to pull (default 30).")
    p.add_argument("--dry-run", action="store_true", help="Print results instead of writing files.")
    p.add_argument("--sink", choices=["files", "supabase"], default="files")
    p.add_argument("--out", default="./garmin", help="Output folder for --sink files.")
    p.add_argument("--export-ci-token", action="store_true")
    args = p.parse_args()

    if args.export_ci_token:
        export_ci_token()
        return

    if args.login:
        get_client(require_hidden_input=True)
        print("Login complete. You can now run: python sync_garmin.py --days 30 --dry-run")
        return

    client = get_client()
    activities, wellness = fetch_range(client, args.days)

    if wellness and all(d.get("stats") is None and d.get("sleep") is None for d in wellness):
        die("Aucune donnée de bien-être récupérée (limite Garmin ou session invalide).")

    if args.dry_run:
        print(json.dumps({"activities": activities, "wellness": wellness}, indent=2, default=str)[:4000])
        print(f"\n(dry run — {len(activities)} activities, {len(wellness)} days of wellness, nothing written)")
        return

    if args.sink == "files":
        write_files_sink(activities, wellness, Path(args.out))
    else:
        send_to_supabase(activities, wellness)


if __name__ == "__main__":
    main()