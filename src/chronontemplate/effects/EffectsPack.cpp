#include "chronontemplate/effects/EffectsPack.hpp"

#include <chronon3d/render_plan/color_utils.hpp>

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace chronontemplate::effects {

    namespace {

        struct Ctx {
            TemplateScene& scene;
            const EffectSpec& spec;
            float W;
            float H;
            int dur;
            std::vector<MotionLayerId>& out;
        };

        float clamp01(float v) { return std::clamp(v, 0.f, 1.f); }

        // Deterministic hash in [0, 1): same seed gives the same overlay on any
        // machine, so a distributed or resumed render matches frame for frame.
        float unit(std::uint32_t seed, std::uint32_t idx, std::uint32_t salt) {
            std::uint32_t h = seed * 0x9E3779B1u ^ (idx + 1u) * 0x85EBCA77u ^ (salt + 7u) * 0xC2B2AE3Du;
            h ^= h >> 15;
            h *= 0x2C1B3C6Du;
            h ^= h >> 12;
            h *= 0x297A2D39u;
            h ^= h >> 15;
            return static_cast<float>(h & 0xFFFFFFu) / 16777216.f;
        }

        std::string colorOr(const EffectSpec& spec, const char* fallback) {
            return spec.color.empty() ? std::string(fallback) : spec.color;
        }

        /// Effect strength after the shared spec scaling.
        float scaled(const EffectSpec& spec, float base) {
            return clamp01(base * spec.intensity * spec.opacity);
        }

        ShapeSpec makeShape(const std::string& name, float w, float h, const std::string& color) {
            ShapeSpec s{};
            s.size = chrononmotion::Vector2(std::max(1.f, w), std::max(1.f, h));
            s.fillColor = color;
            s.name = name;
            return s;
        }

        // Author a shape layer alive for the effect window. No opacity is set:
        // the caller chooses a static opacity or animated segments, not both.
        LayerHandle& spawn(Ctx& c, const ShapeSpec& shape, float x, float y) {
            LayerHandle& h = c.scene.shape(shape);
            h.position(x, y);
            h.alive(c.spec.startFrame, c.spec.endFrame);
            c.out.push_back(h.id());
            return h;
        }

        // Static layer with opacity = base * intensity * opacity.
        void solid(Ctx& c, const ShapeSpec& shape, float x, float y, float base) {
            spawn(c, shape, x, y).opacity(scaled(c.spec, base));
        }

        // Fade a layer in from 0 to `peak` and back out to 0 over [start, start+dur).
        void pulse(LayerHandle& h, int start, int dur, float peak) {
            const int fade = std::clamp(dur / 4, 4, 30);
            h.animateOpacity(start, fade, 0.f, peak);
            if (dur - fade > fade)
                h.animateOpacity(start + dur - fade, fade, peak, 0.f);
            else
                h.animateOpacity(start + fade, dur - fade, peak, 0.f);
        }

        // Soft blob from nested flat ellipses (the renderer's radial gradient
        // fill does not produce pixels, so falloff is built from rings).
        // `peak` is the core opacity before spec scaling; every ring shares the
        // same drift and pulse so the blob moves as one body.
        void onion(Ctx& c, const std::string& name, float cx, float cy, float w, float h,
                   const std::string& color, float peak, int rings,
                   const chrononmotion::Vector3& drift, bool breathe) {
            static constexpr float kFractions[] = {1.f, 0.76f, 0.54f, 0.34f, 0.18f, 0.08f};
            static constexpr float kLevels[] = {0.22f, 0.38f, 0.6f, 0.82f, 1.f, 1.f};
            const int count = std::clamp(rings, 2, 6);
            for (int i = 0; i < count; ++i) {
                ShapeSpec s = makeShape(name + "_ring" + std::to_string(i),
                                        w * kFractions[i], h * kFractions[i], color);
                s.geometry = ShapeGeometry::Ellipse;
                LayerHandle& handle = spawn(c, s, cx, cy);
                const float level = scaled(c.spec, peak * kLevels[i]);
                if (breathe)
                    pulse(handle, c.spec.startFrame, c.dur, level);
                else
                    handle.opacity(level);
                if (drift.x != 0.f || drift.y != 0.f || drift.z != 0.f)
                    handle.animatePosition(c.spec.startFrame, c.dur, drift);
            }
        }

        // A soft mass from a cluster of small overlapping dots. This is the
        // same pattern as the (proven) bokeh spots: mid-size translucent
        // ellipses in one onion stack can black out the frame, while small
        // animated dots composite correctly at any layer count.
        void cluster(Ctx& c, const std::string& name, std::uint32_t count,
                     float minD, float maxD, float x0, float x1, float y0, float y1,
                     const std::string& color, float minPeak, float maxPeak,
                     const chrononmotion::Vector3& drift, std::uint32_t salt) {
            for (std::uint32_t i = 0; i < count; ++i) {
                const float d = minD + (maxD - minD) * unit(c.spec.seed, i, salt + 1);
                const float margin = d * 0.5f + 4.f;
                const float cx = std::clamp(x0 + (x1 - x0) * unit(c.spec.seed, i, salt + 2),
                                            margin, c.W - margin);
                const float cy = std::clamp(y0 + (y1 - y0) * unit(c.spec.seed, i, salt + 3),
                                            margin, c.H - margin);
                ShapeSpec s = makeShape(name + "_dot" + std::to_string(i), d, d, color);
                s.geometry = ShapeGeometry::Ellipse;
                LayerHandle& h = spawn(c, s, cx, cy);
                pulse(h, c.spec.startFrame, c.dur,
                      scaled(c.spec, minPeak + (maxPeak - minPeak) * unit(c.spec.seed, i, salt + 4)));
                if (drift.x != 0.f || drift.y != 0.f || drift.z != 0.f)
                    h.animatePosition(c.spec.startFrame, c.dur, drift);
            }
        }

        // Flat frame outline (stroke-only shapes render; gradient fills don't).
        void strokeFrame(Ctx& c, const std::string& name, float w, float h,
                         const std::string& color, float width, float base,
                         float dx, float dy, const chrononmotion::Vector3& drift) {
            ShapeSpec s = makeShape(name, w, h, color);
            s.fillEnabled = false;
            s.strokeColor = color;
            s.strokeWidth = std::max(0.25f, width);
            LayerHandle& handle = spawn(c, s, c.W * 0.5f + dx, c.H * 0.5f + dy);
            handle.opacity(scaled(c.spec, base));
            if (drift.x != 0.f || drift.y != 0.f || drift.z != 0.f)
                handle.animatePosition(c.spec.startFrame, c.dur, drift);
        }

        // ── Film & analog ───────────────────────────────────────────────────

        void lightLeak(Ctx& c) {
            // Main leak sweeps in from the left, secondary answers from the
            // right. Blobs stay fully on-screen: filled ellipses crossing the
            // canvas edge render black in this renderer.
            onion(c, "light_leak_main", c.W * 0.35f, c.H * 0.32f, c.W * 0.6f, c.H * 0.6f,
                  colorOr(c.spec, "#FF8A3D"), 0.75f, 5,
                  chrononmotion::Vector3(c.W * 0.16f, 0.f, 0.f), true);
            onion(c, "light_leak_echo", c.W * 0.7f, c.H * 0.7f, c.W * 0.44f, c.H * 0.4f,
                  colorOr(c.spec, "#FFC46B"), 0.5f, 4,
                  chrononmotion::Vector3(-c.W * 0.1f, 0.f, 0.f), true);
        }

        void filmGrain(Ctx& c) {
            // Coarse animated grain: fine 1.5px noise explodes the file size
            // (140+ MB for 5 s) because every pixel changes every frame.
            ShapeSpec s = makeShape("film_grain", c.W, c.H, colorOr(c.spec, "#808080"));
            s.noiseAmount = 0.15f * c.spec.intensity;
            s.noiseSeed = c.spec.seed;
            s.animatedNoise = true;
            s.noiseSize = 5.f;
            solid(c, s, c.W * 0.5f, c.H * 0.5f, 0.25f);
        }

        void filmScratches(Ctx& c) {
            // Gray scratches: white lines are invisible on a white card.
            for (std::uint32_t i = 0; i < 5; ++i) {
                ShapeSpec s = makeShape("film_scratch_" + std::to_string(i), 2.f, c.H,
                                        colorOr(c.spec, "#B4B4B4"));
                LayerHandle& h = spawn(c, s, c.W * unit(c.spec.seed, i, 3), c.H * 0.5f);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.5f + 0.4f * unit(c.spec.seed, i, 20)));
                h.animatePosition(c.spec.startFrame, c.dur,
                                  chrononmotion::Vector3(16.f * (unit(c.spec.seed, i, 21) - 0.5f) * 2.f,
                                                         0.f, 0.f));
            }
        }

        void filmBurn(Ctx& c) {
            // A fiery mass pushing in from the right, then receding.
            cluster(c, "film_burn", 14, 120.f, 260.f, c.W * 0.5f, c.W * 0.96f,
                    c.H * 0.12f, c.H * 0.88f, colorOr(c.spec, "#FF5A1F"), 0.45f, 0.8f,
                    chrononmotion::Vector3(-c.W * 0.12f, 0.f, 0.f), 30);
        }

        void scanlineInterference(Ctx& c) {
            // Thin horizontal bars, one layer per row. A dense grid geometry
            // (hundreds of thousands of lines) stalls the renderer. The whole
            // stack scrolls down one row over the clip so the crawl is visible.
            constexpr float kRowSpacing = 18.f;
            constexpr float kRowHeight = 2.f;
            int row = 0;
            for (float y = kRowSpacing * 0.5f; y < c.H; y += kRowSpacing, ++row) {
                ShapeSpec s = makeShape("scanline_" + std::to_string(row), c.W, kRowHeight,
                                        colorOr(c.spec, "#000000"));
                LayerHandle& h = spawn(c, s, c.W * 0.5f, y);
                h.opacity(scaled(c.spec, 0.35f));
                h.animatePosition(c.spec.startFrame, c.dur, chrononmotion::Vector3(0.f, kRowSpacing, 0.f));
            }
        }

        void gateWeave(Ctx& c) {
            strokeFrame(c, "gate_frame", c.W - 16.f, c.H - 16.f, colorOr(c.spec, "#000000"),
                        3.f, 0.65f, 0.f, 0.f, chrononmotion::Vector3(8.f, 6.f, 0.f));
        }

        void floatingDust(Ctx& c) {
            constexpr std::uint32_t kParticles = 24;
            for (std::uint32_t i = 0; i < kParticles; ++i) {
                const float d = 3.f + 9.f * unit(c.spec.seed, i, 4);
                ShapeSpec s = makeShape("dust_" + std::to_string(i), d, d, colorOr(c.spec, "#E8C86B"));
                s.geometry = ShapeGeometry::Ellipse;
                LayerHandle& h = spawn(c, s, c.W * unit(c.spec.seed, i, 5),
                                       c.H * unit(c.spec.seed, i, 6));
                pulse(h, c.spec.startFrame, c.dur,
                      scaled(c.spec, 0.45f + 0.45f * unit(c.spec.seed, i, 7)));
                h.animatePosition(c.spec.startFrame, c.dur,
                                  chrononmotion::Vector3(240.f * (unit(c.spec.seed, i, 8) - 0.5f),
                                                         180.f * (unit(c.spec.seed, i, 9) - 0.5f), 0.f));
            }
        }

        void atmosphericHaze(Ctx& c) {
            ShapeSpec s = makeShape("haze", c.W, c.H, colorOr(c.spec, "#B9CBD8"));
            LayerHandle& h = spawn(c, s, c.W * 0.5f, c.H * 0.5f);
            // Slow swell: breathe in, hold, breathe out.
            const int fade = c.dur / 2;
            h.animateOpacity(c.spec.startFrame, fade, scaled(c.spec, 0.1f), scaled(c.spec, 0.3f));
            h.animateOpacity(c.spec.startFrame + fade, c.dur - fade, scaled(c.spec, 0.3f),
                             scaled(c.spec, 0.1f));
        }

        void defocusedBokeh(Ctx& c) {
            constexpr std::uint32_t kSpots = 8;
            for (std::uint32_t i = 0; i < kSpots; ++i) {
                const float r = 40.f + 80.f * unit(c.spec.seed, i, 10);
                const float margin = r + 8.f;
                const float cx = margin + (c.W - 2.f * margin) * unit(c.spec.seed, i, 11);
                const float cy = margin + (c.H - 2.f * margin) * unit(c.spec.seed, i, 12);
                const std::string color = colorOr(c.spec, "#E8A93D");
                const chrononmotion::Vector3 drift(300.f * (unit(c.spec.seed, i, 22) - 0.5f),
                                                  220.f * (unit(c.spec.seed, i, 23) - 0.5f), 0.f);
                for (int ring = 0; ring < 2; ++ring) {
                    const float rr = ring == 0 ? r : r * 0.55f;
                    ShapeSpec s = makeShape("bokeh_" + std::to_string(i) + "_r" + std::to_string(ring),
                                            2.f * rr, 2.f * rr, color);
                    s.geometry = ShapeGeometry::Ellipse;
                    LayerHandle& h = spawn(c, s, cx, cy);
                    pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, ring == 0 ? 0.3f : 0.55f));
                    h.animatePosition(c.spec.startFrame, c.dur, drift);
                }
            }
        }

        void lightRays(Ctx& c) {
            constexpr std::uint32_t kRays = 5;
            for (std::uint32_t i = 0; i < kRays; ++i) {
                const float w = 60.f + 120.f * unit(c.spec.seed, i, 13);
                ShapeSpec s = makeShape("light_ray_" + std::to_string(i), w, c.H * 1.4f,
                                        colorOr(c.spec, "#F5C95C"));
                LayerHandle& h = spawn(c, s, c.W * unit(c.spec.seed, i, 14), c.H * 0.5f);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.22f));
                h.animatePosition(c.spec.startFrame, c.dur,
                                  chrononmotion::Vector3(480.f * (unit(c.spec.seed, i, 15) - 0.5f),
                                                         0.f, 0.f));
            }
        }

        void movingLightShadow(Ctx& c) {
            // A soft dark mass sweeping right to left across the frame.
            cluster(c, "moving_shadow", 14, 150.f, 280.f, c.W * 0.55f, c.W * 0.98f,
                    c.H * 0.05f, c.H * 0.95f, colorOr(c.spec, "#2A2A2A"), 0.35f, 0.6f,
                    chrononmotion::Vector3(-c.W * 0.55f, 0.f, 0.f), 40);
        }

        void lensFlare(Ctx& c) {
            // Bright core, two stroke rings and ghosts along the source-to-centre
            // line; the whole rig sweeps across the frame.
            const float cx = c.W * 0.72f;
            const float cy = c.H * 0.28f;
            const std::string color = colorOr(c.spec, "#E8A93D");
            const chrononmotion::Vector3 sweep(-c.W * 0.3f, c.H * 0.18f, 0.f);
            {
                ShapeSpec core = makeShape("lens_flare_core", 90.f, 90.f, "#FFF3D0");
                core.geometry = ShapeGeometry::Ellipse;
                LayerHandle& h = spawn(c, core, cx, cy);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.95f));
                h.animatePosition(c.spec.startFrame, c.dur, sweep);
            }
            for (const float ring : {150.f, 260.f}) {
                ShapeSpec s = makeShape("lens_flare_ring", ring, ring, color);
                s.geometry = ShapeGeometry::Ellipse;
                s.fillEnabled = false;
                s.strokeColor = color;
                s.strokeWidth = 5.f;
                LayerHandle& h = spawn(c, s, cx, cy);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.6f));
                h.animatePosition(c.spec.startFrame, c.dur, sweep);
            }
            for (const float t : {0.6f, 1.2f, 1.5f}) {
                const float size = 40.f + 50.f * t;
                ShapeSpec ghost = makeShape("lens_flare_ghost", size, size, "#FFE9B0");
                ghost.geometry = ShapeGeometry::Ellipse;
                LayerHandle& h = spawn(c, ghost, cx + (c.W * 0.5f - cx) * t,
                                       cy + (c.H * 0.5f - cy) * t);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.7f));
                h.animatePosition(c.spec.startFrame, c.dur, sweep);
            }
        }

        void cinematicVignette(Ctx& c) {
            // Dark falloff from nested stroke frames (margins widen, opacity
            // falls); corners stack darkest. Breathes slightly so it lives.
            const float margins[][2] = {{0.f, 45.f}, {45.f, 100.f}, {100.f, 170.f},
                                        {170.f, 250.f}, {250.f, 340.f}};
            const float levels[] = {0.32f, 0.2f, 0.12f, 0.06f, 0.03f};
            for (int i = 0; i < 5; ++i) {
                const float m0 = margins[i][0];
                const float m1 = margins[i][1];
                ShapeSpec s = makeShape("vignette_band" + std::to_string(i), c.W - (m0 + m1),
                                        c.H - (m0 + m1), colorOr(c.spec, "#000000"));
                s.fillEnabled = false;
                s.strokeColor = s.fillColor;
                s.strokeWidth = m1 - m0;
                LayerHandle& h = spawn(c, s, c.W * 0.5f, c.H * 0.5f);
                const int fade = c.dur / 2;
                h.animateOpacity(c.spec.startFrame, fade, scaled(c.spec, levels[i] * 0.85f),
                                 scaled(c.spec, levels[i]));
                h.animateOpacity(c.spec.startFrame + fade, c.dur - fade, scaled(c.spec, levels[i]),
                                 scaled(c.spec, levels[i] * 0.85f));
            }
        }

        void chromaticAberration(Ctx& c) {
            // A red and a cyan fringe frame, shifted apart and jittering.
            const float d = 5.f;
            const std::string redColor = colorOr(c.spec, "#FF2A00");
            const std::string cyanColor = "#00C8FF";
            const std::pair<std::string, float> fringes[] = {{redColor, -d}, {cyanColor, d}};
            for (const auto& [color, shift] : fringes) {
                ShapeSpec s = makeShape("chromatic_fringe", c.W - 16.f, c.H - 16.f, color);
                s.fillEnabled = false;
                s.strokeColor = color;
                s.strokeWidth = 8.f;
                LayerHandle& h = spawn(c, s, c.W * 0.5f + shift, c.H * 0.5f);
                h.opacity(scaled(c.spec, 0.5f));
                h.animatePosition(c.spec.startFrame, c.dur,
                                  chrononmotion::Vector3(shift > 0.f ? 12.f : -12.f, 0.f, 0.f));
            }
        }

        void paperGrain(Ctx& c) {
            ShapeSpec s = makeShape("paper_grain", c.W, c.H, colorOr(c.spec, "#E9DFC8"));
            s.noiseAmount = 0.3f * c.spec.intensity;
            s.noiseSeed = c.spec.seed;
            s.animatedNoise = false;
            s.noiseSize = 1.2f;
            solid(c, s, c.W * 0.5f, c.H * 0.5f, 0.5f);
        }

        void filmHalation(Ctx& c) {
            // Warm rim glow from nested orange stroke frames + a soft pulse.
            const float margins[][2] = {{0.f, 60.f}, {60.f, 140.f}, {140.f, 240.f}};
            const float levels[] = {0.45f, 0.28f, 0.14f};
            for (int i = 0; i < 3; ++i) {
                const float m0 = margins[i][0];
                const float m1 = margins[i][1];
                ShapeSpec s = makeShape("halation_band" + std::to_string(i), c.W - (m0 + m1),
                                        c.H - (m0 + m1), colorOr(c.spec, "#FF6A3D"));
                s.fillEnabled = false;
                s.strokeColor = s.fillColor;
                s.strokeWidth = m1 - m0;
                LayerHandle& h = spawn(c, s, c.W * 0.5f, c.H * 0.5f);
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, levels[i]));
            }
        }

        void opticalDiffusion(Ctx& c) {
            // Warm shimmer: white bloom is invisible on a white card, so the
            // diffusion carries a faint warm tint that reads as glow.
            cluster(c, "diffusion", 12, 150.f, 260.f, c.W * 0.1f, c.W * 0.9f,
                    c.H * 0.1f, c.H * 0.9f, colorOr(c.spec, "#FFE9C4"), 0.3f, 0.55f,
                    chrononmotion::Vector3(c.W * 0.04f, 0.f, 0.f), 50);
        }

        void filmEdgeMatte(Ctx& c) {
            const float border = std::max(1.f, 60.f * c.spec.intensity);
            ShapeSpec s = makeShape("edge_matte", c.W - border, c.H - border, colorOr(c.spec, "#000000"));
            s.fillEnabled = false;
            s.strokeColor = s.fillColor;
            s.strokeWidth = border;
            solid(c, s, c.W * 0.5f, c.H * 0.5f, 0.9f);
        }

        void directionalMotionSmear(Ctx& c) {
            // Gray streaks: white smears vanish on a white card.
            constexpr std::uint32_t kStreaks = 6;
            for (std::uint32_t i = 0; i < kStreaks; ++i) {
                ShapeSpec s = makeShape("motion_smear_" + std::to_string(i), c.W * 0.4f, 4.f,
                                        colorOr(c.spec, "#C2C2C2"));
                LayerHandle& h = spawn(c, s, c.W * unit(c.spec.seed, i, 16),
                                       c.H * unit(c.spec.seed, i, 17));
                pulse(h, c.spec.startFrame, c.dur, scaled(c.spec, 0.55f));
                h.animatePosition(c.spec.startFrame, c.dur, chrononmotion::Vector3(-c.W * 0.4f, 0.f, 0.f));
            }
        }

        void exposureFlicker(Ctx& c) {
            // Stepped flicker: six staggered full-frame layers alternate bright
            // and dark so the exposure visibly pumps instead of slowly fading.
            struct Step {
                const char* color;
                float opacity;
            };
            const Step steps[] = {
                {"#FFFFFF", 0.12f}, {"#000000", 0.1f}, {"#FFFFFF", 0.07f},
                {"#000000", 0.13f}, {"#FFFFFF", 0.1f}, {"#000000", 0.06f},
            };
            const int count = 6;
            for (int i = 0; i < count; ++i) {
                const int s0 = c.spec.startFrame + (c.dur * i) / count;
                const int s1 = c.spec.startFrame + (c.dur * (i + 1)) / count;
                if (s1 <= s0)
                    continue;
                ShapeSpec s = makeShape(std::string("exposure_step") + std::to_string(i), c.W, c.H,
                                        steps[i].color);
                LayerHandle& h = c.scene.shape(s);
                h.position(c.W * 0.5f, c.H * 0.5f);
                h.alive(s0, s1);
                h.opacity(scaled(c.spec, steps[i].opacity));
                c.out.push_back(h.id());
            }
        }

        void validate(const EffectSpec& spec) {
            if (!std::isfinite(spec.intensity) || spec.intensity < 0.f || spec.intensity > 1.f)
                throw std::invalid_argument("effects: intensity must be in [0, 1]");
            if (!std::isfinite(spec.opacity) || spec.opacity < 0.f || spec.opacity > 1.f)
                throw std::invalid_argument("effects: opacity must be in [0, 1]");
            if (spec.startFrame < 0 || spec.endFrame <= spec.startFrame)
                throw std::invalid_argument("effects: frame window must satisfy 0 <= start < end");
            if (!spec.color.empty() && !chronon3d::render_plan::parse_hex_color(spec.color))
                throw std::invalid_argument("effects: color must be #RRGGBB");
        }

    } // namespace

    std::vector<MotionLayerId> addEffect(TemplateScene& scene, EffectKind kind, const EffectSpec& spec) {
        validate(spec);
        std::vector<MotionLayerId> out;
        Ctx c{scene, spec, scene.canvas().x, scene.canvas().y,
              std::max(1, spec.endFrame - spec.startFrame), out};
        switch (kind) {
        case EffectKind::LightLeak: lightLeak(c); break;
        case EffectKind::FilmGrain: filmGrain(c); break;
        case EffectKind::FilmScratches: filmScratches(c); break;
        case EffectKind::FilmBurn: filmBurn(c); break;
        case EffectKind::ScanlineInterference: scanlineInterference(c); break;
        case EffectKind::GateWeave: gateWeave(c); break;
        case EffectKind::FloatingDust: floatingDust(c); break;
        case EffectKind::AtmosphericHaze: atmosphericHaze(c); break;
        case EffectKind::DefocusedBokeh: defocusedBokeh(c); break;
        case EffectKind::LightRays: lightRays(c); break;
        case EffectKind::MovingLightShadow: movingLightShadow(c); break;
        case EffectKind::LensFlare: lensFlare(c); break;
        case EffectKind::CinematicVignette: cinematicVignette(c); break;
        case EffectKind::ChromaticAberration: chromaticAberration(c); break;
        case EffectKind::PaperGrain: paperGrain(c); break;
        case EffectKind::FilmHalation: filmHalation(c); break;
        case EffectKind::OpticalDiffusion: opticalDiffusion(c); break;
        case EffectKind::FilmEdgeMatte: filmEdgeMatte(c); break;
        case EffectKind::DirectionalMotionSmear: directionalMotionSmear(c); break;
        case EffectKind::ExposureFlicker: exposureFlicker(c); break;
        }
        return out;
    }

    const char* effectName(EffectKind kind) noexcept {
        switch (kind) {
        case EffectKind::LightLeak: return "light_leak";
        case EffectKind::FilmGrain: return "film_grain";
        case EffectKind::FilmScratches: return "film_scratches";
        case EffectKind::FilmBurn: return "film_burn";
        case EffectKind::ScanlineInterference: return "scanline_interference";
        case EffectKind::GateWeave: return "gate_weave";
        case EffectKind::FloatingDust: return "floating_dust";
        case EffectKind::AtmosphericHaze: return "atmospheric_haze";
        case EffectKind::DefocusedBokeh: return "defocused_bokeh";
        case EffectKind::LightRays: return "light_rays";
        case EffectKind::MovingLightShadow: return "moving_light_shadow";
        case EffectKind::LensFlare: return "lens_flare";
        case EffectKind::CinematicVignette: return "cinematic_vignette";
        case EffectKind::ChromaticAberration: return "chromatic_aberration";
        case EffectKind::PaperGrain: return "paper_grain";
        case EffectKind::FilmHalation: return "film_halation";
        case EffectKind::OpticalDiffusion: return "optical_diffusion";
        case EffectKind::FilmEdgeMatte: return "film_edge_matte";
        case EffectKind::DirectionalMotionSmear: return "directional_motion_smear";
        case EffectKind::ExposureFlicker: return "exposure_flicker";
        }
        return "unknown";
    }

    const char* effectsId() noexcept {
        return "effects_overlay_v1";
    }

} // namespace chronontemplate::effects
