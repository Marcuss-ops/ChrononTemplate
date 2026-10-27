// test_native_svg_parser.cpp
// Validates Native C++ SVG Path parsing and direct topological morphing

#include <chronontemplate/vector_diagram/SvgPathParser.hpp>
#include <chronontemplate/vector_diagram/TopologicalPathMorpher.hpp>
#include <iostream>
#include <cassert>

using namespace chronontemplate::vector_diagram;

int main() {
    std::cout << "=== Running Unit Tests: Native C++ SVG Parser ===\n";

    // TEST 1: Parse standard path string with curves and relative coordinates
    {
        std::cout << "[Test 1] Parsing SVG path string with Cubic Beziers & relative coords...\n";
        std::string d = "M 10 20 L 50 20 C 60 20, 70 30, 70 40 c 0 10, -10 20, -20 20 l -40 0 Z";
        BLPath blPath;
        std::vector<Point2D> pts;
        bool ok = SvgPathParser::parsePathString(d, blPath, pts);
        assert(ok);
        assert(pts.size() > 10);
        std::cout << "  -> PASSED: Successfully extracted " << pts.size() << " polyline samples from SVG path.\n";
    }

    // TEST 2: Direct loading of real SVG icon files from disk
    {
        std::cout << "[Test 2] Loading real SVG files from disk (rocket.svg & brain.svg)...\n";
        ArcLengthPath pathRocket, pathBrain;
        BLPath blRocket, blBrain;

        bool okRocket = SvgPathParser::loadSvgFile("C:/Users/pater/Pyt/ChrononTemplate/assets/icons/svg/rocket.svg", pathRocket, blRocket);
        bool okBrain = SvgPathParser::loadSvgFile("C:/Users/pater/Pyt/ChrononTemplate/assets/icons/svg/brain.svg", pathBrain, blBrain);

        assert(okRocket);
        assert(okBrain);
        assert(pathRocket.total_length > 10.0);
        assert(pathBrain.total_length > 10.0);
        std::cout << "  -> PASSED: Loaded rocket.svg (L=" << pathRocket.total_length 
                  << ") and brain.svg (L=" << pathBrain.total_length << ") in pure C++.\n";

        // TEST 3: Direct Native Topological Morphing between the two SVGs
        std::cout << "[Test 3] Pure C++ Topological Morphing between rocket.svg and brain.svg...\n";
        TopologicalPathMorpher morpher;
        morpher.initialize(pathRocket, pathBrain, 256);

        assert(morpher.get_pts_a().size() == 256);
        assert(morpher.get_pts_b_aligned().size() == 256);

        auto morphed_50 = morpher.evaluate_morph(0.5);
        assert(morphed_50.size() == 256);
        for (const auto& p : morphed_50) {
            assert(!std::isnan(p.x) && !std::isnan(p.y));
        }

        std::cout << "  -> PASSED: Morph initialized with N=256, shift=" << morpher.get_metrics().optimal_shift
                  << ", energy=" << morpher.get_metrics().min_energy << ".\n";
    }

    std::cout << "\nALL NATIVE C++ SVG PARSER & MORPHER TESTS PASSED SUCCESSFULLY!\n";
    return 0;
}
