# TICKET-CT-EDITORIAL-MAP-LATE-MOTION-2026-11-25 — movimento nella coda dei sei stili editoriali

- **Stato:** CLOSED (2026-11-25)
- **Priorità:** P1
- **Owner:** templates / map packs
- **Origine:** audit 2026-11-24 delle animazioni mappa; rischio di coda
  statica nei pack editoriali.
- **Repo:** ChrononTemplate

## Problema

I sei stili `editorial_vox`, `paper_cutout`, `dark_radar`, `blueprint`,
`connection_arc` e `floating_island` non avevano un gate che dimostrasse che
almeno un layer resta animato fino alla fine della finestra. Una regressione
poteva quindi produrre un'intro breve seguita da una coda completamente
statica senza che la suite se ne accorgesse.

## Fix

`tests/editorial_map_pack.cpp` ora controlla, per ogni stile:

- esiste un layer con l'ultimo `transform_sample` nel 10% finale della
  finestra (`>= 0,9 * (frame_count - 1)`);
- l'ultimo campione differisce dal primo per opacità, scala o posizione.

La soglia scala con `frame_count`, quindi il gate non dipende dai 240 frame
dei fixture correnti.

## Evidenza

```sh
cd ChrononTemplate
cmake -S . -B build-map-anim -DCHRONONTEMPLATE_BUILD_TESTS=ON \
  -DCMAKE_BUILD_TYPE=Release -DCHRONON3D_INCLUDE_DIR="$PWD/../Chronon3d/include"
cmake --build build-map-anim --target chronontemplate_editorial_map_pack_test \
  chronontemplate_modern_map_pack_test chronontemplate_map_fx_pack_test \
  chronontemplate_tactical_fill_pack_test -j4
ctest --test-dir build-map-anim \
  -R 'chronontemplate_(editorial_map_pack|modern_map_pack|map_fx_pack|tactical_fill_pack)_test' \
  --output-on-failure
```

Risultato 2026-11-25: 4/4 PASS. Il test editoriale copre i sei fixture e gira
in 0,49 s; gli altri tre test mappa nativi restano verdi.

## Criteri di accettazione

- [x] Tutti e sei gli stili hanno un layer animato nel 10% finale del clip.
- [x] Il campione finale differisce dal primo (opacità/scala/posizione).
- [x] La suite mappa nativa resta verde.
- [x] Il gate non richiede rete, GPU o asset esterni.

## Limiti dichiarati

- Il gate verifica il `RenderPlan`, non i pixel finali: non sostituisce la
  parità visiva del renderer.
- La resa del bridge video-layer Chronon3D (dominante viola e testo alterato
  osservati nel confronto del 2026-11-20) resta fuori scope e va tracciata
  separatamente.
