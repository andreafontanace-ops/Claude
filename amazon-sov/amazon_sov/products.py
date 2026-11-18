"""Formulazione (forma + tipo di ferro) e produttore di ogni prodotto."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .brands import GENERIC_BRAND, UNKNOWN_BRAND, normalize
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
    """Ordine: correzione per ASIN > marchio→produttore in config > pagina prodotto > stesso marchio > Google."""

    def __init__(self, cfg: Config, infos: dict[str, dict], web: dict[str, dict] | None = None):
        self.overrides = {k.upper(): v for k, v in cfg.manufacturer_overrides.items()}
        self.by_brand = {normalize(k): v for k, v in cfg.manufacturer_by_brand.items()}
        self.page = {a: i["manufacturer"] for a, i in infos.items() if i.get("manufacturer")}
        self.web = {k: w["manufacturer"] for k, w in (web or {}).items() if w.get("manufacturer")}
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
            if r.manufacturer is None and r.brand not in (UNKNOWN_BRAND, GENERIC_BRAND) and votes.get(r.brand):
                r.manufacturer = votes[r.brand].most_common(1)[0][0]
                r.manufacturer_source = "same_brand"
            elif r.manufacturer is None and r.brand not in (UNKNOWN_BRAND, GENERIC_BRAND) and normalize(r.brand) in self.web:
                r.manufacturer = self.display(self.web[normalize(r.brand)])
                r.manufacturer_source = "google"


def annotate_products(
    rows: list[SerpRow], cfg: Config, infos: dict[str, dict], web: dict[str, dict] | None = None
) -> list[SerpRow]:
    """Aggiunge forma, tipo di ferro e produttore (le righe devono avere già il marchio)."""
    clf = FormulationClassifier.from_config(cfg)
    for r in rows:
        info = infos.get(r.asin.upper()) or {}
        r.form = clf.form(r.title, info.get("item_form"))
        r.iron_type = clf.iron_type(r.title)
    ManufacturerResolver(cfg, infos, web).apply(rows)
    return rows


AMAZON_SOURCES = ("product_page", "same_brand", "config", "override")


def same_company(a: str, b: str) -> bool:
    """Stessa azienda anche se scritta diversamente: "PharmaNutra S.p.A." / "PHARMANUTRA GROUP"."""
    ka, kb = manufacturer_key(a), manufacturer_key(b)
    if not ka or not kb:
        return False
    return ka == kb or f" {ka} " in f" {kb} " or f" {kb} " in f" {ka} "


def verify_brands(brand_rows: list[dict], rows: list[SerpRow], web: dict[str, dict]) -> None:
    """Confronta per ogni marchio il produttore letto su Amazon con quello trovato su Google."""
    votes: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.relevant and r.manufacturer and r.manufacturer_source in AMAZON_SOURCES:
            votes[r.brand][r.manufacturer] += 1
    for b in brand_rows:
        amazon = votes[b["brand"]].most_common(1)[0][0] if votes.get(b["brand"]) else None
        w = web.get(normalize(b["brand"]))
        google = w.get("manufacturer") if w else None
        b["amazon_manufacturer"] = amazon
        b["web_manufacturer"] = google
        b["web_mentions"] = w.get("mentions") if w else None
        if amazon and google:
            b["verification"] = "confermato" if same_company(amazon, google) else "diverso"
        elif google:
            b["verification"] = "solo Google"
        elif amazon:
            b["verification"] = "solo Amazon" if w else "da cercare su Google"
        else:
            b["verification"] = "non trovato" if w else "da cercare su Google"
