# Sculpture Audio System

A distributed audio system for interactive sculpture installations using Raspberry Pi devices and a central control server.

## Overview

This system creates a network of three sculptures, each equipped with a Raspberry Pi, microphone, and speaker. Each sculpture captures audio from its environment and streams it to a central server, which creates personalized audio mixes for each sculpture. Each sculpture hears the audio from the other two sculptures, but not its own.

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

2. **Follow Setup Guide:**
   See [docs/quickstart.md](docs/quickstart.md) for detailed deployment instructions.

## Repository Structure

```
sculpture-system/
├── edge/                    # Raspberry Pi configuration
│   ├── ansible/            # Deployment automation
│   ├── darkice/            # Audio streaming config
│   ├── scripts/            # Pi agent and utilities
│   └── systemd/            # Service definitions
├── server/                 # Control server setup
│   ├── ansible/           # Server deployment
│   ├── liquidsoap/        # Audio mixing engine
│   ├── nodered/           # Web dashboard
│   └── templates/         # Configuration templates
└── docs/                  # Documentation
    └── quickstart.md      # Deployment guide
```

## System Components

### Edge Devices (Raspberry Pi)
- **DarkIce:** Streams microphone audio to Icecast server
- **MPV:** Plays audio streams from control server
- **Pi-Agent:** MQTT client for remote control and monitoring
- **PulseAudio:** Audio routing and volume control

### Control Server (Windows + WSL 2 or Linux)
- **Icecast2:** Audio streaming server
- **Liquidsoap:** Real-time audio mixing and processing
- **Mosquitto:** MQTT broker for device communication
- **Node-RED:** Web dashboard for system control

## Audio Flow

1. **Capture:** Each Pi captures audio via USB microphone
2. **Stream:** DarkIce streams audio to Icecast server
3. **Mix:** Liquidsoap creates personalized mixes (sculpture 1 hears 2+3, etc.)
4. **Distribute:** Mixed audio streams back to respective sculptures
5. **Play:** MPV plays the personalized mix through speakers

## Control Interface

Access the web dashboard at `http://CONTROL_SERVER_IP:1880/ui` to:
- Adjust volume for each sculpture
- Switch between live and local playback modes
- Monitor system status (CPU, temperature)
- Emergency stop functionality

**Note:** If using WSL 2, use your WSL IP address, not your Windows IP.

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
- 3x Raspberry Pi 4 (4GB recommended)
- 3x USB audio interfaces
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

**WSL 2 Users:** Use your WSL IP address (found with `ip addr show eth0`) as the control_host, not your Windows IP.

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

- **System Status:** Node-RED dashboard shows CPU and temperature
- **Audio Levels:** Icecast web interface at port 8000
- **Service Logs:** `journalctl -u service-name -f`
- **MQTT Traffic:** `mosquitto_sub -h server -t '#'`

## Troubleshooting

### Common Issues

1. **No Audio Capture:**
   - Check USB audio device connection
   - Verify ALSA device configuration
   - Test with `arecord -l` and `aplay -l`

2. **Network Connectivity:**
   - Verify IP addresses in configuration
   - **WSL 2:** Ensure using WSL IP, not Windows IP
   - Test MQTT with `mosquitto_pub/sub`
   - Check firewall settings

3. **Service Failures:**
   - Check service status: `systemctl status service-name`
   - View logs: `journalctl -u service-name -f`
   - Restart services: `systemctl restart service-name`

### Debug Commands

```bash
# Test audio capture
arecord -D hw:1,0 -f cd test.wav

# Test MQTT
mosquitto_pub -h server -t test -m "hello"

# Check Liquidsoap
liquidsoap --check /etc/liquidsoap/main.liq

# Monitor network streams
curl http://server:8000/status.xsl

# WSL 2: Check IP address
ip addr show eth0
```

## Development

### Adding Features
1. Modify Liquidsoap scripts for audio processing
2. Update Node-RED flows for dashboard changes
3. Extend pi-agent for new MQTT commands
4. Update Ansible playbooks for deployment

### Testing
- Use test tones: `speaker-test -c 1 -t sine`
- Monitor MQTT: `mosquitto_sub -h server -t '#'`
- Check audio streams in browser or VLC

## License

This project is open source. See individual component licenses for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Test individual components
4. Create GitHub issue with logs and configuration

## Contributing

1. Fork the repository
2. Create feature branch
3. Test changes thoroughly
4. Submit pull request with description

---

**Note:** This system is designed for art installations and may require customization for specific environments and requirements. 