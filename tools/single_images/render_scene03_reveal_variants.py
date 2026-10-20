#!/usr/bin/env python3
"""Render Scene 03 animated reveal examples after the PNG lane mask limitation."""
from __future__ import annotations

import math
import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

SOURCE = Path("/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Scene03_Seated_Desk/Photo_Reveal_Variants/Composition_Preview.png")
OUT = SOURCE.parent
W, H, FPS, SEGMENT = 854, 480, 30, 90
LABELS = ("DRY BRUSH", "WATERCOLOR", "IRIS REVEAL", "DIAGONAL WIPE")
FONT_PATH = OUT / "Inter-Bold.ttf"


def create_matte(style: int, frame: int) -> Image.Image:
    scale = W/854
    matte = Image.new("L", (W,H), 0)
    if frame == 0:
        return matte
    if frame >= 60:
        return Image.new("L", (W,H), 255)
    p = frame/60
    draw = ImageDraw.Draw(matte)
    if style == 0:  # rough bristle edge, with stable long streaks
        boundary = []
        for y in range(int(-12*scale),H+int(20*scale),max(1,int(9*scale))):
            yn = y/scale
            wobble = scale*(12*math.sin(yn*.027) + 7*math.sin(yn*.091+0.7) + 4*math.sin(yn*.21))
            boundary.append((int(W*p+wobble),y))
        draw.polygon([(0,int(-10*scale)),(int(W*p-10*scale),int(-10*scale)),*boundary,
                      (0,H+int(10*scale))],fill=255)
        matte = matte.filter(ImageFilter.GaussianBlur(1.8*scale))
    elif style == 1:  # watercolor blooms from an irregular, evolving perimeter
        cx, cy = W/2, H/2
        points=[]
        for i in range(97):
            angle=2*math.pi*i/96
            ripple=1 + .10*math.sin(5*angle+.3) + .06*math.sin(11*angle+1.4) + .035*math.cos(19*angle)
            rx=(W*.78*p)*ripple
            ry=(H*.79*p)*ripple
            points.append((cx+math.cos(angle)*rx,cy+math.sin(angle)*ry))
        draw.polygon(points,fill=255)
        matte = matte.filter(ImageFilter.GaussianBlur(7*scale))
    elif style == 2:  # cinematic centered iris
        radius=math.hypot(W,H)*.56*p
        draw.ellipse((W/2-radius,H/2-radius,W/2+radius,H/2+radius),fill=255)
        matte = matte.filter(ImageFilter.GaussianBlur(3*scale))
    else:  # diagonal sweep with a gently uneven leading edge
        x=int(W*p)
        points=[(-H,int(-5*scale)),(x-H,int(-5*scale))]
        for y in range(int(-5*scale),H+int(10*scale),max(1,int(10*scale))):
            yn=y/scale
            points.append((x+int(.72*y)+int(3*scale*math.sin(yn*.05)),y))
        points.extend([(-H,H+int(5*scale)),(-H,int(-5*scale))])
        draw.polygon(points,fill=255)
        matte = matte.filter(ImageFilter.GaussianBlur(2*scale))
    return matte


def main() -> None:
    global W, H
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=854)
    parser.add_argument('--height',type=int,default=480)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    W,H=args.width,args.height
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = Image.open(SOURCE).convert("RGB").resize((W,H),Image.Resampling.LANCZOS)
    font_scale=W/854
    font = ImageFont.truetype(str(FONT_PATH), max(1,round(20*font_scale)))
    target = args.output or OUT/f"Scene03_Photo_Reveal_Variants_{W}x{H}.mp4"
    encoder=subprocess.Popen(["ffmpeg","-y","-hide_banner","-loglevel","error",
                              "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
                              "-r",str(FPS),"-i","-","-c:v","libx264",
                              "-preset","medium","-crf","18","-pix_fmt","yuv420p",
                              "-movflags","+faststart",str(target)],stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    try:
        for style_index, title in enumerate(LABELS):
            for frame_index in range(SEGMENT):
                matte = create_matte(style_index, frame_index)
                frame = Image.composite(source, Image.new("RGB",(W,H),(0,0,0)), matte)
                # Keep label visible through the reveal; simple dark plate maintains contrast.
                draw = ImageDraw.Draw(frame, "RGBA")
                bounds = draw.textbbox((0,0),title,font=font)
                tw, th = bounds[2]-bounds[0], bounds[3]-bounds[1]
                x0 = (W-tw)//2-round(16*font_scale)
                top=round(14*font_scale)
                draw.rounded_rectangle((x0,top,x0+tw+round(32*font_scale),
                                        top+th+round(18*font_scale)),
                                       radius=round(8*font_scale),fill=(0,0,0,170))
                draw.text(((W-tw)//2,round(20*font_scale)),title,font=font,fill=(255,255,255,255))
                encoder.stdin.write(frame.tobytes())
    finally:
        encoder.stdin.close()
    if encoder.wait()!=0:
        raise RuntimeError('FFmpeg failed to encode the reveal video')
    print(target)


if __name__ == "__main__":
    main()
