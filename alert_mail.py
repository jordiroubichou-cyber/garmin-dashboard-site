#!/usr/bin/env python3
"""Envoie un mail d'alerte court quand le workflow quotidien échoue (étape, lien vers le journal, causes probables).
Usage (étape finale du workflow, avec « if: failure() ») : python alert_mail.py --step "Synchronisation Garmin"
Variables : MAIL_USER, MAIL_PASSWORD, MAIL_TO (mêmes secrets que send_mail.py) ; GITHUB_* fournies automatiquement par GitHub Actions."""
import argparse, html, os, smtplib, ssl, sys
from email.message import EmailMessage
from datetime import datetime, timezone

HINTS = {
    "sync": "La session Garmin a probablement expiré : sur ton Mac, lance `python sync_garmin.py --login` puis `python sync_garmin.py --export-ci-token`, et colle le contenu du fichier dans le secret GARMIN_TOKEN_B64 du dépôt.",
    "build": "Le calcul du dashboard a échoué : ouvre le journal, la dernière ligne rouge donne le fichier et la ligne en cause. Tu peux m'envoyer ce texte.",
    "mail": "L'envoi du mail a échoué : vérifie le mot de passe d'application iCloud (secret MAIL_PASSWORD).",
    "publish": "La publication de la page chiffrée a échoué : vérifie le secret SITE_PUSH_TOKEN (jeton GitHub expiré ?).",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default="étape inconnue")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    env = os.environ.get
    user, to = env("MAIL_USER", ""), env("MAIL_TO", "")
    if not (user and to) and not a.dry_run:
        sys.exit("MAIL_USER / MAIL_TO manquants.")
    repo, run = env("GITHUB_REPOSITORY", ""), env("GITHUB_RUN_ID", "")
    link = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{run}" if repo and run else ""
    low = a.step.lower()
    hint = next((v for k, v in HINTS.items() if k in low or (k == "sync" and "garmin" in low)), "Ouvre le journal de l'exécution pour voir l'erreur exacte.")
    body = (f'<div style="font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:560px;margin:auto;color:#1D1D1F">'
            f'<div style="font-size:22px;font-weight:700;color:#FF3B30;margin-bottom:8px">⚠ Le dashboard du jour n’a pas pu être généré</div>'
            f'<p style="font-size:15px;line-height:1.5">Étape en échec : <b>{html.escape(a.step)}</b><br>Le dernier dashboard publié reste en ligne, mais il n’est pas à jour.</p>'
            f'<p style="font-size:14px;line-height:1.5;background:#F5F5F7;border-radius:12px;padding:12px 14px">{html.escape(hint)}</p>'
            + (f'<p><a href="{html.escape(link)}" style="color:#007AFF">Ouvrir le journal de l’exécution</a></p>' if link else "")
            + f'<p style="font-size:12px;color:#86868B">{datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC</p></div>')
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = f"⚠ Échec du dashboard : {a.step}", env("MAIL_FROM") or user or "dashboard@example.com", to or "test@example.com"
    msg.set_content(f"Le dashboard du jour n'a pas pu être généré. Étape en échec : {a.step}. {hint} {link}")
    msg.add_alternative(body, subtype="html")
    if a.dry_run:
        print(msg.as_string()[:600]); return
    pwd = env("MAIL_PASSWORD", "")
    if not pwd:
        sys.exit("MAIL_PASSWORD manquant.")
    with smtplib.SMTP(env("MAIL_HOST", "smtp.mail.me.com"), int(env("MAIL_PORT", "587")), timeout=60) as sm:
        sm.starttls(context=ssl.create_default_context()); sm.login(user, pwd); sm.send_message(msg)
    print("Mail d'alerte envoyé à", to)


if __name__ == "__main__":
    main()
