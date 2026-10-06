import re

with open("ChrononTemplate/tools/map/render_map_image_v2_opencv.py") as f:
    content = f.read()

# Replace _draw_title with the ultra-premium Frosted Glass Typography Badge
old_draw_title_pattern = r"  def _draw_title\(self,frame,f,progress,pts\):.*?(?=  def render_frame_fast)"

new_draw_title = """  def _draw_title(self,frame,f,progress,pts):
   alpha=ease((progress-.14)/.18)
   if alpha<=0.005:return
   
   metadata = {
       'brazil': ('SOUTH AMERICA  ·  BR', 'BRAZIL', 'CAPITAL: BRASÍLIA  ·  15.8° S, 47.9° W'),
       'usa': ('NORTH AMERICA  ·  US', 'UNITED STATES', 'CAPITAL: WASHINGTON D.C.  ·  38.9° N, 77.0° W'),
       'iran': ('MIDDLE EAST  ·  IR', 'IRAN', 'CAPITAL: TEHRAN  ·  35.7° N, 51.4° E'),
       'india': ('SOUTH ASIA  ·  IN', 'INDIA', 'CAPITAL: NEW DELHI  ·  28.6° N, 77.2° E'),
       'gujarat': ('WESTERN INDIA  ·  GJ', 'GUJARAT', 'STATE CAPITAL: GANDHINAGAR  ·  23.2° N, 72.6° E'),
       'italy': ('SOUTHERN EUROPE  ·  IT', 'ITALY', 'CAPITAL: ROME  ·  41.9° N, 12.5° E'),
       'nigeria': ('WEST AFRICA  ·  NG', 'NIGERIA', 'FEDERAL CAPITAL: ABUJA  ·  9.1° N, 7.5° E'),
       'china': ('EAST ASIA  ·  CN', 'CHINA', 'CAPITAL: BEIJING  ·  39.9° N, 116.4° E'),
       'korea': ('EAST ASIA  ·  KR', 'SOUTH KOREA', 'CAPITAL: SEOUL  ·  37.6° N, 127.0° E'),
       'australia': ('OCEANIA  ·  AU', 'AUSTRALIA', 'CAPITAL: CANBERRA  ·  35.3° S, 149.1° E')
   }
   kicker, hero_title, meta = metadata.get(self.slug, ('FIELD ATLAS', self.title.upper(), ''))
   
   # Placement coordinates
   pose_zoom = self.pose(f)[2]
   title_lat, title_lon = (43.25, 12.5) if self.slug == 'italy' else self.anchor
   cx, cy = self._screen(title_lon, title_lat, pose_zoom)
   
   # For Korea, place slightly offset
   if self.slug == 'korea':
       cx, cy = cx + 180, cy - 80
   elif self.slug == 'usa':
       cx, cy = cx, cy - 40
       
   cx = max(240, min(W - 240, cx))
   cy = max(130, min(H - 130, cy))
   
   # Font paths
   f_hero = str(ROOT / 'Chronon3d/assets/fonts/Bricolage-Grotesque.ttf')
   f_sans = str(ROOT / 'Chronon3d/assets/fonts/Plus-Jakarta-Sans.ttf')
   f_mono = str(ROOT / 'Chronon3d/assets/fonts/UbuntuMono-R.ttf')
   
   # Card Dimensions
   font_h = ImageFont.truetype(f_hero, 60 if len(hero_title) < 10 else 52)
   font_k = ImageFont.truetype(f_sans, 15)
   font_m = ImageFont.truetype(f_mono, 15)
   
   # Compute text width
   temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
   tw_h = temp_draw.textbbox((0, 0), hero_title, font=font_h)[2]
   tw_m = temp_draw.textbbox((0, 0), meta, font=font_m)[2]
   card_w = max(420, max(tw_h, tw_m) + 64)
   card_h = 186
   
   # Elastic vertical rise animation
   y_offset = int((1.0 - alpha) * 26)
   x0 = int(cx - card_w // 2)
   y0 = int(cy - card_h // 2 + y_offset)
   x1 = x0 + card_w
   y1 = y0 + card_h
   
   # 1. Soft glowing aura around card
   glow_mask = np.zeros((H, W), dtype=np.uint8)
   cv2.rectangle(glow_mask, (max(0, x0 - 6), max(0, y0 - 6)), (min(W - 1, x1 + 6), min(H - 1, y1 + 6)), 255, -1)
   glow_blur = cv2.GaussianBlur(glow_mask, (0, 0), 22).astype(np.float32) / 255.0
   
   accent_rgb = (int(self.hex[1:3], 16), int(self.hex[3:5], 16), int(self.hex[5:7], 16))
   accent_bgr = self.accent
   
   # Apply glow aura to frame
   glow_strength = 0.38 * alpha
   for c in range(3):
       frame[:, :, c] = np.clip(frame[:, :, c].astype(np.float32) * (1.0 - glow_blur * glow_strength) + accent_bgr[c] * (glow_blur * glow_strength), 0, 255).astype(np.uint8)
       
   # 2. Draw frosted glass card with PIL
   overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
   draw = ImageDraw.Draw(overlay)
   
   # Glass fill + neon border
   glass_alpha = int(225 * alpha)
   border_alpha = int(255 * alpha)
   draw.rounded_rectangle([x0, y0, x1, y1], radius=20, 
                          fill=(8, 16, 26, glass_alpha), 
                          outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], border_alpha), width=2)
   
   # Top glass specular sheen
   draw.rounded_rectangle([x0 + 4, y0 + 4, x1 - 4, y0 + 34], radius=15, 
                          fill=(255, 255, 255, int(18 * alpha)))
   
   # Top kicker
   draw.text((x0 + 26, y0 + 18), kicker, font=font_k, fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], border_alpha))
   
   # Hero Title
   draw.text((x0 + 24, y0 + 42), hero_title, font=font_h, fill=(255, 255, 255, border_alpha))
   
   # Divider line
   draw.line([x0 + 24, y0 + 128, x1 - 24, y0 + 128], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(80 * alpha)), width=1)
   
   # Technical Metadata
   draw.text((x0 + 26, y0 + 140), meta, font=font_m, fill=(185, 205, 225, int(235 * alpha)))
   
   # Indicator dot
   draw.ellipse([x1 - 36, y0 + 22, x1 - 24, y0 + 34], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], border_alpha))
   
   # Alpha blend overlay onto frame
   overlay_np = np.asarray(overlay)
   o_alpha = (overlay_np[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
   o_bgr = cv2.cvtColor(overlay_np[:, :, :3], cv2.COLOR_RGB2BGR).astype(np.float32)
   f_float = frame.astype(np.float32)
   frame[:] = np.clip(f_float * (1.0 - o_alpha) + o_bgr * o_alpha, 0, 255).astype(np.uint8)
"""

modified = re.sub(old_draw_title_pattern, new_draw_title, content, flags=re.DOTALL)
with open("ChrononTemplate/tools/map/render_map_image_v2_opencv.py", "w") as f:
    f.write(modified)

print("Updated render_map_image_v2_opencv.py with Monumental Frosted Glass Typography Badge!")
