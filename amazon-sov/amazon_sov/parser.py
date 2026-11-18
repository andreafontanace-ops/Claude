"""Parsing delle pagine di risultati di ricerca (SERP) di Amazon.

Il markup di Amazon cambia spesso: ogni campo ha più selettori di riserva e il parser
non fallisce se un campo manca (lo lascia vuoto). Usa `amazon-sov inspect pagina.html`
per controllare cosa viene estratto da una pagina reale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
RESULT_SELECTOR = 'div[data-component-type="s-search-result"]'

SPONSORED_SELECTORS = (
    ".puis-sponsored-label-text",
    ".puis-sponsored-label-info-icon",
    ".s-sponsored-label-text",
    ".s-sponsored-label-info-icon",
    '[data-component-type="sp-sponsored-result"]',
)
SPONSORED_WORDS = {"sponsorizzato", "sponsorizzata", "sponsorizzati", "sponsored", "annuncio sponsorizzato"}


@dataclass
class SerpItem:
    asin: str
    slot: int  # posizione nella pagina (1 = primo risultato); 0 per i widget
    title: str
    brand_raw: str | None
    sponsored: bool
    placement: str  # "organic" | "sponsored" | "widget"
    price: float | None = None
    list_price: float | None = None
    rating: float | None = None
    reviews: int | None = None
    bought_last_month: int | None = None
    badges: list[str] = field(default_factory=list)
    widget: str | None = None  # tipo di widget quando placement == "widget"


@dataclass
class ParsedPage:
    keyword: str | None
    page: int | None
    items: list[SerpItem]
    blocked: str | None = None  # "captcha" | "interstitial" | "error" | None
    result_count_text: str | None = None

    @property
    def results(self) -> list[SerpItem]:
        return [i for i in self.items if i.placement != "widget"]


# --------------------------------------------------------------------------- numeri


def parse_price(text: str | None) -> float | None:
    """'12,90 €' -> 12.9 ; '1.234,50 €' -> 1234.5 ; '€12.90' -> 12.9"""
    if not text:
        return None
    t = re.sub(r"[^\d,.]", "", text)
    if not re.search(r"\d", t):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") == 1 and len(t.split(".")[1]) == 2:
        pass  # punto decimale all'inglese
    else:
        t = t.replace(".", "")
    try:
        return round(float(t), 2)
    except ValueError:
        return None


def parse_rating(text: str | None) -> float | None:
    """'4,5 su 5 stelle' -> 4.5"""
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:su|out of|von)\s*5", text, re.I)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    return value if 0 <= value <= 5 else None


def parse_count(text: str | None) -> int | None:
    """'12.345' -> 12345 ; '(1,2K)' -> 1200 ; 'Più di 1000 acquisti' -> 1000 ; '3 mila' -> 3000"""
    if not text:
        return None
    t = text.replace("\xa0", " ").lower()
    m = re.search(r"(\d+(?:[.,]\d+)*)\s*(k|mila|mln|m)?(?![a-z])", t)
    if not m:
        return None
    num, suffix = m.groups()
    if suffix:
        mult = 1000 if suffix in ("k", "mila") else 1_000_000
        return int(round(float(num.replace(".", "").replace(",", ".") if "," in num else num) * mult))
    return int(re.sub(r"\D", "", num))


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


# --------------------------------------------------------------------------- pagina


def detect_block(html: str) -> str | None:
    """Riconosce le pagine che non sono risultati: captcha, verifica anti-bot, errore."""
    low = html.lower()
    if "validatecaptcha" in low or "inserisci i caratteri" in low or "api-services-support@amazon.com" in low:
        return "captcha"
    if 's-search-result' in low:
        return None
    if "bm-verify" in low or "/_sec/verify" in low:
        return "interstitial"
    if "siamo spiacenti" in low and "amazon" in low and "s-main-slot" not in low:
        return "error"
    return None


def parse_search_page(html: str, keyword: str | None = None, page: int | None = None) -> ParsedPage:
    soup = BeautifulSoup(html, "lxml")
    blocked = detect_block(html)

    box = soup.select_one("input#twotabsearchtextbox") or soup.select_one('input[name="field-keywords"]')
    detected_kw = _clean(box.get("value")) if box and box.get("value") else None

    detected_page = None
    sel = soup.select_one(".s-pagination-selected")
    if sel and sel.get_text(strip=True).isdigit():
        detected_page = int(sel.get_text(strip=True))

    count_text = None
    for el in soup.select('[data-component-type="s-result-info-bar"] span, .s-breadcrumb span, h1 span'):
        t = _clean(el.get_text(" "))
        if "risultat" in t.lower() or "results" in t.lower():
            count_text = t
            break

    result_els = [el for el in soup.select(RESULT_SELECTOR)]
    items: list[SerpItem] = []
    slot = 0
    for el in result_els:
        asin = (el.get("data-asin") or "").strip().upper()
        if not ASIN_RE.match(asin):
            continue
        slot += 1
        items.append(_parse_result(el, asin, slot))

    items.extend(_parse_widgets(soup))

    return ParsedPage(
        keyword=keyword or detected_kw,
        page=page or detected_page or 1,
        items=items,
        blocked=blocked if not result_els else None,
        result_count_text=count_text,
    )


# --------------------------------------------------------------------------- risultato


def _parse_result(el: Tag, asin: str, slot: int) -> SerpItem:
    title, brand = _title_and_brand(el)
    sponsored = _is_sponsored(el)
    price_el = el.select_one(".a-price:not(.a-text-price) .a-offscreen") or el.select_one(".a-price .a-offscreen")
    list_el = el.select_one(".a-price.a-text-price .a-offscreen")
    return SerpItem(
        asin=asin,
        slot=slot,
        title=title,
        brand_raw=brand,
        sponsored=sponsored,
        placement="sponsored" if sponsored else "organic",
        price=parse_price(price_el.get_text() if price_el else None),
        list_price=parse_price(list_el.get_text() if list_el else None),
        rating=_rating(el),
        reviews=_reviews(el),
        bought_last_month=_bought_last_month(el),
        badges=_badges(el),
    )


def _is_sponsored(el: Tag) -> bool:
    if "AdHolder" in (el.get("class") or []):
        return True
    if any(el.select_one(s) for s in SPONSORED_SELECTORS):
        return True
    for a in el.select("a[href]"):
        if "/sspa/click" in a["href"]:
            return True
    for span in el.select("span.a-color-secondary, .puis-label-popover-default span, .s-label-popover-default span"):
        if _clean(span.get_text()).lower() in SPONSORED_WORDS:
            return True
    return False


def _strip_sponsored_prefix(text: str) -> str:
    return re.sub(r"^(annuncio\s+)?sponsorizzat[oa]\s*(annuncio)?\s*[-–—:]?\s*", "", text, flags=re.I).strip()


def _title_and_brand(el: Tag) -> tuple[str, str | None]:
    scope = el.select_one('[data-cy="title-recipe"]') or el
    title = None
    brand = None
    for h2 in scope.find_all("h2"):
        text = _clean(h2.get_text(" "))
        in_link = h2.find_parent("a") is not None or h2.find("a") is not None
        is_title = in_link or "a-text-normal" in (h2.get("class") or [])
        if is_title and not title:
            title = text or _strip_sponsored_prefix(_clean(h2.get("aria-label")))
        elif not is_title and text and not brand:
            brand = text
    if not brand:
        # markup meno recente: riga del marchio in un h5 sopra il titolo
        for b in scope.select("h5.s-line-clamp-1 span, div.a-row.a-color-secondary > h5 span"):
            text = _clean(b.get_text(" "))
            if text:
                brand = text
                break
    if not brand and scope is not el:
        # riga del marchio senza h2/h5: testo breve sopra il titolo, fuori dal link del titolo
        for b in scope.select("div.a-row.a-color-secondary span.a-size-base-plus, div.a-row.a-color-secondary span.a-size-base"):
            text = _clean(b.get_text(" "))
            if text and b.find_parent("a") is None and _looks_like_brand(text):
                brand = text
                break
    if not brand:
        # riga "di Marca" sotto il titolo
        for row in el.select("div.a-row"):
            m = re.fullmatch(r"di\s+(.{2,40})", _clean(row.get_text(" ")))
            if m and _looks_like_brand(m.group(1)):
                brand = m.group(1)
                break
    if not title:
        link = el.select_one("a.a-text-normal span, a.s-link-style span") or el.select_one("img.s-image")
        if link is not None:
            title = _clean(link.get("alt") if link.name == "img" else link.get_text(" "))
    title = _strip_sponsored_prefix(title or "")
    if brand and (brand.lower() in SPONSORED_WORDS or len(brand) > 60 or brand == title):
        brand = None
    return title, brand


def _looks_like_brand(text: str) -> bool:
    if text.lower() in SPONSORED_WORDS or len(text) > 40 or len(text.split()) > 5 or text[:1].isdigit():
        return False
    return not re.search(r"\d+[.,]?\d*\s*(€|%|stelle|valutazion|acquist)", text, re.I)


def _rating(el: Tag) -> float | None:
    for cand in el.select('[data-cy="reviews-block"] span.a-icon-alt, i[class*="a-icon-star"] span.a-icon-alt, span.a-icon-alt'):
        value = parse_rating(cand.get_text())
        if value is not None:
            return value
    for cand in el.select("[aria-label]"):
        value = parse_rating(cand.get("aria-label"))
        if value is not None:
            return value
    return None


def _reviews(el: Tag) -> int | None:
    for cand in el.select("[aria-label]"):
        label = cand.get("aria-label", "")
        if re.search(r"\d\s*(valutazion|recension|ratings?\b)", label, re.I):
            return parse_count(label)
    for cand in el.select('a[href*="customerReviews"] span, span.s-underline-text'):
        text = _clean(cand.get_text())
        if re.fullmatch(r"\(?\d[\d.,]*\s*(k|mila)?\)?", text, re.I):
            return parse_count(text)
    return None


def _bought_last_month(el: Tag) -> int | None:
    for node in el.find_all(string=re.compile(r"mese scorso|past month", re.I)):
        text = _clean(node.parent.get_text(" ") if node.parent else str(node))
        value = parse_count(text)
        if value is not None:
            return value
    return None


def _badges(el: Tag) -> list[str]:
    texts = [_clean(b.get_text(" ")).lower() for b in el.select(".a-badge-text, .a-badge-label-inner, .s-label-popover-hover")]
    found = []
    if el.select_one('[id$="-amazons-choice"]') or any("scelta amazon" in t or "amazon's choice" in t for t in texts):
        found.append("Scelta Amazon")
    if el.select_one('[id$="-best-seller"]') or any("vendut" in t or "best seller" in t or "bestseller" in t for t in texts):
        found.append("Bestseller")
    if any("offerta" in t or "deal" in t for t in texts):
        found.append("Offerta")
    return found


def compact_html(html: str, asin: str, limit: int = 3500) -> str:
    """HTML ridotto all'osso di un risultato (struttura e classi, niente script né immagini)."""
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(f'{RESULT_SELECTOR}[data-asin="{asin}"]')
    if el is None:
        return ""
    for junk in el.select("script, style, svg, noscript, img, input"):
        junk.decompose()
    keep = {"class", "id", "data-cy", "data-component-type", "aria-label", "data-asin", "href"}
    for tag in [el, *el.find_all(True)]:
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in keep}
        if "href" in tag.attrs:
            tag.attrs["href"] = str(tag.attrs["href"])[:40]
    text = re.sub(r">\s+<", "><", " ".join(str(el).split()))
    return text if len(text) <= limit else text[:limit] + " …[tagliato]"


# --------------------------------------------------------------------------- widget


def _widget_type(el: Tag) -> str:
    ids = []
    node: Tag | None = el
    depth = 0
    while node is not None and isinstance(node, Tag) and depth < 12:
        for attr in ("data-component-type", "data-cel-widget", "cel_widget_id", "class"):
            val = node.get(attr)
            if val:
                ids.append(" ".join(val) if isinstance(val, list) else str(val))
        node = node.parent
        depth += 1
    joined = " ".join(ids).lower()
    if re.search(r"\bsbv|sb[-_]|_sb\b|sponsored-brand|multi-brand|headline", joined):
        return "sponsored_brand"
    if "sponsored" in joined or re.search(r"\bsp[-_]", joined):
        return "sponsored_widget"
    return "widget"


def _parse_widgets(soup: BeautifulSoup) -> list[SerpItem]:
    """Prodotti fuori dalla griglia dei risultati (Sponsored Brands, caroselli, ecc.)."""
    scope = soup.select_one("div.s-main-slot") or soup.select_one("#search") or soup
    out: list[SerpItem] = []
    seen: set[tuple[str, str]] = set()
    for el in scope.select("[data-asin]"):
        asin = (el.get("data-asin") or "").strip().upper()
        if not ASIN_RE.match(asin):
            continue
        if el.get("data-component-type") == "s-search-result" or el.find_parent(attrs={"data-component-type": "s-search-result"}):
            continue
        kind = _widget_type(el)
        if (asin, kind) in seen:
            continue
        seen.add((asin, kind))
        img = el.select_one("img[alt]")
        title = _clean(img.get("alt")) if img else ""
        if not title:
            link = el.select_one("a span, a")
            title = _clean(link.get_text(" ")) if link else ""
        out.append(
            SerpItem(
                asin=asin,
                slot=0,
                title=title,
                brand_raw=None,
                sponsored=kind.startswith("sponsored"),
                placement="widget",
                widget=kind,
            )
        )
    return out


# --------------------------------------------------------------------------- pagina prodotto

_MARKS = "\u200e\u200f\u200b\ufeff"
_ADDRESS = re.compile(
    # dopo una virgola o un punto e virgola: parola tipica di indirizzo, oppure un pezzo con un numero civico/CAP
    r"[,;]\s*(?:(?:via|viale|piazza|piazzale|corso|largo|strada|localit\w*|zona|contrada|tel|e-?mail)\b|loc\.|c\.da|www\."
    r"|[^,;]*\d).*$",
    re.I,
)


@dataclass
class ProductInfo:
    brand: str | None = None
    manufacturer: str | None = None
    item_form: str | None = None


def _label(text: str) -> str:
    return " ".join(text.translate({ord(c): None for c in _MARKS}).strip().rstrip(":").split()).lower()


def _value(text: str) -> str:
    return _clean(text.translate({ord(c): None for c in _MARKS})).strip(" :")


def _product_facts(soup: BeautifulSoup) -> dict[str, str]:
    """Etichetta -> valore da tabella panoramica, dettagli tecnici e «Dettagli prodotto»."""
    facts: dict[str, str] = {}
    rows = soup.select(
        "#productOverview_feature_div tr, tr.po-brand, table.prodDetTable tr, "
        "#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr"
    )
    for row in rows:
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            value = _value(cells[1].get_text(" "))
            if value:
                facts.setdefault(_label(cells[0].get_text(" ")), value)
    for li in soup.select("#detailBullets_feature_div li, #detailBulletsWrapper_feature_div li"):
        text = _clean(li.get_text(" "))
        m = re.match(rf"^(.{{2,60}}?)[\s{_MARKS}]*:[\s{_MARKS}]*(.+)$", text)
        if m and _value(m.group(2)):
            facts.setdefault(_label(m.group(1)), _value(m.group(2)))
    return facts


def _fact(facts: dict[str, str], *labels: str) -> str | None:
    for label in labels:
        if facts.get(label):
            return facts[label]
    return None


def clean_manufacturer(text: str | None) -> str | None:
    """Toglie l'indirizzo: 'Pharma Srl, Via Roma 1, Milano' -> 'Pharma Srl'."""
    if not text:
        return None
    name = _ADDRESS.sub("", _value(text)).strip(" ,;-")
    return name or None


def parse_product_page(html: str) -> ProductInfo:
    """Marchio, produttore e forma dalla pagina prodotto (/dp/ASIN)."""
    soup = BeautifulSoup(html, "lxml")
    facts = _product_facts(soup)
    brand = None
    byline = soup.select_one("#bylineInfo")
    if byline:
        text = _clean(byline.get_text(" "))
        for pattern in (
            r"^Visita lo Store di\s+(.+)$",
            r"^Marca:\s*(.+)$",
            r"^Brand:\s*(.+)$",
            r"^Visit the\s+(.+?)\s+Store$",
        ):
            m = re.match(pattern, text, re.I)
            if m:
                brand = m.group(1).strip()
                break
    brand = brand or _fact(facts, "marca", "brand")
    manufacturer = clean_manufacturer(
        _fact(facts, "produttore", "nome del produttore", "fabbricante", "manufacturer")
    )
    item_form = _fact(facts, "forma del prodotto", "forma dell'articolo", "forma dell’articolo", "forma", "item form")
    return ProductInfo(brand=brand, manufacturer=manufacturer, item_form=item_form)


def parse_product_brand(html: str) -> str | None:
    return parse_product_page(html).brand
