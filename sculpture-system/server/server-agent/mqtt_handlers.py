#!/usr/bin/env python3
"""
MQTT handlers module for server-agent
Contains MQTT callbacks, message handlers, and publishing functions
"""

import json
import time
import logging
import subprocess
from datetime import timedelta

# Import configuration
from config import (
    CMD_TOPIC, STATUS_TOPIC, PLAN_TOPIC, UNDERRUN_TOPIC, DARKICE_TOPIC,
    STATUS_PUBLISH_INTERVAL
)

logger = logging.getLogger(__name__)

class MQTTHandlers:
    """Handles MQTT callbacks and message processing."""
    
    def __init__(self, plan_manager, liquidsoap_client, underrun_monitor, darkice_monitor):
        self.plan_manager = plan_manager
        self.liquidsoap_client = liquidsoap_client
        self.underrun_monitor = underrun_monitor
        self.darkice_monitor = darkice_monitor
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback."""
        logger.info(f"[MQTT] Connected to MQTT broker with result code {rc}")
        client.subscribe(CMD_TOPIC)
        client.subscribe("system/broadcast")  # Listen for plan broadcasts
        client.subscribe("system/audio/cmd")  # Listen for audio commands
        
        # Publish initial plan status
        self.publish_plan_status(client)
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)
            
            if msg.topic == CMD_TOPIC:
                self.handle_command_message(client, data)
            elif msg.topic == "system/broadcast":
                self.handle_broadcast_message(client, data)
            elif msg.topic == "system/audio/cmd":
                self.handle_audio_command_message(client, data)
            else:
                logger.warning(f"[MQTT] Unknown topic: {msg.topic}")
                
        except Exception as e:
            logger.error(f"[MQTT] Message handling error: {e}")
    
    def handle_command_message(self, client, data):
        """Handle command messages."""
        try:
            if 'restart' in data:
                service = data['restart']
                if service in ['icecast2', 'liquidsoap']:
                    logger.info(f"[MQTT] Restarting {service}...")
                    subprocess.run(['sudo', 'systemctl', 'restart', service], check=True)
                    logger.info(f"[MQTT] Restarted {service}")
                    
                    # Re-sync plan with Liquidsoap after restart
                    if service == 'liquidsoap':
                        time.sleep(2)  # Give liquidsoap time to start
                        self.handle_plan_command(client, self.plan_manager.get_plan())
                else:
                    logger.warning(f"[MQTT] Unknown service: {service}")
            
            elif 'underrun_summary' in data:
                logger.info("[MQTT] Underrun summary requested")
                self.publish_underrun_summary(client)
            
            elif 'darkice_summary' in data:
                logger.info("[MQTT] Darkice summary requested")
                self.publish_darkice_summary(client)
            
            elif 'darkice_restart' in data:
                system = data.get('system')
                service = data.get('service', 'darkice')
                if system:
                    logger.info(f"[MQTT] Manual darkice restart requested for {system}/{service}")
                    self.darkice_monitor.trigger_darkice_restart(system, service)
                else:
                    logger.warning("[MQTT] Darkice restart command missing system parameter")
            
            else:
                logger.warning(f"[MQTT] Unknown command: {data}")
                
        except Exception as e:
            logger.error(f"[MQTT] Command handling error: {e}")
    
    def handle_broadcast_message(self, client, data):
        """Handle broadcast messages."""
        try:
            if 'plan' in data:
                plan = data['plan']
                mode = data.get('mode', 'live')  # Default to live if mode not specified
                
                logger.info(f"[MQTT] Received plan broadcast: {plan} (mode: {mode})")
                
                # Update Liquidsoap with plan (Liquidsoap doesn't care about mode)
                self.handle_plan_command(client, plan)
                
                # Forward complete message to pi-agents for mode switching
                self.forward_to_sculptures(client, plan, mode)
            else:
                logger.warning(f"[MQTT] Broadcast message missing plan: {data}")
                
        except Exception as e:
            logger.error(f"[MQTT] Broadcast handling error: {e}")
    
    def handle_audio_command_message(self, client, data):
        """Handle audio command messages."""
        try:
            if 'processing_toggle' in data:
                enable = data['processing_toggle']
                logger.info(f"[MQTT] Audio processing toggle: {'enable' if enable else 'disable'}")
                
                if enable:
                    response = self.liquidsoap_client.send_command("enable_processing")
                else:
                    response = self.liquidsoap_client.send_command("disable_processing")
                
                if response:
                    logger.info(f"[MQTT] Liquidsoap response: {response}")
                    # Publish status update
                    self.publish_audio_processing_status(client)
                else:
                    logger.error(f"[MQTT] Failed to toggle audio processing")
                    
            elif 'get_processing_status' in data:
                logger.info("[MQTT] Audio processing status requested")
                self.publish_audio_processing_status(client)
                
            elif 'reset' in data:
                logger.info("[MQTT] Audio processing reset requested")
                response = self.liquidsoap_client.send_command("reset_audio")
                if response:
                    logger.info(f"[MQTT] Audio reset response: {response}")
                    self.publish_audio_processing_status(client)
                else:
                    logger.error(f"[MQTT] Failed to reset audio processing")
                    
            else:
                # Handle individual audio parameter commands
                for param, value in data.items():
                    if param in ['compress_ratio', 'compress_threshold', 'attack_time', 'release_time',
                               'highpass_freq', 'lowpass_freq', 'delay_time', 'delay_feedback',
                               'gate_threshold', 'normalize_target']:
                        command = f"set_{param}"
                        response = self.liquidsoap_client.send_command(command, str(value))
                        if response:
                            logger.info(f"[MQTT] Set {param} to {value}: {response}")
                        else:
                            logger.error(f"[MQTT] Failed to set {param} to {value}")
                
        except Exception as e:
            logger.error(f"[MQTT] Audio command handling error: {e}")
    
    def publish_audio_processing_status(self, client):
        """Publish current audio processing status to MQTT."""
        try:
            response = self.liquidsoap_client.send_command("get_processing_status")
            if response:
                # Response is 'enabled' or 'disabled'
                is_enabled = response.strip() == 'enabled'
                status_data = {
                    'processing_enabled': is_enabled,
                    'timestamp': time.time(),
                    'source': 'server-agent'
                }
                client.publish("system/audio/status", json.dumps(status_data), retain=True)
                logger.info(f"[MQTT] Published audio processing status: {'enabled' if is_enabled else 'disabled'}")
            else:
                logger.error("[MQTT] Failed to get audio processing status from Liquidsoap")
        except Exception as e:
            logger.error(f"[MQTT] Failed to publish audio processing status: {e}")
    
    def handle_plan_command(self, client, plan):
        """Handle plan selection command."""
        if not self.plan_manager.is_valid_plan(plan):
            logger.warning(f"[MQTT] Invalid plan: {plan}")
            return
        
        current_plan = self.plan_manager.get_plan()
        logger.info(f"[MQTT] Changing plan from {current_plan} to {plan}")
        
        # Update Liquidsoap
        response = self.liquidsoap_client.set_plan(plan)
        
        if response:
            logger.info(f"[MQTT] Liquidsoap response: {response}")
            self.plan_manager.set_plan(plan)
            self.publish_plan_status(client)
        else:
            logger.error(f"[MQTT] Failed to set plan in Liquidsoap")
    
    def forward_to_sculptures(self, client, plan, mode):
        """Forward plan and mode information to all pi-agents."""
        try:
            message_data = {
                'plan': plan,
                'mode': mode,
                'timestamp': time.time(),
                'source': 'server-agent'
            }
            
            # Publish to system/plan topic for pi-agents
            client.publish("system/plan", json.dumps(message_data), retain=True)
            logger.info(f"[MQTT] Forwarded plan {plan} (mode: {mode}) to sculptures")
            
        except Exception as e:
            logger.error(f"[MQTT] Failed to forward plan to sculptures: {e}")
    
    def publish_plan_status(self, client):
        """Publish current plan status to MQTT."""
        try:
            status = self.plan_manager.get_plan_status()
            client.publish(STATUS_TOPIC, json.dumps(status), retain=True)
            client.publish(PLAN_TOPIC, json.dumps({'plan': self.plan_manager.get_plan()}), retain=True)
            logger.info(f"[MQTT] Published plan status: {self.plan_manager.get_plan()}")
        except Exception as e:
            logger.error(f"[MQTT] Failed to publish plan status: {e}")
    
    def publish_underrun_summary(self, client):
        """Publish underrun summary to MQTT."""
        try:
            summary = self.underrun_monitor.get_underrun_summary()
            summary_data = {
                'timestamp': time.time(),
                'systems': summary,
                'source': 'server-agent'
            }
            client.publish(f"{UNDERRUN_TOPIC}/summary", json.dumps(summary_data), retain=True)
            
            # Log summary for console visibility
            totals = summary.get('_totals', {})
            total_underruns = totals.get('total_underruns', 0)
            recent_underruns = totals.get('recent_underruns_1h', 0)
            
            logger.info(f"[MQTT] Underrun summary - Total: {total_underruns}, Recent (1h): {recent_underruns}")
            
        except Exception as e:
            logger.error(f"[MQTT] Failed to publish underrun summary: {e}")
    
    def publish_darkice_summary(self, client):
        """Publish darkice buffer overrun summary to MQTT."""
        try:
            summary = self.darkice_monitor.get_darkice_summary()
            summary_data = {
                'timestamp': time.time(),
                'systems': summary,
                'source': 'server-agent'
            }
            client.publish(f"{DARKICE_TOPIC}/summary", json.dumps(summary_data), retain=True)
            
            # Log summary for console visibility
            total_overruns = sum(
                sum(service.get('total_buffer_overruns', 0) for service in system.values())
                for system in summary.values()
            )
            restart_attempts = sum(
                sum(service.get('restart_attempts', 0) for service in system.values())
                for system in summary.values()
            )
            spam_detected = any(
                any(service.get('spam_detected', False) for service in system.values())
                for system in summary.values()
            )
            
            logger.info(f"[MQTT] Darkice summary - Buffer overruns: {total_overruns}, Restart attempts: {restart_attempts}, Spam detected: {spam_detected}")
            
        except Exception as e:
            logger.error(f"[MQTT] Failed to publish darkice summary: {e}")

class StatusPublisher:
    """Handles periodic status publishing."""
    
    def __init__(self, mqtt_handlers, plan_manager, liquidsoap_client):
        self.mqtt_handlers = mqtt_handlers
        self.plan_manager = plan_manager
        self.liquidsoap_client = liquidsoap_client
    
    def status_publisher_thread(self, client):
        """Background thread to periodically publish status and sync with Liquidsoap."""
        while True:
            try:
                # Periodically sync plan state with Liquidsoap
                liquidsoap_plan = self.liquidsoap_client.get_plan()
                current_plan = self.plan_manager.get_plan()
                
                if liquidsoap_plan and liquidsoap_plan != current_plan:
                    logger.info(f"[STATUS] Plan drift detected. Liquidsoap: {liquidsoap_plan}, Agent: {current_plan}")
                    # Update our state to match Liquidsoap (Liquidsoap is source of truth)
                    self.plan_manager.set_plan(liquidsoap_plan)
                    self.mqtt_handlers.publish_plan_status(client)
                
                # Regular status publish
                self.mqtt_handlers.publish_plan_status(client)
                
                # Publish audio processing status
                self.mqtt_handlers.publish_audio_processing_status(client)
                
                # Publish monitoring summaries
                self.mqtt_handlers.publish_underrun_summary(client)
                self.mqtt_handlers.publish_darkice_summary(client)
                
            except Exception as e:
                logger.error(f"[STATUS] Publisher error: {e}")
            
            time.sleep(STATUS_PUBLISH_INTERVAL) 