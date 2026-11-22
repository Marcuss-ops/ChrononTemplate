# TICKET-REPO-ARTIFACTS-HYGIENE-2026-11-22 — log, PNG, OBJ e cache generati nei repo

**Stato:** `OPEN`
**Priorità:** P3
**Data:** 2026-11-22
**Owner:** repository maintenance
**Origine:** REPO-AUDIT-01
**Padre:** [TICKET-CT-CLEANUP-2026-11-22](TICKET-CT-CLEANUP-2026-11-22.md)
**Correlato:** [TICKET-CM3D-BOUNDARY-ARTIFACTS-2026-11-22](../../../ChrononMotion3D/docs/tickets/TICKET-CM3D-BOUNDARY-ARTIFACTS-2026-11-22.md)

## Problema

I repository contengono artefatti generati (log, PNG, OBJ, cache) che:
- sporcano `git status`;
- fanno fallire il boundary test Motion, che li scansiona come sorgenti;
- rendono ambiguo quali file siano fixture e quali output.

## Evidenza

- `[CHRONON3D]` 27 file `chronon3d-2026*.log` nella root.
- `[CHRONON3D]` 2 file `RenderingGen_probe*.png` nella root.
- `[CHRONONTEMPLATE]` 13 file `.obj` (audit: ~600 KB, alcuni tracciati).
- `[CHRONONPLUGIN]` `plugins/maps/assets/maps/cache/pyramid/` non tracciata.
- `[CHRONONMOTION3D]` `out/threepp_certification/T06|T12|T14|T16-gpu-verify/README.txt`
  con riferimenti ffmpeg/NVENC che fanno fallire `chrononmotion_boundary`.
- `[ROOT]` `ops/jobs/*` e file di report dei job sono **live**, non vanno
  cancellati da questa pulizia.

## Piano di chiusura

1. **Classificare prima di cancellare.**
   ```bash
   git ls-files '*.log' '*.png' '*.obj'
   git status --short -- '*.log' '*.png' '*.obj'
   ```
   Ogni file tracciato va verificato con `rg` per riferimenti prima di
   rimuoverlo.
2. **Fixture vs output.** Se un `.obj`/font/immagine è una fixture, spostarlo
   sotto `tests/fixtures/` e aggiornare i riferimenti. Se è output, rimuoverlo
   solo se non tracciato.
3. **`.gitignore`.** Aggiungere pattern per:
   - `chronon3d-*.log`
   - `RenderingGen_probe*.png`
   - `out/`
   - `plugins/maps/assets/maps/cache/`
   - build dir e cache già ignorate
   Evitare pattern troppo larghi che nascondano fixture reali.
4. **Boundary Motion.** Con `out/` ignorato/spostato, rieseguire
   `chrononmotion_boundary` e verificare che continui a scansionare i sorgenti.
5. **Live jobs.** Escludere esplicitamente `ops/jobs/` e i report live dalla
   pulizia; non cancellare dati di job non tracciati.
6. **Verifica finale.** `git status --short` pulito nei quattro repo, esclusi i
   file live dei job.

## Gate di accettazione

- [ ] Nessun log/PNG/OBJ/cache generato è tracciato.
- [ ] Gli artefatti non tracciati sono rimossi o spostati in directory ignorate.
- [ ] Le fixture spostate hanno riferimenti aggiornati.
- [ ] `chrononmotion_boundary` PASS.
- [ ] `git status --short` pulito nei quattro repo, esclusi i live job.
- [ ] Nessun file tracciato rimosso senza `rg` di controllo.

## Comandi di verifica

```bash
cd /home/pierone/src/go-master/projects/Pyt/VeloxEditing
git -C Chronon3d status --short
git -C ChrononMotion3D status --short
git -C ChrononPlugin status --short
git -C ChrononTemplate status --short

ctest --test-dir ChrononMotion3D/build/verify -R '^chrononmotion_boundary$' \
  --output-on-failure
```

## Rischi e rollback

- Cancellare un `.obj` tracciato può rompere un test: usare `git ls-files` e
  `rg` prima, e lasciare il file se è una fixture.
- Non aggiungere `*.png`/`*.obj` globali al `.gitignore`: nasconderebbe fixture
  legittime. Preferire path specifici.

## Definition of Done

Nessun artefatto generato resta nel repo; le fixture sono sotto `tests/fixtures`
con riferimenti aggiornati; boundary e build restano verdi; `git status` è
pulito nei quattro repo, esclusi i file live dei job.
