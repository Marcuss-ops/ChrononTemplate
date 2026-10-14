#include "chronontemplate/backgrounds/ProceduralBackground.hpp"
#include "chronontemplate/elements/HighlightingV2.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cmath>

using namespace chronontemplate::native;
namespace {
constexpr int frames=150;
Json text(const std::string& id,const std::string& content,float x,float y,float width,float size,
          const std::string& color="#E9EDF3") {
    auto layer=Text::layer(id,content,{x,y,0},{width,160},"Chronon3d/assets/fonts/Inter-Regular.ttf",
                           size,color,frames);
    layer.erase("enable_3d");
    layer["position"]={x,y};
    return layer;
}
Json document() {
    Json layers=Json::array({{{"id","backdrop"},{"type","color"},{"color",Material::rgba("#101725")},
        {"size",{1920,1080}},{"position",{0,0}},{"start_frame",0},{"duration_frames",frames}},
        {{"id","paper"},{"type","color"},{"color",Material::rgba("#EAE5D7")},
        {"size",{1350,880}},{"position",{285,100}},{"start_frame",0},{"duration_frames",frames}}});
    layers.push_back(text("masthead","THE CHRONON JOURNAL",960,220,1160,46,"#25292F"));
    layers.push_back(text("headline","Evidence changes the story",960,350,1160,66,"#171E28"));
    layers.push_back(text("article","The investigation follows the evidence.\nA date, a document, a detail: each matters.\nIndependent sources confirm the timeline.",
        960,540,1160,36,"#25292F"));
    layers.push_back(text("source","ARCHIVE / RESEARCH / 12 OCTOBER 2026",960,850,1160,26,"#54606E"));
    return layers;
}
Json highlight(const std::string& name,unsigned index) {
    Json layers=document();
    if (index==0) {
        layers=Json::array({layers[0]});
        for (unsigned i=0;i<4;++i) {
            const auto style=highlightingStyle(highlightingPresets()[i]);
            auto marker=style;marker.width=24.f+i*9.f;
            layers.push_back(highlightStroke("marker_"+std::to_string(i),{{330,250.f+i*160},{1570,250.f+i*160}},
                marker,5+i*12,45+i*12,frames));
            layers.push_back(text("sample_"+std::to_string(i),highlightingPresets()[i],960,240.f+i*160,1200,48));
        }
    } else if (index==1) {
        layers=Json::array({layers[0]});
        for (unsigned i=0;i<12;++i) {
            std::vector<Paths::Point> points;
            const float x=170.f+(i%3)*590.f,y=210.f+(i/3)*210.f;
            for (unsigned j=0;j<=32;++j) points.push_back({x+j*14.f,y+(i%4)*2.f*std::sin(j*.25f)});
            auto style=highlightingStyle(i%3==0?"underline_glow":"underline_clean");
            style.widthEm=0;style.width=.5f+i*1.5f;style.dashed=i%4==0;
            layers.push_back(highlightStroke("underline_"+std::to_string(i),points,style,i*4,45+i*4,frames));
            layers.push_back(text("label_"+std::to_string(i),std::to_string(style.width)+" px",x+220,y-48,400,26));
        }
    } else if (index==4 || index==7) {
        const std::string content=index==7?"12 OCTOBER 2026 / 42 SOURCES / 98% VERIFIED":
            "The investigation follows the evidence.\nA date, a document, a detail: each matters.\nIndependent sources confirm the timeline.";
        auto layer=text("native_layout_highlight",content,960,550,1080,44,"#101725");
        layer["spans"]=Json::array({highlightSpan(content,0,content.size(),"evidence-text",highlightingStyle("marker_soft"))});
        layers.erase(layers.begin()+4);
        layers.push_back(layer);
    } else {
        auto style=highlightingStyle(index==3?"evidence_red":"underline_glow");
        layers.push_back(highlightStroke("headline_underline",{{405,405},{1515,405}},style,8,55,frames));
        std::vector<Paths::Point> outline{{390,290},{1530,290},{1530,410},{390,410},{390,290}};
        if (index==3) {
            outline.clear();
            for (unsigned j=0;j<=96;++j) {
                const float a=j*6.2831853f/96;
                outline.push_back({960+580*std::cos(a),350+95*std::sin(a)});
            }
        }
        auto regionStyle=highlightingStyle(index==3?"investigation_circle":"box_outline");
        regionStyle.glow=index==6;
        auto region=highlightStroke("focus_outline",outline,regionStyle,12,65,frames);
        if (index==5) region["animation"]={{"tracks",Json::array({Motion::track("position",{{0,{0,0}},{149,{0,140}}},"in_out_sine")})}};
        if (index==6) region["animation"]={{"tracks",Json::array({Motion::track("opacity",{{0,.2},{50,1},{100,.4},{149,1}},"in_out_sine")})}};
        layers.push_back(region);
        if (index==2 || index==8 || index==9) {
            for (const auto& dim:focusDim({380,280,1160,150},.62f,frames)) layers.push_back(dim);
        }
        if (index==3 || index==9) {
            auto connector=highlightingStyle("callout_elbow");
            layers.push_back(highlightStroke("evidence_connector",{{1450,410},{1630,470},{1630,690},{1350,690}},
                connector,65,100,frames));
            layers.push_back(text("evidence_note","SOURCE VERIFIED",1420,750,600,30,"#72CFFF"));
        }
    }
    if (index==5) {
        // The target and its annotation share the exact same sampled motion.
        const auto track=Motion::track("position",{{0,{960,350}},{149,{960,490}}},"in_out_sine");
        layers[3]["animation"]={{"tracks",Json::array({track})}};
    }
    if (index==2 || index==9) {
        // Camera-only 2D presentation: same affine transform on every layer,
        // preserving all content/annotation relationships during the push.
        for (auto& layer:layers) {
            const auto p=layer.value("position",Json::array({0,0}));
            const float x=p[0].get<float>(), y=p[1].get<float>();
            auto& tracks=layer["animation"]["tracks"];
            if (tracks.is_null()) tracks=Json::array();
            tracks.push_back(Motion::track("position",{{0,{x,y}},
                {149,{960+(x-960)*1.1f,350+(y-350)*1.1f}}},"in_out_sine"));
            tracks.push_back(Motion::track("scale",{{0,1.f},{149,1.1f}},"in_out_sine"));
        }
    }
    return TemplateComposition::renderPlan(name,1920,1080,30,frames,layers);
}
void write(const std::filesystem::path& dir,const std::string& name,Json plan) {
    plan["output"]["path"]=(dir/(name+".mp4")).string();
    std::ofstream file(dir/(name+".plan.json"));
    if (!file) throw std::runtime_error("cannot open plan output");
    file<<plan.dump(2)<<'\n';
    if (!file) throw std::runtime_error("cannot write plan output");
}
}
int main(int argc,char** argv) {
    try {
        if (argc!=2) throw std::invalid_argument("usage: emit_procedural_documentary_v2 OUTPUT_DIR");
        const std::filesystem::path dir=std::filesystem::absolute(argv[1]);
        std::filesystem::create_directories(dir);
        for (const auto& preset:proceduralBackgroundPresets()) {
            ProceduralBackgroundSpec s;s.preset=preset;
            write(dir,preset,proceduralBackground(s));
        }
        const std::vector<std::string> names={"01_marker_quality","02_underline_various","03_web_article_focus",
            "04_newspaper_investigation","05_multi_line_highlight","06_tracking_focus","07_glow_outline",
            "08_data_highlight","09_mask_spotlight","10_documentary_master"};
        for (unsigned i=0;i<names.size();++i) write(dir,names[i],highlight(names[i],i));
        std::cout<<"Emitted 17 RenderPlan V3 compositions\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
