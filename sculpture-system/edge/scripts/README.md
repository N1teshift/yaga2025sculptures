# Edge Device Scripts

This directory contains utility scripts for Raspberry Pi sculpture devices. These scripts are deployed to each sculpture device during Ansible installation and provide diagnostic, testing, and optimization capabilities.

## Scripts Overview

### `audio_diagnostics.sh`
**Purpose**: Comprehensive audio system diagnostics and troubleshooting

**Usage**: 
```bash
sudo /opt/sculpture-system/audio_diagnostics.sh
```

**Features**:
- Hardware detection (sound cards, IQaudIO codec status)
- ALSA configuration validation
- Service status checking (darkice, player-live, player-loop, pi-agent)
- Audio routing and mixer control analysis
- Network streaming status
- Disk space and log file inspection
- System load and memory usage

**When to Use**: 
- Troubleshooting audio issues
- Initial setup verification
- Regular system health checks
- Before and after configuration changes

### `hardware_audio_test.sh`
**Purpose**: Direct hardware audio testing to isolate hardware vs software issues

**Usage**:
```bash
/opt/sculpture-system/hardware_audio_test.sh
```

**Features**:
- Direct ALSA hardware testing with sine wave generation
- Test file playback through hardware layer
- Bypasses complex audio routing for basic functionality verification
- Identifies whether issues are at hardware/driver level

**When to Use**:
- Suspected hardware problems
- New installation verification  
- When audio_diagnostics shows software is configured correctly but no audio output
- Driver installation verification

**What You Should Hear**: 
- Test 1: 440Hz sine wave for 3 seconds
- Test 2: Test audio file playback (if available)

### `optimize_audio.sh`
**Purpose**: System-level optimization for consistent audio performance

**Usage**:
```bash
sudo /opt/sculpture-system/optimize_audio.sh
```

**Features**:
- CPU governor optimization (performance mode)
- Real-time scheduling configuration
- Kernel audio buffer optimization
- Memory and swap tuning for audio workloads
- USB and network latency reduction
- GPU memory split optimization for audio focus
- Creates systemd service for persistent optimizations

**When to Use**:
- Initial system setup (automatically run by Ansible)
- After system updates that might reset CPU governor
- When experiencing audio dropouts or underruns
- Performance troubleshooting

**Effects**:
- Reduces audio underruns and dropouts
- Provides more consistent audio latency
- Prioritizes audio processing over other system tasks
- May increase power consumption but improves audio reliability

## Deployment

These scripts are automatically deployed by the Ansible playbook to `/opt/sculpture-system/` on each Raspberry Pi device. They are copied with appropriate executable permissions and can be run locally on each sculpture device for maintenance and troubleshooting.

## Troubleshooting Workflow

1. **Start with `audio_diagnostics.sh`**: Get overall system status
2. **If software looks good but no audio**: Run `hardware_audio_test.sh`
3. **If experiencing dropouts/underruns**: Run `optimize_audio.sh`
4. **Repeat diagnostics**: Verify improvements with `audio_diagnostics.sh`

## Dependencies

- **IQaudIO codec**: All scripts assume IQaudIO audio HAT
- **ALSA tools**: amixer, aplay, speaker-test
- **systemctl**: For service management
- **Standard Linux utilities**: grep, awk, ps, df, etc.

## Output and Logging

Scripts output detailed information to stdout and can be redirected to log files for analysis:

```bash
# Save diagnostics to file
sudo /opt/sculpture-system/audio_diagnostics.sh > /tmp/audio_diag_$(date +%Y%m%d_%H%M).log 2>&1

# Run optimization and log results  
sudo /opt/sculpture-system/optimize_audio.sh > /tmp/audio_opt_$(date +%Y%m%d_%H%M).log 2>&1
```