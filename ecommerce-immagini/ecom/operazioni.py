"""Scontorno, sfondi, upscaling e loghi.

L'IA calcola maschere, sfondi e ingrandimenti, ma il prodotto finale viene
sempre ricomposto a partire dai pixel originali.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageOps

from .comfy import ComfyUI, prepara
from .immagini import (
    LANCZOS,
    _eredita,
    applica_maschera,
    avviso,
    bbox_soggetto,
    componi_su,
    ridimensiona,
)

# ---------------------------------------------------------------- scontorno

_sessione_rembg = None


def _sembra_invertita(m: Image.Image) -> bool:
    """Il prodotto di solito sta al centro: se il bordo è più chiaro del centro, la maschera è al contrario."""
    a = np.asarray(m, dtype=np.float32)
    h, w = a.shape
    bordo = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]).mean()
    centro = a[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4].mean()
    return bordo > centro


def maschera(img: Image.Image, motore: str, client: ComfyUI | None = None, workflow=None) -> Image.Image:
    if motore == "rembg":
        global _sessione_rembg
        try:
            from rembg import new_session, remove
        except ImportError as e:
            raise SystemExit("motore rembg non installato: pip install \"rembg[gpu]\"") from e
        if _sessione_rembg is None:
            _sessione_rembg = new_session("birefnet-general")
        m = remove(img.convert("RGB"), session=_sessione_rembg, only_mask=True)
    else:
        rif = client.carica(img.convert("RGB"))
        m = client.esegui(prepara(workflow, immagine=rif))[0]
        if m.mode == "RGBA" and m.getchannel("A").getextrema() != (255, 255):
            m = m.getchannel("A")
        m = m.convert("L")

    if m.size != img.size:
        m = m.resize(img.size, LANCZOS)
    if _sembra_invertita(m):
        avviso("la maschera sembrava al contrario (sfondo bianco): l'ho invertita")
        m = ImageOps.invert(m)
    return m


def scontorna(img, motore, client=None, workflow=None, pulizia: int = 0) -> Image.Image:
    """RGBA con i pixel originali; la trasparenza arriva dalla maschera.

    `pulizia` (0-255) azzera la trasparenza residua sotto la soglia, per eliminare aloni leggeri.
    """
    m = maschera(img, motore, client, workflow)
    if pulizia:
        m = m.point(lambda v: 0 if v < pulizia else v)
    return applica_maschera(img, m)


# ---------------------------------------------------------------- inpainting

def _multiplo8(n: int) -> int:
    return int(math.ceil(n / 8) * 8)


def rigenera_trasparente(
    rgba: Image.Image,
    client: ComfyUI,
    workflow: dict,
    prompt: str,
    negativo: str = "",
    seed: int = 0,
    lato: int = 1024,
) -> Image.Image:
    """Fa generare all'IA le zone trasparenti di `rgba` e restituisce un RGB della stessa misura.

    L'IA lavora su una copia ridotta a ~1 megapixel: il risultato è pensato per
    sfondi e zone da cancellare, mai per il prodotto.
    """
    w, h = rgba.size
    f = lato / max(w, h)
    lw, lh = max(8, round(w * f)), max(8, round(h * f))
    lavoro = Image.new("RGBA", (_multiplo8(lw), _multiplo8(lh)), (0, 0, 0, 0))
    lavoro.paste(ridimensiona(rgba, lw, lh), (0, 0))

    rif = client.carica(lavoro)
    wf = prepara(workflow, immagine=rif, testi={"PROMPT": prompt, "NEGATIVO": negativo}, seed=seed)
    generata = client.esegui(wf)[0].convert("RGB")
    if generata.size != lavoro.size:
        raise RuntimeError(f"il workflow ha cambiato la misura dell'immagine ({generata.size} invece di {lavoro.size})")
    return generata.crop((0, 0, lw, lh)).resize((w, h), LANCZOS)


# ---------------------------------------------------------------- sfondi

def sfondo_colore(prodotto: Image.Image, colore_rgb, con_ombra=False) -> Image.Image:
    return componi_su(prodotto, Image.new("RGB", prodotto.size, colore_rgb), con_ombra)


def sfondo_immagine(prodotto: Image.Image, sfondo: Image.Image, con_ombra=False) -> Image.Image:
    from .immagini import adatta

    tela = adatta(sfondo.convert("RGB"), prodotto.width, prodotto.height, "riempi")
    return componi_su(prodotto, tela, con_ombra)


def sfondo_ai(prodotto, client, workflow, prompt, negativo="", seed=0, con_ombra=False) -> Image.Image:
    generato = rigenera_trasparente(prodotto, client, workflow, prompt, negativo, seed)
    return componi_su(prodotto, generato, con_ombra)


# ---------------------------------------------------------------- upscaling

def upscale(img, fattore, motore="comfy", client=None, workflow=None, modello=None) -> Image.Image:
    w, h = img.size
    tw, th = round(w * fattore), round(h * fattore)
    if motore == "lanczos":
        return ridimensiona(img, tw, th)

    parametri = {"UpscaleModelLoader": {"model_name": modello}} if modello else None
    corrente = img.convert("RGB")
    for _ in range(3):
        if corrente.width >= tw:
            break
        rif = client.carica(corrente)
        corrente = client.esegui(prepara(workflow, immagine=rif, parametri=parametri))[0].convert("RGB")
    fx, fy = corrente.width / w, corrente.height / h
    if abs(fx - fy) > 0.01:
        raise RuntimeError(f"il modello ha scalato in modo non proporzionale ({fx:.3f} x {fy:.3f})")
    out = corrente.resize((tw, th), LANCZOS) if corrente.size != (tw, th) else corrente
    if img.mode == "RGBA":
        out.putalpha(img.getchannel("A").resize((tw, th), LANCZOS))
    return _eredita(out, img)


# ---------------------------------------------------------------- loghi

STILE_LOGO = "flat vector logo mark, minimal, clean shapes, centered, plain white background, "
NEGATIVO_LOGO = "text, letters, words, watermark, signature, photo, photorealistic, 3d render, blurry, noisy, gradient mesh"


def genera_simboli(client, workflow, prompt, negativo, quanti, seed, lato=1024) -> list[Image.Image]:
    out = []
    for i in range(quanti):
        wf = prepara(
            workflow,
            testi={"PROMPT": STILE_LOGO + prompt, "NEGATIVO": negativo or NEGATIVO_LOGO},
            seed=seed + i,
            larghezza=lato,
            altezza=lato,
        )
        out.append(client.esegui(wf)[0])
    return out


def aggiungi_scritta(simbolo: Image.Image, scritta: str, font_path: str, colore_rgb, disposizione="sotto") -> Image.Image:
    """Compone il simbolo con la scritta disegnata nel font vero del marchio (l'IA sbaglia le lettere)."""
    from .testo import carica_font

    simbolo = simbolo.convert("RGBA")
    box = bbox_soggetto(simbolo)
    if box:
        simbolo = simbolo.crop(box)
    sw, sh = simbolo.size

    altezza_testo = sh * (0.28 if disposizione == "sotto" else 0.45)
    dimensione = max(8, round(altezza_testo))
    font = carica_font(font_path, dimensione)
    l, t, r, b = font.getbbox(scritta)
    limite = sw * 2.5 if disposizione == "sotto" else sw * 4
    if r - l > limite:
        dimensione = max(8, round(dimensione * limite / (r - l)))
        font = carica_font(font_path, dimensione)
        l, t, r, b = font.getbbox(scritta)
    tw, th = r - l, b - t
    spazio = round(sh * 0.12)

    if disposizione == "sotto":
        W, H = max(sw, tw), sh + spazio + th
        pos_simbolo = ((W - sw) // 2, 0)
        pos_testo = ((W - tw) // 2 - l, sh + spazio - t)
    else:
        W, H = sw + spazio + tw, max(sh, th)
        pos_simbolo = (0, (H - sh) // 2)
        pos_testo = (sw + spazio - l, (H - th) // 2 - t)

    margine = round(max(W, H) * 0.08)
    tela = Image.new("RGBA", (W + 2 * margine, H + 2 * margine), (0, 0, 0, 0))
    tela.alpha_composite(simbolo, (pos_simbolo[0] + margine, pos_simbolo[1] + margine))
    from PIL import ImageDraw

    ImageDraw.Draw(tela).text(
        (pos_testo[0] + margine, pos_testo[1] + margine), scritta, font=font, fill=(*colore_rgb, 255)
    )
    return tela
