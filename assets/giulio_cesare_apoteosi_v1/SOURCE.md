# Source — Giulio Cesare bust

## Scan

- Opera: Giulio Cesare, KAS297
- Istituzione: Statens Museum for Kunst (SMK), Copenaghen
- Download: `https://api.smk.dk/api/v1/download-3d/5999n821n_KAS297_small.stl`
- File locale: `source/SMK_KAS297_Julius_Caesar_small.stl`
- Scaricato: 2026-11-04
- Formato: STL binario, 399.996 triangoli, circa 20 MB
- Diritti: SMK / SMK Open. Attribuzione: “Statens Museum for Kunst (SMK),
  KAS297”. Verificare i termini SMK Open prima di ridistribuire lo scan o
  un’opera derivata.

## Trasformazioni

`tools/showcases/build_giulio_cesare_apoteosi_v1.py`:

- weld dei vertici duplicati dello STL;
- decimazione a 7.001 vertici / 13.998 triangoli;
- mapping Y-up, centratura sull'asse verticale, altezza normalizzata a 1;
- normali area-weighted;
- mesh inline per Chronon3D.

Lo scan originale non viene modificato. La v3 conserva la mesh originale
decimata: il ray cast conferma che è watertight e che la nuca è una superficie
esterna chiusa; il difetto era nel culling/depth del renderer, non nella mesh.
Il generatore aggiunge nel piano un collare tornito che copre il perno
quadrato tra il taglio del petto e il basamento, senza riscrivere lo scan.

## Titolo

`tools/showcases/build_giulio_cesare_title_mesh.py` produce una mesh estrusa
Playfair (50.914 vertici / 20.426 triangoli) come asset alternativo. Nella v3
il titolo finale è un plate 1920×1080 generato da
`tools/showcases/composite_giulio_cesare_apoteosi_v1.py`, sfocato e composto
dietro la silhouette del busto: il compositor mesh non applica il depth tra
layer e una mesh dietro al busto copriva petto e collo. Lo stesso plate
contiene il pavimento discreto e l'ombra di contatto sotto il basamento.

Font: Playfair Display Bold (`Chronon3d/assets/fonts/PlayfairDisplay-Bold.ttf`,
SIL Open Font License).
