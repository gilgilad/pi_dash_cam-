from PIL import Image, ImageDraw, ImageFont
import epaper

def update_display(is_recording, duration, storage_free, filename):
    # Initialize screen
    image = Image.new('1', (display.width, display.height), "white")
    draw = ImageDraw.Draw(image)
    
    # Draw status bar
    draw.rectangle([(0,0),(display.width,20)], fill="black")
    draw.text((5,2), "🎥 🎤 📁 📶", font=font_small, fill="white")
    
    # Main content
    if is_recording:
        draw.ellipse((50,30,80,60), fill="red")
        draw.text((90,40), "REC", font=font_large, fill="red")
    else:
        draw.text((40,40), "Ready", font=font_large, fill="black")
    
    # System info
    draw.text((5,70), f"Time: {duration}", font=font_small)
    draw.text((5,85), f"Storage: {storage_free} GB free", font=font_small)
    draw.text((5,100), f"File: {filename}", font=font_small)
    
    # Update physical display
    display.ShowImage(image)

DISPLAY_TYPE = "epd1in54"
epd=epaper.epaper(DISPLAY_TYPE).EPD()
epd.init(epd.lut_partial_update)
epd.Clear()