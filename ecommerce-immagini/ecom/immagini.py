"""Operazioni sulle immagini con tre regole fisse.

1. Mai scalare in modo non proporzionale: niente schiacciamenti o allungamenti.
2. Salvare sempre senza perdita (PNG, WebP lossless, TIFF). Il JPEG si usa solo
   se richiesto, alla qualità massima.
3. I pixel del prodotto non si rigenerano mai: dove il prodotto è opaco,
   l'uscita contiene esattamente i pixel originali.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageColor, ImageFilter, ImageOps

ESTENSIONI = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
LANCZOS = Image.Resampling.LANCZOS


def avviso(msg: str) -> None:
    print(f"  ! {msg}", file=sys.stderr)


def _eredita(dst: Image.Image, src: Image.Image) -> Image.Image:
    """Copia il profilo colore e i DPI (le altre operazioni li perdono)."""
    for chiave in ("icc_profile", "dpi"):
        if chiave in src.info:
            dst.info[chiave] = src.info[chiave]
    return dst


def apri(percorso) -> Image.Image:
    """Apre un'immagine in RGB o RGBA, applica la rotazione EXIF e converte il CMYK in sRGB tramite il profilo ICC."""
    img = Image.open(percorso)
    img.load()
    icc = img.info.get("icc_profile")
    dpi = img.info.get("dpi")
    img = ImageOps.exif_transpose(img)

    if img.mode == "CMYK":
        if icc:
            sorgente = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
            img = ImageCms.profileToProfile(img, sorgente, srgb, outputMode="RGB")
            icc = srgb.tobytes()
        else:
            avviso(f"{Path(percorso).name}: CMYK senza profilo, conversione approssimata dei colori")
            img = img.convert("RGB")
    elif img.mode in ("P", "LA", "PA") or "transparency" in img.info:
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    img.info = {}
    if icc:
        img.info["icc_profile"] = icc
    if dpi:
        img.info["dpi"] = dpi
    return img


def salva(img: Image.Image, percorso) -> Path:
    percorso = Path(percorso)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    ext = percorso.suffix.lower()
    extra = {k: img.info[k] for k in ("icc_profile",) if k in img.info}
    dpi = {"dpi": img.info["dpi"]} if "dpi" in img.info else {}

    if ext == ".png":
        img.save(percorso, "PNG", compress_level=6, **extra, **dpi)
    elif ext == ".webp":
        img.save(percorso, "WEBP", lossless=True, quality=100, method=6, exact=True, **extra)
    elif ext in (".tif", ".tiff"):
        img.save(percorso, "TIFF", compression="tiff_lzw", **extra, **dpi)
    elif ext in (".jpg", ".jpeg"):
        if img.mode == "RGBA":
            raise ValueError("il JPEG non supporta la trasparenza: usa .png o scegli un --sfondo")
        avviso(f"{percorso.name}: il JPEG comprime con perdita; salvo a qualità 100 senza sottocampionamento")
        img.save(percorso, "JPEG", quality=100, subsampling=0, **extra, **dpi)
    else:
        raise ValueError(f"formato di uscita non supportato: {ext}")
    return percorso


def colore(testo: str) -> tuple[int, int, int]:
    return ImageColor.getrgb(testo)[:3]


def ridimensiona(img: Image.Image, larghezza: int, altezza: int) -> Image.Image:
    """Lanczos. Con RGBA lavora ad alpha premoltiplicata per non creare aloni sui bordi."""
    if img.size == (larghezza, altezza):
        return img.copy()
    if img.mode == "RGBA":
        out = img.convert("RGBa").resize((larghezza, altezza), LANCZOS).convert("RGBA")
    else:
        out = img.resize((larghezza, altezza), LANCZOS)
    return _eredita(out, img)


def scala(img: Image.Image, fattore: float) -> Image.Image:
    """Scala proporzionale: lo stesso fattore su entrambi i lati."""
    w, h = img.size
    return ridimensiona(img, max(1, round(w * fattore)), max(1, round(h * fattore)))


def bbox_soggetto(img: Image.Image, soglia: int = 24) -> tuple[int, int, int, int] | None:
    """Riquadro del soggetto: pixel non trasparenti oppure diversi dal colore del bordo."""
    if img.mode == "RGBA":
        return img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    bordo = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    fondo = np.median(bordo, axis=0)
    diversi = np.abs(arr - fondo).max(axis=2) > soglia
    ys, xs = np.nonzero(diversi)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def unione_bbox(riquadri):
    riquadri = [b for b in riquadri if b]
    if not riquadri:
        return None
    return (
        min(b[0] for b in riquadri),
        min(b[1] for b in riquadri),
        max(b[2] for b in riquadri),
        max(b[3] for b in riquadri),
    )


def ritaglia_proporzione(img: Image.Image, rw: int, rh: int, centro=None) -> Image.Image:
    """Il ritaglio più grande con proporzione rw:rh, centrato sul soggetto. Nessun ricampionamento."""
    w, h = img.size
    if w * rh > h * rw:
        cw, ch = round(h * rw / rh), h
    else:
        cw, ch = w, round(w * rh / rw)
    if centro is None:
        box = bbox_soggetto(img)
        centro = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else (w / 2, h / 2)
    x = int(min(max(centro[0] - cw / 2, 0), w - cw))
    y = int(min(max(centro[1] - ch / 2, 0), h - ch))
    return _eredita(img.crop((x, y, x + cw, y + ch)), img)


def _tela(img: Image.Image, w: int, h: int, sfondo):
    if sfondo is None:
        modo = "RGBA" if img.mode == "RGBA" else "RGB"
        return Image.new(modo, (w, h), (0, 0, 0, 0) if modo == "RGBA" else (255, 255, 255))
    return Image.new("RGB", (w, h), colore(sfondo))


def adatta(
    img: Image.Image,
    larghezza: int,
    altezza: int,
    modo: str = "contieni",
    margine: float = 0.0,
    sfondo: str | None = None,
    riquadro=None,
) -> Image.Image:
    """Porta l'immagine a larghezza x altezza senza deformarla.

    - contieni: tutta l'immagine entra, lo spazio avanzato diventa sfondo
    - riempi:   copre tutta la tela, l'eccedenza viene ritagliata attorno al soggetto
    - soggetto: ritaglia sul soggetto, poi applica contieni con il margine
    `riquadro` fissa il ritaglio del soggetto; serve a inquadrare allo stesso modo
    tutti i fotogrammi di una rotazione a 360°.
    """
    if modo == "soggetto":
        box = riquadro or bbox_soggetto(img)
        if box:
            img = _eredita(img.crop(box), img)
        modo = "contieni"

    iw, ih = img.size
    if modo == "contieni":
        disp_w, disp_h = larghezza * (1 - 2 * margine), altezza * (1 - 2 * margine)
        f = min(disp_w / iw, disp_h / ih)
    elif modo == "riempi":
        f = max(larghezza / iw, altezza / ih)
    else:
        raise ValueError(f"modo sconosciuto: {modo}")

    if f > 1.001:
        avviso(f"ingrandimento x{f:.2f} con Lanczos: per più dettaglio passa prima da `upscale`")
    scalata = scala(img, f)

    if modo == "riempi":
        box = bbox_soggetto(scalata)
        centro = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) if box else None
        sw, sh = scalata.size
        cx, cy = centro or (sw / 2, sh / 2)
        x = int(min(max(cx - larghezza / 2, 0), sw - larghezza))
        y = int(min(max(cy - altezza / 2, 0), sh - altezza))
        out = scalata.crop((x, y, x + larghezza, y + altezza))
        if sfondo and out.mode == "RGBA":
            out = componi_su(out, Image.new("RGB", out.size, colore(sfondo)))
        return _eredita(out, img)

    tela = _tela(scalata, larghezza, altezza, sfondo)
    pos = ((larghezza - scalata.width) // 2, (altezza - scalata.height) // 2)
    if scalata.mode == "RGBA":
        if tela.mode == "RGBA":
            tela.paste(scalata, pos)
        else:
            tela = tela.convert("RGBA")
            tela.alpha_composite(scalata, pos)
            tela = tela.convert("RGB")
    else:
        tela.paste(scalata, pos)
    return _eredita(tela, img)


def applica_maschera(originale: Image.Image, maschera: Image.Image) -> Image.Image:
    """Pixel RGB originali più la maschera come canale alpha. Il colore del prodotto non cambia."""
    maschera = maschera.convert("L")
    if maschera.size != originale.size:
        maschera = maschera.resize(originale.size, LANCZOS)
    out = originale.convert("RGB")
    out.putalpha(maschera)
    return _eredita(out, originale)


def ombra(prodotto: Image.Image, opacita: float = 0.35, sfocatura: float = 0.015) -> Image.Image:
    """Ombra morbida ricavata dalla sagoma del prodotto e spostata leggermente in basso."""
    w, h = prodotto.size
    raggio = max(1, round(max(w, h) * sfocatura))
    alpha = prodotto.getchannel("A").point(lambda v: round(v * opacita))
    sagoma = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sagoma.putalpha(alpha)
    livello = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    livello.paste(sagoma, (0, raggio))
    return livello.filter(ImageFilter.GaussianBlur(raggio))


def componi_su(prodotto: Image.Image, sfondo: Image.Image, con_ombra: bool = False) -> Image.Image:
    """Mette il prodotto (RGBA) sopra lo sfondo; dove il prodotto è opaco i pixel restano quelli originali."""
    if sfondo.size != prodotto.size:
        raise ValueError("sfondo e prodotto devono avere la stessa dimensione")
    tela = sfondo.convert("RGBA")
    if con_ombra:
        tela.alpha_composite(ombra(prodotto))
    tela.alpha_composite(prodotto.convert("RGBA"))
    return _eredita(tela.convert("RGB"), prodotto)
