"""Envoi d'e-mails de confirmation de rendez-vous.
Si SMTP_HOST n'est pas défini, l'e-mail est SIMULÉ (affiché dans le terminal)."""
import os
import smtplib
from email.message import EmailMessage


def send_email(to, subject, body):
    host = os.getenv("SMTP_HOST", "")
    if not host:
        print(f"[E-MAIL SIMULÉ] à {to} | {subject}\n{body}\n")
        return "simulé"
    try:
        msg = EmailMessage()
        msg["From"] = os.getenv("SMTP_SENDER", os.getenv("SMTP_USER", ""))
        msg["To"], msg["Subject"] = to, subject
        msg.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            if os.getenv("SMTP_USER"):
                s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return "envoyé"
    except Exception as exc:
        return f"échec : {exc}"


def confirm_rdv(patient, date, heure, level_label):
    """Retourne le statut d'envoi, ou 'pas d'e-mail' si le patient n'en a pas."""
    if not patient.get("email"):
        return "pas d'e-mail"
    body = (f"Bonjour {patient['prenom']},\n\n"
            f"Votre rendez-vous est fixé le {date} à {heure}.\n"
            f"Niveau de priorité : {level_label}.\n\n"
            "En cas d'empêchement, merci de nous prévenir.\n\nGlycoFlow")
    return send_email(patient["email"], "Confirmation de votre rendez-vous", body)