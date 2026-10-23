#pragma once

#include <blend2d.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;

namespace chronon::youtuber {

// Scene geometry is authored in a 3840x2160 logical space and rasterized at
// 1920x1080 for the requested delivery size.
constexpr int kW = 3840;
constexpr int kH = 2160;
constexpr int k4KW = kW;
constexpr int k4KH = kH;

inline const std::string kFinalBase1 = "C:/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Youtuberstle/Final";
inline const std::string kFinalBase2 = "C:/Users/pater/OneDrive/Documenti/Chronomotion/ChrononMotion3D/Final";
inline const std::string kAssetsDir  = "C:/Users/pater/dev/projects/ChrononTemplate/tools/youtuber_style/assets";
inline const std::string kFontsDir   = "C:/Users/pater/Pyt/Chronon3d/assets/fonts";

struct FontBundle {
    BLFont fontTitle;
    BLFont fontHeadline;
    BLFont fontSubhead;
    BLFont fontBody;
    BLFont fontMono;
    BLFont fontSerif;
    BLFont fontSerifRegular;
    bool valid{false};
};

inline FontBundle loadFonts() {
    FontBundle fb;
    BLFontFace faceBold, faceReg, faceSerif;
    if (faceBold.createFromFile((kFontsDir + "/Inter-Bold.ttf").c_str()) == BL_SUCCESS &&
        faceReg.createFromFile((kFontsDir + "/Inter-Regular.ttf").c_str()) == BL_SUCCESS &&
        faceSerif.createFromFile((kFontsDir + "/Georgia_Bold.ttf").c_str()) == BL_SUCCESS) {
        fb.fontTitle.createFromFace(faceBold, 216.0f);
        fb.fontHeadline.createFromFace(faceBold, 160.0f);
        fb.fontSubhead.createFromFace(faceBold, 96.0f);
        fb.fontBody.createFromFace(faceReg, 72.0f);
        fb.fontMono.createFromFace(faceReg, 64.0f);
        fb.fontSerif.createFromFace(faceSerif, 168.0f);
        BLFontFace faceFreeSerif;
        if (faceFreeSerif.createFromFile((kFontsDir + "/FreeSerif.ttf").c_str()) == BL_SUCCESS)
            fb.fontSerifRegular.createFromFace(faceFreeSerif, 168.0f);
        fb.valid = true;
    }
    return fb;
}

inline void drawText(BLContext& ctx, const BLPoint& pt, const BLFont& font, const std::string& text) {
    ctx.fillUtf8Text(pt, font, text.c_str(), text.size());
}

inline double lerp(double a, double b, double t) {
    return a + (b - a) * t;
}

inline double easeInOutCubic(double t) {
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - std::pow(-2.0 * t + 2.0, 3.0) / 2.0;
}

inline double easeOutCubic(double t) {
    return 1.0 - std::pow(1.0 - t, 3.0);
}

inline void exportAndMirrorVideo(const std::string& animName, const std::string& framesPattern, int fps, int startFrame, int numFrames) {
    std::string out1 = kFinalBase1 + "/" + animName + "/" + animName + ".mp4";
    std::string out2 = kFinalBase2 + "/" + animName + "/" + animName + ".mp4";
    
    fs::create_directories(kFinalBase1 + "/" + animName);
    fs::create_directories(kFinalBase2 + "/" + animName);

    std::string cmd = "ffmpeg -y -framerate " + std::to_string(fps) +
                      " -start_number " + std::to_string(startFrame) +
                      " -i \"" + framesPattern + "\"" +
                      " -c:v libx264 -pix_fmt yuv420p -crf 18 \"" + out1 + "\" > nul 2>&1";
    std::system(cmd.c_str());

    if (fs::exists(out1)) {
        fs::copy_file(out1, out2, fs::copy_options::overwrite_existing);
    }
}

inline void mirrorFrames(const std::string& animName, int startFrame, int endFrame) {
    std::string dir1 = kFinalBase1 + "/" + animName;
    std::string dir2 = kFinalBase2 + "/" + animName;
    fs::create_directories(dir2);

    for (int i = startFrame; i <= endFrame; ++i) {
        std::ostringstream ss;
        ss << "frame_" << std::setw(4) << std::setfill('0') << i << ".png";
        std::string fname = ss.str();
        fs::path f1 = fs::path(dir1) / fname;
        fs::path f2 = fs::path(dir2) / fname;
        if (fs::exists(f1)) {
            fs::copy_file(f1, f2, fs::copy_options::overwrite_existing);
        }
    }
}

} // namespace chronon::youtuber
