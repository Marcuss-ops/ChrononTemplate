// ChrononTemplate analog video-essay bullet families.
// Native Blend2D drawing, image-plane moves and direct NVIDIA NVENC encoding.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <blend2d.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
constexpr int W=1920, H=1080, FPS=30, FRAMES=150;
constexpr double PI=3.14159265358979323846;
const fs::path ROOT=L"C:/Users/pater/Pyt";
const fs::path OUTPUT_DIR=ROOT/L"ChrononTemplate/out/bullet_families";
const fs::path FONTS=ROOT/L"Chronon3d/assets/fonts";
const fs::path REFERENCE=L"C:/Users/pater/OneDrive/Immagini/Catture di schermata/Screenshot 2026-10-25 at 12-22-41 Unsettling Conspiracies That Turned Out True - YouTube.png";

struct Clip { std::string family, slug; int index; double panX=0,panY=0,yaw=0,zoom=0; };
const std::array<Clip,10> RAP={{
 {"Rapdaily","pan_left_yaw_in",1,-70,0,-2.0,.035}, {"Rapdaily","pan_right_yaw_in",2,70,0,2.0,.035},
 {"Rapdaily","yaw_left_orbit",3,-44,-8,-3.0,.055}, {"Rapdaily","yaw_right_orbit",4,44,8,3.0,.055},
 {"Rapdaily","pan_up_tilt",5,0,-40,-1.0,.025}, {"Rapdaily","pan_down_tilt",6,0,40,1.0,.025},
 {"Rapdaily","dutch_yaw_left",7,-34,0,-4.0,.06}, {"Rapdaily","dutch_yaw_right",8,34,0,4.0,.06},
 {"Rapdaily","push_pan_combo",9,-54,-9,1.5,.075}, {"Rapdaily","pull_yaw_combo",10,54,9,-1.5,-.025}
}};
const std::array<std::string,15> TYPE={{"typewriter","fade_up","slide_left","slide_right","rise_reveal","scale_pop","word_cascade","letter_cascade","wipe_left","wipe_right","bounce_in","blur_resolve","line_by_line","glitch_snap","underline_reveal"}};
const std::array<std::string,15> APPLE={{"soft_fade","rise","slide_left","slide_right","scale_in","word_stagger","line_stagger","mask_reveal","blur_fade","gentle_pop","tracking_in","vertical_reveal","cascade","focus_shift","quiet_wipe"}};

double clamp01(double v){return std::clamp(v,0.0,1.0);}
double ease(double x){x=clamp01(x);return 1-std::pow(1-x,3);}
double smooth(double x){x=clamp01(x);return x*x*(3-2*x);}
uint32_t hash32(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
double rand01(uint32_t x){return double(hash32(x))/double(0xffffffffu);}

struct Fonts { BLFontFace headline,serif,small; };
bool loadFonts(Fonts& f){
 return f.headline.createFromFile((ROOT/L"ChrononTemplate/catalog/vintage_documentary_title_01/assets/Anton.ttf").string().c_str())==BL_SUCCESS &&
        f.serif.createFromFile((FONTS/L"FreeSerif.ttf").string().c_str())==BL_SUCCESS &&
        f.small.createFromFile((FONTS/L"Inter-Regular.ttf").string().c_str())==BL_SUCCESS;
}
BLFont font(const BLFontFace& face,double size){BLFont f;f.createFromFace(face,float(size));return f;}
double textWidth(const BLFont& f,const std::string& s){BLGlyphBuffer b;b.setUtf8Text(s.c_str(),s.size());f.shape(b);BLTextMetrics m;f.getTextMetrics(b,m);return m.advance.x;}
void text(BLContext& c,const BLFont& f,double x,double y,const std::string& s,BLRgba32 color){c.setFillStyle(color);c.fillUtf8Text(BLPoint(x,y),f,s.c_str(),s.size());}
std::string clipName(const std::string& family,int index,const std::string& slug){return family+"_"+(index<10?"0":"")+std::to_string(index)+"_"+slug+"_1920x1080.mp4";}

BLImage makeNewspaperCrop(){
 BLImage source;if(source.readFromFile(REFERENCE.string().c_str())!=BL_SUCCESS)throw std::runtime_error("Cannot load the supplied newspaper reference screenshot");
 BLImage crop(786,442,BL_FORMAT_PRGB32);BLContext c(crop);c.clearAll();
 // Keep only the torn archival frame from the supplied screenshot; exclude the player UI and captions.
 c.blitImage(BLPoint(-537,-82),source);c.end();return crop;
}

void drawFilm(BLContext& c,int frame){
 // Fine, frame-varying dust on a true black plate. Sparse and low contrast.
 for(uint32_t i=0;i<230;++i){uint32_t h=hash32(uint32_t(frame)*0x9e3779b9u+i*0x85ebca6bu);double x=rand01(h)*W,y=rand01(h^0xa511e9b3u)*H;uint8_t a=uint8_t(10+rand01(h^0x63d83595u)*34);double r=rand01(h^0xb5297a4du)<.94?0.65:1.25;c.setFillStyle(BLRgba32(218,214,202,a));c.fillCircle(x,y,r);}
 // Occasional hairline scratches, visible only when looked for.
 for(int i=0;i<3;++i){uint32_t h=hash32(uint32_t(frame/3)*29u+uint32_t(i)*313u);if((h&7u)!=0u)continue;double x=rand01(h)*W,y=rand01(h^0x68bc21ebu)*H;double len=5+rand01(h^0x02e5be93u)*30;c.setStrokeStyle(BLRgba32(210,204,190,18));c.setStrokeWidth(.7);c.strokeLine(BLPoint(x,y),BLPoint(x+len,y+len*.24));}
}

void drawRoughRule(BLContext& c,int frame){
 c.setStrokeStyle(BLRgba32(224,220,210,235));c.setStrokeWidth(4.0);
 BLPath path;path.moveTo(0,539);
 for(int x=0;x<=W;x+=80){double wobble=(rand01(hash32(uint32_t(x*7+frame/4)))-.5)*2.6;path.lineTo(x,539+wobble);}
 c.strokePath(path);
}

struct Motion {double x=0,y=0,scale=1,rotation=0,opacity=1;bool wipe=false;double wipeAmount=1;std::string shown;};
Motion evaluate(const std::string& style,const std::string& value,double p,bool title){
 Motion m;m.shown=value;double q=ease(p);
 if(style=="typewriter"&&title){int n=int(clamp01((p-.04)/.66)*value.size());m.shown=value.substr(0,n);m.opacity=n?1:0;return m;}
 if(style=="letter_cascade"&&title){int n=int(clamp01(p*1.3)*value.size());m.shown=value.substr(0,n);}
 if(style=="word_cascade"||style=="word_stagger"||style=="line_stagger"||style=="cascade"||style=="line_by_line")q=ease(p*.92);
 if(style=="slide_left")m.x=-240*(1-q);
 if(style=="slide_right")m.x=240*(1-q);
 if(style=="fade_up"||style=="rise"||style=="rise_reveal")m.y=74*(1-q);
 if(style=="vertical_reveal")m.y=-24*(1-q);
 if(style=="scale_pop"||style=="scale_in"||style=="gentle_pop")m.scale=.88+.12*q;
 if(style=="bounce_in")m.y=38*std::sin((1-q)*PI);
 if(style=="tracking_in")m.x=-18*(1-q);
 if(style=="glitch_snap")m.x=(int(p*54)%2?9:-9)*(1-q);
 if(style=="focus_shift"||style=="blur_resolve"||style=="blur_fade")m.scale=1.02-.02*q;
 if(style=="wipe_left"||style=="wipe_right"||style=="mask_reveal"||style=="quiet_wipe") {m.wipe=true;m.wipeAmount=q;}
 if(style=="soft_fade"||style=="fade_up"||style=="blur_fade"||style=="blur_resolve")m.opacity=q;
 return m;
}

void drawAnimatedText(BLContext& c,const BLFont& f,const std::string& style,const std::string& value,
                      double centerX,double baseline,double p,bool title,BLRgba32 color){
 Motion m=evaluate(style,value,p,title);if(m.opacity<.005||m.shown.empty())return;
 const double w=textWidth(f,m.shown),x=centerX-w*.5+m.x;uint8_t alpha=uint8_t(255*clamp01(m.opacity));
 c.save();c.translate(centerX,baseline);c.rotate(m.rotation*PI/180);c.scale(m.scale);c.translate(-centerX,-baseline);
 if(m.wipe){double visible=w*m.wipeAmount;double left=(style=="wipe_right")?x+w-visible:x;c.save();c.clipToRect(BLRect(left,baseline-105,visible+1,135));}
 BLRgba32 ink(color.r(),color.g(),color.b(),alpha);
 // A small warm shadow gives the lettering weight without a neon or bloom treatment.
 if(title){text(c,f,x+2,baseline+3,m.shown,BLRgba32(74,28,18,uint8_t(alpha*.55)));}
 text(c,f,x,baseline,m.shown,ink);
 if(m.wipe)c.restore();
 if(style=="underline_reveal"&&title){c.setStrokeStyle(BLRgba32(135,87,39,uint8_t(210*m.wipeAmount)));c.setStrokeWidth(2);c.strokeLine(BLPoint(centerX-w*.5,baseline+13),BLPoint(centerX-w*.5+w*clamp01(p),baseline+13));}
 c.restore();
}

BLImage renderFrame(const std::string& family,const std::string& style,const Clip* camera,
                    const BLImage& newspaper,const Fonts& faces,int frame){
 const double t=double(frame)/FPS;BLImage image(W,H,BL_FORMAT_PRGB32);BLContext c(image);c.clearAll();
 c.setFillStyle(BLRgba32(3,3,4));c.fillRect(BLRect(0,0,W,H));
 // Low contrast vignette and soft charcoal lift keep the black from looking digital-flat.
 BLGradient vignette(BLRadialGradientValues(W*.5,H*.44,W*.5,H*.44,W*.76,W*.16));
 vignette.addStop(0.0,BLRgba32(17,16,15,0));vignette.addStop(.72,BLRgba32(4,4,5,38));vignette.addStop(1.0,BLRgba32(0,0,1,176));
 c.setFillStyle(vignette);c.fillRect(BLRect(0,0,W,H));

 double photoProgress=smooth((t-.12)/.7),photoX=0,photoY=0,photoScale=1;
 if(camera){double drift=ease(t/5);photoX=camera->panX*(.52-drift);photoY=camera->panY*(.52-drift);photoScale=1+camera->zoom*std::sin(t*PI/5);}
 BLRect dest(567+photoX,83+photoY,786,442);
 c.save();c.translate(960+photoX,304+photoY);c.rotate(camera?camera->yaw*std::sin(t*PI/5)*PI/180:0);c.scale(photoScale);c.translate(-960-photoX,-304-photoY);
 c.setFillStyle(BLRgba32(75,70,63,uint8_t(130*photoProgress)));c.fillRect(BLRect(dest.x-4,dest.y+4,dest.w+8,dest.h+5));
 c.setGlobalAlpha(photoProgress);c.blitImage(dest,newspaper);c.setGlobalAlpha(1.0);c.restore();

 drawRoughRule(c,frame);
 const BLFont year=font(faces.serif,61),headline=font(faces.headline,88);
 const double yearP=clamp01((t-.82)/.85),titleP=clamp01((t-1.18)/1.02);
 const std::string yearText="1971",titleText="EXPOSED BY THE MEDIA";
 BLRgba32 yearInk(223,219,207,uint8_t(255*ease(yearP)));
 drawAnimatedText(c,year,style,yearText,W*.5,628,yearP,true,yearInk);
 drawAnimatedText(c,headline,style,titleText,W*.5,732,titleP,true,BLRgba32(189,155,69));
 // Print-like ink flecks inside the ochre title, deliberately subdued.
 if(titleP>.5){uint32_t seed=hash32(uint32_t(frame)*17u);for(int i=0;i<22;++i){seed=hash32(seed+i*41u);double x=525+rand01(seed)*870,y=660+rand01(seed^0xb5297a4du)*90;if(rand01(seed^0x68bc21ebu)>.64){c.setFillStyle(BLRgba32(15,13,9,46));c.fillRect(BLRect(x,y,1.0,1.0));}}}
 drawFilm(c,frame);
 c.end();return image;
}

std::string quote(const fs::path& p){return "\""+p.string()+"\"";}
void encode(const std::string& family,const std::string& slug,int index,const std::string& style,
            const Clip* camera,const BLImage& image,const Fonts& faces){
 fs::path out=OUTPUT_DIR/clipName(family,index,slug);
 std::string cmd="ffmpeg.exe -y -v error -f rawvideo -pixel_format bgra -video_size 1920x1080 -framerate 30 -i - -an -c:v h264_nvenc -preset p5 -tune hq -cq 19 -pix_fmt yuv420p -movflags +faststart "+quote(out);
 FILE* pipe=_popen(cmd.c_str(),"wb");if(!pipe)throw std::runtime_error("Could not launch FFmpeg/NVENC");bool okay=true;
 for(int i=0;i<FRAMES;++i){BLImage frame=renderFrame(family,style,camera,image,faces,i);BLImageData data{};frame.getData(&data);const auto* bytes=static_cast<const uint8_t*>(data.pixelData);for(int y=0;y<H;++y){if(std::fwrite(bytes+y*data.stride,1,W*4,pipe)!=size_t(W*4)){okay=false;break;}}if(!okay)break;}
 const int rc=_pclose(pipe);if(!okay||rc!=0)throw std::runtime_error("NVENC render failed: "+out.filename().string());
 std::cout<<"Rendered "<<out.filename().string()<<"\n";
}

void writeManifest(){
 std::ofstream f(OUTPUT_DIR/"manifest.json",std::ios::binary|std::ios::trunc);
 f<<"{\n  \"visual_style\": \"archival video essay; film dust, torn newspaper, warm ochre title; no neon or bloom\",\n"
  <<"  \"resolution\": \"1920x1080\",\n  \"fps\": 30,\n  \"duration_seconds\": 5,\n"
  <<"  \"codec\": \"H.264\",\n  \"encoder\": \"NVIDIA NVENC\",\n  \"clip_count\": 40,\n  \"clips\": [\n";
 std::vector<std::string> names;
 for(const auto& c:RAP)names.push_back(clipName("Rapdaily",c.index,c.slug));
 int i=1;for(const auto& s:TYPE)names.push_back(clipName("Typewriter",i++,s));
 i=1;for(const auto& s:APPLE)names.push_back(clipName("Apple",i++,s));
 for(size_t n=0;n<names.size();++n)f<<"    \""<<names[n]<<"\""<<(n+1<names.size()?",":"")<<"\n";
 f<<"  ]\n}\n";
 if(!f)throw std::runtime_error("Could not write manifest.json");
}

int main(){try{
 fs::create_directories(OUTPUT_DIR);Fonts faces;if(!loadFonts(faces))throw std::runtime_error("Could not load headline, serif and sans fonts");
 BLImage newspaper=makeNewspaperCrop();
 for(const auto& shot:RAP)encode("Rapdaily",shot.slug,shot.index,shot.slug,&shot,newspaper,faces);
 int n=1;for(const auto& style:TYPE)encode("Typewriter",style,n++,style,nullptr,newspaper,faces);
 n=1;for(const auto& style:APPLE)encode("Apple",style,n++,style,nullptr,newspaper,faces);
 writeManifest();
 std::cout<<"Rendered 40 analog video-essay clips with C++ / Blend2D / NVIDIA NVENC.\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
