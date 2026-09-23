"""Estrae le immagini dai PDF, per esempio i fotogrammi di una rotazione a 360°.

Prima prova a estrarre le immagini incorporate alla loro risoluzione originale
(JPEG e PNG vengono copiati byte per byte, senza ricomprimerli). Se non ne
trova, renderizza le pagine al DPI richiesto.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from .immagini import avviso

LATO_MINIMO = 64  # sotto questa misura sono icone, maschere o decorazioni


def estrai(pdf, cartella, modo: str = "auto", dpi: int = 400) -> list[Path]:
    pdf, cartella = Path(pdf), Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf) as doc:
        _avvisa_3d(doc, pdf.name)
        if modo in ("auto", "immagini"):
            usciti = _incorporate(doc, cartella)
            if usciti or modo == "immagini":
                return usciti
            avviso(f"{pdf.name}: nessuna immagine incorporata, renderizzo le pagine a {dpi} DPI")
        return _pagine(doc, cartella, dpi)


def _avvisa_3d(doc, nome: str) -> None:
    for pagina in doc:
        for annot in pagina.annots() or []:
            if annot.type[0] == pymupdf.PDF_ANNOT_3D:
                avviso(
                    f"{nome}, pagina {pagina.number + 1}: contiene un modello 3D interattivo (U3D/PRC). "
                    "Il modello non si può estrarre come immagini: esporta le viste da Acrobat "
                    "o dal programma 3D, poi passa qui le immagini. Estraggo solo l'anteprima statica."
                )
                return


def _incorporate(doc, cartella: Path) -> list[Path]:
    usciti, visti = [], set()
    for pagina in doc:
        for info in pagina.get_images(full=True):
            xref, smask, larghezza, altezza = info[0], info[1], info[2], info[3]
            if xref in visti or min(larghezza, altezza) < LATO_MINIMO:
                continue
            visti.add(xref)
            base = cartella / f"p{pagina.number + 1:03d}_img{len(visti):03d}"

            dati = doc.extract_image(xref)
            if dati and smask == 0 and dati["ext"] in ("jpeg", "png"):
                destinazione = base.with_suffix(".jpg" if dati["ext"] == "jpeg" else ".png")
                destinazione.write_bytes(dati["image"])
                usciti.append(destinazione)
                continue

            pix = pymupdf.Pixmap(doc, xref)
            if pix.colorspace and pix.colorspace.n == 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if smask:
                pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))
            destinazione = base.with_suffix(".png")
            pix.save(destinazione)
            usciti.append(destinazione)
    return usciti


def _pagine(doc, cartella: Path, dpi: int) -> list[Path]:
    usciti = []
    for pagina in doc:
        pix = pagina.get_pixmap(dpi=dpi, alpha=False, colorspace=pymupdf.csRGB)
        destinazione = cartella / f"pagina{pagina.number + 1:03d}.png"
        pix.save(destinazione)
        usciti.append(destinazione)
    return usciti
