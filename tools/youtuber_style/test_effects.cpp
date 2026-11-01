#include "native_rebuild.hpp"
#include <iostream>

int main() {
    std::cout << "[TEST] Testing newly added Chronon effects in C++..." << std::endl;
    BLImage img(1920, 1080, BL_FORMAT_PRGB32);
    BLContext ctx(img);

    // 1. Dark backdrop
    chronon::youtuber::dark(ctx);

    // 2. Volumetric light cone
    chronon::youtuber::volumetricLightCone(ctx, 960, 80, 820, 1000, BLRgba32(75, 80, 95, 200));

    // 3. Shaded celestial spheres
    chronon::youtuber::shadedSphere(ctx, 940, 600, 24.0, BLRgba32(245, 245, 250, 255));
    chronon::youtuber::shadedSphere(ctx, 890, 530, 18.0, BLRgba32(240, 205, 15, 255));
    chronon::youtuber::shadedSphere(ctx, 950, 530, 14.0, BLRgba32(240, 205, 15, 255));
    chronon::youtuber::shadedSphere(ctx, 1000, 530, 11.0, BLRgba32(240, 205, 15, 255));

    // 4. Inked brushed reticle brackets [ ]
    chronon::youtuber::brushedReticle(ctx, 950, 560, 85.0, 28.0, 0.0, BLRgba32(250, 252, 255, 255), 6.0, 10);

    // 5. Inked brushed bounding box with authentic line-boil
    chronon::youtuber::brushedBox(ctx, 865, 475, 170.0, 170.0, BLRgba32(255, 255, 255, 255), 6.0, 12);

    // 6. Target lock-on
    chronon::youtuber::targetLockon(ctx, 1000, 530, 20.0, BLRgba32(245, 40, 40, 255), 10);

    ctx.end();

    // 7. Dynamic continuous film grain and archival dust
    chronon::youtuber::applyContinuousFilmGrain(img, 10, 14.0f, 25);

    img.writeToFile("C:/Users/pater/Pyt/assets/chronon_visual_venture_pack/test_cpp_effects.png");
    std::cout << "[SUCCESS] C++ Chronon Effects executed and saved to test_cpp_effects.png!" << std::endl;
    return 0;
}
