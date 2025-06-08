#!/usr/bin/env python3
"""
FIXAD Display Monitor - Korrekt filnamnsparsning för transkriptionsmatchning
Fil: display_monitor.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/display_monitor.py

FIXAR:
- Korrekt parsning av event-filnamn
- Rätt matchning mellan event och transkription
"""

import os
import sys
import time
import json
import logging
import threading
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
# CONFIGURATION - ENERGIOPTIMERAT
# ========================================
PROJECT_DIR = Path(__file__).parent
LOGS_DIR = PROJECT_DIR / "logs"
TRANSCRIPTIONS_DIR = LOGS_DIR / "transcriptions"  # NYTT: Transkriptionsmapp

# RDS log files som VMA-systemet skapar
RDS_CONTINUOUS_LOG_PATTERN = "rds_continuous_*.log"
RDS_EVENT_LOG_PATTERN = "rds_event_*.log"
SYSTEM_LOG_PATTERN = "system_*.log"

# NYTT: Transkriptionsfil-mönster
TRANSCRIPTION_PATTERN = "audio_traffic_*.txt"

# ROBUSTA polling intervals för att undvika edge cases
LOG_POLL_INTERVAL = 3     # seconds (var 10s → 3s) - mycket mer responsivt
TRANSCRIPTION_POLL_INTERVAL = 5  # NYTT: Kontrollera transkriptioner var 5:e sekund

# ENERGIOPTIMERING: Längre status intervall
STATUS_UPDATE_INTERVAL = 900  # seconds (15 minuter för heartbeat)

# BEVARAR DIN FUNGERANDE CUTOFF LOGIK
STARTUP_CUTOFF_MINUTES = 15  # Bara events från senaste 15 min vid start

# ========================================
# BEVARAR DIN FUNGERANDE LOG FILE MONITOR
# ========================================
class LogFileMonitor:
    """
    BEVARAR din fungerande version + transkriptionsövervakning
    """
    
    def __init__(self):
        self.logs_dir = LOGS_DIR
        self.transcriptions_dir = TRANSCRIPTIONS_DIR
        self.last_positions = {}
        self.processed_events = set()  # KRITISK: Bevarar din fungerande deduplication
        self.processed_transcriptions = set()  # NYTT: Spåra processade transkriptioner
        self.startup_time = datetime.now()
        
        # NYTT: Mappar aktiva traffic events till deras audio-filer
        self.active_traffic_events = {}  # event_file → audio_file mapping
        
        self.system_status = {
            'rds_active': False,
            'last_rds_time': None,
            'events_today': 0,
            'last_event': None
        }
        
        # BEVARAR DIN FUNGERANDE CUTOFF LOGIK
        self.cutoff_time = self.startup_time - timedelta(minutes=STARTUP_CUTOFF_MINUTES)
        
        # ENERGIOPTIMERING: Spåra sista status update
        self.last_status_update = datetime.now() - timedelta(minutes=20)  # Force initial
        
        logging.info(f"FIXAD LogFileMonitor initialiserad med transkriptionsövervakning")
        logging.info(f"Startup: {self.startup_time}")
        logging.info(f"Event cutoff: {self.cutoff_time} (15 min grace period)")
        logging.info(f"Robusta polling: {LOG_POLL_INTERVAL}s (var 10s)")
        logging.info(f"Transkriptionspolling: {TRANSCRIPTION_POLL_INTERVAL}s")
        logging.info("🔋 ENERGIOPTIMERING: 15min status intervall")
        logging.info("📋 INGEN night mode - enkla state transitions")
    
    def get_latest_rds_log(self) -> Optional[Path]:
        """Hitta senaste RDS continuous log"""
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
                
                # BEVARAR DIN FUNGERANDE FILTER 1: Bara filer efter längre cutoff (15 min)
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
    
    def check_for_new_transcriptions(self) -> List[Dict]:
        """NYTT: Kontrollera efter nya transkriptionsfiler"""
        transcriptions = []
        
        if not self.transcriptions_dir.exists():
            return transcriptions
        
        # Hitta alla transkriptionsfiler
        transcription_files = list(self.transcriptions_dir.glob(TRANSCRIPTION_PATTERN))
        
        for trans_file in transcription_files:
            try:
                # Skippa redan processade
                if str(trans_file) in self.processed_transcriptions:
                    continue
                
                # Kontrollera att filen är färdigskriven (inte modifierad på 2 sekunder)
                file_mtime = trans_file.stat().st_mtime
                if time.time() - file_mtime < 2:
                    continue  # Vänta tills filen är stabil
                
                # Extrahera audio-filnamn från transkriptionsfilnamn
                # Format: audio_traffic_start_TIMESTAMP_TIMESTAMP.txt
                filename = trans_file.stem
                if filename.startswith('audio_traffic_'):
                    # Hitta motsvarande audio-fil
                    parts = filename.split('_')
                    if len(parts) >= 4:
                        audio_base = '_'.join(parts[:4])  # audio_traffic_start_TIMESTAMP
                        
                        # Läs transkriptionsinnehåll
                        transcription_data = self._parse_transcription_file(trans_file)
                        if transcription_data:
                            transcription_data['audio_base'] = audio_base
                            transcriptions.append(transcription_data)
                            self.processed_transcriptions.add(str(trans_file))
                            logging.info(f"🎯 Ny transkription hittad: {trans_file.name}")
                
            except Exception as e:
                logging.error(f"Fel vid kontroll av transkription {trans_file}: {e}")
        
        return transcriptions
    
    def _parse_transcription_file(self, trans_file: Path) -> Optional[Dict]:
        """NYTT: Parsa transkriptionsfil och extrahera nyckelinformation"""
        try:
            with open(trans_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extrahera olika sektioner
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
            
            # Extrahera trafikinformation
            if '## EXTRAHERAD TRAFIKINFORMATION' in content:
                info = {}
                section_start = content.find('## EXTRAHERAD TRAFIKINFORMATION')
                section_end = content.find('\n\n', section_start)
                section = content[section_start:section_end]
                
                # Vägar
                if 'Vägar:' in section:
                    line_start = section.find('Vägar:')
                    line_end = section.find('\n', line_start)
                    roads = section[line_start+6:line_end].strip()
                    if roads:
                        info['roads'] = roads
                
                # Platser
                if 'Platser:' in section:
                    line_start = section.find('Platser:')
                    line_end = section.find('\n', line_start)
                    locations = section[line_start+8:line_end].strip()
                    if locations:
                        info['locations'] = locations
                
                # Typ
                if 'Typ:' in section:
                    line_start = section.find('Typ:')
                    line_end = section.find('\n', line_start)
                    incident_type = section[line_start+4:line_end].strip()
                    if incident_type:
                        info['incident_type'] = incident_type
                
                if info:
                    result['extracted_info'] = info
            
            return result
            
        except Exception as e:
            logging.error(f"Fel vid parsning av transkriptionsfil {trans_file}: {e}")
            return None
    
    def match_transcription_to_event(self, transcription: Dict) -> Optional[str]:
        """NYTT: Matcha transkription med aktiv traffic event"""
        audio_base = transcription.get('audio_base')
        if not audio_base:
            return None
        
        # Sök i aktiva events
        for event_file, event_info in self.active_traffic_events.items():
            if event_info.get('audio_base') == audio_base:
                logging.info(f"✅ Matchade transkription med event: {event_file}")
                return event_file
        
        return None
    
    def read_new_rds_data(self) -> List[Dict]:
        """Läs ny RDS-data från continuous log"""
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
            logging.error(f"Fel vid läsning av RDS-log: {e}")
        
        return new_data
    
    def update_system_status(self):
        """Uppdatera systemstatus"""
        # Check RDS activity
        rds_data = self.read_new_rds_data()
        if rds_data:
            self.system_status['rds_active'] = True
            self.system_status['last_rds_time'] = datetime.now()
        
        # Check if RDS is stale - LÄNGRE TIMEOUT
        if (self.system_status['last_rds_time'] and 
            datetime.now() - self.system_status['last_rds_time'] > timedelta(minutes=15)):
            self.system_status['rds_active'] = False
        
        # Count processed events
        self.system_status['events_today'] = len(self.processed_events)
    
    def detect_events_from_logs(self) -> List[Dict]:
        """BEVARAR DIN FUNGERANDE VERSION: Detektera ENDAST nya events"""
        events = []
        
        recent_events = self.get_recent_event_logs()
        
        for event_file in recent_events:
            try:
                file_key = str(event_file)
                
                # Parse event-fil
                event_info = self._parse_event_file(event_file)
                if event_info:
                    # BEVARAR DIN FUNGERANDE timestamp-kontroll
                    event_time = event_info.get('time')
                    if event_time and event_time < self.cutoff_time:
                        logging.debug(f"Skippar gammalt event: {event_file.name}")
                        self.processed_events.add(file_key)
                        continue
                    
                    # NYTT: Spara info om traffic_start events för transkriptionsmatchning
                    if event_info['type'] == 'traffic_start':
                        # FIXAD PARSNING: Korrekt extrahering av timestamp
                        # Filnamn: rds_event_traffic_start_YYYYMMDD_HHMMSS.log
                        filename_parts = event_file.stem.split('_')
                        
                        # Hitta datum och tid i filnamnet
                        if len(filename_parts) >= 5:
                            date_part = filename_parts[-2]  # YYYYMMDD
                            time_part = filename_parts[-1]  # HHMMSS
                            audio_timestamp = f"{date_part}_{time_part}"
                            audio_base = f"audio_traffic_start_{audio_timestamp}"
                            
                            self.active_traffic_events[file_key] = {
                                'audio_base': audio_base,
                                'start_time': event_time,
                                'event_info': event_info
                            }
                            logging.info(f"📌 Sparar traffic event för matchning: {audio_base}")
                    
                    # NYTT: Rensa aktiv event vid traffic_end
                    elif event_info['type'] == 'traffic_end':
                        # Hitta och ta bort matchande start event
                        for ef, ei in list(self.active_traffic_events.items()):
                            if 'traffic_start' in ef:
                                del self.active_traffic_events[ef]
                                logging.info(f"🏁 Traffic slutade, rensar aktiv event")
                                break
                    
                    # Detta är ett nytt, relevant event
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
        """Parse event-fil"""
        try:
            with open(event_file, 'r') as f:
                content = f.read()
            
            # Extract event type från filename
            filename = event_file.name
            if 'traffic_start' in filename:
                event_type = 'traffic_start'
            elif 'traffic_end' in filename:
                event_type = 'traffic_end'
            elif 'vma_start' in filename:
                event_type = 'vma_start'
            elif 'vma_test_start' in filename:
                event_type = 'vma_test_start'
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
# FIXAD DISPLAY CONTROLLER MED TRANSKRIPTIONSÖVERVAKNING
# ========================================
class SimplifiedDisplayController:
    """
    FIXAD Display Controller med transkriptionsövervakning
    """
    
    def __init__(self):
        self.monitor = LogFileMonitor()
        self.display_manager = DisplayManager(log_dir=str(LOGS_DIR))
        self.startup_time = datetime.now()
        
        logging.info("FIXAD DisplayController initialiserad med transkriptionsövervakning")
        logging.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE (INGEN night mode)")
        logging.info("🔋 15min status intervall för optimal batteritid")
        logging.info("📝 Övervakar transkriptioner var 5:e sekund")
    
    def start(self):
        """Starta FIXAD display-kontroll med transkriptionsövervakning"""
        if not self.display_manager.display_available:
            logging.warning("Display inte tillgänglig - kör i simulator-läge")
        
        # Starta display manager (visar startup-skärm automatiskt)
        self.display_manager.start()
        logging.info("🖥️ FIXAD Display Manager startad")
        
        # Start monitoring thread med ROBUSTA intervaller
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # NYTT: Start transkriptionsövervakning
        transcription_thread = threading.Thread(target=self._transcription_monitoring_loop, daemon=True)
        transcription_thread.start()
        
        logging.info("📡 FIXAD monitoring aktiv med transkriptionsövervakning")
        logging.info("✅ Startup-skärm visas tills första event")
        logging.info("♾️  Events visas tills nästa event (inga timers)")
        logging.info("🔋 Status uppdateras var 15:e minut (heartbeat)")
        logging.info("📝 Transkriptioner kontrolleras var 5:e sekund")
    
    def stop(self):
        """Stoppa display-kontroll"""
        if self.display_manager:
            self.display_manager.stop()
        logging.info("🔋 FIXAD Display Controller stoppad")
    
    def _monitoring_loop(self):
        """ENERGIOPTIMERAD och ROBUST monitoring loop"""
        while True:
            try:
                # BEVARAR DIN FUNGERANDE EVENT-DETECTION
                events = self.monitor.detect_events_from_logs()
                for event in events:
                    self._handle_event(event)
                
                # Update system status
                self.monitor.update_system_status()
                
                # ENERGIOPTIMERING: Status update endast var 15:e minut
                now = datetime.now()
                time_since_status = (now - self.monitor.last_status_update).total_seconds()
                
                if time_since_status >= STATUS_UPDATE_INTERVAL:  # 15 minuter
                    # Skicka status update till display manager
                    if hasattr(self.display_manager, '_update_status_feedback'):
                        self.display_manager._update_status_feedback()
                    self.monitor.last_status_update = now
                    logging.debug("🔋 15-minuters heartbeat status update")
                
                # ROBUST polling intervall för att undvika edge cases
                time.sleep(LOG_POLL_INTERVAL)  # 3 sekunder (var 10s)
                
            except Exception as e:
                logging.error(f"Fel i monitoring loop: {e}")
                time.sleep(30)
    
    def _transcription_monitoring_loop(self):
        """NYTT: Övervaka transkriptioner separat"""
        while True:
            try:
                # Kontrollera nya transkriptioner
                new_transcriptions = self.monitor.check_for_new_transcriptions()
                
                for transcription in new_transcriptions:
                    # Matcha med aktiv event
                    event_file = self.monitor.match_transcription_to_event(transcription)
                    
                    if event_file:
                        # Skicka transkription till display manager
                        self._handle_transcription_complete(transcription)
                    else:
                        logging.warning(f"⚠️ Kunde inte matcha transkription: {transcription['filename']}")
                
                # Poll intervall för transkriptioner
                time.sleep(TRANSCRIPTION_POLL_INTERVAL)
                
            except Exception as e:
                logging.error(f"Fel i transkriptionsövervakning: {e}")
                time.sleep(30)
    
    def _handle_transcription_complete(self, transcription: Dict):
        """NYTT: Hantera färdig transkription"""
        logging.info(f"📝 Skickar transkription till display: {transcription.get('short_summary', 'N/A')}")
        
        # Skicka till display manager
        self.display_manager.handle_transcription_complete({
            'text': transcription.get('text', ''),
            'short_summary': transcription.get('short_summary', ''),
            'extracted_info': transcription.get('extracted_info', {}),
            'timestamp': transcription.get('timestamp', datetime.now())
        })
    
    def _handle_event(self, event: Dict):
        """BEVARAR DIN FUNGERANDE VERSION: Hantera event via event-driven display manager"""
        event_type = event['type']
        event_time = event['time']
        
        logging.info(f"🎯 Hantera ENERGIOPTIMERAT event: {event_type} vid {event_time}")
        
        # Skicka till FÖRENKLAD event-driven display manager
        if event_type == 'traffic_start':
            self.display_manager.handle_traffic_start({
                'start_time': event_time,
                'content': event.get('content', ''),
                'location': 'Okänd'  # Kan parsas från content
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
            
        else:
            logging.debug(f"Okänd event-typ: {event_type}")

# ========================================
# MAIN ENTRY POINT
# ========================================
def main():
    """FIXAD main function med transkriptionsövervakning"""
    
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
    
    logging.info("🔋 FIXAD Display Monitor - Med korrekt filnamnsparsning")
    logging.info("=" * 60)
    logging.info("✅ FÖRENKLADE ANVÄNDARKRAV:")
    logging.info("  1. Trafikmeddelanden visas tills nästa event")
    logging.info("  2. Startup-skärm vid start tills första event")
    logging.info("  3. VMA visas tills nästa event")
    logging.info("  4. Status feedback i alla modes")
    logging.info("  5. NYTT: Transkriptioner uppdateras automatiskt")
    logging.info("🔧 FIXAD: Korrekt parsning av event-filnamn")
    logging.info("🔋 ENERGIOPTIMERING: 15min status intervall")
    logging.info("📝 TRANSKRIPTIONER: Kontrolleras var 5:e sekund")
    logging.info("🔧 ARKITEKTUR: Event-driven state machine (inga timers)")
    logging.info("⚡ ROBUST: 3s polling (var 10s) + 15min cutoff (var 5min)")
    
    # Kontrollera att logs-katalog finns
    if not LOGS_DIR.exists():
        logging.error(f"Logs-katalog inte funnen: {LOGS_DIR}")
        logging.error("VMA-systemet måste köras först för att skapa loggar")
        sys.exit(1)
    
    # Skapa screen-katalog
    screen_dir = LOGS_DIR / "screen"
    screen_dir.mkdir(exist_ok=True)
    
    # Kontrollera/skapa transkriptionskatalog
    if not TRANSCRIPTIONS_DIR.exists():
        logging.warning(f"Transkriptionskatalog saknas, skapar: {TRANSCRIPTIONS_DIR}")
        TRANSCRIPTIONS_DIR.mkdir(exist_ok=True)
    
    # Skapa och starta FIXAD display controller
    try:
        controller = SimplifiedDisplayController()
        controller.start()
        
        logging.info("✅ FIXAD Display Monitor aktiv")
        logging.info("🏠 Startup-skärm visas nu")
        logging.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE → repeat")
        logging.info("🔋 15min heartbeat för optimal batteritid")
        logging.info("📝 Övervakar transkriptioner kontinuerligt")
        logging.info("🔧 Filnamnsparsning nu korrekt")
        logging.info("Tryck Ctrl+C för att stoppa")
        
        # Keep running
        while True:
            time.sleep(60)
            
            # Status var 10:e minut
            if datetime.now().minute % 10 == 0:
                status = controller.display_manager.get_status()
                current_state = status.get('current_state', 'unknown')
                current_mode = status.get('current_mode', 'unknown')
                screenshots = status.get('screenshots_available', 0)
                processed_events = len(controller.monitor.processed_events)
                processed_trans = len(controller.monitor.processed_transcriptions)
                
                logging.info(f"📊 Status: {current_state} mode, {screenshots} skärmdumpar, {processed_events} events, {processed_trans} transkriptioner")
                
                # State machine debug info
                debug_info = status.get('state_machine_debug', {})
                recent_transitions = debug_info.get('recent_transitions', [])
                if recent_transitions:
                    logging.info(f"🔄 Senaste transitions: {recent_transitions}")
            
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt - stoppar FIXAD display monitor")
    except Exception as e:
        logging.error(f"Fatal fel: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'controller' in locals():
            controller.stop()
        
        logging.info("FIXAD Display Monitor stoppad - med korrekt filnamnsparsning!")

if __name__ == "__main__":
    main()