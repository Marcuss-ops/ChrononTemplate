#!/usr/bin/env python3
"""Prepare transparent image layers for the two green-screen rig proofs."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[2] / "assets" / "social_rig_proof_v1"
OUT = ROOT / "processed"


def polygon_mask(size, points, feather=0.45):
    scale = 4
    mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    ImageDraw.Draw(mask).polygon([(x * scale, y * scale) for x, y in points], fill=255)
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    return mask.filter(ImageFilter.GaussianBlur(feather)) if feather else mask


def cutout(image, mask):
    out = image.copy()
    alpha = Image.composite(mask, Image.new("L", image.size, 0), image.getchannel("A"))
    out.putalpha(alpha)
    return out


OUT.mkdir(parents=True, exist_ok=True)
actor = Image.open(OUT / "keanu_wave_keyed.png").convert("RGBA")
size = actor.size

# Whole head, hair, beard and neck down to the shirt collar. The pivot sits at
# the lower neck; the torso plate beneath it closes the joint during motion.
head = [(694, 22), (762, 28), (835, 58), (887, 116), (920, 190), (937, 270),
        (928, 351), (900, 423), (873, 485), (849, 531), (826, 571), (795, 606),
        (765, 636), (741, 663), (716, 683), (687, 692), (655, 680), (627, 656),
        (600, 630), (574, 599), (548, 558), (520, 511), (495, 457), (478, 392),
        (468, 320), (475, 240), (495, 166), (532, 99), (589, 48)]
cutout(actor, polygon_mask(size, head)).save(OUT / "keanu_head_layer.png")

# Viewer-right arm, with overlaps at each joint so rigid part rotations cannot
# open a seam. Pivots are shoulder (1000,610), elbow (1548,822), wrist (1398,432).
upper_arm = [(970, 586), (1031, 586), (1090, 601), (1162, 624), (1230, 654),
             (1304, 686), (1378, 718), (1444, 756), (1502, 789), (1558, 812),
             (1590, 832), (1590, 858), (1560, 880), (1522, 881), (1478, 862),
             (1428, 839), (1378, 818), (1320, 795), (1260, 770), (1194, 744),
             (1129, 714), (1066, 684), (1000, 657)]
forearm = [(1518, 800), (1549, 798), (1582, 816), (1601, 843), (1594, 872),
           (1570, 889), (1544, 882), (1511, 864), (1487, 835), (1468, 799),
           (1449, 751), (1432, 697), (1415, 640), (1397, 581), (1381, 527),
           (1368, 480), (1362, 444), (1370, 419), (1395, 412), (1421, 428),
           (1440, 465), (1461, 512), (1481, 565), (1498, 620), (1511, 681),
           (1520, 740)]
hand = [(1364, 449), (1345, 424), (1317, 389), (1282, 346), (1246, 302),
        (1210, 258), (1174, 217), (1147, 183), (1137, 158), (1144, 137),
        (1163, 132), (1190, 151), (1223, 186), (1251, 221), (1221, 180),
        (1190, 139), (1177, 116), (1186, 96), (1207, 95), (1234, 121),
        (1269, 160), (1244, 119), (1231, 98), (1237, 78), (1257, 74),
        (1284, 101), (1312, 138), (1290, 98), (1285, 77), (1298, 61),
        (1318, 65), (1343, 93), (1364, 132), (1374, 184), (1380, 239),
        (1386, 296), (1391, 353), (1401, 403), (1412, 430)]
cutout(actor, polygon_mask(size, upper_arm)).save(OUT / "keanu_upper_arm.png")
cutout(actor, polygon_mask(size, forearm)).save(OUT / "keanu_forearm.png")
cutout(actor, polygon_mask(size, hand)).save(OUT / "keanu_wave_hand.png")

# Finger chains are cut from one keyed photo. Adjacent segments overlap across
# the joint crease; the parent-child transforms provide actual articulated bends.
hand_img = Image.open(OUT / "hand_keyed.png").convert("RGBA")
hs = hand_img.size
def capsule(start, end, half_width, extend=10):
    import math
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    ex, ey = dx / length * extend, dy / length * extend
    a = (start[0] - ex, start[1] - ey)
    b = (end[0] + ex, end[1] + ey)
    return [(a[0] + nx * half_width, a[1] + ny * half_width),
            (b[0] + nx * half_width, b[1] + ny * half_width),
            (b[0] - nx * half_width, b[1] - ny * half_width),
            (a[0] - nx * half_width, a[1] - ny * half_width)]

fingers = {
    "pinky": ([(121, 328), (153, 319), (178, 386), (202, 458), (228, 531),
               (263, 584), (276, 615), (264, 644), (235, 650), (207, 625),
               (190, 589), (169, 530), (145, 463), (126, 397)],
              [(242, 575), (211, 479), (178, 390), (138, 330)], 44),
    "ring": ([(286, 163), (321, 158), (343, 177), (349, 256), (359, 338),
              (369, 421), (380, 500), (386, 548), (367, 580), (333, 582),
              (311, 554), (304, 478), (298, 397), (292, 315)],
             [(376, 561), (361, 444), (346, 309), (337, 163)], 45),
    "middle": ([(435, 90), (479, 86), (503, 105), (510, 210), (514, 318),
                (519, 424), (520, 528), (501, 566), (470, 580), (443, 551),
                (440, 431), (438, 320), (436, 208)],
               [(511, 560), (509, 423), (501, 302), (486, 91)], 46),
    "index": ([(624, 171), (660, 167), (681, 188), (682, 278), (678, 370),
               (675, 459), (667, 544), (648, 578), (618, 580), (599, 553),
               (598, 512), (602, 429), (607, 339), (615, 252)],
              [(656, 564), (665, 463), (667, 355), (673, 171)], 42),
    "thumb": ([(684, 743), (710, 680), (755, 621), (815, 574), (876, 537),
               (923, 542), (966, 570), (996, 602), (1001, 625), (984, 648),
               (950, 651), (905, 638), (864, 649), (817, 687), (775, 742),
               (740, 798), (712, 789)],
              [(744, 777), (820, 694), (895, 625), (980, 600)], 58),
}
digit_masks = []
for name, (silhouette, joints, width) in fingers.items():
    digit = polygon_mask(hs, silhouette, feather=0.25)
    digit_masks.append(digit)
    for i in range(3):
        band = polygon_mask(hs, capsule(joints[i], joints[i + 1], width, extend=34), feather=0)
        segment = ImageChops.multiply(digit, band)
        cutout(hand_img, segment).save(OUT / f"hand_{name}_{i+1}.png")

# Palm and wrist remain fixed. Remove only finger silhouettes from the palm plate;
# the same pixels are restored by the articulated segment layers.
digits = Image.new("L", hs, 0)
for mask in digit_masks:
    digits = ImageChops.lighter(digits, mask)
palm_mask = ImageChops.invert(digits)
cutout(hand_img, palm_mask).save(OUT / "hand_palm_wrist.png")

print(f"Prepared rig layers from {size[0]}x{size[1]} actor and {hs[0]}x{hs[1]} hand sources")
