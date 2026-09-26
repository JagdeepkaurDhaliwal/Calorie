import os
from PIL import Image, ImageDraw

def create_icon(size: int, is_maskable: bool = False) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background
    bg_color = (15, 23, 42, 255) # #0f172a
    if is_maskable:
        # Full square fill for maskable icons
        draw.rectangle([0, 0, size, size], fill=bg_color)
    else:
        # Rounded rectangle for regular icons
        corner_radius = int(size * 0.22)
        draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=bg_color)

    # Outer subtle ring
    center = size / 2
    ring_radius = size * (0.38 if is_maskable else 0.42)
    draw.ellipse(
        [center - ring_radius, center - ring_radius, center + ring_radius, center + ring_radius],
        outline=(56, 189, 248, 120), # subtle cyan
        width=max(int(size * 0.02), 2)
    )

    # Flame / Heart / Pulse symbol in Red & Orange
    # Scale factor
    s = size / 100.0

    # Draw flame silhouette
    flame_pts = [
        (50 * s, 18 * s), # top flame tip
        (65 * s, 35 * s),
        (78 * s, 55 * s),
        (75 * s, 75 * s),
        (62 * s, 85 * s),
        (50 * s, 88 * s),
        (38 * s, 85 * s),
        (25 * s, 75 * s),
        (22 * s, 55 * s),
        (35 * s, 35 * s),
    ]
    draw.polygon(flame_pts, fill=(239, 68, 68, 255)) # #ef4444 vibrant red

    # Inner flame in orange
    inner_pts = [
        (50 * s, 38 * s),
        (60 * s, 50 * s),
        (66 * s, 65 * s),
        (58 * s, 78 * s),
        (50 * s, 82 * s),
        (42 * s, 78 * s),
        (34 * s, 65 * s),
        (40 * s, 50 * s),
    ]
    draw.polygon(inner_pts, fill=(249, 115, 22, 255)) # orange

    # Pulse heart-rate line across flame in bright cyan / white
    line_y = 62 * s
    pulse_pts = [
        (18 * s, line_y),
        (36 * s, line_y),
        (43 * s, line_y - 12 * s),
        (50 * s, line_y + 14 * s),
        (57 * s, line_y - 8 * s),
        (64 * s, line_y),
        (82 * s, line_y),
    ]
    draw.line(pulse_pts, fill=(255, 255, 255, 240), width=max(int(size * 0.035), 3), joint="curve")

    return img

def main():
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "icons")
    os.makedirs(icons_dir, exist_ok=True)

    # 192x192
    img192 = create_icon(192)
    img192.save(os.path.join(icons_dir, "icon-192.png"), "PNG")
    print(f"Generated {icons_dir}/icon-192.png")

    # 512x512
    img512 = create_icon(512)
    img512.save(os.path.join(icons_dir, "icon-512.png"), "PNG")
    print(f"Generated {icons_dir}/icon-512.png")

    # 512x512 Maskable
    img_mask = create_icon(512, is_maskable=True)
    img_mask.save(os.path.join(icons_dir, "icon-maskable.png"), "PNG")
    print(f"Generated {icons_dir}/icon-maskable.png")

    # 64x64 favicon
    img_fav = create_icon(64)
    img_fav.save(os.path.join(icons_dir, "favicon.png"), "PNG")
    print(f"Generated {icons_dir}/favicon.png")

if __name__ == "__main__":
    main()
