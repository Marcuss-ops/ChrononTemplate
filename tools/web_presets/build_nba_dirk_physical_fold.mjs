#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {resolveCameraSamples} from '../camera_roll/camera_samples.mjs';

const root = fileURLToPath(new URL('../..', import.meta.url));
const out = path.join(root, 'out/nba_dirk_physical_fold');
fs.mkdirSync(out, {recursive:true});
const W=1920, H=1080, FRAMES=240;
const rng = (()=>{let x=2011;return ()=>{x=(x*1664525+1013904223)>>>0;return x/4294967296;};})();
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const pts=[];
for(let x=18;x<=1702;x+=70)pts.push(`${x},${Math.round(16+(rng()-.5)*15)}`);
for(let y=30;y<=935;y+=55)pts.push(`${Math.round(1705+(rng()-.5)*20)},${y}`);
for(let x=1700;x>=15;x-=70)pts.push(`${x},${Math.round(940+(rng()-.5)*18)}`);
for(let y=920;y>=25;y-=55)pts.push(`${Math.round(18+(rng()-.5)*18)},${y}`);
const outline=pts.join(' ');
let flecks='';
for(let i=0;i<2100;i++){
  const x=32+rng()*1660, y=28+rng()*900, r=.35+rng()*1.8;
  const color=rng()>.52?'#5b472c':'#f5e8c8';
  flecks+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(2)}" fill="${color}" opacity="${(.035+rng()*.12).toFixed(3)}"/>`;
}
let fibers='';
for(let i=0;i<210;i++){
 const x=40+rng()*1630,y=35+rng()*880,len=5+rng()*34;
 fibers+=`<path d="M${x.toFixed(1)} ${y.toFixed(1)} l${(len*(rng()-.5)).toFixed(1)} ${(rng()*2-1).toFixed(1)}" stroke="#6e5d40" stroke-width="${(.3+rng()*.5).toFixed(2)}" opacity=".10"/>`;
}
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1720" height="960" viewBox="0 0 1720 960">
<defs>
 <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ddcba7"/><stop offset=".48" stop-color="#c8b38b"/><stop offset="1" stop-color="#b49e76"/></linearGradient>
 <linearGradient id="fold" x1="0" x2="1"><stop stop-color="#6f5a39" stop-opacity="0"/><stop offset=".42" stop-color="#4d3e29" stop-opacity=".38"/><stop offset=".55" stop-color="#f0dfb7" stop-opacity=".78"/><stop offset="1" stop-color="#59452c" stop-opacity="0"/></linearGradient>
 <linearGradient id="edge" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#382d20" stop-opacity=".28"/><stop offset=".08" stop-color="#fff5d9" stop-opacity="0"/><stop offset=".92" stop-color="#fff5d9" stop-opacity="0"/><stop offset="1" stop-color="#382d20" stop-opacity=".30"/></linearGradient>
 <clipPath id="sheet"><polygon points="${outline}"/></clipPath>
</defs>
<g clip-path="url(#sheet)">
 <rect width="1720" height="960" fill="url(#paper)"/>
 <rect width="1720" height="960" fill="#786341" opacity=".055"/>
 ${flecks}${fibers}
 <rect x="24" y="22" width="1674" height="916" fill="url(#edge)"/>
 <rect x="1182" y="18" width="38" height="922" fill="url(#fold)"/>
 <path d="M1200 32 C1193 210 1208 375 1197 520 C1188 700 1206 812 1198 928" fill="none" stroke="#665238" stroke-opacity=".36" stroke-width="3"/>
 <path d="M1205 26 C1214 204 1199 408 1208 574 C1217 751 1197 830 1206 932" fill="none" stroke="#f1e2c2" stroke-opacity=".52" stroke-width="2"/>
 <text x="100" y="148" font-family="Georgia,serif" font-size="24" letter-spacing="4" fill="#493b29" opacity=".72">DALLAS  •  FINALS ARCHIVE  •  2011</text>
 <path d="M96 174 H1104" stroke="#4a3b28" stroke-width="2" opacity=".45"/>
 <text x="102" y="230" font-family="Georgia,serif" font-size="20" letter-spacing="2" fill="#625239" opacity=".65">THE SEASON THAT REWROTE A LEGACY</text>
 <text x="105" y="665" font-family="Georgia,serif" font-size="24" fill="#56472f" opacity=".72">A seven-game series. A comeback from the edge. One unforgettable finish.</text>
 <path d="M104 700 H1090 M104 724 H1044 M104 748 H1080 M104 772 H980 M104 796 H1072 M104 820 H1020" stroke="#5e4b32" stroke-width="3" opacity=".24"/>
 <text x="104" y="878" font-family="Georgia,serif" font-size="18" letter-spacing="2" fill="#67553b" opacity=".65">SPORTS DESK   /   ARCHIVE EDITION   /   2011</text>
 <text x="1280" y="145" font-family="Georgia,serif" font-size="20" letter-spacing="2" fill="#58462c" opacity=".7">THE FINALS</text>
 <path d="M1278 169 H1645" stroke="#5c4b31" stroke-width="2" opacity=".38"/>
 <text x="1280" y="218" font-family="Georgia,serif" font-size="19" fill="#55452e" opacity=".65">Dallas meets Miami</text>
 <path d="M1280 246 H1640 M1280 269 H1625 M1280 292 H1650 M1280 315 H1570 M1280 338 H1640" stroke="#66543a" stroke-width="3" opacity=".28"/>
 <rect x="1280" y="390" width="340" height="210" fill="#5a4933" opacity=".12"/>
 <rect x="1287" y="397" width="326" height="196" fill="#e1d1af" opacity=".45"/>
 <text x="1304" y="439" font-family="Georgia,serif" font-size="17" letter-spacing="2" fill="#5c4b31" opacity=".70">THE FINAL MOMENT</text>
 <path d="M1304 464 H1585 M1304 488 H1568 M1304 512 H1590 M1304 536 H1530" stroke="#5d4d34" stroke-width="3" opacity=".28"/>
 <path d="M1278 660 H1645 M1278 684 H1608 M1278 708 H1643 M1278 732 H1582 M1278 756 H1638 M1278 780 H1598" stroke="#5d4d34" stroke-width="3" opacity=".27"/>
</g></svg>`;
const bg=`<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080"><defs><radialGradient id="v"><stop stop-color="#24201a"/><stop offset=".72" stop-color="#100f0d"/><stop offset="1" stop-color="#050505"/></radialGradient></defs><rect width="1920" height="1080" fill="url(#v)"/><ellipse cx="960" cy="930" rx="690" ry="70" fill="#000" opacity=".32"/></svg>`;
fs.writeFileSync(path.join(out,'sheet_full.svg'),svg);
fs.writeFileSync(path.join(out,'black_vignette.svg'),bg);
function raster(svgPath,pngPath){execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-i',svgPath,'-frames:v','1','-update','1',pngPath]);}
raster(path.join(out,'sheet_full.svg'),path.join(out,'sheet_full.png'));
raster(path.join(out,'black_vignette.svg'),path.join(out,'black_vignette.png'));
for(const [name,filter] of [['main','crop=1200:960:0:0'],['flap','crop=520:960:1200:0']])
 execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-i',path.join(out,'sheet_full.png'),'-vf',filter,'-frames:v','1',path.join(out,`paper_${name}.png`)]);
for(const [name,x,w] of [['main',0,1200],['flap',1200,520]]){
 const back=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="960"><defs><linearGradient id="b" x2="1" y2="1"><stop stop-color="#57452f"/><stop offset="1" stop-color="#342a1e"/></linearGradient></defs><rect x="4" y="5" width="${w-10}" height="950" rx="4" fill="url(#b)"/><path d="M8 18 H${w-12} M8 944 H${w-12}" stroke="#241d15" stroke-width="5" opacity=".55"/></svg>`;
 fs.writeFileSync(path.join(out,`back_${name}.svg`),back);
 raster(path.join(out,`back_${name}.svg`),path.join(out,`back_${name}.png`));
}
fs.copyFileSync(path.join(fileURLToPath(new URL('../../../Chronon3d/assets/fonts/Georgia_Bold.ttf',import.meta.url))),path.join(out,'Georgia_Bold.ttf'));
const key=(frame,value)=>({frame,value});
const opacityReveal=(id,start,end)=>({id,selectors:[{id:`${id}_selector`,unit:'grapheme',shape:'square',order:'forward',combine:'replace',exclude_spaces:true,start:{keyframes:[key(0,0),key(start,0),key(end,100)],easing:'linear'},end:{keyframes:[key(0,100),key(FRAMES-1,100)],easing:'linear'}}],properties:[{property:'opacity',keyframes:[key(0,0),key(FRAMES-1,0)]}]});
const tracksForFlap=[];
for(const [frame,degrees] of [[0,48],[58,26],[120,10],[160,10],[210,58],[239,42]]){
 const r=degrees*Math.PI/180;
 tracksForFlap.push({frame,degrees,x:340+260*Math.cos(r)-600,z:-260*Math.sin(r)});
}
const track=(property,field)=>({property,easing:'in_out_cubic',keyframes:tracksForFlap.map(s=>key(s.frame,s[field]))});
const img=(id,asset,position,size,animation=null)=>({id,type:'image',asset,size,position,fit:'contain',enable_3d:true,start_frame:0,duration_frames:FRAMES,...(animation?{animation}:{})});
const pageCamera={type:'perspective',position:[0,0,-1150],rotation_deg:[0,0,0],fov_deg:53.14,near:.1,far:10000,zoom:1};
const plan={schema:'chronon.render-plan.v3',version:3,job_id:'nba_dirk_physical_fold_v1',canvas:{width:W,height:H,fps_num:30,fps_den:1,duration_frames:FRAMES},camera:pageCamera,layers:[
 {id:'black_surround',type:'image',asset:'black_vignette.png',size:[W,H],position:[0,0],fit:'cover',screen_space:true,start_frame:0,duration_frames:FRAMES},
 img('main_backing','back_main.png',[-267,-5,8],[1208,970]),
 img('flap_backing','back_flap.png',[600,-5,8],[528,970],{tracks:[track('rotation_y','degrees'),track('position_x','x'),track('position_z','z')]}),
 img('sheet_main','paper_main.png',[-270,0,0],[1200,960]),
 img('sheet_folded_flap','paper_flap.png',[600,0,0],[520,960],{tracks:[track('rotation_y','degrees'),track('position_x','x'),track('position_z','z')]}),
 {id:'headline_written_on_paper',type:'text',text:'2011 Dirk Nowitzki\nWas A GOD',size:[1100,280],position:[690,555,-4],enable_3d:true,start_frame:0,duration_frames:FRAMES,style:{font:'Georgia_Bold.ttf',font_size:84,min_font_size:84,max_font_size:84,fit_mode:'shrink_only',fill:'#261e14'},text_animators:[opacityReveal('write_headline',36,148)]},
 {id:'ink_bleed_headline',type:'text',text:'2011 Dirk Nowitzki\nWas A GOD',size:[1100,280],position:[693,552,-2],enable_3d:true,opacity:.10,start_frame:0,duration_frames:FRAMES,style:{font:'Georgia_Bold.ttf',font_size:84,min_font_size:84,max_font_size:84,fit_mode:'shrink_only',fill:'#3a2918'},text_animators:[opacityReveal('bleed_headline',36,148)]}
],output:{path:'NBA_Article_and_Title_Chronon.mp4',format:'mp4',codec:'h264'}};
const cameraChannels=[
 ['position_x',[[0,-80],[72,-20],[150,0],[239,0]]],
 ['position_z',[[0,-1180],[72,-1100],[150,-1040],[239,-1250]]],
 ['rotation_y',[[0,5],[72,1],[150,-3],[239,-8]]],
 ['rotation_x',[[0,2],[72,0],[150,0],[239,-3]]],
].map(([channel,keyframes])=>({channel,easing:'in_out_cubic',keyframes:keyframes.map(([frame,value])=>({frame,value}))}));
plan.camera_samples=resolveCameraSamples(pageCamera,cameraChannels,30,FRAMES);
plan.camera=plan.camera_samples[0].camera;
// The plan already carries resolved `camera_samples` (the V3 contract); the
// legacy camera_animation post-bake step is retired and its binary no longer
// exists, so the plan is written as-is.
fs.writeFileSync(path.join(out,'nba_dirk_physical_fold.plan.json'),JSON.stringify(plan,null,2)+'\n');
console.log(`Wrote ${path.join(out,'nba_dirk_physical_fold.plan.json')}`);
