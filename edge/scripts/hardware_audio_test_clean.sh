#!/bin/bash

echo "=== CLEAN HARDWARE AUDIO TEST FOR $(hostname) ==="
echo "This script stops services and tests direct ALSA output"
echo

# Find IQaudIO card
CARD_NUM=$(grep 'IQaudIOCODEC' /proc/asound/cards | awk '{print $1}')
if [ -z "$CARD_NUM" ]; then
    echo "ERROR: IQaudIO card not found!"
    exit 1
fi

echo "Found IQaudIO card at index: $CARD_NUM"
echo

# Stop audio services to free the device
echo "=== Stopping audio services temporarily ==="
systemctl stop player-live.service
systemctl stop player-loop.service  
systemctl stop darkice.service
sleep 2

# Kill any remaining audio processes
killall mpv 2>/dev/null
killall darkice 2>/dev/null
sleep 1

echo "Services stopped. Testing hardware directly..."
echo

# Test 1: Check mixer controls properly
echo "=== TEST 1: Current mixer control levels ==="
echo "Lineout control:"
amixer -c $CARD_NUM get Lineout 2>/dev/null || echo "Lineout control not found"
echo
echo "Headphone control:"
amixer -c $CARD_NUM get Headphone 2>/dev/null || echo "Headphone control not found"
echo
echo "DAC controls:"
amixer -c $CARD_NUM get 'Mixout Left DAC Left' 2>/dev/null || echo "Left DAC control not found"
amixer -c $CARD_NUM get 'Mixout Right DAC Right' 2>/dev/null || echo "Right DAC control not found"
echo

# Test 2: Generate sine wave directly to hardware
echo "=== TEST 2: Direct ALSA sine wave (440Hz for 5 seconds) ==="
echo "Listen carefully for audio output..."
timeout 5s speaker-test -c 2 -t sine -f 440 -l 1 -s 1 -D hw:$CARD_NUM,0 2>/dev/null &
sleep 5
killall speaker-test 2>/dev/null
echo "Sine wave test completed"
echo

# Test 3: Test different frequencies
echo "=== TEST 3: Testing different frequencies ==="
for freq in 220 440 880; do
    echo "Testing ${freq}Hz for 2 seconds..."
    timeout 2s speaker-test -c 1 -t sine -f $freq -l 1 -s 1 -D hw:$CARD_NUM,0 >/dev/null 2>&1 &
    sleep 2
    killall speaker-test 2>/dev/null
done
echo

# Test 4: Check if audio device responds
echo "=== TEST 4: Audio device response test ==="
if aplay -D hw:$CARD_NUM,0 --dump-hw-params /dev/zero 2>&1 | head -5; then
    echo "Audio device is responding to requests"
else
    echo "Audio device is not responding properly"
fi
echo

# Restart services
echo "=== Restarting audio services ==="
systemctl start darkice.service
systemctl start player-live.service
echo

echo "=== HARDWARE TEST COMPLETE ==="
echo "If you heard tones during tests 2-3, hardware is working"
echo "If no audio, check physical connections, power, and amplifier" 