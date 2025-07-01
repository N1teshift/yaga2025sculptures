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

## Step 6: Choose audio routing approach

Select sculpture system's audio approach by editing in edge/ansible/group_vars/all.yml audio_backend variable value to either `pulse` or `alsa`.

## Step 7: Deploy to Raspberry Pis

```bash
# Run the edge playbook to configure all Pis
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml
```

This command runs the main Ansible playbook, which automates the entire configuration process for each Raspberry Pi. The playbook handles all the setup, so you don't have to configure each Pi manually. The playbook performs the following tasks in order:

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

**5. Service Management:**

22. **Install systemd Services:** Creates and installs `systemd` service files for `darkice`, `pi-agent`, `player-live` (for live playback), and `player-loop` (for local track playback). This allows the applications to run as background services.
23. **Enable and Start Services:** Enables and starts the `darkice`, `player-live`, `player-loop`, and `pi-agent` services so they launch on boot.
24. **Disable player-loop by Default:** Immediately disables and stops the `player-loop` service, as it's only intended to be activated on demand by the `pi-agent`.
25. **Enable PulseAudio TCP Access:** If using PulseAudio, allows remote monitoring of PulseAudio streams over the network for debugging.
26. **Remove Old PulseAudio Sink Config:** If using PulseAudio, removes any old `sculpture_sink` configuration from the PulseAudio configuration to ensure a clean setup.
27. **Ensure pi-agent is Running:** Double-checks that the main `pi-agent` service is started and enabled.
28. **Grant Sudo Access to pi-agent:** Adds a `sudoers` file that allows the `pi-agent` script to start and stop the other audio-related services without needing a password, enabling autonomous control.

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

This command runs the control node Ansible playbook, which sets up all the server services on your WSL machine. The playbook performs the following tasks in order:

**1. System Preparation:**
1. **Update package cache:** Updates the list of available packages from the repositories.
2. **Add NodeSource Node.js repository:** Adds the official Node.js 20.x repository to enable installation of a recent Node.js version.
3. **Install required packages:** Installs essential server software: `icecast2` (streaming server), `liquidsoap` (audio mixer), `mosquitto` (MQTT broker), `mosquitto-clients` (MQTT tools), `nodejs` (JavaScript runtime), and `python3-pip` (Python package manager).
4. **Install Node-RED globally:** Installs Node-RED as a global npm package for flow-based programming and dashboard creation.

**2. User Management:**
5. **Create node-red user:** Creates a dedicated system user for running the Node-RED service securely.
6. **Create liquidsoap user:** Creates a dedicated system user for running the Liquidsoap audio mixer service.
7. **Create unix user for MQTT bridge:** Creates a system user for the MQTT to Telnet bridge service.

**3. Directory Structure:**
8. **Create sculpture system directory:** Creates the main application directory at `/opt/sculpture-system` with proper ownership for the node-red user.
9. **Create shared loops directory:** Creates a subdirectory for shared audio loop files.
10. **Create liquidsoap scripts directory:** Creates a subdirectory for Liquidsoap-related scripts and files.
11. **Create liquidsoap config directory:** Creates the system configuration directory at `/etc/liquidsoap` for Liquidsoap configuration files.

**4. Node-RED Configuration:**
12. **Install Node-RED dashboard:** Installs the Node-RED dashboard package for creating web-based control interfaces.
13. **Generate Node-RED flow configuration:** Creates the main Node-RED flow configuration from a template, customized with project-specific settings.
14. **Create Node-RED settings file:** Generates the Node-RED settings file with custom paths, security settings, and API endpoints configuration.

**5. Audio Streaming Configuration:**
15. **Configure Icecast2:** Templates the main Icecast2 configuration file with streaming server settings, mount points, and access credentials.
16. **Enable Icecast2 in default config:** Modifies the system default configuration to enable Icecast2 to start automatically.
17. **Template Liquidsoap main configuration:** Creates the main Liquidsoap script from a template with audio mixing logic and stream routing.
18. **Copy Liquidsoap presets:** Copies the Liquidsoap presets file containing audio effect and processing configurations.

**6. MQTT Communication:**
19. **Configure Mosquitto MQTT broker:** Creates the Mosquitto configuration file to enable anonymous connections on port 1883 for inter-service communication.

**7. Service Management:**
20. **Create Liquidsoap systemd service:** Installs the systemd service file for Liquidsoap with proper dependencies and restart behavior.
21. **Create Node-RED systemd service:** Installs the systemd service file for Node-RED with custom settings and working directory.
22. **Copy MQTT to Telnet bridge script:** Copies the Python script that bridges MQTT messages to Liquidsoap's telnet interface for real-time control.
23. **Install MQTT bridge Python dependencies:** Installs required Python packages for the MQTT bridge from the requirements.txt file.
24. **Copy MQTT to Telnet bridge service:** Installs the systemd service file for the MQTT bridge service.

**8. Final Setup:**
25. **Set ownership of sculpture directory:** Ensures all files in the sculpture system directory have the correct ownership for the node-red user.
26. **Enable and start services:** Enables and starts all five services (`icecast2`, `mosquitto`, `liquidsoap`, `node-red`, `mqtt_to_telnet_bridge`) so they launch on boot and begin running immediately.

The playbook configures a complete audio streaming and control infrastructure on your WSL machine.

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

### 3. Check Pi sinks and sources
```bash
pactl list sinks short
pactl list sources short
```

You should see only

```bash
0       alsa_output.platform-soc_sound.stereo-fallback  module-alsa-card.c      s16le 2ch 16000Hz       RUNNING
0       alsa_output.platform-soc_sound.stereo-fallback.monitor  module-alsa-card.c      s16le 2ch 16000Hz       IDLE
1       alsa_input.platform-soc_sound.stereo-fallback   module-alsa-card.c      s16le 2ch 16000Hz       RUNNING
```

### 4. Test Pi services status
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

### 5. Check Icecast2 mounts existance
http://localhost:8000/admin/listmounts.xsl

Should see six mounts: mix-for-1, mix-for-2, mix-for-3, s1-mic, s2-mic, s3-mic.

If you dont see mix-for-1, mix-for-2, mix-for-3 - it means liquidsoap is bad.

If you dont see s1-mic, s2-mic, s3-mic - it means darkice is bad or the microphones. In such case on each Pi execute:
```bash
sudo systemctl restart darkice
```

### 6. Test Icecast2 mounts in VLC
Check if the desired microphone sound encoding coming from darkice matches the mix stream encoding coming from liquidsoap.

http://localhost:8000/s1-mic.ogg
http://localhost:8000/s2-mic.ogg
http://localhost:8000/s3-mic.ogg

http://localhost:8000/mix-for-1.ogg
http://localhost:8000/mix-for-2.ogg
http://localhost:8000/mix-for-3.ogg

### 7. Test hardware audio output
Test the transducer/speaker output:
```bash
# Test speakers (always sink 0 on all sculptures)
timeout 3s speaker-test -c 1 -t sine -D pulse:0
```

### 8. Test PulseAudio hardware routing
Test the complete audio chain through PulseAudio:
```bash
# Test audio output with live stream (always sink 0)
mpv --no-video --audio-device=pulse/0 --audio-samplerate=16000 http://192.168.8.156:8000/mix-for-3.ogg
```

### 9. Test microphone input
Test the microphone input:
```bash
# Test microphone (always source 1 on all sculptures)
timeout 3s parec --device=1 --raw | od -t d2 -w2 | head -5
```

## Known issues

### Mountpoint ghost listeners

Sometimes for no apperant reason sculpture's microphone stream in icecast mointpoint can start gathering somekind of fake liquidsoap listeners and in this way the mointpoint reaches max 20 listeners and through VLC is not possible to listen to the stream anymore.
This can be fixed by restarting darkice on that sculpture's rasberry device.
```bash
sudo systemctl restart darkice
```

If that doesnt help then do a more proper restarting procedure:

```bash
# First on control node
sudo systemctl restart icecast2
sudo systemctl restart liquidsoap
```

```bash
# then on each Pi
sudo systemctl restart darkice
```
