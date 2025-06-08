#!/bin/bash
#
# VMA Monitoring System - Final Clean Implementation
# Uses ECHO method: rtl_fm → redsea -e → RDS pipe + audio recorder
#

# ========================================
# CONFIGURATION
# ========================================
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Radio parameters
FREQUENCY=103300000    # P4 Stockholm 103.3 MHz  
SAMPLE_RATE=171000     # 171k works perfectly with redsea
GAIN=30                # dB
PPM_CORRECTION=50      # frequency correction

# Paths
REDSEA_PATH="/home/chris/redsea/build/redsea"
RDS_PIPE="/tmp/vma_rds_data"

# Process tracking
RTL_FM_PID=""
RDS_LOGGER_PID=""
AUDIO_RECORDER_PID=""

# ========================================
# UTILITY FUNCTIONS
# ========================================
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        log_message "❌ ERROR: Required command '$1' not found"
        exit 1
    fi
}

cleanup_processes() {
    log_message "Cleaning up processes..."
    
    # Kill related processes
    if [[ -n "$RTL_FM_PID" ]] && kill -0 "$RTL_FM_PID" 2>/dev/null; then
        kill -TERM "$RTL_FM_PID"
    fi
    if [[ -n "$RDS_LOGGER_PID" ]] && kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
        kill -TERM "$RDS_LOGGER_PID"
    fi
    if [[ -n "$AUDIO_RECORDER_PID" ]] && kill -0 "$AUDIO_RECORDER_PID" 2>/dev/null; then
        kill -TERM "$AUDIO_RECORDER_PID"
    fi
    
    # Kill by name as backup
    pkill -f "rtl_fm.*103300000" 2>/dev/null || true
    pkill -f "redsea" 2>/dev/null || true
    pkill -f "rds_logger.py" 2>/dev/null || true
    pkill -f "audio_recorder.py" 2>/dev/null || true
    
    # Remove named pipes
    if [[ -e "$RDS_PIPE" ]]; then
        rm -f "$RDS_PIPE"
    fi
    
    log_message "Cleanup complete"
}

# Signal handlers
trap cleanup_processes EXIT
trap cleanup_processes SIGINT
trap cleanup_processes SIGTERM

# ========================================
# STARTUP VALIDATION
# ========================================
log_message "🚀 VMA Monitoring System - Final Clean Implementation"
log_message "======================================================="
log_message "Project directory: $PROJECT_DIR"

# Check dependencies
log_message "Checking system requirements..."
check_dependency "rtl_fm"
check_dependency "python3"
check_dependency "mkfifo"
check_dependency "sox"

# Check redsea
if [[ ! -x "$REDSEA_PATH" ]]; then
    log_message "❌ ERROR: Redsea not found at $REDSEA_PATH"
    exit 1
fi

# Check RTL-SDR
if ! rtl_test -t &>/dev/null; then
    log_message "❌ ERROR: No RTL-SDR device found"
    exit 1
fi

# Check Python scripts
for script in "rds_logger.py" "audio_recorder.py"; do
    if [[ ! -f "$PROJECT_DIR/$script" ]]; then
        log_message "❌ ERROR: Required script not found: $script"
        exit 1
    fi
done

log_message "All requirements satisfied ✅"

# ========================================
# CLEANUP AND PREPARE
# ========================================
log_message "Cleaning up any existing processes..."
cleanup_processes
sleep 2

# Create RDS pipe
log_message "Creating RDS data pipe..."
if ! mkfifo "$RDS_PIPE" 2>/dev/null; then
    log_message "❌ ERROR: Failed to create RDS pipe: $RDS_PIPE"
    exit 1
fi
log_message "RDS pipe created: $RDS_PIPE ✅"

# ========================================
# START RDS LOGGER (reads from pipe)
# ========================================
log_message "Starting RDS Logger..."
python3 "$PROJECT_DIR/rds_logger.py" < "$RDS_PIPE" &
RDS_LOGGER_PID=$!

if ! kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
    log_message "❌ ERROR: Failed to start RDS Logger"
    exit 1
fi
log_message "RDS Logger started (PID: $RDS_LOGGER_PID) ✅"

# ========================================
# START ECHO PIPELINE
# ========================================
log_message "Starting ECHO pipeline..."
log_message "Pipeline: rtl_fm → redsea -e → audio_recorder"
log_message "RDS flow: stderr → $RDS_PIPE → rds_logger.py"
log_message "Audio flow: stdout → audio_recorder.py"

# Start the ECHO pipeline:
# rtl_fm → redsea -e 2> rds_pipe | audio_recorder
{
    rtl_fm -f $FREQUENCY -M fm -l 0 -A std -p $PPM_CORRECTION -s $SAMPLE_RATE -g $GAIN -F 9 - | \
    "$REDSEA_PATH" -e -r $SAMPLE_RATE 2> "$RDS_PIPE" | \
    python3 "$PROJECT_DIR/audio_recorder.py"
} &

# Get process IDs
sleep 3
RTL_FM_PID=$(pgrep -f "rtl_fm.*$FREQUENCY")
AUDIO_RECORDER_PID=$(pgrep -f "audio_recorder.py")

# Verify components started
if [[ -z "$RTL_FM_PID" ]]; then
    log_message "❌ ERROR: RTL_FM failed to start"
    exit 1
fi
log_message "RTL_FM started (PID: $RTL_FM_PID) ✅"

if ! pgrep -f "redsea" &>/dev/null; then
    log_message "❌ WARNING: Redsea process not detected"
else
    log_message "Redsea process detected ✅"
fi

if [[ -z "$AUDIO_RECORDER_PID" ]]; then
    log_message "❌ WARNING: Audio recorder not detected"
else
    log_message "Audio recorder started (PID: $AUDIO_RECORDER_PID) ✅"
fi

# Check RDS pipe
if [[ -p "$RDS_PIPE" ]]; then
    log_message "RDS pipe ready ✅"
else
    log_message "❌ WARNING: RDS pipe issue"
fi

# ========================================
# SYSTEM READY
# ========================================
log_message ""
log_message "🎯 VMA Monitoring System Active - ECHO Implementation"
log_message "====================================================="
log_message "RTL_FM Process: PID $RTL_FM_PID"
log_message "RDS Logger: PID $RDS_LOGGER_PID"
log_message "Audio Recorder: PID $AUDIO_RECORDER_PID"
log_message "Frequency: $(echo "scale=1; $FREQUENCY/1000000" | bc) MHz (P4 Stockholm)"
log_message ""
log_message "ECHO Method:"
log_message "  rtl_fm → redsea -e → audio_recorder.py"
log_message "  RDS: stderr → named pipe → rds_logger.py"
log_message "  Audio: stdout → real-time recording"
log_message "  Coordination: Control pipe for start/stop commands"
log_message ""
log_message "Features:"
log_message "  ✅ Fixed event detection (ignores null TA values)"
log_message "  ✅ Real-time audio recording with pre-trigger buffer"
log_message "  ✅ Complete event logging (start + end)"
log_message "  ✅ VMA and traffic announcement detection"
log_message ""
log_message "Log files:"
log_message "  RDS: logs/rds_continuous_$(date +%Y%m%d).log"
log_message "  System: logs/system_$(date +%Y%m%d).log"
log_message "  Events: logs/rds_event_*.log"
log_message "  Audio: logs/audio/audio_*.wav"
log_message ""
log_message "System ready for VMA and traffic announcements! 🎧"
log_message "Press Ctrl+C to stop the entire system"
log_message ""

# ========================================
# MONITOR SYSTEM HEALTH
# ========================================
while true; do
    # Check RTL_FM
    if [[ -n "$RTL_FM_PID" ]] && ! kill -0 "$RTL_FM_PID" 2>/dev/null; then
        log_message "❌ RTL_FM process died, shutting down"
        break
    fi
    
    # Check RDS Logger
    if [[ -n "$RDS_LOGGER_PID" ]] && ! kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
        log_message "❌ RDS Logger process died, shutting down"
        break
    fi
    
    # Check Redsea
    if ! pgrep -f "redsea" &>/dev/null; then
        log_message "❌ Redsea process died, shutting down"
        break
    fi
    
    # Check RDS pipe
    if [[ ! -p "$RDS_PIPE" ]]; then
        log_message "❌ RDS pipe disappeared, shutting down"
        break
    fi
    
    # Status update every 2 minutes
    sleep 120
    log_file="$PROJECT_DIR/logs/rds_continuous_$(date +%Y%m%d).log"
    if [[ -f "$log_file" ]]; then
        file_size=$(stat -c%s "$log_file" 2>/dev/null || echo "0")
        file_size_kb=$((file_size / 1024))
        log_message "Status: RDS log ${file_size_kb}KB | System running normally"
    fi
done

log_message "System monitoring ended"
