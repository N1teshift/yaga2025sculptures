#!/usr/bin/env python3
"""
LiquidSoapClient module for server-agent
Handles communication with Liquidsoap via telnet
"""

import logging
import socket

# Import configuration
from config import LIQUIDSOAP_HOST, LIQUIDSOAP_PORT

logger = logging.getLogger(__name__)

class LiquidSoapClient:
    """Simple client to communicate with Liquidsoap via telnet."""
    
    def __init__(self, host=None, port=None):
        self.host = host or LIQUIDSOAP_HOST
        self.port = port or LIQUIDSOAP_PORT
    
    def send_command(self, command, *args):
        """Send a command to Liquidsoap via telnet."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # 5 second timeout
                sock.connect((self.host, self.port))
                
                # Build command with arguments
                if args:
                    full_command = f"{command} {' '.join(str(arg) for arg in args)}"
                else:
                    full_command = command
                
                # Send command
                sock.sendall(f"{full_command}\n".encode())
                
                # Read response
                response = sock.recv(1024).decode().strip()
                return response
        except Exception as e:
            logger.error(f"[LIQUIDSOAP] Failed to send command to Liquidsoap: {e}")
            return None
    
    def set_plan(self, plan):
        """Set the current plan in Liquidsoap."""
        logger.info(f"[LIQUIDSOAP] Setting plan to {plan}")
        return self.send_command(f"set_plan {plan}")
    
    def get_plan(self):
        """Get the current plan from Liquidsoap."""
        return self.send_command("get_plan")
    
    def test_connection(self):
        """Test the connection to Liquidsoap."""
        try:
            response = self.send_command("help")
            if response:
                logger.info(f"[LIQUIDSOAP] Connection test successful")
                return True
            else:
                logger.error(f"[LIQUIDSOAP] Connection test failed - no response")
                return False
        except Exception as e:
            logger.error(f"[LIQUIDSOAP] Connection test failed: {e}")
            return False 