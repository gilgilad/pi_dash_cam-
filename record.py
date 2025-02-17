import sys
print( sys.executable)

import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import logging
import time
import epaper
import os
import threading
import subprocess
import psutil
logger = logging.getLogger(__name__)
DISPLAY_TYPE = "epd1in54"
VIDEO_SIZE = '640x480'
SEGMENT_TIME = 30


class StatusScreen:
    def __init__(self, epd, font):
        self.epd = epd
        self.font = font

        # Initialize base image
        self.base_image = Image.new('1', (self.epd.width, self.epd.height), 255)
        
        self.base_draw = ImageDraw.Draw(self.base_image)

        # Initialize display
        self.epd.init(self.epd.lut_full_update)
        self.epd.Clear()

        # Initialize state tracking attributes
        self.last_storage = None
        self.last_status = None
        self.blip_state = True
        self.last_elapsed = None

    def draw_storage_bar(self, draw, storage_percent, x, y, width, outlier_percent=None):
        """Draws a storage bar with an optional outlier."""

        draw.text((5, y ), f"Storage:", font=self.font, fill=0)
        y=y+self.font.getsize("Storage:")[1] + 10
        width_edge = width - 10
        draw.rectangle((x-7, y-7, x + width_edge+14, y + 10+14), fill=0)
        draw.rectangle((x-5, y-5, x + width_edge+12, y + 10+12), fill=1)  # Main bar
        bar_width = int(width_edge * (storage_percent / 100))
        draw.rectangle((x, y, x + bar_width, y + 10+7), fill=0)  # Main bar

        draw.rectangle((x, y + 30, x + len(f"{storage_percent}%")*24 , y + 30+24), fill=1)
        draw.text((x, y + 30), f"{storage_percent}%", font=self.font, fill=0)  # Text below bar
    
    def draw_blip_X(self, draw, x, y, size, recording=False):
        """Draws the blip animation (crosshair) with configurable parameters."""

        x1 = x
        y1 = y
        x2 = x + size  # Calculate the end points based on size
        y2 = y + size

        draw.line((x1, y1, x2, y2), width=3, fill=1)  # Initial crosshair
        draw.line((x1, y2, x2, y1), width=3, fill=1)

      
        if self.blip_state and not recording:  # Use self.blip_state for blinking
            draw.line((x1, y1, x2, y2), width=3, fill=0)  # Blinking part
            draw.line((x1, y2, x2, y1), width=3, fill=0) 
        
            

    def draw_status_screen(self, is_recording, elapsed_time, storage_percent, filename=None):
        draw = ImageDraw.Draw(self.base_image)
        self.epd.init(self.epd.lut_partial_update)
        # Update storage text and bar if value changed
        if self.last_storage != storage_percent:
            self.draw_storage_bar(draw, storage_percent, 10, 100, self.epd.width - 20)
            # bar_width = int((self.epd.width - 20) * (storage_percent / 100))
            # draw.rectangle((10, 75, 10 + bar_width, 85), fill=0)
            self.last_storage = storage_percent

        # Update status header text if value changed
        if self.last_status != is_recording:
            draw.rectangle((50, 2, 120, 20), fill=1)
            # self.epd.display(self.epd.getbuffer(self.base_image))
            status_text = "REC" if is_recording else "IDLE"
            draw.text((50, 2), f"{status_text}", font=self.font, fill=0 )
            self.last_status = is_recording
        def char_changed(last_elapsed, elapsed_time):
            for i in range(len(elapsed_time)):
                    if last_elapsed[i] != elapsed_time[i]:
                        return i
        if self.last_elapsed != elapsed_time:
            i = char_changed(self.last_elapsed, elapsed_time) if self.last_elapsed else 0
            draw.rectangle((5+i*10, 55, 200, 75), fill=1)
            # self.epd.display(self.epd.getbuffer(self.base_image))
        self.last_elapsed = elapsed_time
        # Always update elapsed time as it changes frequently
        draw.text((5, 55), f"Time:{elapsed_time}", font=self.font, fill=0)
        # draw a blinking X
        blip_x = 10  # X-coordinate of the blip
        blip_y = 5  # Y-coordinate of the blip
        blip_size = 30  # Size of the blip (crosshair length)


        self.draw_blip_X(draw, blip_x, blip_y, blip_size, is_recording)
        # Recording blip animation
        if is_recording:
            draw.ellipse((3, 3, 37, 37), outline=0)
            if self.blip_state:
                draw.ellipse((5, 5, 35, 35), fill=0)
            else:
                draw.ellipse((5, 5, 35, 35), fill=1)

        self.blip_state = not self.blip_state

        # Update display
        self.epd.display(self.epd.getbuffer(self.base_image.rotate(180)))



class RecorderDisplay:
    def __init__(self):
        self.epd  = epaper.epaper(DISPLAY_TYPE).EPD()
        self.font = ImageFont.truetype( '/usr/share/fonts/truetype/freefont/FreeMono.ttf', 24)
        # self.big_font = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 24)
        self.screen = StatusScreen(self.epd, self.font)
        self.init_display()

    def init_display(self):
        # Initialize display in full update mode for the first clear
        self.epd.init(self.epd.lut_full_update)
        self.epd.Clear(0xFF)
        logging.info("Display initialized")

  
    def clear(self):
        # Clear the display in full update mode
        self.epd.init(self.epd.lut_full_update)
        self.epd.Clear(0xFF)
        logging.info("Display cleared")

    def sleep(self):
        # Put the display to sleep
        self.epd.sleep()
        logging.info("Display sleeping")





class Recorder:
    def __init__(self, display):
        self.recording_process = None
        self.display = display
        self.start_time = None
        self.is_recording = False
        self.frame_interval = 10  # Seconds between thumbnails

    def start_recording(self, input_device, output_path):
        ROOT_PATH = os.getenv("ROOT_PATH", "/home/pi")
        RECORDINGS_PATH = os.getenv("RECORDINGS_PATH", "recordings")
        DATE_FMT = "%Y_%m_%d_%H"
        HOUR_FMT = "%H_%M_%S"
        SEGMENT_TIME = 30
        VIDEO_SIZE = os.getenv("VIDEO_SIZE", "640x480")
        Path(RECORDINGS_PATH).mkdir(parents=True, exist_ok=True)
        date = datetime.datetime.now()
        folder_name = date.strftime(DATE_FMT)
        time_prefix = date.strftime(HOUR_FMT)

        recording_path = os.path.join(ROOT_PATH, RECORDINGS_PATH, folder_name)
        Path(recording_path).mkdir(parents=True, exist_ok=True)
        
        # setup_logging(recording_path)
        logging.info(f"Starting recording session in {recording_path}")

        segments_path = os.path.join(recording_path, f"time_{time_prefix}_%03d.mp4")
        command = f'ffmpeg -i /dev/video0 -c:v libx264 -framerate 10 -s {VIDEO_SIZE} -an -sn -dn -vf "drawtext=fontfile=/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans-Bold.ttf:text=\'%{{localtime\\\\:%Y-%m-%d %T}}\' :fontcolor=white@0.8:fontsize=24:box=1:boxcolor=black@0.5:x=7:y=10" -segment_time {SEGMENT_TIME} -f segment {segments_path}'

        logging.info(f"Executing command: {command}")
        
        try:
            self.recording_process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            def print_output(process):
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break  # Process finished
                    print(line.strip())  # Print the line to the console

            # Start a separate thread to handle output
            output_thread = threading.Thread(target=print_output, args=(self.recording_process,))
            output_thread.daemon = True  # Allow the main thread to exit even if this thread is running
            output_thread.start()
            self.start_time = time.time()
            self.is_recording = True
            logging.info("Recording started")

        except Exception as e:
            logging.error(f"Recording start failed: {str(e)}")

    def __del__(self):
        self.stop_recording()
        self.display.clear()
        self.display.sleep()

    def stop_recording(self):
        if self.recording_process and self.recording_process.poll() is None:
            self.recording_process.terminate()
            self.recording_process.wait()
            self.is_recording = False
            logging.info("Recording stopped")

    def get_storage_percent(self):
        try:
            return psutil.disk_usage('/').percent
            pass
        except Exception as e:
            logging.error(f"Storage check failed: {str(e)}")
            return 0

    def update_display(self):
        while True:
            if self.is_recording:
                elapsed = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
                storage = self.get_storage_percent()
                self.display.screen.draw_status_screen(True, elapsed, storage)
            else:
                self.display.screen.draw_status_screen(False, "00:00:00", self.get_storage_percent())
            
            time.sleep(0.2)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        display = RecorderDisplay()
        recorder = Recorder(display)
        
        # Start display update thread
        display_thread = threading.Thread(target=recorder.update_display)
        display_thread.daemon = True
        display_thread.start()
        
        # Example usage:
        recorder.start_recording("/dev/video0","/home/pi/recordings/")
        while True:
            time.sleep(10)
        # recorder.stop_recording()
        
    except Exception as e:
        recorder.stop_recording()
        logger.error(f"An error occurred: {str(e)}")

