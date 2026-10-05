# scene_camera_sequencer_v1 — il vocabolario camera da stacco a stacco

Pre-configurazioni camera pronte all'uso per le sequenze editoriali: ogni
**stacco** è un soggetto (frase, immagine, testo, card) che tiene la propria
inquadratura; tra uno stacco e l'altro **la camera** porta lo spettatore al
prossimo oggetto, che atterra sulla sua nuova inquadratura. I soggetti non si
animano mai: l'unica cosa che si muove è la lente (contratto P0 testato).

## Struttura del pack

| file | ruolo |
|---|---|
| `include/chronontemplate/SceneCameraPack.hpp` | il vocabolario: `SceneSubject`, `SceneBeat`, `SceneCameraSequence`, le 8 transizioni |
| `src/chronontemplate/SceneCameraPack.cpp` | il lowering: rest pose per soggetto + piani di gamba abbassati sui canali del `CameraRig` |
| `tests/scene_camera_pack.cpp` | 8 gate contrattuali × 8 transizioni (131 check) |
| `tools/dump_scene_camera_poses.cpp` | sequenze canoniche → pose per frame |
| `tools/render_scene_camera_sequencer_v1.py` | dump → piani `chronon.render-plan.v3` → render CLI Chronon3D |
| `../../RenderingGen/UploadDrive/upload_scene_camera_sequencer_v1.sh` | pubblicazione Drive con verifica SHA-256 |

## Le otto transizioni

`scene_camera_push_through` (tuffo attraverso la cucitura) ·
`scene_camera_lateral_swipe` (il corpo attraversa di lato, mira bloccata in
avanti) · `scene_camera_arc_carry` (arco perpendicolare, l'elegante di
default) · `scene_camera_orbit_handoff` (orbita di 26° attorno al perno di
cucitura) · `scene_camera_rise_and_land` (quota sopra la cucitura e atterra)
· `scene_camera_focus_rack` (quasi fermo: la lente passa il fuoco da A a B) ·
`scene_camera_pull_back_reveal` (parte stretta su A con rollio, atterra largo
su B) · `scene_camera_whip_reframe` (acquisizione secca, poi lungo assestamento).

Ogni gamba è una traiettoria a 3 chiavi (partenza / vertice / atterraggio) le
cui metà hanno pendenza combaciante: la velocità è continua attraverso il
vertice, senza stalli né scatti. L'intensità (`0.55 subtle / 1 editorial /
1.9 cinematic`) scala tutti i delta.

## Come si usa

```cpp
#include "chronontemplate/SceneCameraPack.hpp"

applySceneCameraSequence(scene, SceneCameraSequence{
    .beats = {{{SubjectKind::Phrase, {960.f, 540.f, 0.f}, 520.f, 110.f}, 60},
              {{SubjectKind::Image,  {960.f, 540.f, -80.f}, 460.f, 260.f}, 60},
              {{SubjectKind::Text,   {960.f, 540.f, 0.f}, 620.f, 150.f}, 60}},
    .transition = SceneCameraTransition::ArcCarry,
    .intensity = 1.f,
    .travelFrames = 24,
    .inFrame = 0});
```

La distanza di riposo di ogni stacco è derivata dalle semi-dimensioni del
soggetto con una sola legge ottica (`sceneFramingDistance`, riempimento
0.62+0.10·intensità dell'asse corto) e dalla lente del tipo
(`sceneSubjectFov`: Phrase 50°, Image 62°, Text 44°, Card 56°): frase,
immagine e titolo si incorniciano da soli, senza coordinate da autare.

## Mappe pre-configurate da JSON (senza ricompilare)

Una mappa è un documento `chronontemplate.scene-camera-sequence.v1`: camera
(kind, center, half extents, hold), transizione, intensità, travel — più il
blocco `content` per il render (testo/immagine/card), che il lente non legge
mai. Il catalogo canonico vive in `catalog/scene_camera_sequences_v1/`:

| mappa | grammatica |
|---|---|
| `editorial_three.json` | frase → immagine → testo, `scene_camera_arc_carry` |
| `documentary_five.json` | 5 stacchi (frase/immagine/citazione/card/frase), `scene_camera_pull_back_reveal` |
| `social_reel_three.json` | 3 stacchi corti, `scene_camera_whip_reframe` a intensità 1.4 |

Render di una mappa, end-to-end senza C++:

```sh
python3 tools/render_scene_camera_sequencer_v1.py \
  --sequence-json catalog/scene_camera_sequences_v1/editorial_three.json
```

Il tool `chronontemplate_sequence_from_json <map.json>` valida fail-closed
(schema sconosciuto, transizione sconosciuta, kind sconosciuto, meno di due
beat, hold < 6, geometria non finita, JSON malformato → exit 1 con messaggio
sul stderr) e emette le stesse righe del dumper. Il contratto è fissato da
`tools/test_scene_sequence_json.py` (CTest: `chronontemplate_scene_sequence_json_contract`).

## Rigenerare e pubblicare

```sh
cmake --build --preset dev --target chronontemplate_dump_scene_camera_poses
python3 tools/render_scene_camera_sequencer_v1.py     # piani + render
ctest --preset dev -R scene_camera                    # gate contrattuale
../RenderingGen/UploadDrive/upload_scene_camera_sequencer_v1.sh
```

Output: `out/scene_camera_sequencer_v1/{plans,renders}` — 8 clip gallery da
228 frame + `master_five_stacchi_arc_carry` da 420 frame (14 s), 1920×1080
30 fps. La cartella `RenderingGen/UploadDrive/scene_camera_sequencer_v1/`
contiene la copia pronta per il Drive con piani e timing sidecar.
