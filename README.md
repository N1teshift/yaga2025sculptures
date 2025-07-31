# YAGA 2025 Sculptures - Interactive Audio System

A distributed audio system for interactive sculpture installations, featuring networked Raspberry Pi devices and centralized audio mixing. Successfully deployed at YAGA 2025 festival.

## 🎯 Project Overview

This system creates a network of three interactive sculptures, each equipped with a Raspberry Pi, microphone, and speaker. Each sculpture captures ambient audio and streams it to a central server, which creates personalized audio mixes that are played back through each sculpture's speaker, creating an immersive, responsive audio environment.

## 🏗️ System Architecture

- **🎤 Edge Devices (3x Raspberry Pi)**: Audio capture, streaming, and playback
- **🎛️ Control Server (Linux/WSL)**: Audio mixing engine, MQTT broker, web dashboard  
- **📡 Communication**: MQTT for device control, Icecast for audio streaming
- **🌐 Web Interface**: Real-time control and monitoring dashboard

## ✨ Key Features

- **🔄 Live Audio Processing**: Real-time capture, mixing, and playback
- **🎨 Dynamic Audio Mixing**: Each sculpture receives unique processed mixes via Liquidsoap
- **📱 Web Control Interface**: Volume control, mode switching, system monitoring
- **📊 Real-time Monitoring**: CPU, temperature, audio levels, service status
- **🚀 Automated Deployment**: Complete Ansible automation for reproducible setup
- **🎵 Flexible Playback**: Live streaming mode + local playlist fallback
- **⚡ High Performance**: Optimized for low-latency audio processing

## 🚀 Quick Start

### Prerequisites
- **Control Server**: Linux PC or Windows with WSL 2 (Ubuntu 22.04+ recommended)
- **Edge Devices**: 3x Raspberry Pi with audio HATs (IQaudIO codec recommended)
- **Network**: WiFi/Ethernet network connecting all devices
- **Software**: Ansible installed on control server

### Basic Setup

1. **Clone Repository:**
   ```bash
   git clone https://github.com/N1teshift/yaga2025sculptures.git
   cd yaga2025sculptures
   ```

2. **Configure Network:**
   ```bash
   # Update IP addresses in configuration files
   nano sculpture-system/edge/ansible/hosts.ini
   nano sculpture-system/server/ansible/hosts.ini
   ```

3. **Deploy System:**
   ```bash
   # Deploy to edge devices (Raspberry Pis)
   cd sculpture-system/edge/ansible
   ansible-playbook -i hosts.ini playbook.yml
   
   # Deploy to server
   cd ../../server/ansible  
   ansible-playbook -i hosts.ini playbook.yml
   ```

4. **Access Dashboard:**
   Open `http://YOUR_SERVER_IP:1880/ui` for the control interface

## 📁 Repository Structure

```
yaga2025sculptures/
├── sculpture-system/            # Core sculpture system
│   ├── 🎤 edge/                 #   Raspberry Pi sculpture devices
│   │   ├── ansible/             #     Automated deployment & configuration
│   │   ├── pi-agent/           #     Python modules for device control
│   │   ├── scripts/            #     Diagnostic and maintenance scripts
│   │   ├── darkice/            #     Audio streaming configuration
│   │   └── systemd/            #     Service definitions
│   ├── 🎛️ server/               #   Central control server
│   │   ├── ansible/            #     Server deployment automation
│   │   ├── liquidsoap/         #     Audio mixing engine
│   │   ├── node-red/           #     Web dashboard components
│   │   ├── server-agent/       #     Server monitoring & control
│   │   └── icecast/            #     Streaming server config
│   ├── 🎵 samples/              #   Audio content library
│   ├── ⚙️ audio_config.yml      #   Global audio settings
│   └── 📋 playlists.yml         #   Predefined audio playlists
├── 📚 GUIDE.md                  # Complete installation guide
└── 📜 LICENSE.md               # MIT License
```

## System Components

### Edge Devices (Raspberry Pi)
- **DarkIce:** Streams Raspebbry's microphone audio to Icecast server
- **MPV:** Plays audio streams from control server
- **Pi-Agent:** MQTT client for remote control and monitoring
- **PulseAudio:** Audio routing and volume control

### Control Server (Windows + WSL 2 or Linux)
- **Icecast2:** Audio streaming server
- **Liquidsoap:** Real-time audio mixing and processing
- **Mosquitto:** MQTT broker for device communication
- **Node-RED:** Web dashboard for system control

## Audio Flow

1. **Capture:** Each Pi captures audio via microphone
2. **Stream:** DarkIce streams audio to Icecast server
3. **Mix:** Liquidsoap creates personalized mixes for sculptures
4. **Distribute:** Mixed audio streams back to respective sculptures
5. **Play:** MPV plays the personalized mix through speakers

## Control Interface

Access the web dashboard at `http://CONTROL_SERVER_IP:1880/api/ui` to:
- Adjust volume for each sculpture
- Switch between live and local playback modes
- Switch between liquidsoap mix routing plans A1, A2, B1, B2, B3, C and D
- Monitor system status (CPU, temperature)
- Monitor microphone and output level
- Emergency stop functionality
- Mute functionality

## MQTT Topics

- `sculpture/{id}/cmd` - Commands to individual sculptures
- `sculpture/{id}/status` - Status updates from sculptures
- `system/broadcast` - System-wide commands

### Command Examples

```json
// Volume control (0.0 to 1.0)
{"volume": 0.7}

// Switch to live mode
{"mode": "live"}

// Switch to local playback
{"mode": "local", "track": "ambient.wav"}
```

## Audio Streams

- **Input Streams:** `http://server:8000/s{1-3}-mic.ogg`
- **Output Mixes:** `http://server:8000/mix-for-{1-3}.ogg`

## Requirements

### Hardware
- 3x Raspberry Pi Zero W
- 3x Microphones
- 3x Speakers/Amplifiers
- 1x Control laptop/PC
- Network infrastructure (WiFi/Ethernet)

### Software
- **Edge Devices:** Raspberry Pi OS Lite
- **Control Server:**
  - Windows 10/11 with WSL 2 (Ubuntu 22.04 recommended), OR
  - Native Ubuntu/Debian Linux
- **Deployment:** Ansible (installed in WSL or Linux)

## Configuration

### Network Setup
Update IP addresses in:
- `edge/ansible/hosts.ini`
- Service configuration files

### Audio Devices
Configure ALSA device names in:
- `edge/ansible/hosts.ini` (alsa_device variable)
- `edge/darkice/darkice.cfg`

### Security
Default passwords (change for production):
- Icecast: admin/hackme
- Liquidsoap telnet: admin
- MQTT: no authentication

## Usefull commands

- **WSL IP:** `ip addr show eth0`
- **Service Logs:** `journalctl -u service-name -f`
- **MQTT Traffic:** `mosquitto_sub -h server -t '#'`
- **sculpture_sink:** `ssh pi@<RASPBERRY_PI_IP> "pacat -r -d sculpture_sink.monitor" | pacat -p`
- **CPU:** `htop`
- **CPU Snapshot:** `top -b -n 1 | head -n 20`
- **Sinks:** `pactl list sinks`
- **Sink Inputs:** `pactl list sink-inputs`
- **Liquidsoap Script:** `liquidsoap --check /etc/liquidsoap/main.liq`
- **Icecast2:** `curl http://server:8000/status.xsl`
- **Test Tone:** `timeout 3s speaker-test -c 1 -t sine`
- **Telnet:** `telnet localhost 1234` # Password: admin
- **Alsamixer:** `alsamixer`
- **flow.json:** `jq . /opt/sculpture-system/flow.json`
- **Inspecting the copied samples audio settings:**
```
ffprobe -v error -show_entries \
        stream=sample_rate,channels,sample_fmt \
        -of default=noprint_wrappers=1:nokey=1 \
        /opt/sculpture-system/*.wav
```
- **Reseting SSH keys after Pi IP/SD_card change:**
```
ssh-keygen -f "/home/unix_user/.ssh/known_hosts" -R "192.168.8.154"
ssh-keygen -f "/home/unix_user/.ssh/known_hosts" -R "192.168.8.157" 
ssh-keygen -f "/home/unix_user/.ssh/known_hosts" -R "192.168.8.158"
```

## Dev Container
The `.devcontainer` folder provides a ready-to-use VS Code development
container. It mirrors the control node and Pi simulator packages so Node.js
20, Liquidsoap, Mosquitto, Node‑RED and the required Python packages are
available out of the box. Open the project with the **Remote – Containers**
extension to develop without installing dependencies locally.

## 🔮 Future Development Ideas

*Ideas for potential improvements if development continues:*

### 🔧 **System Improvements**
- **Enhanced Ansible Modularity**: Break down playbooks into focused, reusable modules for faster development cycles
- **Automated Recovery**: Implement self-healing mechanisms for common failure scenarios
- **Dynamic Sample Rate Management**: Create dedicated playbooks for quick audio configuration updates
- **Comprehensive System Restart Sequencing**: Ordered service restart logic for complete system recovery

### 🎵 **Audio Features**  
- **Advanced Plan Switching**: Enable live-to-local mode transitions per sculpture
- **Enhanced Audio Processing**: Improve audible effects of processing parameters with better monitoring
- **Stereo-to-Mono Optimization**: Refinements to dual-head microphone processing

### 🚀 **Performance & Monitoring**
- **Production Underrun Monitoring**: Enhanced buffer management and dropout prevention
- **Extended Audio Processing Documentation**: Better characterization of effect parameters
- **Server-Agent Connectivity Improvements**: More robust edge device communication

### 🏗️ **Architecture** 
- **Service Modularity**: Further decomposition of components for easier maintenance
- **Cross-Platform Audio Backend**: Enhanced PulseAudio/ALSA abstraction layer

## 📊 Project Status

This system was successfully deployed and operated during the **YAGA 2025 festival**. The codebase is now in a clean, documented state suitable for archival and potential future development.

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE.md) for details.

## 🙏 Acknowledgments

Developed for the YAGA 2025 festival interactive sculpture installation.
