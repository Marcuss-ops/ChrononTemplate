import re, resvg_py, io
from PIL import Image

with open(r'C:\Users\pater\Pyt\ChrononTemplate\assets\icons\svg\cpu.svg') as f:
    raw_svg = f.read()

white_svg = raw_svg
white_svg = white_svg.replace('stroke="currentColor"', 'stroke="#FFFFFF"')
# Match only standalone width and height (not stroke-width)
white_svg = re.sub(r'(?<![-a-zA-Z])width="[^"]+"', 'width="512"', white_svg)
white_svg = re.sub(r'(?<![-a-zA-Z])height="[^"]+"', 'height="512"', white_svg)

png = resvg_py.svg_to_bytes(svg_string=white_svg)
im = Image.open(io.BytesIO(png))
print('Fixed size:', im.size)
print('Corner pixel:', im.getpixel((0, 0)))
print('Non-zero alpha bbox:', im.getbbox())
