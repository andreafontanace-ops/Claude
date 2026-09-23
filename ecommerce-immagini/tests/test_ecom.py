import numpy as np
import pymupdf
import pytest
from PIL import Image

from ecom import operazioni as op
from ecom import testo as tx
from ecom.comfy import ComfyUI, ErroreComfy, carica_workflow, prepara
from ecom.immagini import adatta, apri, bbox_soggetto, ritaglia_proporzione, salva
from ecom.pdf import estrai

FINTO_RMBG = {
    "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
    "2": {"class_type": "FintoRMBG", "inputs": {"image": ["1", 0]}},
    "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "x"}},
}


def test_rifiuta_comfy_non_locale():
    with pytest.raises(ErroreComfy):
        ComfyUI("http://192.168.1.20:8188")
    with pytest.raises(ErroreComfy):
        ComfyUI("https://mio-tunnel.example.com")
    ComfyUI("http://localhost:8188")
    ComfyUI("http://[::1]:8188")


def test_prepara_compila_e_usa_preview():
    wf = prepara(carica_workflow("logo"), testi={"PROMPT": "a", "NEGATIVO": "b"}, seed=7, larghezza=512, altezza=768)
    assert wf["2"]["inputs"]["text"] == "a" and wf["3"]["inputs"]["text"] == "b"
    assert wf["5"]["inputs"]["seed"] == 7
    assert (wf["4"]["inputs"]["width"], wf["4"]["inputs"]["height"]) == (512, 768)
    assert wf["7"]["class_type"] == "PreviewImage" and "filename_prefix" not in wf["7"]["inputs"]
    with pytest.raises(ErroreComfy):
        prepara(carica_workflow("logo"))  # segnaposto non compilati
    with pytest.raises(ErroreComfy):
        prepara({"nodes": [], "links": []})


def test_scontorno_conserva_i_pixel(finto_comfy, prodotto):
    c = ComfyUI(finto_comfy.url)
    rgba = op.scontorna(prodotto, "comfy", c, FINTO_RMBG)
    assert finto_comfy.upload_type == ["temp"]
    assert finto_comfy.prompt_ricevuti[0]["1"]["inputs"]["image"].endswith(" [temp]")
    a = np.asarray(rgba)
    assert a[0, 0, 3] == 0 and a[150, 200, 3] == 255
    assert (a[..., :3] == np.asarray(prodotto)).all()


def test_sfondo_ai_non_tocca_il_prodotto(finto_comfy, prodotto):
    c = ComfyUI(finto_comfy.url)
    rgba = op.scontorna(prodotto, "comfy", c, FINTO_RMBG)
    out = op.sfondo_ai(rgba, c, carica_workflow("sfondo_inpaint"), "marble table")
    a, o = np.asarray(out), np.asarray(prodotto)
    assert out.size == prodotto.size
    assert (a[50:250, 100:300] == o[50:250, 100:300]).all()
    assert tuple(a[5, 5]) == (10, 200, 10)
    # l'immagine mandata all'IA ha lati multipli di 8
    wf = finto_comfy.prompt_ricevuti[-1]
    assert wf["3"]["inputs"]["text"] == "marble table"


def test_upscale_proporzionale_con_alpha(finto_comfy, prodotto):
    c = ComfyUI(finto_comfy.url)
    rgba = op.scontorna(prodotto, "comfy", c, FINTO_RMBG)
    out = op.upscale(rgba, 2, "comfy", c, carica_workflow("upscale"), "altro.pth")
    assert out.size == (800, 600) and out.mode == "RGBA"
    assert finto_comfy.prompt_ricevuti[-1]["2"]["inputs"]["model_name"] == "altro.pth"
    assert op.upscale(prodotto, 3, "lanczos").size == (1200, 900)


def test_adatta_non_deforma(prodotto):
    for modo in ("contieni", "riempi", "soggetto"):
        out = adatta(prodotto, 1000, 1000, modo, margine=0.05)
        assert out.size == (1000, 1000)
    # soggetto 200x200 con margine 5% → 900x900, quadrato come l'originale
    out = adatta(prodotto, 1000, 1000, "soggetto", margine=0.05)
    x0, y0, x1, y1 = bbox_soggetto(out)
    assert (x1 - x0, y1 - y0) == (900, 900)
    r = ritaglia_proporzione(prodotto, 1, 1)
    assert r.size == (300, 300)
    assert (np.asarray(r) == np.asarray(prodotto)[:, 50:350]).all()


def test_salvataggio_senza_perdita(tmp_path, prodotto):
    for ext in (".png", ".webp", ".tif"):
        p = salva(prodotto, tmp_path / f"x{ext}")
        assert (np.asarray(apri(p)) == np.asarray(prodotto)).all()
    with pytest.raises(ValueError):
        salva(prodotto.convert("RGBA"), tmp_path / "x.jpg")


def test_pdf_estrae_immagini_originali(tmp_path, prodotto):
    frames = []
    doc = pymupdf.open()
    for i in range(3):
        f = prodotto.rotate(i * 10, fillcolor="white")
        p = tmp_path / f"f{i}.png"
        f.save(p)
        frames.append(f)
        pagina = doc.new_page()
        pagina.insert_image(pagina.rect, filename=str(p))
    doc.save(tmp_path / "giro.pdf")
    usciti = estrai(tmp_path / "giro.pdf", tmp_path / "out")
    assert len(usciti) == 3
    for u, f in zip(usciti, frames):
        assert (np.asarray(apri(u)) == np.asarray(f)).all()
    pagine = estrai(tmp_path / "giro.pdf", tmp_path / "pag", "pagine", dpi=72)
    assert len(pagine) == 3


def _font():
    import glob

    candidati = glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)
    if not candidati:
        pytest.skip("font di prova non disponibile")
    return candidati[0]


def test_testo_colore_e_area(prodotto):
    font = _font()
    img = Image.new("RGB", (600, 200), (240, 230, 200))
    from PIL import ImageDraw

    from ecom.testo import carica_font

    ImageDraw.Draw(img).text((50, 60), "SALDI 30%", font=carica_font(font, 60), fill=(200, 30, 60))
    img.paste((0, 0, 0), (500, 20, 580, 180))  # "prodotto" fuori dal riquadro
    box = (30, 40, 400, 110)
    a = tx.analizza(img, box)
    assert all(abs(x - y) <= 6 for x, y in zip(a.colore, (200, 30, 60)))
    out = tx.scrivi(tx.cancella_opencv(img, box, a), box, "SALDI 50%", font, a.colore, a)
    o, i = np.asarray(out), np.asarray(img)
    # fuori dal riquadro nulla cambia
    fuori = np.ones(o.shape[:2], bool)
    fuori[40:150, 30:430] = False
    assert (o[fuori] == i[fuori]).all()
    assert not (o[40:150, 30:430] == i[40:150, 30:430]).all()


def test_logo_con_scritta(finto_comfy):
    c = ComfyUI(finto_comfy.url)
    simboli = op.genera_simboli(c, carica_workflow("logo"), "mountain", "", 2, 5)
    assert [w["5"]["inputs"]["seed"] for w in finto_comfy.prompt_ricevuti] == [5, 6]
    simbolo = op.scontorna(simboli[0], "comfy", c, FINTO_RMBG)
    logo = op.aggiungi_scritta(simbolo, "ALPI", _font(), (17, 17, 17))
    assert logo.mode == "RGBA" and logo.height > 400
