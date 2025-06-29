# Sculpture System - Quick Start Guide

This guide will help you deploy the complete sculpture audio system with three Raspberry Pi and one control laptop.

## Prerequisites

- 1x Laptop/PC running **Windows 10/11 with WSL 2** (control node)
- 3x Raspberry Pi Zero W (edge devices)
- 3x HAT IQaudIO Pi-Codec Zero sound cards
- 3x Transducers
- 3x microSD cards 16GB+

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

1. Flash Raspberry Pi OS Lite to three SD cards using Raspberry pi Imager
2. Before flashing set custom settings to enable SSH and configure WiFi 
3. Boot each Pi and note their IP addresses

## Step 3: Update and Upgrade Pis


```bash
# In each Pi terminal run
sudo apt update
sudo apt upgrade -y
```

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
sculpture1 ansible_host=YOUR_PI1_IP id=1 alsa_device=hw:1,0 control_host=YOUR_CONTROl_NODE_IP
sculpture2 ansible_host=YOUR_PI2_IP id=2 alsa_device=hw:1,0 control_host=YOUR_CONTROl_NODE_IP
sculpture3 ansible_host=YOUR_PI3_IP id=3 alsa_device=hw:1,0 control_host=YOUR_CONTROl_NODE_IP
```

## Step 6: Deploy to Raspberry Pis

Select sculpture system's audio approach by editing in edge/ansible/group_vars/all.yml audio_backend variable value to either `pulse` or `alsa`.

## Step 7: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml
```

This command runs the main Ansible playbook, which automates the entire configuration process for each Raspberry Pi. The playbook performs the following tasks in order:

**1. System Preparation:**

1.  **Update package cache:** Updates the list of available packages from the repositories.
2.  **Upgrade installed packages:** Upgrades all installed system packages to their latest versions.
3.  **Install required packages:** Installs essential software: `darkice` (for audio streaming), `mpv` (for audio playback), `python3-paho-mqtt` (for MQTT communication), `rsync` (for file synchronization), `alsa-utils`, `python3-pip`, `git`, and `pulsemixer`.
4.  **Install PulseAudio (PulseAudio mode only):** Conditionally installs `pulseaudio` if the `audio_backend` variable in `group_vars/all.yml` is set to `pulse`.
5.  **Disable WiFi power saving:** Creates a configuration file to disable WiFi power-saving mode, ensuring a stable network connection for streaming.

**2. Audio Hardware Setup:**

6.  **Detect & Set Boot Config Path:** Checks for the correct location of the Raspberry Pi's boot configuration file (`/boot/config.txt` or `/boot/firmware/config.txt`) and sets a variable for use in subsequent tasks.
7.  **Enable IQaudIO Codec & I2S:** Modifies the boot configuration to load the `iqaudio-codec` device tree overlay and ensures the I2S interface (`dtparam=i2s=on`) is enabled. Both are required to activate the IQaudIO sound card HAT.
8.  **Disable Built-in Audio:** Disables the Raspberry Pi's onboard audio (`dtparam=audio=off`) to prevent conflicts with the IQaudIO HAT.
9.  **Reboot if Audio Config Changed:** Automatically reboots the Pi if any of the above boot settings were changed, as a reboot is required for them to take effect.
10. **Find & Set IQaudIO Card Number:** Identifies and saves the system's card number for the IQaudIO sound card for use in mixer configuration.
11. **Configure ALSA Mixer (Mic & Speaker):** Uses the `amixer` command to set the appropriate controls and volume levels for both the microphone input and speaker output channels.

**3. Application & Audio Files:**

12. **Create Sculpture System Directory:** Creates the main application directory at `/opt/sculpture-system` where all project files will be stored.
13. **Check for ffmpeg on Control Node:** Verifies that the `ffmpeg` command-line tool is installed on the control machine (your WSL instance). The playbook will fail with an error if it's not found.
14. **Convert Loop Files Locally:** On your control machine, it creates a temporary directory, then uses `ffmpeg` to convert all `.wav` files from the `samples/` directory to the sample rate and channel count defined in the Ansible variables.
15. **Copy Converted Loop Files:** Copies the newly converted audio files from the temporary directory on your control machine to the `/opt/sculpture-system/` directory on each Raspberry Pi.
16. **Clean Up Temporary Directory:** Removes the temporary directory and its contents from your control machine.

**4. Configuration:**

17. **Template Application Scripts:** Creates the `pi-agent.py`, `audio_manager.py`, and `system_manager.py` scripts from templates, filling in necessary configuration.
18. **Copy Status Collector:** Copies the `status_collector.py` script to the device.
19. **Template darkice Configuration:** Generates a `darkice.cfg` file from a template, customized with the control node's IP and the sculpture's ID for streaming audio to the server.
20. **Configure PulseAudio Rate:** If using PulseAudio, it sets the correct default and alternate sample rates in `/etc/pulse/daemon.conf`.
21. **Configure ALSA for Shared Access:** If using ALSA, it creates an `/etc/asound.conf` file to allow multiple applications to use the audio device simultaneously.
22. **Create PulseAudio Sink:** If using PulseAudio, it sets up a special "null sink" which is used for routing and monitoring audio within the system.
23. **Enable PulseAudio TCP Access:** Allows remote monitoring of PulseAudio streams over the network for debugging.

**5. Service Management:**

24. **Install systemd Services:** Creates and installs `systemd` service files for `darkice`, `pi-agent`, `player-live` (for live playback), and `player-loop` (for local track playback). This allows the applications to run as background services.
25. **Enable and Start Services:** Enables and starts the `darkice`, `player-live`, `player-loop`, and `pi-agent` services so they launch on boot.
26. **Disable player-loop by Default:** Immediately disables and stops the `player-loop` service, as it's only intended to be activated on demand by the `pi-agent`.
27. **Ensure pi-agent is Running:** Double-checks that the main `pi-agent` service is started and enabled.
28. **Grant Sudo Access to pi-agent:** Adds a `sudoers` file that allows the `pi-agent` script to start and stop the other audio-related services without needing a password, enabling autonomous control.

The playbook handles all the setup, so you don't have to configure each Pi manually.

# Verify deployment
ansible sculptures -i edge/ansible/hosts.ini -m ping


## Step 8: Install Control Node Services

Now, run the Ansible playbook that installs and configures all the local services on your WSL machine (Icecast, Liquidsoap, Mosquitto, Node-RED).

```bash
# In WSL Ubuntu terminal, ensure you are in your project directory
# cd /path/to/your/yaga2025sculptures
# Run the control node playbook
sudo ansible-playbook -i server/ansible/hosts.ini server/ansible/install_control_node.yml
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
