"""python -m ecom <comando> --help"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import operazioni as op
from . import testo as tx
from .comfy import ComfyUI, ErroreComfy, carica_workflow, prepara
from .immagini import ESTENSIONI, adatta, apri, avviso, bbox_soggetto, colore, ritaglia_proporzione, salva, unione_bbox
from .pdf import estrai

USCITA = Path("lavoro/uscita")


def _numeri(testo: str, sep: str, quanti: int) -> tuple[int, ...]:
    parti = [int(p) for p in testo.lower().replace(" ", "").split(sep)]
    if len(parti) != quanti:
        raise argparse.ArgumentTypeError(f"formato atteso con {quanti} numeri separati da '{sep}': {testo}")
    return tuple(parti)


def raccogli(percorsi, cartella_pdf: Path, dpi: int, modo_pdf: str = "auto") -> list[Path]:
    file = []
    for p in map(Path, percorsi):
        if p.is_dir():
            figli = sorted(p.iterdir())
            file += [f for f in figli if f.suffix.lower() in ESTENSIONI]
            for pdf in (f for f in figli if f.suffix.lower() == ".pdf"):
                file += estrai(pdf, cartella_pdf / pdf.stem, modo_pdf, dpi)
        elif p.suffix.lower() == ".pdf":
            file += estrai(p, cartella_pdf / p.stem, modo_pdf, dpi)
        elif p.suffix.lower() in ESTENSIONI and p.exists():
            file.append(p)
        else:
            avviso(f"ignoro {p}: non esiste o non è un'immagine/PDF")
    if not file:
        raise SystemExit("nessuna immagine da elaborare")
    return file


def client(args) -> ComfyUI:
    return ComfyUI(args.comfy, consenti_remoto=args.consenti_remoto, cartella_upload=args.cartella_upload)


def _uscita(args, comando: str, sorgente: Path, estensione: str | None = None) -> Path:
    cartella = Path(args.out) if args.out else USCITA / comando
    return cartella / f"{sorgente.stem}{estensione or '.' + args.formato}"


def _serve_scontorno(img, args, c=None):
    """Restituisce un RGBA: usa la trasparenza esistente o scontorna al momento."""
    if img.mode == "RGBA" and img.getchannel("A").getextrema()[0] < 255:
        return img
    wf = carica_workflow(args.workflow_scontorno) if args.motore == "comfy" else None
    return op.scontorna(img, args.motore, c or (client(args) if args.motore == "comfy" else None), wf)


# ---------------------------------------------------------------- comandi

def cmd_controlla(args):
    c = client(args)
    info = c.info_sistema()
    for d in info.get("devices", []):
        print(f"GPU: {d.get('name')}  VRAM {d.get('vram_total', 0) / 2**30:.1f} GB")
    print(f"ComfyUI {info.get('system', {}).get('comfyui_version', '?')} su {c.url}")
    print("checkpoint:", ", ".join(c.opzioni("CheckpointLoaderSimple", "ckpt_name")) or "nessuno")
    print("modelli upscale:", ", ".join(c.opzioni("UpscaleModelLoader", "model_name")) or "nessuno")

    from PIL import Image

    prova = Image.new("RGB", (64, 64), (200, 30, 30))
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
        "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": "ecom"}},
    }
    try:
        c.esegui(prepara(wf, immagine=c.carica(prova)))
        print(f"prova di caricamento nella cartella '{c.cartella_upload}': ok")
    except ErroreComfy as e:
        print(f"prova di caricamento nella cartella '{c.cartella_upload}' FALLITA: {e}")
        if c.cartella_upload == "temp":
            print("  riprova con --cartella-upload input (oppure ECOM_CARTELLA_UPLOAD=input)")
        sys.exit(1)

    for nome in ("rimuovi_sfondo", "upscale", "sfondo_inpaint", "logo"):
        try:
            carica_workflow(nome)
            print(f"workflow {nome}: presente")
        except ErroreComfy:
            print(f"workflow {nome}: MANCANTE (vedi README)")


def cmd_estrai_pdf(args):
    for pdf in args.pdf:
        cartella = Path(args.out) if args.out else USCITA / "pdf" / Path(pdf).stem
        usciti = estrai(pdf, cartella, args.modo, args.dpi)
        print(f"{pdf}: {len(usciti)} immagini in {cartella}")


def cmd_scontorna(args):
    file = raccogli(args.ingressi, USCITA / "pdf", args.dpi)
    c = client(args) if args.motore == "comfy" else None
    wf = carica_workflow(args.workflow_scontorno) if c else None
    for f in file:
        print(f"scontorno {f.name}")
        rgba = op.scontorna(apri(f), args.motore, c, wf, args.pulizia)
        salva(rgba, _uscita(args, "scontornate", f, ".png"))


def cmd_sfondo(args):
    file = raccogli(args.ingressi, USCITA / "pdf", args.dpi)
    c = client(args) if (args.motore == "comfy" or args.prompt) else None
    sfondo_img = apri(args.immagine) if args.immagine else None
    wf_ai = carica_workflow(args.workflow) if args.prompt else None
    for i, f in enumerate(file):
        print(f"sfondo {f.name}")
        prodotto = _serve_scontorno(apri(f), args, c)
        if args.colore:
            out = op.sfondo_colore(prodotto, colore(args.colore), args.ombra)
        elif sfondo_img is not None:
            out = op.sfondo_immagine(prodotto, sfondo_img, args.ombra)
        else:
            out = op.sfondo_ai(prodotto, c, wf_ai, args.prompt, args.negativo, args.seed + i, args.ombra)
        salva(out, _uscita(args, "sfondi", f))


def cmd_testo(args):
    img = apri(args.immagine)
    box = args.box
    analisi = tx.analizza(img, box, args.soglia)
    col = analisi.colore if args.colore == "auto" else colore(args.colore)
    if args.cancella == "ai":
        pulita = tx.cancella_ai(img, box, analisi, client(args), carica_workflow(args.workflow), args.prompt_cancella, args.seed)
    else:
        pulita = tx.cancella_opencv(img, box, analisi)
    out = tx.scrivi(pulita, box, args.testo, args.font, col, analisi, args.dimensione, args.allinea, args.sposta, args.variante)
    salva(out, _uscita(args, "testi", Path(args.immagine)))


def cmd_upscale(args):
    file = raccogli(args.ingressi, USCITA / "pdf", args.dpi)
    c = client(args) if args.motore == "comfy" else None
    wf = carica_workflow(args.workflow) if c else None
    for f in file:
        img = apri(f)
        print(f"upscale {f.name} {img.width}x{img.height} → x{args.fattore}")
        salva(op.upscale(img, args.fattore, args.motore, c, wf, args.modello), _uscita(args, "upscale", f))


def cmd_formato(args):
    file = raccogli(args.ingressi, USCITA / "pdf", args.dpi)
    immagini = [(f, apri(f)) for f in file]
    riquadro = None
    if args.sequenza:
        riquadro = unione_bbox(bbox_soggetto(img) for _, img in immagini)
        print(f"sequenza: stesso ritaglio {riquadro} per {len(immagini)} fotogrammi")
    for f, img in immagini:
        if args.box:
            x, y, w, h = args.box
            out = img.crop((x, y, x + w, y + h))
            out.info = img.info
        elif args.proporzione and not args.dimensione:
            out = ritaglia_proporzione(img, *args.proporzione)
        elif args.dimensione:
            out = adatta(img, *args.dimensione, args.modo, args.margine, args.sfondo, riquadro)
        else:
            raise SystemExit("indica --dimensione, --proporzione o --box")
        print(f"{f.name}: {img.width}x{img.height} → {out.width}x{out.height}")
        salva(out, _uscita(args, "formato", f))


def cmd_logo(args):
    c = client(args)
    simboli = op.genera_simboli(c, carica_workflow(args.workflow), args.prompt, args.negativo, args.quanti, args.seed)
    cartella = Path(args.out) if args.out else USCITA / "loghi"
    wf_sc = carica_workflow(args.workflow_scontorno) if (args.trasparente or args.scritta) and args.motore == "comfy" else None
    for i, simbolo in enumerate(simboli, 1):
        nome = f"logo_{args.seed + i - 1}"
        salva(simbolo, cartella / f"{nome}_bozza.png")
        if args.trasparente or args.scritta:
            simbolo = op.scontorna(simbolo, args.motore, c, wf_sc)
        if args.scritta:
            simbolo = op.aggiungi_scritta(simbolo, args.scritta, args.font, colore(args.colore), args.disposizione)
        salva(simbolo, cartella / f"{nome}.png")
        print(f"{nome}.png")


# ---------------------------------------------------------------- argomenti

def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m ecom", description="Immagini e-commerce con ComfyUI in locale")
    p.add_argument("--comfy", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    p.add_argument("--consenti-remoto", action="store_true", help="permette un ComfyUI non locale (sconsigliato)")
    p.add_argument("--cartella-upload", default=os.environ.get("ECOM_CARTELLA_UPLOAD", "temp"), choices=["temp", "input"])
    sub = p.add_subparsers(dest="comando", required=True)

    def comune(sp, formato="png", motore=False):
        sp.add_argument("--out", help="cartella di uscita (predefinita: lavoro/uscita/<comando>)")
        sp.add_argument("--formato", default=formato, choices=["png", "webp", "tif", "jpg"])
        sp.add_argument("--dpi", type=int, default=400, help="DPI per renderizzare le pagine PDF senza immagini")
        if motore:
            sp.add_argument("--motore", default="comfy", choices=["comfy", "rembg"], help="motore di scontorno")
            sp.add_argument("--workflow-scontorno", default="rimuovi_sfondo")

    sp = sub.add_parser("controlla", help="verifica ComfyUI, GPU, modelli e workflow")
    sp.set_defaults(fn=cmd_controlla)

    sp = sub.add_parser("estrai-pdf", help="estrae le immagini (o renderizza le pagine) dai PDF")
    sp.add_argument("pdf", nargs="+")
    sp.add_argument("--modo", default="auto", choices=["auto", "immagini", "pagine"])
    sp.add_argument("--dpi", type=int, default=400)
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_estrai_pdf)

    sp = sub.add_parser("scontorna", help="toglie lo sfondo (PNG trasparente, pixel originali)")
    sp.add_argument("ingressi", nargs="+", help="immagini, cartelle o PDF")
    comune(sp, motore=True)
    sp.add_argument("--pulizia", type=int, default=0, help="0-255: elimina gli aloni semi-trasparenti sotto la soglia")
    sp.set_defaults(fn=cmd_scontorna)

    sp = sub.add_parser("sfondo", help="cambia lo sfondo: colore, immagine o generato con l'IA")
    sp.add_argument("ingressi", nargs="+")
    comune(sp, motore=True)
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--colore", help="es. '#FFFFFF'")
    g.add_argument("--immagine", help="immagine di sfondo (riempie senza deformare)")
    g.add_argument("--prompt", help="descrizione dello sfondo da generare")
    sp.add_argument("--negativo", default="product, text, watermark, people, blurry")
    sp.add_argument("--seed", type=int, default=1)
    sp.add_argument("--ombra", action="store_true", help="aggiunge un'ombra morbida sotto il prodotto")
    sp.add_argument("--workflow", default="sfondo_inpaint")
    sp.set_defaults(fn=cmd_sfondo)

    sp = sub.add_parser("testo", help="sostituisce un testo grafico dentro un riquadro")
    sp.add_argument("immagine")
    sp.add_argument("--box", required=True, type=lambda s: _numeri(s, ",", 4), help="x,y,larghezza,altezza in pixel")
    sp.add_argument("--testo", required=True)
    sp.add_argument("--font", required=True, help="file .ttf/.otf del font originale")
    sp.add_argument("--variante", help="per i font variabili, es. 'Bold'")
    sp.add_argument("--colore", default="auto", help="'auto' misura il colore originale, oppure '#RRGGBB'")
    sp.add_argument("--dimensione", type=int, help="dimensione in pixel (predefinita: uguale all'originale)")
    sp.add_argument("--allinea", default="centro", choices=["sinistra", "centro", "destra"])
    sp.add_argument("--sposta", type=lambda s: _numeri(s, ",", 2), default=(0, 0), help="correzione dx,dy in pixel")
    sp.add_argument("--soglia", type=int, default=60, help="sensibilità nel distinguere testo e sfondo")
    sp.add_argument("--cancella", default="opencv", choices=["opencv", "ai"], help="ai per sfondi con texture")
    sp.add_argument("--prompt-cancella", default="clean background, seamless texture")
    sp.add_argument("--seed", type=int, default=1)
    sp.add_argument("--workflow", default="sfondo_inpaint")
    sp.add_argument("--out")
    sp.add_argument("--formato", default="png", choices=["png", "webp", "tif", "jpg"])
    sp.set_defaults(fn=cmd_testo)

    sp = sub.add_parser("upscale", help="ingrandisce senza deformare")
    sp.add_argument("ingressi", nargs="+")
    comune(sp)
    sp.add_argument("--fattore", type=float, default=2)
    sp.add_argument("--motore", default="comfy", choices=["comfy", "lanczos"])
    sp.add_argument("--modello", help="file del modello in models/upscale_models")
    sp.add_argument("--workflow", default="upscale")
    sp.set_defaults(fn=cmd_upscale)

    sp = sub.add_parser("formato", help="ritagli e misure per i marketplace, senza deformare")
    sp.add_argument("ingressi", nargs="+")
    comune(sp)
    sp.add_argument("--dimensione", type=lambda s: _numeri(s, "x", 2), help="es. 2000x2000")
    sp.add_argument("--modo", default="soggetto", choices=["contieni", "riempi", "soggetto"])
    sp.add_argument("--margine", type=float, default=0.05, help="spazio attorno al soggetto (0.05 = 5%% per lato)")
    sp.add_argument("--sfondo", help="colore della tela, es. '#FFFFFF' (predefinito: trasparente o bianco)")
    sp.add_argument("--proporzione", type=lambda s: _numeri(s, ":", 2), help="solo ritaglio, es. 4:5 (nessun ricampionamento)")
    sp.add_argument("--box", type=lambda s: _numeri(s, ",", 4), help="ritaglio esatto x,y,larghezza,altezza")
    sp.add_argument("--sequenza", action="store_true", help="stesso ritaglio per tutti i fotogrammi (rotazioni 360°)")
    sp.set_defaults(fn=cmd_formato)

    sp = sub.add_parser("logo", help="genera simboli e compone la scritta con il font del marchio")
    sp.add_argument("--prompt", required=True, help="descrizione del simbolo, es. 'stylized mountain and leaf'")
    sp.add_argument("--negativo", default="")
    sp.add_argument("--quanti", type=int, default=4)
    sp.add_argument("--seed", type=int, default=1)
    sp.add_argument("--scritta", help="nome del marchio da aggiungere")
    sp.add_argument("--font", help="font del marchio (.ttf/.otf), obbligatorio con --scritta")
    sp.add_argument("--colore", default="#111111")
    sp.add_argument("--disposizione", default="sotto", choices=["sotto", "destra"])
    sp.add_argument("--trasparente", action="store_true")
    sp.add_argument("--motore", default="comfy", choices=["comfy", "rembg"])
    sp.add_argument("--workflow-scontorno", default="rimuovi_sfondo")
    sp.add_argument("--workflow", default="logo")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_logo)

    args = p.parse_args(argv)
    if args.comando == "logo" and args.scritta and not args.font:
        p.error("--scritta richiede --font")
    try:
        args.fn(args)
    except (ErroreComfy, ValueError) as e:
        raise SystemExit(f"errore: {e}")


if __name__ == "__main__":
    main()
