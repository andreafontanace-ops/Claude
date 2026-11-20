import re

import pytest
from fastapi.testclient import TestClient

from conftest import csrf, signup
from sovweb.app import create_app
from sovweb.mailer import OUTBOX
from sovweb.settings import Settings


def last_link(path):
    body = OUTBOX[-1]["body"]
    return re.search(rf"http://localhost:8000({path}\?t=\S+)", body).group(1)


def test_security_headers(client):
    r = client.get("/")
    h = r.headers
    assert "script-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "no-store"
    assert "strict-transport-security" not in h  # solo online
    assert "<script>" not in client.get("/registrati").text  # nessuno script in linea


def test_login_is_rate_limited(client):
    signup(client)
    client.post("/esci", data={"csrf": csrf(client, "/dashboard")})
    token = csrf(client, "/accedi")
    for _ in range(8):
        r = client.post("/accedi", data={"csrf": token, "email": "anna@example.com", "password": "sbagliata!!"})
        assert r.status_code == 200
    r = client.post("/accedi", data={"csrf": token, "email": "anna@example.com", "password": "password-lunga-1"})
    assert r.status_code == 429 and "Troppi tentativi" in r.text


def test_password_reset_flow_and_sessions_closed(app):
    a, other = TestClient(app), TestClient(app)
    signup(a)
    token = csrf(other, "/accedi")
    other.post("/accedi", data={"csrf": token, "email": "anna@example.com", "password": "password-lunga-1"})
    assert other.get("/dashboard", follow_redirects=False).status_code in (200, 303)

    anon = TestClient(app)
    t = csrf(anon, "/password-dimenticata")
    r = anon.post("/password-dimenticata", data={"csrf": t, "email": "nessuno@example.com"})
    assert "Se l'indirizzo è registrato" in r.text  # stessa risposta, nessuna email
    n = len(OUTBOX)
    r = anon.post("/password-dimenticata", data={"csrf": t, "email": "anna@example.com"})
    assert "Se l'indirizzo è registrato" in r.text and len(OUTBOX) == n + 1
    link = last_link("/reimposta")

    page = anon.get(link).text
    assert "Scegli una nuova password" in page and 'name="password2"' in page
    token = re.search(r'name="t" value="([^"]+)"', page).group(1)
    bad = anon.post("/reimposta", data={"csrf": t, "t": token, "password": "nuova-password-1", "password2": "diversa-1234"})
    assert "non coincidono" in bad.text
    ok = anon.post("/reimposta", data={"csrf": t, "t": token, "password": "nuova-password-1", "password2": "nuova-password-1"})
    assert ok.url.path in ("/dashboard", "/benvenuto")
    assert "già stato usato" in anon.get(link).text  # monouso

    # le sessioni aperte prima del cambio password sono chiuse
    assert other.get("/dashboard", follow_redirects=False).headers["location"] == "/accedi"
    assert a.get("/dashboard", follow_redirects=False).headers["location"] == "/accedi"


def test_email_verification(client):
    signup(client)
    assert "Conferma il tuo indirizzo email" in client.get("/benvenuto").text
    link = last_link("/verifica")
    assert "Email confermata" in client.get(link).text
    assert "Conferma il tuo indirizzo email" not in client.get("/benvenuto").text
    assert "Link non valido" in client.get("/verifica?t=falso").text


@pytest.mark.parametrize("kwargs, message", [
    ({"environment": "staging", "secret_key": "corta"}, "SOV_SECRET_KEY"),
    ({"environment": "staging", "secret_key": "x" * 40, "database_url": "sqlite:///a.sqlite"}, "Postgres"),
    ({"environment": "production", "secret_key": "x" * 40, "database_url": "postgresql://u@h/db",
      "data_provider": "demo"}, "dimostrativi"),
    ({"environment": "dev", "ingest_token": "breve"}, "SOV_INGEST_TOKEN"),
    ({"environment": "test"}, "SOV_ENV"),
])
def test_unsafe_settings_are_refused(kwargs, message):
    with pytest.raises(RuntimeError, match=message):
        Settings(**kwargs).check()


def test_online_mode_forces_https_and_hsts(tmp_path, monkeypatch):
    # in staging serve Postgres: per il test si salta il controllo e si usa SQLite
    monkeypatch.setattr(Settings, "check", lambda self: None)
    app = create_app(Settings(environment="staging", secret_key="x" * 40,
                              database_url=f"sqlite:///{tmp_path / 's.sqlite'}"))
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/", headers={"x-forwarded-proto": "http"}, follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"].startswith("https://")
    r = c.get("/")
    assert "max-age=31536000" in r.headers["strict-transport-security"]
    assert "Ambiente di prova" in r.text
