// Sample the lateral pull-out with ChrononMotion3D's CameraRig.
#include <chrononmotion/motion/CameraRig.hpp>
#include <chrononmotion/motion/Easing.hpp>

#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>

using chrononmotion::Vector3;
using chrononmotion::motion::CameraRig;

int main(int argc,char**argv){
 try{
  if(argc!=2)throw std::runtime_error("usage: sample_rapdaily_camera <output.csv>");
  constexpr int fps=30,frames=90;
  const float end=float(frames-1)/float(fps);
  const auto ease=chrononmotion::motion::Easing::easeInOut();
  CameraRig rig(1,45.f,16.f/9.f,1.f,5000.f);
  // Deliberate lateral camera travel: enough angle to read the title plane in
  // perspective, while keeping the full phrase inside the safe area.
  rig.setPosition({550.f,540.f,1220.f}).setTarget({960.f,540.f,0.f});
  rig.positionTrack().add(0.f,{550.f,540.f,1220.f},ease)
      .add(end*.52f,{960.f,540.f,1120.f},ease)
      .add(end,{1370.f,540.f,1300.f},ease);
  rig.targetTrack().add(0.f,{960.f,540.f,0.f},ease)
      .add(end*.52f,{960.f,540.f,0.f},ease)
      .add(end,{960.f,540.f,0.f},ease);
  std::ofstream out(argv[1]);
  if(!out)throw std::runtime_error("cannot create camera sample output");
  for(int frame=0;frame<frames;++frame){
   const auto pose=rig.sample(float(frame)/float(fps));
   const float x=pose.orientation.x,y=pose.orientation.y,z=pose.orientation.z,w=pose.orientation.w;
   const double yaw=std::atan2(2.0*(w*y+x*z),1.0-2.0*(y*y+z*z));
   out<<frame<<','<<pose.position.x<<','<<pose.position.y<<','<<pose.position.z<<','<<pose.fov<<','<<yaw<<'\n';
  }
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
