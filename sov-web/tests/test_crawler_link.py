"""Collegamento crawler → piattaforma: i dati veri delle pagine Amazon passano dall'API di caricamento."""

import re
import shutil
from pathlib import Path

from sqlalchemy import select

from amazon_sov.cli import _filters, main as crawler
from amazon_sov.config import load_config
from amazon_sov.pipeline import reclassify
from amazon_sov.platform import build_payload
from amazon_sov.storage import Store
from conftest import choose, set_brands, signup
from sovweb.collector import run_due
from sovweb.db import Database
from sovweb.models import Run
from sovweb.providers import NoProvider

SOV = Path(__file__).resolve().parents[2] / "amazon-sov"


def crawler_payload(tmp_path):
    html = tmp_path / "pagine"
    html.mkdir()
    for name in ("integratore-ferro__p1.html", "integratore-ferro__p2.html"):
        shutil.copy(SOV / "tests" / "fixtures" / name, html / name)
    crawler(["-c", str(SOV / "config.toml"), "--data-dir", str(tmp_path / "data"), "--non-aprire",
             "parse", str(html), "--out", str(tmp_path / "reports")])
    store = Store(tmp_path / "data" / "sov.sqlite")
    cfg = load_config(SOV / "config.toml")
    rows = reclassify(store.rows(store.latest_run_id()), *_filters(cfg, store))
    return build_payload(rows, "ferro", "amazon-it", "2026-11-20T10:30:00")


def test_crawler_results_feed_the_dashboard(client, settings, tmp_path):
    signup(client)
    choose(client, ["Ferro"], ["Amazon.it"])
    set_brands(client, own="Nutravita")
    payload = crawler_payload(tmp_path)
    r = client.post("/api/ingest", json=payload, headers={"Authorization": "Bearer tok-123-prova-abcdefghijklmnop"})
    assert r.status_code == 200 and r.json()["status"] == "ok"
    feed_id = re.search(r'href="/dashboard/(\d+)"', client.get("/dashboard").text).group(1)
    page = client.get(f"/dashboard/{feed_id}").text
    assert "Sideral" in page and "Nutravita" in page and '<span class="tag">tuo</span>' in page
    with Database(settings.database_url).Session() as s:
        run = s.scalar(select(Run).where(Run.source == "ingest"))
        assert run.started_at.isoformat().startswith("2026-11-20")


def test_no_provider_means_no_empty_runs(client, settings):
    signup(client)
    with Database(settings.database_url).Session() as s:
        assert run_due(s, NoProvider()) == 0


def test_ingest_rejects_bad_input(client):
    h = {"Authorization": "Bearer tok-123-prova-abcdefghijklmnop"}
    assert client.post("/api/ingest", json={"category": "ferro", "site": "amazon-it", "results": {}}, headers=h).status_code == 422
    bad = {"category": "ferro", "site": "amazon-it", "collected_at": "ieri", "results": {"x": [{"id": "1"}]}}
    assert client.post("/api/ingest", json=bad, headers=h).status_code == 422
