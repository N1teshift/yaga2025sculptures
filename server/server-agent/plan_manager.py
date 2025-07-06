#!/usr/bin/env python3
"""
Plan management module for server-agent
Handles plan state persistence and validation
"""

import json
import time
import os
import logging

# Import configuration
from config import PLAN_STATE_FILE, DEFAULT_PLAN, VALID_PLANS

logger = logging.getLogger(__name__)

class PlanManager:
    """Manages plan state persistence and validation."""
    
    def __init__(self):
        self.current_plan = DEFAULT_PLAN
        self.load_plan_state()
    
    def load_plan_state(self):
        """Load the current plan from persistent storage."""
        try:
            if os.path.exists(PLAN_STATE_FILE):
                with open(PLAN_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.current_plan = data.get('plan', DEFAULT_PLAN)
                    logger.info(f"[PLAN] Loaded plan state: {self.current_plan}")
            else:
                logger.info(f"[PLAN] No saved plan state found, using default: {self.current_plan}")
        except Exception as e:
            logger.error(f"[PLAN] Failed to load plan state: {e}")
            self.current_plan = DEFAULT_PLAN
    
    def save_plan_state(self):
        """Save the current plan to persistent storage."""
        try:
            with open(PLAN_STATE_FILE, 'w') as f:
                json.dump({
                    'plan': self.current_plan, 
                    'timestamp': time.time()
                }, f)
            logger.info(f"[PLAN] Saved plan state: {self.current_plan}")
        except Exception as e:
            logger.error(f"[PLAN] Failed to save plan state: {e}")
    
    def set_plan(self, plan):
        """Set the current plan after validation."""
        if plan in VALID_PLANS:
            old_plan = self.current_plan
            self.current_plan = plan
            self.save_plan_state()
            logger.info(f"[PLAN] Changed plan from {old_plan} to {plan}")
            return True
        else:
            logger.warning(f"[PLAN] Invalid plan: {plan}. Valid plans: {VALID_PLANS}")
            return False
    
    def get_plan(self):
        """Get the current plan."""
        return self.current_plan
    
    def is_valid_plan(self, plan):
        """Check if a plan is valid."""
        return plan in VALID_PLANS
    
    def get_valid_plans(self):
        """Get list of valid plans."""
        return VALID_PLANS.copy()
    
    def get_plan_status(self):
        """Get current plan status for MQTT publishing."""
        return {
            'plan': self.current_plan,
            'timestamp': time.time(),
            'source': 'server-agent-plan-manager'
        } 