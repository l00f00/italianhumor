from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import random
import requests
from io import BytesIO

def create_image(text, output_path="output.jpg", background_url=None):
    """
    Creates an image with the text. If background_url is provided, it uses that image as background.
    Otherwise, uses a random colored background.
    """
    # Image settings
    width, height = 1080, 1080  # Default target size
    
    img = None
    
    # Try to load background from URL
    if background_url:
        try:
            response = requests.get(background_url)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGB")
            # Resize/Crop to fit 1080x1080 or keep aspect ratio?
            # Let's resize to fit width 1080 and crop height or vice versa
            # For simplicity, let's just resize to cover 1080x1080
            
            # Calculate aspect ratio
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Image is wider, resize by height
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                # Image is taller, resize by width
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (new_width - width) / 2
            top = (new_height - height) / 2
            right = (new_width + width) / 2
            bottom = (new_height + height) / 2
            
            img = img.crop((left, top, right, bottom))
            
            # Darken the image slightly to make text pop
            # Create a black overlay with transparency (Increased opacity from 100 to 140 for better contrast)
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 140))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay).convert('RGB')
            
        except Exception as e:
            print(f"Error loading background URL: {e}")
            img = None

    # Fallback if no image or error
    if img is None:
        bg_color = (
            random.randint(0, 50),
            random.randint(0, 50),
            random.randint(0, 50)
        )
        img = Image.new('RGB', (width, height), color=bg_color)

    draw = ImageDraw.Draw(img)

    # Load font
    try:
        # Check for common fonts in Docker/Linux or Windows
        # Added Impact.ttf which is thicker, or Arial Bold
        possible_fonts = ["Impact.ttf", "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
        font_path = None
        for f in possible_fonts:
            try:
                ImageFont.truetype(f, 20) # Test open
                font_path = f
                break
            except:
                continue
        
        if font_path:
            # Increased font size from 80 to 110
            font_size = 110
            font = ImageFont.truetype(font_path, font_size)
        else:
            raise IOError("No font found")
    except IOError:
        font = ImageFont.load_default()
        font_size = 40

    text_color = (255, 255, 255) # White

    # Wrap text
    # Adjusted wrap width since font is bigger (from 15 to 12 chars per line approx)
    lines = textwrap.wrap(text, width=12) 
    
    # Calculate text position
    total_text_height = 0
    line_heights = []
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        # Increased spacing between lines
        total_text_height += h + 30

    current_y = (height - total_text_height) / 2

    # Helper for outlined text
    def draw_text_with_outline(draw, position, text, font, text_color, outline_color, outline_width=5):
        x, y = position
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color)

    # Draw text
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (width - w) / 2
        
        # Increased outline width from 4 to 6
        draw_text_with_outline(draw, (x, current_y), line, font, text_color, (0, 0, 0), 6)
        current_y += line_heights[i] + 30

    # Add watermark
    footer = "@NelCuloBot"
    try:
        if font_path:
            footer_font = ImageFont.truetype(font_path, 50) # Increased footer size
        else:
            footer_font = ImageFont.load_default()
    except:
        footer_font = ImageFont.load_default()
        
    f_bbox = draw.textbbox((0, 0), footer, font=footer_font)
    f_w = f_bbox[2] - f_bbox[0]
    
    draw_text_with_outline(draw, ((width - f_w) / 2, height - 100), footer, footer_font, (220, 220, 220), (0,0,0), 3)

    # Save with higher quality
    img.save(output_path, quality=95, subsampling=0)
    return output_path

if __name__ == "__main__":
    # Test with a dummy URL (google logo or similar, but let's just test fallback for now or use a placeholder)
    # create_image("Harry Potter e la pietra filosofale nel c*lo", background_url="https://image.tmdb.org/t/p/w500/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg")
    create_image("Harry Potter e la pietra filosofale nel c*lo")
    print("Test image created: output.jpg")
