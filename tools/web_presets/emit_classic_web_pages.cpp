#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using J = nlohmann::ordered_json;
namespace {
constexpr int W=1920,H=1080;
constexpr const char* regular="assets/fonts/Inter-Regular.ttf";
constexpr const char* medium="assets/fonts/Inter-Medium.ttf";
constexpr const char* bold="assets/fonts/Inter-Bold.ttf";
constexpr const char* extra="assets/fonts/Inter-ExtraBold.ttf";
constexpr const char* serif="assets/fonts/PlayfairDisplay-Bold.ttf";
struct Page { J layers=J::array(); std::string name; };
J shape(std::string id,float x,float y,float w,float h,std::string color,float alpha=1.f) {
  const auto c=[&](int i){return std::stoi(color.substr(1+i*2,2),nullptr,16)/255.f;};
  return {{"id",id},{"type","shape"},{"position",{x+w/2.f,y+h/2.f}},
    {"size",{w,h}},{"start_frame",0},{"duration_frames",1},
    {"shape",{{"type","rect"},{"fill",{c(0),c(1),c(2),alpha}}}}};
}
void rect(Page& p,std::string id,float x,float y,float w,float h,std::string c,float a=1.f){p.layers.push_back(shape(std::move(id),x,y,w,h,std::move(c),a));}
void txt(Page& p,std::string id,std::string value,float x,float y,float w,float h,float fs,const char* font,std::string color) {
 p.layers.push_back({{"id",std::move(id)},{"type","text"},{"text",std::move(value)},
   {"position",{x+w/2.f,y+h/2.f}},{"size",{w,h}},
   {"start_frame",0},{"duration_frames",1},
   {"style",{{"font",font},{"font_size",fs},{"fill",std::move(color)},{"fit_mode","none"}}}});
}
void img(Page& p,std::string id,std::string asset,float x,float y,float w,float h) {
  p.layers.push_back({{"id",std::move(id)},{"type","image"},{"asset",std::move(asset)},
    {"position",{x+w/2.f-W/2.f,y+h/2.f-H/2.f}},{"size",{w,h}},
    {"fit","cover"},{"start_frame",0},{"duration_frames",1}});
}
void paper(Page& p,std::string color){const auto c=[&](int i){return std::stoi(color.substr(1+i*2,2),nullptr,16)/255.f;};p.layers.push_back({{"id","canvas"},{"type","color"},{"color",{c(0),c(1),c(2),1.f}},{"size",{W,H}},{"start_frame",0},{"duration_frames",1}});}
J plan(const Page& p){return {{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",p.name},
 {"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},
 {"layers",p.layers},{"output",{{"path",p.name+".mp4"},{"format","mp4"},{"codec","h264"}}}};}

Page home(){Page p;p.name="classic_home_editorial";paper(p,"#F7F6F2");rect(p,"topbar",0,0,W,34,"#13283A");txt(p,"edition","INDEPENDENT JOURNALISM  ·  ITALIAN EDITION",70,4,750,25,14,medium,"#FFFFFF");txt(p,"topright","THURSDAY 22 OCTOBER 2026     SUBSCRIBE",1370,4,480,25,14,medium,"#FFFFFF");
 txt(p,"brand","THE CHRONICLE",560,42,800,93,75,serif,"#102B45");txt(p,"tagline","Stories that explain the present",640,127,640,28,17,regular,"#68747B");rect(p,"rule_1",70,164,1780,2,"#1C3547");txt(p,"nav","WORLD      BUSINESS      CULTURE      SCIENCE      TECHNOLOGY      LIFE      OPINION",190,172,1540,38,17,bold,"#273E4E");rect(p,"rule_2",70,217,1780,1,"#C9CECD");
 txt(p,"lead_tag","WORLD  /  THE BIG STORY",78,239,540,30,16,extra,"#176D8C");txt(p,"lead_head_1","The city that learned",76,276,1030,72,56,serif,"#17232B");txt(p,"lead_head_2","to breathe again",76,342,1030,72,56,serif,"#17232B");txt(p,"lead_dek","A bold experiment is giving residents cleaner air, quieter streets and a new sense of neighbourhood.",80,422,1000,58,23,regular,"#4E585E");txt(p,"lead_by","BY ELENA MARCHETTI  ·  8 MIN READ",80,490,760,28,15,bold,"#53616A");txt(p,"lead_cta","READ THE FULL STORY  →",80,536,440,32,17,extra,"#176D8C");
 img(p,"lead_photo","assets/images/true_legacy_night_restaurant_v1.png",1160,239,690,360);rect(p,"photo_scrim",1160,559,690,40,"#142432",.86);txt(p,"photo_caption","A neighbourhood changes after dark",1180,567,640,24,14,medium,"#FFFFFF");
 rect(p,"latest_rule",70,625,1780,2,"#1C3547");txt(p,"latest","LATEST",75,639,280,38,23,extra,"#17232B");
 const char* imgs[]={"assets/images/investigative_journalist_card.png","assets/images/people_sample_portrait_b.png","assets/images/card_quad_1.png"};
 const char* tags[]={"CULTURE  ·  5 MIN","BUSINESS  ·  7 MIN","IDEAS  ·  4 MIN"};const char* heads[]={"Inside the newsroom\nchanging local news","The people shaping\na fairer future","Why good design\nstarts with listening"};
 for(int i=0;i<3;i++){float x=76+i*594;img(p,"latest_img_"+std::to_string(i),imgs[i],x,683,550,190);txt(p,"latest_tag_"+std::to_string(i),tags[i],x,882,540,24,14,extra,"#176D8C");txt(p,"latest_head_"+std::to_string(i),heads[i],x,909,550,86,27,serif,"#17232B");}
 return p;}

Page forum(){Page p;p.name="classic_blog_forum";paper(p,"#F1F4F6");rect(p,"header",0,0,W,76,"#FFFFFF");rect(p,"header_rule",0,74,W,2,"#DCE2E6");txt(p,"brand","CHRONON / COMMUNITY",62,17,470,40,25,extra,"#183C5A");rect(p,"search",700,17,510,42,"#F1F4F6");txt(p,"search_text","SEARCH  ·  Discussions and people",720,24,470,28,16,regular,"#7A8790");rect(p,"new_button",1550,15,210,46,"#176D8C");txt(p,"new_text","NEW THREAD",1570,24,180,28,15,bold,"#FFFFFF");img(p,"avatar","assets/images/people_sample_portrait_b.png",1790,12,48,48);
 rect(p,"sidebar",34,103,285,930,"#FFFFFF");txt(p,"categories","CATEGORIES",60,125,230,30,16,extra,"#52616B");
 const char* cats[]={"●  Announcements","●  General discussion","●  Creative work","●  Questions & help","●  Show and tell"};const char* counts[]={"12","248","86","143","57"};for(int i=0;i<5;i++){int y=175+i*54;txt(p,"cat_"+std::to_string(i),cats[i],58,y,225,31,16,i==0?bold:regular,i==0?"#176D8C":"#394A55");txt(p,"count_"+std::to_string(i),counts[i],266,y,35,31,14,medium,"#8B969D");}
 rect(p,"side_sep",58,469,232,1,"#DCE2E6");txt(p,"tags_title","POPULAR TAGS",58,486,230,28,15,extra,"#52616B");txt(p,"tags","#design   #rendering\n#feedback   #workflow",58,523,230,77,15,regular,"#54636D");txt(p,"online_title","ONLINE NOW",58,630,220,29,15,extra,"#52616B");img(p,"member_1","assets/images/premium_sample_portrait.png",60,676,34,34);txt(p,"member_name_1","Maya Chen",103,679,160,25,15,medium,"#394A55");img(p,"member_2","assets/images/truett_cathy_portrait_v5_real_photo.png",60,721,34,34);txt(p,"member_name_2","Andrea Rossi",103,724,160,25,15,medium,"#394A55");
 txt(p,"crumb","Community  /  Forums  /  Announcements",355,103,800,28,15,medium,"#73818A");txt(p,"board_title","Announcements",352,139,650,58,43,extra,"#1A2C37");txt(p,"board_meta","12,408 discussions  ·  updated moments ago",355,198,650,28,15,regular,"#73818A");
 rect(p,"main_panel",340,240,1045,760,"#FFFFFF");txt(p,"tab_latest","LATEST",370,258,130,30,15,extra,"#176D8C");txt(p,"tab_top","TOP",525,258,90,30,15,medium,"#66757E");txt(p,"tab_unanswered","UNANSWERED",635,258,190,30,15,medium,"#66757E");rect(p,"tabs_rule",360,300,1000,1,"#DCE2E6");
 const char* titles[]={"Welcome to the new Chronon community","Share your latest scene and get feedback","Tips for building a clean render plan","What are you making this week?","New guide: planning a camera move","Show us your best title treatment"};const char* desc[]={"A place to learn, share work and help each other create.","Post a frame, explain your goal and invite critique.","A few patterns that have made projects easier to maintain.","Tell us what is on your timeline right now.","A practical walkthrough from first block to final pass.","Collecting strong examples from the community."};
 for(int i=0;i<6;i++){int y=314+i*111;if(i==0)rect(p,"pinned",356,y,1012,106,"#F0F8FA");else rect(p,"rowbg_"+std::to_string(i),356,y,1012,106,"#FFFFFF");img(p,"row_avatar_"+std::to_string(i),i%2?"assets/images/people_sample_portrait_b.png":"assets/images/premium_sample_portrait.png",372,y+17,54,54);txt(p,"row_title_"+std::to_string(i),titles[i],444,y+12,640,34,20,bold,"#243640");txt(p,"row_desc_"+std::to_string(i),desc[i],444,y+51,640,28,15,regular,"#76838B");txt(p,"row_stats_"+std::to_string(i),i==0?"48 replies\n1.2k views":"12 replies\n348 views",1110,y+21,170,55,14,medium,"#66757E");rect(p,"row_rule_"+std::to_string(i),370,y+105,975,1,"#E5E9EB");}
 rect(p,"right_panel",1410,103,475,330,"#FFFFFF");txt(p,"online","COMMUNITY TODAY",1440,125,410,30,16,extra,"#52616B");txt(p,"stats","1,284  MEMBERS\n   92  ONLINE NOW\n   36  NEW THIS WEEK",1440,174,390,150,22,bold,"#263A46");rect(p,"tip_panel",1410,457,475,315,"#E7F0F4");txt(p,"tip_title","A GOOD FIRST POST",1440,480,410,32,17,extra,"#176D8C");txt(p,"tip_body","Show a frame, describe what you want it to do, and tell us what you have tried so far.",1440,531,405,145,20,regular,"#344A58");
 return p;}

Page docs(){Page p;p.name="classic_wiki_docs";paper(p,"#FFFFFF");rect(p,"top",0,0,W,70,"#FFFFFF");rect(p,"toprule",0,68,W,2,"#E3E7EA");rect(p,"logo_square",48,17,36,36,"#176D8C");txt(p,"logo_mark","C",54,19,24,30,20,extra,"#FFFFFF");txt(p,"brand","Chronon Docs",98,17,290,38,24,extra,"#213541");rect(p,"version",405,19,100,32,"#F0F4F6");txt(p,"version_text","v3.2",418,22,80,26,14,medium,"#53636D");rect(p,"search",670,16,470,38,"#F3F5F6");txt(p,"search_text","SEARCH  ·  Documentation",687,21,440,28,15,regular,"#87939A");txt(p,"github","GITHUB",1530,21,120,28,15,bold,"#4D5C65");txt(p,"support","SUPPORT",1690,21,140,28,15,bold,"#4D5C65");
 rect(p,"left",44,91,300,945,"#FFFFFF");txt(p,"start","GETTING STARTED",65,111,250,26,14,extra,"#839099");const char* nav[]={"Introduction","Installation","Your first scene","GUIDES","Rendering","Camera and lenses","Working with assets","REFERENCE","Render plan schema","CLI commands","API"};int yy=151;for(int i=0;i<11;i++){if(i==3||i==7||i==10){yy+=9;txt(p,"navhead_"+std::to_string(i),nav[i],65,yy,250,25,13,extra,"#839099");yy+=34;}else{if(i==4)rect(p,"active",51,yy-4,285,34,"#EAF4F7");txt(p,"navitem_"+std::to_string(i),nav[i],i==4?77:66,yy,255,26,15,i==4?bold:regular,i==4?"#176D8C":"#465660");yy+=38;}}
 rect(p,"left_rule",344,90,1,946,"#E3E7EA");txt(p,"breadcrumb","Docs  /  Guides  /  Rendering",390,102,650,27,15,medium,"#71808A");txt(p,"h1","Rendering a scene",388,143,870,66,46,extra,"#192B36");txt(p,"intro","Turn an editable scene plan into a clear, repeatable render with Chronon.",391,215,850,50,21,regular,"#53636D");
 rect(p,"callout",390,287,858,92,"#EDF6F9");rect(p,"callout_edge",390,287,5,92,"#2490AA");txt(p,"callout_title","TIP",413,299,90,26,14,extra,"#176D8C");txt(p,"callout_body","Start with a representative frame and confirm the composition before rendering the full sequence.",413,326,805,42,16,regular,"#334A57");
 txt(p,"h2_plan","The render plan",390,403,850,44,29,extra,"#1D303B");txt(p,"body_1","A render plan describes the canvas, layers, timing and output settings. Keep each visual element on its own layer so it stays easy to revise.",392,452,840,66,17,regular,"#4E5E67");rect(p,"code",390,531,858,176,"#202A32");txt(p,"code_label","scene.plan.json",410,544,260,25,13,bold,"#AFC0CA");txt(p,"code_1", "{  \"canvas\": { \"width\": 1920, \"height\": 1080 },",410,579,810,24,15,regular,"#E6EDF1");txt(p,"code_2","   \"fps_num\": 30, \"duration_frames\": 180 },",410,611,810,24,15,regular,"#E6EDF1");txt(p,"code_3","  \"layers\": [ ... ],  \"output\": { ... }",410,643,810,24,15,regular,"#E6EDF1");
 txt(p,"h2_settings","Common settings",390,732,850,40,27,extra,"#1D303B");rect(p,"tablehead",390,783,858,38,"#F1F4F5");txt(p,"th_name","SETTING",410,790,210,25,13,extra,"#52616B");txt(p,"th_desc","PURPOSE",665,790,530,25,13,extra,"#52616B");const char* names[]={"canvas","fps_num","duration_frames"};const char* meanings[]={"Output width and height","Frames rendered per second","Total length of the sequence"};for(int i=0;i<3;i++){int y=823+i*43;rect(p,"trule_"+std::to_string(i),390,y+40,858,1,"#E3E7EA");txt(p,"tn_"+std::to_string(i),names[i],410,y+7,230,26,15,bold,"#176D8C");txt(p,"td_"+std::to_string(i),meanings[i],665,y+7,550,26,15,regular,"#465660");}
 rect(p,"right_rule",1280,91,1,946,"#E3E7EA");txt(p,"toc_title","ON THIS PAGE",1310,111,500,28,14,extra,"#7A8790");txt(p,"toc","The render plan\n\nCommon settings\n\nPreview and review\n\nNext steps",1310,155,480,190,16,medium,"#53636D");rect(p,"toc_active",1305,155,3,25,"#2490AA");rect(p,"note",1305,401,510,134,"#F4F7F8");txt(p,"note_title","Keep it reproducible",1324,416,460,28,15,extra,"#334A57");txt(p,"note_body","Record the backend, resolution and frame rate with each delivery.",1324,452,460,60,15,regular,"#5A6870");txt(p,"edit","EDIT THIS PAGE ON GITHUB  ↗",390,1001,500,26,14,bold,"#176D8C");return p;}
}
int main(int argc,char**argv) try {if(argc!=2)throw std::runtime_error("usage: emit_classic_web_pages <output-dir>");fs::path out=fs::absolute(argv[1]);fs::create_directories(out);for(Page p:{home(),forum(),docs()}){std::ofstream f(out/(p.name+".plan.json"));if(!f)throw std::runtime_error("cannot write plan");f<<plan(p).dump(2)<<'\n';}return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
