#!/usr/bin/env python3
"""
UPPDATERAD Display Monitor - RDS-INDIKATOR för döva användare
Fil: display_monitor.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/display_monitor.py

NY FUNKTION:
- RDS-mottagningsindikator för döva användare
- Smart timing som INTE triggar extra uppdateringar
- Passiv visning - bara "åker med" befintliga uppdateringar

STRUKTUR:
- backup/daily_YYYYMMDD/session_N_HHMMSS/ (oförändrat)
- RDS-timing spåras från befintliga loggar
- Ingen extra polling eller uppdateringsfrekvens
"""

import os
import sys
import time
import json
import logging
import threading
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Display integration - använd FÖRENKLAD arkitektur
try:
    from display_manager import EventDrivenDisplayManager as DisplayManager
    DISPLAY_AVAILABLE = True
except ImportError:
    print("❌ FÖRENKLAD Display Manager inte tillgänglig")
    sys.exit(1)

# ========================================
# CONFIGURATION - DAGLIG BACKUP (oförändrat)
# ========================================
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
TRANSCRIPTIONS_DIR = LOGS_DIR / "transcriptions"
BACKUP_DIR = PROJECT_DIR / "backup"

# RDS log files som VMA-systemet skapar
RDS_CONTINUOUS_LOG_PATTERN = "rds_continuous_*.log"
RDS_EVENT_LOG_PATTERN = "rds_event_*.log"
SYSTEM_LOG_PATTERN = "system_*.log"

# FÖRENKLAD: Alla txt-filer är transkriptioner
TRANSCRIPTION_PATTERN = "*.txt"

# ROBUSTA polling intervals
LOG_POLL_INTERVAL = 3     # seconds
TRANSCRIPTION_POLL_INTERVAL = 5  # seconds

# ENERGIOPTIMERING: Längre status intervall
STATUS_UPDATE_INTERVAL = 900  # seconds (15 minuter)

# BEVARAR DIN FUNGERANDE CUTOFF LOGIK
STARTUP_CUTOFF_MINUTES = 15  # Bara events från senaste 15 min vid start

# ========================================
# DAGLIG BACKUP SYSTEM - OFÖRÄNDRAT
# ========================================
class DailyBackupManager:
    """
    DAGLIG Backup Manager - organiserar backups per dag istället för per session
    
    STRUKTUR:
    backup/daily_YYYYMMDD/session_N_HHMMSS/data...
    backup/daily_YYYYMMDD/daily_info.json
    """
    
    def __init__(self, project_dir: Path, logs_dir: Path):
        self.project_dir = project_dir
        self.logs_dir = logs_dir
        self.backup_base_dir = project_dir / "backup"
        
        # Dagens datum för backup
        self.today = datetime.now().strftime("%Y%m%d")
        self.daily_backup_dir = self.backup_base_dir / f"daily_{self.today}"
        
        logging.info("📅 DailyBackupManager initialiserad")
        logging.info(f"📁 Dagens backup-katalog: {self.daily_backup_dir.name}")
    
    def create_daily_backup(self) -> Optional[Path]:
        """
        Skapa dagens backup - lägg till ny session i dagens katalog
        Returnerar session-katalog eller None om backup misslyckades
        """
        try:
            # Skapa dagens backup-katalog om den inte finns
            self.daily_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Hitta nästa session-nummer för idag
            session_number = self._get_next_session_number()
            current_time = datetime.now().strftime("%H%M%S")
            session_name = f"session_{session_number}_{current_time}"
            session_backup_dir = self.daily_backup_dir / session_name
            
            session_backup_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"🔄 Skapar daglig backup: {self.daily_backup_dir.name}/{session_name}")
            
            # Backup olika kategorier
            backed_up_files = 0
            total_size = 0
            
            # 1. RDS event-loggar
            backed_up, size = self._backup_category(
                self.logs_dir.glob(RDS_EVENT_LOG_PATTERN),
                session_backup_dir / "rds_events"
            )
            backed_up_files += backed_up
            total_size += size
            
            # 2. Audio-filer
            audio_dir = self.logs_dir / "audio"
            if audio_dir.exists():
                backed_up, size = self._backup_category(
                    audio_dir.glob("*.wav"),
                    session_backup_dir / "audio"
                )
                backed_up_files += backed_up
                total_size += size
            
            # 3. Transkriptioner
            if TRANSCRIPTIONS_DIR.exists():
                backed_up, size = self._backup_category(
                    TRANSCRIPTIONS_DIR.glob("*.txt"),
                    session_backup_dir / "transcriptions"
                )
                backed_up_files += backed_up
                total_size += size
            
            # 4. Äldre system-loggar (inte dagens)
            today = datetime.now().strftime("%Y%m%d")
            old_system_logs = []
            for pattern in ["system_*.log", "display_monitor_*.log", "cleanup_*.log"]:
                for log_file in self.logs_dir.glob(pattern):
                    if today not in log_file.name:  # Inte dagens logg
                        old_system_logs.append(log_file)
            
            if old_system_logs:
                backed_up, size = self._backup_category(
                    old_system_logs,
                    session_backup_dir / "system_logs"
                )
                backed_up_files += backed_up
                total_size += size
            
            # 5. Display-filer
            display_files = []
            screen_dir = self.logs_dir / "screen"
            if screen_dir.exists():
                display_files.extend(screen_dir.glob("*.png"))
            
            # Display state och simuleringsbilder
            for pattern in ["display_sim_*.png", "display_state.json"]:
                display_files.extend(self.logs_dir.glob(pattern))
            
            if display_files:
                backed_up, size = self._backup_category(
                    display_files,
                    session_backup_dir / "display_state"
                )
                backed_up_files += backed_up
                total_size += size
            
            # Skapa session-info för denna session
            self._create_session_info(session_backup_dir, session_number, backed_up_files, total_size)
            
            # Uppdatera dagens samlad metadata
            self._update_daily_info(session_number, backed_up_files, total_size)
            
            if backed_up_files > 0:
                logging.info(f"✅ Daglig backup session {session_number} komplett: {backed_up_files} filer ({total_size/1024/1024:.1f} MB)")
                return session_backup_dir
            else:
                logging.info(f"ℹ️ Daglig backup session {session_number}: Inga filer att spara")
                # Ta bort tom session-katalog
                session_backup_dir.rmdir()
                return None
                
        except Exception as e:
            logging.error(f"❌ Fel vid daglig backup: {e}")
            return None
    
    def _get_next_session_number(self) -> int:
        """Hitta nästa session-nummer för idag"""
        if not self.daily_backup_dir.exists():
            return 1
        
        session_numbers = []
        for item in self.daily_backup_dir.iterdir():
            if item.is_dir() and item.name.startswith('session_'):
                try:
                    # Extrahera session-nummer från namn som "session_1_080000"
                    parts = item.name.split('_')
                    if len(parts) >= 2:
                        session_num = int(parts[1])
                        session_numbers.append(session_num)
                except (ValueError, IndexError):
                    continue
        
        return max(session_numbers, default=0) + 1
    
    def _backup_category(self, file_list, backup_subdir: Path) -> tuple[int, int]:
        """
        Backup en kategori av filer
        Returnerar (antal_filer, total_storlek_bytes)
        """
        files_backed_up = 0
        total_size = 0
        
        files_to_backup = list(file_list) if not isinstance(file_list, list) else file_list
        
        if not files_to_backup:
            return 0, 0
        
        # Skapa backup-subkatalog
        backup_subdir.mkdir(parents=True, exist_ok=True)
        
        for file_path in files_to_backup:
            try:
                if file_path.exists() and file_path.is_file():
                    # Kopiera fil
                    dest_file = backup_subdir / file_path.name
                    shutil.copy2(file_path, dest_file)
                    
                    file_size = file_path.stat().st_size
                    files_backed_up += 1
                    total_size += file_size
                    
                    logging.debug(f"📦 Backup: {file_path.name} ({file_size/1024:.1f} KB)")
                    
            except Exception as e:
                logging.warning(f"⚠️ Kunde inte backup {file_path.name}: {e}")
        
        if files_backed_up > 0:
            logging.info(f"📦 {backup_subdir.name}: {files_backed_up} filer ({total_size/1024:.1f} KB)")
        
        return files_backed_up, total_size
    
    def _create_session_info(self, session_dir: Path, session_number: int, file_count: int, total_size: int):
        """Skapa session-info fil för denna session"""
        session_info = {
            'session_number': session_number,
            'session_timestamp': datetime.now().isoformat(),
            'files_backed_up': file_count,
            'total_size_bytes': total_size,
            'backup_reason': f'Daglig backup session {session_number}',
            'system_info': {
                'project_dir': str(self.project_dir),
                'logs_dir': str(self.logs_dir)
            }
        }
        
        info_file = session_dir / "session_info.json"
        with open(info_file, 'w') as f:
            json.dump(session_info, f, indent=2)
    
    def _update_daily_info(self, session_number: int, file_count: int, total_size: int):
        """Uppdatera dagens samlad metadata"""
        daily_info_file = self.daily_backup_dir / "daily_info.json"
        
        # Läs befintlig info om den finns
        if daily_info_file.exists():
            try:
                with open(daily_info_file, 'r') as f:
                    daily_info = json.load(f)
            except Exception as e:
                logging.warning(f"Kunde inte läsa daily_info.json: {e}")
                daily_info = self._create_initial_daily_info()
        else:
            daily_info = self._create_initial_daily_info()
        
        # Lägg till denna session
        session_data = {
            'session_number': session_number,
            'timestamp': datetime.now().isoformat(),
            'files_backed_up': file_count,
            'size_bytes': total_size
        }
        
        daily_info['sessions'].append(session_data)
        daily_info['sessions_count'] = len(daily_info['sessions'])
        daily_info['total_size_bytes'] = sum(s['size_bytes'] for s in daily_info['sessions'])
        daily_info['last_updated'] = datetime.now().isoformat()
        
        # Spara uppdaterad info
        with open(daily_info_file, 'w') as f:
            json.dump(daily_info, f, indent=2)
    
    def _create_initial_daily_info(self) -> Dict:
        """Skapa initial daglig info-struktur"""
        return {
            'date': self.today,
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'sessions_count': 0,
            'total_size_bytes': 0,
            'sessions': []
        }
    
    def cleanup_workspace_after_backup(self):
        """
        Rensa workspace efter backup (så att vi startar rent)
        """
        try:
            cleaned_files = 0
            
            # Rensa transkriptioner
            if TRANSCRIPTIONS_DIR.exists():
                for txt_file in TRANSCRIPTIONS_DIR.glob("*.txt"):
                    txt_file.unlink()
                    cleaned_files += 1
            
            # Rensa audio-filer
            audio_dir = self.logs_dir / "audio"
            if audio_dir.exists():
                for wav_file in audio_dir.glob("*.wav"):
                    wav_file.unlink()
                    cleaned_files += 1
            
            # Rensa screen-filer
            screen_dir = self.logs_dir / "screen"
            if screen_dir.exists():
                for png_file in screen_dir.glob("*.png"):
                    png_file.unlink()
                    cleaned_files += 1
            
            # Rensa display state
            for pattern in ["display_sim_*.png", "display_state.json"]:
                for file_path in self.logs_dir.glob(pattern):
                    file_path.unlink()
                    cleaned_files += 1
            
            if cleaned_files > 0:
                logging.info(f"🧹 Workspace rensat: {cleaned_files} filer raderade för ny session")
            
        except Exception as e:
            logging.error(f"❌ Fel vid rensning av workspace: {e}")
    
    def get_daily_backup_summary(self) -> Dict:
        """Hämta sammanfattning av dagens backups"""
        daily_info_file = self.daily_backup_dir / "daily_info.json"
        
        if not daily_info_file.exists():
            return {
                'date': self.today,
                'sessions_count': 0,
                'total_size_mb': 0,
                'sessions': []
            }
        
        try:
            with open(daily_info_file, 'r') as f:
                daily_info = json.load(f)
            
            return {
                'date': daily_info['date'],
                'sessions_count': daily_info['sessions_count'],
                'total_size_mb': daily_info['total_size_bytes'] / (1024 * 1024),
                'sessions': daily_info['sessions']
            }
        except Exception as e:
            logging.error(f"Fel vid läsning av daily_info: {e}")
            return {
                'date': self.today,
                'sessions_count': 0,
                'total_size_mb': 0,
                'sessions': []
            }

# ========================================
# FÖRENKLAD LOG FILE MONITOR med RDS-INDIKATOR
# ========================================
class SimplifiedLogFileMonitor:
    """
    FÖRENKLAD version med RDS-mottagningsindikator för döva användare
    """
    
    def __init__(self):
        self.logs_dir = LOGS_DIR
        self.transcriptions_dir = TRANSCRIPTIONS_DIR
        self.last_positions = {}
        self.processed_events = set()
        self.processed_transcriptions = set()  # Spåra redan visade transkriptioner
        self.startup_time = datetime.now()  # 3B: Startup timestamp
        
        self.system_status = {
            'rds_active': False,
            'last_rds_time': None,
            'events_today': 0,
            'last_event': None
        }
        
        # BEVARAR DIN FUNGERANDE CUTOFF LOGIK för events
        self.cutoff_time = self.startup_time - timedelta(minutes=STARTUP_CUTOFF_MINUTES)
        
        # ENERGIOPTIMERING: Spåra sista status update
        self.last_status_update = datetime.now() - timedelta(minutes=20)
        
        # NY: RDS-mottagningsindikator
        self.last_rds_time = None
        self.rds_status_cache = None  # Cache för att undvika onödiga läsningar
        
        logging.info(f"FÖRENKLAD LogFileMonitor initialiserad MED RDS-INDIKATOR")
        logging.info(f"Startup: {self.startup_time}")
        logging.info(f"Event cutoff: {self.cutoff_time} (15 min grace period)")
        logging.info(f"🔧 FÖRENKLAD: Enkel transkriptionslogik - 'senaste txt-fil'")
        logging.info(f"🕐 3B: Timestamp-cutoff för transkriptioner")
        logging.info(f"📡 NY: RDS-mottagningsindikator för döva användare")
    
    def get_latest_rds_log(self) -> Optional[Path]:
        """BEVARAR: Hitta senaste RDS continuous log"""
        rds_logs = list(self.logs_dir.glob(RDS_CONTINUOUS_LOG_PATTERN))
        
        if not rds_logs:
            return None
        
        return max(rds_logs, key=lambda f: f.stat().st_mtime)
    
    def get_recent_event_logs(self) -> List[Path]:
        """BEVARAR DIN FUNGERANDE VERSION: Hitta ENDAST nya event-loggar"""
        event_logs = list(self.logs_dir.glob(RDS_EVENT_LOG_PATTERN))
        recent_logs = []
        
        for log_file in event_logs:
            try:
                # Kontrollera fil-modification time
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                # BEVARAR DIN FUNGERANDE FILTER 1: Bara filer efter cutoff
                if file_mtime < self.cutoff_time:
                    continue
                
                # BEVARAR DIN FUNGERANDE FILTER 2: Skippa redan processade
                if str(log_file) in self.processed_events:
                    continue
                
                recent_logs.append(log_file)
                
            except (OSError, ValueError) as e:
                logging.error(f"Fel vid kontroll av {log_file}: {e}")
                continue
        
        # Sortera efter modification time
        recent_logs.sort(key=lambda f: f.stat().st_mtime)
        
        return recent_logs
    
    def check_for_new_transcriptions(self) -> Optional[Dict]:
        """
        FÖRENKLAD: Hitta senaste transkription skapad efter systemstart
        Returnerar ENDAST EN transkription eller None
        """
        if not self.transcriptions_dir.exists():
            logging.debug("Transkriptionsmapp finns inte än")
            return None
        
        # Hitta alla txt-filer
        transcription_files = list(self.transcriptions_dir.glob(TRANSCRIPTION_PATTERN))
        
        if not transcription_files:
            return None
        
        # Filtrera baserat på startup_time (3B) och processed status
        valid_files = []
        
        for trans_file in transcription_files:
            try:
                # Skippa redan processade
                if str(trans_file) in self.processed_transcriptions:
                    continue
                
                # 3B: Skippa filer äldre än systemstart
                file_mtime = datetime.fromtimestamp(trans_file.stat().st_mtime)
                if file_mtime < self.startup_time:
                    logging.debug(f"Skippar gammal transkription: {trans_file.name} (äldre än startup)")
                    continue
                
                # Kontrollera att filen är stabil (inte modifierad på 2 sekunder)
                if time.time() - trans_file.stat().st_mtime < 2:
                    logging.debug(f"Väntar på att {trans_file.name} ska stabiliseras")
                    continue
                
                valid_files.append((trans_file, file_mtime))
                
            except Exception as e:
                logging.error(f"Fel vid kontroll av {trans_file}: {e}")
                continue
        
        if not valid_files:
            return None
        
        # Hitta SENASTE giltiga fil
        latest_file, latest_time = max(valid_files, key=lambda x: x[1])
        
        # Parsa transkription
        transcription_data = self._parse_transcription_file(latest_file)
        if transcription_data:
            # Markera som processad
            self.processed_transcriptions.add(str(latest_file))
            logging.info(f"🎯 FÖRENKLAD: Senaste transkription: {latest_file.name}")
            return transcription_data
        
        return None
    
    def get_rds_status(self) -> Dict:
        """
        NY: Hämta RDS-mottagningsstatus för döva användare
        SMART: Använder cache för att inte läsa filen för ofta
        """
        now = datetime.now()
        
        # Cache i 30 sekunder för att undvika onödig diskläsning
        if (self.rds_status_cache and 
            hasattr(self, 'rds_cache_time') and 
            (now - self.rds_cache_time).total_seconds() < 30):
            return self.rds_status_cache
        
        try:
            rds_log = self.get_latest_rds_log()
            if not rds_log or not rds_log.exists():
                status = {
                    'last_rds_time': None,
                    'status': 'ingen',
                    'indicator': '✕',
                    'time_str': 'Ingen'
                }
                self.rds_status_cache = status
                self.rds_cache_time = now
                return status
            
            # Läs sista RDS-entryn från filen
            last_rds_time = None
            try:
                with open(rds_log, 'r') as f:
                    # Läs sista raderna
                    lines = f.readlines()
                    if lines:
                        # Hitta senaste giltiga JSON-rad
                        for line in reversed(lines[-10:]):  # Kolla senaste 10 raderna
                            line = line.strip()
                            if line:
                                try:
                                    rds_entry = json.loads(line)
                                    if 'ts' in rds_entry:
                                        # Konvertera ISO timestamp till datetime
                                        timestamp_str = rds_entry['ts']
                                        last_rds_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                        break
                                except (json.JSONDecodeError, ValueError):
                                    continue
            except Exception as e:
                logging.debug(f"Fel vid läsning av RDS-logg: {e}")
            
            # Avgör status baserat på ålder
            if last_rds_time:
                age_minutes = (now - last_rds_time).total_seconds() / 60
                
                if age_minutes < 5:
                    status = 'aktiv'
                    indicator = '●'
                elif age_minutes < 15:
                    status = 'svag'  
                    indicator = '○'
                else:
                    status = 'gammal'
                    indicator = '✕'
                
                # Runda tid till 5-min intervall för stabil hash
                rounded_time = self._round_time_to_5min(last_rds_time)
                time_str = rounded_time.strftime('%H:%M')
            else:
                status = 'ingen'
                indicator = '✕'
                time_str = 'Ingen'
            
            rds_status = {
                'last_rds_time': last_rds_time,
                'status': status,
                'indicator': indicator,
                'time_str': time_str
            }
            
            # Cache resultatet
            self.rds_status_cache = rds_status
            self.rds_cache_time = now
            
            return rds_status
            
        except Exception as e:
            logging.error(f"Fel vid hämtning av RDS-status: {e}")
            # Fallback
            fallback_status = {
                'last_rds_time': None,
                'status': 'fel',
                'indicator': '?',
                'time_str': 'Fel'
            }
            self.rds_status_cache = fallback_status
            self.rds_cache_time = now
            return fallback_status
    
    def _round_time_to_5min(self, dt: datetime) -> datetime:
        """
        Runda tid till närmaste 5-minuters intervall för stabil hash
        Exempel: 14:23 → 14:25, 14:27 → 14:25
        """
        minute = dt.minute
        rounded_minute = round(minute / 5) * 5
        if rounded_minute >= 60:
            rounded_minute = 0
            dt = dt.replace(hour=dt.hour + 1)
        
        return dt.replace(minute=rounded_minute, second=0, microsecond=0)
    
    def _parse_transcription_file(self, trans_file: Path) -> Optional[Dict]:
        """BEVARAR: Parsa transkriptionsfil och extrahera nyckelinformation"""
        try:
            with open(trans_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = {
                'file': str(trans_file),
                'filename': trans_file.name,
                'timestamp': datetime.now()
            }
            
            # Extrahera kortversion för display
            if '## KORTVERSION (för display)' in content:
                start = content.find('## KORTVERSION (för display)')
                start = content.find('\n', start) + 1
                start = content.find('\n', start) + 1  # Skip divider
                end = content.find('\n\n', start)
                if end > start:
                    result['short_summary'] = content[start:end].strip()
            
            # Extrahera filtrerad transkription
            if '## FILTRERAD TRANSKRIPTION' in content:
                start = content.find('## FILTRERAD TRANSKRIPTION')
                start = content.find('\n', start) + 1
                start = content.find('\n', start) + 1  # Skip divider
                end = content.find('\n\n', start)
                if end > start:
                    result['text'] = content[start:end].strip()
                elif '## ORIGINAL TRANSKRIPTION' in content:
                    # Fallback till där original börjar
                    end = content.find('## ORIGINAL TRANSKRIPTION')
                    result['text'] = content[start:end].strip()
            
            # VMA-medveten extraktion - leta efter VMA MEDDELANDE
            if '## VMA MEDDELANDE' in content:
                start = content.find('## VMA MEDDELANDE')
                start = content.find('\n', start) + 1
                start = content.find('\n', start) + 1  # Skip divider
                end = content.find('\n\n', start)
                if end > start:
                    result['text'] = content[start:end].strip()
                elif '## ORIGINAL TRANSKRIPTION' in content:
                    # Fallback till där original börjar
                    end = content.find('## ORIGINAL TRANSKRIPTION')
                    result['text'] = content[start:end].strip()
            
            # Extrahera trafikinformation
            if '## EXTRAHERAD' in content:
                info = {}
                section_start = content.find('## EXTRAHERAD')
                section_end = content.find('\n\n', section_start)
                if section_end == -1:
                    section_end = len(content)
                section = content[section_start:section_end]
                
                # Vägar
                if 'Vägar:' in section:
                    line_start = section.find('Vägar:')
                    line_end = section.find('\n', line_start)
                    if line_end == -1:
                        line_end = len(section)
                    roads = section[line_start+6:line_end].strip()
                    if roads:
                        info['roads'] = roads
                
                # Platser
                if 'Platser:' in section:
                    line_start = section.find('Platser:')
                    line_end = section.find('\n', line_start)
                    if line_end == -1:
                        line_end = len(section)
                    locations = section[line_start+8:line_end].strip()
                    if locations:
                        info['locations'] = locations
                
                # Typ
                if 'Typ:' in section:
                    line_start = section.find('Typ:')
                    line_end = section.find('\n', line_start)
                    if line_end == -1:
                        line_end = len(section)
                    incident_type = section[line_start+4:line_end].strip()
                    if incident_type:
                        info['incident_type'] = incident_type
                
                if info:
                    result['extracted_info'] = info
            
            return result
            
        except Exception as e:
            logging.error(f"Fel vid parsning av transkriptionsfil {trans_file}: {e}")
            return None
    
    def read_new_rds_data(self) -> List[Dict]:
        """BEVARAR: Läs ny RDS-data från continuous log"""
        rds_log = self.get_latest_rds_log()
        if not rds_log or not rds_log.exists():
            return []
        
        file_key = str(rds_log)
        last_pos = self.last_positions.get(file_key, 0)
        
        new_data = []
        try:
            with open(rds_log, 'r') as f:
                f.seek(last_pos)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            rds_entry = json.loads(line)
                            new_data.append(rds_entry)
                        except json.JSONDecodeError:
                            continue
                
                self.last_positions[file_key] = f.tell()
                
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.error(f"Fel vid läsning av RDS-logg: {e}")
        
        return new_data
    
    def update_system_status(self):
        """BEVARAR: Uppdatera systemstatus + RDS-status"""
        rds_data = self.read_new_rds_data()
        if rds_data:
            self.system_status['rds_active'] = True
            self.system_status['last_rds_time'] = datetime.now()
        
        if (self.system_status['last_rds_time'] and 
            datetime.now() - self.system_status['last_rds_time'] > timedelta(minutes=15)):
            self.system_status['rds_active'] = False
        
        self.system_status['events_today'] = len(self.processed_events)
        
        # NY: Uppdatera RDS-status för display
        rds_status = self.get_rds_status()
        self.system_status['rds_status'] = rds_status
    
    def detect_events_from_logs(self) -> List[Dict]:
        """BEVARAR DIN FUNGERANDE VERSION: Detektera ENDAST nya events"""
        events = []
        
        recent_events = self.get_recent_event_logs()
        
        for event_file in recent_events:
            try:
                file_key = str(event_file)
                
                event_info = self._parse_event_file(event_file)
                if event_info:
                    event_time = event_info.get('time')
                    if event_time and event_time < self.cutoff_time:
                        logging.debug(f"Skippar gammalt event: {event_file.name}")
                        self.processed_events.add(file_key)
                        continue
                    
                    events.append(event_info)
                    self.processed_events.add(file_key)
                    
                    logging.info(f"Nytt event: {event_file.name} (tid: {event_time})")
                else:
                    self.processed_events.add(file_key)
                    
            except Exception as e:
                logging.error(f"Fel vid processing av {event_file}: {e}")
                self.processed_events.add(str(event_file))
        
        return events
    
    def _parse_event_file(self, event_file: Path) -> Optional[Dict]:
        """BEVARAR: Parse event-fil med VMA end support"""
        try:
            with open(event_file, 'r') as f:
                content = f.read()
            
            filename = event_file.name
            if 'traffic_start' in filename:
                event_type = 'traffic_start'
            elif 'traffic_end' in filename:
                event_type = 'traffic_end'
            elif 'vma_start' in filename:
                event_type = 'vma_start'
            elif 'vma_test_start' in filename:
                event_type = 'vma_test_start'
            elif 'vma_end' in filename:
                event_type = 'vma_end'
            elif 'vma_test_end' in filename:
                event_type = 'vma_test_end'
            else:
                return None
            
            file_time = datetime.fromtimestamp(event_file.stat().st_mtime)
            
            return {
                'type': event_type,
                'file': str(event_file),
                'time': file_time,
                'content': content[:500]
            }
            
        except Exception as e:
            logging.error(f"Fel vid parsing av {event_file}: {e}")
            return None

# ========================================
# UPPDATERAD DISPLAY CONTROLLER med RDS-STATUS
# ========================================
class SimplifiedDisplayController:
    """
    UPPDATERAD Display Controller med RDS-mottagningsindikator
    """
    
    def __init__(self):
        # 1. FÖRSTA: Skapa DAGLIG backup och rensa workspace
        self._perform_startup_backup()
        
        # 2. SEDAN: Initiera monitor och display manager
        self.monitor = SimplifiedLogFileMonitor()
        self.display_manager = DisplayManager(log_dir=str(LOGS_DIR))
        self.startup_time = datetime.now()
        
        logging.info("🔄 UPPDATERAD DisplayController med RDS-INDIKATOR")
        logging.info("📅 DAGLIG backup-strategi: backup/daily_YYYYMMDD/session_N_HHMMSS/")
        logging.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE")
        logging.info("🔧 FÖRENKLAD: Enkel transkriptlogik + daglig backup")
        logging.info("🕐 3B: Timestamp-cutoff implementerat")
        logging.info("🚨 VMA End Events: Stöds för korrekt display-växling")
        logging.info("📡 NY: RDS-mottagningsindikator för döva användare")
    
    def _perform_startup_backup(self):
        """Genomför DAGLIG backup vid startup"""
        try:
            backup_manager = DailyBackupManager(PROJECT_DIR, LOGS_DIR)
            
            # Skapa dagens backup - lägg till ny session
            session_backup_dir = backup_manager.create_daily_backup()
            
            if session_backup_dir:
                daily_summary = backup_manager.get_daily_backup_summary()
                logging.info(f"✅ Daglig backup komplett: {session_backup_dir.name}")
                logging.info(f"📅 Dagens sammanfattning: {daily_summary['sessions_count']} sessioner, {daily_summary['total_size_mb']:.1f} MB")
                
                # Rensa workspace för ny session
                backup_manager.cleanup_workspace_after_backup()
                logging.info("🧹 Workspace rensat - redo för ny session")
            else:
                logging.info("ℹ️ Ingen backup behövdes - startar med rent workspace")
                
        except Exception as e:
            logging.error(f"❌ Fel vid startup-backup: {e}")
            logging.warning("⚠️ Fortsätter utan backup - systemet kan ändå fungera")
    
    def start(self):
        """Starta FÖRENKLAD display-kontroll med RDS-indikator"""
        if not self.display_manager.display_available:
            logging.warning("Display inte tillgänglig - kör i simulator-läge")
        
        # Starta display manager
        self.display_manager.start()
        logging.info("🖥️ FÖRENKLAD Display Manager startad")
        
        # Start monitoring threads
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # FÖRENKLAD: Enkel transkriptionsövervakning
        transcription_thread = threading.Thread(target=self._transcription_monitoring_loop, daemon=True)
        transcription_thread.start()
        
        logging.info("📡 FÖRENKLAD monitoring aktiv MED RDS-INDIKATOR")
        logging.info("✅ Daglig backup genomförd")
        logging.info("🔧 Enkel transkriptlogik: 'senaste txt-fil efter startup'")
        logging.info("🕐 3B: Bara transkript efter systemstart")
        logging.info("📅 DAGLIG backup: Organiserad per dag istället av per session")
        logging.info("🚨 VMA End Events: Aktivt för korrekt display-växling")
        logging.info("📡 RDS-indikator: ● Aktiv | ○ Svag | ✕ Ingen")
    
    def stop(self):
        """Stoppa display-kontroll"""
        if self.display_manager:
            self.display_manager.stop()
        logging.info("🔋 FÖRENKLAD Display Controller stoppad")
    
    def _monitoring_loop(self):
        """BEVARAR: Event monitoring loop MED RDS-status"""
        while True:
            try:
                # BEVARAR DIN FUNGERANDE EVENT-DETECTION
                events = self.monitor.detect_events_from_logs()
                for event in events:
                    self._handle_event(event)
                
                # Update system status MED RDS-indikator
                self.monitor.update_system_status()
                
                # ENERGIOPTIMERING: Status update var 15:e minut
                now = datetime.now()
                time_since_status = (now - self.monitor.last_status_update).total_seconds()
                
                if time_since_status >= STATUS_UPDATE_INTERVAL:
                    if hasattr(self.display_manager, '_update_status_feedback'):
                        self.display_manager._update_status_feedback()
                    self.monitor.last_status_update = now
                    logging.debug("🔋 15-minuters heartbeat status update MED RDS-indikator")
                
                time.sleep(LOG_POLL_INTERVAL)
                
            except Exception as e:
                logging.error(f"Fel i monitoring loop: {e}")
                time.sleep(30)
    
    def _transcription_monitoring_loop(self):
        """FÖRENKLAD: Enkel transkriptionsövervakning"""
        while True:
            try:
                # FÖRENKLAD: Bara leta efter senaste transkription
                new_transcription = self.monitor.check_for_new_transcriptions()
                
                if new_transcription:
                    logging.info("📝 FÖRENKLAD: Ny transkription hittad - skickar till display")
                    self._handle_transcription_complete(new_transcription)
                
                time.sleep(TRANSCRIPTION_POLL_INTERVAL)
                
            except Exception as e:
                logging.error(f"Fel i transkriptionsövervakning: {e}")
                time.sleep(30)
    
    def _handle_transcription_complete(self, transcription: Dict):
        """FÖRENKLAD: Hantera färdig transkription"""
        summary = transcription.get('short_summary', 'Transkription klar')
        text = transcription.get('text', 'Ingen text tillgänglig')
        
        logging.info(f"📝 FÖRENKLAD: Skickar transkription till display: {summary}")
        
        # Skicka till display manager
        self.display_manager.handle_transcription_complete({
            'text': text,
            'short_summary': summary,
            'extracted_info': transcription.get('extracted_info', {}),
            'timestamp': transcription.get('timestamp', datetime.now()),
            'filename': transcription.get('filename', 'unknown')
        })
    
    def _handle_event(self, event: Dict):
        """BEVARAR DIN FUNGERANDE VERSION + VMA End Events: Hantera event"""
        event_type = event['type']
        event_time = event['time']
        
        logging.info(f"🎯 Hantera FÖRENKLAD event: {event_type} vid {event_time}")
        
        if event_type == 'traffic_start':
            self.display_manager.handle_traffic_start({
                'start_time': event_time,
                'content': event.get('content', ''),
                'location': 'Okänd'
            })
            
        elif event_type == 'traffic_end':
            self.display_manager.handle_traffic_end({
                'end_time': event_time,
                'content': event.get('content', '')
            })
            
        elif event_type in ['vma_start', 'vma_test_start']:
            is_test = event_type == 'vma_test_start'
            self.display_manager.handle_vma_start({
                'start_time': event_time,
                'content': event.get('content', ''),
                'rds_data': {}
            }, is_test=is_test)
            
        elif event_type in ['vma_end', 'vma_test_end']:
            is_test = event_type == 'vma_test_end'
            self.display_manager.handle_vma_end({
                'end_time': event_time,
                'content': event.get('content', ''),
                'rds_data': {}
            }, is_test=is_test)
            
        else:
            logging.debug(f"Okänd event-typ: {event_type}")

# ========================================
# MAIN ENTRY POINT
# ========================================
def main():
    """FÖRENKLAD main function med DAGLIG backup OCH RDS-indikator"""
    
    # Setup logging
    log_format = "%(asctime)s - DISPLAY - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(LOGS_DIR / f"display_monitor_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )
    
    logging.info("📡 UPPDATERAD Display Monitor - RDS-INDIKATOR för döva användare")
    logging.info("=" * 80)
    logging.info("✅ IMPLEMENTERAT:")
    logging.info("  📅 DAGLIG backup-struktur: backup/daily_YYYYMMDD/session_N_HHMMSS/")
    logging.info("  🔢 Automatisk session-numrering inom dagen")
    logging.info("  📊 Daglig metadata + session-metadata")
    logging.info("  🗂️ Organiserad backup per dag istället för per session")
    logging.info("  🧹 Bättre cleanup-möjligheter (radera hela dagar)")
    logging.info("  🔍 Enklare forensisk analys (\"Vad hände 10 juni?\")")
    logging.info("  📡 RDS-mottagningsindikator för döva användare")
    logging.info("🔧 HYBRID: Daglig backup + workspace cleanup")
    logging.info("🕐 3B: Bara transkript efter systemstart")
    logging.info("💡 ENKELT: Senaste txt-fil = senaste transkription")
    logging.info("🚨 VMA FIX: VMA end events hanteras för korrekt display-växling")
    logging.info("📡 RDS-STATUS: ● Aktiv | ○ Svag | ✕ Ingen mottagning")
    
    # Kontrollera att logs-katalog finns
    if not LOGS_DIR.exists():
        logging.error(f"Logs-katalog inte funnen: {LOGS_DIR}")
        logging.error("VMA-systemet måste köras först för att skapa loggar")
        sys.exit(1)
    
    # Skapa nödvändiga kataloger
    TRANSCRIPTIONS_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    (LOGS_DIR / "screen").mkdir(exist_ok=True)
    
    # Skapa och starta FÖRENKLAD display controller med RDS-indikator
    try:
        controller = SimplifiedDisplayController()
        controller.start()
        
        logging.info("✅ FÖRENKLAD Display Monitor aktiv med RDS-INDIKATOR")
        logging.info("🏠 Startup-skärm visas nu")
        logging.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE → repeat")
        logging.info("📅 Daglig backup genomförd")
        logging.info("💡 Enkel transkriptlogik aktiv")
        logging.info("🚨 VMA End Events: Aktivt för korrekt display-växling")
        logging.info("🗂️ DAGLIG backup: Organiserad och lätthanterlig struktur")
        logging.info("📡 RDS-indikator: Visar mottagningsstatus för döva användare")
        logging.info("Tryck Ctrl+C för att stoppa")
        
        # Keep running
        while True:
            time.sleep(60)
            
            # Status var 10:e minut MED RDS-info
            if datetime.now().minute % 10 == 0:
                status = controller.display_manager.get_status()
                current_state = status.get('current_state', 'unknown')
                screenshots = status.get('screenshots_available', 0)
                processed_events = len(controller.monitor.processed_events)
                processed_trans = len(controller.monitor.processed_transcriptions)
                
                # Visa RDS-status i logging
                rds_status = controller.monitor.get_rds_status()
                rds_info = f"RDS: {rds_status['indicator']} {rds_status['time_str']}"
                
                logging.info(f"📊 Status: {current_state} mode, {screenshots} skärmdumpar, {processed_events} events, {processed_trans} transkriptioner, {rds_info}")
            
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt - stoppar FÖRENKLAD display monitor")
    except Exception as e:
        logging.error(f"Fatal fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'controller' in locals():
            controller.stop()
        
        logging.info("FÖRENKLAD Display Monitor stoppad - med RDS-INDIKATOR för döva användare!")

if __name__ == "__main__":
    main()
