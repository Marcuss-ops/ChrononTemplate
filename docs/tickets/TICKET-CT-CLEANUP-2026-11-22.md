# TICKET-CT-CLEANUP-2026-11-22 — monoliths and repository hygiene

**Stato:** `OPEN` (2026-11-22)
**Owner:** template maintenance
**Origine:** audit Chronon 2026-11-22, voci CT-AUDIT-01 e REPO-AUDIT-01

## Problemi

- Monoliti: `BackgroundPack.cpp` (1.324 righe), `EditorialMapPack.cpp`
  (1.212), `WebShotsRebuildPack.cpp` (1.203), `MultiImagePack.cpp` (1.106),
  con helper hex/colore duplicati invece che condivisi in `core/`.
- Artefatti: 13 `.obj` (~600 KB) tracciati nella root, log di build e file non
  committati; Chronon3d ha log `chronon3d-2026*.log` e PNG
  `RenderingGen_probe*.png` non tracciati; ChrononPlugin ha
  `plugins/maps/assets/maps/cache/pyramid/` non tracciata.

## Piano

1. Estrarre gli helper colore/hex in un header `core/` unico e far migrare i
   pack; ogni split deve essere meccanico e coperto dai test esistenti.
2. Verificare l'uso reale dei 13 `.obj` prima di rimuoverli; se sono fixture,
   spostarli sotto `tests/fixtures/` e aggiornare i riferimenti.
3. Aggiungere al `.gitignore` i log/PNG/cache generati e rimuovere solo gli
   artefatti non tracciati. Nessuna cancellazione di file tracciati senza un
   controllo dei reference.
4. Non committare build dir o cache; il repo resta riproducibile dai sorgenti.

## Gate

- [ ] `rg` dimostra che gli helper estratti hanno un solo owner.
- [ ] Build e suite template PASS dopo ogni split.
- [ ] `git status` pulito nei quattro repo Chronon (esclusi file live dei job).
- [ ] Nessun file tracciato rimosso senza riferimento aggiornato.
- [ ] `[NOT RUN]` al 2026-11-22: nessun build lanciato per RAM occupata.
