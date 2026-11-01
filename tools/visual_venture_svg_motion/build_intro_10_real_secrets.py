"""Build and render the story-led, all-SVG Visual Venture opening."""
from pathlib import Path
import os
import shutil
import subprocess

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SVG_OUT = ROOT / "assets" / "intro_10_real_secrets_30s.svg"
MP4_OUT = ROOT / "renders" / "intro_10_real_secrets_30s.mp4"
PACK = Path(__file__).resolve().parents[3] / "assets" / "chronon_visual_venture_pack"
W, H, FPS, DURATION = 1920, 1080, 24, 30


def svg_source():
    # The four paths share the same cubic topology: the central evidence mark
    # really morphs between an isotope, bay, falling device and dossier.
    isotope = "M960 320 C1085 320 1190 430 1190 540 C1190 650 1085 760 960 760 C835 760 730 650 730 540 C730 430 835 320 960 320 Z"
    bay = "M960 320 C1080 400 1150 465 1190 540 C1100 560 1080 650 960 760 C850 675 820 610 730 540 C830 490 850 405 960 320 Z"
    bomb = "M960 320 C1025 410 1100 490 1160 540 C1100 590 1025 670 960 760 C895 670 820 590 760 540 C820 490 895 410 960 320 Z"
    file = "M840 320 C1000 320 1100 320 1190 350 C1190 470 1190 630 1190 730 C1080 760 950 760 730 730 C730 620 730 475 730 350 C760 335 800 325 840 320 Z"
    nodes = []
    for i in range(58):
        x = (i * 331 + 87) % W
        y = (i * 197 + 43) % H
        r = 1.4 if i % 4 else 2.4
        nodes.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#cad4df" opacity=".22"><animate attributeName="opacity" values=".08;.32;.08" dur="{2.1 + (i % 7) * .43:.2f}s" begin="-{(i % 11) * .29:.2f}s" repeatCount="indefinite"/></circle>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080">
<title>Visual Venture — 10 Real Secrets | narrative SVG intro</title>
<desc>Thirty-second vector sequence: radioactive fallout entering a food chain and bone; a biological cloud crossing San Francisco Bay; the Goldsboro bomber and safety switch; declassified evidence converging into the title, then a line leading into Project Sunshine. All illustrations are schematic, not archival reconstructions.</desc>
<defs>
 <radialGradient id="bg"><stop stop-color="#111820"/><stop offset=".55" stop-color="#070a0e"/><stop offset="1" stop-color="#010203"/></radialGradient>
 <radialGradient id="redCore"><stop stop-color="#fff"/><stop offset=".18" stop-color="#ff4148" stop-opacity=".95"/><stop offset="1" stop-color="#ff343b" stop-opacity="0"/></radialGradient>
 <linearGradient id="steel" x2="0" y2="1"><stop stop-color="#edf2f7" stop-opacity=".86"/><stop offset="1" stop-color="#73869b" stop-opacity=".38"/></linearGradient>
 <filter id="glow" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <filter id="soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="22"/></filter>
 <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".78" numOctaves="2" seed="27"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .16"/></feComponentTransfer></filter>
 <clipPath id="bayClip"><path d="M920 184 C1000 235 1105 283 1162 372 C1198 430 1188 490 1134 522 C1080 555 1056 603 1034 680 C1018 738 976 803 916 840 C854 803 832 741 839 682 C850 591 811 558 748 521 C684 484 668 414 715 348 C768 274 840 224 920 184Z"/></clipPath>
 <path id="morphA" d="{isotope}"/><path id="morphB" d="{bay}"/><path id="morphC" d="{bomb}"/><path id="morphD" d="{file}"/>
 </defs>
<rect width="1920" height="1080" fill="url(#bg)"/>
<g>{''.join(nodes)}</g>
<!-- subdued archival grid, parallax guide marks, and continuous white grain -->
<g stroke="#6d8094" opacity=".12" fill="none"><path d="M0 180H1920M0 900H1920"/><path d="M150 0V1080M1770 0V1080"/><circle cx="960" cy="540" r="390"/><circle cx="960" cy="540" r="520" stroke-dasharray="2 18"/></g>

<!-- 00–05: fallout traverses grass, livestock, milk, then enters bone. -->
<g id="sunshine">
 <animate attributeName="opacity" values="1;1;1;0" keyTimes="0;.08;.78;1" dur="5.45s" fill="freeze"/>
 <animateTransform attributeName="transform" type="translate" values="0 34;0 0;0 -8" keyTimes="0;.06;1" dur="5.4s" fill="freeze"/>
 <g opacity=".7" fill="#ff4148" filter="url(#soft)"><circle cx="960" cy="298" r="128"><animate attributeName="r" values="70;155;100" dur="4.7s" fill="freeze"/></circle></g>
 <g fill="#ff454b" filter="url(#glow)">{''.join(f'<circle cx="{740+(i*173)%440}" cy="{155+(i*89)%310}" r="{2+i%4}" opacity=".75"><animate attributeName="cy" values="{155+(i*89)%310};650" dur="{1.2+(i%7)*.21:.2f}s" begin="{(i%17)*.13:.2f}s" fill="freeze"/><animate attributeName="opacity" values=".8;.25;0" dur="{1.2+(i%7)*.21:.2f}s" begin="{(i%17)*.13:.2f}s" fill="freeze"/></circle>' for i in range(48))}</g>
 <!-- linked food-chain path draws from left to right -->
 <path d="M190 648 C330 580 400 580 530 648 S730 716 850 648 S1050 580 1190 648 S1400 716 1540 648 S1710 585 1780 648" fill="none" stroke="#dbe4ed" stroke-opacity=".35" stroke-width="2" stroke-dasharray="1500" stroke-dashoffset="1500" filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="1500" to="0" begin=".3s" dur="3.6s" fill="freeze"/></path>
 <g fill="none" stroke="url(#steel)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)">
   <!-- grass --> <path d="M260 665Q248 622 226 594M260 665Q258 610 270 579M260 665Q280 622 307 602M220 666H310"/>
   <!-- cow profile, intentionally graphic and legible --> <path d="M450 628Q464 590 517 590H587Q613 590 628 620L655 632 648 649 616 651 607 701 594 701 588 651H512L504 701H490L485 650Q455 648 450 628ZM585 592 596 566 605 590M457 604 440 590M450 628 431 621 430 610 447 611"/>
   <!-- milk vessel --> <path d="M773 592H849L841 610 858 687Q859 699 847 700H775Q763 699 766 687L782 610ZM779 627H847"/>
   <!-- stylized x-ray bone, catches the red tracer --> <path d="M1538 619Q1520 596 1541 581Q1560 568 1577 586L1650 659Q1665 645 1684 657Q1706 673 1687 693Q1671 709 1652 695Q1633 714 1614 697Q1598 681 1612 663L1544 596Q1524 611 1538 619Z" stroke="#f2f5f8" stroke-width="6"/>
 </g>
 <g fill="#ff4148" filter="url(#glow)"><circle r="7"><animateMotion path="M260 648 C420 565 520 648 620 648 S790 710 815 648 S1030 584 1150 648 S1400 700 1615 648" dur="3.2s" begin=".65s" fill="freeze"/></circle><circle r="4"><animateMotion path="M260 648 C420 565 520 648 620 648 S790 710 815 648 S1030 584 1150 648 S1400 700 1615 648" dur="3.2s" begin="1s" fill="freeze"/></circle></g>
 <circle cx="1610" cy="650" r="70" fill="url(#redCore)" opacity=".85" filter="url(#glow)"/>
 <path d="M960 320 C1085 320 1190 430 1190 540 C1190 650 1085 760 960 760 C835 760 730 650 730 540 C730 430 835 320 960 320 Z" fill="none" stroke="#edf2f7" stroke-width="2" opacity=".25"><animate attributeName="d" values="{isotope};{bay}" keyTimes="0;1" begin="4.1s" dur=".85s" fill="freeze"/></path>
</g>

<!-- 05–10: schematic Bay Area map; cloud disperses from ship into city. -->
<g id="seaspray" opacity="0">
 <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.04;.85;1" begin="4.75s" dur="5.4s" fill="freeze"/>
 <animateTransform attributeName="transform" type="scale" values="1.12;1;1.045" keyTimes="0;.4;1" begin="4.75s" dur="5.4s" additive="sum" fill="freeze"/>
 <path d="M920 184 C1000 235 1105 283 1162 372 C1198 430 1188 490 1134 522 C1080 555 1056 603 1034 680 C1018 738 976 803 916 840 C854 803 832 741 839 682 C850 591 811 558 748 521 C684 484 668 414 715 348 C768 274 840 224 920 184Z" fill="#101b25" stroke="#8597aa" stroke-width="3"/>
 <path d="M1110 236C1200 290 1250 354 1263 432M1100 680C1170 625 1235 592 1310 586" fill="none" stroke="#63758a" stroke-width="2" stroke-dasharray="5 11" opacity=".6"/>
 <g clip-path="url(#bayClip)" fill="none" stroke="#7e91a6" opacity=".45"><path d="M682 370H1220M680 430H1220M680 490H1220M680 550H1220M680 610H1220M680 670H1220M680 730H1220"/><path d="M760 170V880M830 170V880M900 170V880M970 170V880M1040 170V880M1110 170V880"/></g>
 <!-- coastline city lights --> <g fill="#dce5ee">{''.join(f'<circle cx="{710+(i*53)%440}" cy="{250+(i*97)%540}" r="{1.7+(i%3)*.7}" opacity=".65"/>' for i in range(70))}</g>
 <path d="M540 730Q595 694 650 730L672 750 626 762H556Z" fill="#111923" stroke="#e1e8ef" stroke-width="2"/>
 <path d="M565 715L592 690 620 715M574 715V738M600 712V739M628 715V739" fill="none" stroke="#e1e8ef" stroke-width="2"/>
 <circle cx="605" cy="730" r="18" fill="none" stroke="#ff4148" stroke-width="2" filter="url(#glow)"><animate attributeName="r" values="12;90;150" begin="5.1s" dur="3.3s" fill="freeze"/><animate attributeName="opacity" values="1;.6;0" begin="5.1s" dur="3.3s" fill="freeze"/></circle>
 <g fill="#ff4148" filter="url(#glow)">{''.join(f'<circle cx="620" cy="710" r="{2+i%4}" opacity=".85"><animate attributeName="cx" values="620;{780+(i*43)%360}" begin="{5.25+(i%14)*.08:.2f}s" dur="{1.3+(i%6)*.24:.2f}s" fill="freeze"/><animate attributeName="cy" values="710;{280+(i*61)%440}" begin="{5.25+(i%14)*.08:.2f}s" dur="{1.3+(i%6)*.24:.2f}s" fill="freeze"/><animate attributeName="opacity" values=".9;.55;0" begin="{5.25+(i%14)*.08:.2f}s" dur="{1.3+(i%6)*.24:.2f}s" fill="freeze"/></circle>' for i in range(38))}</g>
 <path d="M960 320 C1080 400 1150 465 1190 540 C1100 560 1080 650 960 760 C850 675 820 610 730 540 C830 490 850 405 960 320 Z" fill="none" stroke="#ff4148" stroke-width="3" opacity=".7" filter="url(#glow)"/>
 <g font-family="Arial,sans-serif" fill="#dce5ee" letter-spacing="4"><text x="1280" y="360" font-size="18" opacity=".6">PACIFIC</text><text x="1280" y="397" font-size="22">SAN FRANCISCO</text><path d="M1250 405H1510" stroke="#ff4148" stroke-width="2"/><text x="1280" y="448" font-size="14" opacity=".58">BIOLOGICAL DISPERSAL / 1950</text></g>
</g>

<!-- 10–15: B-52 silhouette; two falling devices; close on the safety switch. -->
<g id="goldsboro" opacity="0">
 <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.04;.88;1" begin="9.6s" dur="5.8s" fill="freeze"/>
 <animateTransform attributeName="transform" type="translate" values="0 22;0 0;0 -20" keyTimes="0;.12;1" begin="9.6s" dur="5.8s" fill="freeze"/>
 <g transform="translate(960 330)" fill="#17212b" stroke="#dce5ee" stroke-width="3" stroke-linejoin="round">
  <path d="M0 -155L28 -44 310 22 310 50 48 24 26 70 80 110 80 130 0 95 -80 130 -80 110 -26 70 -48 24 -310 50 -310 22 -28 -44Z"/>
  <path d="M-270 24L-242 20M270 24L242 20" stroke="#ff4148" stroke-width="4"/>
 </g>
 <g fill="#ff4148" filter="url(#glow)"><path d="M0 -30L17 0 0 70 -17 0Z" transform="translate(820 500)"><animateTransform attributeName="transform" type="translate" values="820 500;820 855" begin="10.55s" dur="2.2s" fill="freeze"/></path><path d="M0 -30L17 0 0 70 -17 0Z" transform="translate(1100 500)"><animateTransform attributeName="transform" type="translate" values="1100 500;1100 855" begin="10.85s" dur="2.2s" fill="freeze"/></path></g>
 <path d="M820 550V836M1100 550V836" stroke="#ff4148" stroke-width="2" stroke-dasharray="5 13" opacity=".58"><animate attributeName="opacity" values="0;.7;.4;0" keyTimes="0;.2;.8;1" begin="10.5s" dur="2.6s" fill="freeze"/></path>
 <g transform="translate(1490 540)">
   <circle r="160" fill="#0d1319" stroke="#64778b" stroke-width="2"/><circle r="129" fill="none" stroke="#273642" stroke-width="2" stroke-dasharray="2 9"/>
   <path d="M-88 15V-46Q-88-105-28-105H42Q93-105 93-50V18" fill="none" stroke="#dbe4ec" stroke-width="9" stroke-linecap="round"/>
   <path d="M-83 18H83" stroke="#dbe4ec" stroke-width="8" stroke-linecap="round"/>
   <path d="M0 20V-49" stroke="#ff4148" stroke-width="7" stroke-linecap="round" transform="rotate(-55)"><animateTransform attributeName="transform" type="rotate" values="-55 0 20;15 0 20;15 0 20" keyTimes="0;.5;1" begin="10.8s" dur="2.3s" fill="freeze"/></path>
   <circle cx="-102" cy="-90" r="8" fill="#ff4148"><animate attributeName="fill" values="#ff4148;#ff4148;#64d7a2" keyTimes="0;.48;1" begin="10.8s" dur="2.3s" fill="freeze"/></circle>
   <circle cx="101" cy="-90" r="8" fill="#ff4148"><animate attributeName="fill" values="#ff4148;#ff4148;#64d7a2" keyTimes="0;.48;1" begin="10.8s" dur="2.3s" fill="freeze"/></circle>
   <text x="0" y="118" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#8192a3" letter-spacing="3">SAFE / ARMED</text>
 </g>
 <path d="M960 320 C1025 410 1100 490 1160 540 C1100 590 1025 670 960 760 C895 670 820 590 760 540 C820 490 895 410 960 320 Z" fill="none" stroke="#edf2f7" stroke-width="2" opacity=".22"/>
</g>

<!-- 15–21: three evidence sheets stack, stamp, and converge. -->
<g id="files" opacity="0">
 <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.02;.83;1" begin="14.6s" dur="6.8s" fill="freeze"/>
 <g fill="#10161d" stroke="#8192a3" stroke-width="2" filter="url(#glow)">
  <g><animateTransform attributeName="transform" type="translate" values="-600 90;-120 22;0 0;0 -80" keyTimes="0;.45;.82;1" begin="14.8s" dur="6.4s" fill="freeze"/><animateTransform attributeName="transform" additive="sum" type="rotate" values="-12; -5;0;0" keyTimes="0;.55;.82;1" begin="14.8s" dur="6.4s" fill="freeze"/><rect x="380" y="250" width="470" height="590"/><path d="M430 332H775" stroke="#dce5ee"/><path d="M430 390H740M430 430H780M430 470H690M430 550H770M430 590H745M430 630H765M430 690H640" stroke="#62758a"/><path d="M430 470H610" stroke="#ff4148" stroke-width="11"/><text x="430" y="305" fill="#e5ebf1" stroke="none" font-family="Arial" font-size="19" letter-spacing="3">PROJECT SUNSHINE</text></g>
  <g><animateTransform attributeName="transform" type="translate" values="600 -60;110 8;0 0;0 -80" keyTimes="0;.45;.82;1" begin="14.8s" dur="6.4s" fill="freeze"/><animateTransform attributeName="transform" additive="sum" type="rotate" values="10;4;0;0" keyTimes="0;.55;.82;1" begin="14.8s" dur="6.4s" fill="freeze"/><rect x="1070" y="255" width="470" height="590"/><path d="M1120 337H1465" stroke="#dce5ee"/><path d="M1120 395H1420M1120 435H1470M1120 475H1380M1120 555H1460M1120 595H1435M1120 635H1450M1120 695H1320" stroke="#62758a"/><path d="M1120 475H1330" stroke="#ff4148" stroke-width="11"/><text x="1120" y="310" fill="#e5ebf1" stroke="none" font-family="Arial" font-size="19" letter-spacing="3">OPERATION SEA-SPRAY</text></g>
  <g><animateTransform attributeName="transform" type="translate" values="0 600;0 100;0 0;0 -80" keyTimes="0;.45;.82;1" begin="14.8s" dur="6.4s" fill="freeze"/><rect x="725" y="310" width="470" height="590"/><path d="M775 392H1120" stroke="#dce5ee"/><path d="M775 450H1080M775 490H1130M775 530H1040M775 610H1120M775 650H1095M775 690H1110M775 750H980" stroke="#62758a"/><path d="M775 530H990" stroke="#ff4148" stroke-width="11"/><text x="775" y="365" fill="#e5ebf1" stroke="none" font-family="Arial" font-size="19" letter-spacing="3">GOLDSBORO / NORTH CAROLINA</text></g>
 </g>
 <g transform="translate(960 550) rotate(-9)" opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.3;.8;1" begin="16s" dur="4.3s" fill="freeze"/><rect x="-180" y="-58" width="360" height="116" rx="5" fill="#10161d" stroke="#ff4148" stroke-width="4"/><text text-anchor="middle" y="14" font-family="Arial,sans-serif" font-weight="700" font-size="37" letter-spacing="8" fill="#ff4148">DECLASSIFIED</text></g>
 <path d="M840 320 C1000 320 1100 320 1190 350 C1190 470 1190 630 1190 730 C1080 760 950 760 730 730 C730 620 730 475 730 350 C760 335 800 325 840 320 Z" fill="none" stroke="#edf2f7" stroke-width="2" opacity=".22"/>
</g>

<!-- continuous central mark morphs with the story: atom -> bay -> device -> file -->
<path id="evidenceMorph" d="{isotope}" fill="none" stroke="#ff4148" stroke-width="3" opacity=".38" filter="url(#glow)" stroke-dasharray="1000 0">
 <animate attributeName="d" values="{isotope};{bay};{bomb};{file};{isotope}" keyTimes="0;.17;.34;.51;1" begin="0s" dur="30s" fill="freeze"/>
 <animate attributeName="opacity" values=".38;.16;.42;.20;.4;0" keyTimes="0;.18;.34;.51;.67;1" dur="30s" fill="freeze"/>
</path>

<!-- 21–26: evidence retracts into a bold centered title, red underline wipes on. -->
<g id="title" opacity="0">
 <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.82;1" begin="20.7s" dur="5.8s" fill="freeze"/>
 <animateTransform attributeName="transform" type="translate" values="0 28;0 0;0 0;0 -24" keyTimes="0;.25;.8;1" begin="20.7s" dur="5.8s" fill="freeze"/>
 <path d="M210 520H1710" stroke="#dce5ee" stroke-width="1" opacity=".28"/>
 <text x="960" y="535" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="128" font-weight="700" letter-spacing="10" fill="#f0f3f6" filter="url(#glow)">10 REAL SECRETS</text>
 <path d="M385 590H1535" stroke="#ff4148" stroke-width="5" stroke-dasharray="1150" stroke-dashoffset="1150" filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="1150" to="0" begin="21.9s" dur="1.15s" fill="freeze"/></path>
 <text x="960" y="652" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="21" letter-spacing="8" fill="#9ba9b8">CLASSIFIED HISTORY  /  VISUAL VENTURE</text>
 <g fill="#ff4148" filter="url(#glow)">{''.join(f'<circle cx="{460+i*125}" cy="590" r="4"><animate attributeName="cy" values="{590+(i%3-1)*90};590" begin="{21.4+i*.09:.2f}s" dur=".8s" fill="freeze"/></circle>' for i in range(9))}</g>
</g>

<!-- 26–30: typography collapses into a lead line that reveals the opening scene. -->
<g id="handoff" opacity="0">
 <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.78;1" begin="25.6s" dur="4.4s" fill="freeze"/>
 <path d="M960 0V1080" stroke="#ff4148" stroke-width="3" stroke-dasharray="1080" stroke-dashoffset="1080" filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="1080" to="0" begin="26s" dur="1.1s" fill="freeze"/></path>
 <circle cx="960" cy="540" r="10" fill="#f2f5f7" filter="url(#glow)"><animate attributeName="r" values="10;46;8" keyTimes="0;.45;1" begin="26.3s" dur="2.2s" fill="freeze"/></circle>
 <g fill="#ff4148" filter="url(#glow)">{''.join(f'<circle cx="960" cy="{250+i*64}" r="3"><animate attributeName="cx" values="960;{300+i*165};960" begin="{26.4+i*.08:.2f}s" dur="2.5s" fill="freeze"/></circle>' for i in range(9))}</g>
 <path d="M960 540C960 540 1120 540 1440 540" fill="none" stroke="#f1f4f7" stroke-width="2" stroke-dasharray="490" stroke-dashoffset="490"><animate attributeName="stroke-dashoffset" from="490" to="0" begin="27.4s" dur="1.2s" fill="freeze"/></path>
 <text x="960" y="985" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" letter-spacing="6" fill="#718196" opacity=".8">THE FIRST FILE OPENS</text>
</g>

<rect width="1920" height="1080" filter="url(#grain)" opacity=".14" pointer-events="none"/>
<rect x="0" y="0" width="1920" height="1080" fill="none" stroke="#000" stroke-width="130" opacity=".27" pointer-events="none"/>
</svg>'''


def render(svg_path: Path, output: Path):
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "ultrafast", "-movflags", "+faststart", str(output)
    ], stdin=subprocess.PIPE, bufsize=0)
    svg_url = svg_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Render the vector at half the final raster size, then upscale with
        # Lanczos. This keeps SVG geometry crisp while making the 720-frame
        # headless-browser render practical on a workstation.
        rw, rh = W // 2, H // 2
        page = browser.new_page(viewport={"width": rw, "height": rh}, device_scale_factor=1)
        page.goto(svg_url, wait_until="load")
        page.evaluate("""() => {
          const svg = document.documentElement;
          svg.style.width = '100vw'; svg.style.height = '100vh'; svg.style.display = 'block';
          svg.pauseAnimations();
        }""")
        for n in range(FPS * DURATION):
            t = n / FPS
            page.evaluate("t => document.documentElement.setCurrentTime(t)", t)
            raw = page.screenshot(type="jpeg", quality=91, animations="allow")
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if frame is None or frame.shape[:2] != (rh, rw):
                raise RuntimeError(f"SVG frame render failed at {t:.3f}s")
            frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_LANCZOS4)
            payload = memoryview(frame).cast("B")
            while payload:
                written = os.write(ff.stdin.fileno(), payload)
                if written <= 0:
                    raise RuntimeError(f"ffmpeg pipe closed at {t:.3f}s")
                payload = payload[written:]
            if n % (FPS * 5) == 0:
                print(f"Rendered {t:05.1f}s / {DURATION}s", flush=True)
        browser.close()
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg encode failed")


def main():
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    MP4_OUT.parent.mkdir(parents=True, exist_ok=True)
    PACK.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(svg_source(), encoding="utf-8")
    render(SVG_OUT, MP4_OUT)
    shutil.copy2(SVG_OUT, PACK / SVG_OUT.name)
    shutil.copy2(MP4_OUT, PACK / MP4_OUT.name)
    print(f"Created {SVG_OUT} and {MP4_OUT}", flush=True)


if __name__ == "__main__":
    main()
