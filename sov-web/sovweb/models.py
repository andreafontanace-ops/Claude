"""Tabelle del servizio.

I dati di mercato sono condivisi: un Feed è una coppia categoria × sito, raccolta una volta sola
per tutti i clienti che la seguono (Subscription). Ogni cliente ha il suo Workspace, con utenti,
piano e i propri marchi/concorrenti per categoria.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    plan: Mapped[str] = mapped_column(String(30), default="prova")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    api_token: Mapped[str] = mapped_column(String(64), default=lambda: secrets.token_urlsafe(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    users: Mapped[list[User]] = relationship(back_populates="workspace")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    brands: Mapped[list[WorkspaceBrand]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(300))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    workspace: Mapped[Workspace] = relationship(back_populates="users")


class Category(Base):
    """Categoria di prodotto con keyword, regole di pertinenza e formulazioni (formato config di amazon-sov)."""

    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    config: Mapped[dict] = mapped_column(JSON)
    # marchi inventati usati solo dai dati dimostrativi
    demo_brands: Mapped[list] = mapped_column(JSON, default=list)


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), default="marketplace")  # marketplace | farmacia | comparatore


class Feed(Base):
    """Raccolta condivisa di una categoria su un sito."""

    __tablename__ = "feeds"
    __table_args__ = (UniqueConstraint("category_id", "site_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    category: Mapped[Category] = relationship()
    site: Mapped[Site] = relationship()
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="feed")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("workspace_id", "feed_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    workspace: Mapped[Workspace] = relationship(back_populates="subscriptions")
    feed: Mapped[Feed] = relationship(back_populates="subscriptions")


class WorkspaceBrand(Base):
    """Marchi del cliente ("own") e concorrenti da tenere d'occhio ("competitor"), per categoria."""

    __tablename__ = "workspace_brands"
    __table_args__ = (UniqueConstraint("workspace_id", "category_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))  # own | competitor
    workspace: Mapped[Workspace] = relationship(back_populates="brands")


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | ok | error
    source: Mapped[str] = mapped_column(String(40))  # demo | ingest | <fornitore>
    error: Mapped[str] = mapped_column(String(1000), default="")
    keywords_scored: Mapped[int] = mapped_column(Integer, default=0)
    sponsored_slot_share: Mapped[float] = mapped_column(Float, default=0.0)
    feed: Mapped[Feed] = relationship()


class SerpResult(Base):
    """Un risultato di ricerca grezzo (stessi campi di amazon_sov.pipeline.SerpRow)."""

    __tablename__ = "serp_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    keyword: Mapped[str] = mapped_column(String(200))
    page: Mapped[int] = mapped_column(Integer)
    slot: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organic_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(600))
    brand_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sponsored: Mapped[bool] = mapped_column(Boolean)
    placement: Mapped[str] = mapped_column(String(20))
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BrandSov(Base):
    """Share of voice per marchio in un'esecuzione: precalcolata per una dashboard veloce."""

    __tablename__ = "brand_sov"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    brand: Mapped[str] = mapped_column(String(200))
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # vuoto per «non pertinenti», «senza marchio»…
    sov_total: Mapped[float] = mapped_column(Float)
    sov_organic: Mapped[float] = mapped_column(Float)
    sov_paid: Mapped[float] = mapped_column(Float)
    ads_share: Mapped[float] = mapped_column(Float)
    shelf_top10: Mapped[float] = mapped_column(Float)
    n_products: Mapped[int] = mapped_column(Integer)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ProductSov(Base):
    __tablename__ = "product_sov"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(600))
    brand: Mapped[str] = mapped_column(String(200))
    form: Mapped[str | None] = mapped_column(String(80), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(120), nullable=True)  # es. tipo di ferro
    sov_total: Mapped[float] = mapped_column(Float)
    sov_organic: Mapped[float] = mapped_column(Float)
    best_organic_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AlertRule(Base):
    """Regola di avviso scelta dal cliente.

    kind: own_drop (un mio marchio perde almeno `threshold` punti), competitor_top3 (un concorrente entra
    nei primi 3), new_top10 (un marchio mai visto entra nei primi 10), own_rank_lost (un mio marchio scende
    di posizione).
    """

    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    threshold: Mapped[float] = mapped_column(Float, default=0.02)
    email: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    feed_id: Mapped[int | None] = mapped_column(ForeignKey("feeds.id"), nullable=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    emailed: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEvent(Base):
    """Registro degli eventi di sicurezza: accessi riusciti e falliti, cambi password, azioni da amministratore."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), default="")
    kind: Mapped[str] = mapped_column(String(40))
    ip: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(String(300), default="")
