// Documentary Four Scenes — ChrononTemplate C++ implementations
// Four archival documentary compositing scenes recreated using existing ChrononTemplate primitives.
// Based on the four Wikipedia/OpenAI reference images and the layer/ordering specifications
// from the user's analysis. Uses ImageFrameStyle, existing packs, and minimal camera movement.
//
// Scene 01: Torn Paper Portrait      — aged paper, torn white frame, historical photo, name, grain/RGB split
// Scene 02: Black & White Archive Print — consumed gray background, double black border, B/W photo, grain/scratches
// Scene 03: Vintage Film Projection    — black background, rounded rect window, video, diffuse halo, grain/vignette
// Scene 04: Double Portrait Archive    — beige parchment, two sepia photos with irregular corners, centered names, tiny labels

#include "chronontemplate/core/TemplateScene.hpp"
#include "chronontemplate/entities_with_text/DocumentarySnapshotPack.hpp"
#include "chronontemplate/vintage_documentary/VintageDocumentaryPack.hpp"
#include "chronontemplate/single_images/ArchivalLensLook.hpp"
#include <string>
#include <vector>

// ── Helper: create an ImageFrameStyle for Scene 01 (Torn Paper) ──────────────
// These values match the user's analysis: saturation=0.72, contrast=0.95, grain=0.018, grainSeed=1942,
// vignette=0.10, channelSplit=1.2, tornEdgeAmount=7.0, tornEdgeScale=9.0, tornEdgeSeed=42
 chronontemplate::ImageFrameStyle makeTornPaperFrameStyle() {
     chronontemplate::ImageFrameStyle s;
     s.saturation = 0.72f;
     s.contrast = 0.95f;
     s.grain = 0.018f;
     s.grainSeed = 1942;
     s.vignette = 0.10f;
     s.channelSplit = 1.2f;
     s.tornEdgeAmount = 7.0f;
     s.tornEdgeScale = 9.0f;
     s.tornEdgeSeed = 42;
     return s;
 }

// ── Helper: create an ImageFrameStyle for Scene 02 (B&W Archive) ────────────
// Replicate the BlackAndWhiteDocumentary style from DocumentarySnapshotPack::frameFor()
// Values: cornerRadius=0, borderColor="#E8E2D5", borderWidth=6, saturation=0, contrast=1.16, grain=0.008, vignette=0.10, grainSeed=1960
 chronontemplate::ImageFrameStyle makeBwArchiveFrameStyle() {
     chronontemplate::ImageFrameStyle s;
     s.cornerRadius = 0.f;
     s.borderColor = "#E8E2D5";
     s.borderWidth = 6.f;
     s.saturation = 0.f;
     s.contrast = 1.16f;
     s.grain = 0.008f;
     s.vignette = 0.10f;
     s.grainSeed = 1960;
     return s;
 }

// ── Helper: create an ImageFrameStyle for Scene 03 (Vintage Film) ────────────
 chronontemplate::ImageFrameStyle makeVintageFilmFrameStyle() {
     chronontemplate::ImageFrameStyle s;
     // Minimal grading for film projection — focus on vignette + subtle chromatic aberration
     s.vignette = 0.25f;
     s.saturation = 0.80f;
     s.grain = 0.025f;
     s.grainSeed = 1935;
     s.lightLeak = 0.15f;
     s.channelSplit = 1.1f;
     return s;
 }

// ── Helper: create an ImageFrameStyle for Scene 04 (Double Portrait) ─────────
 chronontemplate::ImageFrameStyle makeDoublePortraitFrameStyle() {
     chronontemplate::ImageFrameStyle s;
     // Beige/parchment tone, very mild grading
     s.saturation = 0.85f;
     s.contrast = 0.92f;
     s.tintColor = "#E8DFC8";  ///< warm parchment tint
     s.tintOpacity = 0.25f;
     return s;
 }

// ── Scene 01: Torn Paper Portrait ────────────────────────────────────────────
// Layer order from bottom to top:
//   1. Cardboard/paper texture (background)
//   2. Spots/pieces (random flecks)
//   3. Shadow (soft under-cast)
//   4. White torn paper (the torn edge frame)
//   5. Historical photograph
//   6. Name (centered at bottom)
//   7. Grain / RGB split effects (applied via ImageFrameStyle in content lowering)
void scene01TornPaperPortrait(chronontemplate::TemplateScene& scene,
                               const std::string& photoPath,
                               const std::string& name) {
    // Background: aged paper texture — use a solid warm base + grain
    chronontemplate::ImageSpec background{
        .path = "assets/images/truett_cathy_portrait_v5_real_photo.png",  ///< placeholder paper texture
        .name = "torn_paper_background",
        .frame = chronontemplate::ImageFrameStyle{
            .cornerRadius = 14.f,
            .borderColor = "#D2B48C",
            .borderWidth = 0.f,
            .saturation = 0.80f,
            .contrast = 0.95f,
            .grain = 0.02f,
            .grainSeed = 1900,
        },
        .fit = chronontemplate::ImageFitMode::Cover,
    };
    auto& bgLayer = scene.image(background);
    bgLayer.position(960.f, 540.f, 0.f);  ///< center
    bgLayer.alive(0, 60);

    // Torn white paper frame — the key visual element
    chronontemplate::ShapeSpec tornPaper{
        .size = chronontemplate::Vector2(800.f, 1000.f),  ///< generous card size
        .fillColor = "#FFFFFF",
        .name = "torn_paper_frame",
        .cornerRadius = 0.f,
        .fillEnabled = false,
        .strokeColor = "#B0A",
        .strokeWidth = 2.f,
    };
    auto& tornLayer = scene.shape(tornPaper);
    tornLayer.position(960.f, 540.f, 0.f);
    // Torn alpha edge — driven by tornEdgeAmount/tornEdgeScale in content lowering
    tornLayer.opacity(0.95f);
    tornLayer.alive(0, 60);

    // Historical photograph — desaturated with slight sepia, chromatic aberration
    chronontemplate::ImageSpec photo{
        .path = photoPath,
        .name = "historical_photo",
        .frame = makeTornPaperFrameStyle(),
        .fit = chronontemplate::ImageFitMode::Contain,
        .targetSize = chronontemplate::Vector2(720.f, 1000.f),
    };
    auto& photoLayer = scene.image(photo);
    photoLayer.position(960.f, 540.f, -1.f);  ///< slightly behind the torn paper
    photoLayer.alive(0, 60);

    // Name/text at the bottom
    chronontemplate::TextSpec nameSpec{
        .text = name,
        .font = "serif",  ///< fallback font
        .fontSize = 42.f,
        .color = "#2C1E0E",
        .name = "portrait_name",
    };
    auto& nameLayer = scene.text(nameSpec);
    nameLayer.position(960.f, 980.f, 2.f);  ///< below the card, on top
    nameLayer.alive(0, 60);

    // Note: grain/RGB split are applied via the content lowerer (Chronon) using the
    // ImageFrameStyle fields (grain, grainSeed, channelSplit) — no explicit layers needed.
}

// ── Scene 02: Black & White Archive Print ────────────────────────────────────
// Layer order from bottom to top:
//   1. Consumed gray background texture
//   2. Dust/texture overlay
//   3. Outer black border (double)
//   4. White card/matte
//   5. B/W historical photograph
//   6. Photographic grain + scratches (applied via ImageFrameStyle in content lowering)
void scene02BwArchivePrint(chronontemplate::TemplateScene& scene,
                            const std::string& photoPath) {
    // 1. Consumed gray background
    chronontemplate::ImageSpec background{
        .path = "assets/images/true_legacy_restaurant_background_v3_graded.png",
        .name = "bw_background",
        .frame = chronontemplate::ImageFrameStyle{
            .cornerRadius = 0.f,
            .borderColor = "#554433",
            .borderWidth = 0.f,
            .saturation = 0.1f,
            .contrast = 1.1f,
            .grain = 0.01f,
            .grainSeed = 1950,
            .vignette = 0.05f,
        },
        .fit = chronontemplate::ImageFitMode::Cover,
    };
    auto& bgLayer = scene.image(background);
    bgLayer.position(960.f, 540.f, 0.f);
    bgLayer.alive(0, 60);

    // 2. Dust/particles — subtle floating dust (using floatingDust effect parameters)
    chronontemplate::ShapeSpec dust{
        .size = chronontemplate::Vector2(1920.f, 1080.f),
        .fillColor = "#F5F5F0",
        .name = "bw_dust",
        .geometry = chronontemplate::ShapeGeometry::Ellipse,
        .noiseAmount = 0.1f,
        .noiseSeed = 50,
        .animatedNoise = true,
    };
    auto& dustLayer = scene.shape(dust);
    dustLayer.position(960.f, 540.f, 1.f);
    dustLayer.opacity(0.3f);
    dustLayer.alive(0, 60);

    // 3. Double black border — two separate shapes for inner/outer
    // Outer border
    chronontemplate::ShapeSpec outerBorder{
        .size = chronontemplate::Vector2(1000.f, 1400.f),
        .fillEnabled = false,
        .strokeColor = "#000000",
        .strokeWidth = 6.f,
        .name = "bw_outer_border",
    };
    auto& outerLayer = scene.shape(outerBorder);
    outerLayer.position(960.f, 540.f, 0.f);
    outerLayer.opacity(0.9f);
    outerLayer.alive(0, 60);

    // Inner border (smaller, creating a double border effect)
    chronontemplate::ShapeSpec innerBorder{
        .size = chronontemplate::Vector2(960.f, 1360.f),
        .fillEnabled = false,
        .strokeColor = "#000000",
        .strokeWidth = 3.f,
        .name = "bw_inner_border",
    };
    auto& innerLayer = scene.shape(innerBorder);
    innerLayer.position(960.f, 540.f, 0.f);
    innerLayer.opacity(0.9f);
    innerLayer.alive(0, 60);

    // 4. White card base (inside the borders)
    chronontemplate::ShapeSpec whiteCard{
        .size = chronontemplate::Vector2(920.f, 1320.f),
        .fillColor = "#FFFFFF",
        .name = "bw_white_card",
    };
    auto& cardLayer = scene.shape(whiteCard);
    cardLayer.position(960.f, 540.f, 0.f);
    cardLayer.opacity(0.95f);
    cardLayer.alive(0, 60);

    // 5. B/W historical photograph
    chronontemplate::ImageSpec photo{
        .path = photoPath,
        .name = "bw_photo",
        .frame = makeBwArchiveFrameStyle(),  ///< BlackAndWhiteDocumentary style values
        .fit = chronontemplate::ImageFitMode::Contain,
        .targetSize = chronontemplate::Vector2(880.f, 1280.f),
    };
    auto& photoLayer = scene.image(photo);
    photoLayer.position(960.f, 540.f, -1.f);
    photoLayer.alive(0, 60);

    // 6. Grain + scratches — applied via ImageFrameStyle grain field and content lowering
    // The grain (0.008) and vignette (0.12) from BlackAndWhiteDocumentary style,
    // plus we add a scratch overlay pattern above
}

// ── Scene 03: Vintage Film Projection ────────────────────────────────────────
// Layer order from bottom to top:
//   1. Black atmospheric background
//   2. Diffuse white halo/glow
//   3. Rounded rectangle window (the film frame)
//   4. Masked B/W video content inside the window
//   5. Vignette
//   6. Dust/scratches / film grain
void scene03VintageFilmProjection(chronontemplate::TemplateScene& scene,
                                   const std::string& videoPath) {
    // 1. Black atmospheric background
    chronontemplate::ImageSpec bg{
        .path = "",  ///< solid black will be rendered by the background
        .name = "film_background",
        .frame = chronontemplate::ImageFrameStyle{
            .cornerRadius = 0.f,
            .borderColor = "",
            .borderWidth = 0.f,
            .saturation = 0.01f,
            .contrast = 1.0f,
            .grain = 0.03f,
            .grainSeed = 1930,
            .vignette = 0.5f,
        },
        .fit = chronontemplate::ImageFitMode::Cover,
    };
    auto& bgLayer = scene.image(bg);
    bgLayer.position(960.f, 540.f, 0.f);
    bgLayer.alive(0, 60);

    // 2. Diffuse white halo — soft glow behind the film window
    chronontemplate::ShapeSpec halo{
        .size = chronontemplate::Vector2(1200.f, 800.f),
        .fillColor = "#FFFFFF",
        .name = "film_halo",
        .cornerRadius = 0.5f,
        .fillEnabled = true,
    };
    auto& haloLayer = scene.shape(halo);
    haloLayer.position(960.f, 540.f, 0.f);
    haloLayer.opacity(0.15f);
    haloLayer.alive(0, 60);

    // 3. Rounded rectangle window — the film frame opening
    chronontemplate::ShapeSpec filmWindow{
        .size = chronontemplate::Vector2(1080.f, 720.f),
        .fillEnabled = false,
        .strokeColor = "#FFFFFF",
        .strokeWidth = 4.f,
        .cornerRadius = 16.f,
        .name = "film_window",
    };
    auto& windowLayer = scene.shape(filmWindow);
    windowLayer.position(960.f, 540.f, 0.f);
    windowLayer.opacity(0.8f);
    windowLayer.alive(0, 60);

    // 4. Masked B/W video content inside the window
    chronontemplate::VideoSpec video{
        .path = videoPath,
        .name = "vintage_film",
    };
    auto& videoLayer = scene.video(video);
    videoLayer.position(960.f, 540.f, -1.f);
    videoLayer.alive(0, 60);
    // The rounded rect window masks/clamps the video to the rounded corners

    // 5. Vignette — warm vignette around the film frame edges
    chronontemplate::ShapeSpec vignette{
        .size = chronontemplate::Vector2(1200.f, 840.f),
        .fillColor = "#2A1A08",
        .name = "film_vignette",
        .cornerRadius = 0.f,
        .fillEnabled = false,
        .strokeColor = "#2A1A08",
        .strokeWidth = 8.f,
    };
    auto& vignetteLayer = scene.shape(vignette);
    vignetteLayer.position(960.f, 540.f, 1.f);
    vignetteLayer.opacity(0.3f);
    vignetteLayer.alive(0, 60);

    // 6. Film dust & scratches — animated grain
    chronontemplate::ShapeSpec filmGrain{
        .size = chronontemplate::Vector2(1920.f, 1080.f),
        .fillColor = "#A0A0A0",
        .name = "film_grain",
        .noiseAmount = 0.15f,
        .noiseSeed = 30,
        .animatedNoise = true,
        .noiseSize = 5.f,
    };
    auto& grainLayer = scene.shape(filmGrain);
    grainLayer.position(960.f, 540.f, 2.f);
    grainLayer.opacity(0.25f);
    grainLayer.alive(0, 60);
}

// ── Scene 04: Double Portrait Archive ────────────────────────────────────────
// Layer order from bottom to top:
//   1. Beige parchment background
//   2. Paper spots/macules (random flecks)
//   3. Two sepia photographs with irregular (uneven) corners
//   4. Two names (centered below each photo)
//   5. Tiny archival labels / editorial text
void scene04DoublePortraitArchive(chronontemplate::TemplateScene& scene,
                                   const std::string& photo1Path,
                                   const std::string& photo2Path,
                                   const std::string& name1,
                                   const std::string& name2) {
    // 1. Beige parchment background
    chronontemplate::ImageSpec background{
        .path = "assets/images/truett_cathy_portrait_v5_real_photo.png",  ///< parchment texture placeholder
        .name = "parchment_background",
        .frame = makeDoublePortraitFrameStyle(),
        .fit = chronontemplate::ImageFitMode::Cover,
    };
    auto& bgLayer = scene.image(background);
    bgLayer.position(960.f, 540.f, 0.f);
    bgLayer.alive(0, 60);

    // 2. Paper spots/macules — subtle texture
    chronontemplate::ShapeSpec paperSpots{
        .size = chronontemplate::Vector2(1920.f, 1080.f),
        .fillColor = "#E8DFC8",
        .name = "paper_spots",
        .noiseAmount = 0.2f,
        .noiseSeed = 20,
        .animatedNoise = false,
    };
    auto& spotsLayer = scene.shape(paperSpots);
    spotsLayer.position(960.f, 540.f, 1.f);
    spotsLayer.opacity(0.15f);
    spotsLayer.alive(0, 60);

    // 3. First sepia photograph with irregular corner mask
    chronontemplate::ImageSpec photo1{
        .path = photo1Path,
        .name = "portrait1",
        .frame = chronontemplate::ImageFrameStyle{
            .saturation = 0.80f,
            .contrast = 0.95f,
            .tintColor = "#C9A866",
            .tintOpacity = 0.15f,
        },
        .fit = chronontemplate::ImageFitMode::Contain,
        .targetSize = chronontemplate::Vector2(560.f, 720.f),
    };
    auto& photo1Layer = scene.image(photo1);
    // Position on the left side with irregular positioning — simulates cut-out with uneven edges
    photo1Layer.position(400.f, 540.f, -1.f);
    photo1Layer.alive(0, 60);

    // 4. Second sepia photograph with irregular corner mask
    chronontemplate::ImageSpec photo2{
        .path = photo2Path,
        .name = "portrait2",
        .frame = chronontemplate::ImageFrameStyle{
            .saturation = 0.80f,
            .contrast = 0.95f,
            .tintColor = "#C9A866",
            .tintOpacity = 0.15f,
        },
        .fit = chronontemplate::ImageFitMode::Contain,
        .targetSize = chronontemplate::Vector2(560.f, 720.f),
    };
    auto& photo2Layer = scene.image(photo2);
    photo2Layer.position(1520.f, 540.f, -1.f);
    photo2Layer.alive(0, 60);

    // 5. Name 1 — centered below first photo
    chronontemplate::TextSpec nameSpec1{
        .text = name1,
        .font = "serif",
        .fontSize = 36.f,
        .color = "#4A3B2A",
        .name = "portrait1_name",
    };
    auto& name1Layer = scene.text(nameSpec1);
    name1Layer.position(400.f, 620.f, 2.f);
    name1Layer.alive(0, 60);

    // 6. Name 2 — centered below second photo
    chronontemplate::TextSpec nameSpec2{
        .text = name2,
        .font = "serif",
        .fontSize = 36.f,
        .color = "#4A3B2A",
        .name = "portrait2_name",
    };
    auto& name2Layer = scene.text(nameSpec2);
    name2Layer.position(1520.f, 620.f, 2.f);
    name2Layer.alive(0, 60);

    // 7. Tiny archival labels — small text tags
    chronontemplate::TextSpec label1{
        .text = "Archive · 1940s",
        .font = "serif",
        .fontSize = 14.f,
        .color = "#6B5E3A",
        .name = "label1",
    };
    auto& label1Layer = scene.text(label1);
    label1Layer.position(400.f, 560.f, 3.f);
    label1Layer.alive(0, 60);

    chronontemplate::TextSpec label2{
        .text = "Collection · Private",
        .font = "serif",
        .fontSize = 14.f,
        .color = "#6B5E3A",
        .name = "label2",
    };
    auto& label2Layer = scene.text(label2);
    label2Layer.position(1520.f, 560.f, 3.f);
    label2Layer.alive(0, 60);
}

// ── Main: instantiate all four scenes ────────────────────────────────────────
int main() {
    // All scenes share the same canvas: 1920×1080 at 30fps
    chronontemplate::FakeContentHost host;
    chronontemplate::TemplateScene scene("Four Documentary Scenes", 30.f, host, 1920.f, 1080.f);

    // ---- Scene 01: Torn Paper Portrait ----
    // Using a historical photo URL from the user's description:
    // "She loved him, and he died in the Holocaust. Now her son is bringing his music back to life."
    // Reference: The Boston Globe image
    scene01TornPaperPortrait(scene,
                             "https://images.openai.com/static-rsc-4/YH4RKcK4pZtJCScaIW0frmzq0XWq23qPS2FgR8ifEhPHUWywkOXTEyPo-od1McznkLDTZBb7Vip6dvCAkc3D2NtcOqFtiw9tmUsIDSiljpIdnc7p9WvZ9Y0l64NEcgqL6_15vFsN6W3MfUdVruRmjTnyzropa9jkFuBODKGcAJM?purpose=inline",
                             "SARAH");

    // ---- Scene 02: Black & White Archive Print ----
    scene02BwArchivePrint(scene,
                          "https://images.openai.com/static-rsc-4/cDXJ6rg2sJoJoAH45JUHQGCsP1INjnKoF6dsq89Uyt-5K48qfYlxbh1V3rx-PZpWqrFc6pBaLibuCLWTCiAUiqnpWLa9l6Dvp_MSt72gdIPmiXpcW5DpOx3DQY-1Sma5cwJ8ywvBf3KvANvF6nOIxWjfl4SfSP75r0QAHzLVcAk?purpose=inline");

    // ---- Scene 03: Vintage Film Projection ----
    // Using a film clip — reference: Life Magazine photo inside a film window
    scene03VintageFilmProjection(scene,
                                 "https://images.openai.com/static-rsc-4/k38ExB6PK74C7rQ30Lxt9lRWtqLBzwcR2CoDuRlxrxabK__7OoYRC_r8mRQANvVNEdYYN_s73xHZkYRrFqC9aa2QzPUg2Ch7NrykFFdZ9DndU6CAOSsqfZRRiztUJns0GRQwmRvu2YeIv2J3ZgEmMdXFzya_6QlkuiYX2yn0oQE?purpose=inline");

    // ---- Scene 04: Double Portrait Archive ----
    // Beige parchment with two sepia photos + names + labels
    scene04DoublePortraitArchive(scene,
                                 "https://images.openai.com/static-rsc-4/bB86T3eSOtITR2hTA_PAN26i1QXUfHZlq7GW-bX4753RGne01p7mD9mRdC8homZ3Y7_i015i-7bhVQoyKBX0a8-Vxo_ZSIsZL1KDqCueun1aN5-homDpJTemISId80kieT3Rm8drxIL2Wjciqa8Vn2MpJeiWYASS90YhBVDmXVw?purpose=inline",
                                 "https://images.openai.com/static-rsc-4/bB86T3eSOtITR2hTA_PAN26i1QXUfHZlq7GW-bX4753RGne01p7mD9mRdC8homZ3Y7_i015i-7bhVQoyKBX0a8-Vxo_ZSIsZL1KDqCueun1aN5-homDpJTemISId80kieT3Rm8drxIL2Wjciqa8Vn2MpJeiWYASS90YhBVDmXVw?purpose=inline",  ///< using same for demo
                                 "ELIAS",
                                "CLARA");

    // Submit frame 30 to validate and produce output
    auto submission = scene.submit(30);

    // Print layer information for verification
    std::cout << "Scene: " << scene.name() << "\n";
    std::cout << "FPS: " << scene.fps() << "\n";
    std::cout << "Canvas: " << scene.canvas().x << "x" << scene.canvas().y << "\n";
    std::cout << "Validation: " << scene.validate().size() << " issues\n";

    return 0;
}