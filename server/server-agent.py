#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import subprocess
import threading
import time
import json
import os
import socket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MQTT_BROKER = os.environ.get('CONTROL_HOST', 'localhost')
MQTT_PORT = 1883
CMD_TOPIC = "server/cmd"
STATUS_TOPIC = "system/status"
PLAN_TOPIC = "system/plan"

# Liquidsoap telnet configuration
LIQUIDSOAP_HOST = 'localhost'
LIQUIDSOAP_PORT = 1234

# Plan state management
current_plan = "B1"  # Default plan
plan_state_file = "/tmp/current_plan.json"

# Paths to logs you want to tail
LOG_PATHS = {
    "icecast2": "/var/log/icecast2/icecast.log",
    "liquidsoap": "/var/log/liquidsoap.log",
    "mqtt_to_telnet_bridge": "/var/log/mqtt_to_telnet_bridge.log"
}

class LiquidSoapClient:
    """Simple client to communicate with Liquidsoap via telnet."""
    
    def __init__(self, host='localhost', port=1234):
        self.host = host
        self.port = port
    
    def send_command(self, command):
        """Send a command to Liquidsoap via telnet."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # 5 second timeout
                sock.connect((self.host, self.port))
                
                # Send command
                sock.sendall(f"{command}\n".encode())
                
                # Read response
                response = sock.recv(1024).decode().strip()
                return response
        except Exception as e:
            logger.error(f"Failed to send command to Liquidsoap: {e}")
            return None
    
    def set_plan(self, plan):
        """Set the current plan in Liquidsoap."""
        return self.send_command(f"set_plan {plan}")
    
    def get_plan(self):
        """Get the current plan from Liquidsoap."""
        return self.send_command("get_plan")

def load_plan_state():
    """Load the current plan from persistent storage."""
    global current_plan
    try:
        if os.path.exists(plan_state_file):
            with open(plan_state_file, 'r') as f:
                data = json.load(f)
                current_plan = data.get('plan', 'B1')
                logger.info(f"Loaded plan state: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to load plan state: {e}")
        current_plan = "B1"

def save_plan_state():
    """Save the current plan to persistent storage."""
    try:
        with open(plan_state_file, 'w') as f:
            json.dump({'plan': current_plan, 'timestamp': time.time()}, f)
        logger.info(f"Saved plan state: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to save plan state: {e}")

def publish_plan_status(client):
    """Publish current plan status to MQTT."""
    status = {
        'plan': current_plan,
        'timestamp': time.time(),
        'source': 'server-agent'
    }
    try:
        client.publish(STATUS_TOPIC, json.dumps(status), retain=True)
        client.publish(PLAN_TOPIC, json.dumps({'plan': current_plan}), retain=True)
        logger.info(f"Published plan status: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to publish plan status: {e}")

def handle_plan_command(client, plan):
    """Handle plan selection command."""
    global current_plan
    
    valid_plans = ['A1', 'A2', 'B1', 'B2', 'B3', 'C', 'D']
    
    if plan not in valid_plans:
        logger.warning(f"Invalid plan: {plan}")
        return
    
    logger.info(f"Changing plan from {current_plan} to {plan}")
    
    # Update Liquidsoap
    liquidsoap = LiquidSoapClient(LIQUIDSOAP_HOST, LIQUIDSOAP_PORT)
    response = liquidsoap.set_plan(plan)
    
    if response:
        logger.info(f"Liquidsoap response: {response}")
        current_plan = plan
        save_plan_state()
        publish_plan_status(client)
    else:
        logger.error(f"Failed to set plan in Liquidsoap")

def tail_log(name, path):
    """Continuously tail a log file and print new lines with a prefix."""
    try:
        with subprocess.Popen(['tail', '-F', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            for line in proc.stdout:
                print(f"[{name}] {line.strip()}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(CMD_TOPIC)
    client.subscribe("system/broadcast")  # Listen for plan broadcasts
    
    # Publish initial plan status
    publish_plan_status(client)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        if msg.topic == CMD_TOPIC:
            # Handle service restart commands
            if 'restart' in data:
                service = data['restart']
                if service in ['icecast2', 'liquidsoap']:
                    logger.info(f"Restarting {service}...")
                    subprocess.run(['sudo', 'systemctl', 'restart', service], check=True)
                    logger.info(f"Restarted {service}")
                    
                    # Re-sync plan with Liquidsoap after restart
                    if service == 'liquidsoap':
                        time.sleep(2)  # Give liquidsoap time to start
                        handle_plan_command(client, current_plan)
                else:
                    logger.warning(f"Unknown service: {service}")
            else:
                logger.warning(f"Unknown command: {data}")
                
        elif msg.topic == "system/broadcast":
            # Handle plan broadcast messages
            if 'plan' in data:
                plan = data['plan']
                handle_plan_command(client, plan)
            else:
                logger.warning(f"Broadcast message missing plan: {data}")
                
    except Exception as e:
        logger.error(f"MQTT message handling error: {e}")

def status_publisher_thread(client):
    """Background thread to periodically publish status and sync with Liquidsoap."""
    global current_plan
    
    while True:
        try:
            # Periodically sync plan state with Liquidsoap
            liquidsoap = LiquidSoapClient(LIQUIDSOAP_HOST, LIQUIDSOAP_PORT)
            liquidsoap_plan = liquidsoap.get_plan()
            
            if liquidsoap_plan and liquidsoap_plan != current_plan:
                logger.info(f"Plan drift detected. Liquidsoap: {liquidsoap_plan}, Agent: {current_plan}")
                # Update our state to match Liquidsoap (Liquidsoap is source of truth)
                current_plan = liquidsoap_plan
                save_plan_state()
                publish_plan_status(client)
            
            # Regular status publish
            publish_plan_status(client)
            
        except Exception as e:
            logger.error(f"Status publisher error: {e}")
        
        time.sleep(30)  # Publish every 30 seconds

def main():
    # Load saved plan state
    load_plan_state()
    
    # Start log tailing threads
    for name, path in LOG_PATHS.items():
        if os.path.exists(path):
            t = threading.Thread(target=tail_log, args=(name, path), daemon=True)
            t.start()
        else:
            logger.warning(f"Log file not found: {path}")

    # Start MQTT client  
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    # Start background status publisher
    status_thread = threading.Thread(target=status_publisher_thread, args=(client,), daemon=True)
    status_thread.start()
    
    logger.info("Server agent started with plan management")
    client.loop_forever()

if __name__ == "__main__":
    main() 