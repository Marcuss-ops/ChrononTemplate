// Three separate stills that recreate the remaining supplied web references.
// Layout, typography, highlights and cards are native RenderPlan V3 layers.
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using J = nlohmann::json;
constexpr int W=1920,H=1080;
J color(const std::string& s,double a=1.0){auto n=std::stoul(s.substr(1),nullptr,16);return J::array({((n>>16)&255)/255.0,((n>>8)&255)/255.0,(n&255)/255.0,a});}
J rect(std::string id,double x,double y,double w,double h,std::string c,double a=1,double rot=0){J j={{"id",id},{"type","shape"},{"enable_3d",true},{"position",{x+w/2,H-y-h/2,0}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"shape",{{"type","rect"},{"fill",color(c,a)}}}};if(rot)j["rotation"]={0,0,rot};return j;}
J text(std::string id,std::string v,double x,double y,double w,double h,double fs,std::string font,std::string c,std::string align="left") {return {{"id",id},{"type","text"},{"enable_3d",true},{"text",v},{"position",{x+w/2,H-y-h/2,0}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"style",{{"font",font},{"font_size",fs},{"fill",c},{"fit_mode","none"},{"text_align",align}}}};}
J img(std::string id,std::string asset,double x,double y,double w,double h,double rot=0){J j={{"id",id},{"type","image"},{"enable_3d",true},{"screen_space",true},{"asset",asset},{"position",{x+w/2,y+h/2,0}},{"size",{w,h}},{"fit","cover"},{"start_frame",0},{"duration_frames",1}};if(rot)j["rotation"]={0,0,rot};return j;}
J plan(std::string id,J layers){return {{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",id},{"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},{"layers",std::move(layers)},{"output",{{"path",id+".mp4"},{"format","mp4"},{"codec","h264"}}}};}
J polaroid(){J l=J::array();l.push_back({{"id","canvas"},{"type","color"},{"color",color("#171819")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 // Restrained grain marks retain the nearly black woven backdrop of the reference.
 for(int i=0;i<58;i++){double x=(i*317)%W,y=(i*191)%H;l.push_back(rect("grain_"+std::to_string(i),x,y,1+(i%3),1,"#777777",.10));}
 // Back cards first; the center portrait sits forward and larger.
 // Shape and image layers use opposite Y conventions, so use opposite
 // rotation signs to keep each white matte aligned with its photograph.
 l.push_back(rect("left_shadow",170,304,512,673,"#000000",.55,-12));l.push_back(rect("left_frame",158,288,512,673,"#F3F3F1",1,-12));l.push_back(img("left_portrait","assets/drive_trio_replica_v1/online/portrait_man1.jpg",184,318,460,613,12));
 l.push_back(rect("right_shadow",1238,304,512,673,"#000000",.55,12));l.push_back(rect("right_frame",1250,288,512,673,"#F3F3F1",1,12));l.push_back(img("right_portrait","assets/drive_trio_replica_v1/online/portrait_man2.jpg",1276,318,460,613,-12));
 l.push_back(rect("center_shadow",646,201,628,672,"#000000",.7));l.push_back(rect("center_frame",632,184,656,656,"#F6F6F5"));l.push_back(img("center_portrait","assets/drive_trio_replica_v1/online/portrait_woman.jpg",666,218,588,588));
 // Faint horizontal CRT texture from the supplied central print.
 for(int y=223,n=0;y<803;y+=9,++n)l.push_back(rect("scan_"+std::to_string(n),668,y,584,1,"#111111",.07));
 return l;}
J archive(){J l=J::array();l.push_back({{"id","canvas"},{"type","color"},{"color",color("#D7D6D4")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 l.push_back(text("archive_label","Archive image",104,94,260,28,16,"assets/fonts/Inter-Bold.ttf","#383735"));
 l.push_back(rect("label_rule",104,124,104,2,"#77746E"));
 l.push_back(text("archive_subject","Bednyaks, Serednyaks, and Kulaks",104,132,440,28,16,"assets/fonts/Inter-Bold.ttf","#383735"));
 const double x[3]={238,739,1240}; const char* names[3]={"Bednyaks","Serednyaks","Kulaks"};const char* assets[3]={"bednyaks.png","serednyaks.png","kulaks.png"};
 for(int i=0;i<3;i++){double y=390;l.push_back(rect("photo_shadow_"+std::to_string(i),x[i]+14,y+24,430,395,"#77746E",.40));l.push_back(img("photo_"+std::to_string(i),std::string("assets/web_archive_v1/")+assets[i],x[i],y,430,395));l.push_back(text("label_"+std::to_string(i),names[i],x[i],810,430,38,24,"assets/fonts/PlayfairDisplay.ttf","#F5F3EF","center"));}
 return l;}
J nike(){J l=J::array();l.push_back({{"id","ruled_paper"},{"type","color"},{"color",color("#F2EFE7")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 // Fine notebook ruling from the supplied crop, with the same ink and marker treatment.
 for(int y=78,i=0;y<1080;y+=76,++i)l.push_back(rect("paper_rule_"+std::to_string(i),0,y,W,2,"#A9B2B5",.20));
 l.push_back(text("context","THE RISE AND FALL OF NIKE",-172,254,900,38,19,"assets/fonts/Inter-Bold.ttf","#75736E"));
 l.push_back(rect("yellow_marker",250,454,1420,160,"#F7D426",.88));
 l.push_back(text("phrase","one company",260,438,1400,190,122,"assets/fonts/PlayfairDisplay-BoldItalic.ttf","#111111","center"));
 l.push_back(text("ellipsis","…",115,476,160,112,105,"assets/fonts/PlayfairDisplay-BoldItalic.ttf","#111111"));
 l.push_back(text("small_caption","A story of ambition, culture, and a $230 billion fall",380,690,1160,54,28,"assets/fonts/PlayfairDisplay.ttf","#595750","center"));
 return l;}
J aiTalent(){J l=J::array();l.push_back({{"id","paper"},{"type","color"},{"color",color("#F8F8F6")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 for(int i=0;i<24;i++)l.push_back(rect("paper_fiber_"+std::to_string(i),0,45+i*44,W,1,"#B8BFC0",.045));
 l.push_back(text("kicker","AI  ·  META",-11,76,420,45,32,"assets/fonts/Inter-Medium.ttf","#737F80"));
 l.push_back(rect("hl_line_1",120,208,1395,115,"#F7D51A",.94));
 l.push_back(text("line_1","Meta’s $100 million signing",-207,193,1690,134,82,"assets/fonts/PlayfairDisplay-Bold.ttf","#152126"));
 l.push_back(rect("hl_line_2",120,326,1260,114,"#F7D51A",.94));
 l.push_back(text("line_2_high","bonuses for OpenAI staff",-53,309,1290,138,82,"assets/fonts/PlayfairDisplay-Bold.ttf","#152126"));
 l.push_back(text("line_2_plain","are just",1300,309,490,138,82,"assets/fonts/PlayfairDisplay-Bold.ttf","#152126"));
 l.push_back(text("line_3","the latest sign of extreme AI talent",-133,427,1780,138,82,"assets/fonts/PlayfairDisplay-Bold.ttf","#152126"));
 l.push_back(text("line_4","war",-32,545,450,138,82,"assets/fonts/PlayfairDisplay-Bold.ttf","#152126"));
 return l;}
J docCover(){J l=J::array();l.push_back(img("newsroom_hero","assets/images/investigative_journalist_hero.png",0,0,W,H));l.push_back(rect("dark_wash",0,0,W,H,"#081015",.58));
 l.push_back(rect("left_shade",0,0,920,H,"#071015",.56));l.push_back(rect("eyebrow_rule",128,202,94,5,"#D5AC45"));
 l.push_back(text("eyebrow","CHRONON DOCUMENTARIES   /   EPISODE 01",-142,160,1000,44,21,"assets/fonts/Inter-Bold.ttf","#E1D8C6"));
 l.push_back(text("title_1","THE COST",-480,316,1540,150,112,"assets/fonts/Oswald-Bold.ttf","#F7F4ED"));l.push_back(text("title_2","OF WINNING",-340,441,1540,150,112,"assets/fonts/Oswald-Bold.ttf","#E6BE55"));
 l.push_back(text("dek","Inside the decisions that changed everything",-222,622,1200,66,34,"assets/fonts/PlayfairDisplay.ttf","#E9E4DB"));
 l.push_back(rect("bottom_rule",128,870,1664,2,"#FFFFFF",.38));l.push_back(text("series","A CHRONON ORIGINAL  ·  INVESTIGATIONS",-170,902,1100,38,17,"assets/fonts/Inter-Medium.ttf","#D5D0C7"));
 l.push_back(text("duration","CHAPTER 01  ·  ARCHIVE / CONTEXT",1110,902,680,38,17,"assets/fonts/Inter-Bold.ttf","#D5D0C7","right"));return l;}
J evidenceBoard(){J l=J::array();l.push_back(img("corkboard","assets/nba_rivalry/web/corkboard_bg.png",0,0,W,H));
 l.push_back(text("board_tag","FIELD NOTES   /   INVESTIGATION 07",-212,58,950,42,19,"assets/fonts/Inter-Bold.ttf","#F1E7D0"));
 l.push_back(rect("paper_left_shadow",147,196,675,692,"#20180F",.52));l.push_back(rect("paper_left",128,178,675,692,"#F2ECDD"));
 l.push_back(text("paper_kicker","THE PAPER TRAIL",-51,214,610,34,18,"assets/fonts/Inter-Bold.ttf","#7C3027"));
 l.push_back(text("paper_title_a","Every decision",15,277,570,62,39,"assets/fonts/PlayfairDisplay-Bold.ttf","#292823"));l.push_back(text("paper_title_b","left a trace",15,332,570,62,39,"assets/fonts/PlayfairDisplay-Bold.ttf","#292823"));
 l.push_back(img("evidence_photo_1","assets/web_archive_v1/bednyaks.png",177,432,262,189));l.push_back(img("evidence_photo_2","assets/web_archive_v1/kulaks.png",461,432,287,189));
 l.push_back(text("paper_caption","ARCHIVE IMAGES  /  03 DOCUMENTS",-13,655,620,32,15,"assets/fonts/Inter-Medium.ttf","#6E6A60"));
 // A second note and hand-drawn red connector create an investigation-board layout.
 l.push_back(rect("note_shadow",1018,232,535,422,"#1D150D",.48));l.push_back(rect("note",1003,215,535,422,"#E8D58B"));
 l.push_back(text("note_label","OPEN QUESTION",850,246,530,35,17,"assets/fonts/Inter-Bold.ttf","#6B3028"));
 l.push_back(text("note_text_1","Who benefited",945,311,490,60,34,"assets/fonts/PlayfairDisplay-Bold.ttf","#282722"));l.push_back(text("note_text_2","from the turning point?",970,362,600,60,31,"assets/fonts/PlayfairDisplay.ttf","#282722"));
 l.push_back(rect("red_string",723,715,555,5,"#9B302A",.92,14));l.push_back(rect("red_string_vertical",1203,624,5,110,"#9B302A",.92,-18));
 l.push_back(rect("pin",1250,180,20,20,"#B63D32"));l.push_back(text("stamp","UNRESOLVED",1370,729,420,38,19,"assets/fonts/Oswald-Bold.ttf","#F4E9D1"));
 return l;}
J dataExplainer(){J l=J::array();l.push_back({{"id","ivory"},{"type","color"},{"color",color("#F4F1E8")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 l.push_back(text("kicker","THE BUSINESS OF CULTURE   /   DATA BRIEF",-200,72,1000,42,18,"assets/fonts/Inter-Bold.ttf","#635E53"));
 l.push_back(text("heading","A NUMBER THAT CHANGED THE STORY",-260,150,1460,58,34,"assets/fonts/Inter-Bold.ttf","#24241F"));
 l.push_back(text("figure","$230B",-260,276,1420,250,204,"assets/fonts/Oswald-Bold.ttf","#151A1A"));
 l.push_back(rect("marker",184,527,555,13,"#D5B34C"));l.push_back(text("caption","THE QUESTION BEHIND THE HEADLINE",-51,582,970,52,28,"assets/fonts/Inter-Bold.ttf","#37352F"));
 l.push_back(rect("vertical_divider",1002,212,2,650,"#C7C0B3"));
 l.push_back(text("side_kicker","FOLLOW THE SIGNAL",1004,234,650,43,20,"assets/fonts/Inter-Bold.ttf","#8E332A","center"));
 l.push_back(text("side_copy_1","Markets move in",1010,323,650,60,36,"assets/fonts/PlayfairDisplay.ttf","#34322D","center"));l.push_back(text("side_copy_2","numbers. Stories",1010,376,650,60,36,"assets/fonts/PlayfairDisplay.ttf","#34322D","center"));l.push_back(text("side_copy_3","move in people.",1010,429,650,60,36,"assets/fonts/PlayfairDisplay.ttf","#34322D","center"));
 l.push_back(rect("chart_base",1080,760,590,2,"#8A8479"));double heights[7]={110,160,132,245,220,335,405};for(int i=0;i<7;i++){l.push_back(rect("bar_"+std::to_string(i),1100+i*78,760-heights[i],46,heights[i],i==6?"#B54335":"#343C3A",.9));}
 l.push_back(text("footer","CHRONON DOCUMENTARIES   ·   THE ECONOMY OF ATTENTION",-280,948,1300,30,14,"assets/fonts/Inter-Medium.ttf","#777166"));return l;}
J archiveQuote(){J l=J::array();l.push_back({{"id","paper"},{"type","color"},{"color",color("#DDD8CA")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 l.push_back(img("archive_portrait","assets/famous_people_trio_v1/neil_armstrong.png",0,0,820,H));l.push_back(rect("photo_wash",0,0,820,H,"#111A1E",.25));l.push_back(rect("right_panel",820,0,1100,H,"#EEEADF"));
 l.push_back(text("archive_top","ARCHIVE PORTRAIT   /   APOLLO 11",1040,108,620,38,18,"assets/fonts/Inter-Bold.ttf","#7D4034","center"));
 l.push_back(text("quote_1","ONE SMALL STEP",870,365,900,90,65,"assets/fonts/PlayfairDisplay-Italic.ttf","#22231F","center"));l.push_back(text("quote_2","A WORLD WATCHING",870,458,900,90,58,"assets/fonts/PlayfairDisplay-Italic.ttf","#22231F","center"));
 l.push_back(rect("gold_rule",1100,664,420,3,"#B89A56"));l.push_back(text("speaker","NEIL ARMSTRONG",980,708,700,42,19,"assets/fonts/Inter-Bold.ttf","#34352F","center"));l.push_back(text("context","ARCHIVE RECORD  ·  APOLLO 11",980,760,700,36,16,"assets/fonts/Inter-Medium.ttf","#777267","center"));
 l.push_back(text("folio","CHRONON  /  THE MOMENT THAT CHANGED EVERYTHING",950,970,760,32,14,"assets/fonts/Inter-Medium.ttf","#777267","center"));return l;}
J announcement(){J l=J::array();l.push_back({{"id","paper"},{"type","color"},{"color",color("#F6F5F2")},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 l.push_back(text("brand","MORPH  /  JOURNAL",92,32,360,35,22,"assets/fonts/Inter-ExtraBold.ttf","#242424"));
 l.push_back(text("nav_research","Research",1190,39,130,28,16,"assets/fonts/Inter-Medium.ttf","#363636"));l.push_back(text("nav_policy","Policy",1384,39,110,28,16,"assets/fonts/Inter-Medium.ttf","#363636"));l.push_back(text("nav_comments","Comments",1541,39,190,28,16,"assets/fonts/Inter-Medium.ttf","#363636"));
 l.push_back(text("kicker","Announcements",690,188,540,50,27,"assets/fonts/Inter-Bold.ttf","#424242","center"));
 l.push_back(text("headline_a","Statement on the US government",92,344,1740,104,82,"assets/fonts/Inter-ExtraBold.ttf","#111111"));
 l.push_back(rect("headline_highlight",245,457,1375,106,"#E9826C",.76));
 l.push_back(text("headline_b","to suspend access to Fable 5 and Mythos",92,457,1740,108,74,"assets/fonts/Inter-ExtraBold.ttf","#111111"));
 l.push_back(text("date","12 Jun 2026",735,627,450,48,30,"assets/fonts/Inter-Regular.ttf","#686868","center"));
 const std::string body="The US government, citing national security authorities, has issued an export control directive to suspend access to Fable 5 and Mythos for any foreign national, whether inside or outside the United States. The move raises questions for researchers, companies and the wider technology community.";
 l.push_back(text("body",body,590,778,1110,205,28,"assets/fonts/PlayfairDisplay.ttf","#514F4C"));
 l.push_back(rect("footer_rule",590,1003,1110,1,"#D4D1CC"));l.push_back(text("footer","MORPH JOURNAL  ·  POLICY DESK",590,1018,700,24,13,"assets/fonts/Inter-Medium.ttf","#77736D"));return l;}
J newspaper(){J l=J::array();l.push_back(img("warm_studio_backdrop","assets/nba_rivalry/web/corkboard_bg_softblur.png",0,0,W,H));
 // Folder and rear clipping make the deep stack of evidence papers.
 l.push_back(rect("classified_folder",1323,134,410,765,"#B99062"));l.push_back(rect("folder_shadow",1341,147,377,728,"#8E6843",.45));
 l.push_back(rect("rear_paper",390,162,590,820,"#E8E4D9"));l.push_back(text("rear_masthead","NATIONAL",425,197,280,32,20,"assets/fonts/PlayfairDisplay-Bold.ttf","#29251F"));
 l.push_back(rect("rear_rule",426,235,500,3,"#38332C"));l.push_back(rect("rear_highlight",426,255,490,97,"#EACB4D"));l.push_back(text("rear_headline","Federal judge orders\nrecords released",426,255,490,106,34,"assets/fonts/PlayfairDisplay-Bold.ttf","#1D1B18"));
 l.push_back(img("newsroom_photo","assets/images/investigative_journalist_hero.png",432,381,495,241));
 l.push_back(rect("front_shadow",601,109,648,881,"#191713",.45));l.push_back(rect("front_paper",574,83,650,878,"#F5F1E7"));
 l.push_back(text("paper_masthead","CNN",822,103,165,32,24,"assets/fonts/PlayfairDisplay-Bold.ttf","#28251E","center"));l.push_back(rect("masthead_rule",614,143,570,5,"#343029"));
 l.push_back(rect("yellow_1",614,166,547,45,"#F2D34F"));l.push_back(text("head_1","Romanian prosecutors indict",614,165,570,50,39,"assets/fonts/PlayfairDisplay-Bold.ttf","#171613"));
 l.push_back(rect("yellow_2",614,211,533,45,"#F2D34F"));l.push_back(text("head_2","Andrew Tate for trafficking",614,210,570,50,39,"assets/fonts/PlayfairDisplay-Bold.ttf","#171613"));
 l.push_back(rect("yellow_3",614,256,343,44,"#F2D34F"));l.push_back(text("head_3","and money laundering",614,255,570,50,39,"assets/fonts/PlayfairDisplay-Bold.ttf","#171613"));
 l.push_back(text("byline","By Reuters   |   UPDATED SEP 4, 2026",615,310,550,28,15,"assets/fonts/PlayfairDisplay.ttf","#3B3934"));
 l.push_back(img("article_photo","assets/images/investigative_journalist_hero.png",614,353,570,309));
 l.push_back(text("caption","Andrew Tate speaks with members of the press outside the courthouse.",615,668,568,39,13,"assets/fonts/PlayfairDisplay-Italic.ttf","#615D54"));
 l.push_back(text("column_left","Bucharest (Reuters) — Romanian prosecutors formally indicted social media influencer Andrew Tate on charges of trafficking and money laundering. The case follows a lengthy investigation into activity in the country.",615,716,265,235,17,"assets/fonts/PlayfairDisplay.ttf","#34312B"));
 l.push_back(rect("column_rule",895,714,1,233,"#B7B0A4"));l.push_back(text("column_right","Prosecutors said the investigation remains active. Tate and his representatives have denied wrongdoing. The filing outlines multiple allegations and details a continuing legal process.",914,716,270,230,17,"assets/fonts/PlayfairDisplay.ttf","#34312B"));
 l.push_back(text("confidential_stamp","CONFIDENTIAL",1374,410,300,55,28,"assets/fonts/Oswald-Bold.ttf","#9E4237","center"));
 return l;}
int main(int argc,char**argv)try{if(argc!=3)throw std::runtime_error("usage: emit_web_reference_stills <archive|polaroid|announcement|newspaper|nike|ai_talent|doc_cover|evidence_board|data_explainer|archive_quote> <plan.json>");std::string key=argv[1];J layers=key=="archive"?archive():key=="polaroid"?polaroid():key=="announcement"?announcement():key=="newspaper"?newspaper():key=="nike"?nike():key=="ai_talent"?aiTalent():key=="doc_cover"?docCover():key=="evidence_board"?evidenceBoard():key=="data_explainer"?dataExplainer():key=="archive_quote"?archiveQuote():J();if(layers.empty())throw std::runtime_error("unknown preset: "+key);fs::path out=fs::absolute(argv[2]);fs::create_directories(out.parent_path());std::ofstream f(out);f<<plan("web_reference_"+key+"_native_v1",std::move(layers)).dump(2)<<'\n';if(!f)throw std::runtime_error("could not write plan");std::cout<<out<<'\n';return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
