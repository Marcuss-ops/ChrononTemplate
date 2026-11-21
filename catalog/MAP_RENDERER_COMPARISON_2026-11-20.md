# Confronto verificato: RenderingGen, ChrononTemplate, ChrononPlugin

Inventario locale verificato il 20 novembre 2026. Le parole “catalogato”, “render presente” e “nativo” indicano cose diverse: questa distinzione è intenzionale.

## Sintesi

| Progetto | Cosa c’è davvero | Cosa non significa |
|---|---|---|
| **RenderingGen** | Il renderer semantic maps accetta i 26 ID di animazione pubblicati dal catalogo ChrononPlugin, oltre a 2 movimenti camera e 3 basemap. Sono presenti i composition/overlay per route, pin, geometrie e MapFX. Ci sono anche render caricati di route, pin, mappe Italia/Giappone e gli esempi dei ticket del 19 novembre. | I 26 ID condivisi non sono 26 shader riscritti dentro RenderingGen: il catalogo dichiara ChrononPlugin come renderer di riferimento e il binario `maps_dynamic_map_render`. Un ID accettato dal validatore non dimostra da solo che ogni variante abbia un render caricato in ogni ambiente. |
| **ChrononTemplate** | `maps.v1.json` registra 29 mappe/plate: 28 regioni (12 paesi/regioni e 16 aree amministrative italiane, come documentato da `MAP_DATA_SOURCES.md`) più White Claude Map. `map_motion_v1.json` contiene 45 ricette in 7 famiglie: base, route, multi-location, data, satellite, terrain e historical. Il codice Template include ModernMapPack, 4 MapFx (area glow, radar, beam, city network), TacticalFillPack e sei composizioni EditorialMapPack. | Le 45 ricette sono composizioni e movimenti editoriali, non 45 effetti speciali equivalenti a ChrononPlugin. Le sei composizioni editoriali di Template ricevono geometrie già proiettate; Template non sostituisce da solo il renderer geografico Plugin. Tactical fill è dichiaratamente shape-only e non fa proiezione GeoJSON/OpenCV. |
| **ChrononPlugin** | Il catalogo pubblica 26 animazioni, 2 movimenti camera e 3 basemap. Nel workspace ci sono clip showcase per i diversi stili, sei video editoriali, tre look di basemap, due varianti GPU e render ticket route/area glow/multi-leg. | Un catalogo o una clip showcase prova che quella variante è disponibile nel workspace; non prova che l’effetto sia stato implementato nativamente in ChrononTemplate. |

## Le differenze pratiche

### Effetti ChrononPlugin senza un equivalente nativo 1:1 in ChrononTemplate

Questi 15 ID Plugin non hanno un corrispondente effetto speciale con la stessa implementazione in Template: `route_line`, `multi_leg_flight`, `territory_glow_reveal`, `satellite_scan_reveal`, `territory_flood_fill`, `volumetric_laser_scan`, `vector_particle_flow`, `dark_mirror_diorama`, `voronoi_heat_contours`, `holographic_postfx`, `territory_extrusion`, `map_style_morph`, `mountain_ridge_callout`, `continental_atlas`, `historic_location_timeline`.

Template ha alcune ricette concettualmente simili (route draw/follow, region fill, movimenti satellitari, terrain e historical), ma non sono la stessa resa né la stessa implementazione del Plugin. Per questi stili la galleria Drive contiene i render originali del Plugin; il bridge Template li mette come video layer per provarli nel percorso Chronon3D.

### Stili con un renderer/compositore Template già presente

- I quattro MapFx hanno implementazione Template: `area_glow_pulse`, `radar_location_reveal`, `light_beam_drop`, `city_network_expansion`. Sono effetti leggeri su anchor già posizionati, non il renderer 3D completo.
- `territory_tactical_fill` ha un pack Template, ma accetta poligoni in coordinate canvas e non proietta confini geografici.
- EditorialMapPack riconosce i sei stili `editorial_vox`, `paper_cutout`, `dark_radar`, `blueprint`, `connection_arc`, `floating_island`. Disegna la composizione in Template a partire da una scena con geometrie già proiettate. “Paper cutout” è il nome style del pack Template per il corrispondente `editorial_paper_cutout` del catalogo Plugin.

Quindi questi stili hanno una parte di rendering nativa in Template; non sono per questo un port completo del renderer geografico Plugin.

## Copertura delle anteprime caricate

La galleria contiene tutti i 26 ID del catalogo Plugin, usando clip showcase o render ticket disponibili, più varianti geografiche, due versioni GPU, sei stili editoriali, tre basemap, il demo Pavia, una clip breve di tag e i render ticket reali Firenze–Pisa, area glow Firenze e Firenze–Pisa–Siena. Le clip sono 1920×1080 e al massimo 10 secondi (il tag originale da 12 secondi è tagliato ai primi 10).

La clip route line Firenze–Pisa è inclusa come baseline attuale, non come raccomandazione estetica. Il test del bridge video-layer nel runtime Chronon3D ha prodotto una dominante viola e testo alterato rispetto alla clip originale: i piani sono selezionabili, ma la riproduzione fedele nel runtime resta da correggere. Le clip originali in Drive mantengono l’aspetto del Plugin.
