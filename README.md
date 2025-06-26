# Sculpture Audio System

A distributed audio system for interactive sculpture installations using Raspberry Pi devices and a central control server.

## Overview

This system creates a network of three sculptures, each equipped with a Raspberry Pi, microphone, and speaker. Each sculpture captures audio from its environment and streams it to a central server, which creates personalized audio mixes for each sculpture.

## Architecture

- **Edge Devices (3x Raspberry Pi):** Audio capture, streaming, and playback
- **Control Server (1x Windows + WSL 2 or Linux PC):** Audio mixing, MQTT broker, web dashboard
- **Communication:** MQTT for control, Icecast for audio streaming

## Features

- **Live Audio Streaming:** Real-time audio capture and streaming using DarkIce
- **Personalized Mixing:** Each sculpture receives a unique mix via Liquidsoap
- **Remote Control:** Web-based dashboard for volume control and mode switching
- **System Monitoring:** Real-time CPU and temperature monitoring
- **Automated Deployment:** Ansible playbooks for easy setup
- **Fallback Mode:** Local audio playback when network is unavailable
- **Cross-Platform:** Supports Windows + WSL 2 and native Linux

## Quick Start

1. **Clone Repository:**
   ```bash
   git clone https://github.com/N1teshift/yaga2025sculptures.git
   cd yaga2025sculptures
   ```

2. **Install Server Dependencies:**
   Run the setup script to install Icecast2, Liquidsoap, Mosquitto, Node.js and other requirements.
   ```bash
   sudo ./setup.sh
   ```

3. **Follow Setup Guide:**
   See [docs/quickstart.md](docs/quickstart.md) for detailed deployment instructions.

## Repository Structure

```
sculpture-system/
├── edge/                    # Raspberry Pi configuration
│   ├── ansible/            #   - Deployment automation
│   ├── darkice/            #   - Audio streaming config
│   ├── scripts/            #   - Pi agent and utilities
│   └── systemd/            #   - Service definitions
├── server/                 # Control server setup
│   ├── ansible/           #   - Server deployment & Node-RED flows
│   ├── liquidsoap/        #   - Audio mixing engine
│   └── templates/         #   - Other configuration templates (e.g., Icecast)
└── docs/                  # Documentation
    └── quickstart.md      #   - Deployment guide
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

## Platform-Specific Notes

### Windows + WSL 2
- All services run inside WSL 2 Ubuntu environment
- Access dashboard from Windows browser using WSL IP
- File system performance is best when keeping files in WSL
- Network: WSL 2 uses NAT, so use WSL IP for inter-device communication

### Native Linux
- Services run directly on the host system
- Standard Linux networking applies
- Use host IP address for inter-device communication

## Monitoring

- **Service Logs:** `journalctl -u service-name -f`
- **MQTT Traffic:** `mosquitto_sub -h server -t '#'`
- **sculpture_sink:** `ssh pi@<RASPBERRY_PI_IP> "pacat -r -d sculpture_sink.monitor" | pacat -p`
- **CPU:** `htop`

## Troubleshooting

### Debug Commands

```bash
# Test audio capture
arecord -D hw:1,0 -f cd test.wav

# Check Liquidsoap
liquidsoap --check /etc/liquidsoap/main.liq

# Monitor network streams
curl http://server:8000/status.xsl

# WSL 2: Check IP address
ip addr show eth0
```

## Development

### Testing
- Use test tones: `speaker-test -c 1 -t sine`

### Dev Container
The `.devcontainer` folder provides a ready-to-use VS Code development
container. It mirrors the control node and Pi simulator packages so Node.js
20, Liquidsoap, Mosquitto, Node‑RED and the required Python packages are
available out of the box. Open the project with the **Remote – Containers**
extension to develop without installing dependencies locally.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE.md) for details.
