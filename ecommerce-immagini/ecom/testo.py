"""Sostituisce un testo grafico (banner, etichette, prezzi) con lo stesso font e lo stesso colore.

Lo strumento modifica solo il riquadro indicato con --box: il resto dell'immagine,
compreso quello che è scritto sul prodotto, resta identico pixel per pixel.
Il font non si riconosce in automatico in modo affidabile, quindi serve il file
.ttf/.otf originale. Il colore invece viene misurato sull'immagine.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

from .immagini import _eredita, avviso


@dataclass
class Analisi:
    colore: tuple[int, int, int]
    sfondo: tuple[int, int, int]
    maschera: np.ndarray  # bool, misura del riquadro: True dove c'è il testo
    inchiostro: tuple[int, int, int, int]  # ingombro del testo, relativo al riquadro


def carica_font(percorso: str, dimensione: int, variante: str | None = None):
    motore = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    font = ImageFont.truetype(percorso, dimensione, layout_engine=motore)
    if variante:
        font.set_variation_by_name(variante)
    return font


def analizza(img: Image.Image, box, soglia: int = 60) -> Analisi:
    """Il bordo del riquadro deve essere sfondo: disegna il box con un po' di margine attorno al testo."""
    x, y, w, h = box
    regione = np.asarray(img.convert("RGB").crop((x, y, x + w, y + h)), dtype=np.int16)
    bordo = np.concatenate([regione[0], regione[-1], regione[:, 0], regione[:, -1]])
    sfondo = np.median(bordo, axis=0)
    distanza = np.abs(regione - sfondo).sum(axis=2)
    testo = distanza > soglia
    if not testo.any():
        raise ValueError("nessun testo trovato nel riquadro: controlla --box o abbassa --soglia")
    # i pixel più lontani dallo sfondo sono il cuore delle lettere, senza l'antialiasing dei bordi
    pieni = testo & (distanza >= np.percentile(distanza[testo], 60))
    colore = tuple(int(c) for c in np.median(regione[pieni], axis=0))
    ys, xs = np.nonzero(testo)
    return Analisi(
        colore=colore,
        sfondo=tuple(int(c) for c in sfondo),
        maschera=testo,
        inchiostro=(int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1),
    )


def _maschera_piena(img, box, maschera_box, espandi=2) -> np.ndarray:
    x, y, w, h = box
    m = np.zeros((img.height, img.width), np.uint8)
    m[y : y + h, x : x + w] = maschera_box.astype(np.uint8) * 255
    return cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=espandi)


def cancella_opencv(img: Image.Image, box, analisi: Analisi, raggio: int = 5) -> Image.Image:
    """Adatto a sfondi uniformi o sfumati. Cambia solo i pixel delle lettere."""
    m = _maschera_piena(img, box, analisi.maschera)
    bgr = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    pulita = cv2.inpaint(bgr, m, raggio, cv2.INPAINT_TELEA)
    out = Image.fromarray(cv2.cvtColor(pulita, cv2.COLOR_BGR2RGB))
    if img.mode == "RGBA":
        out.putalpha(img.getchannel("A"))
    return _eredita(out, img)


def cancella_ai(img, box, analisi, client, workflow, prompt, seed=0, contesto=64) -> Image.Image:
    """Per sfondi con texture o foto: l'IA ricostruisce solo i pixel delle lettere."""
    from .operazioni import rigenera_trasparente

    m = _maschera_piena(img, box, analisi.maschera, espandi=3)
    x, y, w, h = box
    x0, y0 = max(0, x - contesto), max(0, y - contesto)
    x1, y1 = min(img.width, x + w + contesto), min(img.height, y + h + contesto)
    zona = img.convert("RGB").crop((x0, y0, x1, y1))
    buco = Image.fromarray(255 - m[y0:y1, x0:x1])
    zona_rgba = zona.copy()
    zona_rgba.putalpha(buco)
    rigenerata = rigenera_trasparente(zona_rgba, client, workflow, prompt, seed=seed, lato=768)

    out = img.copy()
    out.paste(rigenerata.convert(img.mode), (x0, y0), Image.fromarray(m[y0:y1, x0:x1]))
    return _eredita(out, img)


def scrivi(
    img: Image.Image,
    box,
    testo: str,
    font_path: str,
    colore,
    analisi: Analisi,
    dimensione: int | None = None,
    allinea: str = "centro",
    sposta=(0, 0),
    variante: str | None = None,
) -> Image.Image:
    x, y, w, h = box
    ix0, iy0, ix1, iy1 = analisi.inchiostro
    altezza_max = iy1 - iy0

    if dimensione is None:
        # la dimensione più grande che non supera l'altezza del testo originale né la larghezza del box
        basso, alto = 4, 4000
        while basso < alto:
            mezzo = (basso + alto + 1) // 2
            l, t, r, b = carica_font(font_path, mezzo, variante).getbbox(testo)
            if b - t <= altezza_max and r - l <= w:
                basso = mezzo
            else:
                alto = mezzo - 1
        dimensione = basso

    font = carica_font(font_path, dimensione, variante)
    l, t, r, b = font.getbbox(testo)
    larghezza_testo = r - l
    if larghezza_testo > w:
        avviso("il nuovo testo è più largo del riquadro: esce dai bordi")

    if allinea == "sinistra":
        px = x + ix0 - l
    elif allinea == "destra":
        px = x + ix1 - larghezza_testo - l
    else:
        px = x + (ix0 + ix1) / 2 - larghezza_testo / 2 - l
    py = y + (iy0 + iy1) / 2 - (b - t) / 2 - t

    out = img.copy()
    fill = (*colore, 255) if out.mode == "RGBA" else tuple(colore)
    ImageDraw.Draw(out).text((px + sposta[0], py + sposta[1]), testo, font=font, fill=fill)
    print(f"  font {dimensione}px, colore #{'%02x%02x%02x' % tuple(colore[:3])}")
    return _eredita(out, img)
