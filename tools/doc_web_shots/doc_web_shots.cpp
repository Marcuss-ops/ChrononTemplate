// doc_web_shots.cpp — native C++ runner for the 20 documentary web shots.
//
// Usage:
//   doc_web_shots --out DIR [--stills] [--keep-frames] [--only NAME...]
//
// Every frame is drawn by Blend2D. ffmpeg is only the H.264 encoder.

#include "doc_pack.hpp"

#include <nlohmann/json.hpp>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace chronon::docshots {
namespace {

std::vector<Scene> allScenes() {
    auto a = scenesA();
    auto b = scenesB();
    auto c = scenesC();
    a.insert(a.end(), b.begin(), b.end());
    a.insert(a.end(), c.begin(), c.end());
    return a;
}

bool wanted(const Scene& scene, const std::vector<std::string>& only) {
    if (only.empty()) return true;
    for (const auto& name : only) if (name == scene.name) return true;
    return false;
}

int renderScene(const Scene& scene, const fs::path& root, bool stillsOnly,
                bool keepFrames) {
    const fs::path dir = root / scene.name;
    const fs::path frames = dir / "frames";
    fs::create_directories(frames);

    if (!stillsOnly)
    for (int i = 0; i < kFrames; ++i) {
        const double t = double(i) / double(kFrames - 1);
        BLImage image(kW, kH, BL_FORMAT_PRGB32);
        BLContext context(image);
        context.clearAll();
        scene.draw(context, t, i);
        context.end();
        const fs::path path =
            frames / ("frame_" + padded(i) + ".png");
        if (image.writeToFile(path.string().c_str()) != BL_SUCCESS) {
            std::cerr << "write failed: " << path << '\n';
            return 3;
        }
    }

    {
        BLImage image(kW, kH, BL_FORMAT_PRGB32);
        BLContext context(image);
        context.clearAll();
        scene.draw(context, scene.stillT, int(scene.stillT * (kFrames - 1)));
        context.end();
        if (image.writeToFile((dir / "still.png").string().c_str()) != BL_SUCCESS)
            return 4;
    }

    if (stillsOnly) {
        fs::remove_all(frames);
        std::cout << "[stills] " << scene.name << '\n';
        return 0;
    }

    const fs::path mp4 = dir / (scene.name + ".mp4");
    std::ostringstream command;
    command << "ffmpeg -y -v error -framerate " << kFps
            << " -start_number 0 -i \"" << frames.string()
            << "/frame_%04d.png\" -c:v libx264 -preset medium -crf 18"
            << " -pix_fmt yuv420p -movflags +faststart \"" << mp4.string() << "\"";
    if (std::system(command.str().c_str()) != 0) {
        std::cerr << "ffmpeg failed for " << scene.name << '\n';
        return 5;
    }
    if (!keepFrames) fs::remove_all(frames);
    std::cout << "[render] " << scene.name << '\n';
    return 0;
}

void writeManifest(const std::vector<Scene>& scenes, const fs::path& root) {
    using nlohmann::json;
    json manifest;
    manifest["schema"] = "chronon.doc-web-shots.v1";
    manifest["pack"] = "doc_web_shots_2026";
    manifest["count"] = scenes.size();
    manifest["deliver"] = {{"width", kW}, {"height", kH}, {"fps", kFps},
                           {"frames", kFrames}, {"seconds", 3.0}};
    manifest["source_policy"] =
        "native C++ Blend2D vector composition; no browser, screenshot or Python";
    json rows = json::array();
    for (int i = 0; i < int(scenes.size()); ++i) {
        const auto& scene = scenes[i];
        json row;
        row["id"] = i + 1;
        row["shot"] = scene.name;
        row["category"] = scene.category;
        row["description"] = scene.description;
        row["still"] = scene.name + "/still.png";
        row["clip"] = scene.name + "/" + scene.name + ".mp4";
        row["still_t"] = scene.stillT;
        rows.push_back(row);
    }
    manifest["shots"] = rows;
    std::ofstream out(root / "manifest.json");
    out << manifest.dump(2) << '\n';

    std::ofstream readme(root / "README.md");
    readme << "# Documentary Web Shots — 20 native C++ compositions\n\n"
           << "1920x1080, 30 fps, 90 frames, H.264. Every frame is rendered by "
              "Blend2D from C++ geometry and native text; ffmpeg only encodes.\n\n"
           << "## Shots\n\n";
    for (int i = 0; i < int(scenes.size()); ++i) {
        const auto& scene = scenes[i];
        readme << "- `" << scene.name << "` — " << scene.description
               << " (" << scene.category << ")\n";
    }
    readme << "\nSource: `tools/doc_web_shots/`.\n";
}

} // namespace
} // namespace chronon::docshots

int main(int argc, char** argv) {
    using namespace chronon::docshots;
    if (!fonts().valid) {
        std::cerr << "fonts missing under " << fontsDir() << '\n';
        return 2;
    }

    fs::path out = rootDir() / "artifacts" / "doc_web_shots_2026";
    bool stillsOnly = false;
    bool keepFrames = false;
    std::vector<std::string> only;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--out" && i + 1 < argc) out = fs::absolute(argv[++i]);
        else if (arg == "--stills") stillsOnly = true;
        else if (arg == "--keep-frames") keepFrames = true;
        else if (arg == "--only") {
            while (i + 1 < argc && std::string(argv[i + 1]).rfind("--", 0) != 0)
                only.push_back(argv[++i]);
        } else if (arg.rfind("--", 0) == 0) {
            std::cerr << "unknown option " << arg << '\n';
            return 3;
        } else {
            only.push_back(arg);
        }
    }
    fs::create_directories(out);

    auto scenes = allScenes();
    int rendered = 0;
    for (const auto& scene : scenes) {
        if (!wanted(scene, only)) continue;
        const int rc = renderScene(scene, out, stillsOnly, keepFrames);
        if (rc != 0) return rc;
        ++rendered;
    }
    writeManifest(scenes, out);
    std::cout << "[done] " << rendered << " scene(s) -> " << out << '\n';
    return 0;
}
