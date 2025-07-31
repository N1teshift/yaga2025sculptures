#!/bin/bash
# Entrypoint for server-agent in the sim harness.
# Copies the mounted server-agent source to a writable dir, then runs it.
set -e

export CONTROL_HOST="${CONTROL_HOST:-mosquitto}"
export MQTT_PASSWORD="${MQTT_PASSWORD:-changeme}"
export SSH_SIMULATION="${SSH_SIMULATION:-1}"
export PLAN_STATE_FILE=/tmp/current_plan.json

rm -rf /app/run && mkdir -p /app/run
cp -r /app/server-agent/. /app/run/
# In the harness, liquidsoap runs in a separate container (not localhost)
sed -i "s/LIQUIDSOAP_HOST = 'localhost'/LIQUIDSOAP_HOST = 'liquidsoap'/" /app/run/config.py
rm -rf /app/run/__pycache__
cd /app/run

echo "server-agent: starting (broker=${CONTROL_HOST})"
exec python3 server_agent.py
