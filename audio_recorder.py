#!/usr/bin/env python3
"""
Audio Recorder - Final Clean Version
Records audio from stdin (redsea -e output) with event-based triggering
"""

import sys
import os
import logging
import subprocess
import threading
import time
import select
from datetime import datetime
from collections import deque

from config import (
    AUDIO_CONTROL_PIPE, INPUT_SAMPLE_RATE, AUDIO_SAMPLE_RATE, 
    PRE_TRIGGER_BUFFER_SECONDS, get_audio_filename
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/audio_recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AudioRecorder:
    """
    Records audio from stdin with event-based triggering
    Uses circular buffer for pre-trigger capture
    """
    
    def __init__(self, buffer_seconds=PRE_TRIGGER_BUFFER_SECONDS):
        # Audio buffering
        self.buffer_seconds = buffer_seconds
        self.sample_rate = INPUT_SAMPLE_RATE
        self.buffer_size = self.sample_rate * buffer_seconds * 2  # 16-bit samples
        self.audio_buffer = deque(maxlen=self.buffer_size)
        
        # Recording state
        self.is_recording = False
        self.current_recording_file = None
        self.recording_process = None
        
        # Control
        self.control_pipe = AUDIO_CONTROL_PIPE
        self.running = True
        
        # Statistics
        self.bytes_processed = 0
        self.recordings_started = 0
        
        self._create_control_pipe()
        
        logger.info("AudioRecorder initialized")
        logger.info(f"Buffer: {buffer_seconds} seconds ({self.buffer_size} bytes)")
        logger.info(f"Control pipe: {self.control_pipe}")
    
    def _create_control_pipe(self):
        """Create named pipe for receiving recording commands"""
        try:
            if os.path.exists(self.control_pipe):
                os.unlink(self.control_pipe)
            os.mkfifo(self.control_pipe)
            logger.info(f"Control pipe created: {self.control_pipe}")
        except Exception as e:
            logger.error(f"Failed to create control pipe: {e}")
    
    def start(self):
        """Start the main audio processing loop"""
        logger.info("🎧 Starting AudioRecorder main loop")
        
        try:
            # Start control monitoring thread
            control_thread = threading.Thread(target=self._monitor_control_pipe, daemon=True)
            control_thread.start()
            
            # Main audio processing loop
            self._audio_processing_loop()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def _audio_processing_loop(self):
        """Main loop that processes audio from stdin"""
        logger.info("Reading audio from stdin (redsea -e output)...")
        
        chunk_size = 8192  # 8KB chunks
        
        while self.running:
            try:
                # Check if there's data available on stdin
                ready, _, _ = select.select([sys.stdin.buffer], [], [], 0.1)
                
                if ready:
                    # Read audio data from stdin
                    chunk = sys.stdin.buffer.read(chunk_size)
                    
                    if not chunk:  # EOF
                        logger.info("End of audio stream")
                        break
                    
                    # Add to circular buffer
                    self.audio_buffer.extend(chunk)
                    self.bytes_processed += len(chunk)
                    
                    # If recording, write to file
                    if self.is_recording and self.recording_process:
                        try:
                            self.recording_process.stdin.write(chunk)
                            self.recording_process.stdin.flush()
                        except BrokenPipeError:
                            logger.warning("Recording process pipe broken")
                            self._stop_recording_internal()
                
            except Exception as e:
                logger.error(f"Error in audio processing: {e}")
                break
        
        logger.info(f"Audio processing ended. Processed {self.bytes_processed} bytes")
    
    def _monitor_control_pipe(self):
        """Monitor control pipe for recording commands"""
        logger.info("Monitoring control pipe for commands...")
        
        while self.running:
            try:
                # Open pipe for reading (blocking)
                with open(self.control_pipe, 'r') as pipe:
                    command = pipe.readline().strip()
                    
                    if not command:
                        continue
                    
                    logger.info(f"Received command: {command}")
                    
                    if command.startswith("START:"):
                        event_type = command.split(":", 1)[1]
                        self._start_recording_internal(event_type)
                    elif command == "STOP":
                        self._stop_recording_internal()
                    elif command == "QUIT":
                        self.running = False
                        break
                        
            except Exception as e:
                logger.error(f"Error monitoring control pipe: {e}")
                time.sleep(1)
    
    def _start_recording_internal(self, event_type):
        """Start recording to file"""
        if self.is_recording:
            logger.warning("Already recording, ignoring start command")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_recording_file = get_audio_filename(event_type, timestamp)
        
        try:
            # Start sox process to convert and save audio
            sox_cmd = [
                'sox',
                '-t', 'raw',                    # Input: raw audio
                '-r', str(INPUT_SAMPLE_RATE),   # Sample rate from redsea
                '-e', 'signed',                 # Signed samples
                '-b', '16',                     # 16-bit
                '-c', '1',                      # Mono
                '-',                            # Read from stdin
                '-r', str(AUDIO_SAMPLE_RATE),   # Resample to 48k
                '-t', 'wav',                    # Output format
                self.current_recording_file     # Output file
            ]
            
            self.recording_process = subprocess.Popen(
                sox_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Write buffered audio (pre-trigger)
            if self.audio_buffer:
                buffer_data = bytes(self.audio_buffer)
                logger.info(f"Writing {len(buffer_data)} bytes of pre-trigger audio")
                self.recording_process.stdin.write(buffer_data)
                self.recording_process.stdin.flush()
            
            self.is_recording = True
            self.recordings_started += 1
            
            logger.info(f"🎤 Recording started: {self.current_recording_file}")
            logger.info(f"🎯 Event type: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_process = None
    
    def _stop_recording_internal(self):
        """Stop current recording"""
        if not self.is_recording:
            logger.warning("Not recording, ignoring stop command")
            return
        
        try:
            if self.recording_process:
                # Close stdin to signal end of recording
                self.recording_process.stdin.close()
                
                # Wait for sox to finish
                self.recording_process.wait(timeout=10)
                
                # Get file statistics
                stats = self._get_recording_stats()
                logger.info(f"🎵 Recording saved: {stats}")
                
                self.recording_process = None
            
            self.is_recording = False
            self.current_recording_file = None
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
    
    def _get_recording_stats(self):
        """Get statistics about the recorded file"""
        if not self.current_recording_file or not os.path.exists(self.current_recording_file):
            return {"error": "File not found"}
        
        try:
            file_size = os.path.getsize(self.current_recording_file)
            
            # Try to get duration using soxi
            result = subprocess.run(
                ['soxi', '-D', self.current_recording_file],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
            else:
                duration = None
            
            return {
                "filename": os.path.basename(self.current_recording_file),
                "file_size_bytes": file_size,
                "duration_seconds": duration
            }
            
        except Exception as e:
            logger.error(f"Error getting recording stats: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up AudioRecorder")
        
        self.running = False
        
        # Stop any active recording
        if self.is_recording:
            self._stop_recording_internal()
        
        # Remove control pipe
        if os.path.exists(self.control_pipe):
            os.unlink(self.control_pipe)
        
        logger.info("AudioRecorder cleanup complete")

# ========================================
# MAIN ENTRY POINT
# ========================================
def main():
    """Main entry point"""
    logger.info("🚀 AudioRecorder starting")
    
    # Check if running in pipeline
    if sys.stdin.isatty():
        logger.error("This program must be run in a pipeline (reading from stdin)")
        logger.error("Example: rtl_fm ... | redsea -e | python3 audio_recorder.py")
        sys.exit(1)
    
    # Create and start recorder
    recorder = AudioRecorder(buffer_seconds=PRE_TRIGGER_BUFFER_SECONDS)
    recorder.start()

if __name__ == "__main__":
    main()
