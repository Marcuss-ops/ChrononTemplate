# Social Media Recreator V1

Every preset has its own C++ source file in `tools/social_posts/` (for example
`yt01_video_watch_page.cpp` and `ig05_direct_messages.cpp`). Each file defines
that preset's typed recipe; `social_recreator_v1.hpp` supplies shared types,
and `emit_social_recreator_v1.cpp` composes the recipes into native Chronon
RenderPlan V3 layers. Chronon3D renders them headlessly. The
25 recipes cover five each for YouTube, Instagram, TikTok, Discord and X.
The C++ compositor shares typography, card, media and profile primitives while
choosing platform palettes and feed, vertical video, comment, profile, chat,
embed, thread, quote, carousel and poll compositions per recipe.

The recipes and PNGs are mockups built from fictional content. The output is a
native reconstruction, not a capture from any platform, and must not be shown
as authentic evidence. This first pass is static; its vertical video and
carousel frames are layout mockups, not animated playback.

Generate the plans and PNGs:

```sh
cmake --build build/dev --target chronontemplate_emit_social_recreator_v1 -j4
tools/social_posts/render_social_recreator_v1.sh
```

Plans and PNG previews are written to `out/social_recreator_v1/plans/` and
`out/social_recreator_v1/png/`.
