"""Calcolo della share of voice (SoV).

Per ogni keyword k (peso v_k) ogni slot della SERP riceve un peso w(rank) che decresce con la
posizione. La SoV di un prodotto (o marchio) su k è la somma dei pesi dei suoi slot divisa per
la somma dei pesi di tutti gli slot di k. La SoV complessiva è la media delle SoV per keyword
pesata con v_k: così ogni keyword conta per il suo peso, a prescindere da quanti risultati ha.

  sov_total    tutti gli slot (organici + sponsorizzati), peso per posizione assoluta
  sov_organic  solo slot organici, peso per posizione organica
  sov_paid     solo slot sponsorizzati, peso per posizione assoluta
  ads_share    quota della visibilità totale del prodotto/marchio che viene da annunci
  shelf_top10  quota dei primi 10 slot occupati (media pesata sulle keyword)
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .config import ScoringConfig
from .pipeline import SerpRow

NON_RELEVANT = "(non pertinenti)"
NOT_STATED = "(non indicato)"

# raggruppamenti calcolati oltre ai singoli prodotti
GROUPS = {
    "brands": lambda r: r.brand,
    "manufacturers": lambda r: r.manufacturer or NOT_STATED,
    "forms": lambda r: r.form or NOT_STATED,
    "iron_types": lambda r: r.iron_type or NOT_STATED,
}


def position_weight(rank: int, sc: ScoringConfig) -> float:
    if rank < 1:
        raise ValueError("rank parte da 1")
    if sc.weighting == "flat":
        return 1.0
    if sc.weighting == "dcg":
        return 1.0 / math.log2(rank + 1)
    if sc.weighting == "table":
        if rank <= len(sc.table):
            return sc.table[rank - 1]
        return sc.table[-1] * sc.table_decay ** (rank - len(sc.table))
    return 1.0 / rank**sc.zipf_exponent


def describe_weighting(sc: ScoringConfig) -> str:
    return {
        "zipf": "1 / posizione" if sc.zipf_exponent == 1 else f"1 / posizione^{sc.zipf_exponent:g}",
        "dcg": "1 / log2(posizione + 1)",
        "flat": "ogni slot vale 1 (share of shelf)",
        "table": f"tabella {sc.table} poi ×{sc.table_decay:g} a posizione",
    }[sc.weighting]


@dataclass
class _Acc:
    total: float = 0.0
    organic: float = 0.0
    paid: float = 0.0
    paid_part: float = 0.0  # parte di `total` dovuta a slot pagati
    shelf10: float = 0.0
    keywords: set = field(default_factory=set)
    best_org_by_kw: dict = field(default_factory=dict)
    organic_hits: int = 0
    sponsored_hits: int = 0
    widget_hits: int = 0
    asins: set = field(default_factory=set)
    by_asin_total: dict = field(default_factory=lambda: defaultdict(float))


@dataclass
class SovResult:
    products: list[dict]
    groups: dict[str, list[dict]]  # "brands", "manufacturers", "forms", "iron_types"
    keyword_brand: dict[str, dict[str, float]]
    keywords_scored: list[str]
    keywords_empty: list[str]
    meta: dict

    @property
    def brands(self) -> list[dict]:
        return self.groups["brands"]


def compute_sov(
    rows: list[SerpRow],
    keyword_weights: dict[str, float],
    sc: ScoringConfig,
    denominator: str = "all",
) -> SovResult:
    """`denominator`: "all" = quota su tutta la SERP; "relevant" = quota sui soli integratori di ferro."""
    by_kw: dict[str, list[SerpRow]] = defaultdict(list)
    for r in rows:
        by_kw[r.keyword].append(r)

    products: dict[str, _Acc] = defaultdict(_Acc)
    groups: dict[str, dict[str, _Acc]] = {g: defaultdict(_Acc) for g in GROUPS}
    keyword_brand: dict[str, dict[str, float]] = {}
    sample: dict[str, SerpRow] = {}
    v_total = v_org = v_paid = v_top10 = 0.0
    scored, empty = [], []
    slot_count = sponsored_count = relevant_weight = all_weight = 0.0

    for kw in list(keyword_weights) + sorted(set(by_kw) - set(keyword_weights)):
        v = keyword_weights.get(kw, 1.0)
        krows = by_kw.get(kw, [])
        slots = [r for r in krows if r.placement != "widget" and r.rank and (sc.max_rank <= 0 or r.rank <= sc.max_rank)]
        widgets = [r for r in krows if r.placement == "widget"] if sc.widget_weight > 0 else []
        if denominator == "relevant":
            slots = [r for r in slots if r.relevant]
            widgets = [r for r in widgets if r.relevant]
        if not slots and not widgets:
            empty.append(kw)
            continue
        scored.append(kw)

        weight = {id(r): position_weight(r.rank, sc) for r in slots}
        weight.update({id(r): sc.widget_weight for r in widgets})
        w_all = sum(weight.values())
        organic = [r for r in slots if not r.sponsored]
        paid = [r for r in slots if r.sponsored]
        w_org = sum(position_weight(r.organic_rank, sc) for r in organic if r.organic_rank)
        w_paid = sum(weight[id(r)] for r in paid)
        top10 = [r for r in slots if r.rank <= 10]

        v_total += v
        if w_org:
            v_org += v
        if w_paid:
            v_paid += v
        if top10:
            v_top10 += v
        slot_count += v * len(slots)
        sponsored_count += v * len(paid)

        kb: dict[str, float] = defaultdict(float)
        for r in slots + widgets:
            bucket = r.brand if r.relevant else NON_RELEVANT
            share = v * weight[id(r)] / w_all
            all_weight += share
            if r.relevant:
                relevant_weight += share
            kb[bucket] += weight[id(r)] / w_all
            if r.asin not in sample or (sample[r.asin].price is None and r.price is not None):
                sample[r.asin] = r
            accs = [products[r.asin]] + [groups[g][fn(r) if r.relevant else NON_RELEVANT] for g, fn in GROUPS.items()]
            for acc in accs:
                acc.total += share
                acc.keywords.add(kw)
                acc.asins.add(r.asin)
                acc.by_asin_total[r.asin] += share
                if r.placement == "widget":
                    acc.widget_hits += 1
                    if r.sponsored:
                        acc.paid_part += share
                elif r.sponsored:
                    acc.sponsored_hits += 1
                    acc.paid_part += share
                    acc.paid += v * weight[id(r)] / w_paid
                else:
                    acc.organic_hits += 1
                    acc.organic += v * position_weight(r.organic_rank, sc) / w_org
                    best = acc.best_org_by_kw.get(kw)
                    if best is None or r.organic_rank < best:
                        acc.best_org_by_kw[kw] = r.organic_rank
                if r.placement != "widget" and r.rank <= 10:
                    acc.shelf10 += v / len(top10)
        keyword_brand[kw] = dict(kb)

    def finish(acc: _Acc) -> dict:
        best = list(acc.best_org_by_kw.values())
        return {
            "sov_total": acc.total / v_total if v_total else 0.0,
            "sov_organic": acc.organic / v_org if v_org else 0.0,
            "sov_paid": acc.paid / v_paid if v_paid else 0.0,
            "ads_share": acc.paid_part / acc.total if acc.total else 0.0,
            "shelf_top10": acc.shelf10 / v_top10 if v_top10 else 0.0,
            "keywords_present": len(acc.keywords),
            "keywords_top10_organic": sum(1 for b in best if b <= 10),
            "best_organic_rank": min(best) if best else None,
            "avg_organic_rank": round(sum(best) / len(best), 1) if best else None,
            "organic_hits": acc.organic_hits,
            "sponsored_hits": acc.sponsored_hits,
            "widget_hits": acc.widget_hits,
        }

    product_rows = []
    for asin, acc in products.items():
        s = sample[asin]
        product_rows.append(
            {
                "asin": asin,
                "brand": s.brand,
                "brand_source": s.brand_source,
                "title": s.title,
                "relevant": s.relevant,
                **finish(acc),
                "price": s.price,
                "rating": s.rating,
                "reviews": s.reviews,
                "bought_last_month": s.bought_last_month,
                "badges": s.badges,
                "manufacturer": s.manufacturer,
                "manufacturer_source": s.manufacturer_source,
                "form": s.form,
                "iron_type": s.iron_type,
            }
        )
    product_rows.sort(key=lambda p: (-p["sov_total"], p["asin"]))

    def leaders(acc: _Acc, attr: str) -> list[str]:
        """Valori di `attr` (marchio, produttore) dei prodotti del gruppo, dal più visibile."""
        weight: dict[str, float] = defaultdict(float)
        for asin, w in acc.by_asin_total.items():
            value = getattr(sample[asin], attr)
            if value:
                weight[value] += w
        return sorted(weight, key=lambda k: (-weight[k], k))

    group_rows: dict[str, list[dict]] = {}
    for g, accs_by_name in groups.items():
        out = []
        for name, acc in accs_by_name.items():
            top_asin = max(acc.by_asin_total, key=acc.by_asin_total.get)
            out.append(
                {
                    "brand": name,  # nome del gruppo (marchio, produttore, forma o tipo di ferro)
                    **finish(acc),
                    "n_products": len(acc.asins),
                    "top_asin": top_asin,
                    "top_title": sample[top_asin].title,
                    "manufacturer": (leaders(acc, "manufacturer") or [None])[0],
                    "brands": leaders(acc, "brand"),
                }
            )
        out.sort(key=lambda b: (b["brand"] == NON_RELEVANT, b["brand"] == NOT_STATED, -b["sov_total"], b["brand"]))
        group_rows[g] = out
    brand_rows = group_rows["brands"]

    meta = {
        "keywords_scored": len(scored),
        "keyword_weight_total": v_total,
        "sponsored_slot_share": sponsored_count / slot_count if slot_count else 0.0,
        "relevant_visibility_share": relevant_weight / all_weight if all_weight else 0.0,
        "denominator": denominator,
        "weighting": describe_weighting(sc),
        "max_rank": sc.max_rank,
        "n_products": sum(1 for p in product_rows if p["relevant"]),
        "n_brands": sum(1 for b in brand_rows if b["brand"] != NON_RELEVANT),
    }
    return SovResult(product_rows, group_rows, keyword_brand, scored, empty, meta)
