import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
FONTS_DIR = os.path.join(BASE_DIR, "Chronon3d/assets/fonts")
FONT_TITLE = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")

# Load a clean frame of Italy
cap = cv2.VideoCapture(os.path.join(BASE_DIR, "ChrononTemplate/out/map_image_v1_opencv/renders/map_image_italy_beacon_arrival.mp4"))
cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
ret, base_frame = cap.read()
cap.release()
H, W = base_frame.shape[:2]

accent_rgb = (255, 130, 118) # Italy Coral
accent_bgr = (118, 130, 255)
cx, cy = 980, 460
font = ImageFont.truetype(FONT_TITLE, 46)

# Test 1: Mask Slide Up
# Test 2: Elastic Pop & Flare
# Test 3: Tracking Expansion
# Test 4: Typewriter / Glitch Terminal
print("Base frame loaded:", H, W)
