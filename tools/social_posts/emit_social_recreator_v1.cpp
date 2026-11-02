// C++/Chronon native, editable social-media mockup plans (no browser plates).
#include "social_recreator_v1.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
constexpr int W = 1920, H = 1080;

J rgba(const std::string& h, double a=1.) { auto v=std::stoul(h.substr(1),nullptr,16); return J::array({((v>>16)&255)/255.,((v>>8)&255)/255.,(v&255)/255.,a}); }
J shape(std::string id,double x,double y,double w,double h,std::string fill,double radius=0) { J q={{"id",id},{"type","shape"},{"enable_3d",true},{"position",{x+w/2,H-y-h/2,0}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"shape",{{"type",radius?"rounded_rect":"rect"},{"fill",rgba(fill)}}}}; if(radius) q["shape"]["radius"]=radius; return q; }
J text(std::string id,std::string s,double x,double y,double w,double h,double size,std::string fill,std::string font="assets/fonts/Inter-Regular.ttf") { return {{"id",id},{"type","text"},{"enable_3d",true},{"text",s},{"position",{x+w/2,H-y-h/2,0}},{"size",{w,h}},{"start_frame",0},{"duration_frames",1},{"style",{{"font",font},{"font_size",size},{"fill",fill},{"fit_mode","none"},{"text_align","left"}}}}; }
J image(std::string id,std::string asset,double x,double y,double w,double h,double radius=0) { J q={{"id",id},{"type","image"},{"enable_3d",true},{"screen_space",true},{"asset",asset},{"position",{x+w/2,y+h/2,0}},{"size",{w,h}},{"fit","cover"},{"start_frame",0},{"duration_frames",1}}; if(radius)q["radius"]=radius;return q; }
J makePlan(const Recipe& r) {
 const std::string p=r.platform, kind=r.kind;
 const bool dark=std::string(r.theme)=="dark";
 std::string bg=dark?"#101114":"#F5F5F5", surface=dark?"#1B1B1F":"#FFFFFF";
 std::string ink=dark?"#F4F4F5":"#1C1C1E", muted=dark?"#A1A1AA":"#73737A", accent="#5865F2";
 if(p=="x"){bg="#F7F9F9";surface="#FFFFFF";ink="#0F1419";muted="#536471";accent="#1D9BF0";}
 if(p=="youtube"){bg="#0F0F0F";surface="#FFFFFF";ink="#0F0F0F";muted="#606060";accent="#FF0033";if(dark){surface="#212121";ink="#F1F1F1";muted="#AAAAAA";}}
 if(p=="instagram"){bg=dark?"#101014":"#FAFAFA";surface=dark?"#1D1D22":"#FFFFFF";ink=dark?"#FAFAFC":"#262626";muted=dark?"#AAAAB2":"#737373";accent="#C13584";}
 if(p=="tiktok"){bg="#101014";surface="#19191F";ink="#F7F7F8";muted="#AAAAB2";accent="#FE2C55";}
 if(p=="discord"){bg="#313338";surface="#313338";ink="#F2F3F5";muted="#B5BAC1";accent="#5865F2";}
 J l=J::array();
 l.push_back({{"id","canvas"},{"type","color"},{"color",rgba(bg)},{"size",{W,H}},{"screen_space",true},{"start_frame",0},{"duration_frames",1}});
 auto T=[&](std::string id,std::string v,double x,double y,double w,double h,double z,std::string c,std::string f="assets/fonts/Inter-Regular.ttf"){l.push_back(text(std::move(id),std::move(v),x,y,w,h,z,std::move(c),std::move(f)));};
 auto S=[&](std::string id,double x,double y,double w,double h,std::string c,double rad=0){l.push_back(shape(std::move(id),x,y,w,h,std::move(c),rad));};
 auto I=[&](std::string id,double x,double y,double w,double h,double rad=0){l.push_back(image(std::move(id),"assets/images/investigative_journalist_hero.jpg",x,y,w,h,rad));};
 auto A=[&](std::string id,double x,double y,double d,std::string){l.push_back(image(std::move(id),"assets/images/people_sample_portrait_b.png",x,y,d,d,d/2));};
 T("mockup_disclosure","ILLUSTRATIVE MOCKUP",1630,22,250,24,13,muted,"assets/fonts/Inter-Bold.ttf");

 if(p=="youtube" && kind=="video"){
   S("yt_topbar",0,0,W,78,"#0F0F0F");T("yt_logo","▶ YouTube",50,21,220,40,29,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   S("yt_search",600,14,640,48,"#252525",24);T("yt_search_hint","Search",626,24,550,28,18,"#AAAAAA");
   S("yt_nav",0,78,235,H-78,"#0F0F0F");T("yt_nav_items","⌂   Home\n▣   Shorts\n▤   Subscriptions\n\nYou\nHistory\nPlaylists\nYour videos",32,118,190,360,20,"#F1F1F1");
   I("yt_player",275,112,1050,590,12);S("yt_play",752,346,96,96,"#111111",48);T("yt_play_glyph","▶",781,369,42,48,34,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   T("yt_title",r.body,275,720,1040,64,28,"#F1F1F1","assets/fonts/Inter-Bold.ttf");A("yt_channel_avatar",280,798,60,"#B3261E");
   T("yt_channel",std::string(r.author)+"\n82K subscribers",356,796,430,58,19,"#F1F1F1","assets/fonts/Inter-Bold.ttf");
   S("yt_subscribe",1010,800,156,48,"#F1F1F1",24);T("yt_subscribe_text","Subscribe",1033,812,120,26,17,"#0F0F0F","assets/fonts/Inter-Bold.ttf");
   T("yt_video_meta",r.metric,275,882,900,30,17,"#AAAAAA");
   for(int i=0;i<4;i++){double yy=112+i*190;I("yt_recommendation_"+std::to_string(i),1360,yy,238,134,8);T("yt_rec_title_"+std::to_string(i),i==0?"The records behind the timeline":"A closer look at the archive",1612,yy+2,285,56,17,"#F1F1F1","assets/fonts/Inter-Bold.ttf");T("yt_rec_meta_"+std::to_string(i),"Field Notes · 42K views",1612,yy+66,278,28,14,"#AAAAAA");}
 }
 else if(p=="x"){
   S("x_sidebar",0,0,345,H,"#FFFFFF");T("x_logo","X",72,32,100,70,54,"#0F1419","assets/fonts/Inter-Bold.ttf");
   T("x_nav","Home\nExplore\nNotifications\nMessages\nBookmarks\nCommunities\nPremium\nProfile\nMore",70,142,230,495,23,"#0F1419","assets/fonts/Inter-Medium.ttf");
   S("x_timeline",345,0,930,H,"#FFFFFF");T("x_heading","Post",390,28,830,42,25,"#0F1419","assets/fonts/Inter-Bold.ttf");S("x_rule",345,86,930,1,"#EFF3F4");
   A("x_avatar",394,122,58,"#3078A8");T("x_author",std::string(r.author)+"  ✓",470,119,480,32,21,"#0F1419","assets/fonts/Inter-Bold.ttf");T("x_handle",std::string(r.handle)+"  ·  "+r.meta,470,154,500,26,16,"#536471");
   T("x_body",r.body,394,214,824,150,25,"#0F1419");
   if(kind=="poll"){T("x_poll_q","Which source should we publish next?",394,385,820,48,20,"#0F1419");for(int i=0;i<2;i++){double yy=448+i*74;S("x_poll_option_"+std::to_string(i),394,yy,820,54,"#FFFFFF",27);T("x_poll_label_"+std::to_string(i),i?"Interview transcript":"Archive register",418,yy+12,720,32,18,"#0F1419");S("x_poll_outline_"+std::to_string(i),394,yy,820,54,"#1D9BF0",27);}}
   else if(kind=="quote"){S("x_quote",394,390,820,210,"#FFFFFF",16);I("x_quote_image",410,406,260,176,10);T("x_quote_author","Archive Desk  ·  @archivedesk",694,410,485,32,16,"#0F1419","assets/fonts/Inter-Bold.ttf");T("x_quote_copy","The dated registry copy points to an earlier record.",694,452,478,112,18,"#0F1419");}
   else if(kind=="thread"){S("x_thread_line",418,386,3,300,"#CFD9DE");for(int i=0;i<2;i++){double yy=390+i*150;A("x_thread_avatar_"+std::to_string(i),394,yy,50,"#3078A8");T("x_thread_author_"+std::to_string(i),std::string(r.author)+"  ·  "+r.handle,460,yy,680,28,17,"#0F1419","assets/fonts/Inter-Bold.ttf");T("x_thread_copy_"+std::to_string(i),i==0?"First, the public record.":"Next, the original footage.",460,yy+38,710,72,19,"#0F1419");}}
   else if(r.media) I("x_media",394,390,820,354,14);
   T("x_actions","Reply       Repost       Like       Share",394,786,820,36,17,"#536471","assets/fonts/Inter-Medium.ttf");T("x_metrics",r.metric,394,839,820,28,15,"#536471");
   S("x_right_rail",1305,0,615,H,"#FFFFFF");S("x_search",1340,24,535,52,"#EFF3F4",26);T("x_search_label","Search",1372,35,460,30,17,"#536471");S("x_trends",1340,112,535,360,"#F7F9F9",16);T("x_trends_title","What is happening",1372,140,460,38,22,"#0F1419","assets/fonts/Inter-Bold.ttf");T("x_trends_list","Documentary sources\nPublic archive\nTimeline review",1372,198,460,180,19,"#0F1419");
 }
 else if(p=="discord"){
   S("dc_server_rail",0,0,78,H,"#1E1F22");for(int i=0;i<6;i++)S("dc_server_"+std::to_string(i),14,24+i*70,50,50,i==0?accent:"#36383E",25);
   S("dc_channel_rail",78,0,270,H,"#2B2D31");T("dc_server_name","FIELD NOTES  ▾",100,25,230,34,18,ink,"assets/fonts/Inter-Bold.ttf");T("dc_channel_label","RESEARCH CHANNELS",100,102,230,24,13,muted,"assets/fonts/Inter-Bold.ttf");T("dc_channels","# research\n# source-drops\n# timeline-review\n# episode-chat",102,142,220,170,17,muted);
   S("dc_main",348,0,W-348,H,"#313338");S("dc_header",348,0,W-348,72,"#313338");T("dc_header_text","#  "+std::string(r.handle),382,19,700,38,22,ink,"assets/fonts/Inter-Bold.ttf");
   if(kind=="poll"){A("dc_author_avatar",386,112,42,accent);T("dc_author",r.author,442,112,460,30,17,ink,"assets/fonts/Inter-Bold.ttf");T("dc_poll_question",r.body,442,160,1000,70,22,ink);for(int i=0;i<2;i++){double yy=250+i*82;S("dc_option_"+std::to_string(i),442,yy,790,60,"#3B3D44",8);T("dc_option_text_"+std::to_string(i),i?"Interview transcript":"Archive log",462,yy+14,740,32,18,ink);}T("dc_votes",r.metric,442,432,450,28,15,muted);}
   else if(kind=="embed"){A("dc_author_avatar",386,112,42,"#E0A44A");T("dc_author",r.author,442,112,460,30,17,ink,"assets/fonts/Inter-Bold.ttf");T("dc_message",r.body,442,151,1050,54,17,ink);S("dc_embed_bar",442,230,5,280,accent);S("dc_embed_card",447,230,720,280,"#2B2D31",8);T("dc_embed_title","SOURCE PACK  ·  PUBLIC RECORDS",470,248,670,34,18,ink,"assets/fonts/Inter-Bold.ttf");I("dc_embed_image",470,294,310,190,4);T("dc_embed_copy","Scans, dates and uncertainty notes",800,314,342,86,16,muted);}
   else {for(int i=0;i<5;i++){double yy=112+i*160;A("dc_message_avatar_"+std::to_string(i),386,yy,42,i==0?accent:"#9C7568");T("dc_message_author_"+std::to_string(i),i==0?r.author:"archive-reader",442,yy,460,27,17,ink,"assets/fonts/Inter-Bold.ttf");T("dc_time_"+std::to_string(i),"Today at 14:22",620,yy,220,25,14,muted);T("dc_message_"+std::to_string(i),i==0?r.body:(i==1?"I found the scan in the public registry.":"Can you link the original document?"),442,yy+36,1160,58,17,ink);}}
 }
 else if(kind=="vertical"||kind=="duet"||kind=="live"){
   const double px=p=="youtube"?570:600,py=30,pw=610,ph=1020;S("video_phone",px,py,pw,ph,"#09090B",22);
   if(kind=="duet"){I("duet_original",px+10,py+12,286,ph-24,12);S("duet_response",px+304,py+12,296,ph-24,"#25252B",12);T("duet_label","RESPONSE",px+326,py+46,250,30,16,"#FFFFFF","assets/fonts/Inter-Bold.ttf");}
   else I("vertical_media",px+10,py+12,pw-20,ph-24,12);
   S("vertical_scrim",px+12,py+700,pw-24,336,"#000000",12);T("vertical_context",p=="youtube"?"Shorts":"For You",px+34,py+36,pw-70,34,20,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   A("vertical_creator_avatar",px+pw+25,py+538,60,accent);T("vertical_follow","+ Follow",px+pw+20,py+604,100,26,15,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   T("vertical_author",r.author,px+35,py+730,pw-80,34,21,"#FFFFFF","assets/fonts/Inter-Bold.ttf");T("vertical_caption",r.body,px+35,py+773,pw-70,104,18,"#FFFFFF");T("vertical_sound","♫  Original sound",px+35,py+890,pw-70,26,15,"#FFFFFF");
   T("vertical_actions","♡\n24K\n\n◯\n680\n\n↗",px+pw+27,py+680,100,240,20,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   if(kind=="live"){S("live_panel",px+pw+155,py+215,420,650,"#19191F",14);T("live_title","LIVE CHAT",px+180,py+238,360,34,19,"#FFFFFF","assets/fonts/Inter-Bold.ttf");for(int i=0;i<5;i++)T("live_chat_"+std::to_string(i),i==0?r.body:"Where is the original record?",px+180,py+296+i*92,360,74,16,"#F1F1F1");}
 }
 else if(kind=="profile"){
   S("profile_topbar",0,0,W,78,p=="youtube"?"#0F0F0F":bg);T("profile_brand",p=="youtube"?"▶ YouTube":"TikTok",48,20,230,40,26,p=="youtube"?"#FFFFFF":ink,"assets/fonts/Inter-Bold.ttf");
   if(p=="youtube") I("profile_banner",240,104,1440,250,12); else S("profile_banner",240,104,1440,250,"#25252B",12);
   A("profile_avatar",310,284,142,p=="youtube"?"#9D3038":"#66535C");
   T("profile_name",r.author,490,365,760,50,34,ink,"assets/fonts/Inter-Bold.ttf");T("profile_handle",r.handle,490,418,650,30,18,muted);T("profile_bio",r.body,310,465,1240,58,21,ink);T("profile_stats",r.metric,310,535,1000,32,18,muted);
   S("profile_follow",1450,374,184,50,p=="youtube"?"#CC0000":"#FE2C55",25);T("profile_follow_label",p=="youtube"?"Subscribe":"Follow",1480,386,138,28,17,"#FFFFFF","assets/fonts/Inter-Bold.ttf");
   T("profile_tabs","HOME       VIDEOS       SHORTS       PLAYLISTS       COMMUNITY",310,610,1290,38,18,ink,"assets/fonts/Inter-Bold.ttf");
   for(int i=0;i<4;i++){double xx=310+i*338;I("profile_grid_"+std::to_string(i),xx,666,310,180,8);T("profile_grid_title_"+std::to_string(i),i==0?"The record, revisited":"A source-by-source breakdown",xx,856,310,48,17,ink,"assets/fonts/Inter-Bold.ttf");T("profile_grid_meta_"+std::to_string(i),"42K views  ·  2 days ago",xx,910,310,25,14,muted);}
 }
 else if(kind=="chat"){
   S("dm_sidebar",0,0,430,H,p=="discord"?"#2B2D31":surface);S("dm_main",430,0,W-430,H,surface);T("dm_title",p=="discord"?"DIRECT MESSAGES":"Messages",28,30,360,38,24,ink,"assets/fonts/Inter-Bold.ttf");
   for(int i=0;i<5;i++){double yy=108+i*104;A("dm_contact_avatar_"+std::to_string(i),26,yy,54,i==0?accent:"#8A766E");T("dm_contact_"+std::to_string(i),i==0?r.author:"Research team",96,yy,300,28,18,ink,"assets/fonts/Inter-Bold.ttf");T("dm_preview_"+std::to_string(i),i==0?r.body:"Shared a source link",96,yy+34,305,48,15,muted);}
   S("dm_header",430,0,W-430,82,surface);A("dm_header_avatar",462,18,48,accent);T("dm_header_name",r.author,526,18,500,28,19,ink,"assets/fonts/Inter-Bold.ttf");T("dm_status","Active now",526,48,250,22,14,muted);
   S("dm_bubble_in",500,170,760,100,p=="discord"?"#383A40":"#EFEFF0",16);T("dm_text_in","Can you share the source page?",528,191,700,56,20,ink);
   S("dm_bubble_out",875,300,710,112,p=="discord"?"#4752C4":"#3797F0",16);T("dm_text_out","Yes, page 14. The date is visible there.",902,323,660,62,20,"#FFFFFF");
   S("dm_bubble_in_2",500,445,850,106,p=="discord"?"#383A40":"#EFEFF0",16);T("dm_text_in_2","Thanks. I will compare it with the registry copy.",528,470,800,60,20,ink);
   S("dm_composer",482,900,1390,62,p=="discord"?"#383A40":"#F5F5F5",26);T("dm_composer_hint","Message…",514,916,1300,32,17,muted);
 }
 else if(kind=="comments"){
   S("comments_panel",260,40,1400,1000,surface,12);T("comments_heading","Comments   ·   1,284",320,88,1150,52,31,ink,"assets/fonts/Inter-Bold.ttf");T("comments_sort","Sort by  ▾",320,148,250,30,17,muted);
   for(int i=0;i<5;i++){double yy=210+i*158;A("comment_avatar_"+std::to_string(i),320,yy,46,i==0?accent:"#92776B");T("comment_author_"+std::to_string(i),i==0?r.author:"Archive Reader",382,yy,360,28,18,ink,"assets/fonts/Inter-Bold.ttf");T("comment_age_"+std::to_string(i),"·  2 hours ago",552,yy,250,28,15,muted);T("comment_body_"+std::to_string(i),i==0?r.body:(i==1?"The date on the scan is the detail that changes this.":"Could you link the primary source?"),382,yy+35,1160,52,19,ink);T("comment_reactions_"+std::to_string(i),"♡   128       Reply",382,yy+94,500,26,15,muted);if(i==0)T("comment_reply","↳  Creator reply  ·  Source and edit history are linked.",425,yy+126,1100,26,15,accent);}
 }
 else if(kind=="poll"){
   S("poll_card",300,85,1320,910,surface,14);A("poll_avatar",344,124,58,accent);T("poll_author",r.author,420,125,760,32,21,ink,"assets/fonts/Inter-Bold.ttf");T("poll_meta",std::string(r.handle)+"  ·  "+r.meta,420,162,760,26,16,muted);T("poll_question",r.body,344,230,1210,90,29,ink,"assets/fonts/Inter-Bold.ttf");
   for(int i=0;i<3;i++){double yy=360+i*118;S("poll_track_"+std::to_string(i),344,yy,1190,76,dark?"#373940":"#F1F3F4",14);S("poll_result_"+std::to_string(i),344,yy,1190*(i==0?.58:i==1?.28:.14),76,i==0?accent:(dark?"#4B4E56":"#D6DADF"),14);T("poll_label_"+std::to_string(i),i==0?"Archive register":i==1?"Interview transcript":"Publish both sources",370,yy+21,1000,34,19,ink,"assets/fonts/Inter-Bold.ttf");T("poll_pct_"+std::to_string(i),i==0?"58%":i==1?"28%":"14%",1455,yy+21,70,34,18,ink,"assets/fonts/Inter-Bold.ttf");}
   T("poll_total",r.metric,344,760,900,30,16,muted);
 }
 else {
   const double x=250,y=70,w=1420,h=940;S("post_card",x,y,w,h,surface,10);
   if(p=="instagram"){S("ig_nav",0,0,235,H,surface);T("ig_wordmark","Instagram",28,36,190,42,28,ink,"assets/fonts/PlayfairDisplay-Bold.ttf");T("ig_navigation","HOME\nSEARCH\nEXPLORE\nREELS\nMESSAGES\nACTIVITY\nCREATE\nPROFILE",28,140,205,450,19,ink,"assets/fonts/Inter-Medium.ttf");}
   A("post_avatar",x+38,y+32,58,accent);T("post_author",r.author,x+116,y+33,700,32,21,ink,"assets/fonts/Inter-Bold.ttf");T("post_identity",std::string(r.handle)+"  ·  "+r.meta,x+116,y+69,800,28,16,muted);
   if(p=="instagram" && (kind=="post"||kind=="carousel")){
     I("ig_post_media",x+36,y+123,790,760,5);if(kind=="carousel"){S("ig_slide_previous",x+52,y+474,48,48,"#FFFFFF",24);S("ig_slide_next",x+760,y+474,48,48,"#FFFFFF",24);T("ig_slides","●  ○  ○  ○",x+340,y+842,240,26,16,"#FFFFFF");}
     T("ig_caption",r.body,x+866,y+144,500,120,19,ink);for(int i=0;i<5;i++)T("ig_comment_"+std::to_string(i),i==0?"Source link in the bio.":"This adds context to the timeline.",x+866,y+290+i*66,500,52,16,ink);
     T("ig_actions","♡     ◯     ➤",x+866,y+700,420,36,24,ink,"assets/fonts/Inter-Bold.ttf");T("ig_metrics",r.metric,x+866,y+748,480,32,16,ink,"assets/fonts/Inter-Bold.ttf");T("ig_add_comment","Add a comment…",x+866,y+822,480,30,15,muted);
   } else {
     T("post_body",r.body,x+38,y+132,w-76,120,27,ink);if(r.media)I("post_media",x+38,y+268,w-76,475,10);
     S("post_footer_rule",x+38,y+784,w-76,1,dark?"#414248":"#E5E5E5");T("post_actions","♡   Like       ◯   Comment       ↗   Share",x+38,y+805,w-76,35,19,muted,"assets/fonts/Inter-Medium.ttf");T("post_metrics",r.metric,x+38,y+855,w-76,30,16,muted);
     if(kind=="quote"){S("quote_context",x+56,y+420,w-112,180,dark?"#111214":"#F4F5F6",12);T("quote_context_text","Earlier post  ·  original context preserved",x+80,y+448,w-160,90,19,muted);}
     if(kind=="thread"){S("thread_rail",x+56,y+265,3,265,accent);T("thread_followup","↳  Next post in this thread",x+82,y+520,w-164,54,18,accent);}
     if(kind=="embed"){S("embed_bar",x+38,y+270,5,200,accent);S("embed_panel",x+43,y+270,w-86,200,dark?"#292A30":"#F3F4F5",8);T("embed_title","SOURCE PACK  ·  DOCUMENTS & DATES",x+70,y+292,w-140,35,19,ink,"assets/fonts/Inter-Bold.ttf");T("embed_description","Primary records with an uncertainty note",x+70,y+342,w-140,52,17,muted);}
   }
 }
 return {{"schema","chronon.render-plan.v3"},{"version",3},{"job_id",std::string("social_")+r.id+"_v1"},{"canvas",{{"width",W},{"height",H},{"fps_num",30},{"fps_den",1},{"duration_frames",1}}},{"layers",l},{"output",{{"path",std::string(r.id)+".mp4"},{"format","mp4"},{"codec","h264"}}}};
}
int main(int argc,char**argv) try { if(argc!=2) throw std::runtime_error("usage: chronontemplate_emit_social_recreator_v1 <output-dir>"); fs::path out=fs::absolute(argv[1]);fs::create_directories(out); for(const auto&r:allSocialRecreatorV1Recipes()){auto j=makePlan(r);std::ofstream f(out/(std::string("social_")+r.id+"_v1.plan.json"));f<<j.dump(2)<<'\n';if(!f)throw std::runtime_error("failed to write plan");} std::cout<<"Emitted "<<allSocialRecreatorV1Recipes().size()<<" native Chronon social mockup plans to "<<out<<'\n';return 0;} catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
