"""Formulazione (forma + tipo di ferro) e produttore di ogni prodotto."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .brands import UNKNOWN_BRAND, normalize
from .config import Config
from .pipeline import SerpRow

_LEGAL = re.compile(
    r"(?:\s+(?:s ?p ?a|s ?r ?l ?s?|s ?a ?s|s ?n ?c|s ?a|ltd|limited|gmbh|inc|llc|b ?v|ag|co|kg|plc|sl|sarl|srls|"
    r"societa|societa per azioni|a socio unico|unipersonale|& co))+$"
)
_ML = re.compile(r"\d\s*ml\b")


def _pattern(terms: list[str]) -> re.Pattern | None:
    parts = [re.escape(normalize(t)) for t in terms if normalize(t)]
    if not parts:
        return None
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + ")")


class FormulationClassifier:
    def __init__(self, forms: dict[str, list[str]], iron_types: dict[str, list[str]]):
        self.forms = [(label, p) for label, terms in forms.items() if (p := _pattern(terms))]
        self.iron_types = [(label, p) for label, terms in iron_types.items() if (p := _pattern(terms))]

    @classmethod
    def from_config(cls, cfg: Config) -> "FormulationClassifier":
        return cls(cfg.forms, cfg.iron_types)

    def form(self, title: str | None, item_form: str | None = None) -> str | None:
        for text in (title, item_form):
            norm = normalize(text)
            for label, pattern in self.forms:
                if pattern.search(norm):
                    return label
        if _ML.search(normalize(title)):
            return "Liquido/sciroppo"
        return None

    def iron_type(self, title: str | None) -> str | None:
        norm = normalize(title)
        found = [label for label, pattern in self.iron_types if pattern.search(norm)]
        if "Chelato" in found and len(found) > 1:
            found.remove("Chelato")  # "chelato" descrive già il bisglicinato & co.
        return " + ".join(found[:2]) or None


def manufacturer_key(name: str) -> str:
    """Chiave per riconoscere lo stesso produttore scritto in modi diversi (S.p.A., SPA, Srl…)."""
    return _LEGAL.sub("", normalize(name)).strip()


class ManufacturerResolver:
    """Ordine: correzione per ASIN > marchio→produttore in config > pagina prodotto > stesso marchio."""

    def __init__(self, cfg: Config, infos: dict[str, dict]):
        self.overrides = {k.upper(): v for k, v in cfg.manufacturer_overrides.items()}
        self.by_brand = {normalize(k): v for k, v in cfg.manufacturer_by_brand.items()}
        self.page = {a: i["manufacturer"] for a, i in infos.items() if i.get("manufacturer")}
        self._display: dict[str, str] = {}

    def display(self, name: str) -> str:
        cleaned = " ".join(name.split())
        return self._display.setdefault(manufacturer_key(cleaned) or normalize(cleaned), cleaned)

    def apply(self, rows: list[SerpRow]) -> None:
        votes: dict[str, Counter] = defaultdict(Counter)
        for r in rows:
            asin = r.asin.upper()
            if asin in self.overrides:
                r.manufacturer, r.manufacturer_source = self.display(self.overrides[asin]), "override"
            elif normalize(r.brand) in self.by_brand:
                r.manufacturer, r.manufacturer_source = self.display(self.by_brand[normalize(r.brand)]), "config"
            elif asin in self.page:
                r.manufacturer, r.manufacturer_source = self.display(self.page[asin]), "product_page"
                votes[r.brand][r.manufacturer] += 1
            else:
                r.manufacturer, r.manufacturer_source = None, None
        for r in rows:
            if r.manufacturer is None and r.brand != UNKNOWN_BRAND and votes.get(r.brand):
                r.manufacturer = votes[r.brand].most_common(1)[0][0]
                r.manufacturer_source = "same_brand"


def annotate_products(rows: list[SerpRow], cfg: Config, infos: dict[str, dict]) -> list[SerpRow]:
    """Aggiunge forma, tipo di ferro e produttore (le righe devono avere già il marchio)."""
    clf = FormulationClassifier.from_config(cfg)
    for r in rows:
        info = infos.get(r.asin.upper()) or {}
        r.form = clf.form(r.title, info.get("item_form"))
        r.iron_type = clf.iron_type(r.title)
    ManufacturerResolver(cfg, infos).apply(rows)
    return rows
