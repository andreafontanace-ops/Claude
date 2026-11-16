# Tornanti: negozio di tracce GPX e video dei passi

Questo repository contiene due progetti:

- **`site/`**: il negozio di tracce GPX (sito statico, pubblicato con GitHub Pages);
- **`src/`**: le animazioni Remotion dei passi (vedi più sotto).

## Negozio di tracce GPX

```
site/                     sito statico: index, pagine traccia, legali
  store.json              prezzi, tracce gratuite, link Gumroad  <- da modificare a mano
  data/rides.json         generato: statistiche, anteprime, profili
  tracks/*.gpx            generato: solo le tracce GRATUITE
  tracce/*.html           generato: una pagina per traccia
scripts/tracks/
  rides.json              ricette dei percorsi e testi       <- da modificare a mano
  fetch_roads.py          scarica la rete stradale (Overture Maps / OpenStreetMap)
  build_tracks.py         calcola percorsi, quote, GPX, dati del sito
scripts/site/build_pages.py  genera le pagine traccia, sitemap e robots.txt
private-tracks/           generato, ESCLUSO da git: GPX e zip a pagamento
```

Il repository è pubblico: i GPX a pagamento finiscono solo in `private-tracks/`
(ignorata da git) e vanno caricati su Gumroad, mai committati.

### Rigenerare le tracce

```bash
pip install -r scripts/tracks/requirements.txt
python scripts/tracks/fetch_roads.py      # una volta, circa 20 secondi
python scripts/tracks/build_tracks.py
python scripts/site/build_pages.py
```

Per aggiungere un giro: aggiungi una voce in `scripts/tracks/rides.json` (i punti
`via` costringono il percorso sulla strada del passo; `road` limita l'aggancio a
una strada con quel nome o numero), aggiungi il prodotto in `site/store.json` e
rilancia gli script. Se il giro è fuori dalle aree in `fetch_roads.py`, allarga
`REGIONS` e rilancia lo scaricamento con `--force`.

### Mettere in vendita su Gumroad

1. Crea un prodotto digitale per ogni traccia e pacchetto, con il prezzo di `store.json`.
2. Carica il file da `private-tracks/` (il `.gpx`, o lo `.zip` per i pacchetti).
3. Copia il link del prodotto nel campo `checkout` di `site/store.json`.

Un prodotto senza link appare sul sito come «In arrivo».

### Pubblicare il sito

Una sola volta: *Settings → Pages → Build and deployment → Source: GitHub Actions*.
Da lì ogni push su `main` che tocca `site/` ripubblica il sito
(`.github/workflows/pages.yml`). Con un dominio, metti l'indirizzo in `siteUrl`
di `store.json`: le pagine avranno la sitemap.

Anteprima in locale: `cd site && python3 -m http.server 8000`.

Dati stradali © OpenStreetMap contributors (ODbL), via Overture Maps.
Quote: SRTM via AWS Terrain Tiles. Mappa: Leaflet (BSD-2), in `site/vendor/`.

---

# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

Welcome to your Remotion project!

## Commands

**Install Dependencies**

```console
npm i
```

**Start Preview**

```console
npm run dev
```

**Render video**

```console
npx remotion render
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).
