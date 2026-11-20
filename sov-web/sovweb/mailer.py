"""Invio email. Senza SMTP configurato (sviluppo) l'email viene scritta nel log e tenuta in `OUTBOX`."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)
OUTBOX: list[dict] = []  # ultime email "inviate" quando SMTP non è configurato (utile in sviluppo e nei test)


def send_email(settings, to: list[str] | str, subject: str, body: str) -> bool:
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return False
    if not settings.email_enabled:
        OUTBOX.append({"to": recipients, "subject": subject, "body": body})
        del OUTBOX[:-50]
        log.info("Email (non inviata, SMTP non configurato) a %s: %s\n%s", recipients, subject, body)
        return True
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        log.exception("Invio email non riuscito a %s", recipients)
        return False
