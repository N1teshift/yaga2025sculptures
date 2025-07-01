#!/bin/bash

echo "=== AUDIO DIAGNOSTICS FOR SCULPTURE $(hostname) ==="
echo "Timestamp: $(date)"
echo

echo "=== 1. HARDWARE DETECTION ==="
echo "Sound cards detected:"
cat /proc/asound/cards
echo

echo "Audio devices in /proc/asound/:"
ls -la /proc/asound/
echo

echo "=== 2. IQAUDIO CODEC STATUS ==="
CARD_NUM=$(grep 'IQaudIOCODEC' /proc/asound/cards | awk '{print $1}')
if [ -n "$CARD_NUM" ]; then
    echo "IQaudIO card number: $CARD_NUM"
    echo "Current mixer settings:"
    amixer -c $CARD_NUM
else
    echo "ERROR: IQaudIO card not found!"
fi
echo

echo "=== 3. ALSA CONFIGURATION ==="
echo "Default ALSA device:"
aplay -l
echo
echo "Current /etc/asound.conf:"
if [ -f /etc/asound.conf ]; then
    cat /etc/asound.conf
else
    echo "No /etc/asound.conf found"
fi
echo

echo "=== 4. PULSEAUDIO STATUS ==="
echo "PulseAudio running for pi user:"
sudo -u pi pulseaudio --check -v
echo
echo "Available sinks:"
sudo -u pi XDG_RUNTIME_DIR=/run/user/1000 pactl list short sinks
echo
echo "Available sources:"
sudo -u pi XDG_RUNTIME_DIR=/run/user/1000 pactl list short sources
echo

echo "=== 5. SERVICE STATUS ==="
systemctl is-active darkice.service
systemctl is-active player-live.service
systemctl is-active player-loop.service
systemctl is-active pi-agent.service
echo

echo "=== 6. RECENT LOGS ==="
echo "MPV Live player logs (last 10 lines):"
tail -n 10 /tmp/mpv-live-*.log 2>/dev/null || echo "No MPV live logs found"
echo

echo "=== 7. AUDIO TEST ==="
echo "Testing audio output with sine wave (5 seconds)..."
timeout 5s sudo -u pi XDG_RUNTIME_DIR=/run/user/1000 pactl load-module module-sine frequency=440 &>/dev/null
sleep 1
sudo -u pi XDG_RUNTIME_DIR=/run/user/1000 pactl unload-module module-sine &>/dev/null
echo "Sine wave test completed"
echo

echo "=== 8. NETWORK CONNECTIVITY ==="
echo "Can reach control server:"
ping -c 1 192.168.8.156 &>/dev/null && echo "OK" || echo "FAILED"
echo

echo "=== DIAGNOSTICS COMPLETE ===" 