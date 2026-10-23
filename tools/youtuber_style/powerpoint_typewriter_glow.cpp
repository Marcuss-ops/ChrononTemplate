// PowerPoint-style typewriter with keyboard scramble and a soft glow.
//
// Every character slot flickers through random keyboard glyphs shortly before
// its real character settles, so the phrase appears to be decoded left to
// right. The reveal finishes early enough to hold the full sentence under a
// breathing glow.
//
// Usage:
//   powerpoint_typewriter_glow [--text "..."] [--seconds 3.2] [--fps 30]
//                              [--out out/powerpoint_typewriter_glow]
//
// Frames are rendered at 1920x1080 from a 3840x2160 logical canvas, matching
// the other youtuber_style scenes.

#include "common.hpp"

#include <cstdint>
#include <cstdlib>

namespace {

using namespace chronon::youtuber;

constexpr double kFitWidth = 3160.0;
constexpr double kLineHeightFactor = 1.18;

// The characters a slot scrambles through before it settles.
const std::string kKeyboardGlyphs =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "#$%&@*+=<>/\\|!?_-~^";

inline uint64_t mix64(uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

inline double smoothstep(double edge0, double edge1, double x) {
    if (edge1 <= edge0) return x >= edge1 ? 1.0 : 0.0;
    const double t = std::clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

// Overshoots slightly past 1.0 before settling, which gives each revealed
// character its pop instead of letting it fade in flat.
inline double easeOutBack(double x) {
    constexpr double c1 = 1.70158;
    constexpr double c3 = c1 + 1.0;
    const double p = std::clamp(x, 0.0, 1.0);
    return 1.0 + c3 * std::pow(p - 1.0, 3.0) + c1 * std::pow(p - 1.0, 2.0);
}

inline BLRgba32 withAlpha(BLRgba32 color, double alpha) {
    const double a = std::clamp(alpha, 0.0, 1.0);
    return BLRgba32(color.r(), color.g(), color.b(),
                    uint8_t(std::lround(a * 255.0)));
}

inline double textWidth(const BLFont& font, const std::string& text) {
    BLGlyphBuffer gb;
    gb.setUtf8Text(text.c_str(), text.size());
    font.shape(gb);
    BLTextMetrics tm;
    font.getTextMetrics(gb, tm);
    return tm.advance.x;
}

// UTF-8 aware split so accented characters stay intact.
std::vector<std::string> splitUtf8CodePoints(const std::string& text) {
    std::vector<std::string> out;
    for (size_t i = 0; i < text.size();) {
        const unsigned char lead = static_cast<unsigned char>(text[i]);
        size_t len = 1;
        if ((lead & 0xE0) == 0xC0) len = 2;
        else if ((lead & 0xF0) == 0xE0) len = 3;
        else if ((lead & 0xF8) == 0xF0) len = 4;
        len = std::min(len, text.size() - i);
        out.push_back(text.substr(i, len));
        i += len;
    }
    return out;
}

std::string resolveFontPath() {
    const std::vector<std::string> candidates = {
        kFontsDir + "/Inter-Bold.ttf",
        // Same font tree when the project is opened from WSL/Linux.
        "/mnt/c/Users/pater/Pyt/Chronon3d/assets/fonts/Inter-Bold.ttf",
        "assets/fonts/Inter-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    };
    for (const auto& path : candidates) {
        if (fs::exists(path)) return path;
    }
    return {};
}

struct PlacedChar {
    std::string bytes;
    double advance = 0.0;
    int index = 0;
};

struct Line {
    std::vector<PlacedChar> chars;
    double width = 0.0;
};

struct Layout {
    std::vector<Line> lines;
    double fontSize = 160.0;
    double capHeight = 0.0;
    double width = 0.0;
};

Layout buildLayout(const BLFontFace& face, const std::string& text, double fontSize,
                   double maxWidth) {
    Layout layout;
    layout.fontSize = fontSize;

    BLFont font;
    font.createFromFace(face, float(fontSize));
    layout.capHeight = font.metrics().capHeight;

    const double spaceAdvance = textWidth(font, " ");

    // Split into paragraphs on explicit newlines, then wrap words.
    std::vector<std::vector<std::string>> paragraphs(1);
    for (const auto& cp : splitUtf8CodePoints(text)) {
        if (cp == "\n") {
            paragraphs.emplace_back();
        } else if (cp == "\r") {
            continue;
        } else {
            paragraphs.back().push_back(cp);
        }
    }

    int globalIndex = 0;
    for (const auto& paragraph : paragraphs) {
        std::string word;
        std::vector<std::string> words;
        for (const auto& cp : paragraph) {
            if (cp == " " || cp == "\t") {
                if (!word.empty()) {
                    words.push_back(word);
                    word.clear();
                }
            } else {
                word += cp;
            }
        }
        if (!word.empty()) words.push_back(word);

        Line line;
        double lineWidth = 0.0;
        for (const auto& w : words) {
            const double wordWidth = textWidth(font, w);
            const double withSeparator = line.chars.empty() ? wordWidth
                                                            : lineWidth + spaceAdvance + wordWidth;
            if (!line.chars.empty() && withSeparator > maxWidth) {
                layout.lines.push_back(line);
                line = Line{};
                lineWidth = 0.0;
            }
            if (!line.chars.empty()) {
                line.chars.push_back({" ", spaceAdvance, globalIndex++});
                lineWidth += spaceAdvance;
            }
            for (const auto& cp : splitUtf8CodePoints(w)) {
                const double advance = textWidth(font, cp);
                line.chars.push_back({cp, advance, globalIndex++});
                lineWidth += advance;
            }
        }
        layout.lines.push_back(line);
    }

    for (auto& line : layout.lines) {
        for (const auto& ch : line.chars) line.width += ch.advance;
        layout.width = std::max(layout.width, line.width);
    }
    return layout;
}

Layout fitLayout(const BLFontFace& face, const std::string& text) {
    double fontSize = 200.0;
    Layout layout = buildLayout(face, text, fontSize, kFitWidth);
    while (layout.width > kFitWidth && fontSize > 80.0) {
        fontSize *= 0.92;
        layout = buildLayout(face, text, fontSize, kFitWidth);
    }
    // A single unbreakable word can still overflow: shrink to the exact fit.
    if (layout.width > kFitWidth) {
        fontSize *= kFitWidth / layout.width;
        layout = buildLayout(face, text, fontSize, std::max(kFitWidth, layout.width));
    }
    return layout;
}

int totalChars(const Layout& layout) {
    int count = 0;
    for (const auto& line : layout.lines) count += int(line.chars.size());
    return std::max(1, count);
}

double revealTime(int index, int total) {
    constexpr double kRevealStart = 0.10;
    constexpr double kRevealSpan = 0.62;
    if (total <= 1) return kRevealStart;
    return kRevealStart + kRevealSpan * (double(index) / double(total - 1));
}

char scrambleGlyph(int index, int frame) {
    const uint64_t h = mix64(uint64_t(uint32_t(index)) * 0x9E3779B1u ^
                             uint64_t(uint32_t(frame / 2)) * 0x85EBCA6Bu ^
                             0x1B873593u);
    return kKeyboardGlyphs[h % kKeyboardGlyphs.size()];
}

void drawSoftGlow(BLContext& ctx, const Layout& layout, double t, double intro) {
    const double centerY = kH * 0.5;
    const double pulse = 0.78 + 0.22 * std::sin(t * 6.28318530718 * 1.35 - 1.2);
    const double radius = std::max(1450.0, layout.width * 0.82);

    // Blend2D's radial values are (center, center, outerRadius, innerRadius).
    BLGradient halo(BLRadialGradientValues(kW * 0.5, centerY, kW * 0.5, centerY, radius, 0.0));
    halo.addStop(0.0, BLRgba32(96, 214, 255, uint8_t(std::lround(34.0 * pulse * intro))));
    halo.addStop(0.45, BLRgba32(72, 168, 255, uint8_t(std::lround(16.0 * pulse * intro))));
    halo.addStop(1.0, BLRgba32(0, 0, 0, 0));
    ctx.setFillStyle(halo);
    ctx.fillRect(BLRect(0, 0, kW, kH));
}

void drawGlyph(BLContext& ctx, const BLFont& font, const BLPoint& origin,
               const std::string& glyph, BLRgba32 core, BLRgba32 glow,
               double alpha, double fontSize, double glowScale) {
    if (alpha <= 0.002 || glyph == " ") return;

    // Rings of faint offset stamps spread the light without the hard, filled
    // silhouette a very wide glyph stroke would produce.
    struct Ring {
        double radiusFactor;
        double alphaFactor;
        double phase;
        int steps;
    };
    static const Ring rings[] = {
        {0.085, 0.055, 0.00, 8},
        {0.175, 0.030, 0.39, 8},
    };
    for (const auto& ring : rings) {
        const double radius = fontSize * ring.radiusFactor * glowScale;
        for (int i = 0; i < ring.steps; ++i) {
            const double angle = 6.28318530718 * (double(i) / double(ring.steps)) + ring.phase;
            ctx.setFillStyle(withAlpha(glow, alpha * ring.alphaFactor));
            ctx.fillUtf8Text(BLPoint(origin.x + std::cos(angle) * radius,
                                     origin.y + std::sin(angle) * radius),
                             font, glyph.c_str(), glyph.size());
        }
    }

    // Tight rim keeps small glyphs legible, then the solid core on top.
    ctx.setStrokeStyle(withAlpha(glow, alpha * 0.18));
    ctx.setStrokeWidth(fontSize * 0.045 * glowScale);
    ctx.strokeUtf8Text(origin, font, glyph.c_str(), glyph.size());
    ctx.setFillStyle(withAlpha(core, alpha));
    ctx.fillUtf8Text(origin, font, glyph.c_str(), glyph.size());
}

void drawText(BLContext& ctx, const Layout& layout, const BLFont& font, double t,
              double intro, int frame) {
    const int total = totalChars(layout);
    const double lineHeight = layout.fontSize * kLineHeightFactor;
    const double blockHeight = lineHeight * double(layout.lines.size() - 1);
    const double xCenter = kW * 0.5;
    const double centerY = kH * 0.5;

    const BLRgba32 settledColor(244, 250, 255, 255);
    const BLRgba32 settledGlow(96, 214, 255, 255);
    const BLRgba32 scrambleColor(122, 228, 255, 255);
    const BLRgba32 scrambleGlow(58, 170, 255, 255);

    double caretX = xCenter;
    double caretBaseline = centerY;
    bool caretPlaced = false;

    for (size_t li = 0; li < layout.lines.size(); ++li) {
        const Line& line = layout.lines[li];
        const double baseline = centerY - blockHeight * 0.5 + lineHeight * double(li) +
                                layout.capHeight * 0.5;
        double x = xCenter - line.width * 0.5;

        for (const auto& ch : line.chars) {
            const double slotX = x;
            x += ch.advance;

            const double reveal = revealTime(ch.index, total);

            if (t >= reveal) {
                constexpr double kSettleTime = 0.18;
                const double settle = smoothstep(reveal, reveal + kSettleTime, t);
                const double flash = 1.0 - settle;
                const double bodyGlow = 0.72 + 0.28 * settle;

                // Pop: the glyph starts oversized, dips a touch below its final
                // size and springs back to 1.0 around its own center.
                const double popProgress = std::clamp((t - reveal) / kSettleTime, 0.0, 1.0);
                const double popScale = 1.0 + 0.40 * (1.0 - easeOutBack(popProgress));
                // The glyph is opaque from its first frame: a fade-in would hide
                // the oversized start of the pop.
                const double popAlpha = 1.0;
                const double glyphCx = slotX + ch.advance * 0.5;
                const double glyphCy = baseline - layout.capHeight * 0.5;

                ctx.save();
                ctx.translate(glyphCx, glyphCy);
                ctx.scale(popScale);
                ctx.translate(-glyphCx, -glyphCy);

                drawGlyph(ctx, font, BLPoint(slotX, baseline), ch.bytes, settledColor,
                          settledGlow, intro * popAlpha, layout.fontSize,
                          bodyGlow + 0.35 * flash);

                if (flash > 0.01) {
                    // A brief cyan bloom marks the moment the slot resolves.
                    drawGlyph(ctx, font, BLPoint(slotX, baseline), ch.bytes,
                              BLRgba32(235, 252, 255), BLRgba32(150, 240, 255),
                              intro * popAlpha * flash * 0.55, layout.fontSize, 1.3);
                }

                ctx.restore();
                caretX = x;
                caretBaseline = baseline;
                caretPlaced = true;
            } else {
                // Every unresolved slot keeps flickering through keyboard glyphs
                // until its own character settles.
                const double approaches = smoothstep(reveal - 0.24, reveal, t);
                const double flicker = 0.74 + 0.26 *
                    (double((mix64(uint64_t(uint32_t(ch.index)) * 0x27D4EB2Fu ^
                                    uint64_t(uint32_t(frame)) * 0x165667B1u) >> 11) & 1023u) / 1023.0);
                const std::string glyph(1, scrambleGlyph(ch.index, frame));
                const double glyphWidth = textWidth(font, glyph);
                const double centeredX = slotX + (ch.advance - glyphWidth) * 0.5;

                drawGlyph(ctx, font, BLPoint(centeredX, baseline), glyph, scrambleColor,
                          scrambleGlow,
                          intro * (0.34 + 0.34 * approaches) * flicker,
                          layout.fontSize, 0.85);
            }        }
    }

    if (!caretPlaced) {
        const Line& first = layout.lines.front();
        caretX = xCenter - first.width * 0.5;
        caretBaseline = centerY - blockHeight * 0.5 + layout.capHeight * 0.5;
    }

    // Block cursor: blinks while decoding, holds briefly, then fades out.
    const bool typing = t < 0.72;
    const bool blinkOn = !typing || (int(std::floor(t * 2.4)) % 2 == 0);
    const double caretFade = 1.0 - smoothstep(0.78, 0.88, t);
    if (blinkOn && caretFade > 0.01) {
        const double top = caretBaseline - layout.capHeight * 1.04;
        const double bottom = caretBaseline + layout.fontSize * 0.16;
        const double caretWidth = std::max(4.0, layout.fontSize * 0.035);
        const BLRgba32 caretColor = withAlpha(BLRgba32(120, 230, 255), intro * caretFade * 0.9);

        ctx.setFillStyle(withAlpha(BLRgba32(120, 230, 255), intro * caretFade * 0.16));
        ctx.fillRect(BLRect(caretX - caretWidth * 1.6, top - 8, caretWidth * 3.2,
                            (bottom - top) + 16));
        ctx.setFillStyle(caretColor);
        ctx.fillRect(BLRect(caretX, top, caretWidth, bottom - top));
    }
}

int renderScene(const std::string& text, double seconds, int fps,
                const std::string& outDir) {
    const std::string fontPath = resolveFontPath();
    if (fontPath.empty()) {
        std::cerr << "No Inter-Bold.ttf or fallback text font found" << std::endl;
        return 2;
    }

    BLFontFace face;
    if (face.createFromFile(fontPath.c_str()) != BL_SUCCESS) {
        std::cerr << "Failed to load font " << fontPath << std::endl;
        return 2;
    }

    const Layout layout = fitLayout(face, text);
    BLFont font;
    font.createFromFace(face, float(layout.fontSize));

    if (!fs::create_directories(outDir) && !fs::exists(outDir)) {
        std::cerr << "Cannot create output directory " << outDir << std::endl;
        return 3;
    }

    const int frameCount = std::max(1, int(std::lround(seconds * double(fps))));
    for (int frame = 0; frame < frameCount; ++frame) {
        const double t = frameCount == 1 ? 1.0 : double(frame) / double(frameCount - 1);

        BLImage image(kW / 2, kH / 2, BL_FORMAT_PRGB32);
        BLContext ctx(image);
        ctx.clearAll();
        ctx.scale(0.5);

        // Slide background: near-black with a soft vertical falloff.
        BLGradient background(BLLinearGradientValues(0.0, 0.0, 0.0, double(kH)));
        background.addStop(0.0, BLRgba32(10, 13, 20));
        background.addStop(0.55, BLRgba32(6, 8, 13));
        background.addStop(1.0, BLRgba32(2, 3, 6));
        ctx.setFillStyle(background);
        ctx.fillRect(BLRect(0, 0, kW, kH));

        const double intro = smoothstep(0.0, 0.08, t);
        drawSoftGlow(ctx, layout, t, intro);
        drawText(ctx, layout, font, t, intro, frame);

        // Vignette keeps the eye on the sentence.
        BLGradient vignette(BLRadialGradientValues(kW * 0.5, kH * 0.5, kW * 0.5, kH * 0.5,
                                                   kW * 0.74, kW * 0.30));
        vignette.addStop(0.0, BLRgba32(0, 0, 0, 0));
        vignette.addStop(0.58, BLRgba32(0, 0, 0, 46));
        vignette.addStop(1.0, BLRgba32(0, 0, 0, 214));
        ctx.setFillStyle(vignette);
        ctx.fillRect(BLRect(0, 0, kW, kH));

        ctx.end();

        std::ostringstream path;
        path << outDir << "/frame_" << std::setw(4) << std::setfill('0') << (frame + 1)
             << ".png";
        if (image.writeToFile(path.str().c_str()) != BL_SUCCESS) {
            std::cerr << "Failed to write " << path.str() << std::endl;
            return 3;
        }
    }

    std::cout << "Rendered " << frameCount << " frames to " << outDir << " ("
              << kW / 2 << "x" << kH / 2 << ", font " << layout.fontSize << ")"
              << std::endl;
    return 0;
}

void printUsage() {
    std::cout << "Usage: powerpoint_typewriter_glow [options]\n"
                 "  --text <sentence>   text to reveal (default: POWERPOINT TYPEWRITER)\n"
                 "  --seconds <n>       clip length in seconds (default: 3.2)\n"
                 "  --fps <n>           frame rate (default: 30)\n"
                 "  --out <dir>         output directory (default: out/powerpoint_typewriter_glow)\n"
                 "  --help              show this message\n";
}

} // namespace

int main(int argc, char** argv) {
    std::string text = "POWERPOINT TYPEWRITER";
    double seconds = 3.2;
    int fps = 30;
    std::string outDir = "out/powerpoint_typewriter_glow";

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto next = [&](const char* name) -> std::string {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << std::endl;
                std::exit(2);
            }
            return argv[++i];
        };
        if (arg == "--text") text = next("--text");
        else if (arg == "--seconds") seconds = std::max(0.2, std::stod(next("--seconds")));
        else if (arg == "--fps") fps = std::clamp(std::stoi(next("--fps")), 1, 120);
        else if (arg == "--out") outDir = next("--out");
        else if (arg == "--help" || arg == "-h") {
            printUsage();
            return 0;
        } else {
            std::cerr << "Unknown argument " << arg << "\n";
            printUsage();
            return 2;
        }
    }

    if (text.empty()) {
        std::cerr << "--text cannot be empty" << std::endl;
        return 2;
    }
    return renderScene(text, seconds, fps, outDir);
}
