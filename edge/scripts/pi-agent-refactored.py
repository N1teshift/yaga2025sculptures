#!/usr/bin/env python3

import json
import time
import os
import logging
import paho.mqtt.client as mqtt

from audio_manager import AudioManager
from system_manager import SystemManager
from status_collector import StatusCollector

# Configuration
MQTT_BROKER = os.environ.get('CONTROL_HOST', '192.168.8.156')
MQTT_PORT = 1883
SCULPTURE_ID = os.environ.get('SCULPTURE_ID', '1')
SCULPTURE_DIR = '/opt/sculpture-system'
AUDIO_CONFIG_PATH = '/etc/sculpture/audio.conf'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SculptureAgent:
    """Main sculpture agent orchestrating all components."""
    
    def __init__(self):
        # Initialize MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Initialize components
        self.audio_manager = AudioManager(AUDIO_CONFIG_PATH)
        self.system_manager = SystemManager(SCULPTURE_DIR)
        self.status_collector = StatusCollector(SCULPTURE_ID)
        
        # MQTT topics
        self.sculpture_id = SCULPTURE_ID
        self.status_topic = f"sculpture/{self.sculpture_id}/status"
        self.cmd_topic = f"sculpture/{self.sculpture_id}/cmd"
        self.tracks_topic = f"sculpture/{self.sculpture_id}/tracks"
        self.broadcast_topic = "system/broadcast"
        
    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(self.cmd_topic)
        client.subscribe(self.broadcast_topic)
        logger.info(f"Subscribed to {self.cmd_topic} and {self.broadcast_topic}")
        # Default to live mode on connect
        self.handle_mode_command("live")
        
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")
            
            if not isinstance(payload, dict):
                logger.warning(f"Received message is not a JSON object, ignoring. Payload: {payload}")
                return

            # Route commands to appropriate handlers
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
            
    def handle_mode_command(self, mode, track=None):
        """Handle mode switching commands."""
        try:
            if mode == "live":
                self.system_manager.switch_to_live_mode()
            elif mode == "local":
                self.system_manager.switch_to_local_mode(track, self.audio_manager.audio_config)
            else:
                logger.warning(f"Unknown mode: {mode}")
        except Exception as e:
            logger.error(f"Failed to handle mode command: {e}")
            
    def handle_volume_command(self, volume):
        """Handle volume adjustment commands."""
        try:
            self.audio_manager.set_volume(volume)
        except Exception as e:
            logger.error(f"Failed to handle volume command: {e}")
            
    def handle_mute_command(self, mute):
        """Handle mute/unmute commands."""
        try:
            self.audio_manager.set_mute(mute)
        except Exception as e:
            logger.error(f"Failed to handle mute command: {e}")
            
    def handle_restart_command(self):
        """Handle restart commands."""
        try:
            self.system_manager.restart_all_services()
        except Exception as e:
            logger.error(f"Failed to handle restart command: {e}")
            
    def handle_get_tracks(self):
        """Handle get tracks commands."""
        try:
            tracks = self.system_manager.get_available_tracks()
            self.client.publish(self.tracks_topic, json.dumps(tracks), retain=True)
        except Exception as e:
            logger.error(f"Failed to handle get tracks command: {e}")
            
    def handle_stop_command(self):
        """Handle emergency stop commands."""
        try:
            self.system_manager.stop_all_services()
        except Exception as e:
            logger.error(f"Failed to handle stop command: {e}")
            
    def get_system_status(self):
        """Get complete system status."""
        try:
            # Get audio levels
            mic_level = self.audio_manager.get_microphone_level()
            output_level = self.audio_manager.get_output_level()
            
            # Get mute status
            is_muted = self.audio_manager.get_mute_status(self.system_manager.current_mode)
            
            # Build status using status collector
            status = self.status_collector.build_status(
                current_mode=self.system_manager.current_mode,
                is_muted=is_muted,
                mic_level=mic_level,
                output_level=output_level
            )
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            # Return fallback status
            return self.status_collector.build_status(
                current_mode=self.system_manager.current_mode,
                is_muted=self.audio_manager.is_muted,
                mic_level=-60,
                output_level=-60,
                error_message=str(e)
            )
            
    def publish_status(self):
        """Publish system status to MQTT."""
        status = self.get_system_status()
        self.client.publish(self.status_topic, json.dumps(status))
        
    def run(self):
        """Main run loop."""
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