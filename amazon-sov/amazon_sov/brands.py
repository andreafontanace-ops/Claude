"""Normalizzazione dei marchi e filtro di pertinenza (è un integratore di ferro?)."""

from __future__ import annotations

import re
import unicodedata

from .config import Config

UNKNOWN_BRAND = "(sconosciuto)"

# Parole che nei titoli degli integratori non sono mai un marchio (si aggiungono a brands.generic_words).
BUILTIN_GENERIC_WORDS = frozenset("""
ferro ferri ferroso ferrosa ferrico ferrica ferritina ferrous iron eisen fer alto alta dose forte plus extra max
puro pura bio per con senza di da del della dello e ed il lo la le gli i un una uomo donna donne uomini mese mesi
giorni set kit pack nuovo nuova cpr cps stick spray gocce goccia fiale scorta energia difese anemia formula rapido
gummies gummy vegan vegano vegana vegane vegani natural naturale naturali organic acido mg ml mcg ui zinco rame
magnesio potassio calcio selenio
""".split())
# Inizi di parola (radici lunghe): "integrator" copre integratore e integratori.
BUILTIN_GENERIC_PREFIXES = (
    "integrator", "vitamin", "multivitamin", "multiminerale", "minerali", "compless", "complex", "compress",
    "capsul", "bustin", "orosolubil", "sciropp", "liquid", "polver", "gommos", "masticabil", "flaconcin",
    "tavolett", "tablet", "pastigli", "bisglicinat", "bisglycinat", "diglicinat", "liposom", "sucrosom",
    "pirofosfat", "fumarat", "gluconat", "solfat", "chelat", "lattoferrin", "folic", "folat", "dosaggi",
    "premium", "biologic", "vegetal", "biodisponibil", "assorbibil", "gastroprotett", "delicat", "supplement",
    "alimentar", "bambin", "adult", "gravidanz", "allattament", "stanchezz", "immunitar", "confezion",
)
_JOIN_NEXT = {"dr", "dott", "doctor's", "doctors", "nature's", "natures", "the", "mr", "dottor"}
_SEGMENT = re.compile(r"\s[-–—|:]\s|[,|(\[/]")

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
        self._generic |= BUILTIN_GENERIC_WORDS
        self._overrides = {k.upper(): v for k, v in cfg.asin_overrides.items()}
        # un valore vuoto vuol dire "pagina già controllata, marchio non trovato"
        self._page_brands = {k.upper(): v for k, v in (product_page_brands or {}).items() if v}
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

    def is_generic(self, word: str) -> bool:
        norm = normalize(word)
        if len(norm) < 2 or not re.search(r"[a-z]", norm) or re.match(r"\d", norm):
            return True  # numeri, dosi ("28mg"), sigle di una lettera
        if norm in self._generic:
            return True
        return norm.startswith(BUILTIN_GENERIC_PREFIXES)

    def _guess_from_title(self, title: str | None) -> str | None:
        """Il marchio è di solito la prima o la seconda parola del titolo, prima di « - », «|» o «,»."""
        segment = _SEGMENT.split(_TRADEMARKS.sub("", title or ""), maxsplit=1)[0]
        tokens = [t.strip(" ,;:-|()[]\"'+&.") for t in segment.split()]
        tokens = [t for t in tokens if t]
        for i, tok in enumerate(tokens[:2]):
            if self.is_generic(tok) and normalize(tok) not in _JOIN_NEXT:
                continue
            if normalize(tok) in _JOIN_NEXT and i + 1 < len(tokens):
                return f"{tok} {tokens[i + 1]}"
            return tok
        return None
