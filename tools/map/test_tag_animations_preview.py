import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
FONTS_DIR = os.path.join(BASE_DIR, "Chronon3d/assets/fonts")
FONT_TITLE = os.path.join(FONTS_DIR, "Bricolage-Grotesque.ttf")
FONT_SANS = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")

frame_path = os.path.join(BASE_DIR, "ChrononTemplate/out/italy_f100_badge.png")
# load basemap frame (without old badge) or clean frame
