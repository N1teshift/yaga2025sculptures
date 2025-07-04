# Node-RED Flow Architecture

## Overview

This Node-RED flow has been completely reorganized into a modular, maintainable structure with focused components under 200 lines each. The flow is organized into three main categories: **Core**, **System Control**, and **Sculpture Components**.

## Directory Structure

```
flow_parts/
├── core/
│   ├── config.json.j2           # MQTT broker, UI tabs, basic setup
│   ├── startup.json.j2          # Initial volume/capture value injection
│   └── dashboard.json.j2        # Dashboard connection and track fetching
├── system/
│   ├── plan_buttons.json.j2     # Plan selection buttons (A1, A2, B1, etc.)
│   ├── plan_logic.json.j2       # Plan highlighting and broadcast logic
│   ├── emergency_stop.json.j2   # Emergency stop functionality
│   └── system_restart_buttons.json.j2  # Icecast2/Liquidsoap restart
└── sculpture/
    ├── mqtt_inputs.json.j2      # MQTT subscriptions for sculpture data
    ├── controls.json.j2         # Volume/capture sliders, mute, mode display
    ├── tracks.json.j2           # Track selection dropdown and load button
    ├── gauges.json.j2           # CPU, temp, mic, output level gauges
    └── restart_buttons.json.j2  # Per-sculpture service restart buttons
```

## Component Details

### Core Components

#### `config.json.j2` (47 lines)
- MQTT broker configuration (localhost:1883)
- Main UI tab definition ("Sculpture System")
- System Control UI group
- Basic dashboard structure

#### `startup.json.j2` (26 lines)
- Initial volume injection (0.5) at 1.5s delay
- Initial capture injection (0.5) at 2.0s delay
- Link out nodes to distribute to all sculptures

#### `dashboard.json.j2` (42 lines)
- Dashboard connection listener
- Plan highlight on connect logic
- Track list fetching on startup
- Initial system state setup

### System Control Components

#### `plan_buttons.json.j2` (182 lines)
- Plan selection buttons (A1, A2, B1, B2, B3, etc.)
- Plan highlighting and state management
- MQTT broadcast to all sculptures

#### `plan_logic.json.j2` (73 lines)
- Plan broadcast and highlighting logic
- Flow context management for current plan
- UI button state synchronization

#### `emergency_stop.json.j2` (55 lines)
- Emergency stop button
- System-wide shutdown commands
- Safety override functionality

#### `system_restart_buttons.json.j2` (61 lines)
- Icecast2 restart button
- Liquidsoap restart button
- Server-level service management

### Sculpture Components (Per Sculpture: 1, 2, 3)

#### `mqtt_inputs.json.j2` (64 lines)
- MQTT subscriptions for each sculpture:
  - `sculpture/{id}/status` → Status parser
  - `sculpture/{id}/mode` → Mode display
  - `sculpture/{id}/mute` → Mute state
  - `sculpture/{id}/tracks` → Track list updates

#### `controls.json.j2` (174 lines per sculpture)
Each sculpture gets:
- **UI Group**: Sculpture {id} group container
- **Volume Slider**: Master volume (0-1, 0.01 steps)
- **Capture Slider**: Capture level (0-1, 0.01 steps)
- **Mode Display**: Current operation mode
- **Mute Button**: Toggle mute state with visual feedback
- **Command Formatting**: JSON command preparation
- **MQTT Output**: Commands to `sculpture/{id}/cmd`

#### `tracks.json.j2` (66 lines per sculpture)
Each sculpture gets:
- **Track Dropdown**: Dynamic track selection
- **Load Button**: Load selected track
- **Track Logic**: Flow context management
- **Track List Updates**: Dynamic option population

#### `gauges.json.j2` (95 lines per sculpture)
Each sculpture gets 4 gauges:
- **CPU Gauge**: 0-100%, green/yellow/red zones (50%/80%)
- **Temperature Gauge**: 0-85°C, green/yellow/red zones (60°C/75°C)
- **Microphone Gauge**: -60 to 0 dB, red/yellow/green zones (-40/-20 dB)
- **Output Gauge**: -60 to 0 dB, red/yellow/green zones (-40/-20 dB)
- **Status Parser**: Routes incoming status to appropriate gauges

#### `restart_buttons.json.j2` (85 lines per sculpture)
Each sculpture gets restart buttons for:
- **Liquidsoap** (red background)
- **Darkice** (orange background)
- **Player Live** (blue background)
- **Player Loop** (purple background)
- **Reboot Pi** (dark red background)

## Flow Generation

The main `flow.json.j2` template includes all components in logical order:

```jinja2
[
    // === CORE COMPONENTS ===
    {% include "flow_parts/core/config.json.j2" %},
    {% include "flow_parts/core/startup.json.j2" %},
    {% include "flow_parts/core/dashboard.json.j2" %},
    
    // === SYSTEM CONTROL COMPONENTS ===
    {% include "flow_parts/system/plan_buttons.json.j2" %},
    {% include "flow_parts/system/plan_logic.json.j2" %},
    {% include "flow_parts/system/emergency_stop.json.j2" %},
    {% include "flow_parts/system/system_restart_buttons.json.j2" %},
    
    // === SCULPTURE COMPONENTS ===
    {% include "flow_parts/sculpture/mqtt_inputs.json.j2" %},
    {% include "flow_parts/sculpture/controls.json.j2" %},
    {% include "flow_parts/sculpture/tracks.json.j2" %},
    {% include "flow_parts/sculpture/gauges.json.j2" %},
    {% include "flow_parts/sculpture/restart_buttons.json.j2" %}
]
```

## Benefits of New Architecture

### 🔧 **Maintainability**
- Each component under 200 lines
- Single responsibility principle
- Easy to locate specific functionality

### 🚀 **Scalability** 
- Add new sculptures by incrementing loop
- Add new gauge types in single file
- Extend system controls independently

### 🧪 **Testability**
- Test individual components in isolation
- Clear separation of concerns
- Predictable data flow

### 📚 **Documentation**
- Self-documenting structure
- Component purpose clear from filename
- Logical grouping of related functionality

### 🔄 **Reusability**
- Sculpture components are templates
- System components can be extended
- Core components are foundational

## Migration Notes

The new structure maintains full backward compatibility with existing MQTT topics and command structures. All existing functionality has been preserved while improving organization and maintainability.

### Old vs New Structure
- `part1.json.j2` → Split into `core/` components
- `part2.json.j2` → Split into `sculpture/` components  
- `sculpture_gauges.json.j2` → `sculpture/gauges.json.j2`
- `sculpture_restart_buttons.json.j2` → `sculpture/restart_buttons.json.j2`
- System components remained in `system/` directory

## Adding New Features

### New Sculpture Component
1. Create new file in `sculpture/` directory
2. Use Jinja2 loop: `{% for sculpture_id in [1, 2, 3] %}`
3. Add include to main `flow.json.j2`

### New System Feature
1. Create new file in `system/` directory
2. Add include to main `flow.json.j2`
3. Update UI group order as needed

### New Core Feature  
1. Create new file in `core/` directory
2. Add include to main `flow.json.j2`
3. Consider startup sequence timing 