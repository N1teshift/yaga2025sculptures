# Docker-Based Sculpture System Testing

This guide helps you test the sculpture system using Docker containers that simulate the Raspberry Pi sculptures.

## Overview

The Docker setup creates:
- **3 simulated Raspberry Pi containers** (sculpture1, sculpture2, sculpture3)
- **Audio generators** that create different test tones for each sculpture
- **Virtual networking** that mimics the real sculpture network
- **All the same services** as real Pis (DarkIce, pi-agent, MPV, etc.)

## Prerequisites

- Docker Desktop installed and running
- WSL 2 with Ubuntu 22.04 (for control server)
- At least 4GB RAM available for containers

## Quick Start

### 1. Start the Control Server (WSL 2)

First, set up the control server in WSL:

```bash
# In WSL Ubuntu terminal
cd /mnt/c/Users/user/source/repos/yaga2025sculptures

# Install control server services
ansible-playbook server/ansible/install_control_node.yml

# Start services
sudo systemctl start icecast2
sudo systemctl start mosquitto  
sudo systemctl start liquidsoap
sudo systemctl start node-red
```

### 2. Build and Start Docker Containers

```bash
# In Windows PowerShell or WSL
cd C:\Users\user\source\repos\yaga2025sculptures\docker

# Build and start all containers
docker-compose up --build -d

# Check container status
docker-compose ps
```

### 3. Verify System Operation

**Check containers are running:**
```bash
docker ps
```

**Check audio streams:**
- Open browser to `http://localhost:8000` (Icecast status)
- You should see streams: `s1-mic.ogg`, `s2-mic.ogg`, `s3-mic.ogg`

**Check control dashboard:**
- Open browser to `http://localhost:1880/ui`
- You should see volume sliders and status gauges

## Container Details

### Sculpture Containers
- **sculpture1**: IP 172.20.0.101, SSH port 2201, generates 440Hz sine waves
- **sculpture2**: IP 172.20.0.102, SSH port 2202, generates 880Hz square waves  
- **sculpture3**: IP 172.20.0.103, SSH port 2203, generates 1320Hz sawtooth waves

### Audio Simulation
Each container generates unique audio patterns:
- **Sculpture 1**: 440Hz sine wave (musical note A4)
- **Sculpture 2**: 880Hz square wave (musical note A5)
- **Sculpture 3**: 1320Hz sawtooth wave (musical note E6)

## Testing Scenarios

### 1. Basic Audio Flow Test

```bash
# Check if audio is being generated
docker exec sculpture1 ps aux | grep ffmpeg

# Check if DarkIce is streaming
docker exec sculpture1 ps aux | grep darkice

# Check audio streams in browser
# http://localhost:8000/s1-mic.ogg
# http://localhost:8000/s2-mic.ogg  
# http://localhost:8000/s3-mic.ogg
```

### 2. MQTT Communication Test

```bash
# In WSL, test MQTT
mosquitto_pub -h localhost -t sculpture/1/cmd -m '{"volume":0.5}'
mosquitto_sub -h localhost -t sculpture/+/status

# Check pi-agent logs
docker exec sculpture1 journalctl -u pi-agent -f
```

### 3. Volume Control Test

1. Open dashboard: `http://localhost:1880/ui`
2. Move volume sliders for each sculpture
3. Check container logs for volume changes:
   ```bash
   docker logs sculpture1 -f
   ```

### 4. Mode Switching Test

1. In dashboard, toggle between Live/Local mode
2. Verify services start/stop in containers:
   ```bash
   docker exec sculpture1 systemctl status darkice
   docker exec sculpture1 systemctl status player-live
   ```

## Debugging

### Container Access
```bash
# SSH into containers (password: raspberry)
ssh -p 2201 pi@localhost  # sculpture1
ssh -p 2202 pi@localhost  # sculpture2
ssh -p 2203 pi@localhost  # sculpture3

# Or use docker exec
docker exec -it sculpture1 bash
```

### Service Status
```bash
# Check services in container
docker exec sculpture1 systemctl status darkice
docker exec sculpture1 systemctl status pi-agent
docker exec sculpture1 systemctl status player-live

# View logs
docker exec sculpture1 journalctl -u darkice -f
docker exec sculpture1 journalctl -u pi-agent -f
```

### Audio Debugging
```bash
# Check PulseAudio in container
docker exec sculpture1 pulseaudio --check
docker exec sculpture1 pactl list sinks
docker exec sculpture1 pactl list sources

# Test audio generation
docker exec sculpture1 speaker-test -c 1 -t sine
```

### Network Debugging
```bash
# Test connectivity from container to host
docker exec sculpture1 ping host.docker.internal
docker exec sculpture1 telnet host.docker.internal 8000
docker exec sculpture1 telnet host.docker.internal 1883

# Check container networking
docker network inspect docker_sculpture_net
```

## Customization

### Modify Audio Patterns
Edit `docker/pi-simulator/audio-simulator.sh` to change:
- Frequencies
- Waveform types (sine, square, sawtooth, triangle)
- Audio duration and patterns

### Add More Sculptures
1. Add new service in `docker-compose.yml`
2. Create corresponding audio generator
3. Update Ansible inventory

### Change Network Configuration
Modify `docker-compose.yml` networks section to use different IP ranges.

## Cleanup

```bash
# Stop all containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Troubleshooting

### Common Issues

1. **Containers won't start**
   - Check Docker Desktop is running
   - Verify WSL 2 integration is enabled
   - Check available disk space and memory

2. **No audio streams**
   - Check if control server services are running in WSL
   - Verify Icecast is accessible at `http://localhost:8000`
   - Check container logs for audio generation errors

3. **MQTT not working**
   - Verify Mosquitto is running in WSL: `sudo systemctl status mosquitto`
   - Check firewall settings
   - Test MQTT from WSL: `mosquitto_sub -h localhost -t '#'`

4. **Dashboard not accessible**
   - Check Node-RED is running: `sudo systemctl status node-red`
   - Verify port 1880 is not blocked
   - Try accessing from WSL: `curl http://localhost:1880/ui`

### Performance Tips

- **Allocate more memory** to Docker Desktop (4GB minimum)
- **Use WSL 2 backend** for better performance
- **Keep containers running** instead of frequent restarts
- **Monitor resource usage** with `docker stats`

## Real vs Simulated Differences

| Aspect | Real Raspberry Pi | Docker Simulator |
|--------|------------------|------------------|
| Audio Input | USB microphone | Generated test tones |
| Audio Output | Physical speakers | Virtual PulseAudio sinks |
| Network | WiFi/Ethernet | Docker bridge network |
| Hardware | ARM processor | x86 emulation |
| Performance | Limited resources | Host system resources |
| Persistence | SD card storage | Container volumes |

## Next Steps

Once you've tested with Docker:

1. **Verify all features work** in the simulated environment
2. **Customize audio processing** in Liquidsoap
3. **Test failure scenarios** (network disconnection, service crashes)
4. **Deploy to real Raspberry Pis** using the same configurations
5. **Compare behavior** between simulated and real environments

The Docker simulation provides an excellent testing ground before deploying to actual hardware! 