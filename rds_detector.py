#!/usr/bin/env python3
"""
RDS Event Detector - Updated with VMA Support + VMA START Force Fix
OVERWRITES: ~/rds_logger3/rds_detector.py
"""

import logging
import os
import threading
import time
from enum import Enum
from datetime import datetime, timedelta
from config import EVENT_TIMEOUT_SECONDS, MIN_EVENT_DURATION_SECONDS, MIN_VMA_DURATION_SECONDS

logger = logging.getLogger(__name__)

class EventType(Enum):
    TRAFFIC_START = "traffic_start"
    TRAFFIC_END = "traffic_end"
    TRAFFIC_TIMEOUT = "traffic_timeout"  # Emergency stop
    VMA_START = "vma_start"
    VMA_END = "vma_end"
    VMA_TEST_START = "vma_test_start"
    VMA_TEST_END = "vma_test_end"
    PROGRAM_CHANGE = "program_change"

def is_start_event(event_type: EventType) -> bool:
    return event_type.value.endswith('_start')

def is_end_event(event_type: EventType) -> bool:
    return event_type.value.endswith('_end') or event_type == EventType.TRAFFIC_TIMEOUT

def is_vma_event(event_type: EventType) -> bool:
    """Check if event is VMA-related (should bypass timeout)"""
    return 'vma' in event_type.value.lower()

class RDSEventDetector:
    """
    RDS Event Detector with Emergency Stop System + VMA Support
    
    FILTER 1: Duration - Events must be ≥15 seconds (Traffic) or ≥10 seconds (VMA)
    FILTER 2: RDS Continuity - Must have RDS data every 30 seconds  
    EMERGENCY: Maximum 10 minutes - Force stop runaway recordings
    
    CRITICAL: VMA events NEVER suppressed by timeout - they are always critical!
    """
    
    def __init__(self, event_callback=None):
        self.event_callback = event_callback
        self.previous_state = {}
        self.current_state = {}
        self.last_event_time = None
        self.event_timeout = timedelta(seconds=EVENT_TIMEOUT_SECONDS)
        self.events_detected = 0
        
        # Track last valid TA state (ignoring nulls)
        self.last_valid_ta_state = None
        
        # DUAL FILTER SYSTEM - UPDATED with VMA support
        self.current_traffic_start_time = None
        self.min_traffic_duration_seconds = MIN_EVENT_DURATION_SECONDS  # 15s for traffic
        
        # VMA event type tracking
        self.current_event_type = 'traffic'  # Default to traffic
        
        # RDS CONTINUITY TRACKING
        self.rds_timestamps_during_event = []
        self.max_rds_gap_seconds = 30
        
        # EMERGENCY STOP SYSTEM
        self.max_traffic_duration_seconds = 600  # 10 minutes MAX
        self.timeout_timer = None
        self.emergency_stops = 0
        
        # Statistics
        self.filtered_events = 0
        self.duration_filtered = 0
        self.continuity_filtered = 0
        self.timeout_events = 0
        
        logger.info("RDSEventDetector initialized with VMA SUPPORT + VMA TIMEOUT BYPASS")
        logger.info(f"Filter 1 - Traffic duration: {self.min_traffic_duration_seconds} seconds")
        logger.info(f"Filter 1 - VMA duration: {MIN_VMA_DURATION_SECONDS} seconds")
        logger.info(f"Filter 2 - RDS continuity: Max {self.max_rds_gap_seconds}s gap")
        logger.info(f"EMERGENCY - Maximum duration: {self.max_traffic_duration_seconds} seconds (10 min)")
        logger.info("CRITICAL: VMA events bypass timeout to ensure they are NEVER suppressed")
    
    def process_rds_data(self, rds_data: dict):
        """Process RDS data and detect events"""
        if not rds_data:
            return
            
        self.previous_state = self.current_state.copy()
        self.current_state.update(rds_data)
        
        # Track RDS messages during active traffic events
        if self.current_traffic_start_time:
            self.rds_timestamps_during_event.append(datetime.now())
        
        self._detect_traffic_events()
        self._detect_vma_events()
        self._detect_program_changes()
    
    def _detect_traffic_events(self):
        """Detect traffic announcement events with dual filtering"""
        current_ta = self.current_state.get('ta')
        
        # IGNORE null values completely
        if current_ta is None:
            return
        
        # Only process boolean values
        if current_ta not in [True, False]:
            return
        
        # Skip if this is the first valid TA value
        if self.last_valid_ta_state is None:
            self.last_valid_ta_state = current_ta
            logger.debug(f"First valid TA state: {current_ta}")
            return
        
        # Check for genuine state change
        if self.last_valid_ta_state != current_ta:
            logger.debug(f"TA change: {self.last_valid_ta_state} → {current_ta}")
            
            if current_ta is True:  # false → true = traffic starts
                self._handle_traffic_start()
                
            elif current_ta is False:  # true → false = traffic ends
                self._handle_traffic_end()
            
            # Update last valid state
            self.last_valid_ta_state = current_ta
    
    def _handle_traffic_start(self):
        """Handle traffic start with emergency timer + VMA event type tracking"""
        
        # CRITICAL FIX: Skip traffic events if PTY indicates VMA is active
        current_pty = self.current_state.get('pty')
        if current_pty in [30, 31]:
            logger.info(f"🚨 Skipping traffic start - PTY {current_pty} indicates VMA is active")
            logger.info("🚨 VMA events take priority over TA-based traffic detection")
            return
        
        self.current_traffic_start_time = datetime.now()
        self.rds_timestamps_during_event = [self.current_traffic_start_time]
        
        # Track event type for duration filtering
        if self.current_state.get('pty') in [30, 31]:
            self.current_event_type = 'vma'
        else:
            self.current_event_type = 'traffic'
        
        # START EMERGENCY TIMER
        self._start_emergency_timer()
        
        event_type = EventType.TRAFFIC_START
        trigger = "ta_activated"
        
        logger.info(f"🚦 {self.current_event_type.upper()} start detected: false → true")
        logger.info(f"⏱️ Emergency timer started: {self.max_traffic_duration_seconds}s")
        
        # Always trigger start event (recording begins)
        self._trigger_event(event_type, {
            'trigger': trigger,
            'ta_state': True,
            'rds_data': self.current_state.copy(),
            'start_time': self.current_traffic_start_time.isoformat(),
            'event_type': self.current_event_type
        })
    
    def _start_emergency_timer(self):
        """Start emergency timer to force-stop runaway events"""
        # Cancel any existing timer
        if self.timeout_timer:
            self.timeout_timer.cancel()
        
        # Start new timer
        self.timeout_timer = threading.Timer(
            self.max_traffic_duration_seconds, 
            self._emergency_timeout
        )
        self.timeout_timer.start()
        
        logger.info(f"🚨 Emergency timer armed: {self.max_traffic_duration_seconds}s")
    
    def _emergency_timeout(self):
        """Emergency timeout - force stop runaway recording"""
        logger.error(f"🚨 EMERGENCY TIMEOUT TRIGGERED!")
        logger.error(f"🚨 Event exceeded {self.max_traffic_duration_seconds}s maximum")
        logger.error(f"🚨 RDS signal likely stuck - forcing event end")
        
        self.emergency_stops += 1
        self.timeout_events += 1
        
        # Force trigger timeout event - this is an END event so it bypasses timeout
        self._trigger_event(EventType.TRAFFIC_TIMEOUT, {
            'trigger': 'emergency_timeout',
            'ta_state': None,  # Unknown state
            'rds_data': self.current_state.copy(),
            'duration_seconds': self.max_traffic_duration_seconds,
            'filtered': True,
            'reason': f'Emergency timeout after {self.max_traffic_duration_seconds}s',
            'emergency': True
        }, force=True)  # Force to bypass timeout
        
        # Reset state
        self.current_traffic_start_time = None
        self.rds_timestamps_during_event = []
        self.timeout_timer = None
        self.current_event_type = 'traffic'
    
    def _handle_traffic_end(self):
        """Handle traffic end with dual filter system + VMA duration support"""
        # CANCEL EMERGENCY TIMER
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None
            logger.info(f"🚨 Emergency timer cancelled - normal end detected")
        
        end_time = datetime.now()
        
        # Calculate duration if we have start time
        duration_seconds = None
        if self.current_traffic_start_time:
            duration = end_time - self.current_traffic_start_time
            duration_seconds = duration.total_seconds()
            
            logger.info(f"🚦 {self.current_event_type.upper()} end detected: true → false")
            logger.info(f"⏱️ Duration: {duration_seconds:.1f} seconds")
            
            # DUAL FILTER CHECK
            filter_reasons = []
            
            # FILTER 1: Duration check - different thresholds for VMA vs Traffic
            current_event_type = getattr(self, 'current_event_type', 'traffic')
            if 'vma' in current_event_type.lower():
                min_duration = MIN_VMA_DURATION_SECONDS
            else:
                min_duration = self.min_traffic_duration_seconds

            if duration_seconds < min_duration:
                filter_reasons.append(f"Duration {duration_seconds:.1f}s < minimum {min_duration}s")
                self.duration_filtered += 1
            
            # FILTER 2: RDS Continuity check
            continuity_ok = self._check_rds_continuity()
            if not continuity_ok:
                filter_reasons.append(f"RDS gaps > {self.max_rds_gap_seconds}s detected")
                self.continuity_filtered += 1
            
            # Determine if event should be filtered
            should_filter = len(filter_reasons) > 0
            
            if should_filter:
                logger.warning(f"🗑️ DUAL FILTER TRIGGERED:")
                for reason in filter_reasons:
                    logger.warning(f"🗑️   - {reason}")
                self.filtered_events += 1
                
                # Trigger filtered end event - MUST go through to stop recording!
                self._trigger_event(EventType.TRAFFIC_END, {
                    'trigger': 'ta_deactivated',
                    'ta_state': False,
                    'rds_data': self.current_state.copy(),
                    'duration_seconds': duration_seconds,
                    'filtered': True,
                    'filter_reasons': filter_reasons,
                    'reason': '; '.join(filter_reasons),
                    'event_type': self.current_event_type
                }, force=True)  # Force END events through!
            else:
                # Event passed both filters
                logger.info(f"✅ DUAL FILTER PASSED - Valid {self.current_event_type} event")
                logger.info(f"✅   Duration: {duration_seconds:.1f}s OK")
                logger.info(f"✅   RDS continuity: OK")
                
                self._trigger_event(EventType.TRAFFIC_END, {
                    'trigger': 'ta_deactivated',
                    'ta_state': False,
                    'rds_data': self.current_state.copy(),
                    'duration_seconds': duration_seconds,
                    'filtered': False,
                    'event_type': self.current_event_type
                }, force=True)  # Force END events through!
        
        # Reset tracking for next event
        self.current_traffic_start_time = None
        self.rds_timestamps_during_event = []
        self.current_event_type = 'traffic'
    
    def _check_rds_continuity(self):
        """Check if RDS data was continuous during the event"""
        if len(self.rds_timestamps_during_event) < 2:
            logger.warning("🔍 RDS continuity: Insufficient data points")
            return False
        
        # Check gaps between consecutive RDS messages
        max_gap_found = 0
        gap_count = 0
        
        for i in range(1, len(self.rds_timestamps_during_event)):
            gap = (self.rds_timestamps_during_event[i] - self.rds_timestamps_during_event[i-1]).total_seconds()
            if gap > self.max_rds_gap_seconds:
                gap_count += 1
                max_gap_found = max(max_gap_found, gap)
        
        total_event_time = (self.rds_timestamps_during_event[-1] - self.rds_timestamps_during_event[0]).total_seconds()
        rds_message_count = len(self.rds_timestamps_during_event)
        
        logger.info(f"🔍 RDS continuity analysis:")
        logger.info(f"🔍   Total RDS messages: {rds_message_count}")
        logger.info(f"🔍   Event duration: {total_event_time:.1f}s")
        logger.info(f"🔍   Large gaps (>{self.max_rds_gap_seconds}s): {gap_count}")
        if gap_count > 0:
            logger.info(f"🔍   Largest gap: {max_gap_found:.1f}s")
        
        # Fail if we found significant gaps
        if gap_count > 0:
            logger.warning(f"🔍 RDS continuity FAILED: {gap_count} gaps > {self.max_rds_gap_seconds}s")
            return False
        
        logger.info(f"🔍 RDS continuity PASSED: No gaps > {self.max_rds_gap_seconds}s")
        return True
    
    def _detect_vma_events(self):
        """Detect VMA events based on PTY codes"""
        prev_pty = self.previous_state.get('pty')
        curr_pty = self.current_state.get('pty')
        
        # Ignore null values
        if curr_pty is None:
            return
        
        # VMA start detection
        if curr_pty in [30, 31] and prev_pty not in [30, 31]:
            if curr_pty == 30:
                event_type = EventType.VMA_TEST_START
            else:
                event_type = EventType.VMA_START
                
            logger.info(f"🚨 VMA detected: PTY → {curr_pty}")
            
            # VMA START events MUST force through - they are critical!
            self._trigger_event(event_type, {
                'trigger': f'pty_{curr_pty}_activated',
                'pty_code': curr_pty,
                'rds_data': self.current_state.copy()
            }, force=True)  # FORCE VMA START EVENTS THROUGH!
        
        # VMA end detection
        elif prev_pty in [30, 31] and curr_pty not in [30, 31]:
            if prev_pty == 30:
                event_type = EventType.VMA_TEST_END
            else:
                event_type = EventType.VMA_END
                
            logger.info(f"🚨 VMA ended: PTY {prev_pty} → {curr_pty}")
                
            self._trigger_event(event_type, {
                'trigger': f'pty_{prev_pty}_deactivated',
                'prev_pty_code': prev_pty,
                'rds_data': self.current_state.copy()
            }, force=True)  # Force VMA end events through
    
    def _detect_program_changes(self):
        """Detect program changes"""
        # Station change
        prev_pi = self.previous_state.get('pi')
        curr_pi = self.current_state.get('pi')
        
        if prev_pi and curr_pi and prev_pi != curr_pi:
            logger.debug(f"Station change: {prev_pi} → {curr_pi}")
            self._trigger_event(EventType.PROGRAM_CHANGE, {
                'trigger': 'station_change',
                'previous_pi': prev_pi,
                'current_pi': curr_pi,
                'rds_data': self.current_state.copy()
            })
    
    def _trigger_event(self, event_type: EventType, event_data: dict, force: bool = False):
        """
        Trigger an event with timeout protection
        
        CRITICAL: VMA events and End events bypass timeout to ensure they NEVER get suppressed!
        """
        now = datetime.now()
        
        # CRITICAL FIX: VMA events and End events must ALWAYS go through
        is_critical_event = force or is_vma_event(event_type) or is_end_event(event_type)
        
        if not is_critical_event:
            # Only apply timeout to non-critical events (regular traffic starts)
            if (self.last_event_time and 
                now - self.last_event_time < self.event_timeout):
                logger.debug(f"Event {event_type.value} suppressed (timeout)")
                return
        else:
            # Critical events bypass timeout
            event_priority = "VMA" if is_vma_event(event_type) else "END"
            logger.debug(f"Event {event_type.value} forced through ({event_priority} event)")
        
        self.last_event_time = now
        self.events_detected += 1
        
        event_data['event_time'] = now.isoformat()
        event_data['event_type'] = event_type.value
        
        # Log different event types appropriately
        if event_type == EventType.TRAFFIC_TIMEOUT:
            logger.error(f"🚨 EMERGENCY: {event_type.value} - {event_data.get('reason', 'Unknown')}")
        elif event_data.get('filtered'):
            filter_reasons = event_data.get('filter_reasons', [])
            logger.warning(f"🗑️ FILTERED Event: {event_type.value}")
            for reason in filter_reasons:
                logger.warning(f"🗑️   Reason: {reason}")
        else:
            log_prefix = "🚨" if is_vma_event(event_type) else "🎯"
            logger.info(f"{log_prefix} Event detected: {event_type.value} (trigger: {event_data.get('trigger')})")
        
        if self.event_callback:
            try:
                self.event_callback(event_type, event_data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        # Cancel any running timer
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None
            logger.info("Emergency timer cancelled on cleanup")
    
    def get_stats(self) -> dict:
        """Get detector statistics with emergency stop info"""
        total_filtered = self.filtered_events + self.timeout_events
        filter_rate = total_filtered / max(1, self.events_detected)
        
        return {
            'events_detected': self.events_detected,
            'filtered_events': self.filtered_events,
            'timeout_events': self.timeout_events,
            'emergency_stops': self.emergency_stops,
            'duration_filtered': self.duration_filtered,
            'continuity_filtered': self.continuity_filtered,
            'total_filter_rate': filter_rate,
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'current_ta_state': self.last_valid_ta_state,
            'timeout_seconds': self.event_timeout.total_seconds(),
            'min_traffic_duration_filter': self.min_traffic_duration_seconds,
            'min_vma_duration_filter': MIN_VMA_DURATION_SECONDS,
            'max_duration_emergency': self.max_traffic_duration_seconds,
            'max_rds_gap_filter': self.max_rds_gap_seconds
        }