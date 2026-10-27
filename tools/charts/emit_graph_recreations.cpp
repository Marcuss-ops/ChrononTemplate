#include "chronontemplate/core/RenderPlanContentHost.hpp"
#include "chronontemplate/core/TemplateScene.hpp"
#include "chrononmotion/motion/RenderPlanEmission.hpp"
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using namespace chronontemplate;
using namespace chrononmotion;
using namespace chrononmotion::motion;

namespace {
constexpr int kFrames = 120;
constexpr float kFps = 30.f;
constexpr float kW = 1920.f;
constexpr float kH = 1080.f;

struct Assets {
    std::uint64_t next{1};
    std::unordered_map<ContentId, std::string> fingerprints;
    ContentHandle make(std::string id, ContentKind kind, Vector2 size) {
        ContentHandle h;
        h.id = std::move(id); h.wireId = next++; h.kind = kind;
        h.metrics.naturalSize = size; h.metrics.anchor = {0.5f, 0.5f};
        h.metrics.fingerprint = "chronontemplate-graphs-reference-v1:" + h.id;
        fingerprints.emplace(h.id, h.metrics.fingerprint); return h;
    }
    ContentHandle text(const TextRequest& r) {
        return make("text/" + r.text, ContentKind::Text,
                    {r.fontSize * (static_cast<float>(r.text.size()) * .68f + .7f), r.fontSize * 1.4f});
    }
    ContentHandle image(const ImageRequest& r) { return make(r.path, ContentKind::Image, {kW, kH}); }
    ContentHandle video(const VideoRequest& r) { return make(r.path, ContentKind::Video, {kW, kH}); }
    ContentHandle shape(const ShapeRequest& r) { return make("shape/" + r.name, ContentKind::Image, r.size); }
    std::string fingerprint(const ContentId& id) const {
        auto i=fingerprints.find(id); return i==fingerprints.end()?std::string{}:i->second;
    }
};
struct SceneContext {
    RenderPlanContentHost host;
    TemplateScene scene;
    int serial{0};
    SceneContext(const std::string& id, Assets& a) : host({
        .createText=[&](const TextRequest& r){return a.text(r);},
        .createImage=[&](const ImageRequest& r){return a.image(r);},
        .createVideo=[&](const VideoRequest& r){return a.video(r);},
        .createShape=[&](const ShapeRequest& r){return a.shape(r);},
        .currentFingerprint=[&](const ContentId& id){return a.fingerprint(id);}}),
        scene(id,kFps,host,kW,kH) {
        scene.camera().setFov(55.f);
    }
    LayerHandle& rect(float x,float y,float w,float h,const std::string& color,
                      const std::string& name,int at=0,float radius=0.f) {
        ShapeSpec s; s.size=Vector2(w,h); s.fillColor=color;
        s.name="graphs_"+std::to_string(serial++)+"_"+name; s.cornerRadius=radius;
        auto& l=scene.shape(s); l.position(x,kH-y,0.f).alive(0,kFrames-1);
        if(at>0) l.animateOpacity(at,12,0.f,1.f,Easing::easeOut());
        return l;
    }
    LayerHandle& circle(float x,float y,float diameter,const std::string& color,
                        const std::string& name,int at=0) {
        ShapeSpec s; s.size=Vector2(diameter,diameter); s.fillColor=color;
        s.name="graphs_"+std::to_string(serial++)+"_"+name; s.geometry=ShapeGeometry::Ellipse;
        auto& l=scene.shape(s); l.position(x,kH-y,0.f).alive(0,kFrames-1);
        if(at>0) l.animateOpacity(at,12,0.f,1.f,Easing::easeOut());
        return l;
    }
    LayerHandle& text(const std::string& value,float x,float y,float size,const std::string& color,
                      const std::string& name,int at=0,const std::string& font="assets/fonts/Inter-SemiBold.ttf") {
        TextSpec s; s.text=value; s.font=font; s.fontSize=size; s.color=color;
        s.name="graphs_"+std::to_string(serial++)+"_"+name;
        auto& l=scene.text(s); l.position(x,kH-y,0.f).alive(0,kFrames-1);
        if(at>0) l.animateOpacity(at,12,0.f,1.f,Easing::easeOut());
        return l;
    }
    void line(float x0,float y0,float x1,float y1,float thick,const std::string& color,
              const std::string& name,int at=0) {
        const float dx=x1-x0,dy=y1-y0,len=std::hypot(dx,dy),angle=std::atan2(dy,dx);
        auto& l=rect((x0+x1)*.5f,(y0+y1)*.5f,std::max(1.f,len),thick,color,name,at,thick*.5f);
        l.layer().tracks.rotation.add(frameToTime(0,kFps),Vector3(0.f,0.f,-angle),Easing::linear());
    }
    void background(const std::string& color) { rect(kW*.5f,kH*.5f,kW*1.12f,kH*1.12f,color,"background"); }
};

void writePlan(SceneContext& c,const std::string& name,const std::filesystem::path& dir) {
    if(!c.scene.validate().empty()) throw std::runtime_error(name+": "+c.scene.validate().front());
    auto plan=lowerToRenderPlan(c.scene,c.host,name,name+".mp4");
    auto doc=nlohmann::json::parse(renderPlanToJson(plan));
    doc.erase("camera_animation"); doc["output"]["format"]="mp4"; doc["output"]["codec"]="h264";
    std::ofstream f(dir/(name+".plan.json"),std::ios::binary|std::ios::trunc);
    if(!f || !(f<<doc.dump(2)<<'\n')) throw std::runtime_error("cannot write plan: "+name);
}
void header(SceneContext& c,const std::string& tag,const std::string& title,const std::string& subtitle,
            const std::string& ink,const std::string& accent) {
    c.rect(220.f,90.f,180.f,34.f,accent,"eyebrow-bg",0,3.f);
    c.text(tag,220.f,90.f,20.f,"#FFFFFF","eyebrow",4);
    c.text(title,960.f,155.f,53.f,ink,"title",8);
    if(!subtitle.empty()) c.text(subtitle,960.f,214.f,28.f,"#68717C","subtitle",14);
}
void series(SceneContext& c,const std::vector<double>& values,const std::vector<std::string>& labels,
            double yMin,double yMax,float left,float right,float top,float bottom,
            const std::string& lineColor,const std::string& gridColor,const std::string& ink,
            const std::vector<std::pair<double,std::string>>& xTicks,const std::string& unit,
            bool dottedFinal=false,bool endpointMarkers=true) {
    if(labels.size()!=values.size() || labels.size()<2) throw std::invalid_argument("series requires matching year labels");
    const double xMin=std::stod(labels.front()), xMax=std::stod(labels.back());
    const auto xAt=[&](double year){return left+(right-left)*static_cast<float>((year-xMin)/(xMax-xMin));};
    for(int i=0;i<=2;++i){
        const double val=yMin+(yMax-yMin)*i/2.0;
        const float y=bottom-(bottom-top)*i/2.f;
        c.line(left,y,right,y,1.5f,gridColor,"series-grid-"+std::to_string(i));
        c.text(std::to_string(static_cast<int>(std::round(val)))+(unit.empty()?"":" "+unit),left-55.f,y-10.f,22.f,ink,"series-y-"+std::to_string(i));
    }
    for(const auto& t:xTicks){
        if(t.first<xMin||t.first>xMax) continue;
        const float x=xAt(t.first);
        c.text(t.second,x,bottom+33.f,21.f,ink,"series-x-"+t.second);
    }
    std::vector<std::pair<float,float>> pts;
    for(std::size_t i=0;i<values.size();++i){
        const float x=xAt(std::stod(labels[i]));
        const float y=bottom-(bottom-top)*static_cast<float>((values[i]-yMin)/(yMax-yMin));
        pts.emplace_back(x,y);
    }
    for(std::size_t i=1;i<pts.size();++i){
        const auto [x0,y0]=pts[i-1]; const auto [x1,y1]=pts[i];
        if(dottedFinal && i+1==pts.size()){
            const int n=4;
            for(int d=0;d<n;++d){float t=(d+.5f)/n;c.circle(x0+(x1-x0)*t,y0+(y1-y0)*t,9.f,lineColor,"forecast-dot-"+std::to_string(d),80+static_cast<int>(d));}
        } else c.line(x0,y0,x1,y1,7.f,lineColor,"series-line-"+std::to_string(i),20+static_cast<int>(i)*3);
    }
    if(endpointMarkers && !pts.empty()){
        const auto [x0,y0]=pts.front(); c.circle(x0,y0,13.f,lineColor,"series-start-point",18);
        const auto [x1,y1]=pts.back(); c.circle(x1,y1,22.f,lineColor,"series-end-point",88);
    }
}
void unemployment(SceneContext& c){
    c.background("#F7F7F3"); header(c,"OCCUPAZIONE","Auto tedesca: mai così pochi occupati",
        "Addetti nell’industria automobilistica in Germania, migliaia","#171717","#F3394B");
    const std::vector<double> v={730,750,702,742,775,806,834,810,775,732,691.5};
    const std::vector<std::string> labs={"2006","2008","2010","2012","2014","2016","2018","2020","2022","2025","2026"};
    series(c,v,labs,650,850,195,1425,390,820,"#F13B4B","#D9DAD7","#333333",
           {{2006,"2006"},{2010,"2010"},{2014,"2014"},{2018,"2018"},{2022,"2022"},{2025,"2025"},{2026,"2026"}},"",true);
    c.circle(933.f,424.f,18.f,"#F13B4B","peak-dot",50);
    c.text("Picco 2018: 834.000",1080.f,398.f,26.f,"#171717","peak-label",56);
    c.text("2025: 732.000",1200.f,700.f,22.f,"#6D6D6D","2025-label",65);
    c.rect(335.f,410.f,300.f,142.f,"#171717","job-loss-callout",42,2.f);
    c.text("−144.000",335.f,385.f,44.f,"#FFFFFF","job-loss-number",48,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("posti persi nella manifattura",335.f,440.f,21.f,"#FFFFFF","job-loss-line1",54);
    c.text("giugno 2025 → giugno 2026",335.f,470.f,21.f,"#FFFFFF","job-loss-line2",58);
    c.rect(1605.f,670.f,310.f,105.f,"#F13B4B","latest-number-bg",70);
    c.text("691.500",1605.f,644.f,48.f,"#FFFFFF","latest-number",74,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("2026 · dato puntuale",1605.f,694.f,18.f,"#FFFFFF","latest-label",78);
    c.text("Fonte: Destatis · medie annuali 2006–2025; giugno 2026 puntuale",960.f,1008.f,20.f,"#676767","source-note",100);
}
void chinaGdp(SceneContext& c){
    c.background("#F2E9E7");
    c.text("China GDP Per Capita Growth (Current LCU)",960.f,78.f,44.f,"#101010","title",6,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("Source: World Bank",960.f,126.f,27.f,"#494343","source",12);
    std::vector<double> v={200,245,290,285,320,370,600,800,980};
    std::vector<std::string> years={"1980","1985","1988","1990","2000","2005","2008","2015","2023"};
    series(c,v,years,0,1000,210,1710,245,825,"#25383C","#ABA3A1","#373232",
           {{1980,"1980"},{1985,"1985"},{1990,"1990"},{2000,"2000"},{2008,"2008"},{2015,"2015"},{2023,"2023"}},"",false,false);
    c.text("Valori di curva ricostruiti visivamente dalla schermata",960.f,1002.f,19.f,"#726A68","trace-note",100);
}
void franceBars(SceneContext& c){
    c.background("#FAFAF8");
    c.text("Spesa pubblica · confronto percentuale",960.f,105.f,45.f,"#151515","title",6,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("Quote riportate nel grafico di riferimento",960.f,160.f,25.f,"#666666","subtitle",12);
    const float left=360.f,right=1615.f,top=260.f,bottom=820.f;
    for(int tick=0;tick<=5;++tick){
        float y=bottom-(bottom-top)*tick/5.f;
        c.line(left,y,right,y,2.f,"#D5D5D2","grid-"+std::to_string(tick));
        c.text(std::to_string(tick*10)+"%",left-68.f,y-2.f,25.f,"#3A3A3A","tick-"+std::to_string(tick));
    }
    const std::vector<std::string> names={"United States","Germany","Scandinavian welfare states"};
    const std::vector<double> vals={38,48,50};
    const float centers[]={560.f,990.f,1420.f};
    for(int i=0;i<3;++i){
        float h=(bottom-top)*static_cast<float>(vals[i]/50.0);
        c.rect(centers[i],bottom-h*.5f,108.f,h,"#E9151C","bar-"+std::to_string(i),24+i*16,2.f);
        c.text(std::to_string(static_cast<int>(vals[i]))+"%",centers[i],bottom-h-36.f,42.f,"#D30F17","value-"+std::to_string(i),40+i*16,"assets/fonts/InterDisplay-Bold.ttf");
        c.text(names[i],centers[i],bottom+42.f,i==2?21.f:24.f,"#161616","category-"+std::to_string(i),56+i*14);
    }
}
void saudiProjects(SceneContext& c){
    c.background("#F5F2EB");
    c.text("SAUDI VISION 2030 · MEGAPROGETTI",960.f,70.f,43.f,"#171717","title",5,"assets/fonts/InterDisplay-Bold.ttf");
    // A portrait medallion and central figure are intentionally vector placeholders,
    // since the screenshot's source portrait and project photographs are not local assets.
    c.circle(960.f,220.f,150.f,"#182536","leader-medallion",12);
    c.circle(960.f,197.f,49.f,"#D5B18C","leader-head",20);
    c.rect(960.f,263.f,88.f,54.f,"#E5E7E8","leader-robe",26,18.f);
    c.rect(960.f,330.f,410.f,52.f,"#121B2A","leader-name-bg",30,9.f);
    c.text("Mohammed bin Salman",960.f,330.f,28.f,"#FFFFFF","leader-name",36);
    c.line(960.f,356.f,960.f,408.f,4.f,"#293342","leader-stem",40);
    c.line(180.f,408.f,1740.f,408.f,4.f,"#293342","project-branch",42);
    const std::vector<std::string> names={"TROJENA","AQUELLUM","THE MUKAAB","QIDDIYA CITY","OXAGON","THE RED SEA PROJECT"};
    const std::vector<std::string> colors={"#637E91","#526A74","#C5A256","#8B9B7C","#293D56","#5C9C9A"};
    for(int i=0;i<6;++i){
        const float x=180.f+312.f*i;
        c.line(x,408.f,x,462.f,3.f,"#293342","project-drop-"+std::to_string(i),48+i*5);
        c.rect(x,558.f,272.f,194.f,colors[i],"project-image-"+std::to_string(i),48+i*5,8.f);
        if(i==0) c.line(x-72.f,595.f,x+68.f,520.f,12.f,"#AEBBC0","trojena-ridge",57);
        else if(i==1) c.rect(x-30.f,554.f,48.f,116.f,"#C6AD84","aquellum-cliff",57,4.f);
        else if(i==2) c.rect(x,555.f,94.f,94.f,"#D9C58F","mukaab-cube",57,2.f);
        else if(i==3) c.circle(x,555.f,92.f,"#AFC1A1","qiddiya-loop",57);
        else if(i==4) c.rect(x,552.f,132.f,42.f,"#71869D","oxagon-skyline",57,3.f);
        else c.circle(x,555.f,96.f,"#91C5B7","red-sea-island",57);
        c.text(names[i],x,681.f,i==5?19.f:23.f,"#111923","project-label-"+std::to_string(i),68+i*5);
    }
    c.line(180.f,785.f,1740.f,785.f,4.f,"#293342","lower-branch",85);
    c.line(960.f,785.f,960.f,833.f,4.f,"#293342","vision-stem",88);
    c.circle(960.f,916.f,174.f,"#CF1640","vision-seal",92);
    c.text("VISION",960.f,880.f,24.f,"#FFFFFF","vision-label",96);
    c.text("2030",960.f,925.f,58.f,"#FFFFFF","vision-year",100,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("PROJECT PORTFOLIO",960.f,1015.f,20.f,"#70706B","portfolio-note",105);
}
void patriotInventory(SceneContext& c){
    c.background("#111111");
    c.text("PATRIOT INTERCEPTOR INVENTORY",960.f,85.f,45.f,"#F2F2F2","title",5,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("Data: CSIS (US), JINSA (Gulf states)",960.f,139.f,28.f,"#D0D0D0","source",12);
    const float left=570.f,right=1660.f,top=330.f,bottom=795.f;
    for(int t=0;t<=5;++t){
        const float x=left+(right-left)*t/5.f;
        c.line(x,top-38.f,x,bottom,1.5f,t==0?"#E4E4E4":"#454545","grid-"+std::to_string(t));
        if(t>0)c.text(std::to_string(t*500),x,bottom+42.f,22.f,"#D5D5D5","tick-"+std::to_string(t));
    }
    const std::vector<std::string> names={"USA","Saudi Arabia","Qatar","UAE","Kuwait","Bahrain"};
    const std::vector<double> values={2330,1800,1000,680,500,100};
    const std::vector<std::string> flags={"US","SA","QA","AE","KW","BH"};
    for(int i=0;i<6;++i){
        const float y=354.f+i*79.f;
        c.text(names[i],390.f,y,31.f,"#F1F1F1","country-"+std::to_string(i),16+i*9);
        c.rect(500.f,y,53.f,34.f,i==0?"#2B3036":"#292D31","flag-"+std::to_string(i),18+i*9,3.f);
        c.text(flags[i],500.f,y,16.f,"#DDDDDD","flag-code-"+std::to_string(i),22+i*9);
        const float w=(right-left)*static_cast<float>(values[i]/2500.0);
        if(i==0){
            const float w1=(right-left)*.31f, w2=(right-left)*.035f, w3=std::max(1.f,w-w1-w2);
            c.rect(left+w1*.5f,y,w1,30.f,"#777777","usa-segment-a",30);
            c.rect(left+w1+w2*.5f,y,w2,30.f,"#A0A0A0","usa-segment-b",46);
            c.rect(left+w1+w2+w3*.5f,y,w3,30.f,"#585858","usa-segment-c",60);
        } else c.rect(left+w*.5f,y,w,30.f,"#747474","inventory-bar-"+std::to_string(i),28+i*11);
    }
    c.text("AS OF JULY 27, 2026",left+185.f,275.f,18.f,"#A5A5A5","current-date",22);
    c.text("PRE-IRAN WAR LEVEL",right-115.f,275.f,18.f,"#A5A5A5","prewar-label",22);
    c.line(left,bottom,right,bottom,2.f,"#E4E4E4","axis",0);
    c.text("Inventory scale · reconstructed from bar lengths in reference",960.f,1004.f,19.f,"#A5A5A5","reconstruction-note",105);
}
void appleServices(SceneContext& c){
    c.background("#FFFFFF");
    c.text("Apple’s Transformation Under Tim Cook",960.f,80.f,48.f,"#111111","title",6,"assets/fonts/InterDisplay-Bold.ttf");
    c.text("Annual Revenue",270.f,190.f,31.f,"#111111","metric-heading",14);
    c.line(250.f,230.f,1670.f,230.f,3.f,"#111111","frame-top",18);
    c.line(250.f,820.f,1670.f,820.f,3.f,"#111111","frame-bottom",18);
    c.line(250.f,230.f,250.f,820.f,3.f,"#111111","frame-left",18);
    c.line(1670.f,230.f,1670.f,820.f,3.f,"#111111","frame-right",18);
    c.text("Apple Services FY2025",520.f,390.f,37.f,"#111111","bar-label",25);
    c.rect(790.f,535.f,1145.f,152.f,"#111111","revenue-bar",42,2.f);
    c.text("$103.73B",1210.f,535.f,44.f,"#FFFFFF","revenue-value",62,"assets/fonts/InterDisplay-Bold.ttf");
    // Minimal vector stand-in for the figure shown in the reference screenshot.
    c.circle(175.f,310.f,80.f,"#D6B89E","figure-head",18);
    c.rect(175.f,470.f,118.f,210.f,"#151515","figure-torso",25,34.f);
    c.line(128.f,410.f,72.f,600.f,38.f,"#151515","figure-arm-left",34);
    c.line(220.f,410.f,273.f,587.f,38.f,"#151515","figure-arm-right",38);
    c.line(152.f,570.f,122.f,728.f,47.f,"#151515","figure-leg-left",44);
    c.line(196.f,570.f,225.f,728.f,47.f,"#151515","figure-leg-right",48);
    c.rect(112.f,746.f,82.f,19.f,"#222222","figure-shoe-left",52,8.f);
    c.rect(240.f,746.f,82.f,19.f,"#222222","figure-shoe-right",56,8.f);
    c.text("Source · Investopedia · Apple Newsroom",300.f,1000.f,21.f,"#222222","source-note",100,"assets/fonts/Inter-SemiBold.ttf");
}

struct Record{int id;std::string name,title,source,method;};
} // namespace

int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"usage: chronontemplate_emit_graph_recreations <json-directory>\n";return 2;}
    try{
        const std::filesystem::path dir(argv[1]);std::filesystem::create_directories(dir);
        const std::vector<Record> rec={
            {1,"graphs_01_german_auto_jobs","Auto tedesca: mai così pochi occupati","$RPCS81N.png","line trace digitized approximately from screenshot; source notes transcribed"},
            {2,"graphs_02_china_gdp_per_capita","China GDP Per Capita Growth (Current LCU)","Screenshot 2026-10-11 at 10-19-24 How China Launched a New Industrial Revolution - YouTube.png","time-series curve digitized approximately from screenshot; labeled World Bank as shown"},
            {3,"graphs_03_france_debt_comparison","Spesa pubblica · confronto percentuale","Screenshot 2026-10-11 at 10-36-44 Why France Is Europe's Next Debt Crisis - YouTube.png","exact visible categories and values transcribed: 38%, 48%, 50%"},
            {4,"graphs_04_saudi_megaprojects","Saudi Vision 2030 · Megaprogetti","Screenshot 2026-10-18 at 09-16-21 The (Overdue) Collapse of Saudi Megaprojects - YouTube.png","six project names and hierarchy transcribed; image thumbnails recreated as vector motifs"},
            {5,"graphs_05_patriot_inventory","Patriot Interceptor Inventory","Screenshot 2026-10-26 at 11-08-13 America’s deadly miscalculation in Iran - YouTube.png","bar lengths digitized approximately; values are not printed as exact claims"},
            {6,"graphs_06_apple_services_revenue","Apple’s Transformation Under Tim Cook","Screenshot 2026-10-26 at 11-18-08 How Tim Cook Built Apple’s $4.5 Trillion Empire Untold Story of the Man Who Made Apple Unstoppable - YouTube.png","exact visible metric transcribed: Apple Services FY2025 $103.73B; human figure recreated as vector silhouette"}};
        nlohmann::json manifest={{"schema","chronontemplate.graph-reference-recreations.v1"},{"renderer","Chronon C++ RenderPlan -> NV12 -> FFmpeg H.264"},{"frames",kFrames},{"fps",kFps},{"resolution",{{"width",1920},{"height",1080}}},{"reconstructions",nlohmann::json::array()}};
        for(const auto& r:rec){
            Assets a;SceneContext c(r.name,a);
            switch(r.id){case 1:unemployment(c);break;case 2:chinaGdp(c);break;case 3:franceBars(c);break;case 4:saudiProjects(c);break;case 5:patriotInventory(c);break;case 6:appleServices(c);break;default:throw std::logic_error("unknown scene");}
            writePlan(c,r.name,dir);
            manifest["reconstructions"].push_back({{"id",r.id},{"name",r.name},{"title",r.title},{"source_screenshot",r.source},{"method",r.method},{"plan",r.name+".plan.json"},{"video",r.name+".mp4"}});
            std::cout<<"emitted "<<r.name<<'\n';
        }
        std::ofstream out(dir/"reconstruction_manifest.json",std::ios::binary|std::ios::trunc);
        if(!out||!(out<<manifest.dump(2)<<'\n'))throw std::runtime_error("cannot write manifest");
    }catch(const std::exception& e){std::cerr<<"graph recreation emission failed: "<<e.what()<<'\n';return 1;}
}
