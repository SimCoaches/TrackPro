#!/usr/bin/env python3
"""
Simple script to create placeholder icons for the quest system
"""

from PIL import Image, ImageDraw
import os

def create_xp_icon():
    """Create XP icon - blue star"""
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a star shape for XP
    center = size // 2
    outer_radius = 14
    inner_radius = 6
    
    points = []
    for i in range(10):
        angle = i * 36 * 3.14159 / 180
        if i % 2 == 0:
            radius = outer_radius
        else:
            radius = inner_radius
        x = center + radius * (angle ** 0.5) % 2 - 1  # Simple approximation
        y = center + radius * ((angle + 1) ** 0.5) % 2 - 1
        points.append((x, y))
    
    # Simple circle for now
    draw.ellipse([center-12, center-12, center+12, center+12], 
                fill=(52, 152, 219, 255), outline=(41, 128, 185, 255), width=2)
    
    # Add "XP" text
    try:
        from PIL import ImageFont
        font = ImageFont.load_default()
        draw.text((center-8, center-6), "XP", fill=(255, 255, 255, 255), font=font)
    except:
        draw.text((center-8, center-6), "XP", fill=(255, 255, 255, 255))
    
    return img

def create_rp_xp_icon():
    """Create Race Pass XP icon - orange diamond"""
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    # Draw diamond shape
    points = [
        (center, center-12),  # top
        (center+12, center),  # right
        (center, center+12),  # bottom
        (center-12, center)   # left
    ]
    
    draw.polygon(points, fill=(243, 156, 18, 255), outline=(230, 126, 34, 255), width=2)
    
    # Add "RP" text
    try:
        from PIL import ImageFont
        font = ImageFont.load_default()
        draw.text((center-8, center-6), "RP", fill=(255, 255, 255, 255), font=font)
    except:
        draw.text((center-8, center-6), "RP", fill=(255, 255, 255, 255))
    
    return img

def create_quest_icon():
    """Create general quest icon - scroll"""
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw scroll shape
    draw.rectangle([6, 4, 26, 28], fill=(245, 245, 220, 255), outline=(139, 69, 19, 255), width=2)
    
    # Add quest lines
    for i, y in enumerate([10, 14, 18, 22]):
        width = 16 - i * 2
        draw.rectangle([8, y, 8 + width, y + 1], fill=(139, 69, 19, 255))
    
    return img

def main():
    """Create all icon files"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create XP icon
    xp_icon = create_xp_icon()
    xp_icon.save(os.path.join(script_dir, 'xp_icon.png'))
    print("Created xp_icon.png")
    
    # Create Race Pass XP icon
    rp_xp_icon = create_rp_xp_icon()
    rp_xp_icon.save(os.path.join(script_dir, 'rp_xp_icon.png'))
    print("Created rp_xp_icon.png")
    
    # Create quest icon
    quest_icon = create_quest_icon()
    quest_icon.save(os.path.join(script_dir, 'quest_icon.png'))
    print("Created quest_icon.png")
    
    print("All icons created successfully!")

if __name__ == "__main__":
    main() 