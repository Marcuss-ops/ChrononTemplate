from pathlib import Path
from PIL import Image
d = Path(__file__).resolve().parents[2] / "assets" / "fast_intro_match_cut"
fs = sorted(d.glob("*.png"))
cols = 4
rows = (len(fs) + cols - 1) // cols
sh = Image.new("RGB", (cols * 480, rows * 270))
for i, f in enumerate(fs):
    sh.paste(Image.open(f).resize((480, 270)), ((i % cols) * 480, (i // cols) * 270))
sh.save(Path(__file__).parent / "ref" / "plates.png")
print([f.name for f in fs])
