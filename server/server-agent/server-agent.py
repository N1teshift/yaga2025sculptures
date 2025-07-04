#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import subprocess
import threading
import time
import json
import os
import socket
import logging
import re
import signal
from datetime import datetime, timedelta
from collections import defaultdict, deque
import paramiko

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
current_plan = "A1"  # Default plan
plan_state_file = "/tmp/current_plan.json"

# Underrun monitoring configuration
PI_SYSTEMS = [
    {"name": "sculpture1", "host": "sculpture1.local", "user": "pi"},
    {"name": "sculpture2", "host": "sculpture2.local", "user": "pi"},
    {"name": "sculpture3", "host": "sculpture3.local", "user": "pi"},
    # Add more systems as needed
]

# Services to monitor for underruns
MONITORED_SERVICES = ["player-live", "player-loop"]

# Services to monitor for darkice buffer overruns
DARKICE_SERVICES = ["darkice"]

# Underrun tracking
underrun_stats = defaultdict(lambda: defaultdict(lambda: {
    'count': 0,
    'last_underrun': None,
    'recent_underruns': deque(maxlen=100)  # Keep last 100 underruns
}))

# Darkice buffer overrun tracking
darkice_stats = defaultdict(lambda: defaultdict(lambda: {
    'buffer_overrun_count': 0,
    'last_buffer_overrun': None,
    'recent_buffer_overruns': deque(maxlen=50),  # Keep last 50 buffer overruns
    'restart_attempts': 0,
    'last_restart_attempt': None,
    'consecutive_overruns': 0,
    'overrun_spam_detected': False
}))

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

class DarkiceMonitor:
    """Monitor darkice services for buffer overrun issues and handle restarts."""
    
    def __init__(self, pi_systems):
        self.pi_systems = pi_systems
        self.ssh_connections = {}
        self.monitoring_threads = {}
        self.buffer_overrun_pattern = re.compile(r'buffer overrun', re.IGNORECASE)
        self.restart_locks = defaultdict(threading.Lock)  # Per-system restart locks
        
    def setup_ssh_connection(self, system):
        """Setup SSH connection to a Pi system."""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                system['host'], 
                username=system['user'],
                timeout=10,
                # Add key-based auth if needed
                # key_filename='/path/to/key'
            )
            self.ssh_connections[system['name']] = ssh
            logger.info(f"SSH connection established to {system['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {system['name']}: {e}")
            return False
    
    def monitor_darkice_service(self, system_name, service):
        """Monitor darkice service for buffer overrun issues."""
        ssh = self.ssh_connections.get(system_name)
        if not ssh:
            return
            
        try:
            # Use journalctl to follow the service logs
            command = f"journalctl -u {service} -f -o cat --no-hostname"
            stdin, stdout, stderr = ssh.exec_command(command)
            
            logger.info(f"Started monitoring {service} on {system_name}")
            
            for line in iter(stdout.readline, ""):
                line = line.strip()
                if not line:
                    continue
                    
                # Check for buffer overrun patterns
                if self.buffer_overrun_pattern.search(line):
                    self.handle_buffer_overrun(system_name, service, line)
                    
        except Exception as e:
            logger.error(f"Error monitoring {service} on {system_name}: {e}")
    
    def handle_buffer_overrun(self, system_name, service, log_line):
        """Handle buffer overrun detection and restart logic."""
        timestamp = datetime.now()
        
        # Update stats
        stats = darkice_stats[system_name][service]
        stats['buffer_overrun_count'] += 1
        stats['last_buffer_overrun'] = timestamp
        stats['recent_buffer_overruns'].append({
            'timestamp': timestamp,
            'log_line': log_line
        })
        stats['consecutive_overruns'] += 1
        
        # Check for spam condition
        recent_window = timestamp - timedelta(seconds=DARKICE_CONFIG['overrun_spam_window'])
        recent_count = sum(1 for overrun in stats['recent_buffer_overruns'] 
                          if overrun['timestamp'] > recent_window)
        
        if recent_count >= DARKICE_CONFIG['overrun_spam_threshold']:
            stats['overrun_spam_detected'] = True
            logger.warning(f"BUFFER OVERRUN SPAM detected on {system_name}/{service} - {recent_count} overruns in {DARKICE_CONFIG['overrun_spam_window']}s")
        
        # Log the buffer overrun
        logger.warning(f"BUFFER OVERRUN detected - {system_name}/{service}: consecutive={stats['consecutive_overruns']}, recent={recent_count}")
        
        # Publish to MQTT
        self.publish_buffer_overrun_event(system_name, service, timestamp, log_line, stats)
        
        # Check if restart is needed
        if (stats['consecutive_overruns'] >= DARKICE_CONFIG['buffer_overrun_threshold'] or 
            stats['overrun_spam_detected']):
            self.trigger_darkice_restart(system_name, service)
    
    def trigger_darkice_restart(self, system_name, service):
        """Trigger a restart of darkice service with robust handling."""
        with self.restart_locks[f"{system_name}-{service}"]:
            stats = darkice_stats[system_name][service]
            
            # Check restart cooldown
            if (stats['last_restart_attempt'] and 
                datetime.now() - stats['last_restart_attempt'] < timedelta(seconds=DARKICE_CONFIG['restart_cooldown'])):
                logger.info(f"Restart cooldown active for {system_name}/{service}")
                return
            
            # Check max attempts
            if stats['restart_attempts'] >= DARKICE_CONFIG['max_restart_attempts']:
                logger.error(f"Max restart attempts ({DARKICE_CONFIG['max_restart_attempts']}) reached for {system_name}/{service}")
                return
            
            stats['restart_attempts'] += 1
            stats['last_restart_attempt'] = datetime.now()
            
            logger.info(f"Attempting to restart {service} on {system_name} (attempt {stats['restart_attempts']})")
            
            # Use a separate thread for restart to avoid blocking monitoring
            restart_thread = threading.Thread(
                target=self.perform_darkice_restart,
                args=(system_name, service),
                daemon=True
            )
            restart_thread.start()
    
    def perform_darkice_restart(self, system_name, service):
        """Perform the actual restart with multiple strategies."""
        ssh = self.ssh_connections.get(system_name)
        if not ssh:
            logger.error(f"No SSH connection for {system_name}")
            return
        
        success = False
        
        # Strategy 1: Normal systemctl restart (try multiple times)
        for attempt in range(3):
            logger.info(f"Restart attempt {attempt + 1} for {system_name}/{service} using systemctl restart")
            success = self.execute_restart_command(ssh, f"sudo systemctl restart {service}", timeout=15)
            if success:
                break
            time.sleep(2)
        
        # Strategy 2: Stop then start if restart failed
        if not success:
            logger.info(f"Systemctl restart failed, trying stop/start for {system_name}/{service}")
            stop_success = self.execute_restart_command(ssh, f"sudo systemctl stop {service}", timeout=10)
            time.sleep(3)
            start_success = self.execute_restart_command(ssh, f"sudo systemctl start {service}", timeout=10)
            success = stop_success and start_success
        
        # Strategy 3: Force kill then start if stop/start failed
        if not success:
            logger.info(f"Stop/start failed, trying force kill for {system_name}/{service}")
            # Kill all darkice processes
            self.execute_restart_command(ssh, f"sudo pkill -9 darkice", timeout=5)
            time.sleep(2)
            success = self.execute_restart_command(ssh, f"sudo systemctl start {service}", timeout=10)
        
        # Update stats based on result
        stats = darkice_stats[system_name][service]
        if success:
            logger.info(f"Successfully restarted {service} on {system_name}")
            stats['consecutive_overruns'] = 0
            stats['overrun_spam_detected'] = False
            self.publish_restart_success(system_name, service)
        else:
            logger.error(f"Failed to restart {service} on {system_name}")
            self.publish_restart_failure(system_name, service)
    
    def execute_restart_command(self, ssh, command, timeout=10):
        """Execute a restart command with timeout and proper error handling."""
        try:
            logger.debug(f"Executing: {command}")
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            
            # Wait for completion with timeout
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                logger.debug(f"Command succeeded: {command}")
                return True
            else:
                error_output = stderr.read().decode().strip()
                logger.warning(f"Command failed with exit code {exit_status}: {command} - {error_output}")
                return False
                
        except Exception as e:
            logger.error(f"Command execution failed: {command} - {e}")
            return False
    
    def publish_buffer_overrun_event(self, system_name, service, timestamp, log_line, stats):
        """Publish buffer overrun event to MQTT."""
        try:
            overrun_data = {
                'system': system_name,
                'service': service,
                'timestamp': timestamp.isoformat(),
                'log_line': log_line,
                'total_count': stats['buffer_overrun_count'],
                'consecutive_overruns': stats['consecutive_overruns'],
                'spam_detected': stats['overrun_spam_detected'],
                'restart_attempts': stats['restart_attempts']
            }
            
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/overrun", json.dumps(overrun_data))
        except Exception as e:
            logger.error(f"Failed to publish buffer overrun event: {e}")
    
    def publish_restart_success(self, system_name, service):
        """Publish successful restart event to MQTT."""
        try:
            restart_data = {
                'system': system_name,
                'service': service,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'message': 'Darkice service restarted successfully'
            }
            
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/restart", json.dumps(restart_data))
        except Exception as e:
            logger.error(f"Failed to publish restart success: {e}")
    
    def publish_restart_failure(self, system_name, service):
        """Publish failed restart event to MQTT."""
        try:
            restart_data = {
                'system': system_name,
                'service': service,
                'timestamp': datetime.now().isoformat(),
                'status': 'failure',
                'message': 'Failed to restart darkice service after multiple attempts'
            }
            
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/restart", json.dumps(restart_data))
        except Exception as e:
            logger.error(f"Failed to publish restart failure: {e}")
    
    def start_monitoring(self):
        """Start monitoring all systems for darkice services."""
        for system in self.pi_systems:
            if self.setup_ssh_connection(system):
                for service in DARKICE_SERVICES:
                    thread_name = f"{system['name']}-{service}-darkice"
                    thread = threading.Thread(
                        target=self.monitor_darkice_service,
                        args=(system['name'], service),
                        daemon=True,
                        name=thread_name
                    )
                    thread.start()
                    self.monitoring_threads[thread_name] = thread
                    logger.info(f"Started darkice monitoring thread: {thread_name}")
    
    def get_darkice_summary(self):
        """Get a summary of darkice buffer overrun statistics."""
        summary = {}
        for system_name, services in darkice_stats.items():
            summary[system_name] = {}
            for service_name, stats in services.items():
                recent_count = sum(1 for overrun in stats['recent_buffer_overruns'] 
                                 if overrun['timestamp'] > datetime.now() - timedelta(hours=1))
                summary[system_name][service_name] = {
                    'total_buffer_overruns': stats['buffer_overrun_count'],
                    'recent_overruns_1h': recent_count,
                    'consecutive_overruns': stats['consecutive_overruns'],
                    'restart_attempts': stats['restart_attempts'],
                    'spam_detected': stats['overrun_spam_detected'],
                    'last_buffer_overrun': stats['last_buffer_overrun'].isoformat() if stats['last_buffer_overrun'] else None,
                    'last_restart_attempt': stats['last_restart_attempt'].isoformat() if stats['last_restart_attempt'] else None
                }
        return summary

class UnderrunMonitor:
    """Monitor underruns on remote Pi systems via SSH."""
    
    def __init__(self, pi_systems):
        self.pi_systems = pi_systems
        self.ssh_connections = {}
        self.monitoring_threads = {}
        self.underrun_pattern = re.compile(r'Audio device underrun detected\.|audio end or underrun')
        
    def setup_ssh_connection(self, system):
        """Setup SSH connection to a Pi system."""
        try:
            logger.info(f"[UNDERRUN] Attempting SSH connection to {system['name']} at {system['host']} as user {system['user']}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                system['host'], 
                username=system['user'],
                timeout=15,
                # Add key-based auth if needed
                # key_filename='/path/to/key'
            )
            
            # Test the connection with a simple command
            stdin, stdout, stderr = ssh.exec_command('echo "SSH connection test"', timeout=5)
            test_result = stdout.read().decode().strip()
            if test_result == "SSH connection test":
                # Test journalctl availability and service status
                for service in MONITORED_SERVICES:
                    stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service}', timeout=5)
                    service_status = stdout.read().decode().strip()
                    logger.debug(f"[UNDERRUN] Service {service} status on {system['name']}: {service_status}")
                    
                    # Test if we can read recent logs
                    stdin, stdout, stderr = ssh.exec_command(f'journalctl -u {service} -n 1 --no-pager', timeout=5)
                    recent_log = stdout.read().decode().strip()
                    if recent_log:
                        logger.debug(f"[UNDERRUN] Recent log from {service} on {system['name']}: {recent_log[:100]}...")
                    else:
                        logger.warning(f"[UNDERRUN] No recent logs found for {service} on {system['name']}")
                
                self.ssh_connections[system['name']] = ssh
                logger.info(f"[UNDERRUN] SSH connection established and tested successfully to {system['name']}")
                return True
            else:
                logger.error(f"[UNDERRUN] SSH connection test failed for {system['name']}")
                ssh.close()
                return False
                
        except Exception as e:
            logger.error(f"[UNDERRUN] Failed to connect to {system['name']} ({system['host']}): {e}")
            return False
    
    def monitor_system_underruns(self, system_name, service):
        """Monitor underruns for a specific service on a system."""
        ssh = self.ssh_connections.get(system_name)
        if not ssh:
            logger.error(f"No SSH connection available for {system_name}")
            return
            
        try:
            # Use journalctl to follow the service logs
            command = f"journalctl -u {service} -f -o cat --no-hostname"
            logger.info(f"Starting underrun monitoring for {service} on {system_name} with command: {command}")
            
            stdin, stdout, stderr = ssh.exec_command(command)
            
            logger.info(f"Successfully started monitoring {service} on {system_name}")
            
            # Read stderr in a separate thread to catch any errors
            def read_stderr():
                try:
                    for error_line in iter(stderr.readline, ""):
                        error_line = error_line.strip()
                        if error_line:
                            logger.warning(f"stderr from {system_name}/{service}: {error_line}")
                except:
                    pass
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Monitor stdout for underrun messages
            line_count = 0
            last_heartbeat = time.time()
            for line in iter(stdout.readline, ""):
                line = line.strip()
                line_count += 1
                
                # Heartbeat every 30 seconds to show monitoring is active
                current_time = time.time()
                if current_time - last_heartbeat >= 30:
                    logger.info(f"[UNDERRUN] Monitoring heartbeat - {system_name}/{service}: {line_count} lines processed")
                    last_heartbeat = current_time
                
                # Log every 100th line to show monitoring is working
                if line_count % 100 == 0:
                    logger.debug(f"[UNDERRUN] Processed {line_count} lines from {system_name}/{service}")
                
                if not line:
                    continue
                    
                # Log all lines for debugging (temporarily)
                logger.debug(f"[UNDERRUN] {system_name}/{service}: {line}")
                    
                # Check for underrun patterns
                if self.underrun_pattern.search(line):
                    logger.info(f"[UNDERRUN] Matched underrun pattern in line: {line}")
                    self.record_underrun(system_name, service, line)
                    
        except Exception as e:
            logger.error(f"Error monitoring {service} on {system_name}: {e}")
            # Try to reconnect after a delay
            time.sleep(10)
            logger.info(f"Attempting to reconnect to {system_name}")
            system_config = next((s for s in self.pi_systems if s['name'] == system_name), None)
            if system_config and self.setup_ssh_connection(system_config):
                logger.info(f"Reconnected to {system_name}, restarting monitoring")
                # Restart monitoring
                self.monitor_system_underruns(system_name, service)
    
    def record_underrun(self, system_name, service, log_line):
        """Record an underrun event."""
        timestamp = datetime.now()
        
        # Update stats
        stats = underrun_stats[system_name][service]
        stats['count'] += 1
        stats['last_underrun'] = timestamp
        stats['recent_underruns'].append({
            'timestamp': timestamp,
            'log_line': log_line
        })
        
        # Log the underrun
        logger.warning(f"UNDERRUN detected - {system_name}/{service}: {log_line}")
        
        # Publish to MQTT
        self.publish_underrun_event(system_name, service, timestamp, log_line)
    
    def publish_underrun_event(self, system_name, service, timestamp, log_line):
        """Publish underrun event to MQTT."""
        try:
            underrun_data = {
                'system': system_name,
                'service': service,
                'timestamp': timestamp.isoformat(),
                'log_line': log_line,
                'total_count': underrun_stats[system_name][service]['count']
            }
            
            # Publish to MQTT (assuming we have access to the client)
            if hasattr(self, 'mqtt_client') and self.mqtt_client:
                self.mqtt_client.publish(UNDERRUN_TOPIC, json.dumps(underrun_data))
        except Exception as e:
            logger.error(f"Failed to publish underrun event: {e}")
    
    def start_monitoring(self):
        """Start monitoring all systems and services."""
        logger.info(f"[UNDERRUN] Starting underrun monitoring for {len(self.pi_systems)} systems: {[s['name'] for s in self.pi_systems]}")
        logger.info(f"[UNDERRUN] Services to monitor: {MONITORED_SERVICES}")
        
        for system in self.pi_systems:
            logger.info(f"[UNDERRUN] Setting up monitoring for system: {system}")
            if self.setup_ssh_connection(system):
                for service in MONITORED_SERVICES:
                    thread_name = f"{system['name']}-{service}"
                    logger.info(f"[UNDERRUN] Creating monitoring thread: {thread_name}")
                    thread = threading.Thread(
                        target=self.monitor_system_underruns,
                        args=(system['name'], service),
                        daemon=True,
                        name=thread_name
                    )
                    thread.start()
                    self.monitoring_threads[thread_name] = thread
                    logger.info(f"[UNDERRUN] Started monitoring thread: {thread_name}")
                    
                    # Verify thread is alive
                    time.sleep(0.1)  # Give thread a moment to start
                    if thread.is_alive():
                        logger.info(f"[UNDERRUN] Thread {thread_name} is running")
                    else:
                        logger.error(f"[UNDERRUN] Thread {thread_name} failed to start or died immediately")
            else:
                logger.error(f"[UNDERRUN] Failed to establish SSH connection to {system['name']}, skipping monitoring")
        
        logger.info(f"[UNDERRUN] Total monitoring threads created: {len(self.monitoring_threads)}")
    
    def get_underrun_summary(self):
        """Get a summary of underrun statistics."""
        summary = {}
        for system_name, services in underrun_stats.items():
            summary[system_name] = {}
            for service_name, stats in services.items():
                recent_count = sum(1 for u in stats['recent_underruns'] 
                                 if u['timestamp'] > datetime.now() - timedelta(hours=1))
                summary[system_name][service_name] = {
                    'total_count': stats['count'],
                    'recent_count_1h': recent_count,
                    'last_underrun': stats['last_underrun'].isoformat() if stats['last_underrun'] else None
                }
        return summary

class LiquidSoapClient:
    """Simple client to communicate with Liquidsoap via telnet."""
    
    def __init__(self, host='localhost', port=1234):
        self.host = host
        self.port = port
    
    def send_command(self, command):
        """Send a command to Liquidsoap via telnet."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # 5 second timeout
                sock.connect((self.host, self.port))
                
                # Send command
                sock.sendall(f"{command}\n".encode())
                
                # Read response
                response = sock.recv(1024).decode().strip()
                return response
        except Exception as e:
            logger.error(f"Failed to send command to Liquidsoap: {e}")
            return None
    
    def set_plan(self, plan):
        """Set the current plan in Liquidsoap."""
        return self.send_command(f"set_plan {plan}")
    
    def get_plan(self):
        """Get the current plan from Liquidsoap."""
        return self.send_command("get_plan")

def load_plan_state():
    """Load the current plan from persistent storage."""
    global current_plan
    try:
        if os.path.exists(plan_state_file):
            with open(plan_state_file, 'r') as f:
                data = json.load(f)
                current_plan = data.get('plan', 'B1')
                logger.info(f"Loaded plan state: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to load plan state: {e}")
        current_plan = "B1"

def save_plan_state():
    """Save the current plan to persistent storage."""
    try:
        with open(plan_state_file, 'w') as f:
            json.dump({'plan': current_plan, 'timestamp': time.time()}, f)
        logger.info(f"Saved plan state: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to save plan state: {e}")

def publish_plan_status(client):
    """Publish current plan status to MQTT."""
    status = {
        'plan': current_plan,
        'timestamp': time.time(),
        'source': 'server-agent'
    }
    try:
        client.publish(STATUS_TOPIC, json.dumps(status), retain=True)
        client.publish(PLAN_TOPIC, json.dumps({'plan': current_plan}), retain=True)
        logger.info(f"Published plan status: {current_plan}")
    except Exception as e:
        logger.error(f"Failed to publish plan status: {e}")

def publish_underrun_summary(client, monitor):
    """Publish underrun summary to MQTT."""
    try:
        summary = monitor.get_underrun_summary()
        summary_data = {
            'timestamp': time.time(),
            'systems': summary,
            'source': 'server-agent'
        }
        client.publish(f"{UNDERRUN_TOPIC}/summary", json.dumps(summary_data), retain=True)
        
        # Log summary for console visibility
        total_underruns = sum(
            sum(service['total_count'] for service in system.values())
            for system in summary.values()
        )
        recent_underruns = sum(
            sum(service['recent_count_1h'] for service in system.values())
            for system in summary.values()
        )
        
        logger.info(f"Underrun summary - Total: {total_underruns}, Recent (1h): {recent_underruns}")
        
    except Exception as e:
        logger.error(f"Failed to publish underrun summary: {e}")

def publish_darkice_summary(client, darkice_monitor):
    """Publish darkice buffer overrun summary to MQTT."""
    try:
        summary = darkice_monitor.get_darkice_summary()
        summary_data = {
            'timestamp': time.time(),
            'systems': summary,
            'source': 'server-agent'
        }
        client.publish(f"{DARKICE_TOPIC}/summary", json.dumps(summary_data), retain=True)
        
        # Log summary for console visibility
        total_overruns = sum(
            sum(service['total_buffer_overruns'] for service in system.values())
            for system in summary.values()
        )
        active_restarts = sum(
            sum(service['restart_attempts'] for service in system.values())
            for system in summary.values()
        )
        spam_detected = any(
            any(service['spam_detected'] for service in system.values())
            for system in summary.values()
        )
        
        logger.info(f"Darkice summary - Buffer overruns: {total_overruns}, Restart attempts: {active_restarts}, Spam detected: {spam_detected}")
        
    except Exception as e:
        logger.error(f"Failed to publish darkice summary: {e}")

def handle_plan_command(client, plan):
    """Handle plan selection command."""
    global current_plan
    
    valid_plans = ['A1', 'A2', 'B1', 'B2', 'B3', 'C', 'D']
    
    if plan not in valid_plans:
        logger.warning(f"Invalid plan: {plan}")
        return
    
    logger.info(f"Changing plan from {current_plan} to {plan}")
    
    # Update Liquidsoap
    liquidsoap = LiquidSoapClient(LIQUIDSOAP_HOST, LIQUIDSOAP_PORT)
    response = liquidsoap.set_plan(plan)
    
    if response:
        logger.info(f"Liquidsoap response: {response}")
        current_plan = plan
        save_plan_state()
        publish_plan_status(client)
    else:
        logger.error(f"Failed to set plan in Liquidsoap")

def tail_log(name, path):
    """Continuously tail a log file and print new lines with a prefix."""
    try:
        with subprocess.Popen(['tail', '-F', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            for line in proc.stdout:
                print(f"[{name}] {line.strip()}")
    except Exception as e:
        print(f"[{name}] ERROR: {e}")

def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(CMD_TOPIC)
    client.subscribe("system/broadcast")  # Listen for plan broadcasts
    
    # Publish initial plan status
    publish_plan_status(client)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        if msg.topic == CMD_TOPIC:
            # Handle service restart commands
            if 'restart' in data:
                service = data['restart']
                if service in ['icecast2', 'liquidsoap']:
                    logger.info(f"Restarting {service}...")
                    subprocess.run(['sudo', 'systemctl', 'restart', service], check=True)
                    logger.info(f"Restarted {service}")
                    
                    # Re-sync plan with Liquidsoap after restart
                    if service == 'liquidsoap':
                        time.sleep(2)  # Give liquidsoap time to start
                        handle_plan_command(client, current_plan)
                else:
                    logger.warning(f"Unknown service: {service}")
            elif 'underrun_summary' in data:
                # Handle underrun summary request
                logger.info("Underrun summary requested")
                if hasattr(userdata, 'underrun_monitor'):
                    publish_underrun_summary(client, userdata.underrun_monitor)
            elif 'darkice_summary' in data:
                # Handle darkice summary request
                logger.info("Darkice summary requested")
                if hasattr(userdata, 'darkice_monitor'):
                    publish_darkice_summary(client, userdata.darkice_monitor)
            elif 'darkice_restart' in data:
                # Handle manual darkice restart request
                system = data.get('system')
                service = data.get('service', 'darkice')
                if system and hasattr(userdata, 'darkice_monitor'):
                    logger.info(f"Manual darkice restart requested for {system}/{service}")
                    userdata.darkice_monitor.trigger_darkice_restart(system, service)
                else:
                    logger.warning("Darkice restart command missing system parameter or darkice monitor not available")
            else:
                logger.warning(f"Unknown command: {data}")
                
        elif msg.topic == "system/broadcast":
            # Handle plan broadcast messages
            if 'plan' in data:
                plan = data['plan']
                handle_plan_command(client, plan)
            else:
                logger.warning(f"Broadcast message missing plan: {data}")
                
    except Exception as e:
        logger.error(f"MQTT message handling error: {e}")

def status_publisher_thread(client, monitor, darkice_monitor):
    """Background thread to periodically publish status and sync with Liquidsoap."""
    global current_plan
    
    while True:
        try:
            # Periodically sync plan state with Liquidsoap
            liquidsoap = LiquidSoapClient(LIQUIDSOAP_HOST, LIQUIDSOAP_PORT)
            liquidsoap_plan = liquidsoap.get_plan()
            
            if liquidsoap_plan and liquidsoap_plan != current_plan:
                logger.info(f"Plan drift detected. Liquidsoap: {liquidsoap_plan}, Agent: {current_plan}")
                # Update our state to match Liquidsoap (Liquidsoap is source of truth)
                current_plan = liquidsoap_plan
                save_plan_state()
                publish_plan_status(client)
            
            # Regular status publish
            publish_plan_status(client)
            
            # Publish underrun summary
            publish_underrun_summary(client, monitor)
            
            # Publish darkice summary
            publish_darkice_summary(client, darkice_monitor)
            
        except Exception as e:
            logger.error(f"Status publisher error: {e}")
        
        time.sleep(30)  # Publish every 30 seconds

def main():
    # Load saved plan state
    load_plan_state()
    
    # Initialize underrun monitor
    underrun_monitor = UnderrunMonitor(PI_SYSTEMS)
    
    # Initialize darkice monitor
    darkice_monitor = DarkiceMonitor(PI_SYSTEMS)
    
    # Start log tailing threads
    for name, path in LOG_PATHS.items():
        if os.path.exists(path):
            t = threading.Thread(target=tail_log, args=(name, path), daemon=True)
            t.start()
        else:
            logger.warning(f"Log file not found: {path}")

    # Start MQTT client  
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Store monitor references in userdata
    client.user_data_set(type('UserData', (), {
        'underrun_monitor': underrun_monitor,
        'darkice_monitor': darkice_monitor
    })())
    underrun_monitor.mqtt_client = client
    darkice_monitor.mqtt_client = client
    
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    # Start monitoring
    logger.info("[MAIN] Starting underrun monitoring...")
    underrun_monitor.start_monitoring()
    logger.info("[MAIN] Starting darkice monitoring...")
    darkice_monitor.start_monitoring()
    logger.info("[MAIN] All monitoring started")
    
    # Start background status publisher
    status_thread = threading.Thread(target=status_publisher_thread, args=(client, underrun_monitor, darkice_monitor), daemon=True)
    status_thread.start()
    
    logger.info("Server agent started with plan management, underrun monitoring, and darkice buffer overrun monitoring")
    client.loop_forever()

if __name__ == "__main__":
    main() 