# Immagini e-commerce con ComfyUI in locale

Strumento a riga di comando per preparare foto prodotto con **ComfyUI sul tuo PC**
(RTX 4080 Super, 16 GB). Le immagini non escono dal computer.

| Comando | A cosa serve |
|---|---|
| `estrai-pdf` | estrae i fotogrammi da PDF (per esempio rotazioni a 360°) alla risoluzione originale |
| `scontorna` | toglie lo sfondo e salva un PNG trasparente |
| `sfondo` | cambia lo sfondo: colore, immagine o sfondo generato dall'IA, con ombra facoltativa |
| `testo` | sostituisce un testo grafico con lo stesso font e lo stesso colore |
| `upscale` | ingrandisce 2x, 4x o altro con un modello di upscale |
| `formato` | ritagli e misure per i marketplace, senza schiacciare né allungare |
| `logo` | genera simboli e ci aggiunge il nome del marchio nel suo font |
| `controlla` | verifica ComfyUI, GPU, modelli installati e workflow |

## Le garanzie

- **Il prodotto non viene mai rigenerato.** L'IA calcola solo la maschera, lo sfondo
  o l'ingrandimento. Il risultato finale viene ricomposto con i pixel originali del
  prodotto, quindi etichette, scritte e loghi sul prodotto restano identici.
- **Nessuna deformazione.** Ogni ridimensionamento usa lo stesso fattore sui due lati.
  Quando la proporzione non coincide si aggiunge sfondo (`contieni`) o si ritaglia
  (`riempi`). `--proporzione` e `--box` ritagliano senza ricampionare.
- **Nessuna compressione con perdita.** L'uscita predefinita è PNG. In alternativa ci sono
  WebP lossless e TIFF LZW. Il JPEG si usa solo se lo chiedi, a qualità 100 e senza
  sottocampionamento. Il profilo colore ICC viene conservato e il CMYK viene
  convertito in sRGB tramite il suo profilo.
- **Solo locale.** Lo strumento rifiuta qualunque indirizzo di ComfyUI diverso da
  `127.0.0.1`/`localhost` e ignora i proxy di sistema. Le immagini vengono caricate
  nella cartella `temp` di ComfyUI, che ComfyUI svuota a ogni avvio. Anche le uscite
  finiscono lì, quindi nelle sue cartelle `input/` e `output/` non restano copie.
- **Niente immagini su Git.** `lavoro/`, le immagini, i PDF e i font sono in `.gitignore`.

## Installazione (Windows)

### 1. ComfyUI

1. Installa **ComfyUI Desktop** (comfy.org) oppure la versione *portable* per NVIDIA.
2. Lascialo in ascolto su `127.0.0.1` (è l'impostazione predefinita). **Non** avviarlo con
   `--listen` e non aprire la porta 8188 sul router.
3. Se usi ComfyUI Desktop, in *Impostazioni* disattiva l'invio delle statistiche d'uso.
4. Da **ComfyUI Manager** installa un custom node per lo scontorno con **BiRefNet**,
   per esempio *ComfyUI-RMBG* (scegli il modello BiRefNet) oppure *ComfyUI_BiRefNet_ll*.
   > RMBG-2.0 di BRIA ha una licenza **non commerciale**. Per un e-commerce usa
   > BiRefNet (licenza MIT) oppure acquista la licenza BRIA.
5. Scarica i modelli nelle cartelle di ComfyUI:

| Cartella | File | Usato da |
|---|---|---|
| `models/checkpoints` | `sd_xl_base_1.0.safetensors` | `logo`, `sfondo --prompt` |
| `models/checkpoints` (facoltativo) | un checkpoint SDXL *inpainting* | sfondi IA più puliti |
| `models/upscale_models` | `RealESRGAN_x4plus.pth` | `upscale` |

Puoi usare altri modelli: `--modello` sceglie il modello di upscale, oppure modifichi il
nome direttamente nei file in `workflows/`. **Verifica sempre la licenza per uso
commerciale:** alcuni modelli di upscale molto diffusi, come 4x-UltraSharp, hanno
licenze non commerciali.

### 2. Questo strumento

```powershell
cd ecommerce-immagini
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m ecom controlla
```

`controlla` mostra GPU, checkpoint e modelli di upscale trovati e fa una prova di
caricamento. Se la prova fallisce, usa `--cartella-upload input` oppure imposta la
variabile d'ambiente `ECOM_CARTELLA_UPLOAD=input`.

### 3. Workflow

I file in `workflows/` sono in **formato API** di ComfyUI. `upscale.json`, `logo.json`
e `sfondo_inpaint.json` usano solo nodi di base e sono già pronti.

**`rimuovi_sfondo.json` va creato una volta**, perché dipende dal custom node che hai installato:

1. In ComfyUI crea: `Load Image` → nodo BiRefNet/RMBG → (uscita **MASK**) → `Convert Mask to Image` → `Save Image`.
2. Provalo su una foto: devi vedere una sagoma bianca su fondo nero.
3. Menu *Workflow* → **Export (API)** → salva come `workflows/rimuovi_sfondo.json`.

Lo strumento prende solo la maschera e la applica ai pixel originali. Se la maschera
esce al contrario, la inverte da solo. In alternativa puoi evitare ComfyUI per lo
scontorno: `pip install "rembg[gpu]"` e poi `--motore rembg` (BiRefNet in locale sulla GPU).

Puoi usare anche workflow tuoi, per esempio Flux al posto di SDXL, con `--workflow percorso.json`.
Le regole sono queste:
- il nodo `Load Image` riceve automaticamente l'immagine;
- nei testi scrivi `{{PROMPT}}` e `{{NEGATIVO}}`, verranno sostituiti;
- `seed`/`noise_seed` e larghezza/altezza dei latenti vuoti vengono impostati dallo strumento;
- ogni `Save Image` diventa `Preview Image` (cartella temp).

## Uso

Metti i file in `lavoro/ingresso/`. I risultati finiscono in `lavoro/uscita/<comando>/`,
oppure nella cartella indicata con `--out`.

### Rotazione a 360° da PDF, scontornata e uniforme

```powershell
python -m ecom scontorna lavoro\ingresso\giro_360.pdf
python -m ecom formato lavoro\uscita\scontornate --dimensione 2000x2000 --sequenza --margine 0.05
```

`--sequenza` applica **lo stesso ritaglio a tutti i fotogrammi**, così nella rotazione il
prodotto non salta e non cambia misura. Senza `--sequenza` ogni foto viene centrata da sola.

Se il PDF contiene **un modello 3D interattivo** (U3D/PRC, quello che ruoti col mouse in
Acrobat), lo strumento te lo segnala. Il modello non contiene immagini da estrarre:
esporta le viste da Acrobat o dal programma 3D (per esempio 36 viste ogni 10°) e passa
quelle immagini.

### Cambiare sfondo

```powershell
python -m ecom sfondo lavoro\ingresso --colore "#FFFFFF" --ombra
python -m ecom sfondo lavoro\ingresso --immagine lavoro\ingresso\cucina.jpg --ombra
python -m ecom sfondo lavoro\ingresso --prompt "light oak table, soft daylight, blurred kitchen background" --ombra
```

Le immagini senza trasparenza vengono scontornate automaticamente. Con `--prompt`
l'IA genera solo lo sfondo, poi il prodotto originale viene rimesso sopra a piena risoluzione.

### Cambiare un testo (banner, prezzi, badge)

```powershell
python -m ecom testo banner.png --box 120,40,600,90 --testo "SALDI -50%" --font lavoro\font\Montserrat-Bold.ttf
```

- `--box x,y,larghezza,altezza` indica il riquadro in pixel. Lascia un po' di margine
  attorno al testo, perché il bordo del riquadro serve a riconoscere lo sfondo.
  Fuori dal riquadro non cambia nessun pixel.
- **Colore:** viene misurato sull'originale. Con `--colore "#C8102E"` lo imponi tu.
- **Font:** serve il file originale (.ttf/.otf). Chiedilo a chi ha fatto la grafica o
  cercalo nei sorgenti PSD/AI. Se devi identificarlo con siti come WhatTheFont, carica
  solo un ritaglio della scritta, perché quei siti ricevono l'immagine.
- **Dimensione:** viene calcolata in modo da non superare l'altezza del testo originale.
  `--dimensione`, `--allinea` e `--sposta dx,dy` servono per le rifiniture.
- **Sfondi:** su sfondi con texture o fotografici usa `--cancella ai`.
- **Scritte sul prodotto:** non selezionarle nel riquadro. Lo strumento non le tocca mai
  da solo.

### Upscale e formati per i marketplace

```powershell
python -m ecom upscale lavoro\ingresso --fattore 2
python -m ecom formato lavoro\uscita\upscale --dimensione 2000x2000 --modo soggetto --margine 0.075 --sfondo "#FFFFFF"
python -m ecom formato foto.png --proporzione 4:5
```

- `--modo contieni`: tutta l'immagine entra nella misura, il resto è sfondo.
- `--modo riempi`: copre tutta la misura e ritaglia il superfluo attorno al soggetto.
- `--modo soggetto` (predefinito): inquadra il prodotto con il margine richiesto.
- `--proporzione 1:1` o `--box`: solo ritaglio, nessun pixel ricalcolato.
- Se `formato` deve ingrandire, lo segnala: per ingrandimenti forti passa prima da `upscale`.
- Su scritte molto piccole i modelli di upscale possono ritoccare leggermente i
  contorni delle lettere: controlla il risultato, oppure usa `--motore lanczos`, che è
  puramente matematico e non inventa dettagli.

### Loghi

```powershell
python -m ecom logo --prompt "stylized mountain peak with a leaf" --quanti 6 --scritta "ALPE VERDE" --font lavoro\font\Brand.otf --colore "#1F4D2B"
```

L'IA disegna solo il simbolo (`*_bozza.png`). La scritta viene composta con il font
vero, perché i modelli di immagini sbagliano le lettere. I loghi escono come PNG
trasparenti. Per un logo definitivo vettoriale, vettorializza il simbolo scelto, per
esempio con Inkscape → *Vettorizza bitmap*.

## Usarlo con Claude Code senza esporre le immagini

- Usa Claude Code **sul tuo PC** (CLI o app desktop), non una sessione nel cloud:
  solo così può raggiungere ComfyUI su `127.0.0.1`.
- Claude può lanciare questi comandi e leggere i messaggi di testo. Le immagini le
  elabora ComfyUI in locale.
- Se chiedi a Claude di *guardare* un'immagine, quell'immagine viene inviata ad Anthropic.
  Per non esporre nulla, controlla tu i risultati.
- Controlla le impostazioni sulla privacy del tuo account Claude.

## Test

```powershell
pip install pytest
python -m pytest
```

I test usano un finto ComfyUI in memoria, quindi non serve la GPU.
