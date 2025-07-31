#!/bin/bash
# Entrypoint for a simulated sculpture container.
# Renders the pi-agent templates, then runs the agent in SIMULATION mode.
set -e

export SIMULATION=1
export AUDIO_BACKEND="${AUDIO_BACKEND:-alsa}"
export SCULPTURE_ID="${SCULPTURE_ID:-1}"
export CONTROL_HOST="${CONTROL_HOST:-mosquitto}"
export MQTT_USERNAME="${MQTT_USERNAME:-sculpture}"
export MQTT_PASSWORD="${MQTT_PASSWORD:-changeme}"

echo "edge-sim: rendering pi-agent templates..."
python3 /app/render.py

cd /app/run
echo "edge-sim: starting pi-agent (id=${SCULPTURE_ID}, sim=${SIMULATION})"
exec python3 pi-agent.py
