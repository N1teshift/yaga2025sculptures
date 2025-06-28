#!/usr/bin/env python3

import json
import time
import subprocess
import os
import sys
import logging
from pathlib import Path
import paho.mqtt.client as mqtt
import random
import pwd
import re
import configparser

# Configuration
MQTT_BROKER = os.environ.get('CONTROL_HOST', '192.168.8.156')
MQTT_PORT = 1883
SCULPTURE_ID = os.environ.get('SCULPTURE_ID', '1')
SCULPTURE_DIR = '/opt/sculpture-system'
AUDIO_CONFIG_PATH = '/etc/sculpture/audio.conf'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_audio_config():
    """Reads audio settings from the config file."""
    config = configparser.ConfigParser()
    # Provide default values consistent with the new centralized settings
    config['audio'] = {
        'samplerate': '22050',
        'device': 'pulse/sculpture_sink'
    }
    
    try:
        if Path(AUDIO_CONFIG_PATH).exists():
            config.read(AUDIO_CONFIG_PATH)
            logger.info(f"Loaded audio configuration from {AUDIO_CONFIG_PATH}")
        else:
            logger.warning(f"Audio configuration file not found at {AUDIO_CONFIG_PATH}. Using default values.")
    except Exception as e:
        logger.error(f"Error reading audio config: {e}. Using default values.")
        
    return config['audio']

def get_pactl_env():
    """Returns a suitable environment for running pactl from a systemd service."""
    try:
        # Get the UID of the 'pi' user, which is needed to find the PulseAudio socket
        pi_uid = pwd.getpwnam('pi').pw_uid
        env = os.environ.copy()
        env['XDG_RUNTIME_DIR'] = f'/run/user/{pi_uid}'
        return env
    except KeyError:
        logger.warning("Could not find user 'pi' to set XDG_RUNTIME_DIR for pactl. Audio control will likely fail.")
        return os.environ.copy()
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating pactl environment: {e}")
        return os.environ.copy()

class SculptureAgent:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sculpture_id = SCULPTURE_ID
        self.status_topic = f"sculpture/{self.sculpture_id}/status"
        self.cmd_topic = f"sculpture/{self.sculpture_id}/cmd"
        self.tracks_topic = f"sculpture/{self.sculpture_id}/tracks"
        self.broadcast_topic = "system/broadcast"
        self.is_muted = False      # Track mute state
        self.current_mode = "live"  # Track current mode (live/local)
        self._last_mute_error = None
        self.audio_config = get_audio_config()
        
    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(self.cmd_topic)
        client.subscribe(self.broadcast_topic)
        logger.info(f"Subscribed to {self.cmd_topic} and {self.broadcast_topic}")
        # Default to live mode on connect for the simulator
        self.handle_mode_command("live")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")
            
            if not isinstance(payload, dict):
                logger.warning(f"Received message is not a JSON object, ignoring. Payload: {payload}")
                return

            if 'mode' in payload:
                self.handle_mode_command(payload['mode'], payload.get('track'))
            elif 'volume' in payload:
                self.handle_volume_command(payload['volume'])
            elif 'mute' in payload:
                self.handle_mute_command(payload['mute'])
            elif 'restart' in payload and payload['restart']:
                self.handle_restart_command()
            elif 'command' in payload and payload['command'] == 'get_tracks':
                self.handle_get_tracks()
            elif 'command' in payload and payload['command'] == 'stop':
                self.handle_stop_command()
            else:
                logger.warning(f"Unknown command: {payload}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message: {msg.payload.decode()}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    def handle_get_tracks(self):
        """List audio tracks and publish them to the tracks topic."""
        try:
            loops_dir = Path(SCULPTURE_DIR) / 'loops'
            if not loops_dir.is_dir():
                logger.warning(f"Loops directory not found: {loops_dir}")
                tracks = []
            else:
                tracks = sorted([f.name for f in loops_dir.iterdir() if f.is_file() and f.suffix in ['.wav', '.mp3', '.flac']])
            
            logger.info(f"Found tracks: {tracks}")
            self.client.publish(self.tracks_topic, json.dumps(tracks), retain=True)
            
        except Exception as e:
            logger.error(f"Error getting tracks: {e}")
            
    def handle_mode_command(self, mode, track=None):
        """Handle mode switching between live and local playback"""
        try:
            if mode == "live":
                logger.info("Switching to live mode")
                self.current_mode = "live"
                # Stop local playback
                subprocess.run(['sudo', 'systemctl', 'stop', 'player-loop.service'], check=False)
                # Start live streaming and playback
                subprocess.run(['sudo', 'systemctl', 'start', 'darkice.service'], check=True)
                subprocess.run(['sudo', 'systemctl', 'start', 'player-live.service'], check=True)
                
            elif mode == "local":
                logger.info(f"Switching to local mode with track: {track}")
                self.current_mode = "local"
                # Stop live services
                subprocess.run(['sudo', 'systemctl', 'stop', 'darkice.service'], check=False)
                subprocess.run(['sudo', 'systemctl', 'stop', 'player-live.service'], check=False)
                
                # Update track if specified
                if track:
                    track_path = Path(SCULPTURE_DIR) / 'loops' / track
                    if track_path.exists():
                        # Update the service to use the new track
                        self.update_loop_track(str(track_path))
                    else:
                        logger.warning(f"Track not found: {track_path}")
                        
                # Restart local playback to apply the new track
                subprocess.run(['sudo', 'systemctl', 'restart', 'player-loop.service'], check=True)

            else:
                logger.warning(f"Unknown mode: {mode}")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute systemctl command: {e}")
            
    def handle_volume_command(self, volume):
        """Handle volume adjustment (0-1 range)"""
        try:
            # Convert to percentage
            volume_percent = int(volume * 100)
            volume_percent = max(0, min(100, volume_percent))  # Clamp to 0-100
            
            logger.info(f"Setting volume to {volume_percent}%")
            subprocess.run([
                'pactl', 'set-sink-volume', 'sculpture_sink', f'{volume_percent}%'
            ], check=True, env=get_pactl_env())
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set volume: {e}")
            
    def handle_mute_command(self, mute):
        self.is_muted = bool(mute)  # Optimistically update state
        try:
            mute_flag = '1' if mute else '0'
            logger.info(f"Setting mute to {mute_flag} (True={mute})")
            subprocess.run([
                'pactl', 'set-sink-mute', 'sculpture_sink', mute_flag
            ], check=True, env=get_pactl_env())
            # Clear previous error on success
            self._last_mute_error = None
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set mute: {e} - state may not be in sync. Check if 'sculpture_sink' exists with 'pactl list sinks'.")

    def handle_stop_command(self):
        """Stop all audio-related services."""
        try:
            logger.info("Stopping all audio services due to emergency stop command.")
            # Stop both live and local playback services
            subprocess.run(['sudo', 'systemctl', 'stop', 'player-loop.service'], check=False)
            subprocess.run(['sudo', 'systemctl', 'stop', 'player-live.service'], check=False)
            # Stop the microphone streaming service
            subprocess.run(['sudo', 'systemctl', 'stop', 'darkice.service'], check=False)
            self.current_mode = "idle" # Set mode to idle
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop services during emergency stop: {e}")

    def handle_restart_command(self):
        try:
            logger.info("Restarting darkice.service via systemctl")
            subprocess.run(['sudo', 'systemctl', 'restart', 'darkice.service'], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart agent: {e}")
            
    def update_loop_track(self, track_path):
        """Update the player-loop service to use a different track via a systemd drop-in file."""
        service_name = 'player-loop.service'
        drop_in_dir = Path(f'/etc/systemd/system/{service_name}.d')
        drop_in_file = drop_in_dir / 'override.conf'

        samplerate = self.audio_config.get('samplerate', '22050')
        device = self.audio_config.get('device', 'pulse/sculpture_sink')
        audio_format = self.audio_config.get('format', 's16')

        # Ensure the drop-in directory exists
        try:
            if not drop_in_dir.exists():
                logger.info(f"Creating systemd drop-in directory: {drop_in_dir}")
                subprocess.run(['sudo', 'mkdir', '-p', str(drop_in_dir)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create systemd drop-in directory: {e}")
            return

        # Create the drop-in file content
        # This overrides only the ExecStart line of the service
        override_content = f"""[Service]
ExecStart=
ExecStart=/usr/bin/mpv --no-video --audio-device={device} --audio-samplerate={samplerate} --audio-format={audio_format} --loop {track_path}
"""
        try:
            # Write to a temporary file and then move it to be atomic
            temp_path = '/tmp/sculpture-override.conf.tmp'
            with open(temp_path, 'w') as f:
                f.write(override_content)
            
            # Use sudo to move the file into the system directory
            subprocess.run(['sudo', 'mv', temp_path, str(drop_in_file)], check=True)
            logger.info(f"Updated systemd drop-in for {service_name} to use track: {track_path}")

            # Reload systemd and restart the service
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        except Exception as e:
            logger.error(f"Failed to update loop service drop-in: {e}")
            
    def get_system_status(self):
        """Get CPU, temperature, microphone level, output level, mute status and mode"""
        try:
            error_message = None

            # Get CPU usage
            cpu_result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, check=True)
            cpu_line = next((line for line in cpu_result.stdout.split('\n') if 'Cpu(s)' in line), None)

            if cpu_line:
                try:
                    # More robust CPU parsing to handle different 'top' formats
                    match = re.search(r'(\d+[\.,]\d+)\s*us', cpu_line)
                    if match:
                        cpu_usage = float(match.group(1).replace(',', '.'))
                    else:
                        # Fallback for formats like "2.5% us"
                        parts = cpu_line.replace(',', ' ').split()
                        try:
                            us_index = parts.index('us')
                            cpu_usage = float(parts[us_index - 1])
                        except (ValueError, IndexError):
                            raise ValueError("Could not find 'us' CPU value.")
                except (ValueError, IndexError) as e:
                    error_message = f"Could not parse CPU usage from 'top' output: '{cpu_line}'. Error: {e}"
                    logger.warning(error_message + " Defaulting to 0.")
                    cpu_usage = 0.0
            else:
                logger.warning("Could not find 'Cpu(s)' line in top output.")
                cpu_usage = 0.0
            
            # Get temperature
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, check=True)
            temp_str = temp_result.stdout.strip().replace('temp=', '').replace("'C", '')
            temperature = float(temp_str)
            
            # Get mute status from pactl
            try:
                # Only check for mute status if we're in a mode that produces audio
                if self.current_mode != "idle":
                    mute_result = subprocess.run(
                        ['pactl', 'get-sink-mute', 'sculpture_sink'],
                        capture_output=True, text=True, check=True, env=get_pactl_env()
                    )
                    # Output is "Mute: yes" or "Mute: no"
                    self.is_muted = 'yes' in mute_result.stdout.lower()
                    # Clear previous error on success
                    self._last_mute_error = None
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                # Log warning only once if sink is not found, to avoid spamming logs
                if self._last_mute_error is None:
                    logger.warning(f"Could not get mute status: {e}. Using last known value. Further warnings will be suppressed.")
                    self._last_mute_error = str(e)

            # Get microphone input level (peak)
            mic_level = -60.0 # Default to silence
            try:
                # Use the special name @DEFAULT_SOURCE@ to listen to the system's default microphone
                mic_output = subprocess.check_output(
                    "parec --raw --device=@DEFAULT_SOURCE@ | od -N 2 -d | head -n 1 | awk '{ val = $2; if (val < 0) val = -val; print 20*(log( (val+0.0001) / 32767) / log(10)) }'",
                    shell=True,
                    timeout=0.5,
                    stderr=subprocess.PIPE,
                    env=get_pactl_env()
                )
                mic_level = float(mic_output.strip())
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
                if isinstance(e, subprocess.CalledProcessError):
                    logger.warning(f"Mic level check failed with error: {e.stderr.decode('utf-8').strip()}")
                pass # Keep default on error

            # Get speaker output level (peak)
            output_level = -60.0 # Default to silence
            try:
                # Use the special name sculpture_sink.monitor to listen to the sink's output
                output_output = subprocess.check_output(
                    "parec --raw --device=sculpture_sink.monitor | od -N 2 -d | head -n 1 | awk '{ val = $2; if (val < 0) val = -val; print 20*(log( (val+0.0001) / 32767) / log(10)) }'",
                    shell=True,
                    timeout=0.5,
                    stderr=subprocess.PIPE,
                    env=get_pactl_env()
                )
                output_level = float(output_output.strip())
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
                if isinstance(e, subprocess.CalledProcessError):
                    logger.warning(f"Output level check failed with error: {e.stderr.decode('utf-8').strip()}")
                pass # Keep default on error

            status = {
                'sculpture_id': self.sculpture_id,
                'cpu_usage': cpu_usage,
                'temperature': temperature,
                'mic_level': mic_level,
                'output_level': output_level,
                'mode': self.current_mode,
                'is_muted': self.is_muted,
                'timestamp': time.time()
            }
            if error_message:
                status['error'] = error_message
            return status
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'sculpture_id': self.sculpture_id,
                'cpu_usage': 0,
                'temperature': 0,
                'mic_level': -60,
                'output_level': -60,
                'mode': self.current_mode,
                'is_muted': self.is_muted,
                'timestamp': time.time(),
                'error': str(e)
            }
            
    def publish_status(self):
        """Publish system status every 5 seconds"""
        status = self.get_system_status()
        self.client.publish(self.status_topic, json.dumps(status))
        
    def run(self):
        """Main run loop"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            logger.info(f"Sculpture {self.sculpture_id} agent started")
            
            while True:
                self.publish_status()
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    agent = SculptureAgent()
    agent.run() 
