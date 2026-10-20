#include <nlohmann/json.hpp>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <string>
using J=nlohmann::json;
static std::string quote(const std::string& s){std::string o="'";for(char c:s)o+=c=='\''?"'\\''":std::string(1,c);return o+"'";}
static double width(const std::string& s,double fs){
 const std::string cmd="hb-shape --font-size="+std::to_string(fs)+" --output-format=json assets/fonts/PlayfairDisplay.ttf "+quote(s)+" 2>/dev/null";
 FILE* p=popen(cmd.c_str(),"r");if(!p)throw std::runtime_error("hb-shape unavailable");std::string out;char b[4096];while(std::fgets(b,sizeof b,p))out+=b;if(pclose(p))throw std::runtime_error("HarfBuzz shaping failed");
 auto glyphs=J::parse(out);double w=0;for(const auto& g:glyphs)w+=g.value("ax",0.0);return w;
}
int main(int argc,char**argv){try{
 const int W=argc>1?std::stoi(argv[1]):854,H=argc>2?std::stoi(argv[2]):480;
 const double s=W/1920.0,fs=42*s,left=112*s,lineH=57*s;
 const std::string font="assets/fonts/PlayfairDisplay.ttf";
 J layers=J::array();
 layers.push_back(J{{"id","paper"},{"type","color"},{"color",{.925,.922,.912,1}},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 layers.push_back(J{{"id","paper_center"},{"type","shape"},{"enable_3d",true},{"size",{W*.94,H*.96}},{"position",{W*.5,H*.5,0}},{"shape",{{"type","rect"},{"fill",{.965,.962,.952,1}}}},{"start_frame",0},{"duration_frames",1}});
 auto addText=[&](const std::string& id,const std::string& str,double y,bool focus){
  const double w=width(str,fs);
  J l={{"id",id},{"type","text"},{"text",str},{"position",{left+w*.5,y+lineH*.5,0}},{"size",{W-left*2,lineH*1.3}},{"enable_3d",true},{"start_frame",0},{"duration_frames",1}};
  l["style"]=J{{"font",font},{"font_size",fs},{"fill",focus?"#232323":"#777875"}};
  if(!focus){
   J selector={{"id",id+"_line"},{"unit","character"},{"shape","square"},{"order","forward"},{"combine","replace"}};
   selector["start"]=J{{"keyframes",J::array({J{{"frame",0},{"value",0.0}}})},{"easing","linear"}};
   selector["end"]=J{{"keyframes",J::array({J{{"frame",0},{"value",100.0}}})},{"easing","linear"}};
   J animator={{"id",id+"_soft_focus_falloff"},{"selectors",J::array({selector})}};
   animator["properties"]=J::array({J{{"property","blur"},{"easing","linear"},{"keyframes",J::array({J{{"frame",0},{"value",3.8}}})}}});
   l["text_animators"]=J::array({animator});
  }
  layers.push_back(std::move(l));return w;
 };
 auto addBand=[&](const std::string& id,const std::string& str,double y){
  const double w=width(str,fs);
  layers.push_back(J{{"id",id},{"type","shape"},{"size",{w+7*s,lineH*.56}},{"position",{left+(w+7*s)*.5,y+lineH*.50,1}},{"enable_3d",true},{"shape",{{"type","rect"},{"fill",{.92,.85,.02,.93}}}},{"start_frame",0},{"duration_frames",1}});
 };
 const double ys[]={60*s,116*s,172*s,228*s,284*s,340*s,396*s};
 addText("context_before_1","Bliss, Skunk, Moon Rocks, and JWH-018, -073 (and other numerical suffixes), after",ys[0],false);
 addText("context_before_2","Huffman’s initials.",ys[1],false);
 const std::string a="Synthetic cannabis, unlike pot, however, can cause a huge variety of";
 const std::string b="symptoms, which can be severe: Agitation, vomiting, hallucination, paranoia, tremor, seizure,";
 const std::string c="tachycardia,";
 addBand("focus_marker_1",a,ys[2]);addText("focus_line_1",a,ys[2],true);
 addBand("focus_marker_2",b,ys[3]);addText("focus_line_2",b,ys[3],true);
 addBand("focus_marker_3",c,ys[4]);addText("focus_line_3",c,ys[4],true);
 addText("context_after_1","hypokalemia, chest pain, cardiac problems, stroke, kidney damage, acute",ys[5],false);
 addText("context_after_2","psychosis, brain damage, and death.",ys[6],false);
 J plan={{"schema","chronon.render-plan.v3"},{"version",3},{"job_id","synthetic_cannabis_focus_reference"},{"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},{"camera",{{"type","perspective"},{"position",{0,0,-1280*s}},{"rotation_deg",{0,2.0,0}},{"fov_deg",48},{"near",1},{"far",5000},{"zoom",1}}},{"layers",layers},{"output",{{"path","unused.png"},{"format","png"}}}};
 std::ofstream out(argc>3?argv[3]:"synthetic_cannabis_focus.plan.json");out<<plan.dump(2)<<"\n";return out?0:3;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
