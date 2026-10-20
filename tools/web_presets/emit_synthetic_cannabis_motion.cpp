#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
using J=nlohmann::json;
int main(int argc,char**argv){
 if(argc!=3){std::cerr<<"usage: emit_synthetic_cannabis_motion <asset path relative to asset root> <output plan>\n";return 2;}
 const std::string asset=argv[1],outPath=argv[2];
 J plan={{"schema","chronon.render-plan.v2"},{"version",2},{"job_id","scientific_evidence_focus_yaw_v1"},
  {"canvas",{{"width",1920},{"height",1080},{"fps_num",30},{"fps_den",1},{"duration_frames",240}}},
  {"layers",J::array({
   J{{"id","paper_backdrop"},{"type","color"},{"color",{.84,.84,.84,1.0}},{"size",{1920,1080}},{"start_frame",0},{"duration_frames",240}},
   J{{"id","evidence_article_crop"},{"type","image"},{"asset",asset},{"fit","stretch"},{"position",{0,0,0}},{"size",{1920,1080}},{"enable_3d",true},{"start_frame",0},{"duration_frames",240},
    {"animation",{{"tracks",J::array({J{{"property","scale"},{"easing","in_out_cubic"},{"keyframes",J::array({J{{"frame",0},{"value",1.0}},J{{"frame",239},{"value",1.045}}})}}})}}}}
  })},
  {"camera",{{"type","perspective"},{"position",{0,0,-1180}},{"rotation_deg",{0,2.0,0}},{"fov_deg",50},{"near",1},{"far",5000}}},
  {"output",{{"path","Synthetic_Cannabis_Evidence_Focus.mp4"},{"format","mp4"},{"codec","h264"}}}};
 std::filesystem::create_directories(std::filesystem::path(outPath).parent_path());
 std::ofstream f(outPath);f<<plan.dump(2)<<"\n";if(!f)return 3;std::cout<<outPath<<"\n";return 0;
}
