import os
import shutil
import logging
from pathlib import Path

# Environment variables and constants
ROOT_PATH = os.getenv("ROOT_PATH", "/home/pi")
RECORDINGS_PATH = os.getenv("RECORDINGS_PATH", "recordings")
PERCENTAGE_THRESHOLD = 25.0

# Configure logging
def setup_logging():
    log_file = os.path.join(ROOT_PATH, "cleanup.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to file
            logging.StreamHandler(),        # Log to screen (console)
        ],
    )

# Main script logic
try:
    # Set up logging
    setup_logging()

    # Check disk usage
    statvfs = os.statvfs(ROOT_PATH)
    free_bytes = statvfs.f_frsize * statvfs.f_bfree
    total_bytes = statvfs.f_frsize * statvfs.f_blocks
    free_bytes_percentage = ((1.0 * free_bytes) / total_bytes) * 100

    logging.info(f"Current free disk space: {free_bytes_percentage:.2f}%")

    if free_bytes_percentage < PERCENTAGE_THRESHOLD:
        logging.warning(f"Free disk space is below the threshold of {PERCENTAGE_THRESHOLD}%.")
        recordings_path = os.path.join(ROOT_PATH, RECORDINGS_PATH)

        # Collect all recordings
        recordings = []
        for dir_name in os.listdir(recordings_path):
            recording_path = os.path.join(recordings_path, dir_name)
            if os.path.isdir(recording_path):  # Ensure it's a directory
                recordings.append((recording_path, os.stat(recording_path).st_mtime))

        # Sort recordings by modification time (oldest first)
        recordings.sort(key=lambda tup: tup[1])

        if recordings:
            oldest_recording = recordings[0][0]
            logging.info(f"Deleting oldest recording: {oldest_recording}")
            shutil.rmtree(oldest_recording)
            logging.info(f"Deleted recording: {oldest_recording}")
        else:
            logging.warning("No recordings found to delete.")
    else:
        logging.info("Free disk space is above the threshold. No action required.")

except Exception as e:
    logging.error(f"An error occurred: {str(e)}", exc_info=True)