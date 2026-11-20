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

    def session(self) -> Iterator[Session]:
        with self.Session() as s:
            yield s
