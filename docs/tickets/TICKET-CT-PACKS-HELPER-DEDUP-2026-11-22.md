# TICKET-CT-PACKS-HELPER-DEDUP-2026-11-22 — split dei pack e helper colore unico

**Stato:** `OPEN`
**Priorità:** P2
**Data:** 2026-11-22
**Owner:** template maintenance
**Origine:** CT-AUDIT-01
**Padre:** [TICKET-CT-CLEANUP-2026-11-22](TICKET-CT-CLEANUP-2026-11-22.md)

## Problema

Quattro pack sono monoliti da oltre 1.100 righe e l'audit ha rilevato helper
hex/colore duplicati invece di un'unica utility condivisa. Questo rende i fix
visivi costosi e rischiosi: una modifica al parsing colore va replicata in più
pack.

## Evidenza

- `[CODICE]` `src/chronontemplate/backgrounds/BackgroundPack.cpp` — 1.324 righe.
- `[CODICE]` `src/chronontemplate/map/EditorialMapPack.cpp` — 1.212 righe.
- `[CODICE]` `src/chronontemplate/web/WebShotsRebuildPack.cpp` — 1.203 righe.
- `[CODICE]` `src/chronontemplate/multiple_images/MultiImagePack.cpp` — 1.106 righe.
- `[CODICE]` `BackgroundPack.cpp:107` usa
  `chronon3d::render_plan::parse_hex_color`; l'audit segnala helper equivalenti
  duplicati negli altri pack. Prima dello split va fatto l'inventario esatto:
  ```bash
  rg -n 'hex|parse_color|color_from|rgba' \
    src/chronontemplate/backgrounds/BackgroundPack.cpp \
    src/chronontemplate/map/EditorialMapPack.cpp \
    src/chronontemplate/web/WebShotsRebuildPack.cpp \
    src/chronontemplate/multiple_images/MultiImagePack.cpp
  ```

## Piano di chiusura

1. **Inventario helper.** Elencare ogni funzione hex/colore e i call site nei
   quattro pack e nel resto di `src/chronontemplate`.
2. **Un solo owner.** Estrarre il parser in un header/sorgente condiviso sotto
   `src/chronontemplate/core/` (nome da concordare con le convenzioni esistenti)
   e migrare tutti i call site. Nessuna copia locale.
3. **Split meccanico.** Dividere ogni pack per responsabilità (layout, testo,
   effetti, rendering) in unità più piccole, mantenendo la classe pubblica e
   l'ordine di registrazione; aggiornare il CMake una volta per pack.
4. **Nessun cambio visivo.** Ogni split deve essere behavior-preserving: stessi
   input, stessi golden/SHA.
5. **Test dopo ogni pack.** Build e suite template dopo ciascuno split, non
   solo alla fine.
6. **Documentazione.** Aggiornare il ticket padre con i nuovi file e il mapping
   classe → unità.

## Gate di accettazione

- [ ] `rg` mostra un solo owner per il parser hex/colore.
- [ ] Nessun pack supera la soglia concordata (proposta: 800 righe per file).
- [ ] Build Template verde.
- [ ] Suite template/golden verde, nessun delta visivo non approvato.
- [ ] Nessuna API pubblica rimossa o rinominata senza migrazione dei call site.

## Comandi di verifica

```bash
cd ChrononTemplate
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j2
ctest --test-dir build --output-on-failure

rg -n 'parse_hex_color|hex_to|color_from_hex' src/chronontemplate
```

## Rischi e rollback

- Uno split troppo aggressivo può cambiare l'ordine di registrazione dei pack:
  mantenere l'ordine e verificare i golden.
- Rollback per pack: ripristinare il file originale e tenere l'helper condiviso
  solo se già migrato e testato.

## Definition of Done

Helper colore con un solo owner, quattro pack divisi in unità leggibili, build
e suite template verdi senza delta visivi. La sola estrazione dell'helper non
chiude il ticket se i monoliti restano.
