"""Build ten story explainers and eight reusable motion primitives as SVG + MP4."""
from pathlib import Path
import math
import json
import shutil
import subprocess
import sys

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
SVG_DIR = HERE / "assets"
VIDEO_DIR = HERE / "renders"
PACK = Path(__file__).resolve().parents[3] / "assets" / "chronon_visual_venture_pack"
W, H, FPS, SECONDS = 1920, 1080, 24, 8
FRAMES = FPS * SECONDS
WHITE = (237, 240, 245)
MUTED = (126, 140, 156)
RED = (52, 54, 245)
AMBER = (32, 180, 245)
GREEN = (125, 210, 116)


def smooth(a, b, x):
    u = max(0.0, min(1.0, (x-a)/(b-a)))
    return u*u*(3-2*u)

STORIES = [
    ("09_project_sunshine_food_chain", "PROJECT SUNSHINE / FALLOUT PATHWAY", "chain"),
    ("10_operation_sea_spray_dispersion", "OPERATION SEA SPRAY / DISPERSION MODEL", "coast"),
    ("11_project_shad_ship_scan", "PROJECT SHAD / SHIP AND TEST ZONE", "ship"),
    ("12_greenbrier_bunker_cutaway", "GREENBRIER / UNDERGROUND CUTAWAY", "bunker"),
    ("13_midnight_climax_surveillance", "MIDNIGHT CLIMAX / ROOM SIGHTLINE", "rooms"),
    ("14_goldsboro_safety_sequence", "GOLDSBORO / ARMING SEQUENCE", "bomb"),
    ("15_fernald_tracer_path", "FERNALD / TRACER PATHWAY", "tracer"),
    ("16_teapot_dome_money_flow", "TEAPOT DOME / CONTRACT FLOW", "money"),
    ("17_operation_washtub_network", "OPERATION WASHTUB / NETWORK MAP", "alaska"),
    ("18_soviet_alfa_cooling_loop", "PROJECT 705 / COOLANT LOOP", "submarine"),
]
PRIMITIVES = [
    ("19_particle_flow", "PARTICLE FLOW", "particle"),
    ("20_path_reveal", "PATH REVEAL", "path"),
    ("21_radar_scan", "RADAR SCAN", "radar"),
    ("22_network_graph", "NETWORK GRAPH", "network"),
    ("23_number_counter", "NUMBER COUNTER", "counter"),
    ("24_shape_morph", "SHAPE MORPH", "morph"),
    ("25_document_reveal", "DOCUMENT REVEAL", "document"),
    ("26_signal_pulse", "SIGNAL PULSE", "signal"),
]


def point(x, y): return (int(x), int(y))


def _make_background():
    yy, xx = np.ogrid[:H, :W]
    d = ((xx - W / 2) / 1050) ** 2 + ((yy - H / 2) / 660) ** 2
    f = np.clip(1 - .78 * d, .22, 1)
    out = np.zeros((H, W, 3), np.uint8)
    for c, v in enumerate((22, 22, 24)): out[:, :, c] = (f * v).astype(np.uint8)
    return out


BACKGROUND = _make_background()
GRAIN = np.random.default_rng(5101).normal(1.8, 5.2, (H, W, 1)).astype(np.float32)


def base_frame(): return BACKGROUND.copy()


def bloom(img):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (0, 0), 3)
    blur = cv2.resize(blur, (W, H), interpolation=cv2.INTER_LINEAR)
    return cv2.addWeighted(img, 1, blur, .7, 0)


def line(img, pts, color=WHITE, width=3, dash=None):
    pts = np.asarray(pts, np.int32).reshape((-1, 1, 2))
    if dash is None: cv2.polylines(img, [pts], False, color, width, cv2.LINE_AA)
    else:
        for a, b in zip(pts[:-1, 0], pts[1:, 0]):
            length = math.dist(a, b); n = max(1, int(length / (dash * 2)))
            for i in range(n + 1):
                u0, u1 = i / n, min(1, (i + .55) / n)
                if i % 2 == 0:
                    p0 = (int(a[0] * (1-u0) + b[0]*u0), int(a[1]*(1-u0)+b[1]*u0))
                    p1 = (int(a[0] * (1-u1) + b[0]*u1), int(a[1]*(1-u1)+b[1]*u1))
                    cv2.line(img, p0, p1, color, width, cv2.LINE_AA)


def circ(img, xy, r, color=WHITE, width=-1): cv2.circle(img, point(*xy), int(r), color, width, cv2.LINE_AA)
def poly(img, pts, color=WHITE, width=2, fill=False):
    p = np.asarray(pts, np.int32)
    if fill: cv2.fillPoly(img, [p], color, cv2.LINE_AA)
    else: cv2.polylines(img, [p], True, color, width, cv2.LINE_AA)


def label(img, text, xy=(100, 105)):
    cv2.putText(img, text, xy, cv2.FONT_HERSHEY_SIMPLEX, .7, MUTED, 1, cv2.LINE_AA)
    cv2.line(img, (xy[0], xy[1] + 18), (xy[0] + 110, xy[1] + 18), RED, 2, cv2.LINE_AA)


def node(img, x, y, title, color=WHITE, r=44):
    circ(img, (x, y), r + 9, color, 1)
    circ(img, (x, y), r, (13, 14, 17), -1)
    circ(img, (x, y), r, color, 2)
    cv2.putText(img, title, (x - max(35, len(title)*9), y + r + 40), cv2.FONT_HERSHEY_SIMPLEX, .5, MUTED, 1, cv2.LINE_AA)


def flowing_dots(img, pts, t, count=9, color=RED, radius=6, speed=.18):
    for i in range(count):
        u = (t * speed + i / count) % 1
        seg = min(len(pts) - 2, int(u * (len(pts) - 1)))
        q = u * (len(pts)-1) - seg
        x = pts[seg][0] * (1-q) + pts[seg+1][0] * q
        y = pts[seg][1] * (1-q) + pts[seg+1][1] * q
        circ(img, (x, y), radius, color)


def scene_chain(img, t):
    label(img, "PROJECT SUNSHINE  /  FOOD-CHAIN PATHWAY")
    xs = [290, 625, 960, 1295, 1630]; y = 540
    morph=smooth(.36,.62,t/8)
    pts=[(x,y+(i-2)*105*morph) for i,x in enumerate(xs)]
    line(img, pts, (78, 87, 98), 2)
    flowing_dots(img, pts, t, 12, RED, 5, .095)
    for i, x in enumerate(xs):
        yy=int(pts[i][1])
        node(img, x, yy, ["FALLOUT", "GRASS", "CATTLE", "MILK", "BONES"][i], RED if i == 4 else WHITE)
        if i == 0:
            for k in range(4): circ(img, (x - 18 + k*12, yy - 12), 3, RED)
        elif i == 1:
            line(img, [(x, yy+14), (x, yy-22), (x-14, yy-9)], GREEN, 3); line(img, [(x, yy-4), (x+15, yy-22)], GREEN, 3)
        elif i == 2:
            cv2.rectangle(img, (x-26,yy-18),(x+25,yy+17),WHITE,2,cv2.LINE_AA); circ(img,(x+25,yy-18),12,WHITE,2); circ(img,(x-14,yy+22),5,WHITE); circ(img,(x+15,yy+22),5,WHITE)
        elif i == 3:
            poly(img,[(x-19,yy-20),(x+19,yy-20),(x+14,yy+24),(x-14,yy+24)],WHITE,2); line(img,[(x-12,yy-7),(x+12,yy-7)],WHITE,2)
        else:
            circ(img,(x,yy-15),14,RED,2); line(img,[(x,yy-1),(x,yy+23)],RED,2); line(img,[(x-18,yy+7),(x+18,yy+7)],RED,2)


def scene_coast(img, t):
    label(img, "OPERATION SEA SPRAY  /  DISPERSION MODEL")
    coast=[(1160,210),(1090,330),(1165,420),(1080,520),(1150,650),(1060,825)]
    line(img,coast,WHITE,3); line(img,[(300,260),(1000,260)],(43,56,69),1)
    circ(img,(500,545),9,WHITE); line(img,[(500,545),(510,575),(490,575),(500,545)],WHITE,2); line(img,[(470,580),(530,580)],WHITE,2)
    cv2.putText(img,"VESSEL",(455,630),cv2.FONT_HERSHEY_SIMPLEX,.5,MUTED,1,cv2.LINE_AA)
    # Wind carries a soft particle plume toward the coast.
    for i in range(65):
        phase=(t*.12+i/65)%1; x=565+phase*480; spread=(phase*100)
        y=545+math.sin(i*12.989+t*1.2)*spread
        circ(img,(x,y),2+(i%3),RED if i%5==0 else (130,142,153))
    for k in range(3): line(img,[(570,420+k*80),(760,400+k*80)],(71,82,95),1)


def scene_ship(img, t):
    label(img,"PROJECT SHAD  /  TEST-AREA SCAN")
    hull=[(520,560),(1350,560),(1260,645),(650,645),(580,605)]
    poly(img,hull,WHITE,3); line(img,[(690,555),(770,480),(1040,480),(1110,555)],WHITE,3)
    line(img,[(820,480),(820,430),(1000,430),(1000,480)],WHITE,2)
    circ(img,(960,415),10,WHITE)
    for r in (160,280,400):
        cv2.ellipse(img,(960,460),(r,r),0,205,335,(63,75,88),1,cv2.LINE_AA)
    ang=205+(t%1)*130
    x=960+390*math.cos(math.radians(ang)); y=460+390*math.sin(math.radians(ang))
    line(img,[(960,460),(x,y)],(96,195,145),2)
    circ(img,(1180,620),20,RED if int(t*2)%2==0 else (100,82,80),2)
    line(img,[(1180,620),(1180,710)],RED,1)


def scene_bunker(img,t):
    label(img,"GREENBRIER  /  PROTECTIVE FACILITY CUTAWAY")
    cv2.line(img,(250,490),(1670,490),(96,103,112),2,cv2.LINE_AA)
    # Hotel above ground
    poly(img,[(700,280),(1220,280),(1290,490),(630,490)],WHITE,3)
    for x in range(710,1210,80): cv2.rectangle(img,(x,340),(x+36,390),MUTED,1)
    # Revealed underground rooms
    reveal=smooth(.18,.72,t/8)
    if reveal>0:
        y0=500; alpha=(100,110,122)
        line(img,[(500,y0),(1420,y0)],WHITE,2)
        for i in range(5):
            x=520+i*175; h=int(180*reveal)
            cv2.rectangle(img,(x,510),(x+145,510+h),alpha,2,cv2.LINE_AA)
            if i==2: cv2.rectangle(img,(x+53,510),(x+90,510+h),RED,2,cv2.LINE_AA)
            cv2.line(img,(x+70,510),(x+70,510+h),(80,88,98),1,cv2.LINE_AA)
        for yy in (720,760): cv2.line(img,(500,yy),(1420,yy),(65,75,87),1,cv2.LINE_AA)
        x=960; circ(img,(x,560+int(160*reveal)),5,RED)


def scene_rooms(img,t):
    label(img,"MIDNIGHT CLIMAX  /  OBSERVATION SIGHTLINE")
    cv2.rectangle(img,(380,300),(1540,790),WHITE,2,cv2.LINE_AA)
    cv2.line(img,(960,300),(960,790),WHITE,3,cv2.LINE_AA)
    cv2.rectangle(img,(944,420),(976,650),RED,1,cv2.LINE_AA)
    # sight cone through the one-way mirror
    angle=-.35+.7*(.5+.5*math.sin(t*math.tau/5)); tip=(1320,420)
    spread=380
    overlay=img.copy(); poly(overlay,[tip,(tip[0]-spread,tip[1]-int(130*angle+105)),(tip[0]-spread,tip[1]+int(130*angle+300))],(78,84,93),1,True); cv2.addWeighted(overlay,.14,img,.86,0,img)
    circ(img,(1320,420),18,WHITE,2); circ(img,(700+int(40*math.sin(t)),520),15,WHITE,2); circ(img,(780,620),8,WHITE)
    for r in (45,75,105): cv2.ellipse(img,(1320,420),(r,r),0,145,220,(57,64,73),1,cv2.LINE_AA)


def scene_bomb(img,t):
    label(img,"GOLDSBORO  /  SAFETY-DEVICE SEQUENCE")
    # aircraft silhouette
    line(img,[(310,340),(530,340),(635,310),(700,340),(850,340),(905,360),(840,382),(650,382),(560,425),(520,425),(550,382),(320,382),(280,360),(310,340)],WHITE,2)
    bx=800; by=470+int(110*(t%1))
    poly(img,[(bx-13,by-32),(bx+13,by-32),(bx+10,by+25),(bx,by+40),(bx-10,by+25)],RED,2)
    line(img,[(bx,420),(bx,by-35)],(92,103,116),1)
    # arming chain
    xs=[1040,1250,1460,1660]; yy=505
    for i,x in enumerate(xs[:-1]): line(img,[(x+27,yy),(xs[i+1]-27,yy)],(74,83,95),2)
    for i,x in enumerate(xs):
        col=GREEN if i==3 else (AMBER if i==2 else RED if i==1 else WHITE)
        circ(img,(x,yy),25,col,3); circ(img,(x,yy),7,col)
        cv2.putText(img,["SAFE","FALL","ARM","SAFE"][i],(x-34,yy+70),cv2.FONT_HERSHEY_SIMPLEX,.45,MUTED,1,cv2.LINE_AA)
    line(img,[(1040,670),(1660,670)],(48,58,70),2)
    pos=1040+int((1660-1040)*(t/8%1)); circ(img,(pos,670),7,RED)


def scene_tracer(img,t):
    label(img,"FERNALD  /  SCIENTIFIC TRACER DIAGRAM")
    # bowl, simplified torso and highlighted route
    poly(img,[(350,380),(520,380),(500,500),(370,500)],WHITE,3); line(img,[(340,380),(530,380)],WHITE,3)
    # torso silhouette
    line(img,[(835,315),(835,400),(780,440),(760,700),(1160,700),(1140,440),(1085,400),(1085,315)],WHITE,3)
    circ(img,(960,350),72,WHITE,2)
    path=[(455,500),(610,530),(740,530),(830,485),(905,515),(1030,510),(1080,585),(980,630),(850,610)]
    line(img,path,RED,3); flowing_dots(img,path,t,10,RED,5,.17)
    line(img,[(550,440),(720,485)],(80,92,106),2)


def scene_money(img,t):
    label(img,"TEAPOT DOME  /  DOCUMENTED CONTRACT FLOW")
    coords=[(460,500),(960,500),(1460,500)]; titles=["GOVERNMENT","OIL COMPANY","OFFICIAL"]
    nodes=[(x,y) for x,y in coords]
    for x,y in nodes: node(img,x,y,"",WHITE,53)
    for x,y,s in zip([460,960,1460],[500]*3,titles): cv2.putText(img,s,(x-70,600),cv2.FONT_HERSHEY_SIMPLEX,.48,MUTED,1,cv2.LINE_AA)
    line(img,[(513,500),(907,500)],(94,104,117),2); line(img,[(1013,500),(1407,500)],(94,104,117),2)
    for i in range(9):
        p=(t*.16+i/9)%1
        for x0,x1,y in [(515,905,500),(1015,1405,520)]: circ(img,(x0+(x1-x0)*p,y),5,AMBER)
    for x,y in nodes: cv2.putText(img,"$",(x-17,y+14),cv2.FONT_HERSHEY_SIMPLEX,1.05,AMBER,2,cv2.LINE_AA)


def scene_alaska(img,t):
    label(img,"OPERATION WASHTUB  /  ALASKA NETWORK")
    alaska=[(390,345),(520,300),(640,325),(735,285),(850,350),(990,330),(1100,390),(1220,360),(1360,425),(1480,480),(1420,560),(1320,585),(1250,690),(1130,650),(1030,720),(920,660),(810,700),(700,620),(585,605),(500,520)]
    poly(img,alaska,(112,126,143),2)
    pts=[(560,450),(760,390),(940,500),(1150,425),(1300,540),(1010,640)]
    for i in range(len(pts)):
        for j in range(i+1,len(pts)):
            if (i*3+j)%3==0: line(img,[pts[i],pts[j]],(65,81,98),1)
    for i,(x,y) in enumerate(pts):
        circ(img,(x,y),7,RED if i==0 else WHITE)
        for k in range(3): cv2.ellipse(img,(x,y),(30+k*22,18+k*18),0,215,325,(75,92,111),1,cv2.LINE_AA)


def scene_submarine(img,t):
    label(img,"PROJECT 705  /  LIQUID-METAL COOLANT LOOP")
    hull=[(360,520),(470,440),(1360,440),(1510,520),(1360,600),(470,600)]
    poly(img,hull,WHITE,3); cv2.rectangle(img,(800,392),(1100,440),WHITE,2,cv2.LINE_AA)
    # reactor and coolant return loop
    cv2.rectangle(img,(895,470),(1025,570),RED,2,cv2.LINE_AA)
    path=[(895,500),(700,500),(700,650),(1220,650),(1220,520),(1025,520)]
    line(img,path,(99,187,212),4); flowing_dots(img,path,t,14,AMBER,5,.15)
    # thermometer
    cv2.rectangle(img,(1600,340),(1640,700),MUTED,2,cv2.LINE_AA)
    cv2.rectangle(img,(1605,510),(1635,695),RED,-1)
    circ(img,(1620,710),25,RED,-1); line(img,[(1570,470),(1670,470)],WHITE,2)


def primitive(img,t,kind):
    cx,cy=960,550
    if kind=="particle":
        label(img,"PARTICLE FLOW")
        path=[(430,550),(700,480),(970,570),(1230,460),(1510,540)]; line(img,path,(86,101,118),2); flowing_dots(img,path,t,18,RED,6,.13)
    elif kind=="path":
        label(img,"PATH REVEAL")
        pts=[(430,650),(610,440),(830,580),(1060,360),(1270,540),(1490,400)];
        n=int(1+(len(pts)-1)*((t/8)%1)); line(img,pts[:n+1],WHITE,4);
        if n<len(pts)-1: circ(img,pts[n],7,RED)
    elif kind=="radar":
        label(img,"RADAR SWEEP")
        for r in (130,250,370): circ(img,(cx,cy),r,(53,68,82),1)
        a=(t%6)*math.tau/6; x=cx+370*math.cos(a); y=cy+370*math.sin(a); line(img,[(cx,cy),(x,y)],GREEN,2)
        for bx,by in ((760,490),(1130,600),(1020,260)): circ(img,(bx,by),6,RED)
    elif kind=="network":
        label(img,"NETWORK GRAPH")
        pts=[(650,400),(900,320),(1130,420),(700,660),(1010,650),(1310,590)]
        for i,p in enumerate(pts):
            for q in pts[i+1:]: line(img,[p,q],(54,68,83),1)
        reveal=min(1,(t/8)*1.4)
        for i,p in enumerate(pts):
            if i/len(pts)<reveal: circ(img,p,12,RED if i==0 else WHITE)
    elif kind=="counter":
        label(img,"NUMBER COUNTER")
        val=int(1200+int(t*375)%3800); cv2.putText(img,f"{val:04d}",(740,590),cv2.FONT_HERSHEY_SIMPLEX,3,WHITE,3,cv2.LINE_AA)
        cv2.rectangle(img,(700,440),(1220,640),MUTED,1,cv2.LINE_AA); circ(img,(1220,540),5,RED)
    elif kind=="morph":
        label(img,"SHAPE MORPH")
        k=.5-.5*math.cos((t/8)*math.tau); n=64
        pts=[]
        for i in range(n):
            a=math.tau*i/n; r=150*((1-k)+k*(1/max(abs(math.cos(a)),abs(math.sin(a)))))
            pts.append((cx+r*math.cos(a),cy+r*math.sin(a)))
        poly(img,pts,WHITE,3)
    elif kind=="document":
        label(img,"DOCUMENT REVEAL")
        cv2.rectangle(img,(700,300),(1210,770),WHITE,2,cv2.LINE_AA)
        p=min(1,(t/8)*1.5)
        for i in range(7):
            yy=390+i*45; x2=int(850+260*p)
            cv2.line(img,(790,yy),(x2,yy),MUTED,2,cv2.LINE_AA)
        for yy in (480,570): cv2.rectangle(img,(790,yy),(1050,yy+18),RED,-1)
    elif kind=="signal":
        label(img,"SIGNAL PULSE")
        circ(img,(cx,cy),20,RED)
        for i in range(3):
            r=40+((t*70+i*115)%340); circ(img,(cx,cy),r,(int(70+80*(1-r/400)),int(82+60*(1-r/400)),int(100+70*(1-r/400))),2)


def draw(kind,t):
    img=base_frame()
    funcs={"chain":scene_chain,"coast":scene_coast,"ship":scene_ship,"bunker":scene_bunker,"rooms":scene_rooms,"bomb":scene_bomb,"tracer":scene_tracer,"money":scene_money,"alaska":scene_alaska,"submarine":scene_submarine}
    if kind in funcs: funcs[kind](img,t)
    else: primitive(img,t,kind)
    return bloom(img)


CAMERA_PATHS={
    # time, zoom, x-pan, y-pan, roll. Each story gets its own camera language.
    "chain":[(0,1.00,0,0,0),(.28,1.12,-120,-5,-.4),(.58,1.22,115,10,.4),(1,1.00,0,0,0)],
    "coast":[(0,1.03,-105,0,-.7),(.32,1.10,-40,-20,0),(.68,1.22,115,30,.8),(1,1.03,-105,0,-.7)],
    "ship":[(0,1.00,0,40,0),(.35,1.25,-15,-35,1.8),(.72,1.16,35,10,-1.8),(1,1.00,0,40,0)],
    "bunker":[(0,.94,0,50,0),(.36,1.05,0,-20,0),(.70,1.30,0,-135,0),(1,.94,0,50,0)],
    "rooms":[(0,1.00,100,0,0),(.38,1.20,30,-5,0),(.70,1.18,-105,10,0),(1,1.00,100,0,0)],
    "bomb":[(0,1.00,-70,20,-1.2),(.36,1.20,-25,-55,1.0),(.72,1.27,90,65,1.8),(1,1.00,-70,20,-1.2)],
    "tracer":[(0,1.00,240,15,0),(.30,1.10,160,-10,-.5),(.68,1.28,-90,45,.6),(1,1.00,240,15,0)],
    "money":[(0,1.00,170,0,0),(.36,1.18,30,0,0),(.70,1.18,-165,0,0),(1,1.00,170,0,0)],
    "alaska":[(0,1.23,0,30,-1.2),(.38,1.12,-70,-5,.8),(.72,.96,5,0,0),(1,1.23,0,30,-1.2)],
    "submarine":[(0,1.00,135,25,0),(.34,1.16,50,0,-.4),(.70,1.24,-100,-20,.4),(1,1.00,135,25,0)],
    "particle":[(0,1.08,160,0,0),(.5,1.12,0,-30,0),(1,1.08,160,0,0)],
    "path":[(0,1.03,170,50,-1),(.45,1.22,0,-25,1),(.8,1.20,-140,-25,0),(1,1.03,170,50,-1)],
    "radar":[(0,1.00,0,0,0),(.5,1.15,0,0,0),(1,1.00,0,0,0)],
    "network":[(0,1.25,0,0,0),(.45,1.12,-60,-20,0),(1,.96,0,0,0)],
    "counter":[(0,1.00,0,0,0),(.5,1.32,0,5,0),(1,1.00,0,0,0)],
    "morph":[(0,1.05,0,0,-9),(.5,1.28,0,0,9),(1,1.05,0,0,-9)],
    "document":[(0,1.00,0,45,0),(.4,1.24,0,0,0),(.75,1.20,0,-75,0),(1,1.00,0,45,0)],
    "signal":[(0,1.25,0,0,0),(.5,1.00,0,0,0),(1,1.25,0,0,0)],
}


def camera_move(img,t,kind):
    # One continuous move with three editorial beats; no looping camera reset.
    p=max(0.0,min(1.0,t/SECONDS))
    keys=CAMERA_PATHS[kind]
    for a,b in zip(keys,keys[1:]):
        if a[0] <= p <= b[0]:
            u=(p-a[0])/(b[0]-a[0]); u=u*u*(3-2*u)
            vals=[a[i]+(b[i]-a[i])*u for i in range(1,5)]
            break
    else: vals=list(keys[-1][1:])
    zoom,pan_x,pan_y,angle=vals
    mat=cv2.getRotationMatrix2D((W/2,H/2),angle,zoom)
    mat[0,2]+=pan_x; mat[1,2]+=pan_y
    return cv2.warpAffine(img,mat,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)


FOCUS={
    "chain":((300,540),(960,540),(1610,545)), "coast":((520,540),(900,520),(1200,520)),
    "ship":((650,580),(960,460),(1200,620)), "bunker":((960,360),(960,520),(960,700)),
    "rooms":((1320,420),(960,520),(700,590)), "bomb":((650,360),(800,520),(1460,505)),
    "tracer":((450,440),(820,520),(1030,590)), "money":((460,500),(960,500),(1460,500)),
    "alaska":((560,450),(940,500),(1150,500)), "submarine":((650,520),(960,520),(1620,520)),
    "particle":((500,540),(960,530),(1440,530)), "path":((520,540),(960,520),(1380,480)),
    "radar":((960,550),(960,550),(960,550)), "network":((650,400),(960,500),(1200,600)),
    "counter":((960,540),(960,540),(960,540)), "morph":((960,550),(960,550),(960,550)),
    "document":((960,500),(960,500),(960,650)), "signal":((960,550),(960,550),(960,550)),
}

def cinematic_finish(img,t,kind):
    """Atmosphere, depth planes, motivated focus, and a paced opening reveal."""
    p=max(0.0,min(1.0,t/SECONDS)); f=smooth(0,.18,p)
    # Deep, restrained vignette plus a traveling pool of soft light.
    yy,xx=np.ogrid[:H,:W]
    anchors=FOCUS[kind]; u=p*2
    if u<1: a,b,q=anchors[0],anchors[1],u
    else: a,b,q=anchors[1],anchors[2],u-1
    q=q*q*(3-2*q); fx=a[0]*(1-q)+b[0]*q; fy=a[1]*(1-q)+b[1]*q
    rad=((xx-fx)/850)**2+((yy-fy)/600)**2
    light=np.clip(1.0-.28*np.clip(rad,0,1),.58,1.0)
    # Opening from darkness is a scene reveal, then the moving key light guides the eye.
    reveal=np.clip((p-.015)/.18,0,1)
    light*= (.20+.80*reveal)
    out=np.clip(img.astype(np.float32)*light[:,:,None],0,255).astype(np.uint8)
    # Foreground dust moves at a separate rate, adding a visible near plane/parallax cue.
    fg=np.zeros_like(out)
    for i in range(42):
        x=int((i*487 + t*(24+(i%5)*7))%W); y=int((i*263 + math.sin(t*.65+i)*32)%H)
        rr=1 if i%4 else 2
        circ(fg,(x,y),rr,(38,49,62))
    out=cv2.addWeighted(out,1,fg,.48,0)
    # A narrow light sweep crosses the frame during the reveal beat.
    sx=int(-260+W*smooth(.12,.34,p))
    sweep=np.zeros_like(out); cv2.line(sweep,(sx,0),(sx+340,H),(44,34,25),3,cv2.LINE_AA)
    glow=cv2.GaussianBlur(sweep,(0,0),48)
    out=cv2.addWeighted(out,1,glow,.55,0)
    return out


def svg_body(kind):
    # The SVGs are editable vector scenes; CSS/SMIL supplies the motion and grain.
    if kind=="chain":
        return '<g class="flow">'+''.join(f'<rect x="{230+i*300}" y="475" width="170" height="100" rx="20"/><circle cx="{315+i*300}" cy="525" r="17" fill="#ff343b"/>' for i in range(5))+'</g><path class="route" d="M315 525H1515"/>'
    if kind=="coast": return '<path d="M1300 240l-80 170 65 100-90 160 70 170"/><path class="route" d="M500 540Q850 430 1180 540"/><g class="particles">'+''.join(f'<circle cx="{570+i*36}" cy="{490+(i%5)*18}" r="5"/>' for i in range(15))+'</g>'
    if kind in ("ship","submarine"): return '<path d="M420 550h900l-120 90H540zM720 550l90-85h250l90 85"/><path class="route" d="M700 640Q960 760 1230 640"/><circle class="pulse" cx="960" cy="540" r="220"/>'
    if kind=="bunker": return '<path d="M620 440h680v120H620zM520 590h880v210H520z"/><path class="route" d="M960 560v190"/><g class="rooms">'+''.join(f'<rect x="{550+i*165}" y="620" width="130" height="120"/>' for i in range(5))+'</g>'
    if kind=="rooms": return '<rect x="380" y="300" width="1160" height="490"/><path d="M960 300v490"/><path class="route" d="M1320 420L960 500 650 520"/><circle class="pulse" cx="1320" cy="420" r="28"/>'
    if kind=="bomb": return '<path d="M300 340h530l90 30-90 30H300z"/><path class="route" d="M800 410v170h800"/><g class="steps">'+''.join(f'<circle cx="{1050+i*180}" cy="580" r="24"/>' for i in range(4))+'</g>'
    if kind=="tracer": return '<path d="M350 380h190l-25 130H375zM820 330v90l-70 60-40 220h360l-40-220-70-60v-90"/><path class="route" d="M460 500Q700 560 850 500t210 110"/><circle class="particle" r="10"/>'
    if kind=="money": return '<path class="route" d="M460 520h1000"/><g class="steps">'+''.join(f'<circle cx="{460+i*500}" cy="520" r="60"/>' for i in range(3))+'</g><circle class="particle" r="9"/>'
    if kind=="alaska": return '<path d="M420 360l210-70 180 45 170-28 180 70 200 95-100 80-130 15-95 120-160-40-140 55-145-85-160-25-90-130z"/><path class="route" d="M560 450L760 390 940 500 1150 425 1300 540 1010 640z"/><circle class="pulse" cx="760" cy="390" r="40"/>'
    if kind=="particle": return '<path class="route" d="M400 550Q700 350 960 550t560 0"/><circle class="particle" r="10"/>'
    if kind=="path": return '<path class="route" d="M430 650l180-210 220 140 230-220 210 180 220-140"/>'
    if kind=="radar": return '<circle cx="960" cy="550" r="320"/><circle cx="960" cy="550" r="210"/><circle cx="960" cy="550" r="100"/><path class="sweep" d="M960 550L1280 550"/>'
    if kind=="network": return '<path class="route" d="M650 400L900 320 1130 420 700 660 1010 650 1310 590"/><g class="steps">'+''.join(f'<circle cx="{x}" cy="{y}" r="13"/>' for x,y in [(650,400),(900,320),(1130,420),(700,660),(1010,650),(1310,590)])+'</g>'
    if kind=="counter": return '<rect x="680" y="400" width="560" height="300" rx="20"/><text x="960" y="590" text-anchor="middle">0427</text>'
    if kind=="morph": return '<path class="morph" d="M960 350L1133 450L1133 650L960 750L787 650L787 450Z"><animate attributeName="d" dur="4s" repeatCount="indefinite" values="M960 350L1133 450L1133 650L960 750L787 650L787 450Z;M820 380L1100 380L1100 720L820 720L820 720L820 380Z;M960 350L1133 450L1133 650L960 750L787 650L787 450Z"/></path>'
    if kind=="document": return '<rect x="700" y="260" width="520" height="550"/><path class="route" d="M790 390h330M790 450h330M790 510h330M790 570h330M790 630h330"/><path d="M790 475h230M790 595h230" stroke="#ff343b" stroke-width="20"/>'
    return '<circle class="pulse" cx="960" cy="550" r="24"/><circle class="ring" cx="960" cy="550" r="60"/><circle class="ring" cx="960" cy="550" r="130"/>'


def write_svg(name,title,kind):
    body=svg_body(kind)
    keys=CAMERA_PATHS[kind]
    camera_css='@keyframes camera{'+''.join(f'{int(p*100)}%{{transform:translate({x}px,{y}px) scale({z}) rotate({rot}deg)}}' for p,z,x,y,rot in keys)+'}'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
<defs><radialGradient id="bg"><stop stop-color="#151619"/><stop offset="1" stop-color="#020203"/></radialGradient>
<filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".82" numOctaves="2" stitchTiles="stitch" seed="4"><animate attributeName="seed" values="4;12;24;4" dur="1.5s" repeatCount="indefinite"/></feTurbulence><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .22"/></feComponentTransfer></filter>
<style><![CDATA[@keyframes route{{to{{stroke-dashoffset:-900}}}}@keyframes pulse{{0%,100%{{opacity:.35;transform:scale(.8)}}50%{{opacity:1;transform:scale(1.08)}}}}@keyframes sweep{{to{{transform:rotate(360deg)}}}}@keyframes reveal{{0%{{stroke-dashoffset:900}}100%{{stroke-dashoffset:0}}}}@keyframes particle{{0%{{transform:translateX(-300px);opacity:0}}20%,80%{{opacity:1}}100%{{transform:translateX(300px);opacity:0}}}}{camera_css}
svg{{background:#030405}}text{{font:42px sans-serif;fill:#e8edf3}}path,rect,circle{{vector-effect:non-scaling-stroke}}.route{{fill:none;stroke:#dce4ec;stroke-width:3;stroke-dasharray:18 14;animation:route 8s linear infinite}}.flow{{fill:none;stroke:#dce4ec;stroke-width:3;animation:pulse 3s ease-in-out infinite;transform-origin:center}}.pulse{{fill:none;stroke:#ff343b;stroke-width:3;animation:pulse 2s ease-in-out infinite;transform-origin:center}}.ring{{fill:none;stroke:#ff343b;stroke-width:3;animation:pulse 2s ease-in-out infinite;transform-origin:960px 550px}}.sweep{{stroke:#a9e6bd;stroke-width:4;transform-origin:960px 550px;animation:sweep 6s linear infinite}}.steps{{fill:none;stroke:#ecf1f6;stroke-width:3;animation:pulse 3s ease-in-out infinite}}.rooms{{fill:none;stroke:#a6b4c3;stroke-width:2;animation:pulse 4s ease-in-out infinite}}.particles{{fill:#ff343b;animation:particle 4s ease-in-out infinite}}.particle{{fill:#ff343b;animation:particle 3s ease-in-out infinite}}.morph{{fill:none;stroke:#ecf1f6;stroke-width:4;animation:pulse 3s ease-in-out infinite;transform-origin:960px 550px}}
.camera{{transform-origin:960px 540px;animation:camera 8s cubic-bezier(.4,0,.2,1) infinite}}
]]></style></defs>
<rect width="1920" height="1080" fill="url(#bg)"/><g class="camera"><text x="90" y="100" fill="#8693a3" font-size="24">{title}</text><g stroke="#e5ebf1" fill="none" filter="url(#glow)">{body}</g></g><rect width="1920" height="1080" filter="url(#grain)" opacity=".38" style="mix-blend-mode:screen;pointer-events:none"/>
</svg>'''
    (SVG_DIR/f"{name}.svg").write_text(svg,encoding="utf-8")


def main():
    SVG_DIR.mkdir(parents=True,exist_ok=True); VIDEO_DIR.mkdir(parents=True,exist_ok=True); PACK.mkdir(parents=True,exist_ok=True)
    jobs=STORIES+PRIMITIVES
    if len(sys.argv)>1:
        requested=set(sys.argv[1:]); jobs=[job for job in jobs if job[0] in requested]
    manifest={"title":"Visual Venture conspiracy motion pack","resolution":[1920,1080],"fps":FPS,"duration_seconds":SECONDS,"grain":"light monochrome grain across the full frame","assets":[{"id":name,"title":title,"category":"story_scene" if name.startswith(tuple(f'{i:02d}_' for i in range(9,19))) else "motion_primitive","svg":f"assets/{name}.svg","mp4":f"renders/{name}.mp4","camera_path":"scene-specific"} for name,title,kind in STORIES+PRIMITIVES]}
    manifest_path=HERE/"conspiracy_motion_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    shutil.copy2(manifest_path,PACK/manifest_path.name)
    for name,title,kind in jobs:
        write_svg(name,title,kind)
        out=VIDEO_DIR/f"{name}.mp4"
        command=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","bgr24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-pix_fmt","yuv420p","-crf","19","-preset","ultrafast","-movflags","+faststart",str(out)]
        encoder=subprocess.Popen(command,stdin=subprocess.PIPE)
        try:
            for frame in range(FRAMES):
                t=frame/FPS
                image=camera_move(draw(kind,t),t,kind)
                image=cinematic_finish(image,t,kind)
                image=np.clip(image.astype(np.float32)+GRAIN,0,255).astype(np.uint8)
                encoder.stdin.write(image.tobytes())
        finally:
            encoder.stdin.close()
        if encoder.wait()!=0: raise RuntimeError(f"ffmpeg failed for {out.name}")
        shutil.copy2(out,PACK/out.name); shutil.copy2(SVG_DIR/f"{name}.svg",PACK/f"{name}.svg")
        print(f"{name}: SVG + MP4",flush=True)


if __name__=="__main__": main()
