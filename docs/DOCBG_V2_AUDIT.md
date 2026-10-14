# Chronon3D — Documentary Background Quality 2.0: audit dei 15 MP4/plate attuali.
# Data: 2026-10-14. Strumento: PIL+numpy+ffmpeg su plate PNG e MP4 esistenti.

## Metodo
# - plate PNG in ChrononTemplate/catalog/minimal_documentary_backgrounds/assets/
# - MP4 in .../out/ (1920x1080 30fps 8s verificati)
# - metriche: media luminanza centro vs angoli, picco gradiente verticale (seam),
#   MSE thumbnail 96x54 (duplicazione), meanabs primo/ultimo frame a 480x270 (moto).

## Misure (riproducibili, vedi log agente)
# - center-corner (c-c): 05_warm=+66.4, 14_olive=+54.2, 03_archival=+55.6
#   -> vignetta pesante / spotlight centrale, non luce naturale (D01).
# - seam ratio (picco/mediana gradiente colonne): 03_archival=10.7 @x=1409
#   (graffio verticale a tutta altezza), 06_ivory=11.8 (bordo ovale sfocato),
#   13_dust=ratio enorme ma mediana ~0 (fondo nero + pochi motes nitidi).
# - duplicazione MSE: 07_vs_10=1.6, 01_vs_04=3.1, 04_vs_10=29.4, 01_vs_07=25.7
#   -> 01/04/07/10 quasi indistinguibili a dimensioni YouTube (D10).
# - moto meanabs: 01=0.01, 13=0.01, 07=0.19, 04=0.21, 10=0.22 (statici),
#   12=2.99, 15=2.95 (solo i due con drift apprezzabile, ma per motivi sbagliati).

## Mappa difetti D01..D10 -> file coinvolti
# D01 vignette triangolari/diamante + spotlight ovali:
#   render_minimal_documentary_backgrounds.py: build_plate_05 (pool ellissi concentriche
#   + blur 55 -> alone scalinato), build_plate_14 (stesso pattern), build_plate_03
#   (anelli concentrici + blur 40), build_plate_06 (outline ellittici width=40 -> ovale),
#   build_plate_07 (pool centrale alpha 48). Difetto: anelli disegnati a passi di 60-80px
#   poi blur -> banding radiale e forma a diamante per aspect 0.62-0.70 non compensato.
# D02 segni verticali persistenti:
#   build_plate_03: 2 linee a tutta altezza x=480,1410 alpha 18-22 (sembrano giunzioni);
#   build_plate_09: segmenti interrotti ok ma 3 x fisse sempre visibili al centro.
# D03 grain poco distinguibile / digitale uniforme:
#   make_grain_texture(): solo 2 scale gaussiane, mappata con abs()*0.3-0.45 e alpha<=28,
#   senza componente bassa frequenza -> grana piatta o invisibile dopo H.264 CRF18.
# D04 Perlin/fBm simmetrici e periodici:
#   nessun fBm vero; gradienti con sin() (08) e loop lineari -> texture simmetriche.
# D05 gradienti scuri piatti + banding:
#   loop per-riga senza dithering sufficiente (alpha<=16), aree piatte 01/04/07/10.
# D06 dust vuoto e nero:
#   build_plate_13: fondo (7,8,10) quasi nero + solo 16 motes raggio 2.5-6 alpha 35-95,
#   blur unico 1.8 -> puntini bianchi isolati, nessuna profondita'/drift.
# D07 righe orizzontali digitali:
#   build_plate_12: griglia permanente ogni 36px a tutta larghezza alpha 14
#   -> scanline, non ledger editoriale.
# D08 ivory riflettore:
#   build_plate_06: fondo (243,239,230) + outline scuri ai bordi -> contrasto centro-bordi
#   percepito come spotlight; fibre tinte a (70,65,58)*0.35 ancora visibili come sporco.
# D09 light sweep fascio diagonale:
#   build_plate_15: rounded_rect 700->100px ruotato -32deg, alpha 32 -> fascio leggibile.
# D10 duplicazione:
#   01/04/07/08/10 condividono base (8-24) + grain alpha<=22 senza identita' cromatica.

## Decisione architetturale (nessuna nuova dipendenza/GUI/browser)
# - Nuovo modulo condiviso: ChrononTemplate/tools/backgrounds/documentary_background_v2.py
#   (basi, grain multiscala, fBm value-noise, vignetta ellittica smoothstep, overlay).
# - 7 basi: dark_graphite, deep_navy, warm_umber, editorial_ivory, newsprint, muted_olive,
#   photo_bokeh. 15 ID storici mappati come varianti parametriche (compatibilita' test).
# - Overlay combinabili: soft_vignette, film_scratches, floating_dust (anche standalone).
# - Separazione: base / texture-grain / imperfezioni / illuminazione / animazione (ffmpeg).
# - Prototipi richiesti: 01_dark_film_grain 2.0, 06_editorial_ivory 2.0, 03_archival_film 2.0,
#   1920x1080 30fps 8s, versione pulita + versione con contenuti.

## File coinvolti nella correzione
# - NUOVO: ChrononTemplate/tools/backgrounds/documentary_background_v2.py
# - NUOVO: out/docbg_v2/*.mp4 + *_content.mp4 + report JSON
# - INVARIATO (compatibilita'): render_minimal_documentary_backgrounds.py,
#   catalog/minimal_documentary_backgrounds/{assets,plans,out,manifest.json},
#   tests/test_minimal_documentary_backgrounds.py
