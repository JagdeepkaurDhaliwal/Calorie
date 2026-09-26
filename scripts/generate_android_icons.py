import os
import shutil
from PIL import Image

def copy_android_icons():
    root = os.path.dirname(os.path.dirname(__file__))
    source_icon = os.path.join(root, "frontend", "icons", "icon-512.png")
    if not os.path.exists(source_icon):
        print("Source icon not found!")
        return

    img = Image.open(source_icon)
    res_dir = os.path.join(root, "android", "app", "src", "main", "res")

    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, dim in densities.items():
        target_dir = os.path.join(res_dir, folder)
        os.makedirs(target_dir, exist_ok=True)
        resized = img.resize((dim, dim), Image.Resampling.LANCZOS)
        out_path = os.path.join(target_dir, "ic_launcher.png")
        resized.save(out_path, "PNG")
        print(f"Created {folder}/ic_launcher.png ({dim}x{dim})")

if __name__ == "__main__":
    copy_android_icons()
