#!/bin/bash

# Installation script for enhanced server-agent with underrun monitoring

echo "Installing enhanced server-agent..."

# Create service directory
sudo mkdir -p /opt/sculpture-system

# Copy service files
sudo cp server-agent.py /opt/sculpture-system/
sudo cp server-agent.service /etc/systemd/system/

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Set permissions
sudo chown -R unix:unix /opt/sculpture-system
sudo chmod +x /opt/sculpture-system/server-agent.py

# Setup SSH key for Pi connections (optional)
echo "Setting up SSH access..."
echo "Make sure you have SSH key-based authentication set up for the Pi systems."
echo "You can do this by running:"
echo "  ssh-keygen -t ed25519 -C 'server-agent'"
echo "  ssh-copy-id pi@sculpture1.local"
echo "  ssh-copy-id pi@sculpture2.local"
echo "  ssh-copy-id pi@sculpture3.local"

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable server-agent
sudo systemctl restart server-agent

echo "Enhanced server-agent installed and started."
echo "Check status with: sudo systemctl status server-agent"
echo "View logs with: journalctl -u server-agent -f -o cat" 