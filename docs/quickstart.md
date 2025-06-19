# Sculpture System - Quick Start Guide

This guide will help you deploy the complete sculpture audio system with three Raspberry Pi sculptures and one control laptop.

## Prerequisites

- 3x Raspberry Pi Zero W with SD cards (16GB+)
- 1x Laptop/PC running **Windows 10/11 with WSL 2** (control node)
- HAT IQaudIO Pi-Codec Zero audio interfaces for each Pi

## Step 1: Setup Control Node (WSL 2 and Ansible)

First, set up the Windows Subsystem for Linux (WSL 2) and install Ansible, which is used to automate the configuration of all devices.

1.  **Install WSL 2:** Open PowerShell as an Administrator and run:
    ```powershell
    wsl --install -d Ubuntu-22.04
    ```
    This will install Ubuntu 22.04. Your computer will likely need to restart.

2.  **Install Ansible:** After the restart, open your new Ubuntu terminal. It will perform a one-time setup. Once you have a command prompt, run the following commands to update the system and install Ansible:
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install ansible -y
    ```

**Important WSL 2 Network Notes:**
- WSL 2 uses a virtual network adapter. If you have multiple WSL distributions (e.g., one for Docker Desktop), ensure you are running subsequent commands in your `Ubuntu-22.04` instance. You can launch it specifically with `wsl -d Ubuntu-22.04` and set it as default with `wsl -s Ubuntu-22.04`.

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

## Step 5: Find Your WSL IP Address

In your WSL Ubuntu terminal:

```bash
# Find your WSL IP address
ip addr show eth0 | grep inet

# Note the IP address (e.g., 172.20.10.2)
```

## Step 6: Update Inventory File

Edit `edge/ansible/hosts.ini` with your actual IP addresses:

```ini
[sculptures]
sculpture1 ansible_host=YOUR_PI1_IP id=1 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture2 ansible_host=YOUR_PI2_IP id=2 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
sculpture3 ansible_host=YOUR_PI3_IP id=3 alsa_device=hw:1,0 control_host=YOUR_WSL_IP
```

## Step 7: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping
```

Note: The `player-live` service uses `mpv` with a 10-second cache (`--cache-secs=10`) to reduce network jitter. To increase or decrease this buffer, edit `edge/systemd/player-live.service.j2` and modify the `--cache-secs` value before re-running the playbook.

Running this playbook also disables WiFi power saving on each Pi by creating `/etc/NetworkManager/conf.d/wifi-powersave.conf`.

## Step 8: Pre-configure Icecast Hostname (Critical)

Before you install the control node services, you must configure the Icecast server template. This ensures that when Icecast is installed, it's already set up to allow other devices on your network (like the Raspberry Pis) to connect to the audio streams.

1.  **Open the Icecast template file** with a text editor. This file is located at `server/templates/icecast.xml`.
2.  **Find the `<hostname>` tag** and replace `localhost` with the WSL IP address you found in Step 5.

    *Before:*
    ```xml
    <hostname>localhost</hostname>
    ```

    *After (example):*
    ```xml
    <hostname>172.20.10.2</hostname>
    ```
3.  **Save and close the file.**

This is a one-time setup. The Ansible playbook will now use your pre-configured file during installation.

## Step 9: Audio‑HAT Preparation (required for IQaudIO CODEC / Codec Zero)
On each Pi:

1. `sudo alsactl --file Codec_Zero_OnboardMIC_record_and_SPK_playback.state restore IQaudIOCODEC`
2. *(optional)* `sudo alsactl store`
3. Test: `arecord -D hw:1,0 -f S16_LE -c 2 -r 44100 -d 5 test.wav && aplay -D hw:1,0`
4. Copy to wsl: `scp pi@sculptureX:~/test.wav .` and check for sound

## Step 10: Install Control Node Services

Now, run the Ansible playbook that installs and configures all the local services on your WSL machine (Icecast, Liquidsoap, Mosquitto, Node-RED).

```bash
# In WSL Ubuntu terminal, ensure you are in your project directory
# cd /path/to/your/yaga2025sculptures
# Run the control node playbook
ansible-playbook server/ansible/install_control_node.yml
```



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

## Troubleshooting

### Service Issues After Playbook

* **Mosquitto:** If Mosquitto fails to start (check `sudo systemctl status mosquitto.service`), it might be due to a duplicate `log_dest file` configuration.
  1. Confirm error: `/usr/sbin/mosquitto -c /etc/mosquitto/mosquitto.conf`.
  2. If duplicate `log_dest` error, edit `/etc/mosquitto/conf.d/sculpture.conf` (e.g., `sudo nano /etc/mosquitto/conf.d/sculpture.conf`) and comment out the `log_dest file ...` line.
  3. Then: `sudo systemctl restart mosquitto` and check status.

* **Node-RED:** If Node-RED fails to start:
  1. Check logs: `sudo journalctl -xeu node-red.service`.
  2. Common issues include incorrect Node.js version or wrong path to the `node-red` executable in `/etc/systemd/system/node-red.service`. Ensure `ExecStart` points to the correct path.
  3. After resolving issues, restart the service and verify:
     ```bash
     sudo systemctl restart node-red
     sudo systemctl status node-red
     ```

### Network Connectivity

1. **Identify the WSL IP address** on the control node:
   ```bash
   ip addr show eth0
   ```
2. **Verify connectivity from each Raspberry Pi:**
   ```bash
   ping YOUR_WSL_IP
   telnet YOUR_WSL_IP 1883  # MQTT
   telnet YOUR_WSL_IP 8000  # Icecast
   ```
3. **Check firewall rules** on the control node if connections fail:
   ```bash
   sudo ufw status
   sudo ufw allow icmp
   sudo ufw allow 8000/tcp
   sudo ufw allow 1883/tcp
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
\n
