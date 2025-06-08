#!/usr/bin/env python3
"""
VMA Project Cleanup System - UPPDATERAD med session-backup hantering
Fil: cleanup.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/cleanup.py

UPPDATERAT STÖD FÖR:
- Session-backup underhåll (behåll 5 senaste sessioner)
- Backup-storlek övervakning och rapportering
- Intelligent rensning av backup-strukturen
- Bevarar ALL befintlig cleanup-funktionalitet

CRON EXEMPEL:
# Daglig cleanup kl 03:00
0 3 * * * cd /home/chris/rds_logger3 && python3 cleanup.py --daily 2>&1 | logger

# Veckovis djuprengöring på söndagar kl 04:00
0 4 * * 0 cd /home/chris/rds_logger3 && python3 cleanup.py --weekly 2>&1 | logger
"""

import os
import sys
import argparse
import shutil
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

# ========================================
# CONFIGURATION
# ========================================
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
BACKUP_DIR = PROJECT_DIR / "backup"

# Cleanup policies - BEVARADE från original
KEEP_DAYS = {
    'rds_continuous': 7,      # RDS-data 1 vecka
    'system_logs': 14,        # Systemloggar 2 veckor  
    'event_logs': 30,         # Event-loggar 1 månad
    'audio_files': 7,         # Audio-filer 1 vecka (stora filer)
    'transcriptions': 30,     # Transkriptioner 1 månad
    'screenshots': 3,         # Skärmdumpar 3 dagar
}

# NYTT: Session-backup policies
SESSION_BACKUP_POLICIES = {
    'keep_sessions': 5,       # Behåll 5 senaste session-backups
    'max_backup_size_gb': 2,  # Varna om backup-katalogen blir större än 2GB
    'emergency_cleanup_gb': 5, # Emergency cleanup om backup-katalogen blir större än 5GB
}

# Diskutrymmes-trösklar - BEVARADE
DISK_THRESHOLDS = {
    'warning_percent': 80,    # Varna vid 80% full disk
    'emergency_percent': 90,  # Emergency cleanup vid 90%
    'critical_percent': 95,   # Kritisk varning vid 95%
}

# ========================================
# LOGGING SETUP
# ========================================
def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging för cleanup operations"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Skapa cleanup-logg med dagens datum
    today = datetime.now().strftime("%Y%m%d")
    cleanup_log = LOGS_DIR / f"cleanup_{today}.log"
    
    # Ensure logs directory exists
    LOGS_DIR.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - CLEANUP - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(cleanup_log),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# ========================================
# NYTT: SESSION BACKUP MANAGER
# ========================================
class SessionBackupCleanup:
    """
    Hanterar cleanup av session-backups enligt policys
    """
    
    def __init__(self, backup_dir: Path, logger: logging.Logger):
        self.backup_dir = backup_dir
        self.logger = logger
        self.policies = SESSION_BACKUP_POLICIES
    
    def cleanup_old_sessions(self) -> Dict[str, any]:
        """
        Rensa gamla session-backups enligt policy
        Returnerar statistik över vad som rensades
        """
        if not self.backup_dir.exists():
            return {'sessions_found': 0, 'sessions_removed': 0, 'space_freed_mb': 0}
        
        # Hitta alla session-backups
        session_dirs = [d for d in self.backup_dir.iterdir() 
                       if d.is_dir() and d.name.startswith('session_')]
        
        if not session_dirs:
            self.logger.info("Inga session-backups hittades")
            return {'sessions_found': 0, 'sessions_removed': 0, 'space_freed_mb': 0}
        
        # Sortera efter skapandetid (nyaste först)
        session_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        
        keep_count = self.policies['keep_sessions']
        sessions_to_remove = session_dirs[keep_count:]
        
        self.logger.info(f"Session-backup analys:")
        self.logger.info(f"  Totalt hittade: {len(session_dirs)}")
        self.logger.info(f"  Behåller: {min(len(session_dirs), keep_count)}")
        self.logger.info(f"  Kommer rensa: {len(sessions_to_remove)}")
        
        # Rensa gamla sessioner
        total_space_freed = 0
        sessions_removed = 0
        
        for session_dir in sessions_to_remove:
            try:
                # Beräkna storlek före rensning
                dir_size = self._get_directory_size(session_dir)
                
                # Ta bort session-backup
                shutil.rmtree(session_dir)
                
                total_space_freed += dir_size
                sessions_removed += 1
                
                self.logger.info(f"🗑️ Rensade session: {session_dir.name} ({dir_size/1024/1024:.1f} MB)")
                
            except Exception as e:
                self.logger.error(f"❌ Fel vid rensning av {session_dir.name}: {e}")
        
        stats = {
            'sessions_found': len(session_dirs),
            'sessions_removed': sessions_removed,
            'space_freed_mb': total_space_freed / 1024 / 1024
        }
        
        if sessions_removed > 0:
            self.logger.info(f"✅ Session cleanup: {sessions_removed} sessioner rensade, {stats['space_freed_mb']:.1f} MB frigjort")
        
        return stats
    
    def check_backup_size(self) -> Dict[str, any]:
        """
        Kontrollera total storlek på backup-katalogen
        Returnerar storleksinformation och varningar
        """
        if not self.backup_dir.exists():
            return {'total_size_gb': 0, 'warning': None, 'action_needed': False}
        
        total_size = self._get_directory_size(self.backup_dir)
        total_size_gb = total_size / 1024 / 1024 / 1024
        
        warning = None
        action_needed = False
        
        if total_size_gb > self.policies['emergency_cleanup_gb']:
            warning = f"KRITISK: Backup-katalogen är {total_size_gb:.1f} GB (>{self.policies['emergency_cleanup_gb']} GB)"
            action_needed = True
        elif total_size_gb > self.policies['max_backup_size_gb']:
            warning = f"VARNING: Backup-katalogen är {total_size_gb:.1f} GB (>{self.policies['max_backup_size_gb']} GB)"
        
        return {
            'total_size_gb': total_size_gb,
            'warning': warning,
            'action_needed': action_needed
        }
    
    def emergency_backup_cleanup(self) -> Dict[str, any]:
        """
        Emergency cleanup av backup-katalogen
        Mer aggressiv rensning när utrymmet är kritiskt
        """
        self.logger.warning("🚨 Emergency backup cleanup aktiverad!")
        
        # Minska antal behållna sessioner temporärt
        original_keep = self.policies['keep_sessions']
        self.policies['keep_sessions'] = max(2, original_keep // 2)  # Behåll hälften, minst 2
        
        self.logger.info(f"Emergency: Minskar behållna sessioner från {original_keep} till {self.policies['keep_sessions']}")
        
        # Genomför aggressiv rensning
        cleanup_stats = self.cleanup_old_sessions()
        
        # Återställ original policy
        self.policies['keep_sessions'] = original_keep
        
        # Rensa även äldre arkitektur-backups om de finns
        arch_stats = self._cleanup_architecture_backups()
        
        total_stats = {
            'sessions_removed': cleanup_stats['sessions_removed'],
            'space_freed_mb': cleanup_stats['space_freed_mb'] + arch_stats.get('space_freed_mb', 0),
            'emergency_mode': True
        }
        
        self.logger.warning(f"🚨 Emergency cleanup slutförd: {total_stats['space_freed_mb']:.1f} MB frigjort")
        
        return total_stats
    
    def _cleanup_architecture_backups(self) -> Dict[str, any]:
        """Rensa gamla arkitektur-backups (behåll bara 3 senaste)"""
        arch_dirs = [d for d in self.backup_dir.iterdir() 
                    if d.is_dir() and d.name.startswith('architecture_')]
        
        if len(arch_dirs) <= 3:
            return {'space_freed_mb': 0}
        
        # Sortera och behåll bara 3 senaste
        arch_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        old_arch_dirs = arch_dirs[3:]
        
        total_freed = 0
        for arch_dir in old_arch_dirs:
            try:
                size = self._get_directory_size(arch_dir)
                shutil.rmtree(arch_dir)
                total_freed += size
                self.logger.info(f"🗑️ Emergency: Rensade arkitektur-backup {arch_dir.name}")
            except Exception as e:
                self.logger.error(f"❌ Fel vid arkitektur-backup rensning: {e}")
        
        return {'space_freed_mb': total_freed / 1024 / 1024}
    
    def _get_directory_size(self, directory: Path) -> int:
        """Beräkna total storlek av katalog i bytes"""
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception:
            pass
        return total_size
    
    def generate_backup_report(self) -> Dict[str, any]:
        """Generera detaljerad rapport över backup-strukturen"""
        if not self.backup_dir.exists():
            return {'exists': False}
        
        report = {'exists': True, 'sessions': [], 'other_backups': [], 'total_size_gb': 0}
        
        total_size = 0
        
        # Analysera session-backups
        for item in self.backup_dir.iterdir():
            if not item.is_dir():
                continue
                
            item_size = self._get_directory_size(item)
            total_size += item_size
            
            if item.name.startswith('session_'):
                # Läs session info om den finns
                info_file = item / "session_info.json"
                session_info = {'timestamp': 'Okänd', 'files_backed_up': 0}
                
                if info_file.exists():
                    try:
                        with open(info_file) as f:
                            session_info = json.load(f)
                    except:
                        pass
                
                report['sessions'].append({
                    'name': item.name,
                    'size_mb': item_size / 1024 / 1024,
                    'timestamp': session_info.get('session_timestamp', 'Okänd'),
                    'files_count': session_info.get('files_backed_up', 0),
                    'age_days': (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days
                })
            else:
                report['other_backups'].append({
                    'name': item.name,
                    'size_mb': item_size / 1024 / 1024,
                    'age_days': (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days
                })
        
        report['total_size_gb'] = total_size / 1024 / 1024 / 1024
        
        # Sortera sessions efter tidsstämpel (nyaste först)
        report['sessions'].sort(key=lambda x: x['timestamp'], reverse=True)
        
        return report

# ========================================
# BEVARAD: TRADITIONAL CLEANUP FUNCTIONALITY
# ========================================
class TraditionalCleanup:
    """
    BEVARAR all befintlig cleanup-funktionalitet
    """
    
    def __init__(self, logs_dir: Path, logger: logging.Logger):
        self.logs_dir = logs_dir
        self.logger = logger
        self.keep_days = KEEP_DAYS
    
    def cleanup_old_logs(self) -> Dict[str, int]:
        """Rensa gamla loggfiler enligt retention policies"""
        stats = {}
        
        # RDS continuous logs
        stats['rds_continuous'] = self._cleanup_files_by_pattern(
            "rds_continuous_*.log", self.keep_days['rds_continuous']
        )
        
        # System logs
        stats['system_logs'] = self._cleanup_files_by_pattern(
            "system_*.log", self.keep_days['system_logs']
        )
        
        # Event logs
        stats['event_logs'] = self._cleanup_files_by_pattern(
            "rds_event_*.log", self.keep_days['event_logs']
        )
        
        return stats
    
    def cleanup_audio_files(self) -> int:
        """Rensa gamla audio-filer"""
        audio_dir = self.logs_dir / "audio"
        if not audio_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.keep_days['audio_files'])
        removed_count = 0
        
        for audio_file in audio_dir.glob("*.wav"):
            try:
                file_mtime = datetime.fromtimestamp(audio_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    audio_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Rensade audio: {audio_file.name}")
            except Exception as e:
                self.logger.error(f"Fel vid rensning av {audio_file.name}: {e}")
        
        if removed_count > 0:
            self.logger.info(f"🎵 Audio cleanup: {removed_count} filer rensade")
        
        return removed_count
    
    def cleanup_transcriptions(self) -> int:
        """Rensa gamla transkriptioner"""
        trans_dir = self.logs_dir / "transcriptions"
        if not trans_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.keep_days['transcriptions'])
        removed_count = 0
        
        for trans_file in trans_dir.glob("*.txt"):
            try:
                file_mtime = datetime.fromtimestamp(trans_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    trans_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Rensade transkription: {trans_file.name}")
            except Exception as e:
                self.logger.error(f"Fel vid rensning av {trans_file.name}: {e}")
        
        if removed_count > 0:
            self.logger.info(f"📝 Transkription cleanup: {removed_count} filer rensade")
        
        return removed_count
    
    def cleanup_screenshots(self) -> int:
        """Rensa gamla skärmdumpar"""
        screen_dir = self.logs_dir / "screen"
        removed_count = 0
        
        if screen_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=self.keep_days['screenshots'])
            
            for screenshot in screen_dir.glob("*.png"):
                try:
                    file_mtime = datetime.fromtimestamp(screenshot.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        screenshot.unlink()
                        removed_count += 1
                        self.logger.debug(f"Rensade skärmdump: {screenshot.name}")
                except Exception as e:
                    self.logger.error(f"Fel vid rensning av {screenshot.name}: {e}")
        
        # Rensa också display_sim filer
        for sim_file in self.logs_dir.glob("display_sim_*.png"):
            try:
                file_mtime = datetime.fromtimestamp(sim_file.stat().st_mtime)
                cutoff_date = datetime.now() - timedelta(days=self.keep_days['screenshots'])
                if file_mtime < cutoff_date:
                    sim_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Rensade sim-bild: {sim_file.name}")
            except Exception as e:
                self.logger.error(f"Fel vid rensning av {sim_file.name}: {e}")
        
        if removed_count > 0:
            self.logger.info(f"📷 Screenshot cleanup: {removed_count} filer rensade")
        
        return removed_count
    
    def _cleanup_files_by_pattern(self, pattern: str, keep_days: int) -> int:
        """Generisk filrensning baserat på mönster och ålder"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0
        
        for log_file in self.logs_dir.glob(pattern):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
                    self.logger.debug(f"Rensade: {log_file.name}")
            except Exception as e:
                self.logger.error(f"Fel vid rensning av {log_file.name}: {e}")
        
        return removed_count

# ========================================
# DISK SPACE MONITORING
# ========================================
class DiskSpaceMonitor:
    """Övervaka diskutrymme och trigga emergency cleanup vid behov"""
    
    def __init__(self, project_dir: Path, logger: logging.Logger):
        self.project_dir = project_dir
        self.logger = logger
        self.thresholds = DISK_THRESHOLDS
    
    def check_disk_space(self) -> Dict[str, any]:
        """Kontrollera diskutrymme och returnera status"""
        try:
            disk_usage = shutil.disk_usage(self.project_dir)
            
            total_gb = disk_usage.total / 1024 / 1024 / 1024
            used_gb = disk_usage.used / 1024 / 1024 / 1024
            free_gb = disk_usage.free / 1024 / 1024 / 1024
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            status = 'ok'
            if used_percent >= self.thresholds['critical_percent']:
                status = 'critical'
            elif used_percent >= self.thresholds['emergency_percent']:
                status = 'emergency'
            elif used_percent >= self.thresholds['warning_percent']:
                status = 'warning'
            
            return {
                'status': status,
                'used_percent': used_percent,
                'total_gb': total_gb,
                'used_gb': used_gb,
                'free_gb': free_gb,
                'needs_cleanup': status in ['emergency', 'critical']
            }
            
        except Exception as e:
            self.logger.error(f"Fel vid kontroll av diskutrymme: {e}")
            return {'status': 'error', 'needs_cleanup': False}

# ========================================
# MAIN CLEANUP ORCHESTRATOR
# ========================================
class VMACleanupManager:
    """
    HUVUDKLASS: Orchestrerar all cleanup-funktionalitet
    NYTT: Inkluderar session-backup hantering
    """
    
    def __init__(self, verbose: bool = False):
        self.logger = setup_logging(verbose)
        self.project_dir = PROJECT_DIR
        self.logs_dir = LOGS_DIR
        self.backup_dir = BACKUP_DIR
        
        # Initiera cleanup-komponenter
        self.session_backup_cleanup = SessionBackupCleanup(self.backup_dir, self.logger)
        self.traditional_cleanup = TraditionalCleanup(self.logs_dir, self.logger)
        self.disk_monitor = DiskSpaceMonitor(self.project_dir, self.logger)
        
        self.logger.info("VMA Cleanup Manager initialiserad med session-backup stöd")
    
    def daily_cleanup(self) -> Dict[str, any]:
        """Daglig cleanup-rutin"""
        self.logger.info("🧹 Startar daglig cleanup...")
        
        results = {
            'disk_space': self.disk_monitor.check_disk_space(),
            'session_backups': {},
            'traditional_cleanup': {},
            'emergency_actions': []
        }
        
        # Kontrollera diskutrymme först
        disk_status = results['disk_space']
        self.logger.info(f"💾 Diskutrymme: {disk_status['used_percent']:.1f}% använt "
                        f"({disk_status['free_gb']:.1f} GB ledigt)")
        
        if disk_status['status'] == 'critical':
            self.logger.critical(f"🚨 KRITISKT: Diskutrymme {disk_status['used_percent']:.1f}% fullt!")
            results['emergency_actions'].append("Critical disk space")
        
        # Session-backup cleanup (NYTT)
        self.logger.info("📦 Session-backup cleanup...")
        backup_size_check = self.session_backup_cleanup.check_backup_size()
        
        if backup_size_check['warning']:
            self.logger.warning(backup_size_check['warning'])
        
        # Emergency backup cleanup om nödvändigt
        if backup_size_check['action_needed'] or disk_status['needs_cleanup']:
            self.logger.warning("🚨 Startar emergency backup cleanup...")
            results['session_backups'] = self.session_backup_cleanup.emergency_backup_cleanup()
            results['emergency_actions'].append("Emergency backup cleanup")
        else:
            # Normal session cleanup
            results['session_backups'] = self.session_backup_cleanup.cleanup_old_sessions()
        
        # Traditional cleanup
        self.logger.info("📁 Traditional cleanup...")
        results['traditional_cleanup'] = {
            'logs': self.traditional_cleanup.cleanup_old_logs(),
            'audio': self.traditional_cleanup.cleanup_audio_files(),
            'transcriptions': self.traditional_cleanup.cleanup_transcriptions(),
            'screenshots': self.traditional_cleanup.cleanup_screenshots()
        }
        
        # Summering
        self._log_cleanup_summary(results)
        
        return results
    
    def weekly_cleanup(self) -> Dict[str, any]:
        """Veckovis djuprengöring"""
        self.logger.info("🧹 Startar veckovis djuprengöring...")
        
        # Kör först daglig cleanup
        results = self.daily_cleanup()
        
        # Lägg till veckospecifika operationer
        self.logger.info("📊 Genererar backup-rapport...")
        backup_report = self.session_backup_cleanup.generate_backup_report()
        results['backup_report'] = backup_report
        
        if backup_report.get('exists'):
            self.logger.info(f"📦 Backup-rapport:")
            self.logger.info(f"  Total backup-storlek: {backup_report['total_size_gb']:.2f} GB")
            self.logger.info(f"  Session-backups: {len(backup_report['sessions'])}")
            self.logger.info(f"  Andra backups: {len(backup_report['other_backups'])}")
        
        return results
    
    def emergency_cleanup(self) -> Dict[str, any]:
        """Emergency cleanup när diskutrymmet är kritiskt"""
        self.logger.warning("🚨 EMERGENCY CLEANUP AKTIVERAD!")
        
        results = {
            'reason': 'Emergency cleanup',
            'actions_taken': []
        }
        
        # Emergency backup cleanup
        backup_stats = self.session_backup_cleanup.emergency_backup_cleanup()
        results['backup_cleanup'] = backup_stats
        results['actions_taken'].append(f"Emergency backup cleanup: {backup_stats['space_freed_mb']:.1f} MB")
        
        # Aggressiv traditional cleanup (minska retention-perioder)
        original_keep_days = self.traditional_cleanup.keep_days.copy()
        
        # Minska retention temporärt
        self.traditional_cleanup.keep_days = {
            'rds_continuous': 3,      # Från 7 till 3 dagar
            'system_logs': 7,         # Från 14 till 7 dagar
            'event_logs': 14,         # Från 30 till 14 dagar
            'audio_files': 3,         # Från 7 till 3 dagar
            'transcriptions': 14,     # Från 30 till 14 dagar
            'screenshots': 1,         # Från 3 till 1 dag
        }
        
        self.logger.warning("🚨 Använde aggressiva retention-perioder för emergency cleanup")
        
        # Genomför aggressiv cleanup
        traditional_stats = {
            'logs': self.traditional_cleanup.cleanup_old_logs(),
            'audio': self.traditional_cleanup.cleanup_audio_files(),
            'transcriptions': self.traditional_cleanup.cleanup_transcriptions(),
            'screenshots': self.traditional_cleanup.cleanup_screenshots()
        }
        
        results['traditional_cleanup'] = traditional_stats
        
        # Återställ original retention
        self.traditional_cleanup.keep_days = original_keep_days
        
        # Summering
        total_files_removed = sum([
            sum(traditional_stats['logs'].values()),
            traditional_stats['audio'],
            traditional_stats['transcriptions'],
            traditional_stats['screenshots']
        ])
        
        results['actions_taken'].append(f"Aggressiv filrensning: {total_files_removed} filer")
        
        self.logger.warning(f"🚨 Emergency cleanup slutförd: {len(results['actions_taken'])} åtgärder")
        
        return results
    
    def status_report(self) -> Dict[str, any]:
        """Generera statusrapport utan att rensa något"""
        self.logger.info("📊 Genererar statusrapport...")
        
        disk_status = self.disk_monitor.check_disk_space()
        backup_size = self.session_backup_cleanup.check_backup_size()
        backup_report = self.session_backup_cleanup.generate_backup_report()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'disk_space': disk_status,
            'backup_size': backup_size,
            'backup_report': backup_report,
            'recommendations': self._generate_recommendations(disk_status, backup_size)
        }
    
    def _generate_recommendations(self, disk_status: Dict, backup_size: Dict) -> List[str]:
        """Generera rekommendationer baserat på aktuell status"""
        recommendations = []
        
        if disk_status['used_percent'] > 85:
            recommendations.append("Överväg att köra emergency cleanup - diskutrymmet är lågt")
        
        if backup_size.get('total_size_gb', 0) > 3:
            recommendations.append("Backup-katalogen är stor - överväg att minska antalet behållna sessioner")
        
        if disk_status['status'] == 'warning':
            recommendations.append("Schemalägg mer frekvent cleanup")
        
        if not recommendations:
            recommendations.append("Systemet ser bra ut - inga åtgärder behövs")
        
        return recommendations
    
    def _log_cleanup_summary(self, results: Dict):
        """Logga sammanfattning av cleanup-resultat"""
        self.logger.info("📋 Cleanup-sammanfattning:")
        
        # Session backup results
        session_stats = results.get('session_backups', {})
        if session_stats.get('sessions_removed', 0) > 0:
            self.logger.info(f"  📦 Session-backups: {session_stats['sessions_removed']} rensade, "
                           f"{session_stats['space_freed_mb']:.1f} MB frigjort")
        
        # Traditional cleanup results
        trad_stats = results.get('traditional_cleanup', {})
        total_files = 0
        for category, count in trad_stats.items():
            if isinstance(count, dict):
                total_files += sum(count.values())
            else:
                total_files += count
        
        if total_files > 0:
            self.logger.info(f"  📁 Traditional cleanup: {total_files} filer rensade")
        
        # Emergency actions
        emergency_actions = results.get('emergency_actions', [])
        if emergency_actions:
            self.logger.warning(f"  🚨 Emergency åtgärder: {', '.join(emergency_actions)}")

# ========================================
# COMMAND LINE INTERFACE
# ========================================
def main():
    parser = argparse.ArgumentParser(description="VMA Project Cleanup System med session-backup stöd")
    parser.add_argument('--daily', action='store_true', help='Kör daglig cleanup')
    parser.add_argument('--weekly', action='store_true', help='Kör veckovis djuprengöring')
    parser.add_argument('--emergency', action='store_true', help='Kör emergency cleanup')
    parser.add_argument('--status', action='store_true', help='Visa statusrapport')
    parser.add_argument('--verbose', '-v', action='store_true', help='Detaljerad loggning')
    
    args = parser.parse_args()
    
    # Defaulta till status om inget anges
    if not any([args.daily, args.weekly, args.emergency, args.status]):
        args.status = True
    
    try:
        cleanup_manager = VMACleanupManager(verbose=args.verbose)
        
        if args.emergency:
            results = cleanup_manager.emergency_cleanup()
        elif args.weekly:
            results = cleanup_manager.weekly_cleanup()
        elif args.daily:
            results = cleanup_manager.daily_cleanup()
        else:  # status
            results = cleanup_manager.status_report()
            
            # Skriv ut statusrapport till konsolen
            print("\n🧹 VMA CLEANUP STATUS RAPPORT")
            print("=" * 50)
            
            disk = results['disk_space']
            print(f"💾 Diskutrymme: {disk['used_percent']:.1f}% använt ({disk['free_gb']:.1f} GB ledigt)")
            
            backup = results.get('backup_size', {})
            if backup.get('total_size_gb'):
                print(f"📦 Backup-storlek: {backup['total_size_gb']:.2f} GB")
            
            recommendations = results.get('recommendations', [])
            if recommendations:
                print(f"\n💡 Rekommendationer:")
                for rec in recommendations:
                    print(f"  • {rec}")
            
            print()
        
        # Exit code baserat på resultat
        if args.status:
            disk_status = results.get('disk_space', {}).get('status', 'ok')
            sys.exit(1 if disk_status == 'critical' else 0)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Fel vid cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()