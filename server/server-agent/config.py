#!/usr/bin/env python3
"""
Configuration module for server-agent
Contains all configuration constants and default values
"""

import os
import re
from collections import defaultdict, deque

# MQTT Configuration
MQTT_BROKER = os.environ.get('CONTROL_HOST', 'localhost')
MQTT_PORT = 1883
CMD_TOPIC = "server/cmd"
STATUS_TOPIC = "system/status"
PLAN_TOPIC = "system/plan"
UNDERRUN_TOPIC = "system/underruns"
DARKICE_TOPIC = "system/darkice"

# Liquidsoap telnet configuration
LIQUIDSOAP_HOST = 'localhost'
LIQUIDSOAP_PORT = 1234

# Plan state management
PLAN_STATE_FILE = "/tmp/current_plan.json"
DEFAULT_PLAN = "A1"

# Underrun monitoring configuration - Enhanced with multiple connection methods
PI_SYSTEMS = [
    {
        "name": "sculpture1", 
        "hosts": ["sculpture1.local", "sculpture1", "192.168.8.158"],  # Multiple connection options
        "user": "pi"
    },
    {
        "name": "sculpture2", 
        "hosts": ["sculpture2.local", "sculpture2", "192.168.8.155"], 
        "user": "pi"
    },
    {
        "name": "sculpture3", 
        "hosts": ["sculpture3.local", "sculpture3", "192.168.8.157"], 
        "user": "pi"
    },
    # Add more systems as needed
]

# Services to monitor for underruns
MONITORED_SERVICES = ["player-live", "player-loop"]

# Services to monitor for darkice buffer overruns
DARKICE_SERVICES = ["darkice"]

# Connection configuration
CONNECTION_CONFIG = {
    'ssh_timeout': 15,
    'connection_retry_interval': 30,  # seconds between connection attempts
    'max_connection_attempts': 3,
    'ssh_key_file': None,  # None for default, or specify path
    'test_connection': True,  # Test connection before starting monitoring
    'heartbeat_interval': 30,  # seconds between heartbeat logs
}

# Paths to logs you want to tail
LOG_PATHS = {
    "icecast2": "/var/log/icecast2/icecast.log",
    "liquidsoap": "/var/log/liquidsoap.log",
    "mqtt_to_telnet_bridge": "/var/log/mqtt_to_telnet_bridge.log"
}

# Darkice restart configuration
DARKICE_CONFIG = {
    'max_restart_attempts': 5,
    'restart_cooldown': 60,  # seconds between restart attempts
    'buffer_overrun_threshold': 5,  # trigger restart after this many buffer overruns in short time
    'overrun_spam_threshold': 10,  # consider it spam if more than this many in 30 seconds
    'overrun_spam_window': 30,  # seconds
    'force_kill_timeout': 10  # seconds to wait before force killing
}

# Underrun detection patterns - specifically for MPV audio issues
UNDERRUN_PATTERNS = [
    re.compile(r'Audio device underrun detected\.', re.IGNORECASE),
    re.compile(r'\[ao/pulse\] audio end or underrun', re.IGNORECASE),
    re.compile(r'\[cplayer\] restarting audio after underrun', re.IGNORECASE),
    re.compile(r'audio underrun', re.IGNORECASE),
    re.compile(r'buffer underrun', re.IGNORECASE),
    re.compile(r'ao_pulse.*underrun', re.IGNORECASE),
]

# Logging configuration
LOG_LEVEL = "DEBUG"
LOG_FORMAT = '%(asctime)s %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%H:%M'

# Status publishing interval
STATUS_PUBLISH_INTERVAL = 30  # seconds

# Data structures for tracking statistics
def create_underrun_stats():
    """Create the underrun statistics data structure"""
    return defaultdict(lambda: defaultdict(lambda: {
        'count': 0,
        'last_underrun': None,
        'recent_underruns': deque(maxlen=100)  # Keep last 100 underruns
    }))

def create_darkice_stats():
    """Create the darkice statistics data structure"""
    return defaultdict(lambda: defaultdict(lambda: {
        'buffer_overrun_count': 0,
        'last_buffer_overrun': None,
        'recent_buffer_overruns': deque(maxlen=50),  # Keep last 50 buffer overruns
        'restart_attempts': 0,
        'last_restart_attempt': None,
        'consecutive_overruns': 0,
        'overrun_spam_detected': False
    }))

# Valid plan options
VALID_PLANS = ['A1', 'A2', 'B1', 'B2', 'B3', 'C', 'D']

def load_config_overrides():
    """Load configuration overrides from config.py if it exists"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_overrides", "config.py")
        if spec and spec.loader:
            config_overrides = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_overrides)
            
            # Override default values with values from config.py
            globals().update({
                name: getattr(config_overrides, name)
                for name in dir(config_overrides)
                if not name.startswith('_') and name in globals()
            })
    except (ImportError, FileNotFoundError):
        pass  # Use defaults if config.py doesn't exist 