# Legacy Flow Construction Files

This directory contains the **old** Node-RED flow construction system that has been **replaced** by the new modular architecture.

## ⚠️ **DO NOT USE THESE FILES** ⚠️

These files are kept for historical reference only and are **NOT** used in the current system.

## Old Files (Legacy - Not Used)

- **`part1.json.j2`** - Old monolithic flow part 1 (replaced by `core/` components)
- **`part2.json.j2`** - Old monolithic flow part 2 (replaced by `sculpture/` components)
- **`sculpture_gauges.json.j2`** - Old gauge definitions (replaced by `sculpture/gauges.json.j2`)
- **`sculpture_restart_buttons.json.j2`** - Old restart buttons (replaced by `sculpture/restart_buttons.json.j2`)

## Current Active System

The **NEW** modular system is organized in:

```
flow_parts/
├── core/           # Core system components (MQTT, UI setup, startup)
├── system/         # System-wide controls (plans, emergency stop, restarts)  
├── sculpture/      # Per-sculpture components (gauges, controls, tracks)
└── old/           # ← YOU ARE HERE (legacy files)
```

See `../ARCHITECTURE.md` for complete documentation of the current modular system.

## Migration History

These legacy files were moved to this directory to clearly separate the old structure from the new modular architecture. The current system maintains full backward compatibility while improving maintainability and organization. 