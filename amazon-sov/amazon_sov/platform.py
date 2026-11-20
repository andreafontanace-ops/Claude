"""Invio dei risultati di un'esecuzione alla piattaforma web (sov-web, API /api/ingest)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .brands import GENERIC_BRAND, UNKNOWN_BRAND
from .pipeline import SerpRow

TOKEN_ENV = "AMAZON_SOV_TOKEN"


class PushError(RuntimeError):
    pass


def build_payload(rows: list[SerpRow], category: str, site: str, collected_at: str | None) -> dict:
    """Risultati per keyword, nell'ordine della pagina, con il marchio già risolto (pagine prodotto incluse)."""
    results: dict[str, list[dict]] = {}
    for r in sorted((r for r in rows if r.placement != "widget" and r.rank), key=lambda r: (r.keyword, r.rank)):
        if r.brand == UNKNOWN_BRAND:
            brand = None  # la piattaforma proverà dal titolo
        elif r.brand == GENERIC_BRAND:
            brand = "Generico"
        else:
            brand = r.brand
        results.setdefault(r.keyword, []).append({
            "id": r.asin, "title": r.title, "brand": brand, "sponsored": r.sponsored,
            "price": r.price, "rating": r.rating, "reviews": r.reviews,
        })
    payload = {"category": category, "site": site, "results": results}
    if collected_at:
        # ora locale del computer, con il fuso orario: la piattaforma la converte
        payload["collected_at"] = datetime.fromisoformat(collected_at).astimezone().isoformat()
    return payload


def push(url: str, token: str, payload: dict) -> dict:
    if not url:
        raise PushError("Indirizzo della piattaforma mancante: imposta [platform] url in config.toml")
    if not token:
        raise PushError(f"Token mancante: impostalo nella variabile d'ambiente {TOKEN_ENV}")
    endpoint = url.rstrip("/") + "/api/ingest"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if endpoint.startswith("https://") and shutil.which("curl"):
        return _push_curl(endpoint, token, body)  # curl usa i certificati del sistema (Mac)
    req = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise PushError(f"La piattaforma ha risposto {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.URLError as exc:
        raise PushError(f"Piattaforma non raggiungibile ({endpoint}): {exc.reason}")


def _push_curl(endpoint: str, token: str, body: bytes) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "payload.json"
        data.write_bytes(body)
        headers = Path(tmp) / "headers.txt"  # il token non compare tra gli argomenti del processo
        headers.write_text(f"Content-Type: application/json\nAuthorization: Bearer {token}\n")
        out = subprocess.run(
            ["curl", "-sS", "-X", "POST", endpoint, "-H", f"@{headers}", "--data-binary", f"@{data}",
             "-w", "\n%{http_code}"],
            capture_output=True, text=True,
        )
    if out.returncode != 0:
        raise PushError(f"Piattaforma non raggiungibile ({endpoint}): {out.stderr.strip()}")
    text, _, code = out.stdout.rpartition("\n")
    if not code.startswith("2"):
        raise PushError(f"La piattaforma ha risposto {code}: {text[:300]}")
    return json.loads(text)


def token_from_env() -> str:
    return os.environ.get(TOKEN_ENV, "").strip()
