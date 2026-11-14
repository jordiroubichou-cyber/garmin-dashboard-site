#!/usr/bin/env python3
"""Envoie le bilan du jour : synthèse de la Partie 1 (1 semaine glissante) dans le corps du mail,
sans pièce jointe.
Le lien vers le dashboard interactif est intégré au corps du mail (voir build_dashboard.py).
Configuration par variables d'environnement (secrets GitHub) :
  MAIL_USER (identifiant SMTP), MAIL_PASSWORD (mot de passe d'application), MAIL_TO (destinataire),
  MAIL_FROM (expéditeur, défaut = MAIL_USER), MAIL_HOST (défaut smtp.mail.me.com), MAIL_PORT (défaut 587)."""
import argparse, os, re, smtplib, ssl, sys
from email.message import EmailMessage
from pathlib import Path



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", type=Path, default=Path("dist"))
    ap.add_argument("--warn", default="")
    ap.add_argument("--dry-run", action="store_true", help="écrit mail_test.eml sans envoyer")
    a = ap.parse_args()
    env = os.environ.get
    user, to = env("MAIL_USER", ""), env("MAIL_TO", "")
    sender = env("MAIL_FROM") or user
    if not (user and to) and not a.dry_run:
        sys.exit("MAIL_USER / MAIL_TO manquants.")
    summary = a.dist / "email_summary.html"
    if not summary.exists():
        sys.exit("email_summary.html introuvable : la génération du dashboard a échoué.")
    body = summary.read_text(encoding="utf-8")
    m = re.search(r"<!--SUBJECT: (.*?)-->", body)
    subject = m.group(1) if m else "Performance : bilan du jour"
    warn = a.warn
    mw = re.search(r"<!--WARN: (.*?)-->", body, re.S)
    banner_in_body = bool(mw) and not warn
    if banner_in_body:
        warn = mw.group(1).strip()
    if warn:
        subject = "⚠ " + subject
    if warn and not banner_in_body:
        body = f'<p style="color:#FF3B30;font-family:Helvetica,Arial,sans-serif;font-size:14px"><b>⚠ {warn}</b></p>' + body
    text = re.sub(r"<[^>]+>", " ", re.sub(r"</(div|h\d|p|tr)>", "\n", body))
    text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text.replace("&amp;", "&").replace("&#x27;", "'"))).strip()
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender or "dashboard@example.com", to or "test@example.com"
    msg.set_content(text)
    msg.add_alternative(body, subtype="html")
    if a.dry_run:
        (a.dist / "mail_test.eml").write_bytes(bytes(msg))
        print("mail_test.eml écrit (rien envoyé).")
        return
    pwd = env("MAIL_PASSWORD", "")
    if not pwd:
        sys.exit("MAIL_PASSWORD manquant.")
    with smtplib.SMTP(env("MAIL_HOST", "smtp.mail.me.com"), int(env("MAIL_PORT", "587")), timeout=90) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(user, pwd)
        s.send_message(msg)
    print("Mail envoyé à", to)


if __name__ == "__main__":
    main()
