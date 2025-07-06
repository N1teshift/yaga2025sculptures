#!/usr/bin/env python3
"""
Connection test script for server-agent underrun monitoring
This script tests SSH connections and service availability before running the full server-agent.
"""

import paramiko
import subprocess
import sys
import socket
import time
from datetime import datetime

# Import configuration from config module
try:
    from config import PI_SYSTEMS, MONITORED_SERVICES, CONNECTION_CONFIG
    SSH_TIMEOUT = CONNECTION_CONFIG['ssh_timeout']
except ImportError:
    # Fallback configuration if config module not available
    PI_SYSTEMS = [
        {
            "name": "sculpture1", 
            "hosts": [
                "sculpture1.local",
                "sculpture1",
                "192.168.1.101"  # Replace with actual IP
            ],
            "user": "pi"
        },
        {
            "name": "sculpture2", 
            "hosts": [
                "sculpture2.local",
                "sculpture2",
                "192.168.1.102"  # Replace with actual IP
            ],
            "user": "pi"
        },
        {
            "name": "sculpture3", 
            "hosts": [
                "sculpture3.local",
                "sculpture3",
                "192.168.1.103"  # Replace with actual IP
            ],
            "user": "pi"
        },
    ]
    MONITORED_SERVICES = ["player-live", "player-loop"]
    SSH_TIMEOUT = 10

def test_dns_resolution(hostname):
    """Test DNS resolution for a hostname."""
    try:
        ip = socket.gethostbyname(hostname)
        return True, ip
    except socket.gaierror as e:
        return False, str(e)

def test_ssh_connection(host, user, timeout=10):
    """Test SSH connection to a host."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, timeout=timeout)
        
        # Test with a simple command
        stdin, stdout, stderr = ssh.exec_command('echo "SSH test successful"', timeout=5)
        result = stdout.read().decode().strip()
        ssh.close()
        
        return True, result
    except Exception as e:
        return False, str(e)

def test_service_status(host, user, service, timeout=10):
    """Test service status on a remote host."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, timeout=timeout)
        
        # Check service status
        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {service}', timeout=5)
        status = stdout.read().decode().strip()
        
        # Get recent log lines
        stdin, stdout, stderr = ssh.exec_command(f'journalctl -u {service} -n 3 --no-pager', timeout=10)
        recent_logs = stdout.read().decode().strip()
        
        ssh.close()
        
        return True, status, recent_logs
    except Exception as e:
        return False, str(e), ""

def test_journalctl_follow(host, user, service, duration=10):
    """Test journalctl follow capability."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, timeout=SSH_TIMEOUT)
        
        # Test journalctl follow for a short duration
        stdin, stdout, stderr = ssh.exec_command(f'timeout {duration} journalctl -u {service} -f -o cat --no-hostname')
        
        lines = []
        start_time = time.time()
        while time.time() - start_time < duration:
            line = stdout.readline()
            if line:
                lines.append(line.strip())
            else:
                break
        
        ssh.close()
        return True, lines
    except Exception as e:
        return False, str(e)

def main():
    """Main test function."""
    print("=" * 80)
    print("Server-Agent Connection Test")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print()
    
    all_tests_passed = True
    
    for system in PI_SYSTEMS:
        print(f"Testing system: {system['name']}")
        print("-" * 40)
        
        successful_host = None
        
        # Test each host
        for host in system['hosts']:
            print(f"  Testing host: {host}")
            
            # Test DNS resolution
            if not host.replace('.', '').isdigit():  # Not an IP address
                dns_ok, dns_result = test_dns_resolution(host)
                if dns_ok:
                    print(f"    DNS resolution: OK -> {dns_result}")
                else:
                    print(f"    DNS resolution: FAILED -> {dns_result}")
                    continue
            else:
                print(f"    DNS resolution: SKIPPED (IP address)")
            
            # Test SSH connection
            ssh_ok, ssh_result = test_ssh_connection(host, system['user'], SSH_TIMEOUT)
            if ssh_ok:
                print(f"    SSH connection: OK -> {ssh_result}")
                successful_host = host
                break
            else:
                print(f"    SSH connection: FAILED -> {ssh_result}")
        
        if successful_host:
            print(f"  ✓ Successfully connected to {system['name']} via {successful_host}")
            
            # Test services
            for service in MONITORED_SERVICES:
                print(f"    Testing service: {service}")
                service_ok, status, logs = test_service_status(successful_host, system['user'], service)
                if service_ok:
                    print(f"      Service status: {status}")
                    if logs:
                        print(f"      Recent logs: {len(logs.split())} lines")
                        # Show first few lines
                        for line in logs.split('\n')[:2]:
                            if line.strip():
                                print(f"        {line[:80]}...")
                    else:
                        print(f"      Recent logs: No logs found")
                else:
                    print(f"      Service test: FAILED -> {status}")
                    all_tests_passed = False
            
            # Test journalctl follow capability
            print(f"    Testing journalctl follow for {MONITORED_SERVICES[0]} (10s test)...")
            follow_ok, follow_result = test_journalctl_follow(successful_host, system['user'], MONITORED_SERVICES[0], 10)
            if follow_ok:
                print(f"      Follow test: OK -> Captured {len(follow_result)} lines")
                if follow_result:
                    print(f"      Sample line: {follow_result[0][:80]}...")
            else:
                print(f"      Follow test: FAILED -> {follow_result}")
                all_tests_passed = False
        else:
            print(f"  ✗ Failed to connect to {system['name']} via any host")
            all_tests_passed = False
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if all_tests_passed:
        print("✓ All tests passed! The server-agent should be able to connect and monitor.")
        print()
        print("Next steps:")
        print("1. Update the IP addresses in config.py if needed")
        print("2. Start the server-agent: sudo systemctl start server-agent")
        print("3. Monitor the logs: journalctl -u server-agent -f")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the following:")
        print("1. Verify the IP addresses are correct")
        print("2. Test SSH connections manually: ssh pi@sculpture1.local")
        print("3. Check that the services are running on the sculptures")
        print("4. Verify network connectivity")
        print("5. Consider setting up SSH key authentication")
        sys.exit(1)

if __name__ == "__main__":
    main() 