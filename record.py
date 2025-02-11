from PIL import Image, ImageDraw, ImageFont
import logging
import time

class RecorderDisplay:
    def __init__(self):
        self.epd = epaper.epd(DISPLAY_TYPE).EPD()
        self.font = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 14)
        self.big_font = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 24)
        self.init_display()

    def init_display(self):
        # Initialize display in full update mode for the first clear
        self.epd.init(self.epd.lut_full_update)
        self.epd.Clear(0xFF)
        logging.info("Display initialized")

    def draw_partial_update(self, x, y, width, height, content_callback):
        """
        Update a specific region of the display.
        
        Args:
            x, y: Top-left corner of the region to update.
            width, height: Dimensions of the region to update.
            content_callback: A function that takes a PIL ImageDraw object and draws the content.
        """
        # Switch to partial update mode
        self.epd.init(self.epd.lut_partial_update)
        
        # Create a new image for the region
        partial_image = Image.new('1', (width, height), 255)  # 255 = white
        partial_draw = ImageDraw.Draw(partial_image)
        
        # Draw content using the callback
        content_callback(partial_draw)
        
        # Rotate the image if needed (depends on your display orientation)
        partial_image = partial_image.rotate(90, expand=True)
        
        # Paste the partial image onto the full display buffer
        full_image = Image.new('1', (self.epd.width, self.epd.height), 255)
        full_image.paste(partial_image, (x, y))
        
        # Display the updated region
        self.epd.displayPartial(self.epd.getbuffer(full_image))
        logging.info(f"Partial update at ({x}, {y}) with size {width}x{height}")

    def clear(self):
        # Clear the display in full update mode
        self.epd.init(self.epd.lut_full_update)
        self.epd.Clear(0xFF)
        logging.info("Display cleared")

    def sleep(self):
        # Put the display to sleep
        self.epd.sleep()
        logging.info("Display sleeping")

# Example usage
def update_timer(draw):
    current_time = time.strftime("%H:%M:%S")
    draw.rectangle((0, 0, 100, 20), fill=255)  # Clear the area
    draw.text((10, 5), current_time, font=font, fill=0)

def update_status(draw):
    draw.rectangle((0, 0, 100, 20), fill=255)  # Clear the area
    draw.text((10, 5), "Recording...", font=font, fill=0)

if __name__ == "__main__":
    display = RecorderDisplay()
    
    try:
        # Update a small region for a clock
        display.draw_partial_update(10, 10, 100, 20, update_timer)
        time.sleep(2)
        
        # Update another region for status
        display.draw_partial_update(10, 40, 100, 20, update_status)
        time.sleep(2)
        
    finally:
        display.clear()
        display.sleep()