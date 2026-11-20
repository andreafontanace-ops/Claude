"""Grafico a linee dell'andamento della share of voice, in SVG generato sul server."""

from __future__ import annotations

from datetime import datetime
from html import escape

# palette categoriale nell'ordine fisso (validata per daltonismo, chiaro/scuro via CSS)
SERIES = 8


def trend_svg(series: dict[str, list[tuple[datetime, float]]], own: set[str], width: int = 760, height: int = 260) -> str:
    """`series`: marchio -> [(istante, sov 0-1)]. I marchi propri sono disegnati per primi e più spessi."""
    points = [(t, v) for pts in series.values() for t, v in pts]
    if len(points) < 2 or len({t for t, _ in points}) < 2:
        return '<p class="muted">L\'andamento compare dalla seconda raccolta.</p>'
    pad_l, pad_r, pad_t, pad_b = 44, 12, 12, 28
    t0 = min(t for t, _ in points).timestamp()
    t1 = max(t for t, _ in points).timestamp()
    top = max(v for _, v in points) * 100 or 1.0
    step = next(s for s in (1, 2, 5, 10, 20, 25) if top / s <= 4)  # 4 tacche "tonde"
    vmax = min(100, step * -(-top // step)) / 100

    def x(t: datetime) -> float:
        return pad_l + (t.timestamp() - t0) / (t1 - t0) * (width - pad_l - pad_r)

    def y(v: float) -> float:
        return pad_t + (1 - v / vmax) * (height - pad_t - pad_b)

    parts = [f'<svg class="trend" viewBox="0 0 {width} {height}" role="img" aria-label="Andamento della share of voice">']
    for i in range(int(round(vmax * 100 / step)) + 1):
        v = i * step / 100
        parts.append(f'<line class="grid" x1="{pad_l}" x2="{width - pad_r}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        parts.append(f'<text class="axis" x="{pad_l - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v * 100:.0f}%</text>')
    for label_t, anchor in ((t0, "start"), ((t0 + t1) / 2, "middle"), (t1, "end")):
        dt = datetime.fromtimestamp(label_t)
        parts.append(f'<text class="axis" x="{x(dt):.1f}" y="{height - 8}" text-anchor="{anchor}">{dt:%d/%m %H:%M}</text>')
    for i, (brand, pts) in enumerate(series.items()):
        cls = f"s{i % SERIES + 1}" + (" own" if brand in own else "")
        pts = sorted(pts)
        path = " ".join(f"{'M' if j == 0 else 'L'}{x(t):.1f},{y(v):.1f}" for j, (t, v) in enumerate(pts))
        parts.append(f'<path class="line {cls}" d="{path}"/>')
        for t, v in pts:
            parts.append(
                f'<circle class="pt {cls}" cx="{x(t):.1f}" cy="{y(v):.1f}" r="4">'
                f"<title>{escape(brand)} · {t:%d/%m %H:%M} · {v * 100:.1f}%</title></circle>"
            )
    parts.append("</svg>")
    legend = "".join(
        f'<span class="key"><i class="sw s{i % SERIES + 1}"></i>{escape(b)}{" (tuo)" if b in own else ""}</span>'
        for i, b in enumerate(series)
    )
    return "".join(parts) + f'<div class="legend">{legend}</div>'
