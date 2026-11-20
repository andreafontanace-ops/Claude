import io
import re

from openpyxl import load_workbook
from sqlalchemy import select

from conftest import choose, csrf, set_brands, signup
from sovweb.collector import run_due
from sovweb.db import Database
from sovweb.models import Feed, Run, Workspace


def db(settings):
    return Database(settings.database_url)


def test_home_and_pricing_are_public(client):
    assert "Prova gratis" in client.get("/").text
    page = client.get("/prezzi").text
    assert "129 €" in page and "449 €" in page and "Su misura" in page
    assert client.get("/salute").json() == {"ok": True}


def test_signup_onboarding_and_dashboard(client):
    page = signup(client)
    assert "Cosa vuoi seguire?" in page.text
    r = choose(client, ["Ferro"], ["Amazon.it"])
    assert "Quali marchi vuoi evidenziare?" in r.text
    assert "facoltativo" in r.text
    r = set_brands(client, own="Ferralia", competitor="Emoplus")
    assert r.url.path == "/dashboard"
    assert "Ferro · Amazon.it" in r.text and "Ferralia" in r.text and "dati dimostrativi" in r.text
    feed_link = re.search(r'href="/dashboard/(\d+)"', r.text).group(1)
    detail = client.get(f"/dashboard/{feed_link}").text
    assert "Classifica dei marchi" in detail and '<span class="tag">tuo</span>' in detail
    assert '<span class="tag">concorrente</span>' in detail
    assert "L'andamento compare dalla seconda raccolta" in detail


def test_brands_are_optional(client):
    signup(client)
    choose(client, ["Magnesio"], ["Amazon.it"])
    r = set_brands(client, skip=True)
    assert r.url.path == "/dashboard"
    assert "è primo" in r.text and "Indica i tuoi marchi" in r.text


def test_skip_keeps_existing_brands(client):
    signup(client)
    choose(client, ["Ferro"], ["Amazon.it"])
    set_brands(client, own="Ferralia")
    set_brands(client, own="", skip=True)
    assert 'value="Ferralia"' in client.get("/benvenuto/marchi").text


def test_plan_limits(client):
    signup(client)
    r = choose(client, ["Ferro", "Magnesio"], ["Amazon.it"])
    assert "comprende 1 categoria e 2 siti" in r.text
    assert "Cosa vuoi seguire?" in r.text


def test_forms_need_csrf_and_login(client):
    r = client.post("/registrati", data={"email": "x@y.it", "password": "password-lunga-1", "company": "X"})
    assert r.status_code == 400
    assert client.get("/dashboard", follow_redirects=False).headers["location"] == "/accedi"


def test_login_logout(client):
    signup(client)
    client.post("/esci", data={"csrf": csrf(client, "/dashboard")})
    token = csrf(client, "/accedi")
    bad = client.post("/accedi", data={"csrf": token, "email": "anna@example.com", "password": "sbagliata!!"})
    assert "non corretti" in bad.text
    ok = client.post("/accedi", data={"csrf": token, "email": "ANNA@example.com", "password": "password-lunga-1"})
    assert ok.url.path in ("/dashboard", "/benvenuto")


def test_workspaces_are_isolated(app, settings):
    from fastapi.testclient import TestClient

    a, b = TestClient(app), TestClient(app)
    signup(a, "a@example.com")
    choose(a, ["Ferro"], ["Amazon.it"])
    set_brands(a, own="Ferralia")
    feed_id = re.search(r'href="/dashboard/(\d+)"', a.get("/dashboard").text).group(1)
    signup(b, "b@example.com")
    choose(b, ["Omega 3"], ["Dr. Max"])
    set_brands(b, skip=True)
    assert b.get(f"/dashboard/{feed_id}").status_code == 404


def test_downloads(client, settings):
    signup(client)
    choose(client, ["Ferro"], ["Amazon.it"])
    set_brands(client, own="Ferralia")
    feed_id = re.search(r'href="/dashboard/(\d+)"', client.get("/dashboard").text).group(1)
    assert client.get(f"/dashboard/{feed_id}/scarica/xlsx").status_code == 403  # prova: niente export
    with db(settings).Session() as s:
        ws = s.scalar(select(Workspace))
        ws.plan = "base"
        s.commit()
    x = client.get(f"/dashboard/{feed_id}/scarica/xlsx")
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Marchi", "Prodotti", "Andamento", "Info"]
    assert wb["Marchi"]["B1"].value == "Marchio" and wb["Marchi"]["C2"].number_format == "0.00%"
    assert "Ferralia" in [c.value for c in wb["Marchi"]["B"]]
    c = client.get(f"/dashboard/{feed_id}/scarica/csv?tabella=prodotti")
    assert c.text.startswith("﻿Posizione;Prodotto;Marchio")
    h = client.get(f"/dashboard/{feed_id}/scarica/html")
    assert "<style>" in h.text and "Classifica dei marchi" in h.text and 'href="/static' not in h.text
    assert 'attachment; filename="sov_ferro_amazon-it_' in h.headers["content-disposition"]


def test_worker_runs_due_feeds_with_subscribers_only(client, settings):
    signup(client)
    choose(client, ["Ferro"], ["Amazon.it"])
    set_brands(client, own="Ferralia")
    from sovweb.providers import DemoProvider
    from datetime import timedelta
    from sovweb.models import utcnow

    with db(settings).Session() as s:
        feed = s.scalar(select(Feed).where(Feed.subscriptions.any()))
        assert feed.interval_minutes == 1440
        orphan = Feed(category_id=feed.category_id + 1, site_id=feed.site_id, next_run_at=utcnow())
        s.add(orphan)
        s.commit()
        assert run_due(s, DemoProvider(), utcnow()) == 0  # non ancora scaduto
        assert run_due(s, DemoProvider(), utcnow() + timedelta(days=1, minutes=1)) == 1
        assert s.scalar(select(Run).where(Run.feed_id == orphan.id)) is None


def test_feed_interval_follows_best_plan(app, settings):
    from fastapi.testclient import TestClient

    a, b = TestClient(app), TestClient(app)
    signup(a, "a@example.com")
    with db(settings).Session() as s:
        s.scalar(select(Workspace)).plan = "pro"
        s.commit()
    choose(a, ["Ferro"], ["Amazon.it"])
    signup(b, "b@example.com")
    choose(b, ["Ferro"], ["Amazon.it"])
    with db(settings).Session() as s:
        feeds = s.scalars(select(Feed)).all()
        assert len(feeds) == 1 and feeds[0].interval_minutes == 60  # dati condivisi, frequenza del piano Pro


def test_ingest_api(client):
    body = {"category": "ferro", "site": "drmax", "results": {"integratore ferro": [
        {"id": "P1", "title": "Ferralia Ferro 30 compresse", "brand": "Ferralia", "sponsored": True, "price": 9.9},
        {"id": "P2", "title": "Emoplus Ferro gocce", "brand": "Emoplus"},
    ]}}
    assert client.post("/api/ingest", json=body).status_code == 401
    r = client.post("/api/ingest", json=body, headers={"Authorization": "Bearer tok-123-prova-abcdefghijklmnop"})
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["keywords"] == 1
