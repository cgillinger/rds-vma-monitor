#!/usr/bin/env python3
"""
VMA Project - Configuration with Adjusted Filter (15s minimum)
OVERWRITES: ~/rds_logger3/config.py
"""

import os
from datetime import datetime

# ========================================
# PROJECT PATHS
# ========================================
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
AUDIO_DIR = os.path.join(LOGS_DIR, "audio")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ========================================
# RTL-SDR & RADIO CONFIGURATION
# ========================================
FREQUENCY = 103300000  # 103.3 MHz P4 Stockholm
SAMPLE_RATE = 171000   # 171k Hz - perfect for redsea RDS decoding
GAIN = 30              # dB
PPM_CORRECTION = 50    # frequency correction

# ========================================
# REDSEA ECHO CONFIGURATION  
# ========================================
REDSEA_PATH = "/home/chris/redsea/build/redsea"
RDS_PIPE = "/tmp/vma_rds_data"  # Named pipe for RDS data from redsea stderr
AUDIO_CONTROL_PIPE = "/tmp/vma_audio_control"  # Control pipe for audio recording

# RDS monitoring
RDS_MONITOR_FIELDS = ['ta', 'pty', 'prog_type', 'ps', 'rt', 'pi', 'ews', 'group']
VMA_PTY_CODES = [30, 31]  # PTY 30 = test VMA, PTY 31 = real VMA emergency
VMA_KEYWORDS = ['VMA', 'Viktigt meddelande', 'viktigt meddelande', 'Faran över']

# ========================================
# AUDIO CONFIGURATION
# ========================================
# Input from redsea -e
INPUT_SAMPLE_RATE = 171000    
INPUT_FORMAT = "signed"       
INPUT_BITS = 16               
INPUT_CHANNELS = 1            # Mono

# Output WAV files
AUDIO_SAMPLE_RATE = 48000     
AUDIO_FORMAT = "S16_LE"       
AUDIO_CHANNELS = 1            

# Pre-trigger buffer
PRE_TRIGGER_BUFFER_SECONDS = 1  # 1 second of pre-recording

# ========================================
# EVENT DETECTION - UPDATED FILTER
# ========================================
EVENT_TIMEOUT_SECONDS = 0.5  # Short timeout for quick TA transitions
MIN_EVENT_DURATION_SECONDS = 15  # UPDATED: More realistic filter (was 30s)
MAX_EVENT_DURATION_SECONDS = 600  # 10 minutes emergency stop

# ========================================
# LOGGING
# ========================================
LOG_DATE_FORMAT = "%Y%m%d"
LOG_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

today = datetime.now().strftime(LOG_DATE_FORMAT)
SYSTEM_LOG_FILE = os.path.join(LOGS_DIR, f"system_{today}.log")
RDS_CONTINUOUS_LOG = os.path.join(LOGS_DIR, f"rds_continuous_{today}.log")

# ========================================
# HELPER FUNCTIONS
# ========================================
def get_audio_filename(event_type: str, timestamp: str = None) -> str:
    if timestamp is None:
        timestamp = datetime.now().strftime(LOG_TIMESTAMP_FORMAT)
    filename = f"audio_{event_type}_{timestamp}.wav"
    return os.path.join(AUDIO_DIR, filename)

def get_event_log_filename(event_type: str, timestamp: str = None) -> str:
    if timestamp is None:
        timestamp = datetime.now().strftime(LOG_TIMESTAMP_FORMAT)
    filename = f"rds_event_{event_type}_{timestamp}.log"
    return os.path.join(LOGS_DIR, filename)

def validate_config() -> list:
    errors = []
    
    if not os.path.isfile(REDSEA_PATH):
        errors.append(f"Redsea not found: {REDSEA_PATH}")
    elif not os.access(REDSEA_PATH, os.X_OK):
        errors.append(f"Redsea not executable: {REDSEA_PATH}")
    
    for directory in [LOGS_DIR, AUDIO_DIR]:
        if not os.path.isdir(directory):
            errors.append(f"Directory missing: {directory}")
        elif not os.access(directory, os.W_OK):
            errors.append(f"Directory not writable: {directory}")
    
    if not (80000000 <= FREQUENCY <= 110000000):
        errors.append(f"Invalid frequency: {FREQUENCY} Hz")
    
    return errors

# ========================================
# MODULE INFO
# ========================================
__version__ = "3.2.0"
__description__ = "VMA Project - With 15s Duration Filter (Realistic for Swedish Traffic)"