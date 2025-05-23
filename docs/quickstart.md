# Sculpture System - Quick Start Guide

This guide will help you deploy the complete sculpture audio system with three Raspberry Pi sculptures and one control laptop.

## Prerequisites

- 3x Raspberry Pi 4 with SD cards (16GB+)
- 1x Laptop/PC running **Windows 10/11 with WSL 2** (control node)
- USB audio interfaces for each Pi
- Network connectivity between all devices
- SSH access configured on all Pis

## Step 0: Setup WSL 2 (Windows Control Node)

If using Windows as the control node, set up WSL 2 first:

```powershell
# In PowerShell as Administrator
wsl --install -d Ubuntu-22.04

# After restart, open Ubuntu terminal and update
sudo apt update && sudo apt upgrade -y
```

**Important WSL 2 Network Notes:**
- WSL 2 uses a virtual network adapter
- Your WSL IP will be different from your Windows IP
- Use `ip addr show eth0` in WSL to find your WSL IP address
- Raspberry Pis should connect to your **WSL IP**, not Windows IP

## Step 1: Flash Raspberry Pi SD Cards

1. Flash Raspberry Pi OS Lite to three SD cards
2. Enable SSH by creating empty `ssh` file in boot partition
3. Configure WiFi by creating `wpa_supplicant.conf` in boot partition:

```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiName"
    psk="YourWiFiPassword"
}
```

4. Boot each Pi and note their IP addresses

## Step 2: Find Your WSL IP Address

In your WSL Ubuntu terminal:

```bash
# Find your WSL IP address
ip addr show eth0 | grep inet

# Note the IP address (e.g., 172.20.10.2)
# This is what you'll use as YOUR_LAPTOP_IP in the next step
```

## Step 3: Update Inventory File

Edit `edge/ansible/hosts.ini` with your actual IP addresses:

```ini
[sculptures]
sculpture1 ansible_host=YOUR_PI1_IP id=1 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture2 ansible_host=YOUR_PI2_IP id=2 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture3 ansible_host=YOUR_PI3_IP id=3 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
```

**Note:** Use your WSL IP address (from Step 2) as `control_host`, not your Windows IP.

## Step 4: Configure SSH Keys

```bash
# In WSL Ubuntu terminal
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy to each Pi
ssh-copy-id pi@YOUR_PI1_IP
ssh-copy-id pi@YOUR_PI2_IP
ssh-copy-id pi@YOUR_PI3_IP
```

## Step 5: Install Ansible (in WSL)

```bash
# In WSL Ubuntu terminal
sudo apt update
sudo apt install ansible
```

## Step 6: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping
```

## Step 7: Install Control Node Services

```bash
# Run the control node playbook
ansible-playbook server/ansible/install_control_node.yml

# Verify services are running
sudo systemctl status icecast2
sudo systemctl status mosquitto
sudo systemctl status liquidsoap
sudo systemctl status node-red
```

## Step 8: Start Audio Processing

```bash
# Start Liquidsoap for audio mixing
sudo systemctl start liquidsoap

# Check Liquidsoap logs
sudo journalctl -u liquidsoap -f
```

## Step 9: Access Control Dashboard

**From Windows:**
1. Open web browser to `http://YOUR_WSL_IP:1880/ui`
2. You should see the sculpture control dashboard
3. Test volume sliders and mode switches

**From WSL:**
```bash
# You can also access from within WSL
curl http://localhost:1880/ui
```

## Step 10: Verify Audio Streams

1. **Check Icecast status:** `http://YOUR_WSL_IP:8000`
2. **Verify sculpture microphone streams are active:**
   - `http://YOUR_WSL_IP:8000/s1-mic.ogg`
   - `http://YOUR_WSL_IP:8000/s2-mic.ogg`
   - `http://YOUR_WSL_IP:8000/s3-mic.ogg`
3. **Verify personalized mixes are available:**
   - `http://YOUR_WSL_IP:8000/mix-for-1.ogg`
   - `http://YOUR_WSL_IP:8000/mix-for-2.ogg`
   - `http://YOUR_WSL_IP:8000/mix-for-3.ogg`

## Step 11: Test System Operation

1. **Live Mode Test:**
   - Switch to "Live Mode" in dashboard
   - Speak into microphones on sculptures
   - Verify each sculpture hears the other two (not itself)

2. **Volume Control Test:**
   - Adjust volume sliders in dashboard
   - Verify volume changes on respective sculptures

3. **Status Monitoring:**
   - Check CPU and temperature gauges update every 5 seconds
   - Verify MQTT communication is working

## WSL 2 Specific Considerations

### Network Access
- **From Windows:** Access services using WSL IP address
- **From other devices:** Raspberry Pis connect to WSL IP
- **Port forwarding:** WSL 2 automatically forwards ports to Windows

### File System
- **WSL files:** Located at `\\wsl$\Ubuntu-22.04\home\username\`
- **Windows files:** Accessible from WSL at `/mnt/c/`
- **Performance:** Keep project files in WSL filesystem for better performance

### Service Management
- All services run inside WSL
- Use `sudo systemctl` commands from WSL terminal
- Services persist across WSL sessions

## Troubleshooting

### WSL 2 Network Issues
```bash
# Check WSL IP address
ip addr show eth0

# Test connectivity from Pi to WSL
# (run on Raspberry Pi)
ping YOUR_WSL_IP

# Check if ports are accessible
# (run on Raspberry Pi)
telnet YOUR_WSL_IP 1883  # MQTT
telnet YOUR_WSL_IP 8000  # Icecast
```

### WSL 2 Service Issues
```bash
# Check WSL services
sudo systemctl status icecast2
sudo systemctl status mosquitto
sudo systemctl status liquidsoap
sudo systemctl status node-red

# Restart WSL if needed
# (from Windows PowerShell)
wsl --shutdown
wsl
```

### Pi Agent Not Starting
```bash
# Check pi-agent service on each Pi
sudo systemctl status pi-agent
sudo journalctl -u pi-agent -f

# Restart if needed
sudo systemctl restart pi-agent
```

### Audio Issues
```bash
# Check audio devices
aplay -l
arecord -l

# Test audio capture
arecord -D hw:1,0 -f cd test.wav

# Check DarkIce status
sudo systemctl status darkice
```

### Network Issues
```bash
# Test MQTT connectivity
mosquitto_pub -h YOUR_WSL_IP -t test -m "hello"
mosquitto_sub -h YOUR_WSL_IP -t test

# Check Icecast connectivity
curl http://YOUR_WSL_IP:8000/status.xsl
```

### Liquidsoap Issues
```bash
# Check Liquidsoap logs
sudo journalctl -u liquidsoap -f

# Test Liquidsoap config
liquidsoap --check /etc/liquidsoap/main.liq

# Connect to telnet interface
telnet localhost 1234
# Password: admin
```

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sculpture 1   │    │   Sculpture 2   │    │   Sculpture 3   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Microphone  │ │    │ │ Microphone  │ │    │ │ Microphone  │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   DarkIce   │ │    │ │   DarkIce   │ │    │ │   DarkIce   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  Pi-Agent   │ │    │ │  Pi-Agent   │ │    │ │  Pi-Agent   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Speaker   │ │    │ │   Speaker   │ │    │ │   Speaker   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────────┐
                    │   Windows + WSL 2       │
                    │                         │
                    │ ┌─────────────────────┐ │
                    │ │      Icecast2       │ │
                    │ └─────────────────────┘ │
                    │ ┌─────────────────────┐ │
                    │ │     Liquidsoap      │ │
                    │ └─────────────────────┘ │
                    │ ┌─────────────────────┐ │
                    │ │     Mosquitto       │ │
                    │ └─────────────────────┘ │
                    │ ┌─────────────────────┐ │
                    │ │      Node-RED       │ │
                    │ └─────────────────────┘ │
                    └─────────────────────────┘
```

## Default Credentials

- **Icecast Admin:** admin / hackme
- **Liquidsoap Telnet:** admin
- **MQTT:** No authentication (local network only)
- **Node-RED Dashboard:** No authentication

## Next Steps

1. Configure audio levels and processing in Liquidsoap
2. Add custom loop files to `/opt/sculpture-system/shared-loops/`
3. Customize Node-RED dashboard for your installation
4. Set up monitoring and alerting
5. Configure firewall rules for production deployment

For advanced configuration and troubleshooting, see the individual component documentation in each service directory. 