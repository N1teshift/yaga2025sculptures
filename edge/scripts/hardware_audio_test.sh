#!/bin/bash

echo "=== HARDWARE AUDIO TEST FOR $(hostname) ==="
echo "This script tests direct ALSA output to isolate hardware issues"
echo

# Find IQaudIO card
CARD_NUM=$(grep 'IQaudIOCODEC' /proc/asound/cards | awk '{print $1}')
if [ -z "$CARD_NUM" ]; then
    echo "ERROR: IQaudIO card not found!"
    exit 1
fi

echo "Found IQaudIO card at index: $CARD_NUM"
echo

# Test 1: Generate sine wave directly to hardware
echo "=== TEST 1: Direct ALSA sine wave (440Hz for 3 seconds) ==="
echo "If you hear a tone, hardware + basic drivers are working"
speaker-test -c 2 -t sine -f 440 -l 1 -s 1 -D hw:$CARD_NUM,0 &
sleep 3
killall speaker-test 2>/dev/null
echo

# Test 2: Test with aplay
echo "=== TEST 2: Playing sample through ALSA (if available) ==="
if [ -f /opt/sculpture-system/test1.wav ]; then
    aplay -D hw:$CARD_NUM,0 /opt/sculpture-system/test1.wav
else
    echo "No test sample found at /opt/sculpture-system/test1.wav"
fi
echo

# Test 3: Check mixer levels
echo "=== TEST 3: Current mixer control levels ==="
echo "Lineout control:"
amixer -c $CARD_NUM get Lineout
echo
echo "Headphone control:"
amixer -c $CARD_NUM get Headphone
echo
echo "DAC controls:"
amixer -c $CARD_NUM get 'Mixout Left DAC Left' 2>/dev/null || echo "Left DAC control not found"
amixer -c $CARD_NUM get 'Mixout Right DAC Right' 2>/dev/null || echo "Right DAC control not found"
echo

echo "=== Hardware test complete ==="
echo "If you heard audio in tests 1 or 2, hardware is likely OK"
echo "If no audio, check physical connections and power" 