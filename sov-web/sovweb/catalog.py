"""Catalogo iniziale di categorie e siti.

La configurazione di ogni categoria ha lo stesso formato di config.toml di amazon-sov (keyword,
pertinenza, alias dei marchi, formulazioni), così il calcolo della share of voice è lo stesso.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category, Site

AMAZON_SOV_CONFIG = Path(__file__).resolve().parents[2] / "amazon-sov" / "config.toml"


def _kw(*terms: str) -> list[dict]:
    return [{"term": t, "weight": 1.0} for t in terms]


def _ferro_config() -> dict:
    if AMAZON_SOV_CONFIG.exists():
        with open(AMAZON_SOV_CONFIG, "rb") as fh:
            return tomllib.load(fh)
    return {"keywords": _kw("integratore ferro", "ferritina", "ferro bisglicinato"),
            "relevance": {"include": ["ferro", "ferritina", "iron"], "exclude": ["senza ferro"]}}


CATEGORIES = [
    {
        "slug": "ferro",
        "name": "Ferro",
        "description": "Integratori di ferro: bisglicinato, liposomiale, sucrosomiale, gocce per bambini…",
        "config": _ferro_config,
        "demo_brands": ["Ferralia", "Emoplus", "Sideron", "Vitaferr", "Nutrisan", "Bioferro Lab", "Gocce d'Oro"],
    },
    {
        "slug": "magnesio",
        "name": "Magnesio",
        "description": "Magnesio e potassio, magnesio citrato, bisglicinato, pidolato.",
        "config": lambda: {
            "keywords": _kw("integratore magnesio", "magnesio", "magnesio e potassio", "magnesio citrato",
                            "magnesio bisglicinato", "magnesio supremo", "magnesio pidolato", "magnesio stanchezza"),
            "relevance": {"include": ["magnesio", "magnesium", "potassio"], "exclude": ["senza magnesio"]},
            "formulation": {"iron_types": {
                "Citrato": ["citrat"], "Bisglicinato": ["bisglicinat", "bisglycinat"], "Pidolato": ["pidolat"],
                "Ossido": ["ossido", "oxide"], "Carbonato": ["carbonat"], "Cloruro": ["clorur", "chlorid"],
                "Treonato": ["treonat", "threonat"], "Con potassio": ["potassio"],
            }},
        },
        "demo_brands": ["Magnesia Pura", "Vitalmag", "Energen", "Mag+K", "NovaFarma", "Bios Lab"],
    },
    {
        "slug": "vitamina-d",
        "name": "Vitamina D",
        "description": "Vitamina D3, D3 + K2, gocce e compresse ad alto dosaggio.",
        "config": lambda: {
            "keywords": _kw("vitamina d", "vitamina d3", "vitamina d3 k2", "vitamina d gocce", "colecalciferolo",
                            "vitamina d3 2000 ui", "vitamina d bambini"),
            "relevance": {"include": ["vitamina d", "vitamina d3", "vitamin d", "colecalciferolo", "d3"],
                          "exclude": []},
            "formulation": {"iron_types": {"Con K2": ["k2", "menachinone"], "Vegana (licheni)": ["lichen"],
                                           "Olio": ["olio", "oil"]}},
        },
        "demo_brands": ["SolD", "D-Vital", "Heliovit", "NovaFarma", "Bios Lab", "Gocce d'Oro"],
    },
    {
        "slug": "omega-3",
        "name": "Omega 3",
        "description": "Olio di pesce, omega 3 alto dosaggio, krill, alga.",
        "config": lambda: {
            "keywords": _kw("omega 3", "omega 3 integratore", "olio di pesce", "omega 3 alto dosaggio", "krill oil",
                            "omega 3 vegano", "epa dha"),
            "relevance": {"include": ["omega 3", "omega", "epa", "dha", "olio di pesce", "krill", "fish oil"],
                          "exclude": []},
            "formulation": {"iron_types": {"Krill": ["krill"], "Alga": ["alga", "algae"],
                                           "Olio di pesce": ["pesce", "fish"]}},
        },
        "demo_brands": ["Marinus", "OmegaPura", "Krillis", "Bios Lab", "NovaFarma", "Vitalia"],
    },
    {
        "slug": "probiotici",
        "name": "Probiotici",
        "description": "Fermenti lattici e probiotici per adulti e bambini.",
        "config": lambda: {
            "keywords": _kw("probiotici", "fermenti lattici", "fermenti lattici bambini", "probiotici intestino",
                            "lactobacillus", "probiotici donna"),
            "relevance": {"include": ["probiotic", "fermenti", "lactobacillus", "bifidobacter", "lattici"],
                          "exclude": []},
            "formulation": {"iron_types": {"Bambini": ["bambin"], "Donna": ["donna", "intim"],
                                           "Miliardi UFC": ["miliardi", "ufc"]}},
        },
        "demo_brands": ["Florabiota", "Lactovis", "Enteris", "Vitalia", "Bios Lab", "NovaFarma"],
    },
]

SITES = [
    {"slug": "amazon-it", "name": "Amazon.it", "domain": "www.amazon.it", "kind": "marketplace"},
    {"slug": "drmax", "name": "Dr. Max", "domain": "www.drmax.it", "kind": "farmacia"},
    {"slug": "farmacosmo", "name": "Farmacosmo", "domain": "www.farmacosmo.it", "kind": "farmacia"},
    {"slug": "efarma", "name": "eFarma", "domain": "www.efarma.com", "kind": "farmacia"},
    {"slug": "1000farmacie", "name": "1000Farmacie", "domain": "www.1000farmacie.it", "kind": "farmacia"},
    {"slug": "topfarmacia", "name": "TopFarmacia", "domain": "www.topfarmacia.it", "kind": "farmacia"},
    {"slug": "google-shopping", "name": "Google Shopping", "domain": "shopping.google.it", "kind": "comparatore"},
]


def seed_catalog(session: Session) -> None:
    """Crea le categorie e i siti mancanti (non tocca quelli già presenti)."""
    have_cat = {c.slug for c in session.scalars(select(Category))}
    for c in CATEGORIES:
        if c["slug"] not in have_cat:
            session.add(Category(slug=c["slug"], name=c["name"], description=c["description"],
                                 config=c["config"](), demo_brands=c["demo_brands"]))
    have_site = {s.slug for s in session.scalars(select(Site))}
    for s in SITES:
        if s["slug"] not in have_site:
            session.add(Site(**s))
    session.commit()
