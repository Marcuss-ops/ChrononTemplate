// One-off probe: how does BLRadialGradientValues map stops to radii?
#include <blend2d.h>
#include <cstdio>

static void probe(const char* name, double r0, double r1, bool stop0IsBright) {
    BLImage img(200, 200, BL_FORMAT_PRGB32);
    BLContext ctx(img);
    ctx.clearAll();
    BLGradient g(BLRadialGradientValues(100.0, 100.0, 100.0, 100.0, r0, r1));
    if (stop0IsBright) {
        g.addStop(0.0, BLRgba32(255, 255, 255, 255));
        g.addStop(1.0, BLRgba32(255, 255, 255, 0));
    } else {
        g.addStop(0.0, BLRgba32(255, 255, 255, 0));
        g.addStop(1.0, BLRgba32(255, 255, 255, 255));
    }
    ctx.setFillStyle(g);
    ctx.fillRect(BLRect(0, 0, 200, 200));
    ctx.end();

    BLImageData data;
    img.getData(&data);
    auto* p = static_cast<const uint8_t*>(data.pixelData);
    auto alphaAt = [&](int x, int y) {
        const uint8_t* px = p + y * data.stride + x * 4;
        // PRGB32 little-endian: B,G,R,A
        return int(px[3]);
    };
    std::printf("%-28s r0=%.0f r1=%.0f  stop0bright=%d : center=%d edge=%d corner=%d\n",
                name, r0, r1, int(stop0IsBright),
                alphaAt(100, 100), alphaAt(195, 100), alphaAt(3, 3));
}

int main() {
    probe("A outer,inner b0bright", 95.0, 5.0, true);
    probe("A outer,inner b1bright", 95.0, 5.0, false);
    probe("B inner,outer b0bright", 5.0, 95.0, true);
    probe("B inner,outer b1bright", 5.0, 95.0, false);
    return 0;
}