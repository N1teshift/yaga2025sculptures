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

## Step 5: Update Inventory File

Edit `edge/ansible/hosts.ini` with your actual IP addresses:

```ini
[sculptures]
sculpture1 ansible_host=YOUR_PI1_IP id=1 alsa_device=hw:1,0 control_host=YOUR_COMPUTER_IP
sculpture2 ansible_host=YOUR_PI2_IP id=2 alsa_device=hw:1,0 control_host=YOUR_COMPUTER_IP
sculpture3 ansible_host=YOUR_PI3_IP id=3 alsa_device=hw:1,0 control_host=YOUR_COMPUTER_IP
```

## Step 6: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml
```

This command runs the main Ansible playbook, which automates the entire configuration process for each Raspberry Pi. The playbook performs the following tasks in order:

*   **1. System Preparation:**
    *   Updates the package cache and upgrades all installed system packages.
    *   Installs essential software: `darkice` for audio streaming, `mpv` for audio playback, `paho-mqtt` for communication, and other system utilities.
    *   Disables WiFi power-saving to ensure a stable network connection.

*   **2. Audio Hardware Setup:**
    *   Detects the correct boot configuration file (`/boot/config.txt` or `/boot/firmware/config.txt`).
    *   Enables the `iqaudio-codec` overlay to activate the IQaudIO HAT.
    *   Disables the Raspberry Pi's built-in audio to prevent conflicts.
    *   Reboots the Pi if any of these audio settings were changed, which is necessary for them to take effect.

*   **3. Application & Audio Files:**
    *   Clones the official `Pi-Codec` git repository, which may contain helper scripts for the audio HAT.
    *   Creates the main application directory at `/opt/sculpture-system`.
    *   **On your control machine**, it converts all sample `.wav` files from the `samples` directory into the required format using `ffmpeg`.
    *   Copies the converted audio files from your machine to the `/opt/sculpture-system/` directory on each Pi.
    *   Copies the main `pi-agent.py` control script to `/opt/sculpture-system/` on each Pi.

*   **4. Configuration:**
    *   Generates a unique `darkice.cfg` file for each Pi from a template, inserting the correct server IP and sculpture ID.
    *   Configures PulseAudio with the correct sample rate to match the project's audio settings.
    *   Creates a `pi-agent` configuration file at `/etc/sculpture/audio.conf`.

*   **5. Service Management:**
    *   Sets up and installs `systemd` service files for `darkice`, `pi-agent`, `player-live`, and `player-loop`. This allows the applications to run as background services.
    *   Enables and starts the `darkice`, `player-live`, and `pi-agent` services so they launch on boot.
    *   Grants the `pi-agent` script passwordless `sudo` permissions to start and stop the other audio-related services, allowing it to control the system autonomously.

The playbook handles all the setup, so you don't have to configure each Pi manually.

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping

## Step 7: Pre-configure Icecast Hostname (Critical)

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

## Step 8: Audio-HAT Preparation (required for IQaudIO CODEC / Codec Zero)
On each Pi:

1. `sudo alsactl --file Codec_Zero_OnboardMIC_record_and_SPK_playback.state restore IQaudIOCODEC`
2. *(optional)* `sudo alsactl store`
3. Test: `arecord -D hw:1,0 -f S16_LE -c 2 -r 44100 -d 5 test.wav && aplay -D hw:1,0`
4. Copy to wsl: `scp pi@sculptureX:~/test.wav .` and check for sound

## Step 9: Install Control Node Services

Now, run the Ansible playbook that installs and configures all the local services on your WSL machine (Icecast, Liquidsoap, Mosquitto, Node-RED).

```bash
# In WSL Ubuntu terminal, ensure you are in your project directory
# cd /path/to/your/yaga2025sculptures
# Run the control node playbook
ansible-playbook server/ansible/install_control_node.yml
```

## Default Credentials

- **Icecast Admin:** admin / hackme
- **Liquidsoap Telnet:** admin
- **MQTT:** No authentication (local network only)
- **Node-RED Dashboard:** No authentication

## Testing

### 1. Test if WSL services are running
```bash
sudo systemctl status icecast2
sudo systemctl status liquidsoap
sudo systemctl status mosquitto
sudo systemctl status mqtt_to_telnet_bridge
sudo systemctl status node-red
```

### 2. Check CPU load averages of one of the Pis
```bash
htop
```
Load averages should be below 1.

### 3. Test Pi services status
```bash
sudo systemctl status darkice
```

```bash
sudo systemctl status pi-agent
```

Check if in player-live script mpv player is set to your prefered audio settings.

```bash
sudo systemctl status player-live
```

### 4. Check Icecast2 mounts existance
http://localhost:8000/admin/listmounts.xsl

Should see six mounts: mix-for-1, mix-for-2, mix-for-3, s1-mic, s2-mic, s3-mic.

If you dont see mix-for-1, mix-for-2, mix-for-3 - it means liquidsoap is bad.

If you dont see s1-mic, s2-mic, s3-mic - it means darkice is bad or the microphones. In such case on each Pi execute:
```bash
sudo systemctl restart darkice
```

### 5. Test Icecast2 mounts in VLC
Check if the desired microphone sound encoding coming from darkice matches the mix stream encoding coming from liquidsoap.

http://localhost:8000/s1-mic.ogg
http://localhost:8000/s2-mic.ogg
http://localhost:8000/s3-mic.ogg

http://localhost:8000/mix-for-1.ogg
http://localhost:8000/mix-for-2.ogg
http://localhost:8000/mix-for-3.ogg

### 6. Test sculpture_sink.monitor sound
```bash
ssh pi@<RASPBERRY_PI_IP> "pacat -r -d sculpture_sink.monitor" | pacat -p
```

### 7. Test Node-red connection with sculpture_sink.monitor
1. While listening to stream from sculpture_sink.monitor in your select Pi go to http://localhost:1880/api/ui

2. Check if CPU, Temperature, Microphone Level and Output Level gauges are active.

3. Slide the volume slider, the sound in sculpture_sink.monitur should change accordingly. Also you should see changes live in these:

```bash
journalctl -u pi-agent -f
```

```bash
mosquitto_sub -h localhost -t '#'
```

4.  Press the red MUTE button - the sculpture_sink.monitor sound should disapear and the red MUTE button should turn to a green UNMUTE button.

5.  Press the green UNMUTE button - the sculpture_sink.monitor sound should reapear and the green UNMUTE button should turn to a red MUTE button.

6. Click PLAN D button to test local tracks playback. The modes of all sculptures should change from LIVE to LOCAL. Listen in the sculpture_sink.monitor if the default test1.wav track is playing.

7. Check if in player-loop script mpv player is set to your prefered audio settings.

```bash
sudo systemctl restart player-loop
journalctl -u player-loop.service -f
```

8. In the Select Track dropdown select a prefered track and then click the LOAD LOCAL TRACK button below. This should change the track in the player-loop script.

9. Change plan back to B1 or A1. This should disable the LOAD LOCAL TRACK buttons and make the live sound come back.

10. 


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
