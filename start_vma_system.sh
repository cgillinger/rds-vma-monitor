#!/bin/bash
#
# VMA Monitoring System - FÖRBÄTTRAD med USB-reset och robust cleanup
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

# NY: USB-reset funktioner
usb_reset_rtlsdr() {
    log_message "🔧 Resetting RTL-SDR USB interface..."
    
    # Försök hitta RTL-SDR USB-enhet
    USB_DEVICE=$(lsusb | grep -i "rtl\|realtek" | head -1)
    
    if [[ -n "$USB_DEVICE" ]]; then
        # Extrahera bus och device nummer
        BUS=$(echo "$USB_DEVICE" | awk '{print $2}')
        DEV=$(echo "$USB_DEVICE" | awk '{print $4}' | sed 's/://')
        
        # Försök USB reset
        if command -v usbreset &> /dev/null; then
            log_message "📡 USB reset: Bus $BUS Device $DEV"
            sudo usbreset "/dev/bus/usb/$BUS/$DEV" 2>/dev/null || true
        fi
        
        # Alternativ: unload/reload usbcore modules
        if [[ -w /sys/bus/usb/drivers/rtl2832u/unbind ]] 2>/dev/null; then
            echo "1-1:1.0" | sudo tee /sys/bus/usb/drivers/rtl2832u/unbind 2>/dev/null || true
            sleep 1
            echo "1-1:1.0" | sudo tee /sys/bus/usb/drivers/rtl2832u/bind 2>/dev/null || true
        fi
    fi
    
    # Extra väntetid för USB stabilisering
    sleep 3
    log_message "✅ USB reset complete"
}

verify_rtlsdr_ready() {
    log_message "🔍 Verifying RTL-SDR is ready..."
    
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if rtl_test -t &>/dev/null; then
            log_message "✅ RTL-SDR ready (attempt $attempt)"
            return 0
        fi
        
        log_message "⏳ RTL-SDR not ready, attempt $attempt/$max_attempts"
        sleep 2
        ((attempt++))
    done
    
    log_message "❌ RTL-SDR not responding after $max_attempts attempts"
    return 1
}

# FÖRBÄTTRAD: Robust cleanup med korrekt process-ordning
cleanup_processes() {
    log_message "🧹 Starting robust cleanup..."
    
    # STEG 1: Stoppa pipeline i RÄTT ordning (bakifrån)
    # Audio recorder först (slutet av kedjan)
    if [[ -n "$AUDIO_RECORDER_PID" ]] && kill -0 "$AUDIO_RECORDER_PID" 2>/dev/null; then
        log_message "Stopping Audio Recorder (PID: $AUDIO_RECORDER_PID)"
        kill -TERM "$AUDIO_RECORDER_PID"
        sleep 2
        if kill -0 "$AUDIO_RECORDER_PID" 2>/dev/null; then
            kill -KILL "$AUDIO_RECORDER_PID" 2>/dev/null || true
        fi
    fi
    
    # Redsea sedan (mitten av kedjan) 
    local REDSEA_PID=$(pgrep -f "redsea" 2>/dev/null || echo "")
    if [[ -n "$REDSEA_PID" ]]; then
        log_message "Stopping Redsea (PID: $REDSEA_PID)"
        kill -TERM "$REDSEA_PID" 2>/dev/null || true
        sleep 2
        if kill -0 "$REDSEA_PID" 2>/dev/null; then
            kill -KILL "$REDSEA_PID" 2>/dev/null || true
        fi
    fi
    
    # RTL_FM sist (början av kedjan, frigör USB)
    if [[ -n "$RTL_FM_PID" ]] && kill -0 "$RTL_FM_PID" 2>/dev/null; then
        log_message "Stopping RTL_FM (PID: $RTL_FM_PID) - frees USB"
        kill -TERM "$RTL_FM_PID"
        sleep 3  # Extra tid för USB-frigöring
        if kill -0 "$RTL_FM_PID" 2>/dev/null; then
            kill -KILL "$RTL_FM_PID" 2>/dev/null || true
        fi
    fi
    
    # RDS Logger (separat process)
    if [[ -n "$RDS_LOGGER_PID" ]] && kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
        log_message "Stopping RDS Logger (PID: $RDS_LOGGER_PID)"
        kill -TERM "$RDS_LOGGER_PID"
        sleep 2
        if kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
            kill -KILL "$RDS_LOGGER_PID" 2>/dev/null || true
        fi
    fi
    
    # STEG 2: Backup cleanup by name (för "läckta" processer)
    log_message "🔍 Backup cleanup by process name..."
    pkill -f "rtl_fm.*103300000" 2>/dev/null || true
    sleep 1
    pkill -f "redsea" 2>/dev/null || true
    pkill -f "rds_logger.py" 2>/dev/null || true
    pkill -f "audio_recorder.py" 2>/dev/null || true
    
    # STEG 3: USB-återställning
    usb_reset_rtlsdr
    
    # STEG 4: Rensa named pipes
    if [[ -e "$RDS_PIPE" ]]; then
        log_message "🗑️ Removing RDS pipe: $RDS_PIPE"
        rm -f "$RDS_PIPE"
    fi
    
    # STEG 5: Rensa audio control pipes
    rm -f /tmp/vma_audio_control 2>/dev/null || true
    
    log_message "✅ Robust cleanup complete"
}

# Signal handlers
trap cleanup_processes EXIT
trap cleanup_processes SIGINT
trap cleanup_processes SIGTERM

# ========================================
# STARTUP VALIDATION
# ========================================
log_message "🚀 VMA Monitoring System - FÖRBÄTTRAD med USB-reset"
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

# Check Python scripts
for script in "rds_logger.py" "audio_recorder.py"; do
    if [[ ! -f "$PROJECT_DIR/$script" ]]; then
        log_message "❌ ERROR: Required script not found: $script"
        exit 1
    fi
done

log_message "All requirements satisfied ✅"

# ========================================
# ROBUST CLEANUP AND PREPARE
# ========================================
log_message "🧹 Starting robust pre-cleanup..."
cleanup_processes
sleep 5  # LÄNGRE väntetid för USB-stabilisering

# FÖRBÄTTRAT: Verifiera RTL-SDR är redo
if ! verify_rtlsdr_ready; then
    log_message "🔧 RTL-SDR not ready, attempting USB reset..."
    usb_reset_rtlsdr
    
    if ! verify_rtlsdr_ready; then
        log_message "❌ ERROR: RTL-SDR not accessible after reset"
        exit 1
    fi
fi

# FÖRBÄTTRAT: Robust named pipe creation
log_message "Creating RDS data pipe..."
if [[ -e "$RDS_PIPE" ]]; then
    log_message "🗑️ Removing existing RDS pipe"
    rm -f "$RDS_PIPE"
fi

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

# FÖRBÄTTRAT: Längre verifiering
sleep 2
if ! kill -0 "$RDS_LOGGER_PID" 2>/dev/null; then
    log_message "❌ ERROR: Failed to start RDS Logger"
    exit 1
fi
log_message "RDS Logger started (PID: $RDS_LOGGER_PID) ✅"

# ========================================
# START ECHO PIPELINE
# ========================================
log_message "Starting ROBUST ECHO pipeline..."
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

# FÖRBÄTTRAT: Längre process startup verification
log_message "⏳ Waiting for pipeline processes to stabilize..."
sleep 5  # Längre stabiliseringstid

RTL_FM_PID=$(pgrep -f "rtl_fm.*$FREQUENCY")
AUDIO_RECORDER_PID=$(pgrep -f "audio_recorder.py")

# ROBUST: Verify components started
if [[ -z "$RTL_FM_PID" ]]; then
    log_message "❌ ERROR: RTL_FM failed to start"
    log_message "🔧 This usually indicates USB interface issues"
    cleanup_processes
    exit 1
fi
log_message "RTL_FM started (PID: $RTL_FM_PID) ✅"

# Extra verifiering av RTL_FM
sleep 2
if ! kill -0 "$RTL_FM_PID" 2>/dev/null; then
    log_message "❌ ERROR: RTL_FM died immediately after start"
    log_message "🔧 USB interface problem detected"
    cleanup_processes
    exit 1
fi

if ! pgrep -f "redsea" &>/dev/null; then
    log_message "❌ WARNING: Redsea process not detected"
    log_message "🔧 Pipeline may be broken"
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
log_message "🎯 VMA Monitoring System Active - FÖRBÄTTRAD IMPLEMENTATION"
log_message "========================================================"
log_message "RTL_FM Process: PID $RTL_FM_PID"
log_message "RDS Logger: PID $RDS_LOGGER_PID"
log_message "Audio Recorder: PID $AUDIO_RECORDER_PID"
log_message "Frequency: $(echo "scale=1; $FREQUENCY/1000000" | bc) MHz (P4 Stockholm)"
log_message ""
log_message "FÖRBÄTTRINGAR:"
log_message "  ✅ USB-reset vid start och stopp"
log_message "  ✅ Robust process cleanup (korrekt ordning)"
log_message "  ✅ Längre stabiliseringstider"
log_message "  ✅ RTL-SDR ready verification"
log_message "  ✅ Named pipe collision handling"
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
# FÖRBÄTTRAD SYSTEM HEALTH MONITORING
# ========================================
while true; do
    # Check RTL_FM (mest kritisk)
    if [[ -n "$RTL_FM_PID" ]] && ! kill -0 "$RTL_FM_PID" 2>/dev/null; then
        log_message "❌ RTL_FM process died - USB issue likely"
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