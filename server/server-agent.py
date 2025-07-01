#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import subprocess
import threading
import time
import json
import os

MQTT_BROKER = os.environ.get('CONTROL_HOST', 'localhost')
MQTT_PORT = 1883
CMD_TOPIC = "server/cmd"

# Paths to logs you want to tail
LOG_PATHS = {
    "icecast2": "/var/log/icecast2/icecast.log",
    "liquidsoap": "/var/log/liquidsoap.log",
    "mqtt_to_telnet_bridge": "/var/log/mqtt_to_telnet_bridge.log"
}

def tail_log(name, path):
    """Continuously tail a log file and print new lines with a prefix."""
    try:
        with subprocess.Popen(['tail', '-F', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            for line in proc.stdout:
                print(f"[{name}] {line.strip()}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code", rc)
    client.subscribe(CMD_TOPIC)

def on_message(client, userdata, msg):
    try:
        if msg.topic == CMD_TOPIC:
            payload = msg.payload.decode()
            data = json.loads(payload)
            if 'restart' in data:
                service = data['restart']
                if service in ['icecast2', 'liquidsoap']:
                    print(f"[CMD] Restarting {service}...")
                    subprocess.run(['sudo', 'systemctl', 'restart', service], check=True)
                    print(f"[CMD] Restarted {service}")
                else:
                    print(f"[CMD] Unknown service: {service}")
            else:
                print(f"[CMD] Unknown command: {data}")
    except Exception as e:
        print(f"[MQTT ERROR] {e}")

def main():
    # Start log tailing threads
    for name, path in LOG_PATHS.items():
        if os.path.exists(path):
            t = threading.Thread(target=tail_log, args=(name, path), daemon=True)
            t.start()
        else:
            print(f"[{name}] Log file not found: {path}")

    # Start MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main() 