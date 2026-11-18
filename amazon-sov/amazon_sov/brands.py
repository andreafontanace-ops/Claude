"""Normalizzazione dei marchi e filtro di pertinenza (è un integratore di ferro?)."""

from __future__ import annotations

import re
import unicodedata

from .config import Config

UNKNOWN_BRAND = "(marchio da verificare)"  # pagina prodotto non ancora letta
GENERIC_BRAND = "(senza marchio)"  # Amazon non indica il marchio o scrive «Generico»

# valori che su Amazon vogliono dire "nessun marchio"
_NO_BRAND = {
    "generico", "generica", "generic", "senza marca", "senza marchio", "unbranded", "no brand", "nessuna marca",
    "non applicabile", "n a", "na", "sconosciuto", "sconosciuta", "unknown", "marca sconosciuta",
}
# forma giuridica in fondo al nome di un'azienda: "WeightWorld Ltd" -> marchio "WeightWorld"
_COMPANY_SUFFIX = re.compile(
    r"[\s,]+(?:S\.?\s?p\.?\s?A\.?|S\.?\s?r\.?\s?l\.?\s?s?\.?|S\.?\s?a\.?\s?s\.?|S\.?\s?n\.?\s?c\.?|"
    r"GmbH(?:\s?&\s?Co\.?\s?KG)?|Ltd\.?|Limited|Inc\.?|LLC|B\.?\s?V\.?|AG|S\.?\s?A\.?|S\.?\s?L\.?|SARL)\s*$",
    re.I,
)


def brand_from_company(name: str | None) -> str | None:
    """Marchio ricavato dal nome del produttore, senza forma giuridica."""
    if not name:
        return None
    brand = name.strip()
    while True:
        stripped = _COMPANY_SUFFIX.sub("", brand).strip(" ,.-")
        if stripped == brand:
            break
        brand = stripped
    return brand or None


def is_no_brand(value: str | None) -> bool:
    return normalize(value) in _NO_BRAND

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
# Parole descrittive che possono stare dentro il nome di un marchio solo come prima parola
# ("Bio Nutrition", "Forte Pharma", "Pura Vida"), mai come seconda ("Solgar Gentle").
_WEAK_FIRST = {"bio", "natural", "naturale", "pura", "puro", "forte", "plus", "premium", "vegan", "extra", "max",
               "alta", "alto", "nuova", "nuovo"}
_NOT_SECOND = {
    "gentle", "high", "strength", "active", "complete", "daily", "advanced", "ultra", "super", "mega", "maxi",
    "gold", "quality", "kids", "junior", "baby", "women", "men", "woman", "man", "chewable", "softgels", "tablets",
    "capsules", "drops", "energy", "fe", "ferrum", "original", "classic", "new", "zero", "light", "family",
}
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

    Ordine: correzione manuale per ASIN > riga del marchio nella SERP > marchio letto dalla pagina
    prodotto > alias trovato nel titolo > produttore della pagina prodotto > prima o seconda parola
    del titolo > «senza marchio» se la pagina prodotto è stata letta e non lo indica.
    """

    def __init__(
        self,
        cfg: Config,
        product_page_brands: dict[str, str] | None = None,
        product_info: dict[str, dict] | None = None,
    ):
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
        self._page_makers: dict[str, str] = {}
        self._checked: set[str] = set()
        for asin, info in (product_info or {}).items():
            asin = asin.upper()
            if info.get("brand"):
                self._page_brands[asin] = info["brand"]
            if info.get("manufacturer"):
                self._page_makers[asin] = info["manufacturer"]
            if info.get("checked_at"):
                self._checked.add(asin)
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
            return (GENERIC_BRAND if is_no_brand(raw_brand) else self.canonical(raw_brand)), "serp"
        page_brand = self._page_brands.get(asin)
        if page_brand and not is_no_brand(page_brand):
            return self.canonical(page_brand), "product_page"
        title_norm = normalize(title)
        for alias, canonical in self._aliases:
            if contains_phrase(title_norm, alias):
                return canonical, "alias"
        maker_brand = brand_from_company(self._page_makers.get(asin))
        if maker_brand and not is_no_brand(maker_brand):
            return self.canonical(maker_brand), "product_page_maker"
        guess = self._guess_from_title(title)
        if guess and not page_brand:  # se Amazon dice «Generico», non inventiamo un marchio dal titolo
            return self.canonical(guess), "title_guess"
        if page_brand or asin in self._checked:
            return GENERIC_BRAND, "product_page"
        return UNKNOWN_BRAND, "unknown"

    def is_generic(self, word: str) -> bool:
        norm = normalize(word)
        if len(norm) < 2 or not re.search(r"[a-z]", norm) or re.match(r"\d", norm):
            return True  # numeri, dosi ("28mg"), sigle di una lettera
        if norm in self._generic:
            return True
        return norm.startswith(BUILTIN_GENERIC_PREFIXES)

    def _second_word_of_brand(self, word: str | None) -> bool:
        return bool(
            word and word[0].isupper() and not self.is_generic(word) and normalize(word) not in _NOT_SECOND
        )

    def _guess_from_title(self, title: str | None) -> str | None:
        """Il marchio è di solito la prima parola del titolo, a volte le prime due."""
        segment = _SEGMENT.split(_TRADEMARKS.sub("", title or ""), maxsplit=1)[0]
        tokens = [t.strip(" ,;:-|()[]\"'+&.") for t in segment.split()]
        tokens = [t for t in tokens if t]
        if not tokens:
            return None
        first = tokens[0]
        second = tokens[1] if len(tokens) > 1 else None
        if normalize(first) in _JOIN_NEXT and second:
            return f"{first} {second}"  # "Dr. Giorgini", "Nature's Bounty"
        if not self.is_generic(first):
            # prima parola; anche la seconda se fa parte del nome ("Pharma Nord", "Named Sport")
            return f"{first} {second}" if self._second_word_of_brand(second) else first
        if normalize(first) in _WEAK_FIRST and self._second_word_of_brand(second):
            return f"{first} {second}"  # "Bio Nutrition", "Forte Pharma"
        if second and not self.is_generic(second):
            return second  # "Ferro WeightWorld …"
        return None
