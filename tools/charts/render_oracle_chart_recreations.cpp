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
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
constexpr int W = 1920, H = 1080, FPS = 30, PER_CHART = 90;
constexpr double PI = 3.14159265358979323846;
const fs::path ROOT = L"C:/Users/pater/Pyt/ChrononTemplate";
const fs::path OUTPUT_DIR = ROOT / L"out/charts/oracle_deal_recreation";
const fs::path FONTS = ROOT / L"assets/fonts";

double clamp01(double x) { return std::clamp(x, 0.0, 1.0); }
double ease(double x) { x = clamp01(x); return x*x*(3.0-2.0*x); }
BLRgba32 rgba(const char* hex, uint8_t alpha=255) {
    unsigned v=0; std::sscanf(hex,"#%x",&v);
    return BLRgba32(uint8_t(v>>16),uint8_t(v>>8),uint8_t(v),alpha);
}

struct Type {
    BLFontFace regular, semibold, bold;
    BLFont r, s, b;
    Type() {
        const auto load=[&](BLFontFace& f,const wchar_t* p){
            if(f.createFromFile((FONTS/p).string().c_str())!=BL_SUCCESS)
                throw std::runtime_error("Could not load Inter font from ChrononTemplate/assets/fonts");
        };
        load(regular,L"Inter-Regular.ttf"); load(semibold,L"Inter-SemiBold.ttf"); load(bold,L"Inter-Bold.ttf");
        if(r.createFromFace(regular,32)!=BL_SUCCESS||s.createFromFace(semibold,32)!=BL_SUCCESS||b.createFromFace(bold,32)!=BL_SUCCESS)
            throw std::runtime_error("Could not create Inter font instances");
    }
};

double measure(const BLFont& f,const char* text) {
    BLGlyphBuffer gb; gb.setUtf8Text(text,std::strlen(text)); f.shape(gb); BLTextMetrics m; f.getTextMetrics(gb,m); return m.advance.x;
}
void text(BLContext& c,const Type& type,const char* value,double x,double baseline,double size,
          const char* color="#090909",int weight=1,bool center=false) {
    BLFont f; f.createFromFace(weight==2?type.bold:weight==1?type.semibold:type.regular,float(size));
    const double xx=center?x-measure(f,value)*.5:x;
    c.setFillStyle(rgba(color)); c.fillUtf8Text(BLPoint(xx,baseline),f,value,std::strlen(value));
}
void textRight(BLContext& c,const Type& f,const char* value,double right,double baseline,double size,
               const char* color="#111111",int weight=1) {
    BLFont font; font.createFromFace(weight==2?f.bold:weight==1?f.semibold:f.regular,float(size));
    text(c,f,value,right-measure(font,value),baseline,size,color,weight,false);
}
// Expose the faces separately without copying their native handles.
using Fonts = Type;

void title(BLContext& c,const Fonts& f,const char* s,double y=120) {
    text(c,f,s,W*.5,y,60,"#080808",2,true);
}
void line(BLContext& c,double x0,double y0,double x1,double y1,double width,const char* color="#111111") {
    BLPath p; p.moveTo(x0,y0); p.lineTo(x1,y1); c.setStrokeStyle(rgba(color)); c.setStrokeWidth(width); c.setStrokeStartCap(BL_STROKE_CAP_BUTT); c.setStrokeEndCap(BL_STROKE_CAP_BUTT); c.strokePath(p);
}
void roundedLabel(BLContext& c,const Type& f,const char* s,double cx,double top,const char* fill,
                  const char* ink,bool centered=true,double size=29) {
    BLFont font; font.createFromFace(f.semibold,size); const double w=measure(font,s)+26,h=size+20;
    c.setFillStyle(rgba(fill)); c.fillRoundRect(BLRoundRect(cx-w*.5,top,w,h,8));
    text(c,f,s,cx,top+h*.70,size,ink,1,centered);
}

uint32_t h32(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
// Dotted newsprint fill like the source graphics. The tint remains readable
// while a small black halftone grid gives the bars their rasterized texture.
void halftoneRect(BLContext& c,double x,double y,double w,double h,const char* fill,uint32_t salt=1) {
    c.setFillStyle(rgba(fill)); c.fillRect(BLRect(x,y,w,h));
    c.save(); c.clipToRect(BLRect(x,y,w,h)); c.setFillStyle(BLRgba32(8,8,8,32));
    const int ix=int(std::floor(x/4.0)), iy=int(std::floor(y/4.0));
    for(int gy=iy;gy<int(std::ceil((y+h)/4.0));++gy) for(int gx=ix;gx<int(std::ceil((x+w)/4.0));++gx){
        if((h32(uint32_t(gx*73856093u)^uint32_t(gy*19349663u)^salt)&3u)!=0u) continue;
        c.fillCircle(gx*4.0+2.0,gy*4.0+2.0,.78);
    }
    c.restore();
    c.setStrokeStyle(BLRgba32(15,15,15,220)); c.setStrokeWidth(2.0); c.strokeRect(BLRect(x,y,w,h));
}

BLImage economics(const Fonts& f,int frame) {
    BLImage im(W,H,BL_FORMAT_PRGB32); BLContext c(im); c.clearAll(); c.setFillStyle(rgba("#FFFFFF")); c.fillRect(BLRect(0,0,W,H));
    const double t=double(frame)/(PER_CHART-1); const double titleA=ease(t/.18);
    c.setGlobalAlpha(titleA); title(c,f,"Oracle-OpenAI Deal Economics",127); c.setGlobalAlpha(1.0);
    constexpr double xAxis=360, yTop=220, yBase=835, scale=7.65;
    line(c,xAxis,yTop,xAxis,yBase,3); line(c,xAxis,yBase,1530,yBase,3);
    for(int v=20;v<=80;v+=20){const double y=yBase-v*scale; line(c,xAxis-9,y,xAxis,y,3); char s[24]; std::snprintf(s,sizeof(s),"%dB",v); textRight(c,f,s,xAxis-10,y+11,31,"#151515",1);}
    struct Bar {const char* value; const char* fill; double x,w,v; const char* a; const char* b;};
    const Bar bars[]={{"$60B","#E65447",466,190,60,"OpenAI Annual","Commitment"},
                      {"$12B","#33C977",850,190,12,"OpenAI Annual","Revenue"},
                      {"$21.5B","#258EF0",1233,190,21.5,"Oracle Annual","Operating Cash Flow"}};
    for(int i=0;i<3;++i){const auto& b=bars[i]; const int start=13+i*12; const double q=ease((frame-start)/27.0); const double bh=b.v*scale*q; const double y=yBase-bh;
        if(q>0){halftoneRect(c,b.x,y,b.w,bh,b.fill,uint32_t(i+11));
            if(q>.72){const double a=ease((q-.72)/.28); c.setGlobalAlpha(a); text(c,f,b.value,b.x+b.w*.5,y-15,37,"#050505",2,true); c.setGlobalAlpha(1.0);}}
        const double la=ease((frame-(start+8))/18.0); c.setGlobalAlpha(la);
        text(c,f,b.a,b.x+b.w*.5,yBase+50,27,"#111111",1,true); text(c,f,b.b,b.x+b.w*.5,yBase+83,27,"#111111",1,true); c.setGlobalAlpha(1.0);
    }
    c.end(); return im;
}

struct Pt{double x,y;};
std::vector<Pt> curvePoints(double endYear){
    const Pt key[]={{0,0},{.5,-100},{1,-70},{2,-40},{3,-10},{4,20},{4.85,40}};
    const int count=220; std::vector<Pt> out; out.reserve(count+1);
    for(int i=0;i<=count;++i){double x=endYear*double(i)/count; int seg=0; while(seg<5&&x>key[seg+1].x)++seg;
        const auto a=key[seg],b=key[seg+1]; const auto p0=key[std::max(0,seg-1)],p3=key[std::min(6,seg+2)];
        const double u=clamp01((x-a.x)/(b.x-a.x));
        const double m1=(b.y-p0.y)/(b.x-p0.x),m2=(p3.y-a.y)/(p3.x-a.x),dx=b.x-a.x;
        const double y=(2*u*u*u-3*u*u+1)*a.y+(u*u*u-2*u*u+u)*dx*m1+(-2*u*u*u+3*u*u)*b.y+(u*u*u-u*u)*dx*m2;
        out.push_back({x,y});
    }
    return out;
}
Pt toScreen(Pt p){return {510+p.x*160,453-p.y*3.36};}
bool inPolygon(const std::vector<Pt>& poly,double x,double y){bool inside=false;for(size_t i=0,j=poly.size()-1;i<poly.size();j=i++){
    const auto&a=poly[i];const auto&b=poly[j];if(((a.y>y)!=(b.y>y))&&(x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x))inside=!inside;}return inside;}
void dottedPoly(BLContext& c,const std::vector<Pt>& p,const char* color,uint32_t seed){
    if(p.size()<3)return;double minx=p[0].x,maxx=minx,miny=p[0].y,maxy=miny;
    for(const auto&q:p){minx=std::min(minx,q.x);maxx=std::max(maxx,q.x);miny=std::min(miny,q.y);maxy=std::max(maxy,q.y);}
    c.setFillStyle(rgba(color,46));c.fillPolygon(reinterpret_cast<const BLPoint*>(p.data()),uint32_t(p.size()));
    c.setFillStyle(BLRgba32(30,30,30,35));
    for(int y=int(miny/5)*5;y<maxy;y+=5)for(int x=int(minx/5)*5;x<maxx;x+=5)
        if((h32(uint32_t(x*31)^uint32_t(y*79)^seed)&3u)==0u&&inPolygon(p,x,y))c.fillCircle(x,y,.72);
}
BLImage jcurve(const Fonts& f,int frame){
    BLImage im(W,H,BL_FORMAT_PRGB32);BLContext c(im);c.clearAll();c.setFillStyle(rgba("#FFFFFF"));c.fillRect(BLRect(0,0,W,H));
    const double a=ease(frame/14.0);c.setGlobalAlpha(a);title(c,f,"The J-Curve Effect",100);c.setGlobalAlpha(1);
    // Legend
    c.setFillStyle(rgba("#32C879"));c.fillRect(BLRect(750,135,25,25));text(c,f,"$30 Annual Rent",796,158,34,"#111111",1,false);
    constexpr double x0=412,x1=1537,y0=453,yTop=121,yBottom=905;
    line(c,x0,yTop,x0,yBottom,2.4);line(c,x0,y0,x1,y0,2.4);
    for(int v=-120;v<=80;v+=20){double y=y0-v*3.36;line(c,x0-9,y,x0,y,2.4);char s[24];std::snprintf(s,sizeof(s),"%d",v);textRight(c,f,s,x0-11,y+11,29,"#111111",1);}
    for(int yr=0;yr<=6;++yr){double x=510+yr*160;line(c,x,y0,x,y0+9,2.4);char s[24];std::snprintf(s,sizeof(s),"Year %d",yr);text(c,f,s,x,yBottom+46,29,"#111111",1,true);}
    c.save();c.translate(260,513);c.rotate(-PI/2);text(c,f,"Cumulative Net Cash Flow ($)",0,0,29,"#111111",1,true);c.restore();
    const double end=4.85*ease((frame-8)/62.0);const auto all=curvePoints(4.85);size_t vis=std::clamp<size_t>(size_t(clamp01(end/4.85)*(all.size()-1)),1,all.size()-1);
    std::vector<Pt> neg{{510,y0}},pos;
    for(size_t i=0;i<=vis;++i){Pt p=toScreen(all[i]); if(p.y>=y0)neg.push_back(p);else pos.push_back(p);}
    if(neg.size()>1){auto poly=neg;poly.push_back({neg.back().x,y0});poly.push_back({neg.front().x,y0});dottedPoly(c,poly,"#EA493A",22);}
    if(pos.size()>1){auto poly=pos;poly.push_back({pos.back().x,y0});poly.push_back({pos.front().x,y0});dottedPoly(c,poly,"#38C879",64);}
    if(vis>1){BLPath red;Pt p=toScreen(all[0]);red.moveTo(p.x,p.y);for(size_t i=1;i<=vis&&toScreen(all[i]).y>=y0;++i){p=toScreen(all[i]);red.lineTo(p.x,p.y);}c.setStrokeStyle(rgba("#E34232"));c.setStrokeWidth(7);c.setStrokeStartCap(BL_STROKE_CAP_ROUND);c.setStrokeEndCap(BL_STROKE_CAP_ROUND);c.strokePath(red);
        BLPath green;bool started=false;for(size_t i=1;i<=vis;++i){p=toScreen(all[i]);if(p.y<y0&&!started){Pt prev=toScreen(all[i-1]);double u=(y0-prev.y)/(p.y-prev.y);green.moveTo(prev.x+(p.x-prev.x)*u,y0);started=true;}if(started)green.lineTo(p.x,p.y);}if(started){c.setStrokeStyle(rgba("#31BD72"));c.setStrokeWidth(7);c.strokePath(green);}}
    struct Marker{int year;double val;const char* label;const char* fill;double dx,dy;};
    const Marker marks[]={{0,-100,"-$100","#E34B3C",0,24},{1,-70,"-$70","#E34B3C",0,27},{2,-40,"-$40","#E34B3C",0,28},{3,-10,"-$10","#E34B3C",0,23},{4,20,"$20","#32C879",0,-44}};
    for(int i=0;i<5;++i){const auto&m=marks[i]; const double reveal=ease((frame-(16+i*9))/12.0);if(reveal<=0)continue;const double x=510+m.year*160,y=y0-m.val*3.36;c.setGlobalAlpha(reveal);
        c.setFillStyle(rgba("#0E0E0E"));c.fillCircle(x,y,9);double top=m.dy<0?y+m.dy-31:y+m.dy;
        roundedLabel(c,f,m.label,x,top,m.fill,"#FFFFFF",true,27);c.setGlobalAlpha(1);}
    c.end();return im;
}

BLImage profits(const Fonts& f,int frame){
    BLImage im(W,H,BL_FORMAT_PRGB32);BLContext c(im);c.clearAll();c.setFillStyle(rgba("#FFFFFF"));c.fillRect(BLRect(0,0,W,H));
    const double titleIn=ease(frame/13.0);c.setGlobalAlpha(titleIn);text(c,f,"Profits",264,472,38,"#111111",2,false);c.setGlobalAlpha(1);
    const double t1=ease((frame-12)/46.0),t2=ease((frame-31)/36.0);
    const double x=267,greenW=1361*t1,greenY=477,h=64;
    if(greenW>1){halftoneRect(c,x,greenY,greenW,h,"#3DC77A",291);if(t1>.82){c.setGlobalAlpha(ease((t1-.82)/.18));textRight(c,f,"$27 B",x+greenW-16,greenY+54,58,"#060606",2);c.setGlobalAlpha(1);}}
    const double redW=310*t2,redY=590;if(redW>1){halftoneRect(c,x,redY,redW,h,"#EF786A",117);if(t2>.78){c.setGlobalAlpha(ease((t2-.78)/.22));text(c,f,"~$5.4 B",x+redW-230,redY+54,56,"#090909",2,false);c.setGlobalAlpha(1);}}
    const double labelA=ease((frame-4)/18.0);c.setGlobalAlpha(labelA);text(c,f,"ORACLE",139,518,26,"#CB3427",1,false);c.setGlobalAlpha(1);
    c.setFillStyle(rgba("#777777"));c.fillRoundRect(BLRoundRect(1390,1008,420,45,10));
    BLFont foot;foot.createFromFace(f.regular,18);c.setFillStyle(rgba("#FFFFFF"));c.fillUtf8Text(BLPoint(1406,1037),foot,"*Figures simplified and rounded for explanation.",47);c.end();return im;
}

BLImage render(int scene,const Fonts& f,int frame){if(scene==0)return economics(f,frame);if(scene==1)return jcurve(f,frame);return profits(f,frame);}
int main(){try{
    fs::create_directories(OUTPUT_DIR); Fonts fonts;
    const fs::path out=OUTPUT_DIR/L"Oracle_Deal_Charts_Reference_Recreation_1920x1080.mp4";
    const std::string cmd="ffmpeg.exe -y -v error -f rawvideo -pixel_format bgra -video_size 1920x1080 -framerate 30 -i - -an -c:v h264_nvenc -preset p5 -tune hq -cq 18 -pix_fmt yuv420p -movflags +faststart \""+out.string()+"\"";
    FILE* pipe=_popen(cmd.c_str(),"wb");if(!pipe)throw std::runtime_error("Could not start FFmpeg encoder");bool ok=true;
    for(int scene=0;scene<3&&ok;++scene)for(int frame=0;frame<PER_CHART&&ok;++frame){
        BLImage image=render(scene,fonts,frame);BLImageData d{};image.getData(&d);const auto* bytes=static_cast<const uint8_t*>(d.pixelData);
        for(int y=0;y<H;++y)if(std::fwrite(bytes+y*d.stride,1,W*4,pipe)!=size_t(W*4)){ok=false;break;}
    }
    int rc=_pclose(pipe);if(!ok||rc!=0)throw std::runtime_error("FFmpeg encoding failed");
    std::cout<<"Rendered "<<out.string()<<"\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
