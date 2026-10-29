#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using json=nlohmann::json;
namespace fs=std::filesystem;
namespace {
constexpr int W=1920,H=1080,FPS=30,FRAMES=90;
json rgba(std::string hex,double alpha=1.0){unsigned v=0;std::sscanf(hex.c_str(),"#%x",&v);return json::array({((v>>16)&255)/255.0,((v>>8)&255)/255.0,(v&255)/255.0,alpha});}
json key(int frame,json value){return json{{"frame",frame},{"value",std::move(value)}};}
json track(std::string property,json frames,std::string easing="out_cubic"){
    return json{{"property",std::move(property)},{"easing",std::move(easing)},{"keyframes",std::move(frames)}};
}
json animation(std::initializer_list<json> tracks){return json{{"tracks",json(tracks)}};}
json base(std::string id,std::string type,double x,double y,double w,double h,int start=0,double opacity=1.0){
    // These planar charts use the 2.5D camera so rotated axis rules work.
    // 3D-enabled layer positions use canvas-centred coordinates with +Y up.
    return json{{"id",std::move(id)},{"type",std::move(type)},{"position",json::array({x-W*.5,H*.5-y,0})},
        {"size",json::array({w,h})},{"scale",json::array({1,1,1})},{"rotation",json::array({0,0,0})},
        {"enable_3d",true},{"screen_space",false},{"start_frame",0},{"duration_frames",FRAMES},{"opacity",opacity}};
}
json rect(std::string id,double x,double y,double w,double h,std::string color,int at=0,
          bool drawBorder=false,bool dotted=false){
    auto l=base(id,"shape",x,y,w,h);json s{{"type",dotted?"dot_grid":"rect"},{"fill",dotted?rgba("#111111",.15):rgba(color)}};
    if(dotted){s["spacing"]=5.0;s["dot_radius"]=.85;}
    if(drawBorder)s["stroke"]=json{{"color","#141414"},{"width",2.0}};
    l["shape"]=std::move(s);
    if(at>0)l["animation"]=animation({track("opacity",json::array({key(0,0.0),key(at,1.0),key(FRAMES-1,1.0)}))});
    return l;
}
json textLayer(std::string id,std::string value,double x,double y,double w,double h,double size,
               std::string color="#111111",std::string align="center",int at=0,bool bold=false){
    auto l=base(id,"text",x,y,w,h);
    l["text"]=std::move(value);l["style"]={{"font",bold?"assets/fonts/Inter-Bold.ttf":"assets/fonts/Inter-SemiBold.ttf"},
        {"font_size",size},{"min_font_size",size},{"max_font_size",size},{"fit_mode","shrink_only"},
        {"fill",color},{"text_align",align}};
    if(at>0)l["animation"]=animation({track("opacity",json::array({key(0,0.0),key(at,1.0),key(FRAMES-1,1.0)}))});
    return l;
}
json lineRect(std::string id,double x0,double y0,double x1,double y1,double thickness,std::string color,int at=0){
    const double dx=x1-x0,dy=y1-y0,len=std::hypot(dx,dy),angle=std::atan2(dy,dx)*180.0/3.141592653589793;
    auto l=rect(std::move(id),(x0+x1)*.5,(y0+y1)*.5,len,thickness,color,at);
    l["rotation"]=json::array({0,0,-angle});return l;
}
json planBase(std::string id){
    return json{{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",id},
        {"canvas",{{"width",W},{"height",H},{"fps_num",FPS},{"fps_den",1},{"duration_frames",FRAMES}}},
        {"camera",{{"type","perspective"},{"position",json::array({0,0,-1000})},{"rotation_deg",json::array({0,0,0})},{"fov_deg",56.738092586557165},{"zoom",1000.0}}},
        {"layers",json::array({json{{"id","white-background"},{"type","color"},{"size",json::array({W,H})},{"color",json::array({1,1,1,1})},{"start_frame",0},{"duration_frames",FRAMES}}})},
        {"output",{{"path",id+".mp4"},{"format","mp4"},{"codec","h264"}}}};
}
void addBarGrowth(json& l,int start,int finish,double baseY,double height){
    l["animation"]["tracks"]=json::array({
        track("scale_y",json::array({key(0,.001),key(start,.001),key(finish,1.0),key(FRAMES-1,1.0)})),
        track("position_y",json::array({key(0,-height*.5),key(start,-height*.5),key(finish,0.0),key(FRAMES-1,0.0)}))});
}
json economics(){
    json p=planBase("oracle_deal_economics");auto& l=p["layers"];
    l.push_back(textLayer("title","Oracle-OpenAI Deal Economics",960,108,1500,92,62,"#080808","center",4,true));
    constexpr double xa=360,top=220,baseY=835,scale=7.65;
    l.push_back(lineRect("y-axis",xa,top,xa,baseY,3,"#101010"));l.push_back(lineRect("x-axis",xa,baseY,1530,baseY,3,"#101010"));
    for(int v=20;v<=80;v+=20){double y=baseY-v*scale;l.push_back(lineRect("ytick-"+std::to_string(v),xa-8,y,xa,y,3,"#111111"));l.push_back(textLayer("ylabel-"+std::to_string(v),std::to_string(v)+"B",xa-18,y,72,44,31,"#111111","right"));}
    struct B{const char* value;const char* color;double x,w,v;const char* a;const char* b;int st;};
    const B bars[]={{"$60B","#E65447",561,190,60,"OpenAI Annual","Commitment",11},{"$12B","#33C977",945,190,12,"OpenAI Annual","Revenue",24},{"$21.5B","#258EF0",1328,190,21.5,"Oracle Annual","Operating Cash Flow",37}};
    for(int i=0;i<3;++i){const auto& b=bars[i];const double bh=b.v*scale,cy=baseY-bh*.5;auto bar=rect("bar-"+std::to_string(i),b.x,cy,b.w,bh,b.color,0,true);addBarGrowth(bar,b.st,b.st+32,baseY,bh);l.push_back(bar);
        auto dots=rect("bar-halftone-"+std::to_string(i),b.x,cy,b.w,bh,"#111111",0,false,true);addBarGrowth(dots,b.st,b.st+32,baseY,bh);l.push_back(dots);
        auto value=textLayer("bar-value-"+std::to_string(i),b.value,b.x,cy-bh*.5-30,b.w+120,52,38,"#050505","center",b.st+27,true);l.push_back(value);
        l.push_back(textLayer("bar-category-a-"+std::to_string(i),b.a,b.x,baseY+49,355,35,27,"#111111","center",b.st+12));
        l.push_back(textLayer("bar-category-b-"+std::to_string(i),b.b,b.x,baseY+82,355,35,27,"#111111","center",b.st+14));}
    return p;
}
struct Point{double x,y;};
std::vector<Point> jCurvePoints(){const Point k[]={{0,0},{.5,-100},{1,-70},{2,-40},{3,-10},{4,20},{4.85,40}};std::vector<Point> out;out.reserve(121);
    for(int i=0;i<=120;++i){double x=4.85*i/120.0;int s=0;while(s<5&&x>k[s+1].x)++s;const auto a=k[s],b=k[s+1],p0=k[std::max(0,s-1)],p3=k[std::min(6,s+2)];double u=std::clamp((x-a.x)/(b.x-a.x),0.0,1.0),dx=b.x-a.x;
        double m1=(b.y-p0.y)/(b.x-p0.x),m2=(p3.y-a.y)/(p3.x-a.x);double y=(2*u*u*u-3*u*u+1)*a.y+(u*u*u-2*u*u+u)*dx*m1+(-2*u*u*u+3*u*u)*b.y+(u*u*u-u*u)*dx*m2;out.push_back({x,y});}
    return out;}
json pathCommand(std::string type,double x=0,double y=0){json j{{"type",std::move(type)}};if(j["type"]!="close")j["point"]=json::array({x,y});return j;}
json areaPath(std::string id,const std::vector<Point>& pts,bool aboveBase,std::string fill,int at){
    std::vector<Point> use;const double baseline=540-453;
    use.push_back({pts.front().x-960,baseline});
    for(const auto& q:pts){const double sx=510+q.x*160,sy=453-q.y*3.36; if((aboveBase&&sy<=453)||(!aboveBase&&sy>=453))use.push_back({sx-960,540-sy});}
    use.push_back({use.back().x,baseline});use.push_back({pts.front().x-960,baseline});
    auto l=base(std::move(id),"shape",960,540,W,H);json cmds=json::array();cmds.push_back(pathCommand("move_to",use[0].x,use[0].y));for(size_t i=1;i<use.size();++i)cmds.push_back(pathCommand("line_to",use[i].x,use[i].y));cmds.push_back(pathCommand("close"));
    l["shape"]={{"type","path"},{"path",std::move(cmds)},{"fill",rgba(fill,.18)}};
    l["animation"]=animation({track("opacity",json::array({key(0,0.0),key(at,.18),key(FRAMES-1,.18)}))});return l;
}
json jcurve(){json p=planBase("oracle_j_curve_effect");auto& l=p["layers"];
    l.push_back(textLayer("title","The J-Curve Effect",960,73,1000,70,53,"#090909","center",3,true));
    l.push_back(rect("legend-swatch",762,146,25,25,"#33C879",4));l.push_back(textLayer("legend","$30 Annual Rent",921,147,310,54,34,"#111111","left",5));
    constexpr double x0=412,x1=1537,y0=453,yt=121,yb=905;
    l.push_back(lineRect("y-axis",x0,yt,x0,yb,2.4,"#111111"));l.push_back(lineRect("x-axis",x0,y0,x1,y0,2.4,"#111111"));
    for(int v=-120;v<=80;v+=20){double y=y0-v*3.36;l.push_back(lineRect("ytick-"+std::to_string(v),x0-8,y,x0,y,2.4,"#111111"));l.push_back(textLayer("ylabel-"+std::to_string(v),std::to_string(v),x0-34,y,65,38,29,"#111111","right"));}
    for(int y=0;y<=6;++y){double x=510+y*160;l.push_back(lineRect("xtick-"+std::to_string(y),x,y0,x,y0+9,2.4,"#111111"));l.push_back(textLayer("xlabel-"+std::to_string(y),"Year "+std::to_string(y),x,yb+34,145,42,28,"#111111","center"));}
    l.push_back(textLayer("axis-title","Cumulative Net Cash Flow ($)",260,513,440,45,29,"#111111","center"));
    auto pts=jCurvePoints();l.push_back(areaPath("loss-area",pts,false,"#EA493A",66));l.push_back(areaPath("gain-area",pts,true,"#38C879",70));
    auto drawCurve=[&](std::string id,size_t begin,size_t end,std::string color,int start,int finish){
        json points=json::array();for(size_t i=begin;i<=end;++i){const auto q=pts[i];const double sx=510+q.x*160,sy=453-q.y*3.36;points.push_back(json::array({sx-960,540-sy}));}
        auto path=base(id,"shape",960,540,W,H);path["shape"]={{"type","monotone_line"},{"data_points",std::move(points)},{"stroke",{{"color",color},{"width",7.0},{"cap","round"},{"join","round"},{"dash_array",json::array({2200.0,2200.0})},{"dash_offset",2200.0}}}};
        path["animation"]=animation({track("stroke_dash_offset",json::array({key(0,2200.0),key(start,2200.0),key(finish,0.0),key(FRAMES-1,0.0)}))});l.push_back(std::move(path));};
    size_t cross=0;while(cross+1<pts.size()&&pts[cross+1].y<=0)++cross;
    drawCurve("loss-curve",0,cross,"#E34232",8,56);drawCurve("gain-curve",cross,pts.size()-1,"#31BD72",42,69);
    struct M{int year;double value;const char* label;const char* color;double dy;};const M marks[]={{0,-100,"-$100","#E34B3C",37},{1,-70,"-$70","#E34B3C",43},{2,-40,"-$40","#E34B3C",43},{3,-10,"-$10","#E34B3C",42},{4,20,"$20","#32C879",-52}};
    for(int i=0;i<5;++i){const auto&m=marks[i];double x=510+m.year*160,y=y0-m.value*3.36,show=18+i*10;
        auto dot=base("marker-"+std::to_string(i),"shape",x,y,18,18);dot["shape"]={{"type","ellipse"},{"fill",rgba("#0D0D0D")}};dot["animation"]=animation({track("opacity",json::array({key(0,0.0),key(int(show),0.0),key(int(show+7),1.0),key(FRAMES-1,1.0)}))});l.push_back(dot);
        double labelY=m.dy<0?y+m.dy:y+m.dy+24;auto box=base("callout-box-"+std::to_string(i),"shape",x,labelY,118,46);box["shape"]={{"type","rounded_rect"},{"radius",7},{"fill",rgba(m.color)}};box["animation"]=animation({track("opacity",json::array({key(0,0.0),key(int(show),0.0),key(int(show+7),1.0),key(FRAMES-1,1.0)}))});l.push_back(box);
        l.push_back(textLayer("callout-label-"+std::to_string(i),m.label,x,labelY,118,42,27,"#FFFFFF","center",int(show+7),true));}
    return p;}
json profits(){json p=planBase("oracle_profits_comparison");auto& l=p["layers"];
    l.push_back(textLayer("title","Profits",265,458,260,55,38,"#111111","left",3,true));
    const double left=267,greenY=509,h=64,greenW=1361;
    l.push_back(textLayer("oracle","ORACLE",198,510,138,40,26,"#CB3427","center",5));
    auto bar=rect("oracle-profit-bar",left+greenW*.5,greenY,greenW,h,"#3DC77A",0,true);bar["animation"]=animation({track("scale_x",json::array({key(0,.001),key(10,.001),key(48,1.0),key(FRAMES-1,1.0)})),track("position_x",json::array({key(0,-greenW*.5),key(10,-greenW*.5),key(48,0.0),key(FRAMES-1,0.0)}))});l.push_back(bar);
    auto dots=rect("profit-halftone",left+greenW*.5,greenY,greenW,h,"#111111",0,false,true);dots["animation"]=bar["animation"];l.push_back(dots);
    auto value=textLayer("profit-value","$27 B",left+greenW-86,510,210,61,58,"#050505","right",45,true);l.push_back(value);
    const double redW=310,redY=622;auto red=rect("openai-profit-bar",left+redW*.5,redY,redW,h,"#EF786A",0,true);red["animation"]=animation({track("scale_x",json::array({key(0,.001),key(29,.001),key(60,1.0),key(FRAMES-1,1.0)})),track("position_x",json::array({key(0,-redW*.5),key(29,-redW*.5),key(60,0.0),key(FRAMES-1,0.0)}))});l.push_back(red);
    auto rd=rect("openai-profit-halftone",left+redW*.5,redY,redW,h,"#111111",0,false,true);rd["animation"]=red["animation"];l.push_back(rd);
    l.push_back(textLayer("small-profit-value","~$5.4 B",left+redW-120,redY,250,60,56,"#090909","right",57,true));
    auto note=base("source-note","shape",1600,1031,420,45);note["shape"]={{"type","rounded_rect"},{"radius",9},{"fill",rgba("#777777")}};l.push_back(note);
    l.push_back(textLayer("source-note-text","*Figures simplified and rounded for explanation.",1600,1030,400,39,17,"#FFFFFF","center"));return p;}
void write(json plan,const fs::path& dir){std::string id=plan["job_id"].get<std::string>();fs::create_directories(dir);std::ofstream f(dir/(id+".plan.json"),std::ios::binary|std::ios::trunc);if(!f||!(f<<plan.dump(2)<<'\n'))throw std::runtime_error("failed writing plan "+id);std::cout<<"Wrote native Chronon3D RenderPlan: "<<(dir/(id+".plan.json"))<<'\n';}
}
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("usage: emit_oracle_chronon_plans <plans-dir>");fs::path dir=fs::absolute(argv[1]);write(economics(),dir);write(jcurve(),dir);write(profits(),dir);return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
