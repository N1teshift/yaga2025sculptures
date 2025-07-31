#!/usr/bin/env python3
"""
Server Agent - Main Application
Modular server agent for sculpture installation monitoring and control
"""

import paho.mqtt.client as mqtt
import subprocess
import threading
import time
import os
import logging
import signal
import sys

# Import our modules
from config import (
    MQTT_BROKER, MQTT_PORT, PI_SYSTEMS, LOG_PATHS, 
    LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, load_config_overrides
)
from underrun_monitor import UnderrunMonitor
from darkice_monitor import DarkiceMonitor
from liquidsoap_client import LiquidSoapClient
from plan_manager import PlanManager
from mqtt_handlers import MQTTHandlers, StatusPublisher

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)

class ServerAgent:
    """Main server agent application."""
    
    def __init__(self):
        # Load configuration overrides
        load_config_overrides()
        
        # Initialize components
        self.plan_manager = PlanManager()
        self.liquidsoap_client = LiquidSoapClient()
        self.underrun_monitor = UnderrunMonitor(PI_SYSTEMS)
        self.darkice_monitor = DarkiceMonitor(PI_SYSTEMS)
        
        # Initialize MQTT handlers
        self.mqtt_handlers = MQTTHandlers(
            self.plan_manager,
            self.liquidsoap_client,
            self.underrun_monitor,
            self.darkice_monitor
        )
        self.status_publisher = StatusPublisher(
            self.mqtt_handlers,
            self.plan_manager,
            self.liquidsoap_client
        )
        
        # MQTT client
        self.mqtt_client = None
        
        # Tracking
        self.log_threads = []
        
    def setup_mqtt_client(self):
        """Setup MQTT client with callbacks."""
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.on_connect = self.mqtt_handlers.on_connect
            self.mqtt_client.on_message = self.mqtt_handlers.on_message
            
            # Set MQTT client references in monitors
            self.underrun_monitor.set_mqtt_client(self.mqtt_client)
            self.darkice_monitor.set_mqtt_client(self.mqtt_client)
            
            # Connect to broker
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logger.info(f"[MAIN] MQTT client configured and connected to {MQTT_BROKER}:{MQTT_PORT}")
            
        except Exception as e:
            logger.error(f"[MAIN] Failed to setup MQTT client: {e}")
            return False
        
        return True
    
    def start_log_tailing(self):
        """Start log tailing threads for server services."""
        for name, path in LOG_PATHS.items():
            if os.path.exists(path):
                thread = threading.Thread(
                    target=self.tail_log, 
                    args=(name, path), 
                    daemon=True,
                    name=f"log-tail-{name}"
                )
                thread.start()
                self.log_threads.append(thread)
                logger.info(f"[MAIN] Started log tailing for {name}: {path}")
            else:
                logger.warning(f"[MAIN] Log file not found: {path}")
    
    def tail_log(self, name, path):
        """Continuously tail a log file and print new lines with a prefix."""
        try:
            with subprocess.Popen(['tail', '-F', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
                for line in proc.stdout:
                    logger.info(f"[{name.upper()}] {line.strip()}")
        except Exception as e:
            logger.error(f"[MAIN] Log tailing error for {name}: {e}")
    
    def start_monitoring(self):
        """Start all monitoring services."""
        logger.info("[MAIN] Starting monitoring services...")
        
        # Start underrun monitoring
        logger.info("[MAIN] Starting underrun monitoring...")
        self.underrun_monitor.start_monitoring()
        
        # Start darkice monitoring
        logger.info("[MAIN] Starting darkice monitoring...")
        self.darkice_monitor.start_monitoring()
        
        logger.info("[MAIN] All monitoring services started")
    
    def start_status_publisher(self):
        """Start the background status publisher."""
        status_thread = threading.Thread(
            target=self.status_publisher.status_publisher_thread,
            args=(self.mqtt_client,),
            daemon=True,
            name="status-publisher"
        )
        status_thread.start()
        logger.info("[MAIN] Status publisher started")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"[MAIN] Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """Graceful shutdown."""
        logger.info("[MAIN] Shutting down server agent...")
        
        # Close MQTT client
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            logger.info("[MAIN] MQTT client disconnected")
        
        # Close SSH connections
        for ssh in self.underrun_monitor.ssh_connections.values():
            try:
                ssh.close()
            except:
                pass
        
        for ssh in self.darkice_monitor.ssh_connections.values():
            try:
                ssh.close()
            except:
                pass
        
        logger.info("[MAIN] Shutdown complete")
    
    def run(self):
        """Main application entry point."""
        logger.info("=" * 60)
        logger.info("Server Agent starting up...")
        logger.info("=" * 60)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Setup MQTT client
        if not self.setup_mqtt_client():
            logger.error("[MAIN] Failed to setup MQTT client, exiting")
            return 1
        
        # Start log tailing
        self.start_log_tailing()
        
        # Start monitoring services
        self.start_monitoring()
        
        # Start status publisher
        self.start_status_publisher()
        
        # Log startup completion
        logger.info("[MAIN] Server agent started successfully with:")
        logger.info(f"[MAIN] - Plan management (current: {self.plan_manager.get_plan()})")
        logger.info(f"[MAIN] - Underrun monitoring ({len(PI_SYSTEMS)} systems)")
        logger.info(f"[MAIN] - Darkice buffer overrun monitoring")
        logger.info(f"[MAIN] - MQTT communication on {MQTT_BROKER}:{MQTT_PORT}")
        logger.info(f"[MAIN] - Log tailing ({len(self.log_threads)} services)")
        
        try:
            # Start MQTT loop
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("[MAIN] Received keyboard interrupt")
        except Exception as e:
            logger.error(f"[MAIN] Unexpected error: {e}")
            return 1
        finally:
            self.shutdown()
        
        return 0

def main():
    """Main entry point."""
    try:
        app = ServerAgent()
        return app.run()
    except Exception as e:
        logger.error(f"[MAIN] Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 