"""Un finto ComfyUI in memoria che imita /upload/image, /prompt, /history e /view."""

import io
import json
import re
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _esegui(wf, file):
    """Simula i pochi nodi usati dai workflow di prova."""
    tipi = {n["class_type"] for n in wf.values()}
    load = next(n for n in wf.values() if n["class_type"] == "LoadImage") if "LoadImage" in tipi else None
    img = None
    if load:
        nome = load["inputs"]["image"].removesuffix(" [temp]")
        img = Image.open(io.BytesIO(file[nome]))
    if "ImageUpscaleWithModel" in tipi:
        img = img.convert("RGB").resize((img.width * 4, img.height * 4))
    elif "FintoRMBG" in tipi:
        # prodotto = pixel non bianchi
        img = img.convert("L").point(lambda v: 0 if v > 240 else 255)
    elif "VAEEncodeForInpaint" in tipi:
        img = Image.new("RGB", img.size, (10, 200, 10))
    elif "EmptyLatentImage" in tipi:
        lat = next(n for n in wf.values() if n["class_type"] == "EmptyLatentImage")["inputs"]
        img = Image.new("RGB", (lat["width"], lat["height"]), (255, 255, 255))
        img.paste((200, 0, 0), (300, 300, 700, 700))
    return img


class FintoComfy:
    def __init__(self):
        self.file, self.storia, self.prompt_ricevuti, self.upload_type = {}, {}, [], []
        stato = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, dati, codice=200):
                corpo = json.dumps(dati).encode()
                self.send_response(codice)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):
                u = urlparse(self.path)
                if u.path == "/system_stats":
                    return self._json({"system": {"comfyui_version": "finto"}, "devices": []})
                if u.path.startswith("/history/"):
                    pid = u.path.split("/")[-1]
                    return self._json({pid: stato.storia[pid]} if pid in stato.storia else {})
                if u.path == "/view":
                    q = parse_qs(u.query)
                    corpo = stato.file[q["filename"][0]]
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(corpo)))
                    self.end_headers()
                    return self.wfile.write(corpo)
                if u.path.startswith("/object_info/"):
                    return self._json({})
                self._json({}, 404)

            def do_POST(self):
                corpo = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path == "/upload/image":
                    nome = re.search(rb'filename="([^"]+)"', corpo).group(1).decode()
                    tipo = re.search(rb'name="type"\r\n\r\n(\w+)', corpo).group(1).decode()
                    inizio = corpo.index(b"\x89PNG")
                    fine = corpo.rindex(b"IEND") + 8
                    stato.file[nome] = corpo[inizio:fine]
                    stato.upload_type.append(tipo)
                    return self._json({"name": nome, "subfolder": "", "type": tipo})
                if self.path == "/prompt":
                    wf = json.loads(corpo)["prompt"]
                    stato.prompt_ricevuti.append(wf)
                    pid = uuid.uuid4().hex
                    img = _esegui(wf, stato.file)
                    buf = io.BytesIO()
                    img.save(buf, "PNG")
                    nome = f"out_{pid}.png"
                    stato.file[nome] = buf.getvalue()
                    stato.storia[pid] = {
                        "status": {"status_str": "success", "messages": []},
                        "outputs": {"9": {"images": [{"filename": nome, "subfolder": "", "type": "temp"}]}},
                    }
                    return self._json({"prompt_id": pid})
                self._json({}, 404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def finto_comfy():
    f = FintoComfy()
    yield f
    f.server.shutdown()


@pytest.fixture
def prodotto():
    """Un 'prodotto' rosso con una scritta blu su sfondo bianco."""
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    img.paste((180, 20, 20), (100, 50, 300, 250))
    img.paste((20, 20, 180), (150, 120, 250, 140))
    return img
