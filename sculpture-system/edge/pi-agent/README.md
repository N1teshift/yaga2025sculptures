# Pi-Agent System

The Pi-Agent is the core software system running on each Raspberry Pi sculpture device. It manages audio capture, playback, MQTT communication, and system monitoring.

## Architecture Overview

The Pi-Agent consists of several modular components that work together to provide a complete sculpture management system:

```
pi-agent.py (Main orchestrator)
├── audio_manager.py      # Audio capture and playback control
├── system_manager.py     # System information and service management  
├── status_collector.py   # Hardware monitoring and status reporting
├── playlist_manager.py   # Audio track and playlist management
├── mqtt_client.py        # MQTT communication wrapper
├── service_manager.py    # Systemd service control utilities
├── gpio_utils.py         # GPIO LED and button control
└── file_utils.py         # File system utilities
```

## Core Components

### `pi-agent.py` (Main Controller)
- **Purpose**: Main orchestrator that coordinates all other components
- **Key Features**:
  - MQTT message handling and routing
  - Component initialization and lifecycle management
  - GPIO setup for LEDs and buttons
  - Command processing and response coordination
- **Dependencies**: All other modules

### `audio_manager.py` (Audio System)
- **Purpose**: Manages all audio capture and playback operations
- **Key Features**:
  - Live audio streaming control (player-live service)
  - Local audio playback (player-loop service) 
  - Volume and capture level control
  - Audio mode switching (live/local)
  - Audio device configuration
- **Audio Backends**: Supports both ALSA and PulseAudio
- **Dependencies**: MPV player, DarkIce, system audio services

### `system_manager.py` (System Control)
- **Purpose**: Provides system information and service management
- **Key Features**:
  - System status monitoring (CPU, temperature, memory)
  - Service restart capabilities
  - System shutdown and reboot control
  - Predefined playlist configuration management
- **Dependencies**: systemd, system monitoring tools

### `status_collector.py` (Hardware Monitoring)
- **Purpose**: Collects real-time hardware and audio metrics
- **Key Features**:
  - CPU usage monitoring
  - Temperature monitoring  
  - Audio level monitoring (microphone input, output levels)
  - Service status checking
  - Formatted status reporting for MQTT
- **Dependencies**: System monitoring utilities, audio level detection tools

### `playlist_manager.py` (Media Management)
- **Purpose**: Manages audio tracks and playlists
- **Key Features**:
  - Dynamic track discovery from samples directory
  - Playlist loading and management
  - Track metadata handling
  - Audio file validation
- **Dependencies**: File system access to samples directory

### `mqtt_client.py` (Communication)
- **Purpose**: Lightweight wrapper around MQTT client
- **Key Features**:
  - Connection management with auto-reconnect
  - Topic subscription handling
  - Last Will and Testament (LWT) support
  - Message publishing utilities
- **Dependencies**: paho-mqtt library

### `service_manager.py` (Service Control)
- **Purpose**: Utilities for controlling systemd services
- **Key Features**:
  - Service start/stop/restart operations
  - Service status checking
  - Graceful service management
- **Dependencies**: systemctl, systemd

### `gpio_utils.py` (Hardware Interface)
- **Purpose**: GPIO control for LEDs and buttons
- **Key Features**:
  - LED control (green/red status indicators)
  - Button handling (shutdown button)
  - Blinking LED patterns
  - GPIO cleanup and initialization
- **Dependencies**: RPi.GPIO library

### `file_utils.py` (File Operations)
- **Purpose**: Common file system operations
- **Key Features**:
  - Safe file reading/writing
  - Directory validation
  - File existence checking
- **Dependencies**: Standard Python file operations

## Configuration Files

### `asound.conf.j2`
- **Purpose**: ALSA audio configuration template
- **Features**: Defines audio device routing and tee output for simultaneous capture/playback

### `pi-agent-sudoers.j2`
- **Purpose**: Sudoers configuration for limited privilege escalation
- **Features**: Allows pi-agent to restart services without full root access

## Service Integration

The Pi-Agent works with several systemd services:

- **`pi-agent.service`**: The main agent process
- **`darkice.service`**: Audio streaming to server
- **`player-live.service`**: Live audio playback from server
- **`player-loop.service`**: Local audio file playback

## MQTT Communication

### Topics Used
- **Command**: `sculpture/{id}/cmd` - Receives commands from server
- **Status**: `sculpture/{id}/status` - Publishes regular status updates
- **Tracks**: `sculpture/{id}/tracks` - Publishes available track list
- **Broadcast**: `system/broadcast` - Receives system-wide commands

### Command Format
Commands are JSON objects with various supported operations:
```json
{"volume": 0.7}                           // Set volume level
{"capture": 0.5}                          // Set capture level  
{"mode": "live"}                          // Switch to live mode
{"mode": "local", "track": "file.wav"}    // Switch to local playback
{"mute": true}                            // Mute/unmute
{"restart": "darkice"}                    // Restart specific service
```

## Installation and Deployment

The Pi-Agent system is deployed via Ansible automation. All `.j2` files are Jinja2 templates that are processed during deployment to insert configuration values specific to each sculpture.

## Hardware Requirements

- Raspberry Pi with GPIO support
- Audio HAT (IQaudIO codec supported)
- Microphone input
- Speaker/amplifier output
- LED indicators (green/red)
- Shutdown button

## Dependencies

- Python 3 with RPi.GPIO, paho-mqtt
- MPV media player
- DarkIce audio streamer
- ALSA or PulseAudio
- systemd for service management