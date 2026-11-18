"""Archivio SQLite: esecuzioni, pagine scaricate, righe SERP, marchi letti dalle pagine prodotto."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import astuple, fields
from datetime import datetime
from pathlib import Path

from .pipeline import SerpRow

_ROW_FIELDS = [f.name for f in fields(SerpRow)]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    source TEXT NOT NULL,
    domain TEXT,
    keywords TEXT
);
CREATE TABLE IF NOT EXISTS pages (
    run_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    page INTEGER NOT NULL,
    status TEXT NOT NULL,
    n_results INTEGER,
    html_path TEXT,
    fetched_at TEXT,
    PRIMARY KEY (run_id, keyword, page)
);
CREATE TABLE IF NOT EXISTS serp (
    run_id TEXT NOT NULL,
    {", ".join(_ROW_FIELDS)}
);
CREATE INDEX IF NOT EXISTS serp_run ON serp(run_id, keyword);
CREATE TABLE IF NOT EXISTS product_brands (
    asin TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    updated_at TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # -- esecuzioni
    def create_run(self, source: str, domain: str, keywords: list[str]) -> str:
        """Registra una nuova esecuzione e restituisce il suo ID (data-ora, con suffisso se già usato)."""
        base = run_id = new_run_id()
        n = 1
        while self.conn.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
            n += 1
            run_id = f"{base}-{n}"
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs(run_id, started_at, source, domain, keywords) VALUES (?, ?, ?, ?, ?)",
                (run_id, now(), source, domain, json.dumps(keywords, ensure_ascii=False)),
            )
        return run_id

    def finish_run(self, run_id: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE runs SET finished_at = ? WHERE run_id = ?", (now(), run_id))

    def runs(self) -> list[dict]:
        cur = self.conn.execute(
            """SELECT r.*, (SELECT COUNT(*) FROM serp s WHERE s.run_id = r.run_id) AS n_rows,
                      (SELECT COUNT(*) FROM pages p WHERE p.run_id = r.run_id AND p.status != 'ok') AS n_failed
               FROM runs r ORDER BY r.started_at DESC, r.run_id DESC"""
        )
        return [dict(r) for r in cur]

    def latest_run_id(self) -> str | None:
        for run in self.runs():
            if run["n_rows"]:
                return run["run_id"]
        return None

    def previous_run_id(self, run_id: str) -> str | None:
        runs = [r for r in self.runs() if r["n_rows"]]
        ids = [r["run_id"] for r in runs]
        if run_id not in ids:
            return None
        idx = ids.index(run_id)
        return ids[idx + 1] if idx + 1 < len(ids) else None

    def run_info(self, run_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    # -- pagine
    def log_page(self, run_id: str, keyword: str, page: int, status: str, n_results: int, html_path: str | None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO pages VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, keyword, page, status, n_results, html_path, now()),
            )

    def pages(self, run_id: str) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM pages WHERE run_id = ? ORDER BY keyword, page", (run_id,))
        return [dict(r) for r in cur]

    # -- righe SERP
    def replace_rows(self, run_id: str, keyword: str, rows: list[SerpRow]) -> None:
        placeholders = ", ".join("?" for _ in range(len(_ROW_FIELDS) + 1))
        with self.conn:
            self.conn.execute("DELETE FROM serp WHERE run_id = ? AND keyword = ?", (run_id, keyword))
            self.conn.executemany(
                f"INSERT INTO serp(run_id, {', '.join(_ROW_FIELDS)}) VALUES ({placeholders})",
                [(run_id, *astuple(r)) for r in rows],
            )

    def rows(self, run_id: str) -> list[SerpRow]:
        cur = self.conn.execute(
            f"SELECT {', '.join(_ROW_FIELDS)} FROM serp WHERE run_id = ? ORDER BY keyword, rank IS NULL, rank, page, slot",
            (run_id,),
        )
        out = []
        for r in cur:
            d = dict(r)
            d["sponsored"] = bool(d["sponsored"])
            d["relevant"] = bool(d["relevant"])
            out.append(SerpRow(**d))
        return out

    # -- marchi dalle pagine prodotto
    def product_brands(self) -> dict[str, str]:
        return {r["asin"]: r["brand"] for r in self.conn.execute("SELECT asin, brand FROM product_brands")}

    def set_product_brand(self, asin: str, brand: str) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO product_brands VALUES (?, ?, ?)", (asin, brand, now()))
