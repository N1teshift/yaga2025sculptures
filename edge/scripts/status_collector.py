#!/usr/bin/env python3

import subprocess
import logging
import time
import re

logger = logging.getLogger(__name__)

class StatusCollector:
    """Handles system status collection including CPU, temperature, and metrics."""
    
    def __init__(self, sculpture_id):
        self.sculpture_id = sculpture_id
        
    def get_cpu_usage(self):
        """Get CPU usage percentage."""
        try:
            cpu_result = subprocess.run(['top', '-bn1'], capture_output=True, text=True, check=True)
            cpu_line = next((line for line in cpu_result.stdout.split('\n') if 'Cpu(s)' in line), None)

            if cpu_line:
                try:
                    # More robust CPU parsing to handle different 'top' formats
                    match = re.search(r'(\d+[\.,]\d+)\s*us', cpu_line)
                    if match:
                        cpu_usage = float(match.group(1).replace(',', '.'))
                    else:
                        # Fallback for formats like "2.5% us"
                        parts = cpu_line.replace(',', ' ').split()
                        try:
                            us_index = parts.index('us')
                            cpu_usage = float(parts[us_index - 1])
                        except (ValueError, IndexError):
                            raise ValueError("Could not find 'us' CPU value.")
                except (ValueError, IndexError) as e:
                    error_message = f"Could not parse CPU usage from 'top' output: '{cpu_line}'. Error: {e}"
                    logger.warning(error_message + " Defaulting to 0.")
                    return 0.0, error_message
            else:
                logger.warning("Could not find 'Cpu(s)' line in top output.")
                return 0.0, None
                
            return cpu_usage, None
        except Exception as e:
            logger.error(f"Failed to get CPU usage: {e}")
            return 0.0, str(e)
    
    def get_temperature(self):
        """Get system temperature in Celsius."""
        try:
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, check=True)
            temp_str = temp_result.stdout.strip().replace('temp=', '').replace("'C", '')
            temperature = float(temp_str)
            return temperature
        except Exception as e:
            logger.error(f"Failed to get temperature: {e}")
            return 0.0
    
    def build_status(self, current_mode, is_muted, mic_level, output_level, error_message=None):
        """Build the complete status dictionary."""
        cpu_usage, cpu_error = self.get_cpu_usage()
        temperature = self.get_temperature()
        
        # Use CPU error if no other error provided
        if error_message is None:
            error_message = cpu_error
        
        status = {
            'id': self.sculpture_id,
            'cpu': round(cpu_usage),
            'temp': round(temperature),
            'mic': round(mic_level),
            'output': round(output_level),
            'mode': current_mode,
            'is_muted': is_muted,
            'time': round(time.time())
        }
        
        if error_message:
            status['error'] = error_message
            
        return status 