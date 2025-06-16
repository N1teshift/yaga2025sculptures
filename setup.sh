#!/bin/bash
# Sculpture System server setup script
# Installs required packages for Icecast, Liquidsoap, Mosquitto, Node.js and Node-RED
# Also installs Python dependencies for the MQTT bridge
set -e

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "Please run as root, e.g. sudo $0" >&2
    exit 1
fi

# Move to repo root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

apt update

# Install Node.js repository
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

apt update

# Install apt packages
apt install -y \
    icecast2 \
    liquidsoap \
    mosquitto \
    mosquitto-clients \
    nodejs \
    ansible \
    python3-pip

# Install Node-RED
npm install -g node-red

# Install Python requirements
pip3 install -r server/liquidsoap/requirements.txt

echo "Setup complete"
