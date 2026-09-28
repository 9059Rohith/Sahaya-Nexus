"""Regenerate the self-hosted PWA icons; requires Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw


public = Path(__file__).resolve().parents[1] / "public"
for size in (192, 512):
    image = Image.new("RGB", (size, size), "#102b45")
    draw = ImageDraw.Draw(image)
    scale = size / 512

    def polygon(points, color):
        draw.polygon([(round(x * scale), round(y * scale)) for x, y in points], fill=color)

    polygon([(86, 281), (224, 145), (272, 193), (134, 329)], "#29bdb2")
    polygon([(192, 319), (348, 163), (396, 211), (240, 367)], "#a5cc78")
    image.save(public / f"icon-{size}.png", optimize=True)
