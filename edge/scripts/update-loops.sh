#!/bin/bash

# Update loops script - rsync new WAVs from control server
# Usage: ./update-loops.sh [control_host]

CONTROL_HOST=${1:-192.168.8.156}
SCULPTURE_DIR="/opt/sculpture-system"
LOOPS_DIR="$SCULPTURE_DIR/loops"
REMOTE_LOOPS_DIR="/opt/sculpture-system/shared-loops"

# Ensure loops directory exists
mkdir -p "$LOOPS_DIR"

# Log file
LOG_FILE="/var/log/sculpture-update-loops.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting loop update from $CONTROL_HOST"

# Check if control host is reachable
if ! ping -c 1 "$CONTROL_HOST" > /dev/null 2>&1; then
    log "ERROR: Control host $CONTROL_HOST is not reachable"
    exit 1
fi

# Sync WAV files from control server
if rsync -avz --include="*.wav" --exclude="*" \
    "pi@$CONTROL_HOST:$REMOTE_LOOPS_DIR/" "$LOOPS_DIR/"; then
    log "Successfully synced loops from $CONTROL_HOST"

    # List updated files
    log "Available loop files:"
    ls -la "$LOOPS_DIR"/*.wav 2>/dev/null | while read line; do
        log "  $line"
    done

    # Restart player-loop service if it's running to pick up new files
    if systemctl is-active --quiet player-loop.service; then
        log "Restarting player-loop service to pick up new files"
        systemctl restart player-loop.service
    fi

else
    log "ERROR: Failed to sync loops from $CONTROL_HOST"
    exit 1
fi

log "Loop update completed successfully"
