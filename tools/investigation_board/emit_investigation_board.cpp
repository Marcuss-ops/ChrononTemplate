// Parametric investigation board: corkboard, pinned photo/document cards and
// red strings, authored as native Chronon render-plan layers.
//
// Input is a small JSON document (board + items + connections + camera); the
// emitted plan keeps every card, pin and string separately editable and the
// camera is resolved to per-frame camera_samples, so the composition renders
// headless and deterministically.
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kPhotoWidth = 360.0;
constexpr double kPhotoHeight = 482.0;
constexpr double kDocumentWidth = 380.0;
constexpr double kDocumentHeight = 500.0;
constexpr double kPinWidth = 58.0;
constexpr double kPinHeight = 50.75;
constexpr double kMinDurationSeconds = 8.0;
constexpr double kMaxDurationSeconds = 30.0;
constexpr int kMaxItems = 120;
constexpr int kMaxConnections = 240;

std::string defaultPinAsset() {
    return "ChrononTemplate/assets/nba_rivalry/web/red_pushpin.png";
}

std::string defaultStringAsset() {
    return "ChrononTemplate/assets/investigation_board/string_red.png";
}

[[noreturn]] void fail(const std::string& path, const std::string& message) {
    throw std::runtime_error(path.empty() ? message : path + ": " + message);
}

bool finite(double value) { return std::isfinite(value); }

double number(const Json& value, const std::string& path) {
    if (!value.is_number()) fail(path, "expected a number");
    const double result = value.get<double>();
    if (!finite(result)) fail(path, "expected a finite number");
    return result;
}

int integer(const Json& value, const std::string& path) {
    if (!value.is_number_integer()) fail(path, "expected an integer");
    return value.get<int>();
}

std::string text(const Json& value, const std::string& path) {
    if (!value.is_string()) fail(path, "expected a string");
    const std::string result = value.get<std::string>();
    if (result.empty()) fail(path, "expected a non-empty string");
    return result;
}

const Json& field(const Json& object, const char* key, const std::string& path) {
    if (!object.contains(key)) fail(path + "." + key, "missing required field");
    return object.at(key);
}

void checkKeys(const Json& object, const std::set<std::string>& allowed,
               const std::string& path) {
    for (auto it = object.begin(); it != object.end(); ++it) {
        if (!allowed.count(it.key()))
            fail(path + "." + it.key(), "unknown field");
    }
}

double clamp(double value, double low, double high) {
    return std::min(high, std::max(low, value));
}

// FNV-1a keeps the default tilt deterministic for a given item id.
std::uint32_t hashId(const std::string& id) {
    std::uint32_t hash = 2166136261u;
    for (const char c : id) {
        hash ^= static_cast<std::uint8_t>(c);
        hash *= 16777619u;
    }
    return hash;
}

double smoothstep(double t) {
    t = clamp(t, 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

struct Item {
    std::string id;
    std::string type;
    std::string asset;
    double x = 0.0;
    double y = 0.0;
    double width = 0.0;
    double height = 0.0;
    double rotation = 0.0;
    double depth = 0.0;
    bool pin = true;
};

struct Connection {
    std::size_t from = 0;
    std::size_t to = 0;
    double width = 5.0;
};

struct Input {
    double boardWidth = 3200.0;
    double boardHeight = 1800.0;
    std::string boardAsset;
    std::string pinAsset;
    std::string stringAsset;
    int canvasWidth = 1920;
    int canvasHeight = 1080;
    int fps = 30;
    double durationSeconds = 16.0;
    double fov = 40.0;
    std::string preset;
    std::vector<std::string> focusOrder;
    std::vector<Item> items;
    std::vector<Connection> connections;
    std::string outputPath = "investigation_board.mp4";
    std::string outputFormat = "mp4";
    std::string outputCodec = "h264";
};

Input parseInput(const Json& root) {
    if (!root.is_object()) fail("", "input must be a JSON object");
    checkKeys(root, {"template", "board", "items", "connections", "camera",
                     "canvas", "output"}, "");
    if (root.contains("template") &&
        text(root.at("template"), "template") != "investigation_board")
        fail("template", "expected \"investigation_board\"");

    Input input;
    const Json& board = field(root, "board", "");
    if (!board.is_object()) fail("board", "expected an object");
    checkKeys(board, {"width", "height", "asset", "pin_asset"}, "board");
    input.boardWidth = number(field(board, "width", "board"), "board.width");
    input.boardHeight = number(field(board, "height", "board"), "board.height");
    if (input.boardWidth < 640.0 || input.boardWidth > 20000.0 ||
        input.boardHeight < 360.0 || input.boardHeight > 20000.0)
        fail("board", "width/height must be within [640, 20000] x [360, 20000]");
    input.boardAsset = text(field(board, "asset", "board"), "board.asset");
    input.pinAsset = board.contains("pin_asset")
        ? text(board.at("pin_asset"), "board.pin_asset") : defaultPinAsset();
    input.stringAsset = defaultStringAsset();

    if (root.contains("canvas")) {
        const Json& canvas = root.at("canvas");
        if (!canvas.is_object()) fail("canvas", "expected an object");
        checkKeys(canvas, {"width", "height"}, "canvas");
        input.canvasWidth = integer(field(canvas, "width", "canvas"), "canvas.width");
        input.canvasHeight = integer(field(canvas, "height", "canvas"), "canvas.height");
        if (input.canvasWidth < 320 || input.canvasWidth > 8192 ||
            input.canvasHeight < 240 || input.canvasHeight > 8192)
            fail("canvas", "width/height out of supported range");
    }

    const Json& camera = field(root, "camera", "");
    if (!camera.is_object()) fail("camera", "expected an object");
    checkKeys(camera, {"preset", "duration_seconds", "fps", "fov_deg",
                       "focus_order"}, "camera");
    if (camera.contains("preset"))
        input.preset = text(camera.at("preset"), "camera.preset");
    if (input.preset != "slow_investigation_pan")
        fail("camera.preset", "expected \"slow_investigation_pan\"");
    if (camera.contains("duration_seconds")) {
        input.durationSeconds = number(camera.at("duration_seconds"),
                                       "camera.duration_seconds");
        if (input.durationSeconds < kMinDurationSeconds ||
            input.durationSeconds > kMaxDurationSeconds)
            fail("camera.duration_seconds", "must be within [8, 30]");
    }
    if (camera.contains("fps")) {
        input.fps = integer(camera.at("fps"), "camera.fps");
        if (input.fps < 24 || input.fps > 60)
            fail("camera.fps", "must be within [24, 60]");
    }
    if (camera.contains("fov_deg")) {
        input.fov = number(camera.at("fov_deg"), "camera.fov_deg");
        if (input.fov < 30.0 || input.fov > 60.0)
            fail("camera.fov_deg", "must be within [30, 60]");
    }
    if (camera.contains("focus_order")) {
        const Json& order = camera.at("focus_order");
        if (!order.is_array()) fail("camera.focus_order", "expected an array");
        for (std::size_t i = 0; i < order.size(); ++i) {
            const std::string id = text(order.at(i),
                "camera.focus_order[" + std::to_string(i) + "]");
            input.focusOrder.push_back(id);
        }
    }

    const Json& items = field(root, "items", "");
    if (!items.is_array() || items.empty())
        fail("items", "expected a non-empty array");
    if (items.size() > kMaxItems)
        fail("items", "at most " + std::to_string(kMaxItems) + " items are supported");

    std::set<std::string> itemIds;
    std::map<std::string, std::size_t> itemIndex;
    for (std::size_t i = 0; i < items.size(); ++i) {
        const Json& raw = items.at(i);
        const std::string path = "items[" + std::to_string(i) + "]";
        if (!raw.is_object()) fail(path, "expected an object");
        checkKeys(raw, {"id", "type", "asset", "position", "size", "rotation",
                        "pin", "depth"}, path);
        Item item;
        item.id = text(field(raw, "id", path), path + ".id");
        if (item.id.size() > 64) fail(path + ".id", "at most 64 characters");
        if (!itemIds.insert(item.id).second)
            fail(path + ".id", "duplicate item id \"" + item.id + "\"");
        item.type = text(field(raw, "type", path), path + ".type");
        if (item.type != "photo" && item.type != "document")
            fail(path + ".type", "expected \"photo\" or \"document\"");
        item.asset = text(field(raw, "asset", path), path + ".asset");

        const Json& position = field(raw, "position", path);
        if (!position.is_array() || position.size() != 2)
            fail(path + ".position", "expected [x, y] in board pixels");
        item.x = number(position.at(0), path + ".position[0]");
        item.y = number(position.at(1), path + ".position[1]");
        if (item.x < 0.0 || item.x > input.boardWidth ||
            item.y < 0.0 || item.y > input.boardHeight)
            fail(path + ".position", "must lie inside the board");

        item.width = item.type == "photo" ? kPhotoWidth : kDocumentWidth;
        item.height = item.type == "photo" ? kPhotoHeight : kDocumentHeight;
        if (raw.contains("size")) {
            const Json& size = raw.at("size");
            if (!size.is_array() || size.size() != 2)
                fail(path + ".size", "expected [width, height]");
            item.width = number(size.at(0), path + ".size[0]");
            item.height = number(size.at(1), path + ".size[1]");
            if (item.width < 24.0 || item.height < 24.0 ||
                item.width > input.boardWidth || item.height > input.boardHeight)
                fail(path + ".size", "must be within the board and at least 24 px");
        }
        if (item.x - item.width * 0.5 < 0.0 ||
            item.x + item.width * 0.5 > input.boardWidth ||
            item.y - item.height * 0.5 < 0.0 ||
            item.y + item.height * 0.5 > input.boardHeight)
            fail(path + ".position", "item does not fit inside the board");

        if (raw.contains("rotation")) {
            item.rotation = number(raw.at("rotation"), path + ".rotation");
            if (item.rotation < -30.0 || item.rotation > 30.0)
                fail(path + ".rotation", "must be within [-30, 30] degrees");
        } else {
            item.rotation = static_cast<double>(hashId(item.id) % 9001u) / 1000.0 - 4.5;
        }
        if (raw.contains("depth")) {
            item.depth = number(raw.at("depth"), path + ".depth");
            if (item.depth < 0.0 || item.depth > 6.0)
                fail(path + ".depth", "must be within [0, 6]");
        }
        if (raw.contains("pin")) {
            const Json& pin = raw.at("pin");
            if (!pin.is_boolean()) fail(path + ".pin", "expected a boolean");
            item.pin = pin.get<bool>();
        }

        itemIndex[item.id] = input.items.size();
        input.items.push_back(std::move(item));
    }

    if (root.contains("connections")) {
        const Json& connections = root.at("connections");
        if (!connections.is_array()) fail("connections", "expected an array");
        if (connections.size() > static_cast<std::size_t>(kMaxConnections))
            fail("connections", "at most " + std::to_string(kMaxConnections) +
                                " connections are supported");
        for (std::size_t i = 0; i < connections.size(); ++i) {
            const Json& raw = connections.at(i);
            const std::string path = "connections[" + std::to_string(i) + "]";
            if (!raw.is_object()) fail(path, "expected an object");
            checkKeys(raw, {"from", "to", "width"}, path);
            const std::string from = text(field(raw, "from", path), path + ".from");
            const std::string to = text(field(raw, "to", path), path + ".to");
            if (!itemIndex.count(from)) fail(path + ".from", "unknown item \"" + from + "\"");
            if (!itemIndex.count(to)) fail(path + ".to", "unknown item \"" + to + "\"");
            if (from == to) fail(path, "an item cannot connect to itself");
            Connection connection;
            connection.from = itemIndex.at(from);
            connection.to = itemIndex.at(to);
            if (raw.contains("width")) {
                connection.width = number(raw.at("width"), path + ".width");
                if (connection.width < 1.0 || connection.width > 24.0)
                    fail(path + ".width", "must be within [1, 24]");
            }
            input.connections.push_back(std::move(connection));
        }
    }

    for (const std::string& id : input.focusOrder)
        if (!itemIndex.count(id))
            fail("camera.focus_order", "unknown item \"" + id + "\"");

    if (root.contains("output")) {
        const Json& output = root.at("output");
        if (!output.is_object()) fail("output", "expected an object");
        checkKeys(output, {"path", "format", "codec"}, "output");
        if (output.contains("path"))
            input.outputPath = text(output.at("path"), "output.path");
        if (output.contains("format"))
            input.outputFormat = text(output.at("format"), "output.format");
        if (output.contains("codec"))
            input.outputCodec = text(output.at("codec"), "output.codec");
        if (input.outputFormat != "mp4")
            fail("output.format", "only \"mp4\" is supported");
    }
    return input;
}

double pinAnchorY(const Item& item) {
    return item.y - item.height * 0.5 - kPinHeight * 0.18;
}

// A static rotation must travel through an animation track: the flat
// `rotation` array is ignored for image layers by the current pipeline.
Json constantRotation(double degrees, int frames) {
    Json keys = Json::array();
    keys.push_back(Json::object({{"frame", 0}, {"value", degrees}}));
    keys.push_back(Json::object({{"frame", frames - 1}, {"value", degrees}}));
    Json track = Json::object({{"property", "rotation_z"},
                               {"easing", "linear"},
                               {"keyframes", std::move(keys)}});
    return Json::object({{"tracks", Json::array({std::move(track)})}});
}

Json makeItemLayers(const Input& input, const Item& item, std::size_t index,
                    int frames) {
    const double sceneX = item.x - input.boardWidth * 0.5;
    // Camera-backed image layers use a Y-up basis; board coordinates grow down.
    const double sceneY = -(item.y - input.boardHeight * 0.5);
    const double cardZ = -12.0 - item.depth;
    const Json shadow = Json{{"type", "drop_shadow"}, {"radius", 22.0},
        {"offset", Json::array({10.0, 14.0})},
        {"color", Json::array({0.035, 0.024, 0.014, 0.55})}};
    const std::string id = "item_" + std::to_string(index) + "_";

    Json layers = Json::array();
    layers.push_back(Json{{"id", id + "card"},
        {"type", "image"}, {"asset", item.asset},
        {"position", {sceneX, sceneY, cardZ}},
        {"size", {item.width, item.height}}, {"fit", "cover"},
        {"effects", Json::array({shadow})},
        {"animation", constantRotation(item.rotation, frames)},
        {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", frames}});

    if (item.pin) {
        const double pinY = pinAnchorY(item);
        layers.push_back(Json{{"id", id + "pin"},
            {"type", "image"}, {"asset", input.pinAsset},
            {"position", {item.x - input.boardWidth * 0.5,
                          -(pinY - input.boardHeight * 0.5), -44.0}},
            {"size", {kPinWidth, kPinHeight}}, {"fit", "contain"},
            {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", frames}});
    }
    return layers;
}

// Path shapes are composed in canvas pixels and do not follow the 3D camera.
// A string is therefore a thin image quad (a solid-red 8x8 asset) placed at the
// midpoint of its two pins and rotated onto that segment, so it projects with
// the cards and the pins.
Json makeConnectionLayer(const Input& input, const Connection& connection,
                         std::size_t index, int frames) {
    const Item& from = input.items.at(connection.from);
    const Item& to = input.items.at(connection.to);
    const double ax = from.x - input.boardWidth * 0.5;
    const double bx = to.x - input.boardWidth * 0.5;
    const double ay = -(pinAnchorY(from) - input.boardHeight * 0.5);
    const double by = -(pinAnchorY(to) - input.boardHeight * 0.5);
    const double dx = bx - ax;
    const double dy = by - ay;
    const double length = std::sqrt(dx * dx + dy * dy);
    if (length < 1.0) return Json();

    // Rotation is applied in screen space (Y down): re-mirror the Y delta.
    double degrees = std::atan2(-dy, dx) * 180.0 / kPi;
    // Keep the quad's local +X axis pointing right so its texture is not
    // mirrored when the connection runs right-to-left.
    if (degrees > 90.0) degrees -= 180.0;
    if (degrees < -90.0) degrees += 180.0;

    return Json{{"id", "string_" + std::to_string(index)},
        {"type", "image"}, {"asset", input.stringAsset},
        {"position", {(ax + bx) * 0.5, (ay + by) * 0.5, -40.0}},
        {"size", {length, std::max(3.0, connection.width)}},
        {"fit", "stretch"},
        {"animation", constantRotation(degrees, frames)},
        {"enable_3d", true}, {"start_frame", 0}, {"duration_frames", frames}};
}

struct CameraKey {
    int frame = 0;
    double x = 0.0;
    double y = 0.0;
    double z = -2000.0;
    double yaw = 0.0;
};

// The authoring `fov_deg` is the vertical field of view we want on screen.
// RenderPlan's video projection multiplies the authored tangent by the canvas
// aspect, so lower the authoring value to the plan value that produces it.
double planFovDegrees(const Input& input) {
    const double aspect = static_cast<double>(input.canvasWidth) /
                          static_cast<double>(input.canvasHeight);
    const double half = std::tan(input.fov * 0.5 * kPi / 180.0);
    return 2.0 * std::atan(half / aspect) * 180.0 / kPi;
}

Json cameraAt(const Input& input, const CameraKey& key) {
    return Json{{"type", "perspective"},
        {"position", Json::array({key.x, key.y, key.z})},
        {"rotation_deg", Json::array({0.0, key.yaw, 0.0})},
        {"fov_deg", planFovDegrees(input)}, {"near", 1.0},
        {"far", 30000.0}, {"zoom", 1.0}};
}

std::vector<CameraKey> buildCameraKeys(const Input& input,
                                       const std::vector<std::size_t>& focus,
                                       int frames, double focusDistance,
                                       double wideDistance, int introEnd,
                                       int outroEnd) {
    // Camera samples are resolved in the same centred scene space as the image
    // layers (0,0 is the board centre); the renderer adds the canvas centre.
    constexpr double centerX = 0.0;
    constexpr double centerY = 0.0;
    const double halfW = input.boardWidth * 0.5;
    const double halfH = input.boardHeight * 0.5;
    const double focusYaw = 1.35;

    // Distribute the focus block between intro and outro, giving every target
    // a move plus a settle hold expressed by a second key at the same spot.
    const int available = std::max(1, outroEnd - introEnd);
    const int count = static_cast<int>(focus.size());
    const int perFocus = count > 0 ? std::max(6, available / count) : available;
    const int moveFrames = std::max(6, static_cast<int>(perFocus * 0.62));
    const int holdFrames = std::max(2, perFocus - moveFrames);

    std::vector<CameraKey> keys;
    keys.push_back({0, centerX + halfW * 0.02, centerY - halfH * 0.015,
                    -wideDistance * 1.02, 0.0});
    keys.push_back({introEnd, centerX, centerY, -wideDistance, 0.0});
    int cursor = introEnd;
    for (int i = 0; i < count; ++i) {
        const Item& item = input.items.at(focus[static_cast<std::size_t>(i)]);
        const double targetX = centerX + (item.x - halfW);
        const double targetY = centerY - (item.y - halfH);
        const double yaw = (i % 2 == 0) ? focusYaw : -focusYaw;
        const int moveEnd = std::min(outroEnd - 1, cursor + moveFrames);
        keys.push_back({moveEnd, targetX, targetY, -focusDistance, yaw});
        const int holdEnd = std::min(outroEnd - 1, moveEnd + holdFrames);
        keys.push_back({holdEnd, targetX, targetY, -focusDistance, yaw});
        cursor = holdEnd;
    }
    keys.push_back({frames - 1, centerX, centerY, -wideDistance, 0.0});
    return keys;
}

Json cameraSamples(const Input& input, const std::vector<CameraKey>& keys,
                   int frames) {
    Json samples = Json::array();
    std::size_t segment = 0;
    for (int frame = 0; frame < frames; ++frame) {
        while (segment + 1 < keys.size() && frame > keys[segment + 1].frame)
            ++segment;
        const CameraKey& left = keys[segment];
        const CameraKey& right = keys[std::min(segment + 1, keys.size() - 1)];
        const int span = std::max(1, right.frame - left.frame);
        const double raw = static_cast<double>(frame - left.frame) / span;
        const double t = (frame <= left.frame) ? 0.0
                        : (frame >= right.frame) ? 1.0
                                                 : smoothstep(raw);
        const double seconds = static_cast<double>(frame) / input.fps;
        // A restrained handheld float keeps static holds alive; it is a pure
        // function of the frame so renders stay reproducible.
        const double driftX = 1.8 * std::sin(2.0 * kPi * 0.11 * seconds + 0.7);
        const double driftY = 1.2 * std::sin(2.0 * kPi * 0.083 * seconds + 1.9);
        const double driftYaw = 0.10 * std::sin(2.0 * kPi * 0.07 * seconds + 0.4);

        CameraKey sample;
        sample.x = left.x + (right.x - left.x) * t + driftX;
        sample.y = left.y + (right.y - left.y) * t + driftY;
        sample.z = left.z + (right.z - left.z) * t;
        sample.yaw = left.yaw + (right.yaw - left.yaw) * t + driftYaw;
        samples.push_back(Json{{"frame", frame},
                               {"camera", cameraAt(input, sample)}});
    }
    return samples;
}

Json buildPlan(const Input& input) {
    const int frames = std::max(2, static_cast<int>(
        std::llround(input.durationSeconds * input.fps)));
    const double halfFov = input.fov * 0.5 * kPi / 180.0;
    const double tanHalf = std::tan(halfFov);
    const double aspect = static_cast<double>(input.canvasWidth) /
                          static_cast<double>(input.canvasHeight);
    // Slightly overfill the frame so the establishing shot has no black edges.
    const double wideDistance =
        std::max(input.boardHeight * 0.5 / tanHalf,
                 input.boardWidth * 0.5 / (tanHalf * aspect)) * 0.96;

    std::vector<std::size_t> focus;
    if (!input.focusOrder.empty()) {
        for (const std::string& id : input.focusOrder)
            for (std::size_t i = 0; i < input.items.size(); ++i)
                if (input.items[i].id == id) focus.push_back(i);
    } else {
        std::set<std::size_t> seen;
        for (const Connection& connection : input.connections) {
            if (seen.insert(connection.from).second) focus.push_back(connection.from);
            if (seen.insert(connection.to).second) focus.push_back(connection.to);
        }
        if (focus.empty())
            for (std::size_t i = 0; i < std::min<std::size_t>(6, input.items.size()); ++i)
                focus.push_back(i);
    }
    if (focus.size() > 10) focus.resize(10);

    double focusDistance = wideDistance * 0.62;
    if (!focus.empty()) {
        const Item& primary = input.items.at(focus.front());
        const double byHeight = primary.height * 0.5 * 1.30 / tanHalf;
        const double byWidth = primary.width * 0.5 * 1.45 / (tanHalf * aspect);
        focusDistance = clamp(std::max(byHeight, byWidth), 320.0,
                              wideDistance * 0.92);
    }

    const int introEnd = std::max(6, static_cast<int>(std::lround(frames * 0.10)));
    const int outroFrames = std::max(10, static_cast<int>(std::lround(frames * 0.18)));
    const int outroStart = std::max(introEnd + 1, frames - 1 - outroFrames);
    const std::vector<CameraKey> keys = buildCameraKeys(
        input, focus, frames, focusDistance, wideDistance, introEnd, outroStart);
    const Json samples = cameraSamples(input, keys, frames);

    Json layers = Json::array();
    layers.push_back(Json{{"id", "corkboard"},
        {"type", "image"}, {"asset", input.boardAsset},
        {"position", {0.0, 0.0, 0.0}},
        {"size", {input.boardWidth, input.boardHeight}},
        {"fit", "cover"}, {"enable_3d", true},
        {"start_frame", 0}, {"duration_frames", frames}});

    for (std::size_t i = 0; i < input.connections.size(); ++i) {
        Json stringLayer = makeConnectionLayer(input, input.connections[i], i, frames);
        if (!stringLayer.is_null()) layers.push_back(std::move(stringLayer));
    }
    for (std::size_t i = 0; i < input.items.size(); ++i) {
        Json itemLayers = makeItemLayers(input, input.items[i], i, frames);
        for (auto& layer : itemLayers) layers.push_back(std::move(layer));
    }

    return Json{{"schema", "chronon.render-plan.v3"}, {"version", 3},
        {"job_id", "investigation_board"},
        {"canvas", {{"width", input.canvasWidth}, {"height", input.canvasHeight},
                    {"fps_num", input.fps}, {"fps_den", 1},
                    {"duration_frames", frames}}},
        {"camera", samples.front().at("camera")},
        {"camera_samples", std::move(samples)},
        {"layers", std::move(layers)},
        {"output", {{"path", input.outputPath},
                    {"format", input.outputFormat},
                    {"codec", input.outputCodec}}}};
}
}

int main(int argc, char** argv) try {
    if (argc < 2 || argc > 3)
        throw std::runtime_error(
            "usage: emit_investigation_board <input.json> [plan.json]");
    const fs::path inputPath = argv[1];
    const fs::path outputPath = argc == 3 ? fs::path(argv[2])
        : fs::path("ChrononTemplate/out/investigation_board") /
              (inputPath.stem().string() + ".plan.json");

    std::ifstream inputFile(inputPath, std::ios::binary);
    if (!inputFile)
        throw std::runtime_error("cannot open input: " + inputPath.string());
    Json root;
    try {
        inputFile >> root;
    } catch (const std::exception& error) {
        throw std::runtime_error("invalid JSON in " + inputPath.string() + ": " +
                                 error.what());
    }

    const Input input = parseInput(root);
    const Json plan = buildPlan(input);

    if (!outputPath.parent_path().empty())
        fs::create_directories(outputPath.parent_path());
    std::ofstream outputFile(outputPath, std::ios::binary | std::ios::trunc);
    if (!outputFile || !(outputFile << plan.dump(2) << '\n'))
        throw std::runtime_error("cannot write plan: " + outputPath.string());

    std::cout << "Wrote " << outputPath << " (" << input.items.size()
              << " items, " << input.connections.size() << " connections, "
              << plan.at("canvas").at("duration_frames").get<int>()
              << " frames at " << input.fps << " fps)\n";
    return 0;
} catch (const std::exception& error) {
    std::cerr << "emit_investigation_board: " << error.what() << '\n';
    return 1;
}
