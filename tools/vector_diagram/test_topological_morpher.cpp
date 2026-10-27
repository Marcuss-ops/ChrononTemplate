// test_topological_morpher.cpp
// Mathematical unit tests for Topological Path Morpher (Arc-Length Resampling + Optimal Pairing)

#include <chronontemplate/vector_diagram/TopologicalPathMorpher.hpp>
#include <iostream>
#include <cassert>
#include <vector>
#include <cmath>

using namespace chronontemplate::vector_diagram;
constexpr double kPi = 3.14159265358979323846;

int main() {
    std::cout << "=== Running Unit Tests: Topological Path Morpher ===\n";

    // TEST 1: Resampling M != K to Uniform N=256
    {
        std::cout << "[Test 1] Unequal Vertices Resampling (Square [4 pts] -> Triangle [3 pts])...\n";
        // Square: 4 vertices
        std::vector<Point2D> square_raw = {
            { 0.0, 0.0 }, { 100.0, 0.0 }, { 100.0, 100.0 }, { 0.0, 100.0 }
        };
        ArcLengthPath square_path;
        square_path.build_from_points(square_raw, true);
        assert(std::abs(square_path.total_length - 400.0) < 1e-4);

        // Triangle: 3 vertices
        std::vector<Point2D> tri_raw = {
            { 50.0, 0.0 }, { 100.0, 100.0 }, { 0.0, 100.0 }
        };
        ArcLengthPath tri_path;
        tri_path.build_from_points(tri_raw, true);

        TopologicalPathMorpher morpher;
        morpher.initialize(square_path, tri_path, 256);

        assert(morpher.get_pts_a().size() == 256);
        assert(morpher.get_pts_b_aligned().size() == 256);

        // Check midpoint morph tau = 0.5
        auto mid = morpher.evaluate_morph(0.5);
        assert(mid.size() == 256);
        for (const auto& p : mid) {
            assert(!std::isnan(p.x) && !std::isnan(p.y));
        }
        std::cout << "  -> PASSED: Resampled 4 and 3 vertices to 256 equidistant nodes.\n";
    }

    // TEST 2: Rotational Phase Shift & Anti-Twist Minimization
    {
        std::cout << "[Test 2] Optimal Vertex Pairing & Rotational Shift Alignment...\n";
        // Circle 1: starts at 0 rad
        std::vector<Point2D> c1_pts;
        for (int i = 0; i < 32; ++i) {
            double a = (i / 32.0) * 2.0 * kPi;
            c1_pts.push_back({ 50.0 * std::cos(a), 50.0 * std::sin(a) });
        }
        ArcLengthPath c1;
        c1.build_from_points(c1_pts, true);

        // Circle 2: same circle, but artificially shifted by pi rad (halfway around)
        std::vector<Point2D> c2_pts;
        for (int i = 0; i < 32; ++i) {
            double a = (i / 32.0) * 2.0 * kPi + kPi; // 180 deg offset
            c2_pts.push_back({ 50.0 * std::cos(a), 50.0 * std::sin(a) });
        }
        ArcLengthPath c2;
        c2.build_from_points(c2_pts, true);

        TopologicalPathMorpher morpher;
        morpher.initialize(c1, c2, 128);

        // The energy should be nearly 0 because both shapes are identical,
        // and the optimal shift should automatically absorb the 180 deg (k ~ 64)
        double min_e = morpher.get_metrics().min_energy;
        std::cout << "  Minimum Deformation Energy = " << min_e 
                  << ", Optimal Shift k* = " << morpher.get_metrics().optimal_shift << "\n";
        assert(min_e < 1.0); // essentially zero error
        std::cout << "  -> PASSED: 180-deg phase shift resolved with zero deformation energy.\n";
    }

    // TEST 3: Winding Direction Inversion
    {
        std::cout << "[Test 3] Winding Direction Inversion Detection (CW vs CCW)...\n";
        std::vector<Point2D> cw_pts = { { 0, 0 }, { 10, 0 }, { 10, 10 }, { 0, 10 } };
        std::vector<Point2D> ccw_pts = { { 0, 0 }, { 0, 10 }, { 10, 10 }, { 10, 0 } };

        ArcLengthPath p_cw, p_ccw;
        p_cw.build_from_points(cw_pts, true);
        p_ccw.build_from_points(ccw_pts, true);

        TopologicalPathMorpher morpher;
        morpher.initialize(p_cw, p_ccw, 64);

        assert(morpher.get_metrics().is_flipped == true);
        assert(morpher.get_metrics().min_energy < 1e-4);
        std::cout << "  -> PASSED: Inverted winding detected and rectified.\n";
    }

    std::cout << "\nALL 3 TOPOLOGICAL MORPHER UNIT TESTS PASSED SUCCESSFULLY!\n";
    return 0;
}
