#!/usr/bin/env python3
"""
VMA Project - Automatic File Cleanup
Removes old log files and audio/transcription files to prevent disk overflow
SAVE AS: ~/rds_logger3/cleanup.py
"""

import os
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# ========================================
# CONFIGURATION
# ========================================
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
AUDIO_DIR = LOGS_DIR / "audio"
TRANSCRIPTIONS_DIR = LOGS_DIR / "transcriptions"

# Cleanup thresholds (adjustable)
LOG_RETENTION_DAYS = 3      # Keep logs for 3 days
AUDIO_RETENTION_DAYS = 7    # Keep audio and transcriptions for 7 days
EMERGENCY_CLEANUP_THRESHOLD = 85  # Start aggressive cleanup at 85% disk usage

# ========================================
# CLEANUP FUNCTIONS
# ========================================

def setup_cleanup_logging():
    """Setup logging for cleanup operations"""
    log_file = LOGS_DIR / f"cleanup_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    return logging.getLogger(__name__)

def get_file_age_days(file_path: Path) -> float:
    """Get the age of a file in days"""
    try:
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - file_mtime
        return age.total_seconds() / (24 * 3600)  # Convert to days
    except (OSError, ValueError):
        return 0

def get_disk_usage_percent() -> float:
    """Get current disk usage percentage"""
    try:
        statvfs = os.statvfs(PROJECT_DIR)
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        return (used / total) * 100
    except Exception:
        return 0

def cleanup_log_files(logger: logging.Logger, emergency_mode: bool = False) -> Tuple[int, int]:
    """
    Clean up old log files
    In emergency mode, uses shorter retention period
    Returns: (files_deleted, total_size_freed_mb)
    """
    if not LOGS_DIR.exists():
        return 0, 0
    
    retention_days = LOG_RETENTION_DAYS
    if emergency_mode:
        retention_days = max(1, LOG_RETENTION_DAYS // 2)  # Half the retention in emergency
        logger.warning(f"🚨 EMERGENCY MODE: Log retention reduced to {retention_days} days")
    
    files_deleted = 0
    total_size_freed = 0
    
    # Patterns for log files to clean (but NOT the current cleanup log)
    log_patterns = [
        "rds_continuous_*.log",
        "system_*.log", 
        "rds_event_*.log",
        "cleanup_*.log"  # Clean old cleanup logs too
    ]
    
    current_cleanup_log = f"cleanup_{datetime.now().strftime('%Y%m%d')}.log"
    
    logger.info(f"🧹 Cleaning log files older than {retention_days} days...")
    
    for pattern in log_patterns:
        log_files = list(LOGS_DIR.glob(pattern))
        
        for log_file in log_files:
            # Don't delete today's cleanup log
            if log_file.name == current_cleanup_log:
                continue
                
            age_days = get_file_age_days(log_file)
            
            if age_days > retention_days:
                try:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    
                    files_deleted += 1
                    total_size_freed += file_size
                    
                    logger.info(f"🗑️ Deleted log: {log_file.name} (age: {age_days:.1f} days, size: {file_size/1024:.1f}KB)")
                    
                except OSError as e:
                    logger.error(f"❌ Failed to delete {log_file.name}: {e}")
    
    total_size_mb = total_size_freed / (1024 * 1024)
    
    if files_deleted > 0:
        logger.info(f"✅ Log cleanup complete: {files_deleted} files deleted, {total_size_mb:.1f} MB freed")
    else:
        logger.info(f"✅ Log cleanup: No old files to delete")
    
    return files_deleted, total_size_mb

def cleanup_audio_files(logger: logging.Logger, emergency_mode: bool = False) -> Tuple[int, int]:
    """
    Clean up old audio files
    In emergency mode, uses shorter retention period
    Returns: (files_deleted, total_size_freed_mb)
    """
    if not AUDIO_DIR.exists():
        return 0, 0
    
    retention_days = AUDIO_RETENTION_DAYS
    if emergency_mode:
        retention_days = max(2, AUDIO_RETENTION_DAYS // 2)  # Half the retention in emergency
        logger.warning(f"🚨 EMERGENCY MODE: Audio retention reduced to {retention_days} days")
    
    files_deleted = 0
    total_size_freed = 0
    
    logger.info(f"🧹 Cleaning audio files older than {retention_days} days...")
    
    # Clean WAV files
    audio_files = list(AUDIO_DIR.glob("*.wav"))
    
    for audio_file in audio_files:
        age_days = get_file_age_days(audio_file)
        
        if age_days > retention_days:
            try:
                file_size = audio_file.stat().st_size
                audio_file.unlink()
                
                files_deleted += 1
                total_size_freed += file_size
                
                logger.info(f"🎵 Deleted audio: {audio_file.name} (age: {age_days:.1f} days, size: {file_size/1024/1024:.1f}MB)")
                
            except OSError as e:
                logger.error(f"❌ Failed to delete {audio_file.name}: {e}")
    
    total_size_mb = total_size_freed / (1024 * 1024)
    
    if files_deleted > 0:
        logger.info(f"✅ Audio cleanup complete: {files_deleted} files deleted, {total_size_mb:.1f} MB freed")
    else:
        logger.info(f"✅ Audio cleanup: No old files to delete")
    
    return files_deleted, total_size_mb

def cleanup_transcription_files(logger: logging.Logger, emergency_mode: bool = False) -> Tuple[int, int]:
    """
    Clean up old transcription files
    In emergency mode, uses shorter retention period
    Returns: (files_deleted, total_size_freed_mb)
    """
    if not TRANSCRIPTIONS_DIR.exists():
        return 0, 0
    
    retention_days = AUDIO_RETENTION_DAYS  # Same as audio files
    if emergency_mode:
        retention_days = max(2, AUDIO_RETENTION_DAYS // 2)
        logger.warning(f"🚨 EMERGENCY MODE: Transcription retention reduced to {retention_days} days")
    
    files_deleted = 0
    total_size_freed = 0
    
    logger.info(f"🧹 Cleaning transcription files older than {retention_days} days...")
    
    # Clean text files
    transcription_files = list(TRANSCRIPTIONS_DIR.glob("*.txt"))
    
    for transcription_file in transcription_files:
        age_days = get_file_age_days(transcription_file)
        
        if age_days > retention_days:
            try:
                file_size = transcription_file.stat().st_size
                transcription_file.unlink()
                
                files_deleted += 1
                total_size_freed += file_size
                
                logger.info(f"📝 Deleted transcription: {transcription_file.name} (age: {age_days:.1f} days, size: {file_size/1024:.1f}KB)")
                
            except OSError as e:
                logger.error(f"❌ Failed to delete {transcription_file.name}: {e}")
    
    total_size_mb = total_size_freed / (1024 * 1024)
    
    if files_deleted > 0:
        logger.info(f"✅ Transcription cleanup complete: {files_deleted} files deleted, {total_size_mb:.1f} MB freed")
    else:
        logger.info(f"✅ Transcription cleanup: No old files to delete")
    
    return files_deleted, total_size_mb

def get_disk_usage_info(logger: logging.Logger):
    """Log current disk usage information"""
    try:
        # Get disk usage for project directory
        statvfs = os.statvfs(PROJECT_DIR)
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        used_percent = (used / total) * 100
        
        logger.info(f"💽 Disk usage: {used_gb:.1f}GB used / {total_gb:.1f}GB total ({used_percent:.1f}%) - {free_gb:.1f}GB free")
        
        # Get project directory size
        try:
            project_size = sum(f.stat().st_size for f in PROJECT_DIR.rglob('*') if f.is_file())
            project_size_mb = project_size / (1024 * 1024)
            logger.info(f"📁 Project directory size: {project_size_mb:.1f} MB")
        except:
            logger.warning("📁 Could not calculate project directory size")
        
        # Warn if disk is getting full
        if used_percent > 95:
            logger.error(f"🚨 CRITICAL: Disk usage is critically high: {used_percent:.1f}%")
        elif used_percent > 90:
            logger.warning(f"⚠️ WARNING: Disk usage is high: {used_percent:.1f}% - consider increasing cleanup frequency")
        elif used_percent > 80:
            logger.warning(f"⚠️ NOTICE: Disk usage warning: {used_percent:.1f}%")
        
        return used_percent
        
    except Exception as e:
        logger.error(f"Error getting disk usage: {e}")
        return 0

def run_full_cleanup(force_emergency: bool = False) -> dict:
    """
    Run complete cleanup process
    Automatically enters emergency mode if disk usage is high
    Returns: Summary dictionary with statistics
    """
    logger = setup_cleanup_logging()
    
    logger.info("🧹 VMA Project - Automatic File Cleanup Starting")
    logger.info("=" * 60)
    
    # Check disk usage and determine if emergency cleanup is needed
    disk_usage_percent = get_disk_usage_info(logger)
    emergency_mode = force_emergency or disk_usage_percent > EMERGENCY_CLEANUP_THRESHOLD
    
    if emergency_mode:
        logger.warning("🚨 EMERGENCY CLEANUP MODE ACTIVATED")
        logger.warning(f"🚨 Disk usage: {disk_usage_percent:.1f}% > {EMERGENCY_CLEANUP_THRESHOLD}% threshold")
        logger.warning("🚨 Using more aggressive cleanup settings")
    
    start_time = datetime.now()
    
    # Run all cleanup operations
    log_files_deleted, log_size_freed = cleanup_log_files(logger, emergency_mode)
    audio_files_deleted, audio_size_freed = cleanup_audio_files(logger, emergency_mode)
    transcription_files_deleted, transcription_size_freed = cleanup_transcription_files(logger, emergency_mode)
    
    # Calculate totals
    total_files_deleted = log_files_deleted + audio_files_deleted + transcription_files_deleted
    total_size_freed = log_size_freed + audio_size_freed + transcription_size_freed
    
    elapsed_time = datetime.now() - start_time
    
    # Summary
    logger.info("=" * 60)
    logger.info("🎯 CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Emergency mode: {'YES' if emergency_mode else 'NO'}")
    logger.info(f"Log files deleted: {log_files_deleted} ({log_size_freed:.1f} MB)")
    logger.info(f"Audio files deleted: {audio_files_deleted} ({audio_size_freed:.1f} MB)")
    logger.info(f"Transcription files deleted: {transcription_files_deleted} ({transcription_size_freed:.1f} MB)")
    logger.info(f"Total files deleted: {total_files_deleted}")
    logger.info(f"Total space freed: {total_size_freed:.1f} MB")
    logger.info(f"Cleanup time: {elapsed_time.total_seconds():.1f} seconds")
    
    # Log disk usage after cleanup
    if total_files_deleted > 0:
        logger.info("💽 Disk usage after cleanup:")
        final_disk_usage = get_disk_usage_info(logger)
        
        if emergency_mode and final_disk_usage > EMERGENCY_CLEANUP_THRESHOLD:
            logger.error("🚨 EMERGENCY CLEANUP INSUFFICIENT!")
            logger.error("🚨 Disk usage still high after cleanup - manual intervention may be needed")
    
    logger.info("✅ Automatic cleanup completed successfully")
    
    return {
        'emergency_mode': emergency_mode,
        'log_files_deleted': log_files_deleted,
        'audio_files_deleted': audio_files_deleted,
        'transcription_files_deleted': transcription_files_deleted,
        'total_files_deleted': total_files_deleted,
        'total_size_freed_mb': total_size_freed,
        'elapsed_seconds': elapsed_time.total_seconds(),
        'initial_disk_usage_percent': disk_usage_percent,
        'final_disk_usage_percent': get_disk_usage_percent()
    }

# ========================================
# STANDALONE EXECUTION
# ========================================
def main():
    """Main entry point for standalone execution"""
    import sys
    
    # Check for emergency flag
    force_emergency = '--emergency' in sys.argv
    
    try:
        summary = run_full_cleanup(force_emergency)
        
        # Print summary to console
        if summary['total_files_deleted'] > 0:
            print(f"✅ Cleanup completed: {summary['total_files_deleted']} files deleted, {summary['total_size_freed_mb']:.1f} MB freed")
            if summary['emergency_mode']:
                print(f"🚨 Emergency mode was used due to high disk usage")
        else:
            print("✅ Cleanup completed: No old files to delete")
        
        # Exit with appropriate code
        if summary['final_disk_usage_percent'] > 95:
            print("🚨 WARNING: Disk usage still critically high after cleanup!")
            return 2  # Critical warning
        elif summary['final_disk_usage_percent'] > 90:
            print("⚠️ WARNING: Disk usage still high after cleanup")
            return 1  # Warning
        else:
            return 0  # Success
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())