// Single archival essay motion sample based on the supplied screenshot.
// C++ / Blend2D frame generation with direct NVIDIA NVENC encoding.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <blend2d.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <queue>
#include <vector>
#include <iostream>

namespace fs=std::filesystem;
constexpr int W=1920,H=1080,FPS=30,FRAMES=150;
constexpr double PI=3.14159265358979323846;
const fs::path ROOT=L"C:/Users/pater/Pyt";
const fs::path OUTPUT_DIR=ROOT/L"ChrononTemplate/out/bullet_families/refined_single";
const fs::path FONT_DIR=ROOT/L"ChrononTemplate/assets/fonts";
const fs::path HEADLINE_FONT=ROOT/L"ChrononTemplate/catalog/vintage_documentary_title_01/assets/Anton.ttf";
const fs::path REFERENCE=L"C:/Users/pater/OneDrive/Immagini/Catture di schermata/Screenshot 2026-10-25 at 12-22-41 Unsettling Conspiracies That Turned Out True - YouTube.png";

double clamp01(double x){return std::clamp(x,0.0,1.0);}
double smooth(double x){x=clamp01(x);return x*x*(3-2*x);}
uint32_t hash(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
double rnd(uint32_t x){return double(hash(x))/double(0xffffffffu);}

BLImage cropReference(){
 BLImage source;if(source.readFromFile(REFERENCE.string().c_str())!=BL_SUCCESS)throw std::runtime_error("Cannot read supplied reference image");
 BLImage crop(786,442,BL_FORMAT_PRGB32);BLContext c(crop);c.clearAll();
 // Crop tightly around the newspaper. Remove only near-black pixels connected to
 // the crop boundary, which cuts away the screenshot's black matte while keeping
 // dark ink and the photograph inside the paper.
 c.blitImage(BLPoint(-537,-82),source);c.end();return crop;
}

BLImage cutPaper(const BLImage& input){
 BLImage out(786,442,BL_FORMAT_PRGB32);BLImageData s{},d{};input.getData(&s);out.getData(&d);
 const int w=786,h=442;std::vector<uint8_t> outside(size_t(w)*h,0);std::queue<int> q;
 const auto* srcPixels=static_cast<const uint8_t*>(s.pixelData);auto* dstPixels=static_cast<uint8_t*>(d.pixelData);
 auto dark=[&](int x,int y){const auto* p=srcPixels+y*s.stride+x*4;return p[0]<36&&p[1]<36&&p[2]<36;};
 auto add=[&](int x,int y){int k=y*w+x;if(!outside[k]&&dark(x,y)){outside[k]=1;q.push(k);}};
 for(int x=0;x<w;++x){add(x,0);add(x,h-1);}for(int y=0;y<h;++y){add(0,y);add(w-1,y);}
 while(!q.empty()){int k=q.front();q.pop();int x=k%w,y=k/w;if(x)add(x-1,y);if(x+1<w)add(x+1,y);if(y)add(x,y-1);if(y+1<h)add(x,y+1);}
 for(int y=0;y<h;++y)for(int x=0;x<w;++x){auto* p=dstPixels+y*d.stride+x*4;const auto* a=srcPixels+y*s.stride+x*4;
   const double lift=1.13;for(int k=0;k<3;++k)p[k]=uint8_t(std::min(255.0,a[k]*lift+2));
   // The supplied screenshot's matte has a few gray pixels at the crop bounds;
   // taper those away so no straight screenshot edge survives the extraction.
   double edge=std::min({double(x)-5.0,double(w-1-x)-5.0,double(y)-4.0,double(h-1-y)-4.0});
   double alpha=clamp01(edge/5.0);p[3]=(outside[size_t(y)*w+x]?0:uint8_t(255*alpha));}
 return out;
}

void drawRule(BLContext& c,double reveal,int frame){
constexpr double baseY=520;BLPath path;path.moveTo(0,baseY);
 for(int x=3;x<=W;x+=3){double n=(rnd(uint32_t(x*13+frame/5))-.5)*2.4+std::sin(x*.071)*.48;path.lineTo(x,baseY+n);}
 c.save();c.clipToRect(BLRect(0,baseY-24,W*clamp01(reveal),48));
 c.setStrokeStyle(BLRgba32(235,232,226,28));c.setStrokeWidth(11);c.strokePath(path);
 c.setStrokeStyle(BLRgba32(245,243,238,250));c.setStrokeWidth(3.1);c.strokePath(path);
 // Fine broken fibers make the separator read as torn paper instead of a UI rule.
 for(int i=0;i<70;++i){uint32_t h=hash(uint32_t(i*71+frame/7));double x=rnd(h)*W,y=baseY+(rnd(h^0x65a1u)-.5)*11;
  c.setStrokeStyle(BLRgba32(230,224,210,uint8_t(22+rnd(h^0xb351u)*36)));c.setStrokeWidth(.6+rnd(h^0x91u));c.strokeLine(BLPoint(x,y),BLPoint(x+2+rnd(h^0x753u)*10,y+(rnd(h^0x331u)-.5)*2));}
 c.restore();
}

void drawDust(BLContext& c,int frame){
 for(uint32_t i=0;i<360;++i){uint32_t h=hash(uint32_t(frame)*0x9e3779b9u+i*0x85ebca6bu);double x=rnd(h)*W,y=rnd(h^0xa511e9b3u)*H;
  uint8_t a=uint8_t(8+rnd(h^0x63d83595u)*43);double r=rnd(h^0xb5297a4du)<.96?.55:1.4;
  c.setFillStyle(BLRgba32(220,214,200,a));c.fillCircle(x,y,r);}
 for(int i=0;i<4;++i){uint32_t h=hash(uint32_t(frame/2)*41u+uint32_t(i)*79u);if((h&3u)!=0)continue;double x=rnd(h)*W,y=rnd(h^0xa511u)*H,len=9+rnd(h^0x5u)*35;
  c.setStrokeStyle(BLRgba32(210,203,187,20));c.setStrokeWidth(.65);c.strokeLine(BLPoint(x,y),BLPoint(x+len,y+len*.16));}
}

void drawHalftone(BLContext& c,double alpha,int frame){
 // Low-contrast, frame-stable print dots over the archive image; restrained enough to retain its source detail.
 c.save();c.clipToRect(BLRect(449,44,1022,575));
 for(int y=48;y<615;y+=9)for(int x=452;x<1470;x+=9){double jitter=(rnd(hash(uint32_t(x*31+y*17)))-.5)*1.4;
   c.setFillStyle(BLRgba32(19,16,12,uint8_t(12*alpha)));c.fillCircle(x+jitter,y+jitter,0.72);}
 c.restore();
}

BLImage makeFrame(const BLImage& paper,const BLFontFace& titleFace,const BLFontFace& serifFace,int frame){
 const double t=double(frame)/FPS,photoIn=smooth((t-.10)/.44),zoom=1.0+.015*clamp01(t/5.0);
 const double shakeX=.7*std::sin(t*2*PI*1.35),shakeY=.55*std::sin(t*2*PI*1.8+.7);
 BLImage image(W,H,BL_FORMAT_PRGB32);BLContext c(image);c.clearAll();c.setFillStyle(BLRgba32(1,1,2));c.fillRect(BLRect(0,0,W,H));
 c.save();c.translate(W*.5,H*.5);c.scale(zoom);c.translate(-W*.5,-H*.5);c.translate(shakeX,shakeY);
 // Stronger archive vignette with a soft lift behind the newspaper.
 BLGradient lift(BLRadialGradientValues(960,330,960,330,740,10));lift.addStop(0,BLRgba32(31,29,26,28));lift.addStop(.66,BLRgba32(10,9,8,16));lift.addStop(1,BLRgba32(0,0,0,0));c.setFillStyle(lift);c.fillRect(BLRect(0,0,W,H));
 // Center the clipping naturally against the divider; retain breathing room above.
 const BLRect dest(550,87,775,434);
 // Keep the shadow restrained and contained under the torn lower edge, avoiding a rectangular matte.
 BLPath paperShadow;paperShadow.moveTo(dest.x+8,dest.y+dest.h-2);paperShadow.lineTo(dest.x+dest.w*.28,dest.y+dest.h+3);paperShadow.lineTo(dest.x+dest.w*.67,dest.y+dest.h+2);paperShadow.lineTo(dest.x+dest.w-8,dest.y+dest.h-2);
 c.setStrokeStyle(BLRgba32(0,0,0,uint8_t(110*photoIn)));c.setStrokeWidth(12);c.strokePath(paperShadow);
 c.setGlobalAlpha(photoIn);c.blitImage(dest,paper);c.setGlobalAlpha(1.0);
 c.setFillStyle(BLRgba32(225,218,202,uint8_t(12*photoIn)));c.fillRect(dest);
 drawHalftone(c,photoIn,frame);

 const double ruleIn=smooth((t-.54)/.42);drawRule(c,ruleIn,frame);
 BLFont year;year.createFromFace(serifFace,74);
 BLFont headline;headline.createFromFace(titleFace,86);
 const std::string yearText="1971",headlineText="EXPOSED BY THE MEDIA";
 const double yearIn=smooth((t-.88)/.48),titleIn=smooth((t-1.24)/.72);
 const double yearW=[&](){BLGlyphBuffer b;b.setUtf8Text(yearText.c_str(),yearText.size());year.shape(b);BLTextMetrics m;year.getTextMetrics(b,m);return m.advance.x;}();
 BLRgba32 yearInk(255,255,253,uint8_t(255*yearIn));
 c.setFillStyle(BLRgba32(3,3,3,uint8_t(160*yearIn)));c.fillUtf8Text(BLPoint(960-yearW*.5+1.5,616+2),year,yearText.c_str(),yearText.size());
 c.setFillStyle(yearInk);c.fillUtf8Text(BLPoint(960-yearW*.5,616),year,yearText.c_str(),yearText.size());
 BLGlyphBuffer hb;hb.setUtf8Text(headlineText.c_str(),headlineText.size());headline.shape(hb);BLTextMetrics hm;headline.getTextMetrics(hb,hm);const double titleX=960-hm.advance.x*.5;
 // Irregular, desaturated brick-red marker behind the words, wiped on with the title.
 const double squeeze=.86;
 BLPath marker;marker.moveTo(titleX-31,661);marker.lineTo(titleX+15,654);marker.lineTo(titleX+hm.advance.x+34,659);marker.lineTo(titleX+hm.advance.x+39,716);marker.lineTo(titleX-37,721);marker.lineTo(titleX-34,688);marker.close();
 // Dry brush edges and a feathered moving reveal, while the final stroke remains behind the full title.
 c.save();c.translate(960,0);c.scale(squeeze,1);c.translate(-960,0);
 c.setFillStyle(BLRgba32(42,5,5,uint8_t(145*titleIn)));c.fillPath(marker);
 for(int i=0;i<32;++i){uint32_t h=hash(uint32_t(i*97));double x=titleX-25+rnd(h)*(hm.advance.x+50),y=687+(rnd(h^0x511u)-.5)*45;
   c.setStrokeStyle(BLRgba32(70,12,12,uint8_t(25*titleIn)));c.setStrokeWidth(.8+rnd(h^0x312u)*2.2);c.strokeLine(BLPoint(x,y),BLPoint(x+5+rnd(h^0x91u)*27,y+(rnd(h^0x71u)-.5)*2));}
 c.setFillStyle(BLRgba32(35,14,11,uint8_t(160*titleIn)));c.fillUtf8Text(BLPoint(titleX+2,710+3),headline,headlineText.c_str(),headlineText.size());
 BLGradient gold(BLLinearGradientValues(0,640,0,712));gold.addStop(0,BLRgba32(238,205,120,uint8_t(255*titleIn)));gold.addStop(.52,BLRgba32(192,151,67,uint8_t(255*titleIn)));gold.addStop(1,BLRgba32(120,83,37,uint8_t(255*titleIn)));
 c.setFillStyle(gold);c.fillUtf8Text(BLPoint(titleX,710),headline,headlineText.c_str(),headlineText.size());
 c.restore();
 c.restore();
 // Film texture is screen-fixed and changes every frame, over the complete image.
 drawDust(c,frame);
 BLGradient vignette(BLRadialGradientValues(960,520,960,520,1220,250));vignette.addStop(0,BLRgba32(0,0,0,0));vignette.addStop(.72,BLRgba32(0,0,0,18));vignette.addStop(1,BLRgba32(0,0,0,190));c.setFillStyle(vignette);c.fillRect(BLRect(0,0,W,H));
 c.end();return image;
}

int main(){try{
 fs::create_directories(OUTPUT_DIR);BLImage paper=cutPaper(cropReference());BLFontFace titleFace,serifFace;
 if(titleFace.createFromFile((FONT_DIR/L"Oswald-Bold.ttf").string().c_str())!=BL_SUCCESS||serifFace.createFromFile((FONT_DIR/L"Oswald.ttf").string().c_str())!=BL_SUCCESS)throw std::runtime_error("Could not load title fonts");
 const fs::path target=OUTPUT_DIR/L"ArchiveEssay_1971_1920x1080.mp4";
 std::string cmd="ffmpeg.exe -y -v error -f rawvideo -pixel_format bgra -video_size 1920x1080 -framerate 30 -i - -an -c:v h264_nvenc -preset p5 -tune hq -cq 19 -pix_fmt yuv420p -movflags +faststart \""+target.string()+"\"";
 FILE* pipe=_popen(cmd.c_str(),"wb");if(!pipe)throw std::runtime_error("Could not start FFmpeg NVENC");bool ok=true;
 for(int f=0;f<FRAMES;++f){BLImage frame=makeFrame(paper,titleFace,serifFace,f);BLImageData d{};frame.getData(&d);const auto* bytes=static_cast<const uint8_t*>(d.pixelData);for(int y=0;y<H;++y)if(std::fwrite(bytes+y*d.stride,1,W*4,pipe)!=size_t(W*4)){ok=false;break;}if(!ok)break;}
 int rc=_pclose(pipe);if(!ok||rc!=0)throw std::runtime_error("Encoding failed");
 std::cout<<"Rendered "<<target.string()<<"\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
