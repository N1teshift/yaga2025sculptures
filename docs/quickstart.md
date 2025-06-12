# Sculpture System - Quick Start Guide

This guide will help you deploy the complete sculpture audio system with three Raspberry Pi sculptures and one control laptop.

## Prerequisites

- 3x Raspberry Pi Zero W with SD cards (16GB+)
- 1x Laptop/PC running **Windows 10/11 with WSL 2** (control node)
- HAT IQaudIO Pi-Codec Zero audio interfaces for each Pi

## Step 1: Setup WSL 2 (Windows Control Node)

If using Windows as the control node, set up WSL 2 first:

```powershell
# In PowerShell as Administrator
# Optionally, first check existing WSL distributions: wsl -l -v
wsl --install -d Ubuntu-22.04

# After restart, open Ubuntu terminal and update
sudo apt update && sudo apt upgrade -y
```

**Important WSL 2 Network Notes:**
- WSL 2 uses a virtual network adapter. If you have multiple WSL distributions (e.g., one for Docker Desktop), ensure you are running subsequent commands in your `Ubuntu-22.04` instance. You can launch it specifically with `wsl -d Ubuntu-22.04` and set it as default with `wsl -s Ubuntu-22.04`.
- Your WSL IP will be different from your Windows IP
- Use `ip addr show eth0` in WSL to find your WSL IP address
- Raspberry Pis should connect to your **WSL IP**, not Windows IP

## Step 2: Flash Raspberry Pi SD Cards

1. Flash Raspberry Pi OS Lite to three SD cards
2. Enable SSH by creating empty `ssh` file in boot partition
3. Configure WiFi 
4. Boot each Pi and note their IP addresses

## Step 3: Update and Upgrade Pis

Run: `sudo apt update`
Run: `sudo apt upgrade -y`
(Optional): `sudo apt full-upgrade -y`
(Optional): sudo `apt autoremove -y`
(Optional): sudo `apt clean`

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


## Step 5: Audio‑HAT Preparation (required for IQaudIO CODEC / Codec Zero)
On each Pi:

1. `sudo apt update && sudo apt full-upgrade -y` → reboot
2. `sudo apt install -y git alsa-utils`
3. Edit `/boot/config.txt` (or could be `/boot/firmware/config.txt`): enable `dtoverlay=iqaudio-codec` and disable `dtparam=audio=on`; reboot
4. `git clone https://github.com/raspberrypi/Pi-Codec.git && cd Pi-Codec`
5. `sudo alsactl --file Codec_Zero_OnboardMIC_record_and_SPK_playback.state restore IQaudIOCODEC`
6. *(optional)* `sudo alsactl store`
7. Test: `arecord -D hw:1,0 -f S16_LE -c 2 -r 48000 -d 5 test.wav && aplay -D hw:1,0`
8. Copy to wsl: `scp pi@sculptureX:~/test.wav .` and check for sound


## Step 6: Find Your WSL IP Address

In your WSL Ubuntu terminal:

```bash
# Find your WSL IP address
ip addr show eth0 | grep inet

# Note the IP address (e.g., 172.20.10.2)
# This is what you'll use as YOUR_LAPTOP_IP in the next step
```

## Step 7: Update Inventory File

Edit `edge/ansible/hosts.ini` with your actual IP addresses:

```ini
[sculptures]
sculpture1 ansible_host=YOUR_PI1_IP id=1 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture2 ansible_host=YOUR_PI2_IP id=2 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture3 ansible_host=YOUR_PI3_IP id=3 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
```

**Note:** Use your WSL IP address (from Step 6) as `control_host`, not your Windows IP.

## Step 8: Install Ansible (in WSL)

```bash
# In WSL Ubuntu terminal
sudo apt update
sudo apt install ansible -y
```

## Step 9: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping
```

## Step 9.5: Install Node-RED Dashboard prerequisites (Control Node)

Node-RED (installed in the next step by Ansible) requires a modern version of Node.js. The playbook now installs Node.js automatically using the NodeSource repository, so manual installation is optional. You can still verify the version after the playbook completes:

```bash
node -v   # Should print a recent LTS version (18+)
```

**Prepare for Node-RED Dashboard Module:**
(The actual module will be installed after Node-RED itself is set up by Ansible.)

## Step 10: Install Control Node Services

This playbook also deploys the MQTT-to-Telnet bridge service used for
dynamic plan switching. The bridge runs under the dedicated `unix` user.

```bash
# In WSL Ubuntu terminal, ensure you are in your project directory
# cd /path/to/your/yaga2025sculptures
# Run the control node playbook
ansible-playbook server/ansible/install_control_node.yml

# OR

ansible-playbook -i inventory --ask-become-pass server/ansible/install_control_node.yml

# Verify services are running
sudo systemctl status icecast2
sudo systemctl status mosquitto
sudo systemctl status liquidsoap
sudo systemctl status node-red
sudo systemctl status mqtt_to_telnet_bridge
```

**Troubleshooting after Ansible Playbook:**

*   **Mosquitto:** If Mosquitto fails to start (check `sudo systemctl status mosquitto.service`), it might be due to a duplicate `log_dest file` configuration.
    1.  Confirm error: `/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf`.
    2.  If duplicate `log_dest` error, edit `/etc/mosquitto/conf.d/sculpture.conf` (e.g., `sudo nano /etc/mosquitto/conf.d/sculpture.conf`) and comment out the `log_dest file ...` line (add `#` at the beginning).
    3.  Then: `sudo systemctl restart mosquitto` and check status.

*   **Node-RED:** If Node-RED fails to start:
    1.  Check logs: `sudo journalctl -xeu node-red.service`.
    2.  Common issues include incorrect Node.js version (addressed in Step 9.5) or path issues for the `node-red` executable in `/etc/systemd/system/node-red.service`. Ensure `ExecStart` uses the correct path (usually `/usr/local/bin/node-red` or `/usr/bin/node-red`).
    3.  **Install `node-red-dashboard` module:** The UI components require this.
        ```bash
        # In WSL Ubuntu terminal, navigate to Node-RED's working/user directory.
        # This is often /opt/sculpture-system or a .node-red folder within it,
        # or /var/lib/node-red, or the home dir of the 'node-red' user.
        # For this project, /opt/sculpture-system is a good place:
        cd /opt/sculpture-system
        sudo npm install node-red-dashboard
        # Ensure the node-red user owns the installed module:
        sudo chown -R node-red:node-red /opt/sculpture-system/node_modules
        # If package-lock.json was created in /opt/sculpture-system:
        # sudo chown node-red:node-red /opt/sculpture-system/package-lock.json
        sudo systemctl restart node-red
        ```
    4. After restarting, check `sudo systemctl status node-red` again.

## Step 11: Start Audio Processing

```bash
# Start Liquidsoap for audio mixing
sudo systemctl start liquidsoap

# Check Liquidsoap logs
sudo journalctl -u liquidsoap -f
```

## Step 12: Access Control Dashboard

**From Windows:**
1. Open web browser. The Node-RED dashboard is often at `http://YOUR_WSL_IP:1880/ui`. If this path does not work, try `http://YOUR_WSL_IP:1880/dashboard` or `http://YOUR_WSL_IP:1880/api/ui/`. The Node-RED flow editor (usually at `http://YOUR_WSL_IP:1880/` or `http://YOUR_WSL_IP:1880/admin/`) typically has a sidebar tab for 'dashboard' with a direct launch button.
2. You should see the sculpture control dashboard.
3. Test volume sliders and mode/plan switches. Selecting plans A1–C now sends `{"mode":"live"}` and Plan D sends `{"mode":"local"}` so the players automatically switch modes.

**From WSL:**
```bash
# You can also access from within WSL
curl http://localhost:1880/ui
```

## Step 13: Verify Audio Streams

1. **Check Icecast status:** `http://YOUR_WSL_IP:8000`
2. **Verify sculpture microphone streams are active:**
   - `http://YOUR_WSL_IP:8000/s1-mic.ogg`
   - `http://YOUR_WSL_IP:8000/s2-mic.ogg`
   - `http://YOUR_WSL_IP:8000/s3-mic.ogg`
3. **Verify personalized mixes are available:**
   - `http://YOUR_WSL_IP:8000/mix-for-1.ogg`
   - `http://YOUR_WSL_IP:8000/mix-for-2.ogg`
   - `http://YOUR_WSL_IP:8000/mix-for-3.ogg`


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
sudo systemctl restart icecast2
sudo systemctl restart mosquitto
sudo systemctl restart liquidsoap
sudo systemctl restart node-red
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