#!/bin/bash

# Log file location

LOG_FILE="/home/pi/wifi-autoconnect.log"
rm $LOG_FILE
exec > >(tee -a "$LOG_FILE") 2>&1

# Configuration
WIFI_INTERFACE="wlan0"
HOTSPOT_SSID="ti"
HOTSPOT_PASS="12345678"
WIFI_CONFIG="/etc/wpa_supplicant/wpa_supplicant.conf"
HOTSPOT_TIMEOUT=0  # Set to 0 for indefinite hotspot, or specify a timeout in seconds

# Function to log messages with timestamps
log() {
    echo "$(date): $1"
}

# Function to stop all network services
stop_network_services() {
    log "Stopping network services..."
    pkill wpa_supplicant
    pkill dhclient
    systemctl stop hostapd 2>/dev/null
    systemctl stop dnsmasq 2>/dev/null
    systemctl stop NetworkManager 2>/dev/null
    ip addr flush dev $WIFI_INTERFACE
    ip link set $WIFI_INTERFACE down
    log "Network services stopped."
}

start_wifi() {
    log "Attempting to connect to Wi-Fi..."

    # Bring the interface up
    #ip link set $WIFI_INTERFACE up
    #if [ $? -eq 0 ]; then
    #    log "Interface $WIFI_INTERFACE brought up successfully."
    #else
     #   log "Failed to bring up interface $WIFI_INTERFACE."
      #  return 1
    #fi
    log "Running Network Manager"
    sudo systemctl start NetworkManager 
    sleep 1
    log "Connection up"
    sudo nmcli connection up  188ee57a-ae3d-4318-b736-25d38dbb72ed
	
#    ip link set $WIFI_INTERFACE up

		
    # Start wpa_supplicant
    #log "Starting wpa_supplicant..."
    #if wpa_supplicant -B -i $WIFI_INTERFACE -c $WIFI_CONFIG; then
     #   log "wpa_supplicant started successfully."
    #else
     #   log "Failed to start wpa_supplicant."
    #    return 1
   # fi

    # Wait for connection
    log "Waiting for Wi-Fi connection..."
    sleep 10

    # Check connection status using iw
    log "Checking connection status..."
    CONNECTION_STATUS=$(iw dev $WIFI_INTERFACE link)
    if echo "$CONNECTION_STATUS" | grep -q "Connected to"; then
        SSID=$(echo "$CONNECTION_STATUS" | grep "SSID" | awk '{print $2}')
        log "Successfully connected to SSID: $SSID."
    else
        log "Failed to connect to any Wi-Fi network."
        return 1
    fi

    # Request an IP address using dhclient
    log "Requesting IP address using dhclient..."
    if dhclient $WIFI_INTERFACE; then
        IP_ADDRESS=$(ip addr show $WIFI_INTERFACE | grep "inet " | awk '{print $2}')
        log "Successfully connected to Wi-Fi. IP address: $IP_ADDRESS."
        return 0  # Success
    else
        log "Failed to obtain an IP address."
        return 1  # Failure
    fi
}

# Function to start hotspot (AP mode)
start_hotspot() {
    log "Starting hotspot..."

    # Configure network for hotspot
    log "Configuring network for hotspot..."
    ip link set $WIFI_INTERFACE down
    ip addr flush dev $WIFI_INTERFACE
    ip addr add 192.168.0.184/24 dev $WIFI_INTERFACE
    ip link set $WIFI_INTERFACE up
    if [ $? -eq 0 ]; then
        log "Network configured for hotspot."
    else
        log "Failed to configure network for hotspot."
        return 1
    fi

    # Configure hostapd
    log "Configuring hostapd..."
    cat > /etc/hostapd/hostapd.conf <<EOF
interface=$WIFI_INTERFACE
driver=nl80211
ssid=$HOTSPOT_SSID
hw_mode=g
channel=7
wmm_enabled=1
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$HOTSPOT_PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

    # Start hostapd
    log "Starting hostapd..."
    if hostapd -B /etc/hostapd/hostapd.conf; then
        log "hostapd started successfully."
    else
        log "Failed to start hostapd."
        return 1
    fi

    # Start dnsmasq
    log "Starting dnsmasq..."
    if systemctl restart dnsmasq; then
        log "dnsmasq started successfully."
    else
        log "Failed to start dnsmasq."
        return 1
    fi

    log "Hotspot is active. SSID: $HOTSPOT_SSID, Password: $HOTSPOT_PASS"

    # Keep hotspot active indefinitely or for a specified timeout
    if [ $HOTSPOT_TIMEOUT -gt 0 ]; then
        log "Hotspot will timeout in $HOTSPOT_TIMEOUT seconds..."
        sleep $HOTSPOT_TIMEOUT
        log "Hotspot timeout reached. Stopping hotspot..."
        stop_network_services
    else
        log "Hotspot is running indefinitely. Press Ctrl+C to stop."
        while true; do
            sleep 3600  # Keep the script running
        done
    fi
}

# Main script logic
log "Starting Wi-Fi autoconnect script..."

# Stop conflicting services
stop_network_services
#start_hotspot
stop_network_services


# Attempt to connect to Wi-Fi
if start_wifi; then
    log "Wi-Fi connection successful."
else
    log "Wi-Fi connection failed. Starting hotspot..."
    stop_network_services
    start_hotspot
fi

log "Script execution completed."
