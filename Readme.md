##
sudo raspi-config 
sdp enable 

sudo nano /etc/rc.local
# Add before exit 0:
python3 /path/to/your/script.py &

pip install waveshare-epaper --break-system-packages