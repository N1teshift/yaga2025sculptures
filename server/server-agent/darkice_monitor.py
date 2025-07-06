#!/usr/bin/env python3
"""
DarkiceMonitor module for server-agent
Handles SSH-based monitoring of darkice buffer overruns and automatic restart functionality
"""

import logging
import threading
import time
import json
import paramiko
import re
from datetime import datetime, timedelta
from collections import deque

# Import configuration
from config import (
    DARKICE_SERVICES, CONNECTION_CONFIG, DARKICE_CONFIG, 
    DARKICE_TOPIC, create_darkice_stats
)

logger = logging.getLogger(__name__)

class DarkiceMonitor:
    """Monitor darkice services for buffer overrun issues and handle restarts."""
    
    def __init__(self, pi_systems):
        self.pi_systems = pi_systems
        self.ssh_connections = {}
        self.monitoring_threads = {}
        self.mqtt_client = None  # Will be set after initialization
        self.buffer_overrun_pattern = re.compile(r'buffer overrun', re.IGNORECASE)
        self.restart_locks = {}  # Per-system restart locks
        self.darkice_stats = create_darkice_stats()
        
        # Initialize restart locks
        for system in self.pi_systems:
            for service in DARKICE_SERVICES:
                self.restart_locks[f"{system['name']}-{service}"] = threading.Lock()
        
    def setup_ssh_connection(self, system):
        """Setup SSH connection to a Pi system with multiple host fallbacks."""
        system_name = system['name']
        
        for host in system['hosts']:
            try:
                logger.info(f"[DARKICE] Attempting SSH connection to {system_name} at {host} as user {system['user']}")
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
                
                # Test the connection
                stdin, stdout, stderr = ssh.exec_command('echo "SSH connection test"', timeout=5)
                test_result = stdout.read().decode().strip()
                if test_result == "SSH connection test":
                    self.ssh_connections[system_name] = ssh
                    logger.info(f"[DARKICE] SSH connection established to {system_name} at {host}")
                    return True
                else:
                    ssh.close()
                    continue
                    
            except Exception as e:
                logger.error(f"[DARKICE] Failed to connect to {system_name} at {host}: {e}")
                if 'ssh' in locals():
                    try:
                        ssh.close()
                    except:
                        pass
                continue
        
        logger.error(f"[DARKICE] All connection attempts failed for {system_name}")
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
            
            logger.info(f"[DARKICE] Started monitoring {service} on {system_name}")
            
            for line in iter(stdout.readline, ""):
                line = line.strip()
                if not line:
                    continue
                    
                # Check for buffer overrun patterns
                if self.buffer_overrun_pattern.search(line):
                    self.handle_buffer_overrun(system_name, service, line)
                    
        except Exception as e:
            logger.error(f"[DARKICE] Error monitoring {service} on {system_name}: {e}")
    
    def handle_buffer_overrun(self, system_name, service, log_line):
        """Handle buffer overrun detection and restart logic."""
        timestamp = datetime.now()
        
        # Update stats
        stats = self.darkice_stats[system_name][service]
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
            logger.warning(f"[DARKICE] BUFFER OVERRUN SPAM detected on {system_name}/{service} - {recent_count} overruns in {DARKICE_CONFIG['overrun_spam_window']}s")
        
        # Log the buffer overrun
        logger.warning(f"[DARKICE] BUFFER OVERRUN detected - {system_name}/{service}: consecutive={stats['consecutive_overruns']}, recent={recent_count}")
        
        # Publish to MQTT
        self.publish_buffer_overrun_event(system_name, service, timestamp, log_line, stats)
        
        # Check if restart is needed
        if (stats['consecutive_overruns'] >= DARKICE_CONFIG['buffer_overrun_threshold'] or 
            stats['overrun_spam_detected']):
            self.trigger_darkice_restart(system_name, service)
    
    def trigger_darkice_restart(self, system_name, service):
        """Trigger a restart of darkice service with robust handling."""
        with self.restart_locks[f"{system_name}-{service}"]:
            stats = self.darkice_stats[system_name][service]
            
            # Check restart cooldown
            if (stats['last_restart_attempt'] and 
                datetime.now() - stats['last_restart_attempt'] < timedelta(seconds=DARKICE_CONFIG['restart_cooldown'])):
                logger.info(f"[DARKICE] Restart cooldown active for {system_name}/{service}")
                return
            
            # Check max attempts
            if stats['restart_attempts'] >= DARKICE_CONFIG['max_restart_attempts']:
                logger.error(f"[DARKICE] Max restart attempts ({DARKICE_CONFIG['max_restart_attempts']}) reached for {system_name}/{service}")
                return
            
            stats['restart_attempts'] += 1
            stats['last_restart_attempt'] = datetime.now()
            
            logger.info(f"[DARKICE] Attempting to restart {service} on {system_name} (attempt {stats['restart_attempts']})")
            
            # Use a separate thread for restart to avoid blocking monitoring
            restart_thread = threading.Thread(
                target=self.perform_darkice_restart,
                args=(system_name, service),
                daemon=True
            )
            restart_thread.start()
    
    def perform_darkice_restart(self, system_name, service):
        """Perform the actual darkice restart with multiple strategies."""
        ssh = self.ssh_connections.get(system_name)
        if not ssh:
            logger.error(f"[DARKICE] No SSH connection available for restart of {system_name}/{service}")
            return
        
        try:
            # Strategy 1: Normal systemctl restart (3 attempts)
            for attempt in range(3):
                if self.execute_restart_command(ssh, f"sudo systemctl restart {service}"):
                    logger.info(f"[DARKICE] Successfully restarted {service} on {system_name} using systemctl restart")
                    self.publish_restart_success(system_name, service)
                    self.reset_overrun_counters(system_name, service)
                    return
                time.sleep(2)
            
            # Strategy 2: Stop then start
            logger.warning(f"[DARKICE] systemctl restart failed, trying stop/start for {system_name}/{service}")
            if (self.execute_restart_command(ssh, f"sudo systemctl stop {service}") and
                self.execute_restart_command(ssh, f"sudo systemctl start {service}")):
                logger.info(f"[DARKICE] Successfully restarted {service} on {system_name} using stop/start")
                self.publish_restart_success(system_name, service)
                self.reset_overrun_counters(system_name, service)
                return
            
            # Strategy 3: Force kill and start
            logger.warning(f"[DARKICE] stop/start failed, trying force kill for {system_name}/{service}")
            if (self.execute_restart_command(ssh, f"sudo pkill -9 {service}") and
                self.execute_restart_command(ssh, f"sudo systemctl start {service}")):
                logger.info(f"[DARKICE] Successfully restarted {service} on {system_name} using force kill/start")
                self.publish_restart_success(system_name, service)
                self.reset_overrun_counters(system_name, service)
                return
            
            # All strategies failed
            logger.error(f"[DARKICE] All restart strategies failed for {system_name}/{service}")
            self.publish_restart_failure(system_name, service)
            
        except Exception as e:
            logger.error(f"[DARKICE] Error during restart of {system_name}/{service}: {e}")
            self.publish_restart_failure(system_name, service)
    
    def execute_restart_command(self, ssh, command, timeout=10):
        """Execute a restart command via SSH."""
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                logger.debug(f"[DARKICE] Command succeeded: {command}")
                return True
            else:
                stderr_output = stderr.read().decode().strip()
                logger.warning(f"[DARKICE] Command failed with exit code {exit_status}: {command}")
                if stderr_output:
                    logger.warning(f"[DARKICE] stderr: {stderr_output}")
                return False
                
        except Exception as e:
            logger.error(f"[DARKICE] Error executing command '{command}': {e}")
            return False
    
    def reset_overrun_counters(self, system_name, service):
        """Reset overrun counters after successful restart."""
        stats = self.darkice_stats[system_name][service]
        stats['consecutive_overruns'] = 0
        stats['overrun_spam_detected'] = False
        logger.info(f"[DARKICE] Reset overrun counters for {system_name}/{service}")
    
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
                'restart_attempts': stats['restart_attempts'],
                'source': 'server-agent-darkice-monitor'
            }
            
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/overrun", json.dumps(overrun_data))
                logger.debug(f"[DARKICE] Published buffer overrun event to MQTT: {system_name}/{service}")
        except Exception as e:
            logger.error(f"[DARKICE] Failed to publish buffer overrun event: {e}")
    
    def publish_restart_success(self, system_name, service):
        """Publish restart success event to MQTT."""
        try:
            restart_data = {
                'system': system_name,
                'service': service,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'message': f'{service} service restarted successfully',
                'source': 'server-agent-darkice-monitor'
            }
            
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/restart", json.dumps(restart_data))
                logger.info(f"[DARKICE] Published restart success to MQTT: {system_name}/{service}")
        except Exception as e:
            logger.error(f"[DARKICE] Failed to publish restart success: {e}")
    
    def publish_restart_failure(self, system_name, service):
        """Publish restart failure event to MQTT."""
        try:
            restart_data = {
                'system': system_name,
                'service': service,
                'timestamp': datetime.now().isoformat(),
                'status': 'failure',
                'message': f'Failed to restart {service} service after multiple attempts',
                'source': 'server-agent-darkice-monitor'
            }
            
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish(f"{DARKICE_TOPIC}/restart", json.dumps(restart_data))
                logger.error(f"[DARKICE] Published restart failure to MQTT: {system_name}/{service}")
        except Exception as e:
            logger.error(f"[DARKICE] Failed to publish restart failure: {e}")
    
    def start_monitoring(self):
        """Start monitoring all systems and services."""
        logger.info(f"[DARKICE] Starting darkice monitoring for {len(self.pi_systems)} systems")
        
        for system in self.pi_systems:
            if self.setup_ssh_connection(system):
                for service in DARKICE_SERVICES:
                    thread_name = f"darkice-{system['name']}-{service}"
                    thread = threading.Thread(
                        target=self.monitor_darkice_service,
                        args=(system['name'], service),
                        daemon=True,
                        name=thread_name
                    )
                    thread.start()
                    self.monitoring_threads[thread_name] = thread
                    logger.info(f"[DARKICE] Started monitoring thread: {thread_name}")
            else:
                logger.error(f"[DARKICE] Failed to establish SSH connection to {system['name']}")
        
        logger.info(f"[DARKICE] Total darkice monitoring threads created: {len(self.monitoring_threads)}")
    
    def get_darkice_summary(self):
        """Get a summary of darkice statistics."""
        summary = {}
        for system_name, services in self.darkice_stats.items():
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
    
    def set_mqtt_client(self, mqtt_client):
        """Set the MQTT client reference."""
        self.mqtt_client = mqtt_client
        logger.info("[DARKICE] MQTT client reference set") 