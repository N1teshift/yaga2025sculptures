#!/bin/bash
# Complete Edge Node Configuration Script
# This script runs all modular playbooks in the correct sequence
# Equivalent to running the original monolithic playbook.yml

set -e

INVENTORY="edge/ansible/hosts.ini"
ANSIBLE_DIR="edge/ansible"

echo "Starting complete edge node configuration..."

echo "Step 1: System Setup & Hardware Configuration"
ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/system-setup.yml"

echo "Step 2: Content Synchronization & Media Management"
ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/content-sync.yml"

echo "Step 3: SSH Key Deployment & Access Management"
ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/ssh-access.yml"

echo "Step 4: Audio Backend Configuration"
ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/audio-backend.yml"

echo "Step 5: Application Deployment & Service Management"
ansible-playbook -i "$INVENTORY" "$ANSIBLE_DIR/app-deploy.yml"

echo "Complete edge node configuration finished!"
echo "All services should now be running on the target nodes." 