# Pi-Agent Refactoring Summary

## Problem
The original `pi-agent.py` file had grown to almost 400 lines with multiple responsibilities mixed together, making it difficult to maintain, test, and extend.

## Solution
Refactored the monolithic script into **4 focused modules** following the Single Responsibility Principle:

### 1. `audio_manager.py` (130 lines)
**Responsibility**: All audio-related operations
- Volume control (`set_volume`)
- Mute/unmute functionality (`set_mute`, `get_mute_status`)
- Audio level monitoring (`get_microphone_level`, `get_output_level`)
- Audio configuration management (`_load_audio_config`)
- PulseAudio environment handling (`get_pactl_env`)

### 2. `system_manager.py` (140 lines)
**Responsibility**: System service management and mode switching
- Mode switching (`switch_to_live_mode`, `switch_to_local_mode`)
- Service control (`stop_all_services`, `restart_darkice`, `restart_all_services`)
- Track management (`get_available_tracks`, `update_loop_track`)
- Systemd service file manipulation

### 3. `status_collector.py` (70 lines)
**Responsibility**: System status monitoring
- CPU usage collection (`get_cpu_usage`)
- Temperature monitoring (`get_temperature`)
- Status object construction (`build_status`)
- Error handling and reporting

### 4. `pi-agent.py` (160 lines)
**Responsibility**: MQTT communication and orchestration
- MQTT client management
- Message routing to appropriate managers
- Component coordination
- Main application loop

## Benefits

### 1. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- Changes to audio logic don't affect system management
- Easier to understand and reason about code

### 2. **Improved Testability**
- Individual components can be unit tested in isolation
- Mock dependencies easily for testing
- Clear interfaces between components

### 3. **Better Maintainability**
- Smaller, focused files are easier to work with
- Clear dependency relationships
- Reduced cognitive load when making changes

### 4. **Enhanced Reusability**
- Audio management can be reused in other projects
- System management logic is portable
- Status collection can be extended independently

### 5. **Easier Extension**
- Adding new audio features only requires changes to `AudioManager`
- New system services can be added to `SystemManager`
- Additional status metrics go in `StatusCollector`

### 6. **Enhanced Restart Functionality**
- The new `restart_all_services()` function properly restarts all services
- Correct shutdown/startup order: stop audio services → restart darkice → restart appropriate player service → restart pi-agent
- Respects current mode when restarting (live/local/idle)

## Migration Path

1. **Development**: Use `pi-agent-refactored.py` alongside the new modules
2. **Testing**: Verify all functionality works with the new structure
3. **Deployment**: Replace `pi-agent.py` with the refactored version
4. **Cleanup**: Archive the original monolithic file

## File Size Comparison

| File | Lines | Responsibility |
|------|-------|----------------|
| **Original** | | |
| `pi-agent.py` | 398 | Everything |
| **Refactored** | | |
| `audio_manager.py` | 130 | Audio operations |
| `system_manager.py` | 140 | System management |
| `status_collector.py` | 70 | Status monitoring |
| `pi-agent.py` | 160 | MQTT & orchestration |
| **Total** | **500** | **Separated concerns** |

*Note: The refactored version has slightly more lines due to proper error handling, documentation, and cleaner interfaces, but is much more maintainable.*

## Automated Configuration System

The system uses **Ansible Jinja2 templates** to automatically populate audio settings directly into Python code:

### Template Files:
- `templates/audio_manager.py.j2` - Audio operations with templated config
- `templates/system_manager.py.j2` - System management with templated fallbacks
- `templates/pi-agent.py.j2` - Main orchestrator
- `scripts/status_collector.py` - Status monitoring (no templating needed)

### How It Works:
1. **Edit `all.yml`** - Change `audio_sample_rate`, `darkice_quality`, etc.
2. **Run Ansible** - Templates Python files with your values automatically
3. **Deploy** - Everything uses the same consistent settings
4. **No config files** - Audio settings are built directly into the code

### Example Configuration Flow:
```yaml
# all.yml
audio_sample_rate: 48000  # Change this once...
```

Gets automatically populated into:
- `audio_manager.py` → `'samplerate': '48000'` (built-in)
- `system_manager.py` → `'samplerate': '48000'` (fallback values)

### Benefits of Direct Templating:
✅ **Simpler deployment** - No separate config files to manage  
✅ **Faster startup** - No file I/O for configuration loading  
✅ **Fewer dependencies** - No configparser module needed  
✅ **Atomic configuration** - All settings embedded at deploy time  
✅ **No runtime config drift** - Settings can't be accidentally changed  

### File Structure:
```
edge/
├── ansible/
│   └── templates/          # Jinja2 templates (.j2 files)
│       ├── audio_manager.py.j2
│       ├── system_manager.py.j2
│       └── pi-agent.py.j2
└── scripts/
    ├── status_collector.py  # No templating needed
    └── pi-agent_old.py     # Original monolithic version
```

**Deployment Flow**: `all.yml` → Ansible → `.j2 templates` → Generated `.py files` on Pi 