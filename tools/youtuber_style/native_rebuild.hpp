#pragma once

#include "common.hpp"

namespace chronon::youtuber {

inline void rect(BLContext& c, double x, double y, double w, double h, BLRgba32 color) {
    c.setFillStyle(color); c.fillRect(BLRect(x, y, w, h));
}
inline void line(BLContext& c, double x1, double y1, double x2, double y2,
                 BLRgba32 color, double width = 5.0) {
    c.setStrokeStyle(color); c.setStrokeWidth(width); c.strokeLine(BLPoint(x1,y1), BLPoint(x2,y2));
}

// ── Visual Venture Inked Brushed Line with authentic Line-Boil (15fps) ────────
inline void brushedLine(BLContext& c, double x1, double y1, double x2, double y2,
                        BLRgba32 color, double width = 6.0, int frameIdx = 0, double wobbleAmp = 3.5) {
    double dx = x2 - x1;
    double dy = y2 - y1;
    double dist = std::hypot(dx, dy);
    if (dist < 1.0) return;

    double perpX = -dy / dist;
    double perpY = dx / dist;

    // Step-printed line boil every 2 frames (~15fps hand-drawn cadence)
    uint32_t boilSeed = static_cast<uint32_t>((frameIdx / 2) * 997 + static_cast<int>(x1 * 13.0 + y1 * 7.0));
    int numSegs = std::max(4, static_cast<int>(dist / 24.0));

    BLPath path;
    path.moveTo(x1, y1);

    for (int i = 1; i < numSegs; ++i) {
        double frac = static_cast<double>(i) / numSegs;
        double bx = x1 + dx * frac;
        double by = y1 + dy * frac;

        // Sine envelope to anchor endpoints
        double edgeDamp = std::sin(frac * 3.1415926535);

        boilSeed = boilSeed * 1664525u + 1013904223u;
        double rnd = (static_cast<double>(boilSeed & 0xFFFF) / 32768.0) - 1.0;
        double wobble = (std::sin(frac * 8.0 + boilSeed * 0.05) * 0.7 + rnd * 0.6) * wobbleAmp * edgeDamp;

        path.lineTo(bx + perpX * wobble, by + perpY * wobble);
    }
    path.lineTo(x2, y2);

    // Layer 1: Soft ink feathering / bleed
    c.setStrokeStyle(BLRgba32(color.r(), color.g(), color.b(), static_cast<uint32_t>(color.a() * 0.45)));
    c.setStrokeWidth(width * 1.5);
    c.strokePath(path);

    // Layer 2: Core ink stroke
    c.setStrokeStyle(color);
    c.setStrokeWidth(width);
    c.strokePath(path);
}

// ── Visual Venture Inked Brushed Box with Line-Boil ───────────────────────────
inline void brushedBox(BLContext& c, double x, double y, double w, double h,
                       BLRgba32 color, double width = 6.0, int frameIdx = 0, double wobbleAmp = 3.5) {
    brushedLine(c, x, y, x + w, y, color, width, frameIdx, wobbleAmp);
    brushedLine(c, x + w, y, x + w, y + h, color, width, frameIdx + 1, wobbleAmp);
    brushedLine(c, x + w, y + h, x, y + h, color, width, frameIdx + 2, wobbleAmp);
    brushedLine(c, x, y + h, x, y, color, width, frameIdx + 3, wobbleAmp);
}

// ── Visual Venture Corner Brackets [ ] with Rotation ──────────────────────────
inline void brushedReticle(BLContext& c, double cx, double cy, double halfSize,
                           double armLen, double angleDeg, BLRgba32 color,
                           double width = 6.0, int frameIdx = 0, double wobbleAmp = 3.0) {
    double rad = angleDeg * 3.1415926535 / 180.0;
    double cosA = std::cos(rad);
    double sinA = std::sin(rad);

    auto rotPt = [&](double px, double py) -> BLPoint {
        return BLPoint(px * cosA - py * sinA + cx, px * sinA + py * cosA + cy);
    };

    // TL
    BLPoint p0 = rotPt(-halfSize, -halfSize);
    BLPoint p0_r = rotPt(-halfSize + armLen, -halfSize);
    BLPoint p0_d = rotPt(-halfSize, -halfSize + armLen);
    brushedLine(c, p0.x, p0.y, p0_r.x, p0_r.y, color, width, frameIdx, wobbleAmp);
    brushedLine(c, p0.x, p0.y, p0_d.x, p0_d.y, color, width, frameIdx + 1, wobbleAmp);

    // TR
    BLPoint p1 = rotPt(halfSize, -halfSize);
    BLPoint p1_l = rotPt(halfSize - armLen, -halfSize);
    BLPoint p1_d = rotPt(halfSize, -halfSize + armLen);
    brushedLine(c, p1.x, p1.y, p1_l.x, p1_l.y, color, width, frameIdx + 2, wobbleAmp);
    brushedLine(c, p1.x, p1.y, p1_d.x, p1_d.y, color, width, frameIdx + 3, wobbleAmp);

    // BR
    BLPoint p2 = rotPt(halfSize, halfSize);
    BLPoint p2_l = rotPt(halfSize - armLen, halfSize);
    BLPoint p2_u = rotPt(halfSize, halfSize - armLen);
    brushedLine(c, p2.x, p2.y, p2_l.x, p2_l.y, color, width, frameIdx + 4, wobbleAmp);
    brushedLine(c, p2.x, p2.y, p2_u.x, p2_u.y, color, width, frameIdx + 5, wobbleAmp);

    // BL
    BLPoint p3 = rotPt(-halfSize, halfSize);
    BLPoint p3_r = rotPt(-halfSize + armLen, halfSize);
    BLPoint p3_u = rotPt(-halfSize, halfSize - armLen);
    brushedLine(c, p3.x, p3.y, p3_r.x, p3_r.y, color, width, frameIdx + 6, wobbleAmp);
    brushedLine(c, p3.x, p3.y, p3_u.x, p3_u.y, color, width, frameIdx + 7, wobbleAmp);
}

// ── 3D Radial Shaded Celestial Sphere with Specular Highlight ─────────────────
inline void shadedSphere(BLContext& c, double cx, double cy, double r,
                         BLRgba32 baseColor, double lightXOffset = -0.35, double lightYOffset = -0.45) {
    if (r <= 2.0) {
        c.setFillStyle(baseColor);
        c.fillCircle(BLCircle(cx, cy, r));
        return;
    }

    double lx = cx + lightXOffset * r;
    double ly = cy + lightYOffset * r;

    // Outer rim glow
    c.setStrokeStyle(BLRgba32(baseColor.r(), baseColor.g(), baseColor.b(), 60));
    c.setStrokeWidth(4.0);
    c.strokeCircle(BLCircle(cx, cy, r + 3.0));

    // Multi-pass gradient stepping for 3D sphere volume
    int steps = static_cast<int>(r);
    for (int s = steps; s >= 1; s -= 2) {
        double frac = static_cast<double>(s) / r;
        double stepCx = lx + (cx - lx) * frac;
        double stepCy = ly + (cy - ly) * frac;
        double factor = std::pow(1.0 - frac, 1.3);

        uint32_t cr = std::min(255, static_cast<int>(baseColor.r() * (0.35 + 0.65 * (1.0 - frac * 0.8)) + 255.0 * factor * 0.95));
        uint32_t cg = std::min(255, static_cast<int>(baseColor.g() * (0.35 + 0.65 * (1.0 - frac * 0.8)) + 255.0 * factor * 0.95));
        uint32_t cb = std::min(255, static_cast<int>(baseColor.b() * (0.35 + 0.65 * (1.0 - frac * 0.8)) + 255.0 * factor * 0.95));

        c.setFillStyle(BLRgba32(cr, cg, cb, 255));
        c.fillCircle(BLCircle(stepCx, stepCy, s));
    }

    // Specular pinpoint glint
    c.setFillStyle(BLRgba32(255, 255, 255, 240));
    c.fillCircle(BLCircle(lx - r * 0.12, ly - r * 0.12, std::max(2.0, r * 0.22)));
}

// ── Volumetric Conical Light Beam with Radial Falloff ─────────────────────────
inline void volumetricLightCone(BLContext& c, double apexX, double apexY,
                                double bottomWidth, double height,
                                BLRgba32 beamColor, double pulse = 1.0) {
    BLPath cone;
    cone.moveTo(apexX, apexY);
    cone.lineTo(apexX + bottomWidth * 0.5 * pulse, apexY + height);
    cone.lineTo(apexX - bottomWidth * 0.5 * pulse, apexY + height);
    cone.close();

    // Outer soft beam
    c.setFillStyle(BLRgba32(beamColor.r(), beamColor.g(), beamColor.b(), static_cast<uint32_t>(beamColor.a() * 0.35)));
    c.fillPath(cone);

    // Inner bright core beam
    BLPath innerCone;
    innerCone.moveTo(apexX, apexY);
    innerCone.lineTo(apexX + bottomWidth * 0.22 * pulse, apexY + height);
    innerCone.lineTo(apexX - bottomWidth * 0.22 * pulse, apexY + height);
    innerCone.close();

    c.setFillStyle(BLRgba32(beamColor.r(), beamColor.g(), beamColor.b(), static_cast<uint32_t>(beamColor.a() * 0.65)));
    c.fillPath(innerCone);

    // Apex emitter
    c.setFillStyle(BLRgba32(255, 255, 255, 240));
    c.fillCircle(BLCircle(apexX, apexY, 24.0));
    c.setStrokeStyle(BLRgba32(255, 255, 255, 90));
    c.setStrokeWidth(6.0);
    c.strokeCircle(BLCircle(apexX, apexY, 48.0));
}

// ── Target Lock-on Reticle with Pulsing Rings & Crosshairs ────────────────────
inline void targetLockon(BLContext& c, double cx, double cy, double radius,
                         BLRgba32 color, int frameIdx = 0) {
    double pulse = 1.0 + 0.12 * std::sin(frameIdx * 0.4);
    double r = radius * pulse;

    // Rings
    c.setStrokeStyle(color);
    c.setStrokeWidth(5.0);
    c.strokeCircle(BLCircle(cx, cy, r));

    c.setStrokeStyle(BLRgba32(color.r(), color.g(), color.b(), 140));
    c.setStrokeWidth(2.5);
    c.strokeCircle(BLCircle(cx, cy, std::max(2.0, r - 8.0)));

    // Crosshairs
    double tick = 16.0;
    line(c, cx - r - tick, cy, cx - r, cy, color, 5.0);
    line(c, cx + r, cy, cx + r + tick, cy, color, 5.0);
    line(c, cx, cy - r - tick, cx, cy - r, color, 5.0);
    line(c, cx, cy + r, cx, cy + r + tick, color, 5.0);
}

// ── Dynamic Continuous Film Grain & Archival Dust/Scratches ───────────────────
inline void applyContinuousFilmGrain(BLImage& img, int frameIdx, float intensity = 12.0f, int dustCount = 30) {
    BLImageData data;
    if (img.getData(&data) != BL_SUCCESS) return;

    int w = data.size.w;
    int h = data.size.h;
    uint8_t* pixels = static_cast<uint8_t*>(data.pixelData);
    intptr_t stride = data.stride;

    uint32_t seed = static_cast<uint32_t>(frameIdx * 104729u + 777u);

    // Fast deterministic pseudo-Gaussian grain modulation
    for (int y = 0; y < h; ++y) {
        uint32_t* row = reinterpret_cast<uint32_t*>(pixels + y * stride);
        for (int x = 0; x < w; ++x) {
            seed = seed * 1664525u + 1013904223u;
            int r1 = static_cast<int>(seed & 0xFF);
            seed = seed * 1664525u + 1013904223u;
            int r2 = static_cast<int>(seed & 0xFF);
            seed = seed * 1664525u + 1013904223u;
            int r3 = static_cast<int>(seed & 0xFF);

            int noise = static_cast<int>(((r1 + r2 + r3) / 3 - 128) * (intensity / 128.0f));

            uint32_t pix = row[x];
            int b = std::clamp(static_cast<int>(pix & 0xFF) + noise, 0, 255);
            int g = std::clamp(static_cast<int>((pix >> 8) & 0xFF) + noise, 0, 255);
            int r = std::clamp(static_cast<int>((pix >> 16) & 0xFF) + noise, 0, 255);
            uint32_t a = (pix >> 24) & 0xFF;

            row[x] = static_cast<uint32_t>(b | (g << 8) | (r << 16) | (a << 24));
        }
    }

    // Dynamic archival dust hairs and flecks
    BLContext ctx(img);
    for (int i = 0; i < dustCount; ++i) {
        seed = seed * 1664525u + 1013904223u;
        double sx = static_cast<double>(seed % w);
        seed = seed * 1664525u + 1013904223u;
        double sy = static_cast<double>(seed % h);
        seed = seed * 1664525u + 1013904223u;
        uint32_t bright = 140u + (seed % 95u);

        if ((seed % 10) > 5) {
            seed = seed * 1664525u + 1013904223u;
            double hx2 = sx + static_cast<double>(static_cast<int>(seed % 17) - 8);
            seed = seed * 1664525u + 1013904223u;
            double hy2 = sy + static_cast<double>(static_cast<int>(seed % 17) - 8);
            line(ctx, sx, sy, hx2, hy2, BLRgba32(bright, bright, bright, 220), 2.0);
        } else {
            ctx.setFillStyle(BLRgba32(bright, bright, bright, 230));
            ctx.fillCircle(BLCircle(sx, sy, 2.0));
        }
    }
}

inline void glowLine(BLContext& c, double x1, double y1, double x2, double y2,
                     BLRgba32 color, double width = 10.0) {
    line(c,x1,y1,x2,y2,BLRgba32(color.r(),color.g(),color.b(),28),width*5.0);
    line(c,x1,y1,x2,y2,BLRgba32(color.r(),color.g(),color.b(),85),width*2.0);
    line(c,x1,y1,x2,y2,color,width);
}
inline void glowCircle(BLContext& c, double x, double y, double r, BLRgba32 color, double width=8.0) {
    c.setStrokeStyle(BLRgba32(color.r(),color.g(),color.b(),26)); c.setStrokeWidth(width*5); c.strokeCircle(BLCircle(x,y,r));
    c.setStrokeStyle(BLRgba32(color.r(),color.g(),color.b(),80)); c.setStrokeWidth(width*2); c.strokeCircle(BLCircle(x,y,r));
    c.setStrokeStyle(color); c.setStrokeWidth(width); c.strokeCircle(BLCircle(x,y,r));
}
inline void glowText(BLContext& c, BLPoint p, const BLFont& f, const std::string& s, BLRgba32 color) {
    for (int i=0;i<3;++i) { c.setFillStyle(BLRgba32(color.r(),color.g(),color.b(),32-8*i)); c.fillUtf8Text(p,f,s.c_str(),s.size()); }
    c.setFillStyle(color); c.fillUtf8Text(p,f,s.c_str(),s.size());
}
inline void drawFigure(BLContext& c, double x, double y, double scale, BLRgba32 color, int pose=0) {
    double r=62*scale;
    glowCircle(c,x,y-250*scale,r,color,9*scale);
    glowLine(c,x,y-185*scale,x,y+40*scale,color,14*scale);
    glowLine(c,x,y-105*scale,x-85*scale,y+10*scale,color,12*scale);
    glowLine(c,x,y-105*scale,x+85*scale,y+10*scale,color,12*scale);
    glowLine(c,x,y+40*scale,x-65*scale,y+200*scale,color,13*scale);
    glowLine(c,x,y+40*scale,x+65*scale,y+200*scale,color,13*scale);
    if (pose==1) {
        glowLine(c,x-4*scale,y-125*scale,x+155*scale,y-315*scale,color,11*scale);
        glowCircle(c,x+165*scale,y-335*scale,37*scale,color,6*scale);
    } else if (pose==2) {
        glowLine(c,x+10*scale,y-95*scale,x+165*scale,y-155*scale,color,11*scale);
        glowLine(c,x+160*scale,y-155*scale,x+235*scale,y-115*scale,color,9*scale);
    }
}
inline void glowBox(BLContext& c,double x,double y,double w,double h,BLRgba32 color,double stroke=8) {
    for (int n=3;n>0;--n) { c.setStrokeStyle(BLRgba32(color.r(),color.g(),color.b(),25*n)); c.setStrokeWidth(stroke*n); c.strokeRect(BLRect(x,y,w,h)); }
    c.setStrokeStyle(color); c.setStrokeWidth(stroke); c.strokeRect(BLRect(x,y,w,h));
}
inline void dark(BLContext& c, BLRgba32 base=BLRgba32(5,5,10,255)) { rect(c,0,0,kW,kH,base); }
inline void centered(BLContext& c,const BLFont& f,const std::string& s,double y,BLRgba32 color=BLRgba32(245,245,245,255),double x=520) {
    c.setFillStyle(color); c.fillUtf8Text(BLPoint(x,y),f,s.c_str(),s.size());
}
inline void drawNewspaper(BLContext& c,double x,double y,double w,double h,double zoom=1.0) {
    c.setFillStyle(BLRgba32(25,25,25,70)); c.fillRect(BLRect(x+25,y+30,w,h));
    c.setFillStyle(BLRgba32(239,236,225,255)); c.fillRect(BLRect(x,y,w,h));
    c.setStrokeStyle(BLRgba32(155,151,143,255)); c.setStrokeWidth(5); c.strokeRect(BLRect(x,y,w,h));
    c.setFillStyle(BLRgba32(40,40,40,255));
    line(c,x+45,y+135,x+w-45,y+135,BLRgba32(60,60,60,255),5);
    const double col=(w-150)/3.0;
    for (int j=0;j<3;++j) {
        double cx=x+50+j*(col+25);
        for (int i=0;i<12;++i) {
            double yy=y+185+i*38;
            double ww=col*(0.68+0.31*((i+j)%4)/3.0);
            rect(c,cx,yy,ww,5,BLRgba32(82,80,75,180));
        }
    }
}
inline void drawGlowBackdrop(BLContext& c,BLRgba32 core) {
    dark(c,BLRgba32(4,4,8,255));
    // Sparse, deterministic dust rather than a visible patterned backdrop.
    uint32_t seed=0x51A7u;
    for(int i=0;i<180;++i) {
        seed=1664525u*seed+1013904223u;
        const double x=(seed%3800u)+20.0;
        seed=1664525u*seed+1013904223u;
        const double y=(seed%2100u)+20.0;
        const double r=(i%7==0)?4.0:2.0;
        c.setFillStyle(BLRgba32(210,185,190,(i%5==0)?70:30)); c.fillCircle(BLCircle(x,y,r));
    }
    c.setFillStyle(BLRgba32(core.r(),core.g(),core.b(),9)); c.fillCircle(BLCircle(kW*.5,kH*.5,440));
}

inline int runNativeScene(int scene) {
    static const int starts[20]={7,34,53,68,91,149,185,239,259,313,329,401,440,474,490,508,527,543,558,575};
    static const int ends[20]  ={30,47,59,80,137,149,208,246,262,317,336,415,457,477,502,515,534,553,560,598};
    static const char* names[20]={"01_subject_floating_push","02_portrait_parallax_drift","03_historical_archive_framing","04_cinematic_title_beat","05_archival_evidence_box","06_documentary_still_evidence","07_archive_scene_pan","08_tactical_radar_graphic","09_newspaper_dossier_zoom","10_highlighter_evidence_sweep","11_subject_tilt_reframe","12_dramatic_cutout_pushin","13_newspaper_headline_wipe","14_archive_document_framing","15_declassified_memo_highlight","16_evidence_callout_card","17_classified_nightvision_reticle","18_witness_portrait_focus","19_chapter_title_card","20_climax_multilayer_parallax"};
    if(scene<1||scene>20) return 2;
    const int idx=scene-1, first=starts[idx], last=ends[idx], count=last-first+1;
    const std::string name=names[idx], outDir=kFinalBase1+"/"+name;
    fs::create_directories(outDir);
    FontBundle fonts=loadFonts();
    BLImage archival,creator,witness,dust,paper,neonFigure,cyanFigure,amberChair,redFigure,globe;
    BLImage creatorPortrait;
    BLImage scene01Start,scene01Mid,scene01End;
    BLImage scene02Photo,scene02Tv;
    BLImage scene04Workstation;
    BLImage scene04Atmosphere;
    BLImage scene05Crystal,scene05FigureCrystal,scene05Computer,scene05Thought;
    BLImage scene06Cloth;
    BLImage scene07Interview;
    BLImage scene08GreenPanels;
    BLImage scene11BrainCard;
    BLImage scene12Final;
    BLImage scene13Anderson;
    BLImage scene20InterviewFinal;
    archival.readFromFile((kAssetsDir+"/generated_archival_meeting_v1.png").c_str());
    creator.readFromFile((kAssetsDir+"/generated_creator_portrait_v1.png").c_str());
    creatorPortrait.readFromFile((kAssetsDir+"/reconstructed_03_creator_v2.png").c_str());
    witness.readFromFile((kAssetsDir+"/generated_witness_interview_v1.png").c_str());
    dust.readFromFile((kAssetsDir+"/13_floating_dust_plate.png").c_str());
    paper.readFromFile((kAssetsDir+"/11_newspaper_paper_plate.png").c_str());
    neonFigure.readFromFile((kAssetsDir+"/generated_neon_figure_v1.png").c_str());
    cyanFigure.readFromFile((kAssetsDir+"/generated_cyan_evidence_figure_v1.png").c_str());
    amberChair.readFromFile((kAssetsDir+"/generated_amber_archive_chair_v1.png").c_str());
    redFigure.readFromFile((kAssetsDir+"/generated_red_archive_figure_v1.png").c_str());
    globe.readFromFile((kAssetsDir+"/generated_stargate_globe_v1.png").c_str());
    if(scene==1) {
        scene01Start.readFromFile((kAssetsDir+"/reconstructed_01_v2.png").c_str());
        scene01Mid.readFromFile((kAssetsDir+"/reconstructed_01_mid_v2.png").c_str());
        scene01End.readFromFile((kAssetsDir+"/reconstructed_01_end_v2.png").c_str());
    }
    if(scene==2) {
        scene02Photo.readFromFile((kAssetsDir+"/reconstructed_02_start_v2.png").c_str());
        scene02Tv.readFromFile((kAssetsDir+"/reconstructed_02_tv_v2.png").c_str());
    }
    if(scene==4) {
        scene04Workstation.readFromFile((kAssetsDir+"/reconstructed_04_workstation_v2.png").c_str());
        scene04Atmosphere.readFromFile((kAssetsDir+"/reconstructed_04_red_atmosphere_v3.png").c_str());
    }
    if(scene==5) {
        scene05Crystal.readFromFile((kAssetsDir+"/reconstructed_05_crystal_v2.png").c_str());
        scene05FigureCrystal.readFromFile((kAssetsDir+"/reconstructed_05_figure_crystal_v2.png").c_str());
        scene05Computer.readFromFile((kAssetsDir+"/reconstructed_05_computer_v2.png").c_str());
        scene05Thought.readFromFile((kAssetsDir+"/reconstructed_05_thought_v2.png").c_str());
    }
    if(scene==6) scene06Cloth.readFromFile((kAssetsDir+"/reconstructed_06_cia_patch_v3.png").c_str());
    if(scene==7) scene07Interview.readFromFile((kAssetsDir+"/reconstructed_07_interview_v2.png").c_str());
    if(scene==8) scene08GreenPanels.readFromFile((kAssetsDir+"/reconstructed_08_green_panels_v3.png").c_str());
    if(scene==11) scene11BrainCard.readFromFile((kAssetsDir+"/reconstructed_11_brain_card_v2.png").c_str());
    if(scene==12) scene12Final.readFromFile((kAssetsDir+"/reconstructed_12_evidence_final_v2.png").c_str());
    if(scene==13) scene13Anderson.readFromFile((kAssetsDir+"/reconstructed_13_anderson_plate_v2.png").c_str());
    if(scene==20) scene20InterviewFinal.readFromFile((kAssetsDir+"/reconstructed_20_interview_final_v2.png").c_str());
    const BLRgba32 magenta(255,74,212,255), amber(255,150,54,255), cyan(65,245,229,255), red(255,65,76,255), green(51,255,76,255), gold(255,207,37,255);
    for(int frame=first;frame<=last;++frame) {
        // The reference extraction contains no frame_0108.png; retain that
        // gap rather than writing a fabricated frame into the sequence.
        if(scene==5 && frame==108) continue;
        const double t=count==1?0.5:double(frame-first)/(count-1);
        const double e=easeInOutCubic(t);
        BLImage img(kW/2,kH/2,BL_FORMAT_PRGB32); BLContext c(img); c.clearAll(); c.scale(0.5);
        switch(scene) {
        case 1: {
            auto cameraPlane=[&](const BLImage& plate,double scale,double dx,double dy,double alpha) {
                if(plate.empty()||alpha<=0.001) return;
                c.save();
                c.setGlobalAlpha(float(std::clamp(alpha,0.0,1.0)));
                const double w=kW*scale,h=kH*scale;
                c.blitImage(BLRect((kW-w)*.5+dx,(kH-h)*.5+dy,w,h),plate);
                c.restore();
            };
            // The source is a 2.5D sequence of changing image plates. Dolly
            // back from the opening close-up, then dissolve between independently
            // rebuilt wide compositions at the same narrative beats.
            if(t<.44) {
                const double q=easeInOutCubic(std::min(1.0,t/.44));
                cameraPlane(scene01Start,1.0-.18*q,-130*q,20*q,1.0);
                if(t>.37) cameraPlane(scene01Mid,1.0,-10,0,easeInOutCubic((t-.37)/.07));
            } else if(t<.78) {
                const double q=easeInOutCubic((t-.44)/.34);
                cameraPlane(scene01Mid,.96+.08*q,-8+16*q,0,1.0);
                if(t>.71) cameraPlane(scene01End,1.0,0,0,easeInOutCubic((t-.71)/.07));
            } else {
                const double q=easeInOutCubic((t-.78)/.22);
                cameraPlane(scene01End,1.0+.09*q,0,0,1.0);
            }
            break; }
        case 2: {
            dark(c,BLRgba32(5,5,8,255));
            const double photoAlpha=t<.40?1.0:1.0-easeInOutCubic(std::min(1.0,(t-.40)/.16));
            const double tvAlpha=t<.40?0.0:t>.56?1.0:easeInOutCubic((t-.40)/.16);
            auto plane=[&](const BLImage& plate,double scale,double dx,double dy,double alpha) {
                if(plate.empty()||alpha<=.001) return;
                c.save(); c.setGlobalAlpha(float(alpha));
                const double w=kW*scale,h=kH*scale;
                c.blitImage(BLRect((kW-w)*.5+dx,(kH-h)*.5+dy,w,h),plate); c.restore();
            };
            plane(scene02Photo,1.02+.06*e,-90+35*e,-20,photoAlpha);
            plane(scene02Tv,.90+.10*e,0,20,tvAlpha);
            if(t>.50) {
                const double a=std::min(1.0,(t-.50)/.10);
                c.save(); c.setGlobalAlpha(float(a));
                glowText(c,BLPoint(1240,780),fonts.fontTitle,"THIS IS",BLRgba32(235,233,220,255));
                glowText(c,BLPoint(2080,780),fonts.fontTitle,"REAL",BLRgba32(255,218,55,255));
                c.restore();
            }
            break; }
        case 3: {
            dark(c,BLRgba32(31,31,33,255));
            // Dense channel page, framed like the close crop in the reference.
            rect(c,1720,0,2120,510,BLRgba32(29,26,24,255));
            BLGradientStop bannerStops[3]={{0.0,BLRgba32(65,49,41,255)},{0.55,BLRgba32(31,28,29,255)},{1.0,BLRgba32(18,18,21,255)}};
            BLGradient banner(BLLinearGradientValues(1720,30,3840,390),BL_EXTEND_MODE_PAD,bannerStops,3);
            c.setFillStyle(banner); c.fillRoundRect(BLRoundRect(1700,-120,2200,600,38,38));
            centered(c,fonts.fontTitle,"VISUAL VENTURE",95,BLRgba32(245,242,235,255),2050);
            centered(c,fonts.fontTitle,"internet culture",210,BLRgba32(235,219,49,255),2050);
            // Avatar is generated artwork, circle-masked in its own raster layer.
            if(!creatorPortrait.empty()) {
                BLImage avatar(560,560,BL_FORMAT_PRGB32); BLContext ac(avatar); ac.clearAll();
                ac.blitImage(BLRect(0,0,560,560),creatorPortrait);
                ac.setCompOp(BL_COMP_OP_DST_IN); ac.setFillStyle(BLRgba32(255,255,255,255)); ac.fillCircle(BLCircle(280,280,278)); ac.end();
                c.blitImage(BLRect(680,690,820,820),avatar);
            }
            centered(c,fonts.fontHeadline,"Visual Venture",740,BLRgba32(245,245,245,255),1580);
            c.setFillStyle(BLRgba32(245,245,245,255)); c.fillCircle(BLCircle(2820,780,42));
            line(c,2798,782,2817,800,BLRgba32(35,38,42,255),10); line(c,2817,800,2848,760,BLRgba32(35,38,42,255),10);
            centered(c,fonts.fontSubhead,"@VisualVenture",900,BLRgba32(234,234,234,255),1580);
            centered(c,fonts.fontBody,"My mission is to make the world a",1060,BLRgba32(238,238,238,255),1580);
            centered(c,fonts.fontBody,"better place.",1060,BLRgba32(229,209,47,255),2740);
            centered(c,fonts.fontSubhead,"Subscribed",1320,BLRgba32(235,235,235,255),1680);
            c.setStrokeStyle(BLRgba32(235,235,235,255)); c.setStrokeWidth(8); c.strokeCircle(BLCircle(1605,1280,28));
            line(c,1586,1280,1605,1303,BLRgba32(235,235,235,255),8); line(c,1605,1303,1624,1280,BLRgba32(235,235,235,255),8);
            rect(c,660,1640,kW-750,3,BLRgba32(72,72,75,255));
            centered(c,fonts.fontBody,"Home       Videos       Shorts       Playlists       Posts",1770,BLRgba32(210,210,212,255),680);
            c.setStrokeStyle(BLRgba32(210,210,212,255)); c.setStrokeWidth(9); c.strokeCircle(BLCircle(2415,1740,28)); line(c,2436,1761,2462,1787,BLRgba32(210,210,212,255),9);
            rect(c,1020,1860,260,12,BLRgba32(210,210,212,255));
            for(int i=0;i<5;++i) {
                const double x=120+770*i;
                rect(c,x,2000,700,400,BLRgba32(36+i*8,40+i*5,47+i*4,255));
                rect(c,x+22,2025,656,330,BLRgba32(52+i*10,49+i*7,43+i*5,255));
            }
            if(t<.42) { c.save(); c.setGlobalAlpha(float(1.0-easeInOutCubic(t/.42))); for(int i=0;i<16;++i) { const double x=(i%4)*1000+e*430-250, y=(i/4)*430+140; rect(c,x,y,900,510,BLRgba32(42+(i%3)*18,40+(i%4)*15,46+(i%2)*20,255)); } c.restore(); }
            break; }
        case 4: {
            rect(c,0,0,kW,kH,BLRgba32(5,1,2,255));
            if(!scene04Atmosphere.empty()) c.blitImage(BLRect(0,0,kW,kH),scene04Atmosphere);
            rect(c,0,0,kW,kH,BLRgba32(0,0,0,35));
            const double reveal=t<.36?1.0:0.0;
            const std::string chapter="CHAPTER 1";
            c.save(); c.setGlobalAlpha(float(reveal));
            // Build a genuine soft halo from progressively wider low-alpha text strokes.
            c.translate(1190*(1.0-1.34),1780*(1.0-1.2)); c.scale(1.34,1.2);
            c.setStrokeStyle(BLRgba32(255,62,72,22)); c.setStrokeWidth(94); c.strokeUtf8Text(BLPoint(1190,1780),fonts.fontTitle,chapter.c_str(),chapter.size());
            c.setStrokeStyle(BLRgba32(255,78,83,34)); c.setStrokeWidth(48); c.strokeUtf8Text(BLPoint(1190,1780),fonts.fontTitle,chapter.c_str(),chapter.size());
            c.setFillStyle(BLRgba32(255,248,246,255)); c.fillUtf8Text(BLPoint(1190,1780),fonts.fontTitle,chapter.c_str(),chapter.size());
            c.restore();
            rect(c,0,2090,kW,70,red);
            if(t>.36&&!scene04Workstation.empty()) {
                const double a=easeInOutCubic(std::min(1.0,(t-.36)/.64));
                c.save(); c.setGlobalAlpha(float(a));
                const double s=1.0+.025*(1.0-a);
                c.blitImage(BLRect(-kW*(s-1.0)*.5,-kH*(s-1.0)*.5,kW*s,kH*s),scene04Workstation);
                c.restore();
            }
            break; }
        case 5: {
            dark(c,BLRgba32(3,3,8,255));
            auto plate=[&](const BLImage& p,double alpha,double scale,double dx=0,double dy=0) {
                if(p.empty()||alpha<=0.001) return;
                c.save(); c.setGlobalAlpha(float(std::clamp(alpha,0.0,1.0)));
                const double w=kW*scale,h=kH*scale;
                c.blitImage(BLRect((kW-w)*.5+dx,(kH-h)*.5+dy,w,h),p); c.restore();
            };
            if(t<.08) plate(scene05Crystal,1.0,1.0+.04*e);
            else if(t<.18) {
                const double q=easeInOutCubic((t-.08)/.10);
                plate(scene05Crystal,1.0-q,1.04); plate(scene05FigureCrystal,q,1.0+.025*q);
            } else if(t<.65) {
                const double q=easeInOutCubic(std::clamp((t-.31)/.10,0.0,1.0));
                if(t<.41) plate(scene05FigureCrystal,1.0-q,1.03);
                plate(scene05Computer,t<.41?q:1.0,1.0+.05*e,-12*e,8*e);
            } else {
                const double q=easeInOutCubic(std::clamp((t-.65)/.13,0.0,1.0));
                if(t<.78) plate(scene05Computer,1.0-q,1.04);
                plate(scene05Thought,q,1.0+.06*e,-8+18*e,10);
            }
            break; }
        case 6: {
            if(!scene06Cloth.empty()) c.blitImage(BLRect(0,0,kW,kH),scene06Cloth);
            else rect(c,0,0,kW,kH,BLRgba32(15,36,85,255));
            break; }
        case 7: {
            dark(c,BLRgba32(2,2,5,255));
            const double chairScale=1.0-.24*e;
            const double chairAlpha=t<.42?1.0:1.0-easeInOutCubic(std::clamp((t-.42)/.20,0.0,1.0));
            if(!amberChair.empty()&&chairAlpha>.001) { c.save(); c.setGlobalAlpha(float(chairAlpha)); c.blitImage(BLRect(190-500*e,20+90*e,kW*chairScale,kH*chairScale),amberChair); c.restore(); }
            if(t>.42&&!scene07Interview.empty()) {
                const double a=easeInOutCubic(std::clamp((t-.42)/.18,0.0,1.0));
                c.save(); c.setGlobalAlpha(float(a));
                const double s=1.0+.035*e;
                c.blitImage(BLRect((kW-kW*s)*.5-20*e,(kH-kH*s)*.5,kW*s,kH*s),scene07Interview);
                c.restore();
            }
            if(t>.92) {
                c.setFillStyle(BLRgba32(0,0,0,155)); c.fillRoundRect(BLRoundRect(1390,1930,1060,150,24,24));
                centered(c,fonts.fontBody,"on the left side of the page",2030,BLRgba32(246,246,246,255),1460);
            }
            break; }
        case 8: {
            if(t<.28) {
                drawGlowBackdrop(c,amber);
                if(!amberChair.empty()) { c.blitImage(BLRect(0,330,2100,1180),amberChair); c.blitImage(BLRect(1770,330,2100,1180),amberChair); }
                else { drawFigure(c,930,1540,.82,amber,0); drawFigure(c,2870,1540,.82,amber,0); }
                rect(c,kW/2-10,0,20,kH,BLRgba32(235,235,235,255));
                break;
            }
            if(!scene08GreenPanels.empty()) {
                const double s=1.0+.018*e;
                c.blitImage(BLRect((kW-kW*s)*.5,(kH-kH*s)*.5,kW*s,kH*s),scene08GreenPanels);
            }
            break; }
        case 9: case 10: case 14: case 15: {
            rect(c,0,0,kW,kH,BLRgba32(197,197,195,255));
            const BLFont& serif=fonts.fontSerifRegular;
            if(scene==9) {
                const double shift=lerp(0,-150,e);
                c.save(); c.translate(shift,0);
                centered(c,serif,"... Project.",250,BLRgba32(93,92,93,220),-250);
                if(t>.45) { c.setFillStyle(BLRgba32(255,225,35,uint8_t(62+80*e))); c.fillRect(BLRect(1900,1040,1150,126)); }
                centered(c,serif,"primarily involved",1130,BLRgba32(100,100,101,230),-60);
                centered(c,serif,"remote viewing",1130,BLRgba32(39,85,168,255),1940);
                centered(c,serif,"Project was overseen until 1987",1450,BLRgba32(100,100,101,220),-40);
                centered(c,serif,"Albert Stubblebine",1770,BLRgba32(112,110,108,205),-40);
                c.restore();
            }
            if(scene==10) {
                const double width=lerp(18,2920,e), textX=lerp(1600,-1000,e);
                c.setFillStyle(BLRgba32(255,229,0,170)); c.fillRect(BLRect(0,850,width,380));
                centered(c,serif,"Over the years more than 20 psychics were employed.",1120,BLRgba32(35,34,32,255),textX);
                centered(c,serif,"some ended up in psychiatric hospitals, others lost the plot ...",1300,BLRgba32(94,92,90,220),textX);
                centered(c,serif,"obsessed with crop circles and aliens.",1480,BLRgba32(94,92,90,220),textX);
            }
            if(scene==14) {
                rect(c,150,150,kW-300,kH-300,BLRgba32(248,247,241,245));
                line(c,210,420,kW-210,420,BLRgba32(80,78,74,220),5);
                centered(c,serif,"Science Times",360,BLRgba32(52,50,47,255),1150);
                centered(c,serif,"A Powerful New Tool",720,BLRgba32(52,50,47,255),780);
                for(int col=0;col<3;++col) for(int row=0;row<10;++row) {
                    const double x=230+col*1180, y=1050+row*82;
                    const double w=930-((row*53+col*91)%280);
                    rect(c,x,y,w,7,BLRgba32(92,90,86,uint8_t(95+(row%3)*20)));
                }
            }
            if(scene==15) {
                centered(c,serif,"years 1983 and 1984",620,BLRgba32(103,101,99,215),-120);
                c.setFillStyle(BLRgba32(255,226,0,164)); c.fillRect(BLRect(0,900,lerp(1100,2850,e),250));
                centered(c,serif,"... but on those programs.",1140,BLRgba32(38,36,32,255),-160);
                centered(c,serif,"former head of the Defense Intelligence Agency",1480,BLRgba32(100,98,96,220),-130);
            }
            break; }
        case 11: {
            dark(c,BLRgba32(0,0,2,255)); double beam=lerp(0,kW,e); rect(c,0,1160,beam,5,BLRgba32(220,220,225,255));
            if(t>.28&&!scene11BrainCard.empty()) {
                const double a=easeInOutCubic(std::clamp((t-.28)/.44,0.0,1.0));
                c.save(); c.setGlobalAlpha(float(a)); c.blitImage(BLRect(720,-40,2650,1476),scene11BrainCard); c.restore();
            }
            centered(c,fonts.fontBody,"1979",1360,BLRgba32(235,234,226,255),1920);
            c.save(); c.translate(250,0); c.scale(.75,1.0);
            if(t>.35) glowText(c,BLPoint(1000,1540),fonts.fontHeadline,"PROJECT STARGATE CHALLENGE",BLRgba32(255,211,43,255));
            c.restore();
            break; }
        case 12: {
            drawGlowBackdrop(c,cyan);
            if(!cyanFigure.empty()) c.blitImage(BLRect(700-120*e,130-80*e,2200+250*e,2010+160*e),cyanFigure);
            else drawFigure(c,1550,1660,2.1+0.25*e,cyan,1);
            if(t>.62&&!scene12Final.empty()) {
                const double a=easeInOutCubic(std::clamp((t-.62)/.28,0.0,1.0));
                c.save(); c.setGlobalAlpha(float(a)); c.blitImage(BLRect(0,0,kW,kH),scene12Final); c.restore();
            }
            break; }
        case 13: {
            dark(c,BLRgba32(12,8,11,255));
            if(t<=.12&&!redFigure.empty()) c.blitImage(BLRect(1740,520,560,1020),redFigure);
            if(!scene13Anderson.empty()&&t>.12) {
                const double a=easeInOutCubic(std::clamp((t-.12)/.40,0.0,1.0));
                const double s=lerp(.90,1.0,e);
                c.save(); c.setGlobalAlpha(float(a));
                c.blitImage(BLRect((kW-kW*s)*.5,(kH-kH*s)*.5,kW*s,kH*s),scene13Anderson);
                c.restore();
            }
            // Add the exact source byline as native text; no headline is present.
            if(t>.7) { c.save(); c.translate(2290,1140); c.scale(1.55,1.55); glowText(c,BLPoint(0,0),fonts.fontBody,"JACK ANDERSON",BLRgba32(240,232,231,255)); c.restore(); }
            break; }
        case 16: {
            dark(c,BLRgba32(0,0,2,255));
            const double lineEnd=lerp(0,kW,e);
            rect(c,0,1150,lineEnd,7,BLRgba32(230,231,238,255));
            if(t<.28) centered(c,fonts.fontBody,"eventually,",1120,BLRgba32(245,245,245,255),1700);
            if(t>.28) {
                const double a=easeInOutCubic(std::clamp((t-.28)/.45,0.0,1.0));
                c.save(); c.setGlobalAlpha(float(a));
                // A luminous blue title panel like the source card, with no extra frame.
                BLGradientStop stops[3]={{0.0,BLRgba32(4,12,48,255)},{0.55,BLRgba32(16,40,117,255)},{1.0,BLRgba32(2,8,34,255)}};
                BLGradient panel(BLLinearGradientValues(1100,180,2740,1120),BL_EXTEND_MODE_PAD,stops,3);
                c.setFillStyle(panel); c.fillRoundRect(BLRoundRect(1110,185,1620,930,18,18));
                uint32_t star=0x1955u;
                for(int i=0;i<180;++i) {
                    star=1664525u*star+1013904223u; const double x=1130+(star%1580u);
                    star=1664525u*star+1013904223u; const double y=205+(star%890u);
                    const double r=(i%9==0)?3.0:1.5;
                    c.setFillStyle(BLRgba32(190,205,255,uint8_t(24+(i%4)*10))); c.fillCircle(BLCircle(x,y,r));
                }
                glowText(c,BLPoint(1360,500),fonts.fontSerifRegular,"PROJECT",BLRgba32(242,239,232,255));
                glowText(c,BLPoint(1280,745),fonts.fontSerifRegular,"STARGATE",BLRgba32(242,239,232,255));
                c.save(); c.translate(1320*(1.0-.62),900*(1.0-.62)); c.scale(.62,.62);
                centered(c,fonts.fontSerifRegular,"AND REMOTE VIEWING",900,BLRgba32(242,239,232,255),1320); c.restore();
                c.save(); c.translate(1570*(1.0-.62),1010*(1.0-.62)); c.scale(.62,.62);
                centered(c,fonts.fontSerifRegular,"TECHNOLOGY",1010,BLRgba32(242,239,232,255),1570); c.restore();
                c.restore();
            }
            if(t>.55) { const double a=easeInOutCubic((t-.55)/.45); c.save(); c.setGlobalAlpha(float(a)); centered(c,fonts.fontMono,"1995",1345,BLRgba32(245,238,226,255),1770); c.save(); c.translate(1120*(1.0-.78),0); c.scale(.78,1.0); glowText(c,BLPoint(1120,1550),fonts.fontHeadline,"STAR GATE PROJECT TRUTH",gold); c.restore(); c.restore(); }
            break; }
        case 17: {
            rect(c,0,0,kW,kH,BLRgba32(0,4,0,255));
            // The reference fills the whole frame with a CRT screen; the cabinet is off-frame.
            BLGradientStop crtStops[3]={{0.0,BLRgba32(0,17,2,255)},{0.5,BLRgba32(0,38,3,255)},{1.0,BLRgba32(0,17,2,255)}};
            BLGradient crt(BLLinearGradientValues(0,0,kW,kH),BL_EXTEND_MODE_PAD,crtStops,3);
            const double staticAlpha=1.0-easeInOutCubic(std::clamp(t/.24,0.0,1.0));
            if(staticAlpha>.001) {
                rect(c,0,0,kW,kH,BLRgba32(37,39,39,255));
                uint32_t noise=0x5317u;
                for(int i=0;i<2100;++i) {
                    noise=1664525u*noise+1013904223u; const double x=noise%3840u;
                    noise=1664525u*noise+1013904223u; const double y=noise%2160u;
                    const uint8_t v=uint8_t(70+(noise%150u));
                    rect(c,x,y,8+(i%5)*5,5+(i%3)*4,BLRgba32(v,v,v,uint8_t(150*staticAlpha)));
                }
                c.save(); c.setGlobalAlpha(float(staticAlpha));
                c.setFillStyle(BLRgba32(232,232,228,245)); c.fillUtf8Text(BLPoint(1760,1190),fonts.fontTitle,"C",1);
                c.restore();
            }
            c.save(); c.setGlobalAlpha(float(1.0-staticAlpha)); c.setFillStyle(crt); c.fillRect(BLRect(0,0,kW,kH));
            const double flicker=.5+.5*sin(t*6.28318530718);
            const uint8_t scanAlpha=uint8_t(14+10*flicker);
            for(int y=0;y<kH;y+=12) rect(c,0,y,kW,2,BLRgba32(75,255,60,scanAlpha));
            c.save(); c.translate(1120,1220); c.scale(4.2,4.2); glowText(c,BLPoint(0,0),fonts.fontMono,"Shutting down",BLRgba32(39,255,69,uint8_t(226+22*flicker))); c.restore();
            c.restore();
            break; }
        case 18: {
            dark(c,BLRgba32(5,3,4,255));
            if(t<.38) {
                const double a=std::clamp(t/.15,0.0,1.0);
                glowText(c,BLPoint(1380,1160),fonts.fontTitle,"FAKE NEWS",BLRgba32(255,223,226,uint8_t(255*a)));
            } else {
                // The reference is a dark Google results page viewed at an angle.
                c.save(); c.translate(300,80); c.rotate(-.055,BLPoint(1900,1000));
                rect(c,120,140,3300,1820,BLRgba32(24,25,29,255));
                centered(c,fonts.fontBody,"Google",460,BLRgba32(226,226,230,255),340);
                c.setFillStyle(BLRgba32(55,57,64,255)); c.fillRoundRect(BLRoundRect(780,340,2250,115,56,56));
                centered(c,fonts.fontSubhead,"STAR GATE PROJECT: AN OVERVIEW",415,BLRgba32(230,230,234,255),900);
                centered(c,fonts.fontSubhead,"AI Mode       All       Images       Videos       News       Forums",660,BLRgba32(174,178,188,255),650);
                line(c,520,740,3220,740,BLRgba32(91,94,104,255),4);
                centered(c,fonts.fontSubhead,"CIA (.gov)",900,BLRgba32(205,207,214,255),650);
                centered(c,fonts.fontBody,"https://www.cia.gov  ›  readingroom  ›  docs  ›  CIA...",1010,BLRgba32(183,185,194,255),650);
                centered(c,fonts.fontHeadline,"STAR GATE PROJECT: AN OVERVIEW",1180,BLRgba32(185,142,219,255),610);
                centered(c,fonts.fontSubhead,"(S/NF/SG/LIMDIS) Primary focus of the STAR GATE effort:",1320,BLRgba32(218,218,221,255),620);
                centered(c,fonts.fontBody,"parapsychological and related phenomena",1430,BLRgba32(197,198,204,255),620);
                centered(c,fonts.fontBody,"29 pages",1540,BLRgba32(197,198,204,255),620);
                c.restore();
            }
            break; }
        case 19: {
            dark(c,BLRgba32(0,0,0,255)); std::string phrase="just get lucky?"; size_t n=std::min(phrase.size(),size_t(phrase.size()*e+1));
            centered(c,fonts.fontSubhead,phrase.substr(0,n),1120,BLRgba32(240,240,240,255),1600); break; }
        case 20: {
            drawGlowBackdrop(c,red);
            if(t<.35) { glowText(c,BLPoint(1150,1120),fonts.fontTitle,"CHAPTER 2",BLRgba32(255,240,235,255)); rect(c,0,2090,kW,18,red); }
            else { double zoom=lerp(.72,1.08,(t-.35)/.65); double d=2900*zoom;
                if(!globe.empty()) c.blitImage(BLRect(500-(d-2900)*.5,-360-(d-2900)*.5,d,d),globe);
                else { double cx=2150,cy=1050,r=540*zoom; c.setFillStyle(BLRgba32(5,8,20,255)); c.fillCircle(BLCircle(cx,cy,r+40)); c.setFillStyle(BLRgba32(24,49,94,255)); c.fillCircle(BLCircle(cx,cy,r)); c.setFillStyle(BLRgba32(216,211,195,255)); c.fillEllipse(BLEllipse(cx,cy,r*.86,r*.47)); }
                if(t>.72 && !scene20InterviewFinal.empty()) {
                    const double a=easeInOutCubic(std::clamp((t-.72)/.20,0.0,1.0));
                    c.save(); c.setGlobalAlpha(float(a));
                    // Crossfade into the interview composition and continue a restrained camera push.
                    const double s=1.0+.025*e;
                    c.blitImage(BLRect((kW-kW*s)*.5,(kH-kH*s)*.5,kW*s,kH*s),scene20InterviewFinal);
                    c.restore();
                }
            }
            break; }
        }
        c.end();
        std::ostringstream path; path<<outDir<<"/frame_"<<std::setw(4)<<std::setfill('0')<<frame<<".png";
        if(img.writeToFile(path.str().c_str())!=BL_SUCCESS) { std::cerr<<"Failed to write "<<path.str()<<std::endl; return 3; }
    }
    std::cout<<"Rendered "<<name<<" frames "<<first<<"-"<<last<<" at "<<kW/2<<"x"<<kH/2<<std::endl;
    return 0;
}

} // namespace chronon::youtuber
