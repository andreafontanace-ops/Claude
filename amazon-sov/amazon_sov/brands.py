"""Normalizzazione dei marchi e filtro di pertinenza (è un integratore di ferro?)."""

from __future__ import annotations

import re
import unicodedata

from .config import Config

UNKNOWN_BRAND = "(sconosciuto)"

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'"})
_NON_WORD = re.compile(r"[^0-9a-z'%]+")
_TRADEMARKS = re.compile(r"[®™©]")


def normalize(text: str | None) -> str:
    """Minuscolo, senza accenti né punteggiatura, spazi singoli."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text.translate(_APOSTROPHES))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return " ".join(_NON_WORD.sub(" ", text).split())


def contains_phrase(haystack_norm: str, phrase_norm: str) -> bool:
    """True se `phrase_norm` compare in `haystack_norm` a parole intere (entrambi già normalizzati)."""
    if not phrase_norm:
        return False
    return f" {phrase_norm} " in f" {haystack_norm} "


class RelevanceFilter:
    def __init__(self, include: list[str], exclude: list[str]):
        self.include = [n for n in (normalize(t) for t in include) if n]
        self.exclude = [n for n in (normalize(t) for t in exclude) if n]

    def __call__(self, title: str | None) -> bool:
        norm = normalize(title)
        if any(contains_phrase(norm, t) for t in self.exclude):
            return False
        return any(contains_phrase(norm, t) for t in self.include)


class BrandResolver:
    """Assegna a ogni prodotto un marchio canonico e dice da dove l'ha preso.

    Ordine: correzione manuale per ASIN > riga del marchio nella SERP > marchio letto
    dalla pagina prodotto (cache) > alias trovato nel titolo > prima parola del titolo.
    """

    def __init__(self, cfg: Config, product_page_brands: dict[str, str] | None = None):
        pairs = []
        for canonical, aliases in cfg.brand_aliases.items():
            for alias in [canonical, *aliases]:
                norm = normalize(alias)
                if norm:
                    pairs.append((norm, canonical))
        # alias più lunghi prima: "vitabiotics feroglobin" vince su "vitabiotics"
        self._aliases = sorted(set(pairs), key=lambda p: (-len(p[0]), p[0]))
        self._exact = {norm: canonical for norm, canonical in pairs}
        self._generic = {normalize(w) for w in cfg.generic_words}
        self._overrides = {k.upper(): v for k, v in cfg.asin_overrides.items()}
        self._page_brands = {k.upper(): v for k, v in (product_page_brands or {}).items()}
        self._display: dict[str, str] = {}

    def canonical(self, raw_brand: str) -> str:
        norm = normalize(raw_brand)
        if not norm:
            return UNKNOWN_BRAND
        if norm in self._exact:
            return self._exact[norm]
        for alias, canonical in self._aliases:
            if contains_phrase(norm, alias):
                return canonical
        cleaned = " ".join(_TRADEMARKS.sub("", raw_brand).split())
        # stesse lettere, maiuscole diverse ("SIDERAL" / "Sideral") -> un solo nome
        return self._display.setdefault(norm, cleaned)

    def resolve(self, asin: str, raw_brand: str | None, title: str | None) -> tuple[str, str]:
        asin = (asin or "").upper()
        if asin in self._overrides:
            return self._overrides[asin], "override"
        if raw_brand and normalize(raw_brand):
            return self.canonical(raw_brand), "serp"
        if asin in self._page_brands:
            return self.canonical(self._page_brands[asin]), "product_page"
        title_norm = normalize(title)
        for alias, canonical in self._aliases:
            if contains_phrase(title_norm, alias):
                return canonical, "alias"
        guess = self._guess_from_title(title)
        if guess:
            return self.canonical(guess), "title_guess"
        return UNKNOWN_BRAND, "unknown"

    def _guess_from_title(self, title: str | None) -> str | None:
        tokens = _TRADEMARKS.sub("", title or "").split()
        if not tokens:
            return None
        first = tokens[0].strip(" ,;:-|()[]\"")
        norm = normalize(first)
        if len(norm) < 2 or norm in self._generic or not re.search(r"[a-z]", norm):
            return None
        return first
