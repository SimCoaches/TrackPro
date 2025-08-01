#!/usr/bin/env python3
"""
Script to create a TrackPro system tray icon
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_trackpro_tray_icon():
    """Create TrackPro tray icon - racing themed"""
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # Draw outer circle (racing wheel)
    draw.ellipse([2, 2, size-2, size-2], 
                fill=(220, 50, 47, 255), outline=(180, 40, 37, 255), width=2)
    
    # Draw inner circle
    draw.ellipse([8, 8, size-8, size-8], 
                fill=(255, 255, 255, 255), outline=(180, 40, 37, 255), width=1)
    
    # Draw spokes (like a steering wheel)
    for angle in [0, 90, 180, 270]:
        import math
        rad = math.radians(angle)
        x1 = center + 6 * math.cos(rad)
        y1 = center + 6 * math.sin(rad)
        x2 = center + 10 * math.cos(rad)
        y2 = center + 10 * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=(180, 40, 37, 255), width=2)
    
    # Add "TP" text in center
    try:
        font = ImageFont.load_default()
        draw.text((center-6, center-6), "TP", fill=(220, 50, 47, 255), font=font)
    except:
        draw.text((center-6, center-6), "TP", fill=(220, 50, 47, 255))
    
    return img

def create_trackpro_tray_icon_ico():
    """Create TrackPro tray icon in ICO format with multiple sizes"""
    sizes = [16, 24, 32, 48]
    images = []
    
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center = size // 2
        border = max(1, size // 16)
        
        # Draw outer circle (racing wheel)
        draw.ellipse([border, border, size-border, size-border], 
                    fill=(220, 50, 47, 255), outline=(180, 40, 37, 255), width=border)
        
        # Draw inner circle
        inner_border = max(1, size // 8)
        inner_size = size - inner_border * 4
        inner_offset = (size - inner_size) // 2
        draw.ellipse([inner_offset, inner_offset, inner_offset + inner_size, inner_offset + inner_size], 
                    fill=(255, 255, 255, 255), outline=(180, 40, 37, 255), width=max(1, border//2))
        
        # Draw spokes for larger sizes
        if size >= 24:
            import math
            spoke_width = max(1, size // 16)
            for angle in [0, 90, 180, 270]:
                rad = math.radians(angle)
                inner_radius = size // 5
                outer_radius = size // 3
                x1 = center + inner_radius * math.cos(rad)
                y1 = center + inner_radius * math.sin(rad)
                x2 = center + outer_radius * math.cos(rad)
                y2 = center + outer_radius * math.sin(rad)
                draw.line([(x1, y1), (x2, y2)], fill=(180, 40, 37, 255), width=spoke_width)
        
        # Add "TP" text for larger sizes
        if size >= 24:
            try:
                font = ImageFont.load_default()
                text_size = draw.textsize("TP", font=font) if hasattr(draw, 'textsize') else (10, 8)
                text_x = center - text_size[0] // 2
                text_y = center - text_size[1] // 2
                draw.text((text_x, text_y), "TP", fill=(220, 50, 47, 255), font=font)
            except:
                text_x = center - 5
                text_y = center - 4
                draw.text((text_x, text_y), "TP", fill=(220, 50, 47, 255))
        
        images.append(img)
    
    return images

def main():
    """Create tray icon files"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create PNG tray icon
    tray_icon = create_trackpro_tray_icon()
    png_path = os.path.join(script_dir, 'trackpro_tray.png')
    tray_icon.save(png_path)
    print(f"Created {png_path}")
    
    # Create ICO tray icon with multiple sizes
    ico_images = create_trackpro_tray_icon_ico()
    ico_path = os.path.join(script_dir, 'trackpro_tray.ico')
    ico_images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in ico_images])
    print(f"Created {ico_path}")
    
    print("TrackPro tray icons created successfully!")

if __name__ == "__main__":
    main() 