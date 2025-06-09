#!/usr/bin/env python3
"""
VMA Project Cleanup System - UPPDATERAD med DAGLIG backup-struktur + 3 månaders skärmdumpar
Fil: cleanup.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/cleanup.py

STORA FÖRÄNDRINGAR:
- Stöd för DAGLIG backup-struktur: backup/daily_YYYYMMDD/ 
- Retention baserat på DAGAR istället för ANTAL SESSIONER
- Bakåtkompatibilitet med gamla session_YYYYMMDD_HHMMSS/ backups
- Skärmdumpar: 3 månader normal, 7 dagar emergency
- Gradvis övergång från session-baserad till daglig struktur
"""

import os
import sys
import time
import shutil
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess

# ========================================
# CONFIGURATION - DAGLIG BACKUP + UPPDATERADE RETENTION
# ========================================
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
BACKUP_DIR = PROJECT_DIR / "backup"

# UPPDATERADE retention policies för working files
WORKING_FILE_POLICIES = {
    'normal': {
        'audio_files': 7,           # dagar
        'transcriptions': 30,       # dagar
        'rds_continuous_logs': 7,   # dagar
        'system_logs': 14,          # dagar
        'event_logs': 30,           # dagar
        'screen_dumps': 90,         # dagar - 3 månader (från tidigare uppdatering)
        'display_state_files': 7    # dagar
    },
    'emergency': {
        'audio_files': 3,           # dagar
        'transcriptions': 14,       # dagar
        'rds_continuous_logs': 3,   # dagar
        'system_logs': 7,           # dagar
        'event_logs': 14,           # dagar
        'screen_dumps': 7,          # dagar - 7 dagar (från tidigare uppdatering)
        'display_state_files': 3    # dagar
    }
}

# UPPDATERADE backup policies - DAGLIG struktur
DAILY_BACKUP_POLICIES = {
    'keep_days': 7,                 # Behåll 7 dagliga backups (istället för 5 sessioner)
    'max_backup_size_gb': 2,        # Varning vid >2GB
    'emergency_backup_size_gb': 5,  # Emergency cleanup vid >5GB
    'emergency_keep_days': 3        # Behåll endast 3 dagar vid emergency
}

# Legacy session backup policies (för gamla session_* mappar)
LEGACY_SESSION_POLICIES = {
    'keep_sessions': 5,             # Behåll 5 gamla session-backups under övergång
    'cleanup_after_days': 30       # Rensa gamla session-backups efter 30 dagar
}

# Disk space thresholds
DISK_SPACE_THRESHOLDS = {
    'warning_percent': 80,          # Varning vid >80% användning
    'emergency_percent': 90,        # Emergency cleanup vid >90%
    'critical_percent': 95          # Kritisk varning vid >95%
}

# ========================================
# LOGGING SETUP
# ========================================
def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging for cleanup operations"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - CLEANUP - %(levelname)s - %(message)s"
    
    # Create logs directory if it doesn't exist
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Setup handlers
    handlers = [
        logging.FileHandler(LOGS_DIR / f"cleanup_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🧹 VMA Cleanup System - DAGLIG Backup-struktur + 3 månaders skärmdumpar")
    logger.info("=" * 80)
    logger.info("✨ UPPDATERAD ARKITEKTUR:")
    logger.info("   📅 DAGLIG backup: backup/daily_YYYYMMDD/ (behåll X dagar)")
    logger.info("   🔄 Legacy support: backup/session_YYYYMMDD_HHMMSS/ (gradvis rensning)")
    logger.info("   📸 Skärmdumpar Normal: 90 dagar (3 månader)")
    logger.info("   📸 Skärmdumpar Emergency: 7 dagar")
    logger.info("   💡 Förbättrad forensisk säkerhet och organisation")
    
    return logger

# ========================================
# DISK SPACE UTILITIES (oförändrad)
# ========================================
class DiskSpaceMonitor:
    """Monitor disk space and determine cleanup strategy"""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage statistics"""
        try:
            total, used, free = shutil.disk_usage(self.project_dir)
            
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'free_gb': free / (1024**3),
                'used_percent': (used / total) * 100
            }
        except Exception as e:
            logging.error(f"Error getting disk usage: {e}")
            return {
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'used_percent': 0
            }
    
    def needs_emergency_cleanup(self) -> Tuple[bool, str]:
        """Check if emergency cleanup is needed"""
        usage = self.get_disk_usage()
        used_percent = usage['used_percent']
        
        if used_percent >= DISK_SPACE_THRESHOLDS['critical_percent']:
            return True, f"KRITISK diskutrymme: {used_percent:.1f}% använt"
        elif used_percent >= DISK_SPACE_THRESHOLDS['emergency_percent']:
            return True, f"Emergency diskutrymme: {used_percent:.1f}% använt"
        elif used_percent >= DISK_SPACE_THRESHOLDS['warning_percent']:
            return False, f"Varning diskutrymme: {used_percent:.1f}% använt"
        else:
            return False, f"Normalt diskutrymme: {used_percent:.1f}% använt"

# ========================================
# WORKING FILES CLEANUP (oförändrad från tidigare)
# ========================================
class WorkingFilesCleanup:
    """Handle cleanup of working files (files created after system startup)"""
    
    def __init__(self, logs_dir: Path, emergency_mode: bool = False):
        self.logs_dir = logs_dir
        self.emergency_mode = emergency_mode
        self.policies = WORKING_FILE_POLICIES['emergency' if emergency_mode else 'normal']
        self.logger = logging.getLogger(__name__)
        
        mode_str = "EMERGENCY" if emergency_mode else "NORMAL"
        self.logger.info(f"📁 WorkingFilesCleanup initialiserad i {mode_str} läge")
        self.logger.info(f"📸 Skärmdump-retention: {self.policies['screen_dumps']} dagar")
    
    def cleanup_file_category(self, pattern: str, retention_days: int, description: str) -> Tuple[int, int]:
        """
        Clean up files matching pattern older than retention_days
        Returns (files_removed, bytes_freed)
        """
        if not self.logs_dir.exists():
            return 0, 0
        
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        files_removed = 0
        bytes_freed = 0
        
        try:
            # Find matching files
            if '/' in pattern:
                # Pattern includes subdirectory
                search_pattern = self.logs_dir / pattern
                matching_files = list(search_pattern.parent.glob(search_pattern.name))
            else:
                # Pattern is just filename pattern
                matching_files = list(self.logs_dir.glob(pattern))
            
            for file_path in matching_files:
                try:
                    if file_path.is_file():
                        # Check file modification time
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            
                            files_removed += 1
                            bytes_freed += file_size
                            
                            self.logger.debug(f"🗑️ Raderad: {file_path.name} ({file_size/1024:.1f} KB, {file_mtime.strftime('%Y-%m-%d')})")
                
                except Exception as e:
                    self.logger.error(f"Fel vid radering av {file_path}: {e}")
        
        except Exception as e:
            self.logger.error(f"Fel vid sökning av {pattern}: {e}")
        
        if files_removed > 0:
            self.logger.info(f"🧹 {description}: {files_removed} filer raderade ({bytes_freed/1024/1024:.1f} MB frigjort)")
        else:
            self.logger.debug(f"✅ {description}: Inga gamla filer att radera")
        
        return files_removed, bytes_freed
    
    def cleanup_all_working_files(self) -> Dict[str, Tuple[int, int]]:
        """Clean up all categories of working files"""
        self.logger.info(f"🧹 Startar working files cleanup ({'EMERGENCY' if self.emergency_mode else 'NORMAL'} läge)")
        
        cleanup_results = {}
        
        # Audio files
        files, bytes_freed = self.cleanup_file_category(
            "audio/*.wav",
            self.policies['audio_files'],
            "Audio-filer"
        )
        cleanup_results['audio'] = (files, bytes_freed)
        
        # Transcriptions
        files, bytes_freed = self.cleanup_file_category(
            "transcriptions/*.txt",
            self.policies['transcriptions'],
            "Transkriptioner"
        )
        cleanup_results['transcriptions'] = (files, bytes_freed)
        
        # Screen dumps - UPPDATERAD RETENTION
        files, bytes_freed = self.cleanup_file_category(
            "screen/*.png",
            self.policies['screen_dumps'],
            f"Skärmdumpar (retention: {self.policies['screen_dumps']} dagar)"
        )
        cleanup_results['screen_dumps'] = (files, bytes_freed)
        
        # Display state files
        files, bytes_freed = self.cleanup_file_category(
            "display_*.png",
            self.policies['display_state_files'],
            "Display state-filer"
        )
        cleanup_results['display_state'] = (files, bytes_freed)
        
        # RDS continuous logs (keep current day)
        current_date = datetime.now().strftime("%Y%m%d")
        files, bytes_freed = self.cleanup_file_category(
            "rds_continuous_*.log",
            self.policies['rds_continuous_logs'],
            "RDS continuous loggar"
        )
        cleanup_results['rds_continuous'] = (files, bytes_freed)
        
        # System logs (keep current day)
        files, bytes_freed = self.cleanup_file_category(
            "system_*.log",
            self.policies['system_logs'],
            "System-loggar"
        )
        cleanup_results['system_logs'] = (files, bytes_freed)
        
        # Event logs
        files, bytes_freed = self.cleanup_file_category(
            "rds_event_*.log",
            self.policies['event_logs'],
            "Event-loggar"
        )
        cleanup_results['event_logs'] = (files, bytes_freed)
        
        # Cleanup logs (keep current day and last 7 days)
        files, bytes_freed = self.cleanup_file_category(
            "cleanup_*.log",
            7,  # Always keep cleanup logs for 7 days
            "Cleanup-loggar"
        )
        cleanup_results['cleanup_logs'] = (files, bytes_freed)
        
        return cleanup_results

# ========================================
# UPPDATERAD BACKUP CLEANUP - DAGLIG + LEGACY SUPPORT
# ========================================
class DailyBackupCleanup:
    """
    UPPDATERAD: Handle cleanup av DAGLIG backup-struktur + legacy session backups
    
    Stöder både:
    - backup/daily_YYYYMMDD/ (nya dagliga backups)
    - backup/session_YYYYMMDD_HHMMSS/ (gamla session backups)
    """
    
    def __init__(self, backup_dir: Path, emergency_mode: bool = False):
        self.backup_dir = backup_dir
        self.emergency_mode = emergency_mode
        self.daily_policies = DAILY_BACKUP_POLICIES
        self.legacy_policies = LEGACY_SESSION_POLICIES
        self.logger = logging.getLogger(__name__)
        
        mode_str = "EMERGENCY" if emergency_mode else "NORMAL"
        self.logger.info(f"📅 DailyBackupCleanup initialiserad i {mode_str} läge")
        self.logger.info("🔄 Stöder: DAGLIG struktur + Legacy session backups")
    
    def get_daily_backups(self) -> List[Tuple[Path, datetime, int]]:
        """Hämta lista över DAGLIGA backups med metadata"""
        if not self.backup_dir.exists():
            return []
        
        daily_backups = []
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith('daily_'):
                try:
                    # Parse datum från directory namn: daily_20250610
                    date_str = backup_dir.name.replace('daily_', '')
                    backup_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    # Beräkna total storlek för dagen
                    total_size = 0
                    for file_path in backup_dir.rglob('*'):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                    
                    daily_backups.append((backup_dir, backup_date, total_size))
                
                except Exception as e:
                    self.logger.warning(f"Kunde inte parsa daglig backup {backup_dir.name}: {e}")
        
        # Sortera efter datum (nyaste först)
        daily_backups.sort(key=lambda x: x[1], reverse=True)
        return daily_backups
    
    def get_legacy_session_backups(self) -> List[Tuple[Path, datetime, int]]:
        """Hämta lista över LEGACY session backups"""
        if not self.backup_dir.exists():
            return []
        
        session_backups = []
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith('session_'):
                try:
                    # Parse timestamp från directory namn: session_20250610_143000
                    timestamp_str = backup_dir.name.replace('session_', '')
                    session_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    
                    # Beräkna total storlek
                    total_size = 0
                    for file_path in backup_dir.rglob('*'):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                    
                    session_backups.append((backup_dir, session_time, total_size))
                
                except Exception as e:
                    self.logger.warning(f"Kunde inte parsa legacy session backup {backup_dir.name}: {e}")
        
        # Sortera efter timestamp (nyaste först)
        session_backups.sort(key=lambda x: x[1], reverse=True)
        return session_backups
    
    def get_total_backup_size(self) -> float:
        """Hämta total storlek av alla backups (dagliga + legacy) i GB"""
        daily_backups = self.get_daily_backups()
        legacy_backups = self.get_legacy_session_backups()
        
        total_bytes = 0
        total_bytes += sum(size for _, _, size in daily_backups)
        total_bytes += sum(size for _, _, size in legacy_backups)
        
        return total_bytes / (1024**3)
    
    def cleanup_daily_backups(self) -> Tuple[int, int]:
        """Rensa överskott av DAGLIGA backups"""
        daily_backups = self.get_daily_backups()
        
        if not daily_backups:
            return 0, 0
        
        # Bestäm hur många dagar att behålla
        if self.emergency_mode:
            keep_days = self.daily_policies['emergency_keep_days']
            self.logger.warning(f"🚨 Emergency: Minskar behållna dagliga backups från {self.daily_policies['keep_days']} till {keep_days} dagar")
        else:
            keep_days = self.daily_policies['keep_days']
        
        # Identifiera backups att radera (äldre än keep_days)
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        backups_to_remove = [
            (backup_dir, backup_date, backup_size) 
            for backup_dir, backup_date, backup_size in daily_backups 
            if backup_date < cutoff_date
        ]
        
        days_removed = 0
        bytes_freed = 0
        
        for backup_dir, backup_date, backup_size in backups_to_remove:
            try:
                shutil.rmtree(backup_dir)
                days_removed += 1
                bytes_freed += backup_size
                
                age_days = (datetime.now() - backup_date).days
                self.logger.info(f"🗑️ Daglig backup raderad: {backup_dir.name} ({backup_size/1024/1024:.1f} MB, {age_days} dagar gammal)")
                
            except Exception as e:
                self.logger.error(f"Fel vid radering av daglig backup {backup_dir.name}: {e}")
        
        if days_removed > 0:
            self.logger.info(f"📅 Daglig backup cleanup: {days_removed} dagar raderade ({bytes_freed/1024/1024:.1f} MB frigjort)")
        else:
            self.logger.debug("✅ Dagliga backups: Inga överskott att radera")
        
        return days_removed, bytes_freed
    
    def cleanup_legacy_session_backups(self) -> Tuple[int, int]:
        """Rensa LEGACY session backups (gradvis övergång)"""
        legacy_backups = self.get_legacy_session_backups()
        
        if not legacy_backups:
            return 0, 0
        
        self.logger.info("🔄 Rensar legacy session backups (gradvis övergång till daglig struktur)")
        
        # Strategi för legacy cleanup:
        # 1. Behåll de senaste 5 sessions (för säkerhets skull)
        # 2. Radera sessions äldre än 30 dagar
        keep_sessions = self.legacy_policies['keep_sessions']
        cleanup_after_days = self.legacy_policies['cleanup_after_days']
        
        cutoff_time = datetime.now() - timedelta(days=cleanup_after_days)
        
        # Sessions att radera: (äldre än 30 dagar) ELLER (fler än 5 senaste)
        sessions_to_remove = []
        
        # Radera gamla sessions (>30 dagar)
        for backup_dir, session_time, backup_size in legacy_backups:
            if session_time < cutoff_time:
                sessions_to_remove.append((backup_dir, session_time, backup_size, f"äldre än {cleanup_after_days} dagar"))
        
        # Radera överskott (behåll bara 5 senaste)
        if len(legacy_backups) > keep_sessions:
            excess_sessions = legacy_backups[keep_sessions:]
            for backup_dir, session_time, backup_size in excess_sessions:
                if (backup_dir, session_time, backup_size, "") not in [(s[0], s[1], s[2], "") for s in sessions_to_remove]:
                    sessions_to_remove.append((backup_dir, session_time, backup_size, f"överskott (behåll {keep_sessions})"))
        
        sessions_removed = 0
        bytes_freed = 0
        
        for backup_dir, session_time, backup_size, reason in sessions_to_remove:
            try:
                shutil.rmtree(backup_dir)
                sessions_removed += 1
                bytes_freed += backup_size
                
                age_days = (datetime.now() - session_time).days
                self.logger.info(f"🗑️ Legacy session raderad: {backup_dir.name} ({backup_size/1024/1024:.1f} MB, {age_days} dagar, {reason})")
                
            except Exception as e:
                self.logger.error(f"Fel vid radering av legacy session {backup_dir.name}: {e}")
        
        if sessions_removed > 0:
            self.logger.info(f"🔄 Legacy session cleanup: {sessions_removed} sessions raderade ({bytes_freed/1024/1024:.1f} MB frigjort)")
            remaining_legacy = len(legacy_backups) - sessions_removed
            if remaining_legacy > 0:
                self.logger.info(f"🔄 Kvarvarande legacy sessions: {remaining_legacy} (gradvis övergång pågår)")
        else:
            self.logger.debug("✅ Legacy sessions: Inga att radera")
        
        return sessions_removed, bytes_freed
    
    def cleanup_all_backups(self) -> Dict[str, Tuple[int, int]]:
        """Rensa alla typer av backups"""
        cleanup_results = {}
        
        # Rensa dagliga backups
        days_removed, daily_bytes_freed = self.cleanup_daily_backups()
        cleanup_results['daily_backups'] = (days_removed, daily_bytes_freed)
        
        # Rensa legacy session backups
        sessions_removed, legacy_bytes_freed = self.cleanup_legacy_session_backups()
        cleanup_results['legacy_sessions'] = (sessions_removed, legacy_bytes_freed)
        
        return cleanup_results
    
    def check_backup_size_limits(self) -> Tuple[bool, str]:
        """Kontrollera om backup-storlek överskrider gränser"""
        total_size_gb = self.get_total_backup_size()
        
        if self.emergency_mode:
            if total_size_gb > self.daily_policies['emergency_backup_size_gb']:
                return True, f"Emergency backup cleanup: {total_size_gb:.2f}GB > {self.daily_policies['emergency_backup_size_gb']}GB"
        else:
            if total_size_gb > self.daily_policies['max_backup_size_gb']:
                return True, f"Backup-storlek varning: {total_size_gb:.2f}GB > {self.daily_policies['max_backup_size_gb']}GB"
        
        return False, f"Backup-storlek OK: {total_size_gb:.2f}GB"
    
    def get_backup_summary(self) -> Dict[str, any]:
        """Hämta sammanfattning av backup-struktur"""
        daily_backups = self.get_daily_backups()
        legacy_backups = self.get_legacy_session_backups()
        total_size_gb = self.get_total_backup_size()
        
        return {
            'total_size_gb': total_size_gb,
            'daily_backups': {
                'count': len(daily_backups),
                'size_gb': sum(size for _, _, size in daily_backups) / (1024**3),
                'oldest_date': daily_backups[-1][1].strftime('%Y-%m-%d') if daily_backups else None,
                'newest_date': daily_backups[0][1].strftime('%Y-%m-%d') if daily_backups else None
            },
            'legacy_sessions': {
                'count': len(legacy_backups),
                'size_gb': sum(size for _, _, size in legacy_backups) / (1024**3),
                'oldest_date': legacy_backups[-1][1].strftime('%Y-%m-%d') if legacy_backups else None,
                'newest_date': legacy_backups[0][1].strftime('%Y-%m-%d') if legacy_backups else None
            }
        }

# ========================================
# MAIN CLEANUP ORCHESTRATOR - UPPDATERAD
# ========================================
class VMACleanupSystem:
    """Main cleanup system orchestrator - UPPDATERAD för daglig backup"""
    
    def __init__(self, verbose: bool = False):
        self.logger = setup_logging(verbose)
        self.project_dir = PROJECT_DIR
        self.logs_dir = LOGS_DIR
        self.backup_dir = BACKUP_DIR
        self.disk_monitor = DiskSpaceMonitor(self.project_dir)
        
        # Ensure directories exist
        self.logs_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def generate_status_report(self) -> Dict[str, any]:
        """Generate comprehensive status report - UPPDATERAD för daglig backup"""
        disk_usage = self.disk_monitor.get_disk_usage()
        
        # UPPDATERAD: Daglig backup info
        daily_backup_cleanup = DailyBackupCleanup(self.backup_dir)
        backup_summary = daily_backup_cleanup.get_backup_summary()
        
        # Working files info
        working_files_stats = self._count_working_files()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'disk_usage': disk_usage,
            'backup_info': backup_summary,
            'working_files': working_files_stats,
            'policies': {
                'normal_retention': WORKING_FILE_POLICIES['normal'],
                'emergency_retention': WORKING_FILE_POLICIES['emergency'],
                'daily_backup': DAILY_BACKUP_POLICIES,
                'legacy_session': LEGACY_SESSION_POLICIES
            }
        }
    
    def _count_working_files(self) -> Dict[str, int]:
        """Count working files by category"""
        stats = {}
        
        file_patterns = {
            'audio_files': 'audio/*.wav',
            'transcriptions': 'transcriptions/*.txt',
            'screen_dumps': 'screen/*.png',
            'rds_continuous_logs': 'rds_continuous_*.log',
            'system_logs': 'system_*.log',
            'event_logs': 'rds_event_*.log'
        }
        
        for category, pattern in file_patterns.items():
            try:
                if '/' in pattern:
                    search_path = self.logs_dir / pattern
                    count = len(list(search_path.parent.glob(search_path.name)))
                else:
                    count = len(list(self.logs_dir.glob(pattern)))
                stats[category] = count
            except Exception:
                stats[category] = 0
        
        return stats
    
    def run_daily_cleanup(self) -> Dict[str, any]:
        """Run daily cleanup routine - UPPDATERAD för daglig backup"""
        self.logger.info("📅 Kör DAGLIG cleanup-rutin (med DAGLIG backup-struktur)")
        
        # Check if emergency cleanup is needed
        needs_emergency, disk_status = self.disk_monitor.needs_emergency_cleanup()
        
        if needs_emergency:
            self.logger.warning(f"🚨 {disk_status} - Växlar till emergency cleanup")
            return self.run_emergency_cleanup()
        else:
            self.logger.info(f"💾 {disk_status}")
        
        # Normal cleanup
        working_cleanup = WorkingFilesCleanup(self.logs_dir, emergency_mode=False)
        working_results = working_cleanup.cleanup_all_working_files()
        
        # UPPDATERAD: Daglig backup cleanup
        backup_cleanup = DailyBackupCleanup(self.backup_dir, emergency_mode=False)
        backup_results = backup_cleanup.cleanup_all_backups()
        
        # Check backup size limits
        size_exceeded, size_message = backup_cleanup.check_backup_size_limits()
        if size_exceeded:
            self.logger.warning(f"⚠️ {size_message}")
        else:
            self.logger.info(f"✅ {size_message}")
        
        # Summary
        total_working_files = sum(result[0] for result in working_results.values())
        total_working_bytes = sum(result[1] for result in working_results.values())
        
        total_backup_items = sum(result[0] for result in backup_results.values())
        total_backup_bytes = sum(result[1] for result in backup_results.values())
        
        total_files = total_working_files + total_backup_items
        total_bytes = total_working_bytes + total_backup_bytes
        
        self.logger.info("🎯 DAGLIG CLEANUP SAMMANFATTNING:")
        self.logger.info(f"   📁 Working files: {total_working_files} filer raderade")
        self.logger.info(f"   📅 Dagliga backups: {backup_results['daily_backups'][0]} dagar raderade")
        self.logger.info(f"   🔄 Legacy sessions: {backup_results['legacy_sessions'][0]} sessions raderade")
        self.logger.info(f"   💾 Totalt frigjort: {total_bytes/1024/1024:.1f} MB")
        self.logger.info(f"   📸 Skärmdumpar behålls i 3 månader (uppdaterad policy)")
        
        return {
            'cleanup_type': 'daily',
            'working_files_results': working_results,
            'backup_results': backup_results,
            'total_files_removed': total_files,
            'total_bytes_freed': total_bytes,
            'disk_status': disk_status,
            'backup_structure': 'daily_with_legacy_support'
        }
    
    def run_weekly_cleanup(self) -> Dict[str, any]:
        """Run weekly cleanup routine (more thorough) - UPPDATERAD"""
        self.logger.info("📅 Kör VECKOVIS cleanup-rutin (med DAGLIG backup-struktur)")
        
        # Run daily cleanup first
        daily_results = self.run_daily_cleanup()
        
        # Additional weekly tasks
        self.logger.info("🧹 Kör veckovis utökad rensning...")
        
        # Clean up any orphaned files
        orphaned_files = self._cleanup_orphaned_files()
        
        # Verify backup integrity (UPPDATERAD för daglig struktur)
        backup_issues = self._verify_backup_integrity()
        
        self.logger.info("🎯 VECKOVIS CLEANUP SAMMANFATTNING:")
        self.logger.info(f"   📁 Daglig cleanup: {daily_results['total_files_removed']} filer")
        self.logger.info(f"   🧹 Orphaned filer: {orphaned_files} raderade")
        self.logger.info(f"   📦 Backup-integritet: {len(backup_issues)} problem hittade")
        self.logger.info(f"   📅 Backup-struktur: DAGLIG + Legacy support")
        
        return {
            'cleanup_type': 'weekly',
            'daily_results': daily_results,
            'orphaned_files_removed': orphaned_files,
            'backup_issues': backup_issues,
            'backup_structure': 'daily_with_legacy_support'
        }
    
    def run_emergency_cleanup(self) -> Dict[str, any]:
        """Run emergency cleanup (aggressive) - UPPDATERAD"""
        self.logger.warning("🚨 EMERGENCY CLEANUP AKTIVERAD! (DAGLIG backup-struktur)")
        
        # Emergency working files cleanup
        working_cleanup = WorkingFilesCleanup(self.logs_dir, emergency_mode=True)
        working_results = working_cleanup.cleanup_all_working_files()
        
        # Emergency backup cleanup
        backup_cleanup = DailyBackupCleanup(self.backup_dir, emergency_mode=True)
        backup_results = backup_cleanup.cleanup_all_backups()
        
        # Total summary
        total_working_files = sum(result[0] for result in working_results.values())
        total_working_bytes = sum(result[1] for result in working_results.values())
        
        total_backup_items = sum(result[0] for result in backup_results.values())
        total_backup_bytes = sum(result[1] for result in backup_results.values())
        
        total_files = total_working_files + total_backup_items
        total_bytes = total_working_bytes + total_backup_bytes
        
        self.logger.warning("🚨 EMERGENCY CLEANUP SLUTFÖRD:")
        self.logger.warning(f"   📁 Working files: {total_working_files} filer raderade")
        self.logger.warning(f"   📅 Dagliga backups: Behåller {DAILY_BACKUP_POLICIES['emergency_keep_days']} dagar")
        self.logger.warning(f"   🔄 Legacy sessions: Aggressiv rensning")
        self.logger.warning(f"   💾 Totalt frigjort: {total_bytes/1024/1024:.1f} MB")
        self.logger.warning(f"   📸 Skärmdumpar: Emergency retention {WORKING_FILE_POLICIES['emergency']['screen_dumps']} dagar")
        
        return {
            'cleanup_type': 'emergency',
            'working_files_results': working_results,
            'backup_results': backup_results,
            'total_files_removed': total_files,
            'total_bytes_freed': total_bytes,
            'backup_structure': 'daily_with_aggressive_legacy_cleanup'
        }
    
    def _cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files (files in wrong locations, etc.)"""
        orphaned_count = 0
        
        try:
            # Look for common orphaned file patterns
            orphaned_patterns = [
                '*.wav',  # Audio files in root logs directory
                '*.mp3',  # Other audio formats
                '*.tmp',  # Temporary files
                'core.*', # Core dumps
                '.nfs*'   # NFS temporary files
            ]
            
            for pattern in orphaned_patterns:
                for file_path in self.logs_dir.glob(pattern):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            orphaned_count += 1
                            self.logger.debug(f"🗑️ Orphaned fil raderad: {file_path.name}")
                        except Exception as e:
                            self.logger.error(f"Fel vid radering av orphaned fil {file_path}: {e}")
            
        except Exception as e:
            self.logger.error(f"Fel vid sökning efter orphaned filer: {e}")
        
        return orphaned_count
    
    def _verify_backup_integrity(self) -> List[str]:
        """Verify backup integrity - UPPDATERAD för daglig struktur"""
        issues = []
        
        try:
            backup_cleanup = DailyBackupCleanup(self.backup_dir)
            
            # Kontrollera dagliga backups
            daily_backups = backup_cleanup.get_daily_backups()
            for backup_dir, backup_date, backup_size in daily_backups:
                # Kontrollera att daily_info.json finns
                daily_info_file = backup_dir / "daily_info.json"
                if not daily_info_file.exists():
                    issues.append(f"Saknar daily_info.json: {backup_dir.name}")
                
                # Kontrollera att det finns minst en session
                session_dirs = [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith('session_')]
                if not session_dirs:
                    issues.append(f"Inga sessioner i daglig backup: {backup_dir.name}")
                
                # Kontrollera att sessions har expected subdirectories
                for session_dir in session_dirs:
                    expected_subdirs = ['audio', 'transcriptions', 'rds_events', 'display_state']
                    for subdir in expected_subdirs:
                        subdir_path = session_dir / subdir
                        if subdir_path.exists() and not any(subdir_path.iterdir()):
                            issues.append(f"Tom session-katalog: {backup_dir.name}/{session_dir.name}/{subdir}")
            
            # Kontrollera legacy session backups
            legacy_backups = backup_cleanup.get_legacy_session_backups()
            for backup_dir, session_time, session_size in legacy_backups:
                # Kontrollera att session_info.json finns
                session_info_file = backup_dir / "session_info.json"
                if not session_info_file.exists():
                    issues.append(f"Legacy session saknar session_info.json: {backup_dir.name}")
        
        except Exception as e:
            issues.append(f"Fel vid backup-verifiering: {e}")
        
        return issues

# ========================================
# CLI INTERFACE - UPPDATERAD
# ========================================
def main():
    """Main CLI interface - UPPDATERAD för daglig backup"""
    parser = argparse.ArgumentParser(
        description="VMA Project Cleanup System - DAGLIG Backup-struktur + 3 månaders skärmdumpar"
    )
    
    parser.add_argument('--daily', action='store_true',
                       help='Kör daglig cleanup-rutin')
    parser.add_argument('--weekly', action='store_true',
                       help='Kör veckovis cleanup-rutin')
    parser.add_argument('--emergency', action='store_true',
                       help='Kör emergency cleanup (aggressiv rensning)')
    parser.add_argument('--status', action='store_true',
                       help='Visa status-rapport utan cleanup')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose loggning')
    
    args = parser.parse_args()
    
    # Initialize cleanup system
    cleanup_system = VMACleanupSystem(verbose=args.verbose)
    
    try:
        if args.status:
            # Status report - UPPDATERAD för daglig backup
            status = cleanup_system.generate_status_report()
            
            print("\n🧹 VMA CLEANUP STATUS RAPPORT - DAGLIG BACKUP")
            print("=" * 60)
            
            # Disk usage
            disk = status['disk_usage']
            print(f"💾 Diskutrymme: {disk['used_percent']:.1f}% använt ({disk['free_gb']:.1f} GB ledigt)")
            
            # UPPDATERAD: Backup info för daglig struktur
            backup = status['backup_info']
            print(f"📦 Total backup-storlek: {backup['total_size_gb']:.1f} GB")
            
            # Dagliga backups
            daily = backup['daily_backups']
            print(f"📅 Dagliga backups: {daily['count']} dagar ({daily['size_gb']:.1f} GB)")
            if daily['oldest_date'] and daily['newest_date']:
                print(f"   Spann: {daily['oldest_date']} → {daily['newest_date']}")
            
            # Legacy sessions
            legacy = backup['legacy_sessions']
            if legacy['count'] > 0:
                print(f"🔄 Legacy sessions: {legacy['count']} sessions ({legacy['size_gb']:.1f} GB)")
                print(f"   Status: Gradvis övergång till daglig struktur")
            
            # Working files
            working = status['working_files']
            print(f"📁 Working files:")
            print(f"   🎵 Audio: {working.get('audio_files', 0)} filer")
            print(f"   📝 Transkriptioner: {working.get('transcriptions', 0)} filer")
            print(f"   📸 Skärmdumpar: {working.get('screen_dumps', 0)} filer (retention: 3 månader)")
            
            # UPPDATERADE Retention policies
            normal = status['policies']['normal_retention']
            emergency = status['policies']['emergency_retention']
            daily_backup_policy = status['policies']['daily_backup']
            
            print(f"\n📋 UPPDATERADE RETENTION POLICIES:")
            print(f"   📸 Skärmdumpar Normal: {normal['screen_dumps']} dagar (3 månader)")
            print(f"   📸 Skärmdumpar Emergency: {emergency['screen_dumps']} dagar")
            print(f"   📅 Dagliga backups: {daily_backup_policy['keep_days']} dagar")
            print(f"   🔄 Legacy sessions: Gradvis rensning efter 30 dagar")
            
            # Recommendations
            needs_emergency, disk_status = cleanup_system.disk_monitor.needs_emergency_cleanup()
            print(f"\n💡 Rekommendationer:")
            if needs_emergency:
                print(f"   🚨 Emergency cleanup rekommenderas: {disk_status}")
            elif backup['total_size_gb'] > DAILY_BACKUP_POLICIES['max_backup_size_gb']:
                print(f"   ⚠️ Backup-storlek över gräns: Kör veckovis cleanup")
            else:
                print(f"   ✅ Systemet ser bra ut - inga åtgärder behövs")
            
            print(f"\n🏗️ BACKUP-ARKITEKTUR:")
            print(f"   📅 Ny struktur: backup/daily_YYYYMMDD/session_N_HHMMSS/")
            print(f"   🔄 Legacy struktur: backup/session_YYYYMMDD_HHMMSS/ (stöds)")
            print(f"   💡 Övergång: Gradvis från session-baserad till daglig")
        
        elif args.emergency:
            # Emergency cleanup
            result = cleanup_system.run_emergency_cleanup()
            
        elif args.weekly:
            # Weekly cleanup
            result = cleanup_system.run_weekly_cleanup()
            
        elif args.daily or len(sys.argv) == 1:
            # Daily cleanup (default)
            result = cleanup_system.run_daily_cleanup()
            
        else:
            parser.print_help()
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Cleanup avbruten av användare")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Fatal fel i cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
