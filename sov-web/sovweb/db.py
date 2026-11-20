"""Connessione al database (SQLite in sviluppo, Postgres in produzione)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str):
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        self.engine = create_engine(url, **kwargs)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        from . import models  # noqa: F401  (registra le tabelle)

        Base.metadata.create_all(self.engine)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """Aggiunge le colonne nuove alle tabelle già esistenti (database creati da versioni precedenti)."""
        from sqlalchemy import inspect, text

        insp = inspect(self.engine)
        with self.engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                if not insp.has_table(table.name):
                    continue
                have = {c["name"] for c in insp.get_columns(table.name)}
                for col in table.columns:
                    if col.name not in have:
                        ddl = col.type.compile(dialect=self.engine.dialect)
                        default = col.default.arg if col.default is not None and not callable(col.default.arg) else None
                        extra = f" DEFAULT {int(default) if isinstance(default, bool) else repr(default)}" if default is not None else ""
                        conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}{extra}'))

    def session(self) -> Iterator[Session]:
        with self.Session() as s:
            yield s
