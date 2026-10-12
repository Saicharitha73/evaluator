import io
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def create_sample_pair_1():
    """Sample Pair 1: Cyberpunk Neon City (Original vs AI Variant)."""
    # Original: Moody sunset cityscape with geometric buildings
    orig = Image.new("RGB", (600, 600), (15, 20, 35))
    draw_orig = ImageDraw.Draw(orig)

    # Sky gradient
    for y in range(350):
        r = int(15 + (180 - 15) * (y / 350) ** 1.5)
        g = int(20 + (80 - 20) * (y / 350) ** 1.5)
        b = int(35 + (120 - 35) * (y / 350) ** 1.5)
        draw_orig.line([(0, y), (600, y)], fill=(r, g, b))

    # Sun
    draw_orig.ellipse([240, 180, 360, 300], fill=(255, 120, 50))

    # Buildings
    buildings = [
        (40, 250, 140, 600, (20, 25, 45)),
        (120, 200, 240, 600, (10, 15, 30)),
        (220, 280, 340, 600, (25, 30, 50)),
        (320, 220, 440, 600, (15, 20, 38)),
        (420, 260, 540, 600, (18, 22, 42)),
    ]
    for x1, y1, x2, y2, color in buildings:
        draw_orig.rectangle([x1, y1, x2, y2], fill=color)
        # Windows
        for wx in range(x1 + 10, x2 - 10, 18):
            for wy in range(y1 + 15, y2 - 20, 24):
                if (wx + wy) % 7 != 0:
                    draw_orig.rectangle([wx, wy, wx + 8, wy + 12], fill=(240, 220, 150))

    # Generated: AI stylized variant with cyan/magenta neon & glow
    gen = orig.copy()
    draw_gen = ImageDraw.Draw(gen)
    # Add neon accents & color tint
    for x1, y1, x2, y2, _ in buildings:
        draw_gen.line([(x1, y1), (x2, y1)], fill=(0, 255, 255), width=2)
        draw_gen.line([(x1, y1), (x1, y2)], fill=(255, 0, 180), width=2)
    # Add atmospheric haze
    gen = gen.filter(ImageFilter.GaussianBlur(radius=0.7))

    b_orig = io.BytesIO()
    orig.save(b_orig, format="JPEG", quality=90)
    b_gen = io.BytesIO()
    gen.save(b_gen, format="JPEG", quality=90)

    return b_orig.getvalue(), b_gen.getvalue()

def create_sample_pair_2():
    """Sample Pair 2: Abstract Nature Emblem (High fidelity match)."""
    orig = Image.new("RGB", (600, 600), (245, 247, 250))
    draw_o = ImageDraw.Draw(orig)

    # Mountain triangles & sun
    draw_o.ellipse([230, 120, 370, 260], fill=(245, 158, 11))
    draw_o.polygon([(50, 520), (250, 240), (450, 520)], fill=(30, 58, 138))
    draw_o.polygon([(220, 520), (380, 290), (550, 520)], fill=(16, 185, 129))

    # Generated variant with slight texture & hue shift
    gen = orig.copy()
    draw_g = ImageDraw.Draw(gen)
    draw_g.polygon([(200, 310), (250, 240), (280, 310)], fill=(255, 255, 255))
    gen = gen.filter(ImageFilter.DETAIL)

    b_orig = io.BytesIO()
    orig.save(b_orig, format="JPEG", quality=90)
    b_gen = io.BytesIO()
    gen.save(b_gen, format="JPEG", quality=90)

    return b_orig.getvalue(), b_gen.getvalue()
