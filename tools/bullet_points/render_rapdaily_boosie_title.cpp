// Rapdaily title animation recreation from the supplied frame. C++ / Blend2D + NVENC.
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
#include <iostream>

namespace fs=std::filesystem;
constexpr int W=1920,H=1080,FPS=30,FRAMES=150;
const fs::path ROOT=L"C:/Users/pater/Pyt";
const fs::path OUTPUT_DIR=ROOT/L"ChrononTemplate/out/bullet_families/rapdaily_single";
const fs::path FONT=ROOT/L"ChrononTemplate/assets/fonts/Oswald-Bold.ttf";
double clamp01(double x){return std::clamp(x,0.0,1.0);}
double smooth(double x){x=clamp01(x);return x*x*(3-2*x);}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
double rnd(uint32_t x){return double(hash(x))/double(0xffffffffu);}

void drawEmbers(BLContext& c,int frame){
 c.setFillStyle(BLRgba32(8,7,12));c.fillRect(BLRect(0,0,W,H));
 BLGradient haze(BLRadialGradientValues(960,520,960,520,1050,10));haze.addStop(0,BLRgba32(13,10,17,35));haze.addStop(1,BLRgba32(0,0,0,0));c.setFillStyle(haze);c.fillRect(BLRect(0,0,W,H));
 for(uint32_t i=0;i<290;++i){uint32_t h=hash(i*0x9e3779b9u);double x=rnd(h)*W,base=rnd(h^0xa51u)*H;
   double y=std::fmod(base-frame*(.35+rnd(h^0x762u)*1.1)+H*2,H);double cluster=std::min(x,double(W)-x);
   double edgeFade=clamp01((cluster-120)/370.0);double alpha=(8+rnd(h^0x118u)*85)*edgeFade;
   if(rnd(h^0x633u)<.20){alpha*=.35;}
   double r=.45+rnd(h^0x49u)*1.6;uint8_t rr=uint8_t(130+rnd(h^0x93u)*115),gg=uint8_t(35+rnd(h^0x54u)*90);
   c.setFillStyle(BLRgba32(rr,gg,28,uint8_t(alpha)));c.fillCircle(x,y,r);
   if(rnd(h^0x222u)<.12){c.setStrokeStyle(BLRgba32(190,68,34,uint8_t(alpha*.32)));c.setStrokeWidth(.65);c.strokeLine(BLPoint(x,y),BLPoint(x+1.5,y-5-rnd(h^0x13u)*12));}
 }
 BLGradient vig(BLRadialGradientValues(960,520,960,520,1230,260));vig.addStop(0,BLRgba32(0,0,0,0));vig.addStop(.78,BLRgba32(0,0,0,35));vig.addStop(1,BLRgba32(0,0,0,115));c.setFillStyle(vig);c.fillRect(BLRect(0,0,W,H));
}

BLImage makeFrame(const BLFontFace& face,int frame){
 const double t=double(frame)/FPS,enter=smooth((t-.12)/.65),zoom=1.0+.015*t/5.0;
 BLImage image(W,H,BL_FORMAT_PRGB32);BLContext c(image);drawEmbers(c,frame);
 BLFont font;font.createFromFace(face,142);
 const char* lines[]={"BOOSIE'S SON AT THE CENTER","OF THE BATON ROUGE CASE!"};
 BLGlyphBuffer gb[2];BLTextMetrics m[2];double maxW=0;
 for(int i=0;i<2;++i){gb[i].setUtf8Text(lines[i],std::strlen(lines[i]));font.shape(gb[i]);font.getTextMetrics(gb[i],m[i]);maxW=std::max(maxW,m[i].advance.x);}
 double squeeze=std::min(.93,1650.0/maxW);double midY=540;double scale=zoom;
 c.save();c.translate(W*.5,midY);c.scale(scale,scale);c.translate(-W*.5,-midY);
 for(int i=0;i<2;++i){double y=520+i*190;double x=W*.5-m[i].advance.x*.5;
   // Layered soft gray passes build a restrained bloom without a hard outline.
   for(int radius=5;radius>=1;--radius){uint8_t a=uint8_t((7-radius)*3.5*enter);c.setFillStyle(BLRgba32(231,231,236,a));
     for(int k=0;k<8;++k){double ang=k*0.785398163; c.fillUtf8Text(BLPoint(x+std::cos(ang)*radius*2,y+std::sin(ang)*radius*2),font,lines[i],std::strlen(lines[i]));}}
 }
 // Render bright glyphs to a small working surface; diagonal cuts are painted only
 // into glyph pixels, preserving the clean typographic silhouette.
 BLImage lettering(W,H,BL_FORMAT_PRGB32);BLContext tc(lettering);tc.clearAll();tc.setFillStyle(BLRgba32(255,255,255,uint8_t(255*enter)));
 for(int i=0;i<2;++i){double y=520+i*190;double x=W*.5-m[i].advance.x*.5;tc.save();tc.translate(W*.5,0);tc.scale(squeeze,1);tc.translate(-W*.5,0);tc.fillUtf8Text(BLPoint(x,y),font,lines[i],std::strlen(lines[i]));tc.restore();}
 tc.end();BLImageData ld{};lettering.getData(&ld);auto* px=static_cast<uint8_t*>(ld.pixelData);
 for(int y=0;y<H;++y)for(int x=0;x<W;++x){uint8_t* p=px+y*ld.stride+x*4;if(p[3]&&((x+y)%13)<3){p[0]=p[1]=p[2]=uint8_t(p[0]*.78);}}
 c.blitImage(BLPoint(0,0),lettering);
 c.restore();c.end();return image;
}

int main(){try{
 fs::create_directories(OUTPUT_DIR);BLFontFace face;if(face.createFromFile(FONT.string().c_str())!=BL_SUCCESS)throw std::runtime_error("Could not load Oswald Bold font");
 const fs::path target=OUTPUT_DIR/L"Rapdaily_Boosie_Title_1920x1080.mp4";
 std::string cmd="ffmpeg.exe -y -v error -f rawvideo -pixel_format bgra -video_size 1920x1080 -framerate 30 -i - -an -c:v h264_nvenc -preset p5 -tune hq -cq 19 -pix_fmt yuv420p -movflags +faststart \""+target.string()+"\"";
 FILE* pipe=_popen(cmd.c_str(),"wb");if(!pipe)throw std::runtime_error("Could not start FFmpeg NVENC");bool ok=true;
 for(int f=0;f<FRAMES;++f){BLImage frame=makeFrame(face,f);BLImageData d{};frame.getData(&d);const auto* bytes=static_cast<const uint8_t*>(d.pixelData);for(int y=0;y<H;++y)if(std::fwrite(bytes+y*d.stride,1,W*4,pipe)!=size_t(W*4)){ok=false;break;}if(!ok)break;}
 int rc=_pclose(pipe);if(!ok||rc!=0)throw std::runtime_error("Encoding failed");std::cout<<"Rendered "<<target.string()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
