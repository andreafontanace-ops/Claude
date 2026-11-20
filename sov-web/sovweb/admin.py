"""Comandi di amministrazione: `python -m sovweb.admin ...`

  crea-admin EMAIL            crea (o promuove) l'account amministratore, con accesso completo
  spazio NOME EMAIL [PIANO]   crea uno spazio cliente con il suo primo utente (piano default: gratuito)
  piano EMAIL PIANO           cambia il piano dello spazio di cui fa parte EMAIL
  elenco                      elenca gli spazi
  init                        crea o aggiorna le tabelle e il catalogo (prima di ogni pubblicazione)
"""

from __future__ import annotations

import getpass
import secrets
import sys

from sqlalchemy import select

from .alerts import add_default_rules
from .catalog import seed_catalog
from .db import Database
from .models import User, Workspace
from .plans import PLANS
from .security import hash_password
from .settings import Settings


def create_workspace(session, name: str, email: str, plan: str, password: str | None = None,
                     admin: bool = False) -> tuple[User, str]:
    """Crea spazio + primo utente. Restituisce l'utente e la password (generata se non indicata)."""
    if plan not in PLANS:
        raise ValueError(f"Piano sconosciuto: {plan}. Disponibili: {', '.join(PLANS)}")
    email = email.strip().lower()
    if session.scalar(select(User).where(User.email == email)):
        raise ValueError(f"Esiste già un utente {email}")
    password = password or secrets.token_urlsafe(12)
    ws = Workspace(name=name.strip(), plan=plan)
    user = User(email=email, name="", password_hash=hash_password(password), workspace=ws, is_admin=admin,
                email_verified=admin)
    session.add_all([ws, user])
    session.flush()
    session.add_all(add_default_rules(ws))
    session.commit()
    return user, password


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return
    settings = Settings()
    db = Database(settings.database_url)
    db.create_all()
    with db.Session() as s:
        seed_catalog(s)
        cmd, args = argv[0], argv[1:]
        if cmd == "init":
            print("Database pronto.")
        elif cmd == "crea-admin" and len(args) == 1:
            email = args[0].strip().lower()
            user = s.scalar(select(User).where(User.email == email))
            if user:
                user.is_admin = True
                user.email_verified = True
                user.workspace.plan = "gratuito"
                s.commit()
                print(f"{email} ora è amministratore, con accesso completo.")
                return
            password = getpass.getpass("Password per l'amministratore (almeno 10 caratteri): ")
            if len(password) < 10:
                sys.exit("Password troppo corta.")
            create_workspace(s, "Amministrazione", email, "gratuito", password, admin=True)
            print(f"Creato l'amministratore {email}. Accedi su /accedi.")
        elif cmd == "spazio" and len(args) in (2, 3):
            name, email = args[0], args[1]
            plan = args[2] if len(args) == 3 else "gratuito"
            try:
                user, password = create_workspace(s, name, email, plan)
            except ValueError as exc:
                sys.exit(str(exc))
            print(f"Creato lo spazio «{name}» (piano {PLANS[plan].name}).\n"
                  f"Accesso: {user.email} · password temporanea: {password}")
        elif cmd == "piano" and len(args) == 2:
            user = s.scalar(select(User).where(User.email == args[0].strip().lower()))
            if user is None or args[1] not in PLANS:
                sys.exit("Utente o piano sconosciuto.")
            user.workspace.plan = args[1]
            s.commit()
            print(f"Spazio «{user.workspace.name}»: piano {PLANS[args[1]].name}.")
        elif cmd == "elenco":
            for ws in s.scalars(select(Workspace).order_by(Workspace.id)):
                print(f"{ws.id:>4}  {ws.name:<30} {ws.plan:<10} {len(ws.users)} utenti  {len(ws.subscriptions)} feed")
        else:
            print(__doc__)


if __name__ == "__main__":
    main()
