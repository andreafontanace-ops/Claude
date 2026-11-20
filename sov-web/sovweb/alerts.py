"""Avvisi: dopo ogni raccolta si confronta la classifica con quella precedente dello stesso feed."""

from __future__ import annotations

import logging
import smtplib
from collections import defaultdict
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AlertRule, BrandSov, Notification, Run, Subscription, Workspace

log = logging.getLogger(__name__)

# tipo -> (titolo, descrizione per la pagina degli avvisi)
KINDS = {
    "own_drop": ("Un mio marchio perde quota", "quando un tuo marchio perde almeno {t} punti di share of voice"),
    "own_rank_lost": ("Un mio marchio scende in classifica", "quando un tuo marchio perde una o più posizioni"),
    "competitor_top3": ("Un concorrente entra nei primi 3", "quando un altro marchio entra tra i primi 3"),
    "new_top10": ("Un marchio nuovo nei primi 10", "quando un marchio che non c'era entra tra i primi 10"),
}
DEFAULT_RULES = [("own_drop", 0.02), ("own_rank_lost", 0.0), ("competitor_top3", 0.0), ("new_top10", 0.0)]


def add_default_rules(ws: Workspace) -> list[AlertRule]:
    return [AlertRule(workspace_id=ws.id, kind=k, threshold=t) for k, t in DEFAULT_RULES]


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%".replace(".", ",")


def evaluate(session: Session, run: Run) -> list[Notification]:
    """Crea le notifiche per tutti i clienti che seguono il feed di questa esecuzione."""
    if run.status != "ok":
        return []
    prev = session.scalar(select(Run).where(Run.feed_id == run.feed_id, Run.status == "ok", Run.id < run.id)
                          .order_by(Run.id.desc()))
    if prev is None:
        return []
    cur = {b.brand: b for b in session.scalars(select(BrandSov).where(BrandSov.run_id == run.id))}
    old = {b.brand: b for b in session.scalars(select(BrandSov).where(BrandSov.run_id == prev.id))}
    feed = run.feed
    where = f"{feed.site.name} · {feed.category.name}"
    created: list[Notification] = []
    for sub in session.scalars(select(Subscription).where(Subscription.feed_id == feed.id)):
        ws = sub.workspace
        rules = session.scalars(select(AlertRule).where(AlertRule.workspace_id == ws.id, AlertRule.active)).all()
        own = {b.name.lower() for b in ws.brands if b.category_id == feed.category_id and b.role == "own"}
        for rule in rules:
            for text in _messages(rule, cur, old, own):
                n = Notification(workspace_id=ws.id, feed_id=feed.id, run_id=run.id, kind=rule.kind,
                                 text=f"{where}: {text}", emailed=not rule.email)
                session.add(n)
                created.append(n)
    session.commit()
    return created


def _messages(rule: AlertRule, cur: dict, old: dict, own: set[str]) -> list[str]:
    out = []
    if rule.kind == "own_drop":
        for name in set(cur) | set(old):
            if name.lower() in own:
                before = old[name].sov_total if name in old else 0.0
                now = cur[name].sov_total if name in cur else 0.0
                if before - now >= rule.threshold:
                    out.append(f"{name} scende da {_pct(before)} a {_pct(now)} "
                               f"(−{(before - now) * 100:.1f} punti)".replace(".", ","))
    elif rule.kind == "own_rank_lost":
        for name, b in cur.items():
            if name.lower() in own and name in old and b.rank and old[name].rank and b.rank > old[name].rank:
                out.append(f"{name} passa dalla posizione {old[name].rank} alla {b.rank}")
    elif rule.kind == "competitor_top3":
        for name, b in cur.items():
            was = old.get(name)
            if name.lower() not in own and b.rank and b.rank <= 3 and (was is None or not was.rank or was.rank > 3):
                out.append(f"{name} entra al {b.rank}° posto ({_pct(b.sov_total)})")
    elif rule.kind == "new_top10":
        for name, b in cur.items():
            if b.rank and b.rank <= 10 and name not in old:
                out.append(f"nuovo marchio {name} al {b.rank}° posto ({_pct(b.sov_total)})")
    return out


def send_pending_emails(session: Session, settings) -> int:
    """Una email riassuntiva per cliente con gli avvisi non ancora inviati. Senza SMTP non fa nulla."""
    if not settings.smtp_host or not settings.mail_from:
        return 0
    pending = session.scalars(select(Notification).where(Notification.emailed.is_(False))
                              .order_by(Notification.created_at)).all()
    by_ws: dict[int, list[Notification]] = defaultdict(list)
    for n in pending:
        by_ws[n.workspace_id].append(n)
    sent = 0
    for ws_id, items in by_ws.items():
        ws = session.get(Workspace, ws_id)
        recipients = [u.email for u in ws.users]
        if not recipients:
            continue
        msg = EmailMessage()
        msg["Subject"] = f"Share of voice: {len(items)} {'novità' if len(items) > 1 else 'novità'} da controllare"
        msg["From"] = settings.mail_from
        msg["To"] = ", ".join(recipients)
        lines = [f"• {n.text}" for n in items]
        msg.set_content("\n".join(lines) + f"\n\nApri la dashboard: {settings.base_url}/dashboard\n"
                        f"Gestisci gli avvisi: {settings.base_url}/avvisi\n")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException):
            log.exception("Invio email non riuscito per il cliente %s", ws_id)
            continue
        for n in items:
            n.emailed = True
        sent += 1
    session.commit()
    return sent
