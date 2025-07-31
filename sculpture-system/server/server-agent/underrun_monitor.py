#!/usr/bin/env python3
"""
UnderrunMonitor module for server-agent
Handles SSH-based monitoring of audio underruns on remote Pi systems
"""

import logging
import threading
import time
import json
import paramiko
from datetime import datetime, timedelta
from collections import deque

# Import configuration
from config import (
    MONITORED_SERVICES, CONNECTION_CONFIG, UNDERRUN_PATTERNS, 
    UNDERRUN_TOPIC, create_underrun_stats
)

logger = logging.getLogger(__name__)

class UnderrunMonitor:
    """Monitor underruns on remote Pi systems via SSH with enhanced connection handling."""
    
    def __init__(self, pi_systems):
        self.pi_systems = pi_systems
        self.ssh_connections = {}
        self.monitoring_threads = {}
        self.mqtt_client = None  # Will be set after initialization
        self.connection_states = {}  # Track connection state for each system
        self.underrun_stats = create_underrun_stats()
        
        # Initialize connection states
        for system in self.pi_systems:
            self.connection_states[system['name']] = {
                'connected': False,
                'last_attempt': None,
                'successful_host': None,
                'failed_hosts': set(),
                'connection_count': 0
            }
        
    def setup_ssh_connection(self, system):
        """Setup SSH connection to a Pi system with multiple host fallbacks."""
        system_name = system['name']
        state = self.connection_states[system_name]
        
        # If we had a successful connection, try that host first
        hosts_to_try = []
        if state['successful_host']:
            hosts_to_try.append(state['successful_host'])
        
        # Add remaining hosts, excluding recently failed ones
        for host in system['hosts']:
            if host not in hosts_to_try and host not in state['failed_hosts']:
                hosts_to_try.append(host)
        
        # If all hosts have failed recently, reset and try all again
        if not hosts_to_try:
            logger.info(f"[UNDERRUN] Resetting failed hosts for {system_name}, trying all hosts again")
            state['failed_hosts'].clear()
            hosts_to_try = system['hosts']
        
        for host in hosts_to_try:
            try:
                logger.info(f"[UNDERRUN] Attempting SSH connection to {system_name} at {host} as user {system['user']}")
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                connect_kwargs = {
                    'hostname': host,
                    'username': system['user'],
                    'timeout': CONNECTION_CONFIG['ssh_timeout'],
                }
                
                if CONNECTION_CONFIG['ssh_key_file']:
                    connect_kwargs['key_filename'] = CONNECTION_CONFIG['ssh_key_file']
                
                ssh.connect(**connect_kwargs)
                
                # Test the connection with a simple command
                if CONNECTION_CONFIG['test_connection']:
                    stdin, stdout, stderr = ssh.exec_command('echo "SSH connection test"', timeout=5)
                    test_result = stdout.read().decode().strip()
                    if test_result != "SSH connection test":
                        logger.error(f"[UNDERRUN] SSH connection test failed for {system_name} at {host}")
                        ssh.close()
                        state['failed_hosts'].add(host)
                        continue
                
                # Test journalctl availability and service status
                services_ok = True
                for service in MONITORED_SERVICES:
                    try:
                        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service}', timeout=5)
                        service_status = stdout.read().decode().strip()
                        logger.info(f"[UNDERRUN] Service {service} status on {system_name}: {service_status}")
                        
                        # Test if we can read recent logs
                        stdin, stdout, stderr = ssh.exec_command(f'journalctl -u {service} -n 3 --no-pager', timeout=5)
                        recent_log = stdout.read().decode().strip()
                        if recent_log:
                            logger.info(f"[UNDERRUN] Recent logs from {service} on {system_name} ({len(recent_log)} chars)")
                        else:
                            logger.warning(f"[UNDERRUN] No recent logs found for {service} on {system_name}")
                    except Exception as e:
                        logger.error(f"[UNDERRUN] Error testing service {service} on {system_name}: {e}")
                        services_ok = False
                
                if not services_ok:
                    logger.warning(f"[UNDERRUN] Service tests failed for {system_name} at {host}")
                    ssh.close()
                    state['failed_hosts'].add(host)
                    continue
                
                # Connection successful
                self.ssh_connections[system_name] = ssh
                state['connected'] = True
                state['successful_host'] = host
                state['connection_count'] += 1
                state['last_attempt'] = datetime.now()
                
                logger.info(f"[UNDERRUN] SSH connection established successfully to {system_name} at {host}")
                return True
                
            except Exception as e:
                logger.error(f"[UNDERRUN] Failed to connect to {system_name} at {host}: {str(e)}")
                state['failed_hosts'].add(host)
                if 'ssh' in locals():
                    try:
                        ssh.close()
                    except:
                        pass
                continue
        
        # All hosts failed
        state['connected'] = False
        state['last_attempt'] = datetime.now()
        logger.error(f"[UNDERRUN] All connection attempts failed for {system_name}")
        return False
    
    def monitor_system_underruns(self, system_name, service):
        """Monitor underruns for a specific service on a system with reconnection logic."""
        while True:  # Keep trying to reconnect
            ssh = self.ssh_connections.get(system_name)
            if not ssh:
                logger.error(f"[UNDERRUN] No SSH connection available for {system_name}")
                time.sleep(CONNECTION_CONFIG['connection_retry_interval'])
                
                # Try to reconnect
                system_config = next((s for s in self.pi_systems if s['name'] == system_name), None)
                if system_config:
                    self.setup_ssh_connection(system_config)
                continue
                
            try:
                # Use journalctl to follow the service logs
                command = f"journalctl -u {service} -f -o cat --no-hostname"
                logger.info(f"[UNDERRUN] Starting monitoring for {service} on {system_name} with command: {command}")
                
                stdin, stdout, stderr = ssh.exec_command(command)
                
                logger.info(f"[UNDERRUN] Successfully started monitoring {service} on {system_name}")
                
                # Read stderr in a separate thread to catch any errors
                def read_stderr():
                    try:
                        for error_line in iter(stderr.readline, ""):
                            error_line = error_line.strip()
                            if error_line:
                                logger.warning(f"[UNDERRUN] stderr from {system_name}/{service}: {error_line}")
                    except Exception as e:
                        logger.debug(f"[UNDERRUN] stderr thread error for {system_name}/{service}: {e}")
                
                stderr_thread = threading.Thread(target=read_stderr, daemon=True)
                stderr_thread.start()
                
                # Monitor stdout for underrun messages
                line_count = 0
                last_heartbeat = time.time()
                
                logger.info(f"[UNDERRUN] Beginning log monitoring loop for {system_name}/{service}")
                
                for line in iter(stdout.readline, ""):
                    line = line.strip()
                    line_count += 1
                    
                    # Heartbeat every specified interval to show monitoring is active
                    current_time = time.time()
                    if current_time - last_heartbeat >= CONNECTION_CONFIG['heartbeat_interval']:
                        logger.info(f"[UNDERRUN] Monitoring active - {system_name}/{service}: {line_count} lines processed")
                        last_heartbeat = current_time
                    
                    if not line:
                        continue
                        
                    # Check for underrun patterns - use multiple patterns for better detection
                    underrun_detected = False
                    for pattern in UNDERRUN_PATTERNS:
                        if pattern.search(line):
                            underrun_detected = True
                            break
                    
                    if underrun_detected:
                        logger.warning(f"[UNDERRUN] DETECTED on {system_name}/{service}: {line}")
                        self.record_underrun(system_name, service, line)
                    else:
                        # Log MPV-related lines for debugging
                        if any(keyword in line.lower() for keyword in ['mpv', 'audio', 'pulse', 'ao/']):
                            logger.debug(f"[UNDERRUN] Audio line from {system_name}/{service}: {line}")
                        
                        # Sample non-audio lines occasionally
                        if line_count % 100 == 0:
                            logger.debug(f"[UNDERRUN] Sample line {line_count} from {system_name}/{service}: {line}")
                    
                # If we reach here, the stdout stream ended
                logger.warning(f"[UNDERRUN] Monitoring stream ended for {system_name}/{service}")
                break
                        
            except Exception as e:
                logger.error(f"[UNDERRUN] Error monitoring {service} on {system_name}: {str(e)}")
                import traceback
                logger.debug(f"[UNDERRUN] Monitoring traceback: {traceback.format_exc()}")
                
                # Mark connection as failed
                if system_name in self.ssh_connections:
                    try:
                        self.ssh_connections[system_name].close()
                    except:
                        pass
                    del self.ssh_connections[system_name]
                
                self.connection_states[system_name]['connected'] = False
                break
            
            # Wait before attempting to restart monitoring
            logger.info(f"[UNDERRUN] Waiting {CONNECTION_CONFIG['connection_retry_interval']}s before restarting monitoring for {system_name}/{service}")
            time.sleep(CONNECTION_CONFIG['connection_retry_interval'])
    
    def record_underrun(self, system_name, service, log_line):
        """Record an underrun event with enhanced logging."""
        timestamp = datetime.now()
        
        # Update stats
        stats = self.underrun_stats[system_name][service]
        stats['count'] += 1
        stats['last_underrun'] = timestamp
        stats['recent_underruns'].append({
            'timestamp': timestamp,
            'log_line': log_line
        })
        
        # Calculate recent underrun rate
        recent_window = timestamp - timedelta(minutes=5)
        recent_count = sum(1 for u in stats['recent_underruns'] 
                          if u['timestamp'] > recent_window)
        
        # Enhanced logging with rate information
        logger.warning(f"UNDERRUN #{stats['count']} detected - {system_name}/{service} (recent 5min: {recent_count}): {log_line}")
        
        # Publish to MQTT
        self.publish_underrun_event(system_name, service, timestamp, log_line)
    
    def publish_underrun_event(self, system_name, service, timestamp, log_line):
        """Publish underrun event to MQTT with better error handling."""
        try:
            underrun_data = {
                'system': system_name,
                'service': service,
                'timestamp': timestamp.isoformat(),
                'log_line': log_line,
                'total_count': self.underrun_stats[system_name][service]['count'],
                'source': 'server-agent-underrun-monitor'
            }
            
            # Publish to MQTT if client is available
            if self.mqtt_client and self.mqtt_client.is_connected():
                result = self.mqtt_client.publish(UNDERRUN_TOPIC, json.dumps(underrun_data))
                if result.rc == 0:  # MQTT_ERR_SUCCESS
                    logger.info(f"[UNDERRUN] Published underrun event to MQTT: {system_name}/{service}")
                else:
                    logger.error(f"[UNDERRUN] Failed to publish underrun event to MQTT: {result.rc}")
            else:
                logger.warning(f"[UNDERRUN] MQTT client not available, underrun event not published: {system_name}/{service}")
                
        except Exception as e:
            logger.error(f"[UNDERRUN] Failed to publish underrun event: {e}")
    
    def set_mqtt_client(self, mqtt_client):
        """Set the MQTT client reference."""
        self.mqtt_client = mqtt_client
        logger.info("[UNDERRUN] MQTT client reference set")
    
    def start_monitoring(self):
        """Start monitoring all systems and services with enhanced error handling."""
        logger.info(f"[UNDERRUN] Starting underrun monitoring for {len(self.pi_systems)} systems: {[s['name'] for s in self.pi_systems]}")
        logger.info(f"[UNDERRUN] Services to monitor: {MONITORED_SERVICES}")
        logger.info(f"[UNDERRUN] Underrun patterns: {len(UNDERRUN_PATTERNS)} patterns configured")
        
        for system in self.pi_systems:
            logger.info(f"[UNDERRUN] Setting up monitoring for system: {system['name']}")
            logger.info(f"[UNDERRUN] Hosts to try: {system['hosts']}")
            
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
        
        # Start enhanced thread health monitor
        def monitor_thread_health():
            while True:
                time.sleep(60)  # Check every minute
                dead_threads = []
                for thread_name, thread in self.monitoring_threads.items():
                    if not thread.is_alive():
                        logger.error(f"[UNDERRUN] Thread {thread_name} has died!")
                        dead_threads.append(thread_name)
                
                if dead_threads:
                    logger.warning(f"[UNDERRUN] {len(dead_threads)} monitoring threads have died: {dead_threads}")
                else:
                    logger.debug(f"[UNDERRUN] All {len(self.monitoring_threads)} monitoring threads are alive")
                
                # Log connection states
                connected_count = sum(1 for state in self.connection_states.values() if state['connected'])
                logger.info(f"[UNDERRUN] Connection status: {connected_count}/{len(self.pi_systems)} systems connected")
                
                for system_name, state in self.connection_states.items():
                    if state['connected']:
                        logger.debug(f"[UNDERRUN] {system_name}: Connected via {state['successful_host']} ({state['connection_count']} connections)")
                    else:
                        logger.debug(f"[UNDERRUN] {system_name}: Disconnected (last attempt: {state['last_attempt']})")
        
        health_thread = threading.Thread(target=monitor_thread_health, daemon=True, name="underrun-health-monitor")
        health_thread.start()
        logger.info(f"[UNDERRUN] Started enhanced thread health monitor")
    
    def get_underrun_summary(self):
        """Get a summary of underrun statistics with enhanced details."""
        summary = {}
        total_underruns = 0
        recent_underruns = 0
        
        for system_name, services in self.underrun_stats.items():
            summary[system_name] = {}
            for service_name, stats in services.items():
                recent_count = sum(1 for u in stats['recent_underruns'] 
                                 if u['timestamp'] > datetime.now() - timedelta(hours=1))
                summary[system_name][service_name] = {
                    'total_count': stats['count'],
                    'recent_count_1h': recent_count,
                    'last_underrun': stats['last_underrun'].isoformat() if stats['last_underrun'] else None
                }
                total_underruns += stats['count']
                recent_underruns += recent_count
        
        # Add connection status to summary
        summary['_connection_status'] = {
            'connected_systems': sum(1 for state in self.connection_states.values() if state['connected']),
            'total_systems': len(self.pi_systems),
            'systems': {
                name: {
                    'connected': state['connected'],
                    'successful_host': state['successful_host'],
                    'connection_count': state['connection_count']
                } for name, state in self.connection_states.items()
            }
        }
        
        summary['_totals'] = {
            'total_underruns': total_underruns,
            'recent_underruns_1h': recent_underruns
        }
        
        return summary 