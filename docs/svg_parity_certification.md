# Certificazione SVG Parity — fase prioritaria (2026-10-28)

> **Revisione look (2026-10-28, seconda passata)** — allineamento al frame di
> riferimento (`out/reference_1010.jpg`, quadrante montagna/sole):
> - Geometria canonica SVG aggiornata al profilo di riferimento (salita
>   irregolare con variazione di pendenza, picco stretto, discesa; rimossi
>   plateau orizzontale e seconda salita).
> - Glow ridisegnato come luce sfocata continua (buffer emissivo + 3 passate
>   box-blur + compositing additivo `BL_COMP_OP_PLUS`): nessun disco
>   concentrico, alone che si disperde nel nero.
> - Gerarchia delle luci: `SunOrb` = punto più luminoso (nucleo giallo caldo
>   piatto), `DocumentaryPath` = stroke sottile neutro (~3px @1080p),
>   `CheckpointMarker` = macchie rosse semitrasparenti, texture quasi invisibile.
> - Test SVG-02/SVG-03 dell'harness resi data-driven (valori dai preset).
> - Certificazione completa ri-eseguita: **12/12 PASS** (SVG-06 peggior errore
>   0.26 px). Nuovi hash RGBA sotto.

Ticket: *Test finale SVG Parity — ChrononTemplate / Chronon3D*, fase prioritaria
(single source of truth + certificazione pixel di Trim Path, Follow Path e camera).

## Stato del codice

- Base: commit locale `8a73f4b` (`feat(vector-diagram): add parity tools and 100 MP4 variants`),
  non ancora pubblicato sul remoto (il `main` remoto ispezionato era fermo a `8d5d6d1`).
- Modifiche di questa fase (working tree, non ancora committate):
  - **nuovo** `tools/vector_diagram/svg_peak_scene.hpp` — modulo condiviso: parsing SVG
    (`#peak_line`, cerchi checkpoint, stroke), preset `chronontemplate.svg_scene_catalog.v1`,
    geometria canvas, easing, campionamento arc-length, Trim Path, camera. Unica fonte
    di verità per entrambi gli eseguibili C++.
  - **riscritto** `tools/vector_diagram/svg_peak_parity_emitter.cpp` — emette il RenderPlan V3
    con le convenzioni del registry Python (CLI-validato), più layer checkpoint e camera;
    ogni valore proviene dal modulo condiviso.
  - **riscritto** `tools/vector_diagram/render_svg_parity_blend2d.cpp` — stesso modulo condiviso;
    resta locale solo il trattamento di disegno (ottave neon, glow, atmosfera). La camera è
    una singola trasformazione applicata a tutti gli elementi.
  - **modificato** `cmake/Tools.cmake` — `find_package(blend2d CONFIG QUIET)` + target Blend2D
    condizionati; include nlohmann per il renderer. Prima della correzione, `cmake` falliva
    alla generate (`blend2d::blend2d` non trovato) e i due target **non esistevano** come
    build pulita.
  - **nuovo** `catalog/documentary_svg_peak_v1_hd.json` — preset canonico 1920×1080/30/150
    con checkpoint e camera (pan+dolly), dati esterni: nessuna ricompilazione per cambiarli.
  - **nuovo** `tools/vector_diagram/svg_peak_parity_pixel_tests.py` — harness di certificazione
    con implementazione Python **indipendente** del contratto (sampling, easing, camera) usata
    come campionatore di riferimento.

## Ambiente e comandi eseguiti

Ambiente: Windows + WSL (il CMake di ChrononTemplate è dichiarato Linux-only; CI = Ubuntu/Ninja).
Blend2D + dipendenze header-only installati via vcpkg (`~/vcpkg/installed/x64-linux`).
GPU: NVIDIA GeForce RTX 4060 Ti.

```bash
# 1. Clean build da zero (SVG-01)
cmake -S ChrononTemplate -B ChrononTemplate/build/svg-parity -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCHRONONTEMPLATE_BUILD_TESTS=ON \
  -DCHRONONTEMPLATE_NLOHMANN_JSON_DIR=/usr/include \
  -DCMAKE_PREFIX_PATH=/home/pater/vcpkg/installed/x64-linux
cmake --build ChrononTemplate/build/svg-parity \
  --target chronontemplate_svg_peak_parity_emitter chronontemplate_render_svg_parity_blend2d

# 2. Certificazione (12 controlli, encode GPU incluso)
python3 tools/vector_diagram/svg_peak_parity_pixel_tests.py \
  --ffmpeg ffmpeg.exe --ffprobe ffprobe.exe
```

## Risultati — 12/12 PASS

Log completo: `out/svg_parity/cert/svg_parity_certification.log`
(ogni riga: `ID \t PASS/FAIL \t messaggio`).

| ID | Matrice (30 test) | Esito | Evidenza |
| --- | --- | --- | --- |
| SVG-01 | Clean build C++ | **PASS** | configure+build puliti da zero; entrambi i target rispondono |
| SVG-01/emit | — | **PASS** | emitter scrive il RenderPlan |
| SVG-02 | RenderPlan V3 | **PASS** | JSON strutturalmente valido + parità semantica col registry Python (`build_plan`) su geometria/timing/marker |
| SVG-03 | SVG source of truth | **PASS** | nessuna coordinata di scena nei sorgenti C++ (scan statico) + SVG/preset perturbati guidano piano e pixel senza ricompilazione |
| SVG-04 | Trim Path 0→100% | **PASS** | copertura 0 a inizio, ≈progresso a metà, ≥0.95 a fine, monotona |
| SVG-05 | Curva e vertice | **PASS** | trim continuo sui vertici, nessun buco né segmenti fuori posto (zone oscurate dai marker escluse) |
| SVG-06 | Follow Path | **PASS** | centroide sole vs campionatore indipendente: errore max **1.05 px** (≤ 2 px) |
| SVG-07 | Timing differenti | **PASS** | varianti 90f/`out_cubic` e 240f/`in_out_cubic`: sole sempre in linea |
| FX-08 | Camera Pan + Dolly | **PASS** | sole, linea e checkpoint allineati sotto pan+dolly (stessa trasformazione condivisa) |
| SVG-08 | Input non valido | **PASS** | SVG malformato, `#peak_line` mancante, comando curva, preset privo di campi, easing sconosciuto → `[ERROR]` esplicito, exit 1, nessun crash |
| INT-03 | Video completo | **PASS** | MP4 1920×1080, 30/1, 150 frame decodificabili, PTS continui |

Mappatura onesto sui test non eseguiti in questa fase: FX-01…FX-07, FX-09, FX-10
(primitive isolate A/B), INT-01, INT-02 (confronto col renderer Chronon3D), INT-04/05
(determinismo, random access), INT-06 (GPU Vulkan), SCALE-01…06, livello 4 (fedeltà ai
video di riferimento). Il modulo **non è ancora** Production Certified.

## Artefatti

Directory: `out/svg_parity/cert/` (gitignored)

- `documentary_svg_peak_blend2d.mp4` — video finale 1920×1080/30/150, **encode GPU h264_nvenc**
  (NVENC verificato operativo sugli stessi frame; fallback libx264 mai raggiunto).
- `documentary_svg_peak_v1_hd.plan.json` + `documentary_svg_peak_v1.plan.json` + neon plan in `plan/`.
- `checkpoint_frame_0058.png`, `checkpoint_frame_0149.png`.
- `frames_hd/` (150 PNG), `frames_sd/` (150 PNG clean-plate), `variants/` (preset SVG/perturbed, A, B, C_camera, errors).
- Hash SHA-256 dei frame RGBA (decode PNG → RGBA, revisione look):
  - frame_0000 `8e6c57275eb881722b1b313dc9e5b7aad3d7414d792454d3e7baeab80e59f08e`
  - frame_0058 `f7c474bd6e0144a3606c047e04780fea8774dd4c4b39832716bc703a0207841c`
  - frame_0149 `e50d2c092df260195478edfb606708c3f5201119bcbfa4ae4f1a5bd1eb5293f0`

## GPU — stato onesto

- **Usata**: encode NVENC (h264_nvenc) per il video finale, verificato RTX 4060 Ti operativa.
- **Non eseguito**: gate Vulkan/INT-06 e i quattro shader (`inner_glow_rim.frag`,
  `multipass_bloom.frag`, `dof_bokeh.frag`, `analog_film_fx.frag`). I file vivono ancora
  fuori dal repo (`neon_essay_animations/shaders/`) e non sono integrati in nessuna pipeline
  con binding/dispatch verificati. Come da linee guida del ticket: **non eseguito, non PASS**.

## Limitazioni

- `chronon3d_cli` non è presente come binario in questo ambiente: SVG-02 è garantito per
  validazione strutturale + parità semantica col generatore Python che `chronon3d_cli validate`
  già accetta, non per un'invocazione diretta del decoder in questa sessione.
- La build è certificata sul toolchain del progetto (Linux/Ninja, come la CI). Il wrapper
  PowerShell/`cl.exe` storico resta disponibile ma non è più necessario per i due target.
- La resa visiva della scena HD (dimensioni marker proporzionali al catalogo SD) non è
  ancora confrontata con i video di riferimento: è il livello 4 del ticket, non questa fase.
