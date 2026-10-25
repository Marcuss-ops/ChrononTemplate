#include "chronontemplate/core/NativePrimitives.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using chronontemplate::native::Json;
using chronontemplate::native::Material;
using chronontemplate::native::TemplateComposition;

namespace {
constexpr int W = 1920, H = 1080, FPS = 30, FRAMES = 240;
constexpr const char* regular = "assets/fonts/Inter-Regular.ttf";
constexpr const char* bold = "assets/fonts/Inter-Bold.ttf";

struct Theme { const char* name; const char* paper; const char* panel; const char* ink; const char* muted; const char* accent; const char* rule; };

Json entranceTrack(const char* property, float from, float to, int start, int end) {
    return {{"property",property},{"easing","out_cubic"},
            {"keyframes",Json::array({{{"frame",0},{"value",from}},
                                      {{"frame",start},{"value",from}},
                                      {{"frame",end},{"value",to}}})}};
}

void entrance(Json& layer, int start, float rise=22.f) {
    layer["animation"]={{"tracks",Json::array({
        entranceTrack("opacity",0.f,1.f,start,start+22),
        entranceTrack("position_y",rise,0.f,start,start+22)})}};
}

Json rect(const char* id, float x, float y, float w, float h, const char* color) {
    return {{"id", id}, {"type", "shape"}, {"enable_3d", true}, {"size", {w,h}},
            {"position", {x+w/2.f,y+h/2.f,0.f}}, {"screen_space", true},
            {"start_frame",0}, {"duration_frames",FRAMES},
            {"shape",{{"type","rect"},{"fill",Material::rgba(color)}}}};
}
Json text(const char* id, const char* value, float x, float y, float w, float h,
          float size, const char* font, const char* color) {
    Json layer={{"id",id},{"type","text"},{"text",value},{"size",{w,h}},
            {"position",{x+w/2.f,y+h/2.f,0.f}},{"enable_3d",true},{"screen_space",true},
            {"start_frame",0},{"duration_frames",FRAMES},
            {"style",{{"font",font},{"font_size",size},{"fill",color}}}};
    std::string name=id;
    int start=4;
    if(name.starts_with("edition")) start=18;
    else if(name.starts_with("headline_a")) start=26;
    else if(name.starts_with("headline_b")) start=34;
    else if(name.starts_with("dek_a")) start=44;
    else if(name.starts_with("dek_b")) start=50;
    else if(name.starts_with("read_cta")) start=58;
    else if(name.starts_with("photo_caption")) start=69;
    else if(name.starts_with("latest_label")) start=91;
    else if(name.starts_with("story_tag_")) start=106+8*(name.back()-'0');
    else if(name.starts_with("story_title_")) start=112+8*(name.back()-'0');
    else if(name.starts_with("footer")) start=145;
    entrance(layer,start);
    return layer;
}
Json build(const Theme& t) {
    Json layers=Json::array();
    layers.push_back({{"id","page_paper"},{"type","color"},{"color",Material::rgba(t.paper)},
                      {"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",FRAMES}});
    layers.push_back(rect("masthead",0,0,W,82,t.panel));
    layers.push_back(rect("masthead_rule",0,80,W,2,t.rule));
    layers.push_back(text("brand","CHRONON JOURNAL",88,22,360,42,25,bold,t.ink));
    layers.push_back(text("nav_world","WORLD",650,29,100,28,16,regular,t.muted));
    layers.push_back(text("nav_business","BUSINESS",790,29,130,28,16,regular,t.muted));
    layers.push_back(text("nav_culture","CULTURE",960,29,110,28,16,regular,t.muted));
    layers.push_back(text("nav_ideas","IDEAS",1115,29,90,28,16,regular,t.muted));
    layers.push_back(rect("subscribe_button",1648,18,184,46,t.accent));
    layers.push_back(text("subscribe","SUBSCRIBE",1664,28,152,28,15,bold,t.paper));
    layers.push_back(text("edition","THE DAILY EDITION  /  MONDAY, OCTOBER 19",92,133,790,26,16,bold,t.accent));
    layers.push_back(text("headline_a","The stories shaping",92,187,780,82,59,bold,t.ink));
    layers.push_back(text("headline_b","what comes next.",92,258,780,82,59,bold,t.ink));
    layers.push_back(text("dek_a","A closer look at the people, ideas and turning points",94,362,730,36,21,regular,t.muted));
    layers.push_back(text("dek_b","moving our world forward.",94,398,710,36,21,regular,t.muted));
    layers.push_back(rect("read_button",92,466,202,54,t.accent));
    layers.push_back(text("read_cta","EXPLORE THE ISSUE  →",105,479,178,28,14,bold,t.paper));
    Json hero={{"id","lead_photo"},{"type","image"},{"asset","assets/images/investigative_journalist_hero.jpg"},
                      {"size",{690,386}},{"position",{1362,340}},{"fit","cover"},{"screen_space",true},
                      {"start_frame",0},{"duration_frames",FRAMES}};
    entrance(hero,39,30.f);
    layers.push_back(std::move(hero));
    layers.push_back(rect("photo_caption_scrim",1018,535,690,51,"#121820"));
    layers.push_back(text("photo_caption_visible","INSIDE THE NEWSROOM  ·  6 MIN READ",1040,547,640,28,14,bold,"#FFFFFF"));
    layers.push_back(rect("latest_rule",92,650,1736,2,t.rule));
    layers.push_back(text("latest_label","LATEST",92,678,250,42,26,bold,t.ink));
    const char* titles[3]={"The new voices\nreshaping the city","Inside the race\nfor cleaner energy","Why design is\nlooking forward"};
    const char* tags[3]={"WORLD  ·  4 MIN","BUSINESS  ·  7 MIN","CULTURE  ·  5 MIN"};
    for(int i=0;i<3;++i){
        float x=92.f+i*590.f;
        layers.push_back(rect((std::string("story_rule_")+char('0'+i)).c_str(),x,742,540,1,t.rule));
        std::string tag="story_tag_"+std::to_string(i), title="story_title_"+std::to_string(i);
        layers.push_back(text(tag.c_str(),tags[i],x,763,510,28,14,bold,t.accent));
        layers.push_back(text(title.c_str(),titles[i],x,803,530,88,27,bold,t.ink));
    }
    layers.push_back(rect("footer_rule",92,1002,1736,1,t.rule));
    layers.push_back(text("footer","CHRONON JOURNAL  ·  STORIES FOR A CHANGING WORLD",92,1022,800,26,13,regular,t.muted));
    return TemplateComposition::renderPlan(std::string("web_classic_home_")+t.name,W,H,FPS,FRAMES,layers,
        chronontemplate::native::Camera::perspective({0.f,0.f,-1320.f},{0.f,0.f,0.f},50.f),{},
        {{"path",std::string("web_classic_home_")+t.name+".mp4"},{"format","mp4"},{"codec","h264"}});
}
}

int main(int argc,char** argv) try {
    if(argc!=2) throw std::runtime_error("usage: emit_web_classic_home <out-dir>");
    fs::path out=fs::absolute(argv[1]); fs::create_directories(out);
    const Theme themes[]={{"light","#F7F6F2","#FFFFFF","#202329","#727780","#B54832","#D9D9D4"},
                          {"dark","#11151A","#171C22","#F1F0EA","#A1A8B1","#E17858","#343B43"}};
    for(const auto& theme:themes){
        auto plan=build(theme);
        std::ofstream f(out/(std::string("web_classic_home_")+theme.name+".plan.json"));
        if(!f) throw std::runtime_error("cannot write plan");
        f<<plan.dump(2)<<'\n';
    }
    return 0;
} catch(const std::exception& e){ std::cerr<<e.what()<<'\n'; return 1; }
