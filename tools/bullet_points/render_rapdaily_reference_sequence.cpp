// Rebuild the supplied 3-second archive-title sequence with a clean portrait crop,
// a unified animated title overlay, and camera samples authored by ChrononMotion3D.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <blend2d.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>

namespace fs=std::filesystem;
constexpr int W=1920,H=1080,FPS=30,FRAMES=90;
const fs::path ROOT=L"C:/Users/pater/Pyt";
const fs::path OUTPUT_DIR=ROOT/L"ChrononTemplate/out/bullet_families/rapdaily_reference_rebuild";
const fs::path ASSET_DIR=ROOT/L"ChrononTemplate/out/bullet_families/rapdaily_single";
const fs::path FONT_DIR=ROOT/L"ChrononTemplate/assets/fonts";
double clamp01(double x){return std::clamp(x,0.0,1.0);}
double smooth(double x){x=clamp01(x);return x*x*(3-2*x);}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
double rnd(uint32_t x){return double(hash(x))/double(0xffffffffu);}
double shutterSampleAlpha(double alpha,int samples){
 alpha=clamp01(alpha);
 return 1.0-std::pow(1.0-alpha,1.0/double(samples));
}

struct CameraSample{double x,y,z,fov,yaw;};
struct CameraTransform{double x,y,scale,scaleX;};
CameraTransform cameraTransform(const CameraSample& pose,double planeZ){
 // Apply the sampled ChrononMotion3D perspective move to the two depth planes.
 const float focal=float(H)/(2.f*std::tan(float(pose.fov)*0.00872664626f));
 const double distance=std::max(1.0,double(pose.z)-planeZ);
 const double scale=focal/distance;
 // The rig looks at the composition target. Keep that target pinned to the
 // optical center while lateral camera travel changes the plane perspective.
 return {960.0,540.0,scale,scale*std::cos(pose.yaw)};
}

std::vector<CameraSample> readCameraSamples(){
 std::ifstream in(OUTPUT_DIR/L"camera_samples.csv");
 if(!in)throw std::runtime_error("Missing ChrononMotion3D camera samples; run build_render_rapdaily_reference_sequence.ps1");
 std::vector<CameraSample> samples;std::string line;
 while(std::getline(in,line)){std::istringstream row(line);int index{};CameraSample s{};char comma{};
  if(!(row>>index>>comma>>s.x>>comma>>s.y>>comma>>s.z>>comma>>s.fov>>comma>>s.yaw))continue;
  if(index!=static_cast<int>(samples.size()))throw std::runtime_error("Camera samples are not frame ordered");samples.push_back(s);}
 if(samples.size()!=FRAMES)throw std::runtime_error("Expected 90 ChrononMotion3D camera samples");return samples;
}

// --- Text animator, the same model the reference workflow uses: a range
// selector (start/end/offset) with a shape profile and high/low easing,
// applied per character. It drives position, opacity and scale together.
enum class RampShape{Square,Triangle,RampUp,RampDown,Smooth,Round};
struct TextAnimator{
 double startY{34.0};      // px vertical displacement applied to a selected glyph
 double scaleX{0.82};      // glyph x scale when fully selected
 double scaleY{0.82};      // glyph y scale when fully selected
 double start{0.0};        // range selector head, in glyph units
 double end{1.0};          // range selector tail, in glyph units
 double offset{-0.12};     // normalized left-to-right selector cursor
 double edgeWidth{0.045};  // one-character soft ramp boundary
 RampShape shape{RampShape::RampUp};
 double easeHigh{0.0};
 double easeLow{100.0};
};
double easeInOut(double u,double easeHigh,double easeLow){
 u=clamp01(u);
 // Keep each half monotonic: Ease High eases into motion; Ease Low eases out.
 if(u<0.5){
  const double exponent=1.0+2.0*clamp01(easeHigh/100.0);
  return 0.5*std::pow(2.0*u,exponent);
 }
 const double exponent=1.0+2.0*clamp01(easeLow/100.0);
 return 1.0-0.5*std::pow(2.0*(1.0-u),exponent);
}
double rampWeight(double u,RampShape shape){
 switch(shape){
  case RampShape::Square:  return (u>=0.0&&u<=1.0)?1.0:0.0;
  case RampShape::Triangle:return std::max(0.0,1.0-std::fabs(u*2.0-1.0));
  case RampShape::RampUp:  return clamp01(u);
  case RampShape::RampDown:return clamp01(1.0-u);
  case RampShape::Smooth:  return smooth(u);
  case RampShape::Round:   {const double v=clamp01(u);return std::sqrt(std::max(0.0,1.0-(2.0*v-1.0)*(2.0*v-1.0)));}
 }
 return clamp01(u);
}
double animInfluence(const TextAnimator&a,double unit){
 // Start with every glyph selected/hidden. As the offset moves right, glyphs
 // behind the cursor leave the animator and become visible from left to right.
 const double sel=clamp01((unit-a.offset+a.edgeWidth)/(2.0*a.edgeWidth));
 return easeInOut(rampWeight(sel,a.shape),a.easeHigh,a.easeLow);
}

void drawDust(BLContext& c,int frame){
 for(uint32_t i=0;i<52;++i){uint32_t h=hash(i*0x9e3779b9u);double x=rnd(h)*W;
  double y=std::fmod(rnd(h^0xa51u)*H-frame*(.2+rnd(h^0x763u)*.7)+H*2,H);
  uint8_t a=uint8_t(4+rnd(h^0x114u)*14);double r=.45+rnd(h^0x62u)*.8;
  c.setFillStyle(BLRgba32(207,202,192,a));c.fillCircle(x,y,r);
 }
}
void drawRule(BLContext& c,int frame,double alpha){
 constexpr double y0=544;BLPath p;p.moveTo(0,y0);
 for(int x=0;x<=W;x+=6){double n=(rnd(uint32_t(x*31+frame/5))-.5)*.32+std::sin(x*.018)*.12;p.lineTo(x,y0+n);}
 c.setStrokeStyle(BLRgba32(240,232,211,uint8_t(30*alpha)));c.setStrokeWidth(11);c.strokePath(p);
 c.setStrokeStyle(BLRgba32(252,250,247,uint8_t(255*alpha)));c.setStrokeWidth(4.5);c.strokePath(p);
}
void drawGlowText(BLContext& c,const BLFont& font,const char* text,double centerX,double baseline,double alpha,double glowStrength){
 BLGlyphBuffer gb;gb.setUtf8Text(text,std::strlen(text));font.shape(gb);BLTextMetrics m;font.getTextMetrics(gb,m);double x=centerX-m.advance.x*.5;
 // The broad halo is a separate field; this short tight pass only softens the edge.
 for(int r=12;r>=1;--r){const double u=double(r)/12.0;
  const uint8_t a=uint8_t((0.22+1.5*(1.0-u))*alpha*glowStrength);
  c.setFillStyle(BLRgba32(216,178,52,a));
  for(int k=0;k<6;++k){double angle=k*6.28318530718/6.0;
   c.fillUtf8Text(BLPoint(x+std::cos(angle)*r,baseline+std::sin(angle)*r*.62),font,text,std::strlen(text));}}
 c.setFillStyle(BLRgba32(234,202,98,uint8_t(255*alpha)));c.fillUtf8Text(BLPoint(x,baseline),font,text,std::strlen(text));
}

// Per-glyph layout: shaped once as a whole string so advances and kerning are
// the real ones; each glyph can then carry its own animator influence.
struct GlyphPos{unsigned first;double x;double adv;double unit;};
std::pair<std::vector<GlyphPos>,double> layoutGlyphs(const BLFont& font,const char* text){
 // Shape every prefix with Blend2D and use its cumulative advances. This
 // preserves the exact kerning of the complete phrase while still exposing
 // each character position to the range selector.
 std::vector<GlyphPos> out;const size_t n=std::strlen(text);out.reserve(n);
 std::string prefix;prefix.reserve(n);double previous=0.0;
 for(size_t i=0;i<n;++i){
  prefix.push_back(text[i]);BLGlyphBuffer gb;gb.setUtf8Text(prefix.c_str(),prefix.size());font.shape(gb);
  BLTextMetrics metrics;font.getTextMetrics(gb,metrics);const double current=metrics.advance.x;
  GlyphPos g;g.first=text[i]==' '?~0u:unsigned(i);g.x=previous;g.adv=current-previous;
  g.unit=n>1?double(i)/double(n-1):0.5;out.push_back(g);previous=current;
 }
 return {out,previous};
}

// One glyph at its animated position: shadow stack, wide halo, tight glow, core.
void drawGlyphAt(BLContext& p,const BLFont& font,const char* glyphUtf8,double gx,double gy,double scx,double scy,double alpha,double glowPulse){
 auto drawAt=[&](double px,double py,double sc){
  p.save();p.translate(px,py);p.scale(sc,sc);
  p.fillUtf8Text(BLPoint(0,0),font,glyphUtf8,std::strlen(glyphUtf8));p.restore();};
 for(int d=6;d>=1;--d){
  p.setFillStyle(BLRgba32(91,68,18,uint8_t(210*alpha)));
  drawAt(gx+0.86*d*scx,gy+0.48*d*scy,scx);}
 for(int r=12;r>=1;--r){const double u=double(r)/12.0;
  const uint8_t a=uint8_t((0.22+1.5*(1.0-u))*alpha*glowPulse);
  p.setFillStyle(BLRgba32(216,178,52,a));
  for(int k=0;k<6;++k){double angle=k*6.28318530718/6.0;
   drawAt(gx+std::cos(angle)*r,gy+std::sin(angle)*r*.62,scx);}}
 p.setFillStyle(BLRgba32(234,202,98,uint8_t(255*alpha)));
 drawAt(gx,gy,scx);
}

// The divider, year, headline and its light are one animated overlay. They share
// the same reveal/exit timing so no typography layer drifts independently.
void drawAnimatedTitleOverlay(BLContext& c,int frame,double t,double alpha,double exit,const CameraSample& camera,const BLFontFace& regular,const BLFontFace& titleFace){
 const double glowPulse=.92+.08*(.5+.5*std::sin(t*4.2));
 // Render the complete typographic group to one transparent plane, then map
 // narrow vertical strips through a pinhole camera. This produces a real
 // projective keystone (near/far edges have different scale), not a 2D scale.
 BLImage titlePlane(W,H,BL_FORMAT_PRGB32);BLContext p(titlePlane);p.clearAll();
 BLFont year;year.createFromFace(regular,61);BLFont title;title.createFromFace(titleFace,74);
 const char* yearText="2019";const char* titleText="THE INVESTIGATION BEGINS";
 BLGlyphBuffer yb;yb.setUtf8Text(yearText,4);year.shape(yb);BLTextMetrics ym;year.getTextMetrics(yb,ym);
 BLGlyphBuffer tb;tb.setUtf8Text(titleText,std::strlen(titleText));title.shape(tb);BLTextMetrics tm;title.getTextMetrics(tb,tm);
 const double yearY=637+1.4*std::sin(t*2.2);
 // Diffuse olive-gold light surrounds the whole phrase, as in the film source.
 BLGradient halo(BLRadialGradientValues(960,708,960,708,460,0));
 halo.addStop(0,BLRgba32(118,108,30,uint8_t(150*alpha*glowPulse)));
 halo.addStop(.48,BLRgba32(110,100,24,uint8_t(92*alpha*glowPulse)));
 halo.addStop(1,BLRgba32(86,80,8,0));
 p.save();p.translate(960,708);p.scale(1.85,.72);p.translate(-960,-708);
 p.setFillStyle(halo);p.fillCircle(960,708,460);p.restore();
 const double side= camera.yaw>=0 ? -1.0 : 1.0;
 // --- Text animators: range selector + ramp shape + easing, per character.
 TextAnimator yearAnim, titleAnim;
 yearAnim.startY=26.0;yearAnim.scaleX=yearAnim.scaleY=0.86;
 yearAnim.offset=-0.12;titleAnim.offset=-0.12;
 const auto [yearGlyphs,yearW]=layoutGlyphs(year,yearText);
 const auto [titleGlyphs,titleW]=layoutGlyphs(title,titleText);
 const double yearX0=960.0-yearW*.5, titleX0=960.0-titleW*.5;
 // Exit: the group drifts up-left and out, the same way the reference clears.
 // Exit: `exit` is what is left of the group (1 = fully there), so the
 // clearing drift grows as it drops to zero.
 const double exitE=1.0-smooth(clamp01(exit));
 const double exitDX=-110.0*exitE, exitDY=-26.0*exitE, exitScale=1.0-0.07*exitE;
 // Motion blur: the glyph reveals are sampled across a shutter, so the
 // characters smear while they travel instead of jumping between frames.
 constexpr int SUB=3;
 for(int s=0;s<SUB;++s){
  const double ft=frame+(double(s)/double(SUB)-0.5)*0.5;
  const double glowP=.92+.08*(.5+.5*std::sin(ft/FPS*4.2));
  TextAnimator ya=yearAnim,ta=titleAnim;
 ya.offset=-0.12+1.24*easeInOut(clamp01((ft-2.0)/16.0),0.0,100.0);
 ta.offset=-0.12+1.24*easeInOut(clamp01((ft-7.0)/26.0),0.0,100.0);
  for(const GlyphPos& g:yearGlyphs){
   if(g.first==~0u)continue;
   const double inf=animInfluence(ya,g.unit),visible=1.0-inf;
   const double gy=yearY+ya.startY*inf+exitDY;
   const double gx=yearX0+g.x+side*1.6*inf+exitDX;
   const double sc=1.0+(ya.scaleX-1.0)*inf;
   char utf8[5];unsigned cp=0;const char* s2=yearText+g.first;unsigned char c=unsigned char(*s2);
   if(c<0x80){cp=c;utf8[0]=char(c);utf8[1]=0;}else{utf8[0]=s2[0];utf8[1]=s2[1];utf8[2]=0;}
   const double glyphAlpha=shutterSampleAlpha(alpha*visible,SUB);
   p.setFillStyle(BLRgba32(91,75,36,uint8_t(155*glyphAlpha)));
   for(int d=5;d>=1;--d){p.save();p.translate(gx+0.72*d*sc,gy+0.38*d*sc);p.scale(sc*exitScale,sc*exitScale);p.fillUtf8Text(BLPoint(0,0),year,utf8,utf8[1]?2:1);p.restore();}
   p.save();p.translate(gx,gy);p.scale(sc*exitScale,sc*exitScale);
   p.setFillStyle(BLRgba32(250,249,246,uint8_t(255*glyphAlpha)));
   p.fillUtf8Text(BLPoint(0,0),year,utf8,utf8[1]?2:1);p.restore();}
  for(const GlyphPos& g:titleGlyphs){
   if(g.first==~0u)continue;
   const double inf=animInfluence(ta,g.unit),visible=1.0-inf;
   const double gy=729.0+ta.startY*inf+1.4*std::sin(t*2.2)+exitDY;
   const double gx=titleX0+g.x+side*2.6*inf+exitDX;
   const double sc=1.0+(ta.scaleX-1.0)*inf;
   char utf8[5];const char* s2=titleText+g.first;unsigned char c=unsigned char(*s2);
   if(c<0x80){utf8[0]=char(c);utf8[1]=0;}else{utf8[0]=s2[0];utf8[1]=s2[1];utf8[2]=s2[2]?s2[2]:0;utf8[3]=0;}
   drawGlyphAt(p,title,utf8,gx,gy,sc*exitScale,sc*exitScale,shutterSampleAlpha(alpha*visible,SUB),glowP);}
 }
 p.end();
 // 3D camera: a slow push-in on top of the sampled orbit, so the group keeps
 // growing in perspective instead of sitting on a fixed plane.
 const double push=easeInOut(clamp01(double(frame)/double(FRAMES-1)),25.0,75.0);
 const double focal=double(H)/(2.0*std::tan(camera.fov*0.00872664626))*(1.0+0.04*push);
 const double distance=std::max(1.0,(camera.z+90.0)*(1.0-0.035*push)),yaw=-camera.yaw;
 const double cs=std::cos(yaw),sn=std::sin(yaw);
 constexpr int STRIP=4;
 for(int sx=0;sx<W;sx+=STRIP){
  const double sw=std::min(STRIP,W-sx),mx=sx+sw*.5-960.0;
  const double depth=std::max(1.0,distance+sn*mx);
  const double localScale=focal/depth;
  const auto projectX=[&](double x){return 960.0+focal*cs*x/std::max(1.0,distance+sn*x);};
  const double left=projectX(sx-960.0)-.45,right=projectX(sx+sw-960.0)+.45;
  const double centerY=540.0;
  const double top=centerY+(0.0-540.0)*localScale,bottom=centerY+(1080.0-540.0)*localScale;
  c.blitImage(BLRect(left,top,right-left,bottom-top),titlePlane,BLRectI(sx,0,int(sw),H));
 }
}

BLImage makeFrame(const BLImage& photo,const BLImage& card,const std::vector<CameraSample>& cameraSamples,const BLFontFace& regular,const BLFontFace& medium,int frame){
 const double t=double(frame)/FPS;BLImage image(W,H,BL_FORMAT_PRGB32);BLContext c(image);c.clearAll();
 c.setFillStyle(BLRgba32(2,2,4));c.fillRect(BLRect(0,0,W,H));
 BLGradient backgroundLift(BLRadialGradientValues(960,340,960,340,900,10));backgroundLift.addStop(0,BLRgba32(27,26,27,34));backgroundLift.addStop(1,BLRgba32(0,0,0,0));c.setFillStyle(backgroundLift);c.fillRect(BLRect(0,0,W,H));
 const CameraSample& pose=cameraSamples.at(static_cast<size_t>(frame));
 const double photoExit=1.0-smooth((t-2.12)/.36),titleExit=1.0-smooth((t-2.18)/.38);
 const auto photoTransform=cameraTransform(pose,0.0);
 c.save();c.translate(photoTransform.x,photoTransform.y);c.scale(photoTransform.scaleX,photoTransform.scale);c.translate(-960.0,-540.0);
 c.setGlobalAlpha(photoExit);
 const double reveal=.48+.52*smooth(t/.46);
 const double photoHeight=438.0,photoWidth=788.0,photoLeft=566.0,photoBottom=535.0;
 c.clipToRect(BLRect(photoLeft,photoBottom-photoHeight*reveal,photoWidth,photoHeight*reveal));
 c.blitImage(BLRect(photoLeft,photoBottom-photoHeight,photoWidth,photoHeight),photo);
 c.restore();
 c.save();c.translate(photoTransform.x,photoTransform.y);c.scale(photoTransform.scaleX,photoTransform.scale);c.translate(-960.0,-540.0);
 c.setGlobalAlpha(1.0);c.restore();
 const double titleAlpha=.94+.06*std::sin(t*3.1);
 drawAnimatedTitleOverlay(c,frame,t,titleAlpha*titleExit,titleExit,pose,regular,regular);
 drawRule(c,frame,photoExit);
 // A small archival video card enters from below as the first title scene clears.
 const double cardIn=smooth((t-2.27)/.55);if(cardIn>0){
  const BLRect cardRect(670,690,580,342);const double scale=.88+.12*cardIn;
  c.save();c.translate(960,855);c.scale(scale,scale);c.translate(-960,-855);
  BLGradient glow(BLRadialGradientValues(960,858,960,858,430,40));glow.addStop(0,BLRgba32(77,31,23,uint8_t(31*cardIn)));glow.addStop(1,BLRgba32(0,0,0,0));c.setFillStyle(glow);c.fillRect(BLRect(540,610,840,480));
  c.setGlobalAlpha(cardIn);c.blitImage(cardRect,card);c.setGlobalAlpha(1);c.restore();
 }
 drawDust(c,frame);
 BLGradient vignette(BLRadialGradientValues(960,520,960,520,1240,180));vignette.addStop(0,BLRgba32(0,0,0,0));vignette.addStop(.78,BLRgba32(0,0,0,26));vignette.addStop(1,BLRgba32(0,0,0,125));c.setFillStyle(vignette);c.fillRect(BLRect(0,0,W,H));
 c.end();return image;
}

int main(){try{
 fs::create_directories(OUTPUT_DIR);BLImage photo,card;
 if(photo.readFromFile((ASSET_DIR/L"reference_article_crop.png").string().c_str())!=BL_SUCCESS)throw std::runtime_error("Could not load clean reference portrait");
 if(card.readFromFile((ASSET_DIR/L"reference_card_crop.png").string().c_str())!=BL_SUCCESS)throw std::runtime_error("Could not load cropped reference card");
 BLFontFace regular,medium;if(regular.createFromFile((FONT_DIR/L"Oswald.ttf").string().c_str())!=BL_SUCCESS||medium.createFromFile((FONT_DIR/L"Oswald-Medium.ttf").string().c_str())!=BL_SUCCESS)throw std::runtime_error("Could not load Oswald fonts");
 const auto cameraSamples=readCameraSamples();
 const fs::path target=OUTPUT_DIR/L"Rapdaily_Archive_Title_Sequence_1920x1080.mp4";
 std::string cmd="ffmpeg.exe -y -v error -f rawvideo -pixel_format bgra -video_size 1920x1080 -framerate 30 -i - -an -c:v h264_nvenc -preset p5 -tune hq -cq 19 -pix_fmt yuv420p -movflags +faststart \""+target.string()+"\"";
 FILE* pipe=_popen(cmd.c_str(),"wb");if(!pipe)throw std::runtime_error("Could not start FFmpeg NVENC");bool ok=true;
 for(int f=0;f<FRAMES;++f){BLImage frame=makeFrame(photo,card,cameraSamples,regular,medium,f);BLImageData d{};frame.getData(&d);const auto* bytes=static_cast<const uint8_t*>(d.pixelData);for(int y=0;y<H;++y)if(std::fwrite(bytes+y*d.stride,1,W*4,pipe)!=size_t(W*4)){ok=false;break;}if(!ok)break;}
 int rc=_pclose(pipe);if(!ok||rc!=0)throw std::runtime_error("Encoding failed");std::cout<<"Rendered "<<target.string()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
