import re

with open("ChrononTemplate/tools/map/render_map_image_v2_opencv.py") as f:
    code = f.read()

# Let's inspect _draw_title in render_map_image_v2_opencv.py
print("Current _draw_title start:")
match = re.search(r"def _draw_title\(.*?\n\s+return", code, re.DOTALL)
if match:
    print(match.group(0)[:300])
