#!/bin/bash

# Audio optimization script for Raspberry Pi sculptures
# This script optimizes system settings to prevent audio underruns

echo "=== AUDIO OPTIMIZATION SCRIPT ==="
echo "Optimizing system for better audio performance..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Set higher priority for audio processes
echo "Setting audio thread priorities..."
if [ -f /proc/sys/kernel/sched_rt_runtime_us ]; then
    echo 950000 > /proc/sys/kernel/sched_rt_runtime_us
    echo "Real-time scheduling enabled"
fi

# Optimize CPU governor for consistent performance
echo "Setting CPU governor to performance mode..."
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
echo performance > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor 2>/dev/null
echo performance > /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor 2>/dev/null
echo performance > /sys/devices/system/cpu/cpu3/cpufreq/scaling_governor 2>/dev/null

# Increase audio buffer sizes at kernel level
echo "Optimizing kernel audio buffers..."
if [ -f /proc/sys/kernel/sched_latency_ns ]; then
    echo 1000000 > /proc/sys/kernel/sched_latency_ns
fi

if [ -f /proc/sys/kernel/sched_min_granularity_ns ]; then
    echo 100000 > /proc/sys/kernel/sched_min_granularity_ns
fi

# Optimize memory settings for audio
echo "Optimizing memory settings..."
echo 1 > /proc/sys/vm/swappiness
echo 50 > /proc/sys/vm/vfs_cache_pressure

# Set audio process nice levels
echo "Setting process priorities..."
pgrep -f "mpv.*sculpture" | while read pid; do
    ionice -c 1 -n 4 -p $pid 2>/dev/null
    renice -10 $pid 2>/dev/null
done

# Optimize PulseAudio if running
if pgrep -f pulseaudio > /dev/null; then
    echo "Optimizing PulseAudio processes..."
    pgrep -f pulseaudio | while read pid; do
        ionice -c 1 -n 4 -p $pid 2>/dev/null
        renice -15 $pid 2>/dev/null
    done
fi

# Check and optimize ALSA buffer settings
echo "Checking ALSA buffer settings..."
CARD_NUM=$(grep 'IQaudIOCODEC' /proc/asound/cards | awk '{print $1}')
if [ -n "$CARD_NUM" ]; then
    echo "Found IQaudIO card at $CARD_NUM"
    # Set optimal buffer sizes for the IQaudIO card
    echo 2048 > /proc/asound/card$CARD_NUM/pcm0p/sub0/prealloc 2>/dev/null
    echo 4096 > /proc/asound/card$CARD_NUM/pcm0p/sub0/prealloc_max 2>/dev/null
    echo "ALSA buffer optimization completed"
fi

# Disable power saving features that might cause audio interruptions
echo "Disabling power saving features..."
echo 0 > /sys/module/snd_hda_intel/parameters/power_save 2>/dev/null
echo 0 > /sys/module/snd_ac97_codec/parameters/power_save 2>/dev/null

# USB audio optimizations (if applicable)
echo "Applying USB audio optimizations..."
echo 0 > /sys/module/usbcore/parameters/autosuspend 2>/dev/null

# Network optimizations to reduce system load
echo "Optimizing network settings..."
echo 1 > /proc/sys/net/core/netdev_budget_usecs 2>/dev/null
echo 300 > /proc/sys/net/core/netdev_max_backlog 2>/dev/null

# Create a systemd service to apply these optimizations on boot
cat > /etc/systemd/system/audio-optimize.service << EOF
[Unit]
Description=Audio Performance Optimization
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/opt/sculpture-system/optimize_audio.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl enable audio-optimize.service

echo "=== AUDIO OPTIMIZATION COMPLETE ==="
echo "System has been optimized for better audio performance"
echo "Reboot recommended for all changes to take effect"
echo "The optimization service will run automatically on boot" 