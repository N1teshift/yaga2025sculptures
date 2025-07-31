#!/usr/bin/env python3

import os
import subprocess
import logging
import time
import re

logger = logging.getLogger(__name__)

SIMULATION = os.environ.get("SIMULATION", "0") == "1"


class StatusCollector:
    """Handles system status collection including CPU, temperature, and metrics."""

    def __init__(self, sculpture_id):
        self.sculpture_id = sculpture_id
        self._proc_stat_prev = None  # (idle, total) snapshot for /proc/stat delta

    def get_cpu_usage(self):
        """CPU usage % from /proc/stat (works in containers; no `top` parsing)."""
        try:
            with open('/proc/stat') as f:
                line = f.readline()
            parts = list(map(int, line.split()[1:]))  # user nice system idle iowait irq softirq steal
            idle = parts[3] + (parts[5] if len(parts) > 5 else 0)
            total = sum(parts)
            if self._proc_stat_prev is not None:
                prev_idle, prev_total = self._proc_stat_prev
                d_idle = idle - prev_idle
                d_total = total - prev_total
                cpu_usage = 0.0 if d_total == 0 else 100.0 * (d_total - d_idle) / d_total
            else:
                cpu_usage = 0.0
            self._proc_stat_prev = (idle, total)
            return round(cpu_usage, 1), None
        except Exception as e:
            logger.debug(f"Failed to get CPU usage (non-Linux?): {e}")
            return 0.0, str(e)

    def get_temperature(self):
        """Temperature in Celsius. Tries vcgencmd; falls back to a sim value."""
        if SIMULATION:
            return round(42.0 + 3.0 * (self.get_cpu_usage()[0] / 100.0), 1)
        try:
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'],
                                         capture_output=True, text=True, check=True)
            return float(temp_result.stdout.strip().replace('temp=', '').replace("'C", ''))
        except Exception as e:
            logger.debug(f"vcgencmd unavailable, temp unknown: {e}")
            return 0.0

    def build_status(self, current_mode, is_muted, mic_level, output_level, current_plan=None, error_message=None):
        cpu_usage, cpu_error = self.get_cpu_usage()
        temperature = self.get_temperature()

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

        if current_plan:
            status['plan'] = current_plan

        if error_message:
            status['error'] = error_message

        return status
