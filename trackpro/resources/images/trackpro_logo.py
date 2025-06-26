#!/usr/bin/env python3
"""
TrackPro Logo Generator
Creates a professional company logo for TrackPro Racing Telemetry System
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_trackpro_logo(width=400, height=200, save_path=None):
    """
    Create a professional TrackPro logo with racing theme
    
    Args:
        width: Logo width in pixels
        height: Logo height in pixels
        save_path: Path to save the logo (optional)
    
    Returns:
        PIL Image object
    """
    
    # Create image with transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Color scheme - Racing inspired
    primary_color = (220, 50, 47)      # Racing red
    secondary_color = (38, 139, 210)   # Tech blue
    accent_color = (255, 193, 7)       # Gold/yellow
    text_color = (248, 248, 242)       # Off-white
    dark_color = (40, 44, 52)          # Dark gray
    
    # Background gradient effect
    for y in range(height):
        alpha = int(255 * (1 - y / height) * 0.1)  # Subtle gradient
        color = (*dark_color, alpha)
        draw.rectangle([(0, y), (width, y+1)], fill=color)
    
    # Draw racing stripes background
    stripe_width = 8
    for i in range(0, width + height, stripe_width * 3):
        # Diagonal stripes
        x1, y1 = i, 0
        x2, y2 = i - height, height
        draw.line([(x1, y1), (x2, y2)], fill=(*primary_color, 30), width=stripe_width//2)
    
    # Draw speedometer/gauge background circle
    center_x, center_y = width // 4, height // 2
    gauge_radius = min(width, height) // 6
    
    # Outer ring
    draw.ellipse([
        center_x - gauge_radius, center_y - gauge_radius,
        center_x + gauge_radius, center_y + gauge_radius
    ], outline=secondary_color, width=4)
    
    # Inner gauge marks
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        inner_x = center_x + (gauge_radius - 15) * math.cos(rad)
        inner_y = center_y + (gauge_radius - 15) * math.sin(rad)
        outer_x = center_x + (gauge_radius - 5) * math.cos(rad)
        outer_y = center_y + (gauge_radius - 5) * math.sin(rad)
        draw.line([(inner_x, inner_y), (outer_x, outer_y)], fill=accent_color, width=2)
    
    # Gauge needle pointing to "high performance"
    needle_angle = math.radians(45)  # 45 degrees
    needle_x = center_x + (gauge_radius - 10) * math.cos(needle_angle)
    needle_y = center_y + (gauge_radius - 10) * math.sin(needle_angle)
    draw.line([(center_x, center_y), (needle_x, needle_y)], fill=primary_color, width=3)
    
    # Center dot
    draw.ellipse([
        center_x - 4, center_y - 4,
        center_x + 4, center_y + 4
    ], fill=primary_color)
    
    # Try to load a nice font, fall back to default if not available
    try:
        # Try to find a good font
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        
        title_font = None
        subtitle_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 36)
                subtitle_font = ImageFont.truetype(font_path, 14)
                break
        
        if title_font is None:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Main title "TrackPro"
    title_text = "TrackPro"
    title_x = width // 2 + 20
    title_y = height // 2 - 25
    
    # Add text shadow effect
    shadow_offset = 2
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title_text, 
              font=title_font, fill=(0, 0, 0, 128), anchor="mm")
    
    # Main title with gradient effect (simulate with multiple colors)
    draw.text((title_x, title_y), title_text, font=title_font, fill=text_color, anchor="mm")
    
    # Subtitle
    subtitle_text = "Racing Telemetry System"
    subtitle_y = title_y + 30
    draw.text((title_x, subtitle_y), subtitle_text, font=subtitle_font, 
              fill=secondary_color, anchor="mm")
    
    # Add racing flag checkered pattern in corner
    flag_size = 30
    flag_x = width - flag_size - 10
    flag_y = 10
    
    # Checkered pattern
    square_size = flag_size // 6
    for row in range(6):
        for col in range(6):
            if (row + col) % 2 == 0:
                x1 = flag_x + col * square_size
                y1 = flag_y + row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size
                draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255, 200))
    
    # Add version/tech elements
    tech_elements = [
        "TELEMETRY", "DATA", "PERFORMANCE", "RACING"
    ]
    
    for i, element in enumerate(tech_elements):
        x = width - 80
        y = height - 60 + i * 12
        draw.text((x, y), element, font=subtitle_font, fill=(*accent_color, 100))
    
    # Save if path provided
    if save_path:
        img.save(save_path, 'PNG')
        print(f"Logo saved to: {save_path}")
    
    return img

def create_splash_background(width=500, height=300, save_path=None):
    """
    Create a splash screen background
    """
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Dark gradient background
    for y in range(height):
        intensity = int(255 * (1 - y / height) * 0.3)
        color = (intensity//3, intensity//3, intensity//2, 255)
        draw.rectangle([(0, y), (width, y+1)], fill=color)
    
    # Add subtle grid pattern
    grid_spacing = 20
    grid_color = (100, 100, 100, 50)
    
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    
    if save_path:
        img.save(save_path, 'PNG')
        print(f"Splash background saved to: {save_path}")
    
    return img

if __name__ == "__main__":
    # Create the images directory if it doesn't exist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create main logo
    logo_path = os.path.join(current_dir, "trackpro_logo.png")
    create_trackpro_logo(400, 200, logo_path)
    
    # Create splash background
    splash_path = os.path.join(current_dir, "splash_background.png")
    create_splash_background(500, 300, splash_path)
    
    # Create smaller logo for splash
    small_logo_path = os.path.join(current_dir, "trackpro_logo_small.png")
    create_trackpro_logo(300, 150, small_logo_path)
    
    print("All logo files created successfully!") 