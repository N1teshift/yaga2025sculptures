"""
MQTT-to-Telnet Bridge for Liquidsoap Plan Switching

- Subscribes to MQTT topic 'system/broadcast'
- Expects messages like {"plan": "A1"}
- Sends 'set_plan <plan>' to Liquidsoap's telnet server (default: localhost:1234)

Configuration:
- MQTT broker: localhost:1883
- Liquidsoap telnet: localhost:1234
- Edit below if needed
"""

import asyncio
import json
import telnetlib3
import paho.mqtt.client as mqtt
import sys

print("MQTT bridge script started", file=sys.stderr)
sys.stderr.flush()

# Config
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_TOPIC = 'system/broadcast'
LIQUIDSOAP_HOST = 'localhost'
LIQUIDSOAP_PORT = 1234

# Async function to send telnet command
def send_telnet_command(plan):
    async def _send():
        try:
            reader, writer = await telnetlib3.open_connection(
                LIQUIDSOAP_HOST, LIQUIDSOAP_PORT
            )
            writer.write(f'set_plan {plan}\n')
            await writer.drain()
            # Optionally read response
            await asyncio.sleep(0.5)
            writer.close()
        except Exception as e:
            print(f"Telnet error: {e}", file=sys.stderr)
    asyncio.run(_send())

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with code {rc}", file=sys.stderr)
    sys.stderr.flush()
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)

        # If 'command' key exists, ignore the message
        if 'command' in data:
            return

        plan = data.get('plan')
        if plan:
            print(f"Received plan: {plan}, sending to Liquidsoap...", file=sys.stderr)
            sys.stderr.flush()
            send_telnet_command(plan)
        else:
            print(f"No 'plan' in message: {payload}", file=sys.stderr)
            sys.stderr.flush()
    except Exception as e:
        print(f"Error processing message: {e}", file=sys.stderr)
        sys.stderr.flush()

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
