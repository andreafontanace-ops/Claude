import re
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import choose, csrf, signup
from sovweb.admin import main as admin_cli
from sovweb.db import Database
from sovweb.models import User, Workspace


def login(client, email, password):
    token = csrf(client, "/accedi")
    return client.post("/accedi", data={"csrf": token, "email": email, "password": password})


def test_admin_cli_and_free_full_access(app, settings, monkeypatch, capsys):
    monkeypatch.setenv("SOV_DATABASE_URL", settings.database_url)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "password-admin-1")
    admin_cli(["crea-admin", "admin@example.com"])
    admin_cli(["spazio", "Alfasigma", "test@alfasigma.example"])
    out = capsys.readouterr().out
    password = re.search(r"password temporanea: (\S+)", out).group(1)

    with Database(settings.database_url).Session() as s:
        ws = s.scalar(select(Workspace).where(Workspace.name == "Alfasigma"))
        assert ws.plan == "gratuito" and ws.trial_ends_at is None

    client = TestClient(app)
    login(client, "test@alfasigma.example", password)
    r = choose(client, ["Ferro", "Magnesio", "Omega 3", "Probiotici", "Vitamina D"],
               ["Amazon.it", "Dr. Max", "Farmacosmo", "eFarma", "1000Farmacie", "TopFarmacia", "Google Shopping"])
    assert "Quali marchi vuoi evidenziare?" in r.text  # nessun limite
    assert client.get("/admin").status_code == 404  # non è amministratore

    admin = TestClient(app)
    login(admin, "admin@example.com", "password-admin-1")
    page = admin.get("/admin").text
    assert "Alfasigma" in page and "Amministrazione" in admin.get("/dashboard", follow_redirects=True).text


def test_admin_web_creates_space_and_changes_plan(app, settings, monkeypatch):
    monkeypatch.setenv("SOV_DATABASE_URL", settings.database_url)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "password-admin-1")
    admin_cli(["crea-admin", "admin@example.com"])
    admin = TestClient(app)
    login(admin, "admin@example.com", "password-admin-1")
    token = csrf(admin, "/admin")
    page = admin.post("/admin/spazio", data={"csrf": token, "name": "Cliente Uno", "email": "uno@example.com",
                                             "plan": "gratuito"}).text
    assert "Spazio «Cliente Uno» creato" in page and "password temporanea" in page
    assert "password temporanea" not in admin.get("/admin").text  # mostrata una volta sola
    with Database(settings.database_url).Session() as s:
        ws_id = s.scalar(select(Workspace.id).where(Workspace.name == "Cliente Uno"))
    admin.post(f"/admin/spazio/{ws_id}/piano", data={"csrf": token, "plan": "pro"})
    with Database(settings.database_url).Session() as s:
        assert s.get(Workspace, ws_id).plan == "pro"
    dup = admin.post("/admin/spazio", data={"csrf": token, "name": "X", "email": "uno@example.com"}).text
    assert "Esiste già un utente" in dup


def test_free_plan_not_on_pricing_page(client):
    assert "Gratuito – accesso completo" not in client.get("/prezzi").text


def test_old_database_gets_new_columns(tmp_path):
    path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, name TEXT, password_hash TEXT, "
                 "workspace_id INTEGER, created_at TEXT)")
    conn.execute("INSERT INTO users (email, name, password_hash, workspace_id) VALUES ('a@b.it', '', 'x', 1)")
    conn.commit()
    conn.close()
    db = Database(f"sqlite:///{path}")
    db.create_all()
    with db.Session() as s:
        assert s.scalar(select(User)).is_admin is False
