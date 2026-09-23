"""Client per l'API di ComfyUI, limitato di proposito all'uso in locale.

- Rifiuta indirizzi che non siano del computer stesso (127.0.0.1, localhost, ::1),
  a meno che venga passato consenti_remoto=True.
- Ignora i proxy di sistema: le immagini vanno direttamente a ComfyUI.
- Carica le immagini nella cartella temp di ComfyUI e trasforma ogni SaveImage
  in PreviewImage. ComfyUI svuota la cartella temp a ogni avvio, quindi non
  restano copie nelle sue cartelle input/ e output/.
"""

from __future__ import annotations

import copy
import io
import ipaddress
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

CARTELLA_WORKFLOW = Path(__file__).resolve().parent.parent / "workflows"


class ErroreComfy(RuntimeError):
    pass


def _locale(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ComfyUI:
    def __init__(
        self,
        url: str = "http://127.0.0.1:8188",
        consenti_remoto: bool = False,
        cartella_upload: str = "temp",
        timeout: float = 1800,
    ):
        host = urlparse(url).hostname or ""
        if not _locale(host) and not consenti_remoto:
            raise ErroreComfy(
                f"{url} non è un indirizzo locale. Per proteggere le immagini lo strumento "
                "parla solo con ComfyUI sullo stesso computer (127.0.0.1). "
                "Se sai cosa stai facendo usa --consenti-remoto."
            )
        if cartella_upload not in ("temp", "input"):
            raise ErroreComfy("cartella_upload deve essere 'temp' o 'input'")
        self.url = url.rstrip("/")
        self.cartella_upload = cartella_upload
        self.timeout = timeout
        self.http = requests.Session()
        self.http.trust_env = False

    def _get(self, percorso: str, **kw):
        try:
            r = self.http.get(f"{self.url}{percorso}", timeout=30, **kw)
        except requests.RequestException as e:
            raise ErroreComfy(f"ComfyUI non risponde su {self.url}: è avviato?") from e
        r.raise_for_status()
        return r

    def info_sistema(self) -> dict:
        return self._get("/system_stats").json()

    def opzioni(self, nodo: str, ingresso: str) -> list[str]:
        """Valori ammessi per un ingresso a scelta, per esempio i modelli installati."""
        dati = self._get(f"/object_info/{nodo}").json().get(nodo, {})
        spec = dati.get("input", {}).get("required", {}).get(ingresso)
        if not spec:
            return []
        if isinstance(spec[0], list):
            return spec[0]
        return spec[1].get("options", []) if len(spec) > 1 and isinstance(spec[1], dict) else []

    def carica(self, img: Image.Image) -> str:
        """Carica un'immagine e restituisce il nome da mettere nel nodo LoadImage."""
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)
        buf.seek(0)
        nome = f"ecom_{uuid.uuid4().hex}.png"
        try:
            r = self.http.post(
                f"{self.url}/upload/image",
                files={"image": (nome, buf, "image/png")},
                data={"type": self.cartella_upload, "overwrite": "true"},
                timeout=120,
            )
        except requests.RequestException as e:
            raise ErroreComfy(f"ComfyUI non risponde su {self.url}: è avviato?") from e
        r.raise_for_status()
        info = r.json()
        rif = f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]
        return rif if self.cartella_upload == "input" else f"{rif} [{self.cartella_upload}]"

    def esegui(self, workflow: dict) -> list[Image.Image]:
        """Accoda il workflow, attende la fine e restituisce le immagini in uscita, in ordine di nodo."""
        try:
            r = self.http.post(
                f"{self.url}/prompt",
                json={"prompt": workflow, "client_id": uuid.uuid4().hex},
                timeout=60,
            )
        except requests.RequestException as e:
            raise ErroreComfy(f"ComfyUI non risponde su {self.url}: è avviato?") from e
        if r.status_code != 200:
            raise ErroreComfy(_descrivi_rifiuto(r))
        id_prompt = r.json()["prompt_id"]

        scadenza = time.monotonic() + self.timeout
        while True:
            storia = self._get(f"/history/{id_prompt}").json()
            if id_prompt in storia:
                break
            if time.monotonic() > scadenza:
                raise ErroreComfy(f"ComfyUI non ha finito entro {self.timeout:.0f} s")
            time.sleep(0.5)

        voce = storia[id_prompt]
        stato = voce.get("status", {})
        if stato.get("status_str") == "error":
            raise ErroreComfy(_descrivi_errore(stato))

        immagini = []
        uscite = voce.get("outputs", {})
        for id_nodo in sorted(uscite, key=lambda n: (0, int(n), "") if n.isdigit() else (1, 0, n)):
            for im in uscite[id_nodo].get("images", []):
                dati = self._get(
                    "/view",
                    params={
                        "filename": im["filename"],
                        "subfolder": im.get("subfolder", ""),
                        "type": im.get("type", "output"),
                    },
                ).content
                img = Image.open(io.BytesIO(dati))
                img.load()
                immagini.append(img)
        if not immagini:
            raise ErroreComfy("il workflow non ha prodotto immagini: manca un nodo Save/Preview Image?")
        return immagini


def _descrivi_rifiuto(r) -> str:
    try:
        dati = r.json()
    except ValueError:
        return f"ComfyUI ha rifiutato il workflow (HTTP {r.status_code}): {r.text[:500]}"
    righe = [f"ComfyUI ha rifiutato il workflow: {dati.get('error', {}).get('message', '')}"]
    for id_nodo, err in (dati.get("node_errors") or {}).items():
        for e in err.get("errors", []):
            righe.append(f"  nodo {id_nodo} ({err.get('class_type')}): {e.get('message')} {e.get('details', '')}")
    if any("not in list" in r_ for r_ in righe):
        righe.append("  → un modello o un file indicato nel workflow non è installato: `python -m ecom controlla` elenca quelli presenti.")
    if any("does not exist" in r_ or "not found" in r_.lower() for r_ in righe):
        righe.append("  → manca un custom node: installalo da ComfyUI Manager e riavvia ComfyUI.")
    return "\n".join(righe)


def _descrivi_errore(stato: dict) -> str:
    for evento, dati in stato.get("messages", []):
        if evento == "execution_error":
            return f"errore nel nodo {dati.get('node_type')}: {dati.get('exception_message', '').strip()}"
    return "ComfyUI ha segnalato un errore durante l'esecuzione"


def carica_workflow(nome_o_percorso: str) -> dict:
    percorso = Path(nome_o_percorso)
    if not percorso.suffix:
        percorso = CARTELLA_WORKFLOW / f"{nome_o_percorso}.json"
    if not percorso.exists():
        raise ErroreComfy(
            f"workflow non trovato: {percorso}. Crealo in ComfyUI ed esportalo in formato API "
            "(vedi README, sezione «Workflow»)."
        )
    return json.loads(percorso.read_text(encoding="utf-8"))


def prepara(
    workflow: dict,
    *,
    immagine: str | None = None,
    testi: dict[str, str] | None = None,
    seed: int | None = None,
    larghezza: int | None = None,
    altezza: int | None = None,
    parametri: dict[str, dict] | None = None,
) -> dict:
    """Compila un workflow in formato API.

    - ogni LoadImage riceve `immagine`
    - i segnaposto {{NOME}} nei testi vengono sostituiti con `testi[NOME]`
    - `seed`/`noise_seed`, e larghezza/altezza dei latenti vuoti, se indicati
    - `parametri` = {class_type: {ingresso: valore}} per esempio il nome di un modello
    - SaveImage diventa PreviewImage (uscita nella cartella temp)
    """
    if "nodes" in workflow and "links" in workflow:
        raise ErroreComfy(
            "questo workflow è nel formato dell'interfaccia. In ComfyUI usa "
            "Workflow → Export (API) e salva quel file."
        )
    wf = copy.deepcopy(workflow)
    trovato_load = False
    for nodo in wf.values():
        tipo = nodo.get("class_type")
        ingressi = nodo.setdefault("inputs", {})
        if tipo == "LoadImage":
            trovato_load = True
            if immagine is not None:
                ingressi["image"] = immagine
        if tipo == "SaveImage":
            nodo["class_type"] = "PreviewImage"
            ingressi.pop("filename_prefix", None)
        if tipo in ("EmptyLatentImage", "EmptySD3LatentImage"):
            if larghezza:
                ingressi["width"] = larghezza
            if altezza:
                ingressi["height"] = altezza
        if parametri and tipo in parametri:
            ingressi.update(parametri[tipo])
        for chiave, valore in list(ingressi.items()):
            if isinstance(valore, str) and testi:
                for segnaposto, testo in testi.items():
                    valore = valore.replace("{{" + segnaposto + "}}", testo)
                ingressi[chiave] = valore
            if seed is not None and chiave in ("seed", "noise_seed") and not isinstance(valore, list):
                ingressi[chiave] = seed

    if immagine is not None and not trovato_load:
        raise ErroreComfy("il workflow non ha un nodo Load Image a cui dare l'immagine")
    residui = [v for n in wf.values() for v in n["inputs"].values() if isinstance(v, str) and "{{" in v]
    if residui:
        raise ErroreComfy(f"segnaposto non compilati nel workflow: {residui}")
    return wf
