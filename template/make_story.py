"""Turn a post image (1080x1350) into a 1080x1920 Story image for Instagram/Facebook Stories.
Usage: python3 make_story.py posts/<file>.jpg posts/<file>-story.jpg
"""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

W, H = 1080, 1920
YELLOW = (255, 221, 0)
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

src, out = sys.argv[1], sys.argv[2]
post = Image.open(src).convert("RGB")

# blurred, darkened fill
r = max(W / post.width, H / post.height)
bg = post.resize((round(post.width * r), round(post.height * r)), Image.LANCZOS)
l, t = (bg.width - W) // 2, (bg.height - H) // 2
bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(40))
bg = ImageEnhance.Brightness(bg).enhance(0.45)

# post card, slightly inset with a yellow frame
cw = 980
card = post.resize((cw, round(post.height * cw / post.width)), Image.LANCZOS)
cx, cy = (W - cw) // 2, (H - card.height) // 2 + 30
d = ImageDraw.Draw(bg)
d.rounded_rectangle((cx - 8, cy - 8, cx + cw + 8, cy + card.height + 8), radius=26, fill=YELLOW)
mask = Image.new("L", card.size, 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width, card.height), radius=20, fill=255)
bg.paste(card, (cx, cy), mask)

# top label + bottom call to action
f = ImageFont.truetype(BOLD, 46)
label = "LATEST NEWS"
b = d.textbbox((0, 0), label, font=f)
lw = b[2] - b[0] + 60
d.rounded_rectangle(((W - lw) // 2, 150, (W + lw) // 2, 230), radius=40, fill=(220, 30, 40))
d.text((W // 2, 190), label, font=f, fill=(255, 255, 255), anchor="mm")
f2 = ImageFont.truetype(BOLD, 40)
d.text((W // 2, cy + card.height + 110), "Full story on our page", font=f2, fill=(255, 255, 255), anchor="mm")
d.text((W // 2, cy + card.height + 165), "RiseUp Pakistan", font=f2, fill=YELLOW, anchor="mm")

bg.save(out, quality=92)
print("saved", out)
