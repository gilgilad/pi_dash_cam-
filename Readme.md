##
sudo raspi-config 
sdp enable 

sudo nano /etc/rc.local

# Add before exit 0:
python3 /home/pi/repos/pi_dash_cam-/record.py &
python3 /home/pi/repos/pi_dash_cam-/purge_old_recording.py &
python -m http.server -d /home/pi/recordings/ &


pip install waveshare-epaper --break-system-packages
