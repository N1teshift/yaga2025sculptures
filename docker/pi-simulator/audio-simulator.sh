#!/bin/bash

# Audio simulator for Docker-based sculpture testing
# Generates different audio patterns for each sculpture

set -e

echo "Starting audio simulator for Sculpture $SCULPTURE_ID"

# Configure PulseAudio
export PULSE_RUNTIME_PATH=/tmp/pulse-runtime
mkdir -p $PULSE_RUNTIME_PATH

# Start PulseAudio in system mode
pulseaudio --system --disallow-exit --disallow-module-loading=false &
sleep 2

# Generate audio based on sculpture ID
case "$SCULPTURE_ID" in
    1)
        FREQ=440    # A4 note
        PATTERN="sine"
        echo "Sculpture 1: Generating 440Hz sine wave"
        ;;
    2)
        FREQ=880    # A5 note  
        PATTERN="square"
        echo "Sculpture 2: Generating 880Hz square wave"
        ;;
    3)
        FREQ=1320   # E6 note
        PATTERN="sawtooth"
        echo "Sculpture 3: Generating 1320Hz sawtooth wave"
        ;;
    *)
        FREQ=440
        PATTERN="sine"
        echo "Default: Generating 440Hz sine wave"
        ;;
esac

# Create a continuous audio stream
while true; do
    # Generate 30 seconds of audio with some variation
    CURRENT_FREQ=$((FREQ + (RANDOM % 100) - 50))  # Add some frequency variation
    
    echo "Generating audio: ${CURRENT_FREQ}Hz ${PATTERN} wave"
    
    # Generate audio and pipe to PulseAudio
    ffmpeg -f lavfi -i "${PATTERN}=frequency=${CURRENT_FREQ}:duration=30" \
           -f pulse -ac 1 -ar 44100 \
           sculpture_source 2>/dev/null &
    
    # Wait and add some silence for realism
    sleep 25
    
    # Add 5 seconds of quiet (simulating ambient noise)
    ffmpeg -f lavfi -i "anoisesrc=duration=5:color=white:amplitude=0.1" \
           -f pulse -ac 1 -ar 44100 \
           sculpture_source 2>/dev/null &
    
    sleep 5
done 