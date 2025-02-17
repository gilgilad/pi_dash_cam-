##
sudo raspi-config 
sdp enable 

sudo nano /etc/rc.local

# Add before exit 0:
#!/bin/bash
# /etc/rc.local

# Wait for network
sleep 10

python3 /home/pi/repos/pi_dash_cam-/record.py &
python3 /home/pi/repos/pi_dash_cam-/purge_old_recording.py &
python -m http.server -d /home/pi/recordings/ &
exit  0 


sudo chmod +x /etc/rc.local
sudo systemctl status rc-local.service

sudo pip3 install waveshare-epaper --break-system-packages
