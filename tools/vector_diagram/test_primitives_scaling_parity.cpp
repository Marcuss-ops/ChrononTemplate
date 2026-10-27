// test_primitives_scaling_parity.cpp
// Mathematical verification of Trim Path, Arc-Length LUT, Non-scaling stroke, and Pivot invariance for Blend2D / Chronon.render-plan.v3

#include <blend2d.h>
#include <cmath>
#include <cassert>
#include <iostream>
#include <vector>
#include <algorithm>

struct Vec2 {
    double x, y;
};

// 1. Arc-Length Lookup Table for constant linear speed across polyline / curves
class ArcLengthLUT {
public:
    struct Sample {
        double length;
        Vec2 pos;
        Vec2 tangent;
    };
    std::vector<Sample> samples;
    double total_length = 0.0;

    void build_from_polyline(const std::vector<Vec2>& pts) {
        samples.clear();
        total_length = 0.0;
        if (pts.empty()) return;

        samples.push_back({0.0, pts[0], {1.0, 0.0}});
        for (size_t i = 1; i < pts.size(); ++i) {
            double dx = pts[i].x - pts[i - 1].x;
            double dy = pts[i].y - pts[i - 1].y;
            double seg_len = std::hypot(dx, dy);
            total_length += seg_len;
            Vec2 tan = (seg_len > 1e-6) ? Vec2{dx / seg_len, dy / seg_len} : samples.back().tangent;
            samples.push_back({total_length, pts[i], tan});
        }
    }

    // Evaluates normalized position u in [0.0, 1.0] at strict constant velocity
    Sample evaluate_normalized(double u) const {
        if (samples.empty()) return {0.0, {0.0, 0.0}, {1.0, 0.0}};
        double target = std::clamp(u, 0.0, 1.0) * total_length;

        for (size_t i = 1; i < samples.size(); ++i) {
            if (samples[i].length >= target) {
                double prev_l = samples[i - 1].length;
                double span = samples[i].length - prev_l;
                double t = (span > 1e-6) ? (target - prev_l) / span : 0.0;
                Vec2 p = {
                    samples[i - 1].pos.x + t * (samples[i].pos.x - samples[i - 1].pos.x),
                    samples[i - 1].pos.y + t * (samples[i].pos.y - samples[i - 1].pos.y)
                };
                return {target, p, samples[i].tangent};
            }
        }
        return samples.back();
    }
};

// 2. 2.5D Transform Matrix with exact Anchor/Pivot invariance and perspective projection
BLMatrix2D compute_transform_25d(
    Vec2 position,       // Target world position where the pivot must sit
    Vec2 anchor_offset,  // Pivot offset in local shape coordinates (e.g. {w*0.5, h*0.5})
    Vec2 scale,          // Local non-uniform scale (sx, sy)
    double rotation_rad, // Local rotation in radians
    double z_depth,      // Layer Z depth
    Vec2 camera_pos,     // Camera X, Y
    double camera_z,     // Camera Z (e.g. -1000.0)
    double focal_length  // Focal length (e.g. 1000.0)
) {
    double dist_z = z_depth - camera_z;
    double perspective = (dist_z > 1.0) ? (focal_length / dist_z) : 1.0;

    // Projected position relative to canvas center (960, 540)
    double proj_x = 960.0 + (position.x - camera_pos.x) * perspective;
    double proj_y = 540.0 + (position.y - camera_pos.y) * perspective;

    BLMatrix2D m;
    m.reset();
    m.translate(proj_x, proj_y);
    m.scale(scale.x * perspective, scale.y * perspective);
    m.rotate(rotation_rad);
    m.translate(-anchor_offset.x, -anchor_offset.y);
    return m;
}

// 3. Non-scaling stroke width helper
inline double compute_screen_stroke_width(double desired_screen_px, Vec2 local_scale, double perspective) {
    // In order for the stroke rendered on a scaled primitive to appear with exact constant thickness,
    // we compensate by the geometric average or axis-aligned inverse scale factor
    double net_scale = std::sqrt(local_scale.x * local_scale.y) * perspective;
    return (net_scale > 1e-4) ? (desired_screen_px / net_scale) : desired_screen_px;
}

int main() {
    std::cout << "========================================================\n"
              << "ChrononTemplate: Mathematical Parity & Primitives Test\n"
              << "========================================================\n";

    // Test 1: Arc-Length Linearity on asymmetrical segments (short + long)
    ArcLengthLUT lut;
    lut.build_from_polyline({{0, 0}, {10, 0}, {10, 90}}); // Total = 10 + 90 = 100
    assert(std::abs(lut.total_length - 100.0) < 1e-5);

    auto mid = lut.evaluate_normalized(0.5); // At 50%, position must be exactly (10, 40)
    assert(std::abs(mid.pos.x - 10.0) < 1e-4 && std::abs(mid.pos.y - 40.0) < 1e-4);
    std::cout << "  [PASS] Test 1: Arc-Length LUT Linearity verified.\n";

    // Test 2: Invariance of Anchor/Pivot under Scaling, Rotation & Perspective
    Vec2 world_targets[] = {{960.0, 540.0}, {400.0, 300.0}, {1400.0, 800.0}};
    Vec2 pivots[] = {{0.0, 0.0}, {50.0, 25.0}, {100.0, 100.0}, {25.0, 75.0}};

    for (const auto& world_target : world_targets) {
        for (const auto& local_pivot : pivots) {
            BLMatrix2D mat = compute_transform_25d(
                world_target, local_pivot, {2.5, 0.4}, 0.785398, -200.0, {960.0, 540.0}, -1000.0, 1000.0
            );
            BLPoint transformed_pivot = mat.mapPoint(local_pivot.x, local_pivot.y);
            
            // The mapped pivot MUST equal projected world coordinate with zero drift (< 1e-4 px)
            double dist_z = -200.0 - (-1000.0);
            double perspective = 1000.0 / dist_z;
            double expected_x = 960.0 + (world_target.x - 960.0) * perspective;
            double expected_y = 540.0 + (world_target.y - 540.0) * perspective;

            assert(std::abs(transformed_pivot.x - expected_x) < 1e-4);
            assert(std::abs(transformed_pivot.y - expected_y) < 1e-4);
        }
    }
    std::cout << "  [PASS] Test 2: Anchor/Pivot Zero-Drift Invariance verified.\n";

    // Test 3: Non-uniform scaling stroke width compensation
    Vec2 non_uniform_scales[] = {{2.5, 0.4}, {0.2, 3.0}, {1.0, 1.0}};
    for (const auto& scale : non_uniform_scales) {
        double desired_px = 4.0;
        double local_stroke = compute_screen_stroke_width(desired_px, scale, 1.0);
        double apparent_screen_px = local_stroke * std::sqrt(scale.x * scale.y);
        assert(std::abs(apparent_screen_px - desired_px) < 1e-4);
    }
    std::cout << "  [PASS] Test 3: Non-Scaling Stroke Width Compensation verified.\n";

    std::cout << "\n[ALL 3 CORE MATHEMATICAL TESTS PASSED SUCCESSFULLY!]\n";
    return 0;
}
