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

# Configuration
MQTT_BROKER = os.environ.get('CONTROL_HOST', '192.168.178.79')
MQTT_PORT = 1883
SCULPTURE_ID = os.environ.get('SCULPTURE_ID', '1')
SCULPTURE_DIR = '/opt/sculpture-system'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SculptureAgent:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sculpture_id = SCULPTURE_ID
        self.status_topic = f"sculpture/{self.sculpture_id}/status"
        self.cmd_topic = f"sculpture/{self.sculpture_id}/cmd"
        self.broadcast_topic = "system/broadcast"
        self.is_recording = False  # Track recording state
        self.is_muted = False      # Track mute state
        
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
            
            if 'mode' in payload:
                self.handle_mode_command(payload['mode'], payload.get('track'))
            elif 'volume' in payload:
                self.handle_volume_command(payload['volume'])
            elif 'mute' in payload:
                self.handle_mute_command(payload['mute'])
            elif 'restart' in payload and payload['restart']:
                self.handle_restart_command()
            else:
                logger.warning(f"Unknown command: {payload}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    def handle_mode_command(self, mode, track=None):
        """Handle mode switching between live and local playback"""
        try:
            if mode == "live":
                logger.info("Switching to live mode")
                self.is_recording = False
                # Stop local playback
                subprocess.run(['sudo', 'systemctl', 'stop', 'player-loop.service'], check=False)
                # Start live streaming and playback
                subprocess.run(['sudo', 'systemctl', 'start', 'darkice.service'], check=True)
                subprocess.run(['sudo', 'systemctl', 'start', 'player-live.service'], check=True)
                
            elif mode == "local":
                logger.info(f"Switching to local mode with track: {track}")
                self.is_recording = False
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
                        
                # Start local playback
                subprocess.run(['sudo', 'systemctl', 'start', 'player-loop.service'], check=True)
                
            elif mode == "recording":
                logger.info("Switching to recording mode")
                self.is_recording = True
                # Implement actual recording logic if needed
                
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
            ], check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set volume: {e}")
            
    def handle_mute_command(self, mute):
        try:
            mute_flag = '1' if mute else '0'
            logger.info(f"Setting mute to {mute_flag} (True={mute})")
            subprocess.run([
                'pactl', 'set-sink-mute', 'sculpture_sink', mute_flag
            ], check=True)
            self.is_muted = bool(mute)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set mute: {e}")

    def handle_restart_command(self):
        try:
            logger.info("Restarting pi-agent.service via systemctl")
            subprocess.run(['sudo', 'systemctl', 'restart', 'pi-agent.service'], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart agent: {e}")
            
    def update_loop_track(self, track_path):
        """Update the player-loop service to use a different track"""
        service_content = f"""[Unit]
Description=Sculpture Loop Player
After=sound.target

[Service]
Type=simple
ExecStart=/usr/bin/mpv --loop --no-video --ao=pulse {track_path}
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
"""
        try:
            with open('/etc/systemd/system/player-loop.service', 'w') as f:
                f.write(service_content)
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        except Exception as e:
            logger.error(f"Failed to update loop service: {e}")
            
    def get_system_status(self):
        """Get CPU, temperature, audio level, recording, and online status"""
        try:
            # Get CPU usage
            cpu_result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
            cpu_line = [line for line in cpu_result.stdout.split('\n') if 'Cpu(s)' in line][0]
            cpu_usage = float(cpu_line.split()[1].replace('%us,', ''))
            
            # Get temperature
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
            temp_str = temp_result.stdout.strip().replace('temp=', '').replace("'C", '')
            temperature = float(temp_str)
            
            # Placeholder for audio level (simulate with random value between -50 and 0 dB)
            audio_level = random.uniform(-50, 0)
            
            # Always online if running
            online = 1
            
            # Recording state
            recording = 1 if self.is_recording else 0
            
            return {
                'sculpture_id': self.sculpture_id,
                'cpu_usage': cpu_usage,
                'temperature': temperature,
                'audio_level': audio_level,
                'recording': recording,
                'online': online,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'sculpture_id': self.sculpture_id,
                'cpu_usage': 0,
                'temperature': 0,
                'audio_level': -60,
                'recording': 0,
                'online': 1,
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
