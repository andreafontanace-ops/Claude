import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from amazon_sov.cli import main
from amazon_sov.platform import PushError, build_payload, push
from amazon_sov.storage import Store

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures"


class Receiver(BaseHTTPRequestHandler):
    received: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("Authorization") != "Bearer segreto":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"detail":"Token non valido"}')
            return
        Receiver.received.append((self.path, body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"run_id": 7, "status": "ok", "keywords": len(body["results"])}).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Receiver.received = []
    httpd = HTTPServer(("127.0.0.1", 0), Receiver)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def parsed_store(tmp_path):
    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    for name in ("integratore-ferro__p1.html", "integratore-ferro__p2.html"):
        shutil.copy(FIX / name, html_dir / name)
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data"), "--non-aprire"]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])
    return args, Store(tmp_path / "data" / "sov.sqlite")


def test_payload_keeps_order_and_resolved_brands(tmp_path):
    _, store = parsed_store(tmp_path)
    from amazon_sov.cli import _filters
    from amazon_sov.config import load_config
    from amazon_sov.pipeline import reclassify

    cfg = load_config(ROOT / "config.toml")
    run_id = store.latest_run_id()
    rows = reclassify(store.rows(run_id), *_filters(cfg, store))
    payload = build_payload(rows, "ferro", "amazon-it", "2026-11-20T10:30:00")
    items = payload["results"]["integratore ferro"]
    assert [i["id"] for i in items[:3]] == ["B07SIDERAL", "B08NUTRAV1", "B000SOLGAR"]
    assert len(items) == 11  # niente widget, pagine 1 e 2 in fila
    assert items[0]["brand"] == "Sideral" and items[0]["sponsored"] is True and items[0]["price"] == 19.9
    assert next(i for i in items if i["id"] == "B000SOLGAR")["brand"] == "Solgar"  # dall'alias nel titolo
    assert next(i for i in items if i["id"] == "B0GENERIC1")["brand"] is None  # da verificare: decide la piattaforma
    assert payload["collected_at"].startswith("2026-11-20T10:30:00") and len(payload["collected_at"]) > 19


def test_push_command(tmp_path, server, monkeypatch):
    args, store = parsed_store(tmp_path)
    monkeypatch.setenv("AMAZON_SOV_TOKEN", "segreto")
    main(args + ["push", "--url", server])
    path, body = Receiver.received[0]
    assert path == "/api/ingest" and body["category"] == "ferro" and body["site"] == "amazon-it"
    assert set(body["results"]) == {"integratore ferro"}


def test_push_errors_are_clear(tmp_path, server, monkeypatch):
    args, _ = parsed_store(tmp_path)
    monkeypatch.delenv("AMAZON_SOV_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="AMAZON_SOV_TOKEN"):
        main(args + ["push", "--url", server])
    with pytest.raises(PushError, match="401"):
        push(server, "sbagliato", {"results": {}})
    with pytest.raises(PushError, match="non raggiungibile"):
        push("http://127.0.0.1:9", "x", {"results": {}})
    with pytest.raises(SystemExit, match="url"):
        monkeypatch.setenv("AMAZON_SOV_TOKEN", "segreto")
        main(args + ["push"])  # url vuoto in config.toml
