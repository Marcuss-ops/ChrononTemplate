#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace fs = std::filesystem;
using json = nlohmann::json;
namespace {
constexpr int kWidth = 1920;
constexpr int kHeight = 1080;
constexpr int kFps = 30;
constexpr int kFrames = 150;
using Point = std::array<double, 2>;

json rgba(const std::string& hex, double alpha = 1.0) {
    const auto part = [&](std::size_t at) { return std::stoi(hex.substr(at, 2), nullptr, 16) / 255.0; };
    return json::array({part(1), part(3), part(5), alpha});
}
json track(const std::string& property, std::vector<std::pair<int, double>> keys,
           const std::string& easing = "out_cubic") {
    json keyframes = json::array();
    for (const auto& [frame, value] : keys)
        keyframes.push_back({{"frame", frame}, {"value", value}});
    return {{"property", property}, {"easing", easing}, {"keyframes", keyframes}};
}
json animation(std::vector<json> tracks) { return {{"tracks", tracks}}; }
json colorLayer(const std::string& id, const std::string& color) {
    return {{"id", id}, {"type", "color"}, {"color", rgba(color)},
            {"size", {kWidth, kHeight}}, {"position", {0, 0}},
            {"start_frame", 0}, {"duration_frames", kFrames}, {"screen_space", true}};
}
json rectLayer(const std::string& id, Point center, Point size, const std::string& fill,
               int reveal = 0, double radius = 0.0) {
    json geometry = {{"type", radius > 0.0 ? "rounded_rect" : "rect"}, {"fill", rgba(fill)}};
    if (radius > 0.0) geometry["radius"] = radius;
    json layer = {{"id", id}, {"type", "shape"}, {"shape", geometry}, {"size", size},
                  {"position", center}, {"start_frame", 0}, {"duration_frames", kFrames},
                  {"screen_space", true}};
    if (reveal > 0) layer["animation"] = animation({track("opacity", {{0, 0}, {reveal, 1}, {kFrames - 1, 1}})});
    return layer;
}
json textLayer(const std::string& id, const std::string& text, Point center, Point size,
               double fontSize, const std::string& color, const std::string& font,
               int reveal = 0, const std::string& align = "center") {
    (void)align;
    json layer = {{"id", id}, {"type", "text"}, {"text", text}, {"size", size},
                  {"position", center}, {"style", {{"font", font}, {"font_size", fontSize},
                  {"min_font_size", fontSize}, {"max_font_size", fontSize},
                  {"fit_mode", "shrink_only"}, {"fill", color}}},
                  {"start_frame", 0}, {"duration_frames", kFrames}, {"screen_space", true}};
    if (reveal > 0) layer["animation"] = animation({track("opacity", {{0, 0}, {reveal, 1}, {kFrames - 1, 1}})});
    return layer;
}
json pathLayer(const std::string& id, const json& commands, const std::string& fill,
               const std::string& stroke, double strokeWidth, int reveal,
               bool drawOn = false) {
    json geometry = {{"type", "path"}, {"path", commands}};
    if (!fill.empty()) geometry["fill"] = rgba(fill);
    if (!stroke.empty()) geometry["stroke"] = {{"color", stroke}, {"width", strokeWidth},
                                                {"cap", "round"}, {"join", "round"}};
    json layer = {{"id", id}, {"type", "shape"}, {"shape", geometry},
                  {"size", {kWidth, kHeight}}, {"position", {kWidth / 2.0, kHeight / 2.0}},
                  {"start_frame", 0}, {"duration_frames", kFrames}, {"screen_space", true}};
    if (drawOn) {
        layer["shape"]["operators"] = json::array({{{"kind", "trim"}, {"params", {
            {"start", 0.0}, {"end", 0.0}, {"animation", {{"easing", "linear"},
                {"keyframes", json::array({{{"frame", reveal}, {"value", 0.0}},
                                           {{"frame", reveal + 48}, {"value", 1.0}}})}}}}}}});
    } else if (reveal > 0) {
        layer["animation"] = animation({track("opacity", {{0, 0}, {reveal, 1}, {kFrames - 1, 1}})});
    }
    return layer;
}
json moveTo(Point p) { return {{"type", "move_to"}, {"point", {p[0], p[1]}}}; }
json lineTo(Point p) { return {{"type", "line_to"}, {"point", {p[0], p[1]}}}; }
json closePath() { return {{"type", "close"}}; }
json plan(const std::string& id, json layers, const std::string& output) {
    return {{"schema", "chronon.render-plan.v3"}, {"version", 3}, {"job_id", id},
            {"canvas", {{"width", kWidth}, {"height", kHeight}, {"fps_num", kFps},
                        {"fps_den", 1}, {"duration_frames", kFrames}}},
            {"layers", std::move(layers)},
            {"output", {{"path", output}, {"format", "mp4"}, {"codec", "h264"}}}};
}
void writePlan(const fs::path& out, const std::string& id, const json& doc) {
    std::ofstream stream(out / (id + ".plan.json"));
    if (!stream) throw std::runtime_error("cannot write plan: " + (out / (id + ".plan.json")).string());
    stream << doc.dump(2) << '\n';
}
std::vector<std::vector<Point>> polygons(const json& geometry) {
    std::vector<std::vector<Point>> result;
    auto readPolygon = [&](const json& polygon) {
        if (polygon.empty()) return;
        std::vector<Point> ring;
        for (const auto& coord : polygon[0])
            ring.push_back({coord[0].get<double>(), coord[1].get<double>()});
        result.push_back(std::move(ring));
    };
    const auto type = geometry.at("type").get<std::string>();
    if (type == "Polygon") readPolygon(geometry.at("coordinates"));
    else if (type == "MultiPolygon") for (const auto& polygon : geometry.at("coordinates")) readPolygon(polygon);
    return result;
}
std::vector<Point> clipRing(std::vector<Point> points) {
    constexpr std::array<double, 4> limits{20.0, 42.5, 20.0, 38.0};
    struct Edge { int axis; double value; bool greater; };
    const std::array<Edge, 4> edges{{{0, limits[0], true}, {0, limits[1], false},
                                     {1, limits[2], true}, {1, limits[3], false}}};
    for (const auto& edge : edges) {
        if (points.empty()) break;
        std::vector<Point> output;
        auto inside = [&](const Point& p) { return edge.greater ? p[edge.axis] >= edge.value : p[edge.axis] <= edge.value; };
        Point previous = points.back();
        for (const auto& current : points) {
            const bool a = inside(previous), b = inside(current);
            if (a != b) {
                const double delta = current[edge.axis] - previous[edge.axis];
                const double ratio = delta == 0.0 ? 0.0 : (edge.value - previous[edge.axis]) / delta;
                output.push_back({previous[0] + ratio * (current[0] - previous[0]),
                                  previous[1] + ratio * (current[1] - previous[1])});
            }
            if (b) output.push_back(current);
            previous = current;
        }
        points = std::move(output);
    }
    return points;
}
Point project(double lon, double lat) { return {960.0 + (lon - 31.0) * 82.0, 540.0 - (lat - 29.0) * 65.0}; }
Point localPoint(const Point& point) { return {point[0] - 960.0, point[1] - 540.0}; }
json polygonCommands(const std::vector<Point>& points) {
    json commands = json::array();
    if (points.size() < 3) return commands;
    // Natural Earth rings can be dense; retain their shape while limiting plan size.
    std::vector<Point> reduced; reduced.reserve(points.size());
    Point last{}; bool haveLast = false;
    for (const auto& p : points) {
        if (!haveLast || std::hypot(p[0]-last[0], p[1]-last[1]) >= 1.5) { reduced.push_back(p); last = p; haveLast = true; }
    }
    if (reduced.size() < 3 && points.size() >= 3)
        reduced = {points.front(), points[points.size()/3], points[(points.size()*2)/3]};
    commands.push_back(moveTo(localPoint(project(reduced.front()[0], reduced.front()[1]))));
    for (std::size_t i=1; i<reduced.size(); ++i) commands.push_back(lineTo(localPoint(project(reduced[i][0], reduced[i][1]))));
    commands.push_back(closePath());
    return commands;
}
void emitMap(const fs::path& root, const fs::path& plans) {
    const auto geo = json::parse(std::ifstream(root / "ChrononTemplate/catalog/ne_50m_admin_0_countries.geojson"));
    const std::map<std::string,std::string> colors{{"Egypt","#188879"},{"Israel","#DE5A60"},
        {"Palestine","#DE5A60"},{"Jordan","#6176D5"},{"Lebanon","#D8D8D3"},
        {"Syria","#D8D8D3"},{"Saudi Arabia","#C89560"},{"Iraq","#D7D6D0"},
        {"Sudan","#D7D6D0"},{"Libya","#D7D6D0"}};
    json layers=json::array(); layers.push_back(colorLayer("sea", "#D1E2E7"));
    // Graticule is a single native path so the full canvas is not allocated once per line.
    json graticule=json::array();
    for (int lon=20; lon<=42; lon+=2) {
        auto a=project(lon,20), b=project(lon,38);
        graticule.push_back(moveTo(localPoint(a))); graticule.push_back(lineTo(localPoint(b)));
    }
    for (int lat=20; lat<=38; lat+=2) {
        auto a=project(20,lat), b=project(42,lat);
        graticule.push_back(moveTo(localPoint(a))); graticule.push_back(lineTo(localPoint(b)));
    }
    layers.push_back(pathLayer("map_graticule",graticule,"","#C2D6DC",1.0,0));
    const std::set<std::string> wanted{"Egypt","Israel","Palestine","Jordan","Lebanon","Syria","Saudi Arabia","Iraq","Sudan","Libya"};
    std::map<std::string,json> countryPaths;
    for (const auto& feature : geo.at("features")) {
        const auto& props=feature.at("properties");
        const std::string country=props.value("ADMIN",props.value("NAME",std::string{}));
        if (!wanted.contains(country)) continue;
        json& commands=countryPaths[country];
        for (auto ring : polygons(feature.at("geometry"))) {
            ring=clipRing(std::move(ring));
            auto subpath=polygonCommands(ring);
            for (auto& cmd : subpath) commands.push_back(std::move(cmd));
        }
    }
    // Keep one native country path per country: this preserves national colors
    // at runtime instead of merging every surrounding border into one bitmap.
    const std::array<std::string,10> drawOrder{"Libya","Sudan","Egypt","Syria","Lebanon",
                                                "Israel","Palestine","Jordan","Saudi Arabia","Iraq"};
    for (const auto& country : drawOrder) {
        const auto it=countryPaths.find(country);
        if (it==countryPaths.end() || it->second.empty()) continue;
        std::string id=country;
        std::replace(id.begin(),id.end(),' ','_');
        const int reveal=country=="Egypt" ? 15 : country=="Israel" ? 22 : country=="Palestine" ? 28 : 8;
        layers.push_back(pathLayer("country_"+id+"_vector",it->second,colors.at(country),"#FAF9F4",3.0,reveal));
    }
    const std::vector<Point> sinaiGeo{{32.45,31.08},{34.35,31.15},{34.82,29.75},
                                      {34.55,28.65},{33.40,27.85},{32.45,29.30}};
    std::vector<Point> sinai; for (auto p:sinaiGeo) sinai.push_back(project(p[0],p[1]));
    json sinaiCommands=polygonCommands(sinaiGeo);
    layers.push_back(pathLayer("sinai_vector_region",sinaiCommands,"#187D71","#FFFFFF",5.0,38));
    json outline=json::array(); outline.push_back(moveTo(localPoint(sinai.front())));
    for(std::size_t i=1;i<sinai.size();++i) outline.push_back(lineTo(localPoint(sinai[i])));
    outline.push_back(closePath());
    layers.push_back(pathLayer("sinai_boundary_draw",outline,"","#173D39",4.0,42,true));
    const auto insidePolygon=[](const Point& p,const std::vector<Point>& polygon){
        bool inside=false;
        for(std::size_t i=0,j=polygon.size()-1;i<polygon.size();j=i++){
            const auto& a=polygon[i]; const auto& b=polygon[j];
            if(((a[1]>p[1])!=(b[1]>p[1])) &&
               p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1]+1e-12)+a[0]) inside=!inside;
        }
        return inside;
    };
    json hatch=json::array();
    const auto [minXIt,maxXIt]=std::minmax_element(sinai.begin(),sinai.end(),[](const Point& a,const Point& b){return a[0]<b[0];});
    const auto [minYIt,maxYIt]=std::minmax_element(sinai.begin(),sinai.end(),[](const Point& a,const Point& b){return a[1]<b[1];});
    for(double x=minXIt->at(0)-220;x<maxXIt->at(0)+220;x+=22.0){
        bool drawing=false; Point start{}; Point last{};
        for(double y=minYIt->at(1);y<=maxYIt->at(1);y+=5.0){
            const Point p{x+(y-minYIt->at(1))*0.55,y};
            const bool in=insidePolygon(p,sinai);
            if(in && !drawing){start=p; drawing=true;}
            if(in){last=p; continue;}
            if(drawing){hatch.push_back(moveTo(localPoint(start))); hatch.push_back(lineTo(localPoint(last))); drawing=false;}
        }
        if(drawing){hatch.push_back(moveTo(localPoint(start))); hatch.push_back(lineTo(localPoint(last)));}
    }
    if(!hatch.empty()) layers.push_back(pathLayer("sinai_hatch_lines",hatch,"","#174D47",2.2,44));
    const std::vector<Point> routeGeo{{32.55,30.00},{32.95,30.20},{33.35,30.40},{33.75,30.58},{34.20,30.76},{34.55,30.90}};
    json route=json::array(); route.push_back(moveTo(localPoint(project(routeGeo.front()[0],routeGeo.front()[1]))));
    for(std::size_t i=1;i<routeGeo.size();++i) route.push_back(lineTo(localPoint(project(routeGeo[i][0],routeGeo[i][1]))));
    layers.push_back(pathLayer("suez_to_sinai_route",route,"", "#F14D36",7.0,54,true));
    layers.push_back(textLayer("map_eyebrow","MEDIO ORIENTE · 1973",{342,78},{520,28},20,"#6F706B","Chronon3d/assets/fonts/Inter-Regular.ttf",8));
    layers.push_back(textLayer("map_title","IL FRONTE DEL SINAI",{410,120},{620,54},34,"#121516","Chronon3d/assets/fonts/Inter-Bold.ttf",14));
    const std::array<std::tuple<std::string,double,double,int,double,double,double>,3> cities{{
        {"IL CAIRO",31.2357,30.0444,70,-80,-25,17},
        {"SUEZ",32.55,29.97,82,45,34,17},
        {"GAZA",34.4668,31.5017,94,55,-22,18}}};
    for(const auto& [name,lon,lat,frame,labelDx,labelDy,labelSize]:cities){
        const auto p=project(lon,lat);
        json marker={{"id","place_marker_"+name},{"type","shape"},
            {"shape",{{"type","ellipse"},{"fill",rgba("#F14D36")},
                      {"stroke",{{"color","#FFFDF7"},{"width",3.0}}}}},
            {"size",{18,18}},{"position",{p[0],p[1]}},{"start_frame",frame},
            {"duration_frames",kFrames-frame},{"screen_space",true},
            {"animation",animation({track("scale",{{0,0.1},{10,1.0},{kFrames-frame-1,1.0}}),
                                    track("opacity",{{0,0.0},{8,1.0},{kFrames-frame-1,1.0}})})}};
        layers.push_back(std::move(marker));
        auto label=textLayer("city_label_"+name,name,{p[0]+labelDx,p[1]+labelDy},{155,30},labelSize,"#121516","Chronon3d/assets/fonts/Inter-Bold.ttf",frame+4);
        label["style"]["background"]={{"color","#FAF9F4"},{"opacity",0.94},{"radius",8},{"padding",{8,4}}};
        layers.push_back(std::move(label));
    }
    const auto addRegionLabel=[&](const std::string& id,const std::string& value,double lon,double lat,
                                  double width,double fontSize,const std::string& fill){
        const auto p=project(lon,lat);
        auto label=textLayer(id,value,p,{width,fontSize+12},fontSize,fill,
                             "Chronon3d/assets/fonts/Inter-Bold.ttf",92);
        layers.push_back(std::move(label));
    };
    addRegionLabel("country_label_egypt","EGITTO",28.0,27.4,230,38,"#F9F7F1");
    addRegionLabel("country_label_israel","ISRAELE",34.85,32.45,180,24,"#121516");
    addRegionLabel("region_label_sinai","DESERTO DEL SINAI",33.25,29.55,300,20,"#121516");
    writePlan(plans,"ref_map_sinai",plan("ref_map_sinai",std::move(layers),"ChrononTemplate/out/oil_crisis_1973_animation_samples/ref_map_sinai.mp4"));
}
void emitDate(const fs::path& plans) {
    json layers=json::array(); layers.push_back(colorLayer("archival_black","#0F1112"));
    auto horizontal=rectLayer("date_bracket_horizontal",{480,700},{960,5},"#F14D36");
    horizontal["animation"]=animation({track("scale_x",{{0,0.001},{58,1.0},{kFrames-1,1.0}})});
    layers.push_back(std::move(horizontal));
    auto vertical=rectLayer("date_bracket_vertical",{960,626},{5,148},"#F14D36");
    vertical["animation"]=animation({track("scale_y",{{0,0.001},{16,0.001},{70,1.0},{kFrames-1,1.0}})});
    layers.push_back(std::move(vertical));
    auto panel=rectLayer("date_coral_panel",{960,480},{900,145},"#F14D36",12,3.0);
    panel["animation"]=animation({track("scale_x",{{0,0.02},{24,1.0},{kFrames-1,1.0}}),track("opacity",{{0,0},{20,1},{kFrames-1,1}})});
    layers.push_back(std::move(panel));
    layers.push_back(textLayer("date_text","6 ottobre 1973",{960,480},{850,126},91,"#FFF9EE","Chronon3d/assets/fonts/Didot-Italic.ttf",25));
    writePlan(plans,"ref_date_october_1973",plan("ref_date_october_1973",std::move(layers),"ChrononTemplate/out/oil_crisis_1973_animation_samples/ref_date_october_1973.mp4"));
}
void emitImage(const fs::path& plans) {
    json layers=json::array(); layers.push_back(colorLayer("charcoal_background","#0E1011"));
    auto edge=rectLayer("coral_card_edge",{965,530},{1518,852},"#F14D36",0,18.0);
    edge["animation"]=animation({track("opacity",{{0,0},{30,1},{kFrames-1,1}}),track("scale",{{0,0.97},{38,1.0},{kFrames-1,1.0}})});
    layers.push_back(std::move(edge));
    json photo={{"id","refinery_image_fade_in"},{"type","image"},
        {"asset","ChrononTemplate/assets/images/showcase/refinery_rounded.png"},
        {"size",{1510,844}},{"position",{0,0}},{"fit","cover"},{"opacity",0.0},
        {"start_frame",0},{"duration_frames",kFrames},{"screen_space",true},
        {"animation",animation({track("opacity",{{0,0},{8,0},{42,1},{kFrames-1,1}}),track("scale",{{0,0.97},{42,1.0},{kFrames-1,1.0}})})}};
    layers.push_back(std::move(photo));
    writePlan(plans,"ref_image_fade_in",plan("ref_image_fade_in",std::move(layers),"ChrononTemplate/out/oil_crisis_1973_animation_samples/ref_image_fade_in.mp4"));
}
} // namespace

int main(int argc,char** argv){
    try{
        if(argc!=2) throw std::runtime_error("usage: chronontemplate_emit_oil_crisis_reference_plans <workspace-root>");
        const fs::path root=fs::absolute(argv[1]);
        const fs::path plans=root/"ChrononTemplate/out/oil_crisis_1973_animation_samples/plans";
        fs::create_directories(plans);
        emitMap(root,plans); emitDate(plans); emitImage(plans);
        std::cout<<"Emitted native C++ render plans for vector map, date marker, and image fade.\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
