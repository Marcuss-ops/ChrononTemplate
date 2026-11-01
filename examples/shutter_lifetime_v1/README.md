# Shutter focus triptych — ChrononTemplate

Un solo video autonomo con tre fotografie create appositamente: isola e battello, radio d'epoca, corridoio. Le stampe hanno spazio tra loro e sono composte come tre livelli distinti, con bordo e ombra propri. Il fuoco passa da sinistra al centro e a destra, poi si assesta sulle tre immagini. Ogni fotogramma integra quattro campioni nel tempo di esposizione equivalente a 180°.

Master: `C:\Users\pater\Downloads\chronons_archival_triptych_rack_focus.mp4` — 1920×1080, H.264, 30 fps, 5 secondi.

Per rigenerare il video:

```powershell
python ChrononTemplate/tools/render_triptych_shutter_focus.py `
  ChrononTemplate/examples/shutter_lifetime_v1/assets `
  C:\Users\pater\Downloads\chronons_archival_triptych_rack_focus.mp4
```

Gli originali 1920×1080 sono `assets/photo_01_island.png`, `assets/photo_02_radio.png` e `assets/photo_03_corridor.png`. `tools/shutter_lifetime_v1.cpp` emette un RenderPlan Chronon singolo con le tre stampe come livelli separati.
