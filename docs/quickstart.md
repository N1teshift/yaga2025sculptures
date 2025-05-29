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
sudo apt install ansible -y
```

## Step 6: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping
```

## Step 6.5: Install Node.js and Node-RED Dashboard prerequisites (Control Node)

Node-RED (installed in the next step by Ansible) requires a modern version of Node.js (e.g., v18 LTS or newer). The default Node.js in Ubuntu repositories might be too old. Additionally, the Node-RED dashboard UI components need to be installed.

**1. Install/Verify Node.js Version:**
It's recommended to install Node.js using NodeSource for a system-wide compatible version.

```bash
# In WSL Ubuntu terminal
sudo apt update
sudo apt install -y curl # Ensure curl is installed
# Install Node.js (e.g., v22.x - choose a current LTS or recent version)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
# Or for Node.js 20.x (another good LTS choice):
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
# Verify installation (should show the new version, e.g., v22.x.x)
echo "Node version: $(node -v)"
echo "Node path: $(which node)" # Should be /usr/bin/node
```
**Note:** If `sudo apt-get install -y nodejs` fails due to file conflicts (e.g., with `libnode-dev` or `common.gypi`), you may need to remove older Node.js-related packages first:
`sudo apt-get remove --purge libnode-dev nodejs-doc npm node-gyp` (and others if listed)
`sudo apt autoremove -y && sudo apt clean`
Then retry the `sudo apt-get install -y nodejs` command. If a specific file conflict persists, a forced overwrite might be needed as a last resort for the `.deb` package, followed by `sudo apt-get install -f -y`.

**2. Prepare for Node-RED Dashboard Module:**
(The actual module will be installed after Node-RED itself is set up by Ansible).

## Step 7: Install Control Node Services

```bash
# In WSL Ubuntu terminal, ensure you are in your project directory
# cd /path/to/your/yaga2025sculptures
# Run the control node playbook
ansible-playbook server/ansible/install_control_node.yml

# Verify services are running
sudo systemctl status icecast2
sudo systemctl status mosquitto
sudo systemctl status liquidsoap
sudo systemctl status node-red
```

**Troubleshooting after Ansible Playbook:**

*   **Mosquitto:** If Mosquitto fails to start (check `sudo systemctl status mosquitto.service`), it might be due to a duplicate `log_dest file` configuration.
    1.  Confirm error: `/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf`.
    2.  If duplicate `log_dest` error, edit `/etc/mosquitto/conf.d/sculpture.conf` (e.g., `sudo nano /etc/mosquitto/conf.d/sculpture.conf`) and comment out the `log_dest file ...` line (add `#` at the beginning).
    3.  Then: `sudo systemctl restart mosquitto` and check status.

*   **Node-RED:** If Node-RED fails to start:
    1.  Check logs: `sudo journalctl -xeu node-red.service`.
    2.  Common issues include incorrect Node.js version (addressed in Step 6.5) or path issues for the `node-red` executable in `/etc/systemd/system/node-red.service`. Ensure `ExecStart` uses the correct path (usually `/usr/local/bin/node-red` or `/usr/bin/node-red`).
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

## Step 8: Start Audio Processing

```bash
# Start Liquidsoap for audio mixing
sudo systemctl start liquidsoap

# Check Liquidsoap logs
sudo journalctl -u liquidsoap -f
```

## Step 9: Access Control Dashboard

**From Windows:**
1. Open web browser. The Node-RED dashboard is often at `http://YOUR_WSL_IP:1880/ui`. If this path does not work, try `http://YOUR_WSL_IP:1880/dashboard` or `http://YOUR_WSL_IP:1880/api/ui/`. The Node-RED flow editor (usually at `http://YOUR_WSL_IP:1880/` or `http://YOUR_WSL_IP:1880/admin/`) typically has a sidebar tab for 'dashboard' with a direct launch button.
2. You should see the sculpture control dashboard.
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