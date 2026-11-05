# Scene contract — Giulio Cesare: apoteosi v3

## Intent

Un busto di Giulio Cesare su fondo nero compie una rotazione completa di 360°
in 8 secondi. La luce principale è centrale/dall'alto; il titolo “GIULIO
CESARE” resta dietro al busto, fuori fuoco, coperto dalla silhouette. Il
basamento deve leggersi come un unico pezzo con il busto: il giunto originale
aveva un perno quadrato e un vuoto anulare che sembravano una mesh scomposta.

Il deliverable vive in ChrononTemplate. La composizione, la camera, la luce, il
DoF e i frame del busto sono Chronon3D (RenderPlan V3, backend **Vulkan** su
NVIDIA RTX A4000). Il titolo e l'ombra di contatto sono composti in post.

## Deliverable

- Video: `ChrononTemplate/out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v3.mp4`
- Piano: `ChrononTemplate/out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v3.plan.json`
- Render busto GPU: `ChrononTemplate/out/giulio_cesare_apoteosi_v1/bust_gpu_v3.mp4`
- Plate titolo/pavimento: `ChrononTemplate/out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v3_title_plate.png`
- Contatto: `ChrononTemplate/out/giulio_cesare_apoteosi_v1/inspect/final_contact_sheet_v3.png`
- Formato: 1920×1080, 30 fps, 240 frame, 8,0 s, H.264 MP4
- Profilo: `production`, backend `vulkan`, encoder nativo NVENC

## Composizione

| Elemento | Valore |
|---|---|
| Camera | prospettica, `[960, 540, -1400]`, fov 32°, near 1, far 6000 |
| Fuoco | distanza 1400, f/2.0, `max_blur` 30 |
| Busto | mesh inline, 7.001 vertici / 13.998 triangoli originali + collare 866 vertici / 1.344 triangoli |
| Collare | profilo tornito y 0,252…0,358, raggio 0,178…0,203, 96 sezioni; copre il perno quadrato |
| Luce | key `[0.04, -0.88, -0.35]` 1.30, ambient 0.30, rim 0.45 / power 2.8 |
| Titolo | plate 1920×1080, Playfair Bold 180, tracking 8, blur 10, colore `(142,114,72)`, baseline 560 |
| Pavimento | gradiente ellittico discreto e ombra di contatto sotto il basamento, nel plate |
| Ordine | render del solo busto in Vulkan → compositing del plate dietro la silhouette |

La key viene dall'alto e leggermente dal fronte; il collare è nello stesso
materiale del marmo e non introduce un secondo materiale sulla scultura.

## Rotazione

La rotazione è bakeata nell'animazione inline della mesh: 60 campioni, frame
0…239. Dopo il remap Y-up lo scan guarda verso **-Z**, cioè verso la camera a
frame 0; l'angolo 0 è già il volto. Non va applicato alcun offset di 180°.

- frame 0: volto
- frame 60: profilo
- frame 120: retro
- frame 239: volto (loop)

## Correzione del culling software

La vista RenderPlan viene convertita in GL con `flip_camera_z`, una riflessione
che inverte il winding. In
`Chronon3d/src/backends/software/specialized/mesh_renderer.cpp` il test ora usa
il determinante di `view * model`: se è negativo, il segno del back-facing
viene invertito. Il render finale usa Vulkan, ma la correzione resta necessaria
per il percorso software e per i test di regressione.

## Giunto busto/basamento

La mesh SMK è un unico componente watertight, ma il taglio del petto e il
basamento sono separati visivamente da un **perno quadrato** con un vuoto
anulare intorno. Il generatore aggiunge al piano un collare tornito che
interseca il basamento e il taglio del petto: il perno non è più visibile e la
silhouette è continua. La mesh sorgente non viene modificata; il collare è
generato nel piano v3 da `add_collar()`.

## Perché titolo e ombra sono in post

Il compositor software non usa il depth tra layer mesh e dipingeva il titolo
davanti al petto; per questo il titolo è un plate sfocato composto dietro la
silhouette. Il pass ombre nativo con un **caster mesh** in questa build
restituisce una silhouette bianca al posto del busto; non viene usato. Il plate
aggiunge quindi un pavimento discreto e un'ombra di contatto sotto il
basamento, senza toccare il render GPU del busto.

## Asset

- Scan: SMK KAS297, `assets/giulio_cesare_apoteosi_v1/source/SMK_KAS297_Julius_Caesar_small.stl`
- Mesh busto: `assets/giulio_cesare_apoteosi_v1/giulio_cesare_bust_mesh.json`
- Mesh titolo (alternativa): `assets/giulio_cesare_apoteosi_v1/giulio_cesare_title_mesh.json`
- Font titolo: `Chronon3d/assets/fonts/PlayfairDisplay-Bold.ttf`
- Generatore scena: `tools/showcases/build_giulio_cesare_apoteosi_v1.py`
- Compositore: `tools/showcases/composite_giulio_cesare_apoteosi_v1.py`

## Riproduzione

```bash
python3 ChrononTemplate/tools/showcases/build_giulio_cesare_apoteosi_v1.py

ROOT="$PWD"
CLI="$ROOT/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
"$CLI" render \
  --plan "$ROOT/ChrononTemplate/out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v3.plan.json" \
  --assets-root "$ROOT" --backend vulkan --hardware nvenc \
  --start-frame 0 --end-frame 239 --profile production \
  --output "$ROOT/ChrononTemplate/out/giulio_cesare_apoteosi_v1/bust_gpu_v3.mp4"

python3 "$ROOT/ChrononTemplate/tools/showcases/composite_giulio_cesare_apoteosi_v1.py" \
  --bust "$ROOT/ChrononTemplate/out/giulio_cesare_apoteosi_v1/bust_gpu_v3.mp4" \
  --out "$ROOT/ChrononTemplate/out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v3.mp4"
```

## Verifica eseguita

- Render Vulkan: 240/240 frame, 1920×1080, 30 fps, 8,000 s; `render_ms=30377`,
  `wall_ms=31598`.
- Video finale: 240 frame, 1920×1080, 30 fps, 8,000 s, H.264.
- Frame 0/30/60/90/120/150/180/239: volto → profilo → nuca → profilo → volto;
  collare chiuso; titolo sfocato dietro, occluso dalla silhouette.
- Piano v3: un solo layer busto; il titolo e il pavimento non sono layer 3D.

## Limiti noti

- Il pass ombre nativo con caster mesh in questa build non è utilizzabile:
  produce una silhouette bianca. L'ombra è quindi un contatto 2D nel plate.
- Non c'è una probe HDRI/IBL dedicata; il riempimento è affidato a key, ambient
  e rim della lighting rig.
- Il titolo resta un plate sfocato, non una mesh 3D, per il limite di depth del
  compositor mesh.
- La licenza dello scan SMK va verificata nei termini SMK prima di una
  ridistribuzione; vedi `assets/giulio_cesare_apoteosi_v1/SOURCE.md`.
