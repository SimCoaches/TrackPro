from PIL import Image, ImageDraw, ImageFont
import os, math

def create_xp_icon(path: str):
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Green circle background
    draw.ellipse([0, 0, 31, 31], fill=(39, 174, 96, 255))  # #27ae60 green
    # XP text in white
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()
    text = "XP"
    bbox = draw.textbbox((0,0), text, font=font)
    w = bbox[2]-bbox[0]
    h = bbox[3]-bbox[1]
    draw.text(((32 - w) / 2, (32 - h) / 2), text, font=font, fill=(255, 255, 255, 255))
    img.save(path)


def create_rp_icon(path: str):
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Gold star background
    cx, cy, r_out, r_in = 16, 16, 14, 6
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_out if i % 2 == 0 else r_in
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=(255, 215, 0, 255))  # gold color
    img.save(path)


def main():
    root = os.getcwd()
    icons_dir = os.path.join(root, 'trackpro', 'resources', 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    create_xp_icon(os.path.join(icons_dir, 'xp_icon.png'))
    create_rp_icon(os.path.join(icons_dir, 'rp_xp_icon.png'))
    print('Generated xp_icon.png and rp_xp_icon.png in', icons_dir)


if __name__ == '__main__':
    main() 