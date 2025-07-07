# YAGA 2025 Sculptures Project - TODO List
**Deadline: Less than 48 hours**

## Current Status
- ✅ Fresh Raspberry Pi reflash completed (new router setup)
- 🔄 **IN PROGRESS**: Ansible deployment on edge devices and server node

---

## Phase 1: Core System Testing & Validation
**Priority: HIGH - Must complete after Ansible deployment**

### Service Status Verification
- [ ] **1. Edge node services status and logs**
  - Check pi-agent, darkice, player-live, player-loop services
  - Verify all services are running without errors
  
- [ ] **2. Server node services status and logs**
  - Check server-agent, liquidsoap, icecast, node-red services
  - Verify connectivity and proper operation

### Streaming & Dashboard Testing
- [ ] **3. Icecast mounts and node-red dashboard**
  - Verify all icecast mount points are accessible
  - Confirm Node-RED dashboard loads and displays correctly
  
- [ ] **4. Listen to s1, s2, s3 streams**
  - Test individual sculpture streams (live capture)
  - Verify audio quality and stability
  
- [ ] **5. Listen to mix1, mix2, mix3 streams**
  - Test mixed output streams
  - Verify proper audio routing and mixing

### Control Interface Testing
- [ ] **6. Test Master volume slider**
  - Verify volume changes are applied correctly
  - Check for audio distortion at different levels
  
- [ ] **7. Test Capture slider**
  - Verify input gain control functionality
  - Test impact on captured audio levels

### Media Management Testing
- [ ] **8. Test track selection and playback**
  - Load and play individual tracks
  - Verify proper audio routing for single track playback
  
- [ ] **9. Test playlist loading and selection**
  - Load different playlists
  - Verify playlist management functionality

### System Control Testing
- [ ] **10. Test mute/unmute button**
  - Verify mute functionality for all streams
  - Test unmute restoration
  
- [ ] **11. Test Sculpture restart buttons**
  - Verify individual sculpture service restarts
  - Check service recovery after restart
  
- [ ] **12. Test Plan switching buttons**
  - Test B1, B2, B3 plan switching
  - Verify proper audio routing changes
  
- [ ] **13. Test emergency stop button**
  - Verify all services stop correctly
  - Test system recovery after emergency stop
  
- [ ] **14. Test system restart buttons**
  - Test server and edge device restart functionality
  - Verify services auto-start after restart

### Missing Functionality
- [ ] **15. Add server-agent restart button**
  - Implement restart button for server-agent service
  - Add to Node-RED dashboard

- [ ] **16. Add comprehensive system restart sequence button**
  - Create "Restart All Services" button for complete system recovery
  - **Sequence**: 
    1. **Stop Phase**: Stop all services on server node and edge devices
    2. **Start Phase** (in order):
       - Start `icecast2` (server) - streaming server foundation
       - Start `pi-agent` (edge devices) - core edge device management
       - Start `darkice` (edge devices) - audio capture and streaming
       - Start `liquidsoap` (server) - audio mixing and processing
       - Start `player-live` (edge devices) - default live playback mode
       - Start remaining services (node-red, server-agent, etc.)
  - Implement with proper delays between service starts
  - Add to Node-RED dashboard as emergency recovery option

---

## Phase 2: Audio Configuration & Processing

### Audio Processing Reset
- [ ] **17. Test Audio processing reset to default values**
  - Verify reset functionality works correctly
  - Test that defaults from `audio_config.yml` are applied

### Audio Backend Migration Issues
- [ ] **18. Investigate PulseAudio → ALSA backend issues**
  - **Context**: Recently switched from PulseAudio to ALSA for CPU optimization
  - Test audio capture and playback stability
  - Verify audio device configurations are correct
  - Check for potential CPU performance improvements

### Stereo-to-Mono Conversion
- [ ] **19. Implement stereo capture with mono processing**
  - **Requirement**: Capture stereo from dual-head microphones
  - Convert to mono at first processing checkpoint (simple mix: (L+R)/2)
  - Ensure entire audio chain processes mono after conversion
  - Update audio processing pipeline accordingly

### Dynamic Sample Rate Management
- [ ] **20. Create sample rate update playbooks**
  - Create separate playbook for edge devices audio config updates
  - Create separate playbook for server node audio config updates
  - Include audio file conversion steps for sample rate changes
  - Enable quick 48kHz → lower sample rate switching if needed for production

---

## Phase 3: New Features & Functionality

### Enhanced Plan Switching
- [ ] **21. Investigate and enhance plan switching functionality**
  - **Current Issue**: Server-agent sometimes glitches plan republishing
  - **Goal**: Add live-to-local mode switching capability
  - **Implementation**: Extend B1, B2, B3 buttons to:
    - Stop `player-live` service on designated "silent" sculpture
    - Start `player-loop` service on that sculpture
    - Maintain live connectivity for other two sculptures
  - Test plan button highlighting effects
  - Verify audio routing plan republishing stability

---

## Phase 4: Audio Processing Understanding & Optimization

### Audio Processing Effects Documentation
- [ ] **22. Document and test audio processing slider effects**
  - **Current Status**: Effects seem active (visible in VLC spectral analysis) but audible impact unclear
  - Document expected audible effects for each slider:
    - **Compress Ratio**: Should affect dynamic range compression
    - **Compress Threshold**: Should set compression activation level
    - **Attack/Release Time**: Should affect compression response speed
    - **Highpass/Lowpass Freq**: Should filter frequency ranges
    - **Delay Time/Feedback**: Should add echo/reverb effects
    - **Gate Threshold**: Should cut low-level noise
    - **Normalize Target**: Should adjust overall level
  - Test with better audio monitoring setup (not transducer on metal pot)
  - Verify processing is actually being applied to mixed streams

---

## Phase 5: Production Readiness & Final Testing

### Underrun Monitoring
- [ ] **23. Test underrun problems in production scenarios**
  - Monitor `player-live` service for audio underruns
  - Monitor `player-loop` service for audio underruns
  - Test with current buffer settings (15 seconds mpv_audio_buffer_secs)
  - Verify cache settings (60 seconds mpv_cache_secs) are adequate

### Server-Agent Connectivity & Auto-Recovery
- [ ] **24. Server-agent debugging and auto-recovery implementation**
  - **Current Issue**: Server-agent fails to connect to Raspberry Pis
  - Debug connectivity issues between server and edge devices
  - Implement automatic service restart logic
  - Create healing procedures for common failure scenarios
  - **Note**: Not critical for production but valuable for autonomous operation

---

## Configuration Files & Settings

### Key Configuration
- Audio sample rate: **48kHz** (configurable via `audio_config.yml`)
- Audio channels: **1 (mono)** after initial stereo-to-mono conversion
- Audio backend: **ALSA** (recently switched from PulseAudio)
- Buffer settings: 15s audio buffer, 60s cache, 20MB demuxer max

### Critical Files
- `audio_config.yml` - Central audio configuration
- `playlists.yml` - Playlist definitions
- Edge device services: pi-agent, darkice, player-live, player-loop
- Server services: server-agent, liquidsoap, icecast, node-red

---

## Notes
- **Time Constraint**: Less than 48 hours to completion
- **Current Focus**: Ansible deployment completion before testing phase
- **Testing Environment**: May need better audio monitoring setup for processing effects
- **Production Priority**: Focus on stability and core functionality over advanced features
