"""Conferma del produttore con una ricerca generica su Google.

Dal testo della pagina dei risultati (titoli, anteprime, riquadro laterale) si estraggono i nomi di
azienda riconoscibili dalla forma giuridica (S.p.A., S.r.l., GmbH, Ltd, …) o da etichette come
«Produttore: …». Vince l'azienda citata più spesso; conta di più se il nome contiene il marchio.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .brands import normalize
from .products import manufacturer_key

GOOGLE_RESULTS_SELECTOR = "#search, #rso"

_LEGAL = (
    r"(?:(?i:S\.\s?p\.\s?A\.?|SpA|S\.\s?r\.\s?l\.?(?:\s?s\.?)?|Srls?|S\.\s?a\.\s?s\.?|S\.\s?n\.\s?c\.?|"
    r"GmbH(?:\s?&\s?Co\.?\s?KG)?|Ltd\.?|Limited|Inc\.?|LLC|SARL|S\.\s?à\s?r\.\s?l\.?)"
    r"|S\.A\.?|SA|AG|B\.V\.?|BV|S\.L\.?|SL)"  # forme brevi solo in maiuscolo
)
# fino a tre parole con l'iniziale maiuscola (o numeri) seguite dalla forma giuridica
_NAME_WORD = r"(?!(?:Ltd|Limited|Inc|LLC|GmbH|SpA|Srl|Srls|SARL|AG|SA|BV|SL)\b)[A-Z0-9][\w'’&\-]*"
_COMPANY = re.compile(
    r"(?<![\w&])((?:" + _NAME_WORD + r"\s+){0,2}" + _NAME_WORD + r")\s+(" + _LEGAL + r")(?=$|[\s,.;:)\]|·•\-])"
)
_LABELED = re.compile(
    r"(?i:produttore|prodotto da|fabbricante|azienda|società controllante|casa madre|titolare)\s*:\s*"
    r"([A-Z][^\n|·•;:]{1,60})"
)
_LEADING_NOISE = re.compile(r"^(?:(?:Il|La|Lo|Le|I|Gli|Da|Di|Dal|Della|Del|By|The|Per|Con|E|And|Marchio|Brand)\s+)+")


@dataclass
class Candidate:
    name: str
    score: float
    mentions: int


def google_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}&hl=it&gl=it&num=10"


def detect_google_block(html: str, url: str = "") -> str | None:
    low = html.lower()
    if "/sorry/" in url or 'id="captcha-form"' in low or "traffico insolito" in low or "unusual traffic" in low:
        return "captcha"
    return None


def results_text(html: str) -> str:
    """Testo visibile dei risultati e del riquadro laterale, nell'ordine della pagina."""
    soup = BeautifulSoup(html, "lxml")
    for junk in soup.select("script, style, noscript, svg"):
        junk.decompose()
    parts = [el.get_text("\n", strip=True) for el in soup.select("#rso, #rhs")]
    if not any(parts):
        body = soup.body or soup
        parts = [body.get_text("\n", strip=True)]
    return "\n".join(p for p in parts if p)


def _clean_name(name: str) -> str:
    name = " ".join(name.replace("’", "'").split()).strip(" ,;:-–")
    if name.endswith(".") and not re.search(r"\b[A-Za-z]\.$", name):
        name = name[:-1]  # "Ltd." -> "Ltd", ma "S.p.A." resta com'è
    return _LEADING_NOISE.sub("", name)


def extract_companies(text: str, brand: str, exclude: list[str]) -> list[Candidate]:
    brand_norm = normalize(brand)
    excluded = [normalize(e) for e in exclude if normalize(e)]
    found: dict[str, Candidate] = {}
    first_seen: dict[str, int] = {}
    variants: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def add(raw: str, pos: int, weight: float) -> None:
        name = _clean_name(raw)
        key = manufacturer_key(name)
        norm = normalize(name)
        if len(key) < 2 or not re.search(r"[a-z]", key) or any(e in norm for e in excluded):
            return
        cand = found.setdefault(key, Candidate(name=name, score=0.0, mentions=0))
        cand.mentions += 1
        cand.score += weight
        variants[key][name] += 1
        first_seen.setdefault(key, pos)

    labeled = []
    for m in _LABELED.finditer(text):
        add(m.group(1), m.start(1), 2.0)  # «Produttore: X» vale doppio
        labeled.append(m.span(1))
    for m in _COMPANY.finditer(text):
        if not any(a <= m.start() < b for a, b in labeled):  # già contata come «Produttore: …»
            add(f"{m.group(1)} {m.group(2)}", m.start(), 1.0)

    # "Integratore Sideral PharmaNutra" e "PharmaNutra" sono la stessa azienda: tieni il nome più corto
    keys = sorted(found, key=len)
    for i, short in enumerate(keys):
        for long in keys[i + 1:]:
            if long in found and short in found and long.endswith(" " + short):
                found[short].score += found[long].score
                found[short].mentions += found[long].mentions
                first_seen[short] = min(first_seen[short], first_seen[long])
                del found[long]

    for key, cand in found.items():
        # nome da mostrare: la variante più citata, meglio se non tutta in maiuscolo
        cand.name = max(variants[key].items(), key=lambda kv: (kv[1], not kv[0].isupper()))[0]

    for key, cand in found.items():
        if brand_norm and contains_word(key, brand_norm):
            cand.score += 2.0  # "Nutravita Ltd" per il marchio Nutravita
    order = {id(c): first_seen[k] for k, c in found.items()}
    return sorted(found.values(), key=lambda c: (-c.score, order[id(c)], c.name))


def contains_word(haystack: str, needle: str) -> bool:
    return f" {needle} " in f" {haystack} "
