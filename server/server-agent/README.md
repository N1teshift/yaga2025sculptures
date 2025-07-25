# Enhanced Server Agent with Underrun Monitoring

This enhanced server-agent provides centralized monitoring of audio underruns across all Pi systems in your sculpture installation.

## Features

### Original Features
- MQTT-based command handling
- Plan management and synchronization with Liquidsoap
- Local log tailing for server services
- Status publishing

### New Features
- **Real-time underrun monitoring** across all Pi systems
- **SSH-based remote log monitoring** for player-live and player-loop services
- **Centralized underrun statistics** with counts and timestamps
- **MQTT publishing** of underrun events and summaries
- **Clean console logging** with underrun counts and summaries
- **Darkice buffer overrun monitoring** with automatic restart capability
- **Robust service restart** with multiple strategies for stuck services
- **Buffer overrun spam detection** to prevent log flooding issues

### Enhanced Connection Handling (NEW)
- **Multiple connection methods** per sculpture (.local, hostname, IP address)
- **Automatic fallback** between connection methods when one fails
- **Connection state tracking** and automatic reconnection
- **Enhanced underrun detection** with multiple regex patterns for MPV
- **Diagnostic tools** for testing connections before deployment
- **Improved logging** with connection status and underrun rates

## Installation

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Set up SSH key authentication** (recommended):
   ```bash
   ssh-keygen -t ed25519 -C "server-agent"
   ssh-copy-id pi@sculpture1.local
   ssh-copy-id pi@sculpture2.local
   ssh-copy-id pi@sculpture3.local
   ```

3. **Configure your systems** (IMPORTANT - Updated Configuration):
   ```bash
   cp config.py.example config.py
   # Edit config.py to match your setup - NOW INCLUDES MULTIPLE CONNECTION METHODS
   ```

4. **Test connections before running** (NEW):
   ```bash
   python3 test_connections.py
   ```

5. **Run the installation script:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

## Architecture

The server-agent uses a modular architecture for better maintainability:

### Module Structure
```
server-agent/
├── server_agent.py          # Main application (~200 lines)
├── config.py                # Configuration and constants
├── underrun_monitor.py      # UnderrunMonitor class
├── darkice_monitor.py       # DarkiceMonitor class  
├── liquidsoap_client.py     # LiquidSoapClient class
├── plan_manager.py          # Plan state management
├── mqtt_handlers.py         # MQTT callbacks and handlers
├── test_connections.py      # Connection diagnostic tool
├── config.py.example        # Configuration template
└── server-agent.service     # Updated systemd service
```

### Benefits of Modular Architecture
- **Better maintainability**: Each module has a single responsibility
- **Easier testing**: Individual components can be tested separately
- **Cleaner imports**: Clear separation of concerns
- **Better organization**: Related functionality grouped together

## Usage

### Clean Log Viewing
To view server-agent logs without timestamps and machine names:
```bash
journalctl -u server-agent -f -o cat
```

### Underrun Monitoring Output
The enhanced server-agent will show:
- Individual underrun detections: `UNDERRUN detected - sculpture1/player-live: Audio device underrun detected.`
- Periodic summaries: `Underrun summary - Total: 45, Recent (1h): 12`

### Darkice Buffer Overrun Monitoring
The server-agent now monitors darkice services for buffer overrun issues and automatically handles restarts:

**Buffer Overrun Detection:**
- Monitors darkice logs for "buffer overrun" messages
- Tracks consecutive overruns and spam detection
- Logs: `BUFFER OVERRUN detected - sculpture1/darkice: consecutive=3, recent=8`
- Spam alert: `BUFFER OVERRUN SPAM detected on sculpture1/darkice - 12 overruns in 30s`

**Automatic Restart Handling:**
- Triggers restart after 5 consecutive buffer overruns OR spam detection
- Uses multiple restart strategies when systemctl commands fail:
  1. Normal `systemctl restart` (3 attempts)
  2. `systemctl stop` followed by `systemctl start`
  3. Force kill processes (`pkill -9 darkice`) then start
- Implements restart cooldown (60s) and max attempts (5) per service
- Publishes restart success/failure events via MQTT

**Summary Output:**
- `Darkice summary - Buffer overruns: 23, Restart attempts: 2, Spam detected: true`

### MQTT Topics

**Underrun Events:**
- Topic: `system/underruns`
- Payload: `{"system": "sculpture1", "service": "player-live", "timestamp": "2025-01-07T00:28:27", "log_line": "Audio device underrun detected.", "total_count": 15}`

**Underrun Summary:**
- Topic: `system/underruns/summary`
- Payload: `{"timestamp": 1704586107, "systems": {"sculpture1": {"player-live": {"total_count": 15, "recent_count_1h": 3, "last_underrun": "2025-01-07T00:28:27"}}}, "source": "server-agent"}`

**Darkice Buffer Overrun Events:**
- Topic: `system/darkice/overrun`
- Payload: `{"system": "sculpture1", "service": "darkice", "timestamp": "2025-01-07T00:28:27", "log_line": "buffer overrun", "total_count": 8, "consecutive_overruns": 3, "spam_detected": false, "restart_attempts": 0}`

**Darkice Restart Events:**
- Topic: `system/darkice/restart`
- Payload: `{"system": "sculpture1", "service": "darkice", "timestamp": "2025-01-07T00:30:15", "status": "success", "message": "Darkice service restarted successfully"}`

**Darkice Summary:**
- Topic: `system/darkice/summary`
- Payload: `{"timestamp": 1704586107, "systems": {"sculpture1": {"darkice": {"total_buffer_overruns": 8, "recent_overruns_1h": 5, "consecutive_overruns": 0, "restart_attempts": 1, "spam_detected": false, "last_buffer_overrun": "2025-01-07T00:28:27", "last_restart_attempt": "2025-01-07T00:30:15"}}}, "source": "server-agent"}`

### Commands

**Request underrun summary:**
```bash
mosquitto_pub -h localhost -t server/cmd -m '{"underrun_summary": true}'
```

**Request darkice summary:**
```bash
mosquitto_pub -h localhost -t server/cmd -m '{"darkice_summary": true}'
```

**Manual darkice restart:**
```bash
mosquitto_pub -h localhost -t server/cmd -m '{"darkice_restart": true, "system": "sculpture1", "service": "darkice"}'
```

## Configuration

### Pi Systems (UPDATED)
Edit the `PI_SYSTEMS` list in `server-agent.py` or create a `config.py` file. 

**New multi-host configuration:**
```python
PI_SYSTEMS = [
    {
        "name": "sculpture1", 
        "hosts": [
            "sculpture1.local",     # Try mDNS first
            "sculpture1",           # Then hostname
            "192.168.1.101"        # Finally IP address
        ],
        "user": "pi"
    },
    {
        "name": "sculpture2", 
        "hosts": [
            "sculpture2.local",
            "sculpture2",
            "192.168.1.102"        # Update with actual IP
        ],
        "user": "pi"
    },
    {
        "name": "sculpture3", 
        "hosts": [
            "sculpture3.local",
            "sculpture3",
            "192.168.1.103"        # Update with actual IP
        ],
        "user": "pi"
    },
]
```

**Important**: Update the IP addresses to match your actual sculpture IPs!

### Services to Monitor
By default, monitors `player-live` and `player-loop` for underruns. Modify `MONITORED_SERVICES` to change this.

By default, monitors `darkice` service for buffer overruns. Modify `DARKICE_SERVICES` to change this.

### Darkice Configuration
The darkice monitoring can be tuned via `DARKICE_CONFIG`:
```python
DARKICE_CONFIG = {
    'max_restart_attempts': 5,      # Maximum restart attempts per service
    'restart_cooldown': 60,         # Seconds between restart attempts
    'buffer_overrun_threshold': 5,  # Trigger restart after this many consecutive overruns
    'overrun_spam_threshold': 10,   # Consider it spam if more than this many in 30 seconds
    'overrun_spam_window': 30,      # Seconds for spam detection window
    'force_kill_timeout': 10        # Seconds to wait before force killing
}
```

## Troubleshooting

### SSH Connection Issues (UPDATED)

**First, use the diagnostic tool:**
```bash
python3 test_connections.py
```

This will test all connection methods and show exactly what's failing.

**Common issues and solutions:**

1. **"Name or service not known" errors:**
   - Update IP addresses in `config.py`
   - Test resolution: `ping sculpture1.local`
   - Use IP addresses instead of hostnames

2. **SSH connection refused:**
   - Check SSH service: `ssh pi@sculpture1.local`
   - Verify SSH key authentication
   - Check firewall settings

3. **All connection methods failing:**
   - Verify network connectivity
   - Check that Pi systems are powered on
   - Use `nmap` to scan for devices: `nmap -sn 192.168.1.0/24`

4. **Service monitoring not working:**
   - Check service status: `ssh pi@sculpture1.local systemctl status player-live`
   - Verify service names match configuration
   - Test log access: `ssh pi@sculpture1.local journalctl -u player-live -n 5`

**Connection State Monitoring:**
The enhanced agent now shows connection status in logs:
```
[UNDERRUN] Connection status: 2/3 systems connected
[UNDERRUN] sculpture1: Connected via 192.168.1.101 (1 connections)
[UNDERRUN] sculpture2: Connected via sculpture2.local (1 connections)
[UNDERRUN] sculpture3: Disconnected (last attempt: 2025-01-07 17:30:15)
```

### Missing Underrun Detection
- Check that the services are running on Pi systems
- Verify service names match exactly
- Test manually: `ssh pi@sculpture1.local journalctl -u player-live -f`

### No MQTT Messages
- Check MQTT broker connectivity
- Verify MQTT_BROKER setting
- Check firewall settings

### Darkice Buffer Overrun Issues
- **Frequent buffer overruns:** Often caused when not all edge devices are connected during ansible deployment
- **Restart attempts failing:** The agent will try multiple strategies (restart, stop/start, force kill)
- **Max restart attempts reached:** Check underlying hardware/network issues
- **Spam detection:** Indicates severe buffer overrun problem, automatic restart will be triggered

### Darkice Service Won't Restart
- Check SSH connectivity to Pi systems
- Verify darkice service exists: `ssh pi@sculpture1.local systemctl status darkice`
- Check for conflicting processes: `ssh pi@sculpture1.local ps aux | grep darkice`
- Manual intervention may be needed if all restart strategies fail

## Understanding Underruns

**What are underruns?**
Audio underruns occur when the audio buffer empties before new data arrives, causing dropouts or interruptions.

**Common causes:**
- Network connectivity issues
- CPU/memory overload
- Storage I/O problems
- Audio hardware issues

**The `[48.0K blob data]` messages:**
These indicate MPV is processing audio data (48KB in this case). This is normal output showing data buffer sizes.

## Monitoring Strategy

The enhanced server-agent provides:
1. **Real-time alerts** for each underrun as it happens
2. **Historical tracking** of underrun patterns
3. **Periodic summaries** every 30 seconds
4. **MQTT integration** for dashboard displays
5. **Centralized logging** instead of multiple terminal windows

This eliminates the need to monitor multiple terminal windows and provides a unified view of audio system health across all sculptures. 