#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
namespace {
constexpr int W=1920,H=1080,FPS=30,FRAMES=240;
constexpr const char* BOLD="out/web_article_fold/fonts/Inter-Bold.ttf";
double estimate_width(const std::string& text,double size){
  double units=0.0;
  for(unsigned char c:text){
    if(c==' ') units+=0.28;
    else if(c=='i'||c=='l'||c=='I'||c=='!'||c=='.'||c==','||c==':') units+=0.29;
    else if(c=='m'||c=='w'||c=='M'||c=='W') units+=0.78;
    else if(c>='A'&&c<='Z') units+=0.64;
    else units+=0.52;
  }
  return units*size;
}
Json key(int frame,Json value){return Json{{"frame",frame},{"value",std::move(value)}};}
Json text_layer(std::string id,std::string text,double left,double y,double size,
                const char* font,const char* fill){
  const double width=estimate_width(text,size);
  Json layer={{"id",std::move(id)},{"type","text"},{"text",std::move(text)},
    {"size",{width*1.32+48.0,static_cast<double>(size*1.65)}},
    {"position",{left+width*.5,H-y}},{"start_frame",0},{"duration_frames",FRAMES},
    {"style",{{"font",font},{"font_size",size},{"fill",fill},{"fit_mode","none"}}}};
  return layer;
}
Json fold_animators(const std::string& text,int offset,int stagger,int fold_frames){
  const int n=static_cast<int>(text.size());
  Json animators=Json::array();
  for(int i=0;i<n;++i){
    const int begin=offset+i*stagger;
    const double lo=100.0*i/n, hi=100.0*(i+1)/n;
    Json selector={{"id","glyph_"+std::to_string(i)},{"unit","character"},
      {"shape","square"},{"order","forward"},{"combine","replace"},
      {"exclude_spaces",false},
      {"start",{{"keyframes",Json::array({key(0,lo)})},{"easing","linear"}}},
      {"end",{{"keyframes",Json::array({key(0,hi)})},{"easing","linear"}}}};
    Json rot=Json::array(),pos=Json::array(),opacity=Json::array();
    auto add_sample=[&](int frame,double p){
      const double eased=1.0-std::pow(1.0-p,3.0);
      rot.push_back(key(frame,Json::array({82.0*(1.0-eased),0.0,0.0})));
      pos.push_back(key(frame,36.0*(1.0-eased)));
      opacity.push_back(key(frame,eased));
    };
    if(begin>0) add_sample(0,0.0);
    add_sample(begin,0.0);
    for(int f=1;f<=fold_frames;++f) add_sample(begin+f,static_cast<double>(f)/fold_frames);
    Json properties=Json::array({
      Json{{"property","rotation"},{"easing","linear"},{"keyframes",std::move(rot)}},
      Json{{"property","position_y"},{"easing","linear"},{"keyframes",std::move(pos)}},
      Json{{"property","opacity"},{"easing","linear"},{"keyframes",std::move(opacity)}}});
    animators.push_back({{"id","fold_glyph_"+std::to_string(i)},
      {"selectors",Json::array({std::move(selector)})},{"properties",std::move(properties)}});
  }
  return animators;
}
Json image_layer(std::string id,std::string asset,int x,int y,int w,int h){
  return Json{{"id",std::move(id)},{"type","image"},{"asset",std::move(asset)},
    {"size",{w,h}},{"position",{x,y}},{"fit","cover"},
    {"start_frame",0},{"duration_frames",FRAMES}};
}
}
int main(int argc,char**argv) try {
  if(argc!=2) throw std::runtime_error("usage: emit_web_article_fold <plan.json>");
  const fs::path out=fs::absolute(argv[1]);
  Json layers=Json::array();
  const fs::path image=out.parent_path()/"static_page.png";
  layers.push_back(image_layer("article_page_and_blurred_copy",fs::relative(image,fs::current_path()).string(),0,0,W,H));

  const std::string headline1="Sources: Jonathan Kuminga";
  const std::string headline2="demanding trade away from Warriors";
  auto h1=text_layer("headline_line_1",headline1,453,153,52,BOLD,"#202124");
  h1["enable_3d"]=true; h1["text_animators"]=fold_animators(headline1,0,2,9);
  layers.push_back(std::move(h1));
  auto h2=text_layer("headline_line_2",headline2,453,216,52,BOLD,"#202124");
  h2["enable_3d"]=true; h2["text_animators"]=fold_animators(headline2,42,2,9);
  layers.push_back(std::move(h2));


  Json plan={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","web_article_fold_title_v1"},
    {"canvas",{{"width",W},{"height",H},{"fps_num",FPS},{"fps_den",1},{"duration_frames",FRAMES}}},
    {"layers",std::move(layers)},
    {"output",{{"path","Web_Article_Fold_Title.mp4"},{"format","mp4"},{"codec","h264"}}}};
  fs::create_directories(out.parent_path());
  std::ofstream file(out); if(!file) throw std::runtime_error("cannot write plan: "+out.string());
  file<<plan.dump(2)<<'\n';
  std::cout<<"Wrote "<<out<<" (article title, two-line per-character fold reveal, 8 s at 30 fps)\n";
  return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
