# media/input — cartella di scambio video

Cartella condivisa per passare a Claude i video su cui lavorare
(analisi delle scene, stesura dello speakeraggio, estrazione fotogrammi).

Claude gira in un container in cloud e non vede il disco locale:
il repository e' l'unico punto di contatto tra le due parti.

## Come caricare un video

    git checkout claude/inspiring-johnson-b80oic
    git pull origin claude/inspiring-johnson-b80oic
    cp /percorso/del/tuo/video.mp4 media/input/
    git add media/input/video.mp4
    git commit -m "Aggiunge video per speakeraggio"
    git push origin claude/inspiring-johnson-b80oic

Poi avvisa Claude in chat: fara' il pull, estrarra' i fotogrammi e lavorera' su quelli.

## Limiti di dimensione

GitHub rifiuta i file oltre i 100 MB e segnala un avviso oltre i 50 MB.
Se il video supera questa soglia va alleggerito prima del commit: per
analizzare le scene non serve la qualita' originale.

    ffmpeg -i originale.mp4 -vf "scale=-2:480,fps=8" -c:v libx264 -crf 32 -an media/input/anteprima.mp4

Un video di pochi minuti scende cosi' sotto i 5 MB, restando piu' che
leggibile per capire cosa succede a schermo.

In alternativa, bastano 10-15 fotogrammi dei momenti chiave, con il
minutaggio nel nome del file (`00-04.png`, `00-11.png`, ...).

## Nota

I file video restano nella storia del repository anche dopo la
cancellazione. Non caricare qui materiale riservato, e ripulisci la
cartella quando il lavoro e' concluso.
