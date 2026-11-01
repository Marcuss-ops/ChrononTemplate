"""
Chronon Vector Motion Engine - Visual Venture Suite (Extended & Enriched Edition)
8.0 seconds (240 frames @ 30fps) of rich, cinematic, procedural vector motion.
"""
import os, sys, math, time, subprocess, shutil
import cv2
import numpy as np

OUTPUT_DIR = r"C:\Users\pater\Pyt\assets\chronon_visual_venture_pack"
CHRONON_RENDERS_DIR = r"C:\Users\pater\Pyt\chronons\ChrononTemplate\tools\visual_venture_svg_motion\renders"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHRONON_RENDERS_DIR, exist_ok=True)

W, H = 1920, 1080
FPS = 30
TOTAL_FRAMES = 240  # 8 seconds at 30 fps

def create_base_canvas():
    canvas = np.zeros((H, W, 3), dtype=np.uint8)
    canvas[:, :] = [6, 4, 4]  # Pure deep black/dark vignette BGR
    return canvas

def draw_bloom(img, radius=21, intensity=0.75):
    ksize = radius if radius % 2 == 1 else radius + 1
    blur = cv2.GaussianBlur(img, (ksize, ksize), 0)
    return cv2.addWeighted(img, 1.0, blur, intensity, 0)

# ==============================================================================
# 01: Reticle Target Scanner & Threat Lock-on (8 Seconds Multi-Stage)
# ==============================================================================
def render_frame_01(f):
    t = f / float(TOTAL_FRAMES)  # 0.0 to 1.0
    img = create_base_canvas()
    overlay = np.zeros_like(img)

    # 1. Header Telemetry & Coordinates (blinking live)
    lat = 37.2431 + math.sin(t * 10) * 0.0015
    lon = -115.7930 + math.cos(t * 8) * 0.0018
    cv2.putText(overlay, f"SECTOR SCAN // COORD: {lat:.4f} N, {lon:.4f} W", (80, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 175, 190), 1, cv2.LINE_AA)
    phase_str = "PHASE: RECON SCAN" if f < 70 else ("PHASE: TARGET ACQUISITION" if f < 140 else "PHASE: THREAT LOCK ENGAGED")
    cv2.putText(overlay, phase_str, (80, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 200, 50) if f >= 70 else (140, 150, 165), 1, cv2.LINE_AA)

    # 2. Top Emitter & Dynamic Conical Spotlight
    em_x, em_y = 960, 50
    cv2.circle(overlay, (em_x, em_y), 18, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(overlay, (em_x, em_y), 32, (255, 255, 255), 1, cv2.LINE_AA)

    beam_sway = math.sin(t * math.pi * 4.0) * 45.0
    pts_beam = np.array([
        [em_x, em_y],
        [int(1280 + beam_sway), 940],
        [int(640 + beam_sway), 940]
    ], np.int32)
    beam_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.fillPoly(beam_mask, [pts_beam], 255)
    beam_layer = np.zeros_like(img)
    beam_layer[beam_mask > 0] = [255, 255, 255]
    beam_alpha = 0.09 + 0.04 * math.sin(t * math.pi * 8.0)
    img = cv2.addWeighted(img, 1.0, beam_layer, beam_alpha, 0)

    # 3. Floating Target Nodes (White origin + 3 Amber targets)
    float_y = math.sin(t * math.pi * 3.0) * 6.0
    spheres = [
        (855, int(540 + float_y), 32, (255, 255, 255)),
        (945, int(525 - float_y * 0.7), 22, (50, 215, 255)),
        (1015, int(515 + float_y * 0.5), 17, (50, 215, 255)),
        (1085, int(508 - float_y * 0.3), 13, (50, 215, 255))
    ]
    for sx, sy, srad, scol in spheres:
        cv2.circle(overlay, (sx, sy), srad, scol, -1, cv2.LINE_AA)
        cv2.circle(overlay, (sx, sy), srad + 6, scol, 1, cv2.LINE_AA)

    # 4. Mechanical Targeting Brackets [ ]
    if f < 60:
        p_in = math.sin((f / 60.0) * (math.pi / 2.0))
        l_x = int(700 + (805 - 700) * p_in)
        r_x = int(1240 - (1240 - 1135) * p_in)
        b_alpha = p_in
    else:
        breath = math.sin((f - 60) * 0.1) * 5.0
        l_x = int(805 + breath)
        r_x = int(1135 - breath)
        b_alpha = 1.0

    b_col = (int(255 * b_alpha), int(255 * b_alpha), int(255 * b_alpha))
    # Draw bracket arms with corner notches
    cv2.line(overlay, (l_x + 40, 460), (l_x, 460), b_col, 4, cv2.LINE_AA)
    cv2.line(overlay, (l_x, 460), (l_x, 590), b_col, 4, cv2.LINE_AA)
    cv2.line(overlay, (l_x, 590), (l_x + 40, 590), b_col, 4, cv2.LINE_AA)

    cv2.line(overlay, (r_x - 40, 460), (r_x, 460), b_col, 4, cv2.LINE_AA)
    cv2.line(overlay, (r_x, 460), (r_x, 590), b_col, 4, cv2.LINE_AA)
    cv2.line(overlay, (r_x, 590), (r_x - 40, 590), b_col, 4, cv2.LINE_AA)

    # 5. Red Threat Lock-On & Conical Alert (Frames 70-240)
    if f >= 70:
        target_x, target_y = 1085, int(508 - float_y * 0.3)
        zoom_p = min(1.0, (f - 70) / 25.0)
        lock_rad = int(60 - (60 - 24) * zoom_p)
        blink = math.sin((f - 70) * 0.45) > 0
        red_col = (30, 30, 255) if blink else (15, 15, 170)

        # Crosshair reticle with spinning tick ring
        cv2.circle(overlay, (target_x, target_y), lock_rad, red_col, 3, cv2.LINE_AA)
        cv2.circle(overlay, (target_x, target_y), 4, red_col, -1, cv2.LINE_AA)

        # Rotating crosshair ticks
        rot_angle = (f - 70) * 0.08
        for a_off in [0, math.pi/2, math.pi, 3*math.pi/2]:
            a = rot_angle + a_off
            x_in = int(target_x + (lock_rad - 6) * math.cos(a))
            y_in = int(target_y + (lock_rad - 6) * math.sin(a))
            x_out = int(target_x + (lock_rad + 10) * math.cos(a))
            y_out = int(target_y + (lock_rad + 10) * math.sin(a))
            cv2.line(overlay, (x_in, y_in), (x_out, y_out), red_col, 2, cv2.LINE_AA)

        # Conical red warning strobe beam
        red_cone = np.array([
            [580, 360],
            [target_x, target_y],
            [580, 660]
        ], np.int32)
        cone_mask = np.zeros((H, W), dtype=np.uint8)
        cv2.fillPoly(cone_mask, [red_cone], 255)
        cone_layer = np.zeros_like(img)
        cone_layer[cone_mask > 0] = [15, 15, 235]
        c_alpha = 0.26 if blink else 0.09
        img = cv2.addWeighted(img, 1.0, cone_layer, c_alpha, 0)

        # Threat badge and countdown timer
        rem_time = max(0.0, (240 - f) / 30.0)
        cv2.putText(overlay, "[ THREAT LOCKED // HOSTILE ]", (target_x - 140, target_y - lock_rad - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, red_col, 2, cv2.LINE_AA)
        cv2.putText(overlay, f"TIME TO INTERCEPT: {rem_time:.2f}s", (target_x - 130, target_y + lock_rad + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 210, 225), 1, cv2.LINE_AA)

    bloom = draw_bloom(overlay, radius=21, intensity=0.9)
    img = cv2.add(img, bloom)
    return img

# ==============================================================================
# 02: Morse Crypto Data Matrix (8 Seconds Multi-Channel Stream)
# ==============================================================================
def render_frame_02(f):
    t = f / float(TOTAL_FRAMES)
    img = create_base_canvas()
    overlay = np.zeros_like(img)

    rows = [300, 460, 620, 780]
    freq_labels = ["CH-01 // 14.025 MHz", "CH-02 // 28.400 MHz", "CH-03 // 07.150 MHz", "CH-04 // 21.050 MHz"]

    # Header audio spectrum visualizer bar
    cv2.putText(overlay, "SIGNAL DECRYPTION / FREQUENCY MULTIPLEX", (400, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (230, 240, 255), 2, cv2.LINE_AA)

    # Real-time changing cryptographic hex stream
    hex_seed = (f // 4)
    hex_vals = [f"0x{(hex_seed * 17 + k * 31) % 256:02X}" for k in range(10)]
    cv2.putText(overlay, "HEX STREAM: " + " ".join(hex_vals), (400, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (120, 190, 255), 1, cv2.LINE_AA)

    for i, ry in enumerate(rows):
        # Baseline channel track
        cv2.line(img, (360, ry), (1560, ry), (45, 35, 30), 1, cv2.LINE_AA)
        cv2.putText(overlay, freq_labels[i], (180, ry + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (130, 145, 160), 1, cv2.LINE_AA)

        # Left white terminal node with pulsating rings
        l_pulse = 1.0 + 0.18 * math.sin(t * math.pi * 8.0 + i * 1.5)
        l_rad = int(18 * l_pulse)
        cv2.circle(overlay, (560, ry), l_rad, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, (560, ry), l_rad + 8, (255, 255, 255), 1, cv2.LINE_AA)

        # Right red alert node
        r_pulse = 1.0 + 0.22 * math.sin(t * math.pi * 9.0 + i * 2.0)
        r_rad = int(16 * r_pulse)
        cv2.circle(overlay, (1360, ry), r_rad, (35, 35, 245), -1, cv2.LINE_AA)
        cv2.circle(overlay, (1360, ry), r_rad + 8, (25, 25, 200), 2, cv2.LINE_AA)

        # Fluid multi-layer sliding data packets (Continuous 8s oscillation)
        shift1 = math.sin(t * math.pi * 4.0 + i * 1.3) * 190.0
        b1_x = int(800 + shift1)
        cv2.rectangle(overlay, (b1_x, ry - 20), (b1_x + 90, ry - 6), (255, 255, 255), -1)

        shift2 = math.cos(t * math.pi * 5.0 + i * 0.9) * 170.0
        b2_x = int(1060 + shift2)
        cv2.rectangle(overlay, (b2_x, ry - 20), (b2_x + 80, ry - 6), (255, 255, 255), -1)

        shift3 = math.sin(t * math.pi * 6.0 + i * 2.1) * 220.0
        b3_x = int(920 + shift3)
        cv2.rectangle(overlay, (b3_x, ry + 6), (b3_x + 110, ry + 20), (30, 30, 245), -1)

        # Fast telemetry ticks
        tick_offset = int((f * 6 + i * 35) % 260)
        cv2.line(overlay, (680 + tick_offset, ry - 3), (700 + tick_offset, ry - 3), (180, 225, 255), 2, cv2.LINE_AA)

    bloom = draw_bloom(overlay, radius=17, intensity=0.85)
    img = cv2.add(img, bloom)
    return img

# ==============================================================================
# 03: Hierarchy Dossier Flowchart (8 Seconds Tree & Signal Cascade)
# ==============================================================================
def render_frame_03(f):
    t = f / float(TOTAL_FRAMES)
    img = create_base_canvas()
    overlay = np.zeros_like(img)

    cx, cy = 960, 560
    bw, bh = 640, 740
    x1, y1 = cx - bw // 2, cy - bh // 2
    x2, y2 = cx + bw // 2, cy + bh // 2

    # Animated moving dashed rectangle
    dash_len = 16
    dash_shift = int((f * 2) % (dash_len * 2))
    for x in range(x1 + dash_shift, x2, dash_len * 2):
        cv2.line(img, (x, y1), (min(x + dash_len, x2), y1), (120, 100, 90), 2, cv2.LINE_AA)
        cv2.line(img, (x, y2), (min(x + dash_len, x2), y2), (120, 100, 90), 2, cv2.LINE_AA)
    for y in range(y1 + dash_shift, y2, dash_len * 2):
        cv2.line(img, (x1, y), (x1, min(y + dash_len, y2)), (120, 100, 90), 2, cv2.LINE_AA)
        cv2.line(img, (x2, y), (x2, min(y + dash_len, y2)), (120, 100, 90), 2, cv2.LINE_AA)

    # Header badge
    cv2.putText(overlay, "DOCUMENTARY INTELLIGENCE DOSSIER // COMPARTMENT 04", (x1 + 25, y1 - 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (220, 230, 245), 2, cv2.LINE_AA)

    # Vertical connection bus
    cv2.line(overlay, (cx, 340), (cx, 780), (255, 255, 255), 4, cv2.LINE_AA)

    # Cascading energy pulse traveling down every 80 frames
    cards_y = [340, 560, 780]
    pulse_loop = (f % 80) / 80.0
    pulse_y = int(340 + (780 - 340) * pulse_loop)
    cv2.circle(overlay, (cx, pulse_y), 18, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(overlay, (cx, pulse_y), 32, (255, 230, 0), 3, cv2.LINE_AA)

    card_titles = ["01. SOURCE INGESTION & CAPTURE", "02. SIGNAL DECRYPTION ENGINE", "03. EXFILTRATION PROTOCOL"]
    card_sub = ["[STATUS: CERTIFIED // 100% TRUTH]", "[STATUS: ACTIVE // INTERPOLATING]", "[STATUS: RESTRICTED LEVEL 5]"]

    for i, cy_node in enumerate(cards_y):
        dist = abs(pulse_y - cy_node)
        is_active = dist < 75
        border_col = (255, 255, 255) if is_active else (130, 115, 95)
        thickness = 4 if is_active else 2

        card_w, card_h = 480, 130
        c_x1, c_y1 = cx - card_w // 2, cy_node - card_h // 2
        c_x2, c_y2 = cx + card_w // 2, cy_node + card_h // 2

        cv2.rectangle(img, (c_x1, c_y1), (c_x2, c_y2), (20, 15, 12), -1)
        cv2.rectangle(overlay, (c_x1, c_y1), (c_x2, c_y2), border_col, thickness, cv2.LINE_AA)

        # Indicator node dot
        dot_col = (255, 255, 255) if i == 0 else ((50, 215, 255) if i == 1 else (35, 35, 245))
        cv2.circle(overlay, (c_x1 + 45, cy_node), 15, dot_col, -1, cv2.LINE_AA)
        cv2.circle(overlay, (c_x1 + 45, cy_node), 23, dot_col, 1, cv2.LINE_AA)

        # Typography text inside card
        cv2.putText(overlay, card_titles[i], (c_x1 + 80, cy_node - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (240, 245, 255), 2, cv2.LINE_AA)
        cv2.putText(overlay, card_sub[i], (c_x1 + 80, cy_node + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 175, 190), 1, cv2.LINE_AA)

    bloom = draw_bloom(overlay, radius=21, intensity=0.9)
    img = cv2.add(img, bloom)
    return img

# ==============================================================================
# 04: Surveillance Spotlight Scanner (8 Seconds Continuous Volumetric Sweep)
# ==============================================================================
def render_frame_04(f):
    t = f / float(TOTAL_FRAMES)
    img = create_base_canvas()
    overlay = np.zeros_like(img)

    # Viewport card
    cw, ch = 480, 560
    cx, cy = 960, 530
    x1, y1 = cx - cw // 2, cy - ch // 2
    x2, y2 = cx + cw // 2, cy + ch // 2

    cv2.rectangle(img, (x1, y1), (x2, y2), (18, 12, 10), -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 3, cv2.LINE_AA)

    # Corner brackets on viewport
    cv2.putText(overlay, "[ TARGET SURVEILLANCE VIEWPORT ]", (x1 + 20, y1 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 230, 245), 2, cv2.LINE_AA)

    # Continuous sweeping emitter bar (sinusoidal 8s cycle)
    sweep_x = cx + int(math.sin(t * math.pi * 4.0) * 110.0)
    bar_y = y1 + 55

    # Volumetric light cone
    cone_pts = np.array([
        [sweep_x - 70, bar_y + 12],
        [sweep_x + 70, bar_y + 12],
        [sweep_x + 165, y2 - 25],
        [sweep_x - 165, y2 - 25]
    ], np.int32)
    cone_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.fillPoly(cone_mask, [cone_pts], 255)
    cone_layer = np.zeros_like(img)
    cone_layer[cone_mask > 0] = [255, 255, 255]
    cv2.addWeighted(img, 1.0, cone_layer, 0.22, 0, dst=img)

    # Emitter bar
    cv2.rectangle(overlay, (sweep_x - 70, bar_y - 10), (sweep_x + 70, bar_y + 10), (255, 255, 255), -1)
    cv2.rectangle(overlay, (sweep_x - 70, bar_y - 10), (sweep_x + 70, bar_y + 10), (255, 255, 255), 2, cv2.LINE_AA)

    # 2 Tracked entities inside
    # Subject A
    e1_x, e1_y = 910, 620
    dist1 = abs(sweep_x - e1_x)
    glow1 = 1.0 + max(0.0, 1.0 - dist1 / 95.0) * 0.9
    cv2.circle(overlay, (e1_x, e1_y), int(30 * glow1), (255, 255, 255), -1, cv2.LINE_AA)
    cv2.putText(overlay, "SUB-A", (e1_x - 22, e1_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 210, 225), 1, cv2.LINE_AA)

    # Subject B
    e2_x, e2_y = 1015, 645
    dist2 = abs(sweep_x - e2_x)
    glow2 = 1.0 + max(0.0, 1.0 - dist2 / 95.0) * 0.9
    cv2.circle(overlay, (e2_x, e2_y), int(19 * glow2), (180, 160, 140), -1, cv2.LINE_AA)
    cv2.putText(overlay, "SUB-B", (e2_x - 20, e2_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 160, 140), 1, cv2.LINE_AA)

    # 11-Dot Telemetry status meter at bottom
    dot_spacing = 42
    dot_start_x = cx - 5 * dot_spacing
    active_dot = int((f * 0.4) % 11)
    for d in range(11):
        dx = dot_start_x + d * dot_spacing
        dy = y2 + 65
        is_lit = (d == active_dot) or (d == (active_dot - 1) % 11)
        d_rad = 10 if is_lit else 6
        d_col = (255, 255, 255) if is_lit else (90, 80, 70)
        cv2.circle(overlay, (dx, dy), d_rad, d_col, -1, cv2.LINE_AA)
        if is_lit:
            cv2.circle(overlay, (dx, dy), d_rad + 6, (255, 255, 255), 1, cv2.LINE_AA)

    # Live telemetry readout
    cv2.putText(overlay, f"OPTICAL FLUX: {85 + math.sin(t*20)*10:.1f}% // AZIMUTH: {math.sin(t*8)*25:.1f} DEG", (cx - 180, y2 + 105),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 155, 175), 1, cv2.LINE_AA)

    bloom = draw_bloom(overlay, radius=21, intensity=0.9)
    img = cv2.add(img, bloom)
    return img

# ==============================================================================
# 05: Orbital Radar Constellation & Reactor Core (8 Seconds 360° Continuous)
# ==============================================================================
def render_frame_05(f):
    t = f / float(TOTAL_FRAMES)
    img = create_base_canvas()
    overlay = np.zeros_like(img)
    cx, cy = 960, 540

    # Degree labels and axes
    cv2.putText(overlay, "N 000°", (cx - 24, cy - 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 155, 170), 1, cv2.LINE_AA)
    cv2.putText(overlay, "S 180°", (cx - 24, cy + 375), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 155, 170), 1, cv2.LINE_AA)
    cv2.putText(overlay, "E 090°", (cx + 355, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 155, 170), 1, cv2.LINE_AA)
    cv2.putText(overlay, "W 270°", (cx - 410, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 155, 170), 1, cv2.LINE_AA)

    # Concentric Radar rings with tick marks
    for r in [130, 230, 330]:
        cv2.circle(img, (cx, cy), r, (65, 55, 45), 1, cv2.LINE_AA)
    cv2.line(img, (cx - 360, cy), (cx + 360, cy), (50, 40, 35), 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy - 360), (cx, cy + 360), (50, 40, 35), 1, cv2.LINE_AA)

    # Continuous revolving radar sweep beam arm (3 full 360° revolutions over 8s)
    sweep_angle = t * math.pi * 2.0 * 3.0
    sw_x = int(cx + 330 * math.cos(sweep_angle))
    sw_y = int(cy + 330 * math.sin(sweep_angle))
    cv2.line(overlay, (cx, cy), (sw_x, sw_y), (140, 205, 255), 2, cv2.LINE_AA)

    # Central breathing crimson reactor core
    core_pulse = 1.0 + 0.18 * math.sin(t * math.pi * 8.0)
    core_rad = int(72 * core_pulse)
    cv2.circle(overlay, (cx, cy), core_rad, (30, 30, 255), -1, cv2.LINE_AA)
    cv2.circle(overlay, (cx, cy), core_rad + 10, (70, 70, 255), 2, cv2.LINE_AA)
    cv2.circle(overlay, (cx, cy), 26, (255, 255, 255), -1, cv2.LINE_AA)

    # Dual orbiting satellites:
    # 1. Inner satellite (Radius 130px, clockwise)
    orb1_angle = t * math.pi * 2.0 * 2.0
    s1_x = int(cx + 130 * math.cos(orb1_angle))
    s1_y = int(cy + 130 * math.sin(orb1_angle))
    cv2.circle(overlay, (s1_x, s1_y), 13, (245, 220, 200), -1, cv2.LINE_AA)
    cv2.circle(overlay, (s1_x, s1_y), 20, (255, 255, 255), 1, cv2.LINE_AA)

    # 2. Middle counter-orbiting satellite (Radius 180px, counter-clockwise)
    orb2_angle = - t * math.pi * 2.0 * 1.5
    s2_x = int(cx + 180 * math.cos(orb2_angle))
    s2_y = int(cy + 180 * math.sin(orb2_angle))
    cv2.circle(overlay, (s2_x, s2_y), 11, (100, 215, 255), -1, cv2.LINE_AA)

    # 16-Dot Outer Constellation (Radius 270px, continuous rotation)
    const_rot = t * math.pi * 2.0 * 1.0  # 1 full rotation
    for i in range(16):
        angle = const_rot + (i * math.pi * 2.0 / 16.0)
        dot_x = int(cx + 270 * math.cos(angle))
        dot_y = int(cy + 270 * math.sin(angle))

        # Traveling wave sparkle
        dot_pulse = 1.0 + 0.35 * math.sin(t * math.pi * 12.0 + i * 1.5)
        d_rad = int(9 * dot_pulse)
        cv2.circle(overlay, (dot_x, dot_y), d_rad, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, (dot_x, dot_y), d_rad + 4, (255, 255, 255), 1, cv2.LINE_AA)

    bloom = draw_bloom(overlay, radius=31, intensity=1.15)
    img = cv2.add(img, bloom)
    return img

# ==============================================================================
# Rendering Pipeline
# ==============================================================================
def render_animation(anim_id, render_func):
    temp_dir = os.path.join(CHRONON_RENDERS_DIR, f"frames_{anim_id}")
    os.makedirs(temp_dir, exist_ok=True)

    print(f"\n[RENDERING {TOTAL_FRAMES} DYNAMIC FRAMES (8s @ 30fps)] {anim_id}...")
    t0 = time.time()

    diffs = []
    prev_frame = None

    for f in range(TOTAL_FRAMES):
        frame = render_func(f)
        frame_path = os.path.join(temp_dir, f"frame_{f:04d}.png")
        cv2.imwrite(frame_path, frame)

        if prev_frame is not None:
            diff = np.mean(np.abs(frame.astype(float) - prev_frame.astype(float)))
            diffs.append(diff)
        prev_frame = frame

    print(f"Frames rendered in {time.time() - t0:.2f}s! Mean motion delta: {np.mean(diffs):.2f}")

    mp4_out = os.path.join(CHRONON_RENDERS_DIR, f"{anim_id}.mp4")
    user_mp4 = os.path.join(OUTPUT_DIR, f"{anim_id}.mp4")

    cmd_nvenc = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(temp_dir, "frame_%04d.png"),
        "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
        "-cq", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        mp4_out
    ]
    res = subprocess.run(cmd_nvenc, capture_output=True, text=True)
    if res.returncode != 0:
        cmd_cpu = [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", os.path.join(temp_dir, "frame_%04d.png"),
            "-c:v", "libx264", "-crf", "15", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            mp4_out
        ]
        subprocess.run(cmd_cpu, check=True)

    shutil.copyfile(mp4_out, user_mp4)
    print(f"[SUCCESS] {anim_id}.mp4 -> {os.path.getsize(user_mp4)/1024:.1f} KB (8.0s extended motion)")
    shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    animations = [
        ("01_reticle_target_scanner", render_frame_01),
        ("02_morse_crypto_matrix", render_frame_02),
        ("03_hierarchy_flowchart", render_frame_03),
        ("04_surveillance_scanner", render_frame_04),
        ("05_orbital_radar_core", render_frame_05)
    ]

    for anim_id, func in animations:
        render_animation(anim_id, func)

    print("\n=======================================================")
    print("ALL 5 EXTENDED 8-SECOND ANIMATIONS RENDERED!")
    print(f"Destination: {OUTPUT_DIR}")
    print("=======================================================")

if __name__ == "__main__":
    main()
