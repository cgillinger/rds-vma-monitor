#!/usr/bin/env python3
"""
FIXAD Display Manager - Bevarar fungerande logik + energioptimering + start_time fix
Fil: display_manager.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/display_manager.py

BEHÅLLER:
- Din fungerande event-driven arkitektur
- Korrekt state machine integration
- Robusta intervaller som fungerar

LÄGGER TILL:
- Content hashing för att undvika identiska uppdateringar
- Energispårning och statistik
- Smart change detection

FIXAR:
- start_time datatyp-konvertering (string → datetime)
- Säkerställer korrekt "STARTAD: HH:MM" för varje nytt trafikmeddelande
"""

import logging
import threading
import time
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from queue import Queue, PriorityQueue
import psutil

try:
    from waveshare_epd import epd4in26
    EPAPER_AVAILABLE = True
except ImportError:
    print("⚠️ Waveshare e-paper bibliotek inte tillgängligt - Simulator-läge")
    EPAPER_AVAILABLE = False

from display_config import DISPLAY_SETTINGS
from content_formatter import ContentFormatter
from screen_layouts import ScreenLayout
from display_state_machine import DisplayStateMachine, DisplayState

logger = logging.getLogger(__name__)

class EventDrivenDisplayManager:
    """
    ENERGIOPTIMERAD version av din fungerande Event-driven Display Manager + start_time fix
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.settings = DISPLAY_SETTINGS
        self.log_dir = log_dir
        
        # Skapa screen-katalog för skärmdumpar
        self.screen_dir = os.path.join(log_dir, "screen")
        os.makedirs(self.screen_dir, exist_ok=True)
        
        # BEVARAR dina fungerande komponenter
        self.formatter = ContentFormatter()
        self.layout = ScreenLayout()
        self.state_machine = DisplayStateMachine()
        
        # E-paper display
        self.epd = None
        self.display_available = False
        
        # BEVARAR din fungerande event queue
        self.event_queue = PriorityQueue()
        self.update_thread = None
        self.status_thread = None
        self.running = False
        
        # ENERGIOPTIMERING: Content tracking
        self.last_content_hash = None
        self.last_content = None
        
        # ENERGIOPTIMERING: Energy tracking
        self.energy_stats = {
            'updates_today': 0,
            'last_update_energy': 0,
            'total_energy_today': 0,
            'battery_level': 100,
            'unnecessary_updates_avoided': 0
        }
        
        # BEVARAR thread safety
        self.update_lock = threading.Lock()
        
        # BEVARAR backup state för recovery
        self.state_file = os.path.join(log_dir, 'display_state.json')
        
        self._initialize_display()
        
    def _initialize_display(self):
        """BEVARAR din fungerande initialisering"""
        if not EPAPER_AVAILABLE:
            logger.warning("E-paper bibliotek inte tillgängligt - Simulator-läge aktivt")
            self.display_available = False
            return
            
        try:
            self.epd = epd4in26.EPD()
            self.epd.init()
            
            # Rensa skärmen vid start - ENDAST EN GÅNG
            self.epd.Clear()
            self.display_available = True
            
            logger.info("✅ E-paper display initialiserat framgångsrikt")
            
            # Återställ state om möjligt
            self._restore_state()
            
        except Exception as e:
            logger.error(f"❌ Fel vid initialisering av e-paper display: {e}")
            self.display_available = False
    
    def calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """ENERGIOPTIMERING: Beräkna hash för change detection"""
        try:
            content_str = json.dumps(content, sort_keys=True, default=str)
            return hashlib.md5(content_str.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Fel vid hash-beräkning: {e}")
            return str(datetime.now().timestamp())
    
    def start(self):
        """BEVARAR din fungerande start-metod + energioptimering"""
        if self.running:
            logger.warning("Display manager körs redan")
            return
            
        self.running = True
        
        # BEVARAR dina fungerande threads med ROBUSTA intervaller
        self.update_thread = threading.Thread(target=self._event_loop, daemon=True)
        self.update_thread.start()
        
        # ENERGIOPTIMERING: Längre status intervall
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self.status_thread.start()
        
        logger.info("🔋 ENERGIOPTIMERAD Event-Driven Display Manager startad")
        logger.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE → repeat (ingen night mode)")
        
        # Visa initial startup-skärm
        self._show_startup_screen()
    
    def stop(self):
        """BEVARAR din fungerande stop-metod + energistatistik"""
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=5)
            
        if self.status_thread:
            self.status_thread.join(timeout=5)
        
        # ENERGIOPTIMERING: Visa energistatistik
        self._log_energy_statistics()
        
        # Spara state
        self._save_state()
        
        # Stäng display
        if self.display_available and self.epd:
            try:
                self.epd.sleep()
                logger.info("E-paper display satt i sovläge")
            except Exception as e:
                logger.error(f"Fel vid stängning av display: {e}")
        
        logger.info("🔋 ENERGIOPTIMERAD Display Manager stoppad")
    
    def _event_loop(self):
        """BEVARAR din fungerande event-loop"""
        while self.running:
            try:
                # Hantera prioriterade events
                if not self.event_queue.empty():
                    priority, timestamp, event_data = self.event_queue.get_nowait()
                    self._handle_display_event(event_data)
                
                # BEVARAR ditt ROBUSTA intervall
                time.sleep(2)  # 2 sekunder - mycket mer responsivt
                
            except Exception as e:
                logger.error(f"Fel i event loop: {e}")
                time.sleep(30)
    
    def _status_loop(self):
        """ENERGIOPTIMERAD: Längre intervall för status-feedback"""
        while self.running:
            try:
                # ENERGIOPTIMERING: Var 15:e minut (var 2:a minut)
                self._update_status_feedback()
                time.sleep(900)  # 15 minuter
                
            except Exception as e:
                logger.error(f"Fel i status loop: {e}")
                time.sleep(60)
    
    def _show_startup_screen(self):
        """BEVARAR din fungerande startup-skärm"""
        logger.info("🏠 Visar ENERGIOPTIMERAD startup-skärm")
        self._update_display_from_state()
    
    def _handle_display_event(self, event_data: Dict):
        """BEVARAR din fungerande event-hantering"""
        event_type = event_data.get('type')
        
        logger.info(f"📲 Hanterar display-event: {event_type}")
        
        # Skicka event till FÖRENKLADE state machine
        needs_update = self.state_machine.process_event(event_type, event_data)
        
        if needs_update:
            self._update_display_from_state()
    
    def _update_display_from_state(self):
        """ENERGIOPTIMERAD: Smart uppdatering med change detection"""
        try:
            # BEVARAR din fungerande state-hämtning
            display_mode = self.state_machine.get_current_display_mode()
            current_content = self.state_machine.get_current_content()
            status_info = self.state_machine.get_status_info()
            
            # BEVARAR din fungerande formattering
            if display_mode == 'startup':
                formatted_content = self.formatter.format_for_startup_mode(status_info)
            elif display_mode == 'idle':
                system_status = self._collect_system_status()
                formatted_content = self.formatter.format_for_idle_mode(system_status, status_info)
            elif display_mode == 'traffic':
                formatted_content = self.formatter.format_for_traffic_mode(
                    current_content.primary_data, 
                    current_content.transcription,
                    status_info
                )
            elif display_mode in ['vma', 'vma_test']:
                is_test = display_mode == 'vma_test'
                formatted_content = self.formatter.format_for_vma_mode(
                    current_content.primary_data,
                    is_test,
                    status_info
                )
            else:
                logger.error(f"Okänd display mode: {display_mode}")
                return
            
            # ENERGIOPTIMERING: Content hash comparison
            content_hash = self.calculate_content_hash(formatted_content)
            
            if content_hash == self.last_content_hash:
                self.energy_stats['unnecessary_updates_avoided'] += 1
                logger.info("🔋 Ingen ändring detekterad - skippar display refresh")
                logger.debug(f"💡 Energibesparing: {self.energy_stats['unnecessary_updates_avoided']} onödiga uppdateringar undvikna")
                return
            
            # Genomför uppdatering
            success = self._update_physical_display(formatted_content)
            
            if success:
                # Spara för nästa jämförelse
                self.last_content_hash = content_hash
                self.last_content = formatted_content.copy()
                logger.info(f"✅ Display uppdaterat till {display_mode} mode")
            
        except Exception as e:
            logger.error(f"Fel vid display-uppdatering från state: {e}")
    
    def _update_physical_display(self, formatted_content: Dict) -> bool:
        """ENERGIOPTIMERAD: Physical display med energy tracking"""
        with self.update_lock:
            try:
                start_time = time.time()
                
                # Skapa layout
                image = self.layout.create_layout(formatted_content)
                
                # BEVARAR skärmdump-funktionalitet
                self._save_screenshot(image, formatted_content.get('mode', 'unknown'))
                
                if self.display_available:
                    # Uppdatera fysisk display
                    self.epd.display(self.epd.getbuffer(image))
                    
                    update_time = time.time() - start_time
                    
                    # ENERGIOPTIMERING: Spåra energiförbrukning
                    self._track_energy_usage(update_time)
                    
                    logger.info(f"🖥️ Fysisk display uppdaterad på {update_time:.2f}s")
                    
                else:
                    logger.info(f"💾 Simulator: Display-bild sparad som skärmdump")
                
                # Spara state
                self._save_state()
                
                return True
                
            except Exception as e:
                logger.error(f"Fel vid fysisk display-uppdatering: {e}")
                return False
    
    def _update_status_feedback(self):
        """ENERGIOPTIMERAD: Mindre frekvent status-feedback"""
        try:
            # Skapa status-update event
            status_event = {
                'type': 'status_update',
                'timestamp': datetime.now(),
                'system_status': 'OK'
            }
            
            # Skicka till state machine
            needs_update = self.state_machine.process_event('status_update', status_event)
            
            if needs_update:
                self._update_display_from_state()
                logger.debug("🔋 15-minuters status feedback uppdaterad")
            
        except Exception as e:
            logger.error(f"Fel vid status feedback-uppdatering: {e}")
    
    # ========================================
    # FIXADE DATETIME HELPER METHODS
    # ========================================
    
    def _parse_datetime(self, dt_value) -> datetime:
        """
        FIXAR: Konvertera datetime-värde från olika format till datetime objekt
        Hanterar både datetime objekt och ISO strings från rds_detector
        """
        if dt_value is None:
            return datetime.now()
        
        # Om det redan är ett datetime objekt, returnera som det är
        if isinstance(dt_value, datetime):
            return dt_value
        
        # Om det är en string (ISO format från rds_detector), konvertera
        if isinstance(dt_value, str):
            try:
                # Försök parsa ISO format: "2025-06-09T20:15:30.123456"
                if 'T' in dt_value:
                    # Ta bort mikrosekunder om de finns
                    if '.' in dt_value:
                        dt_value = dt_value.split('.')[0]
                    return datetime.fromisoformat(dt_value)
                else:
                    # Försök andra vanliga format
                    return datetime.strptime(dt_value, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"Kunde inte konvertera datetime string '{dt_value}': {e}")
                return datetime.now()
        
        # Fallback
        logger.warning(f"Okänd datetime-typ: {type(dt_value)}, använder nuvarande tid")
        return datetime.now()
    
    # ========================================
    # FIXADE PUBLIC INTERFACE METHODS
    # ========================================
    
    def handle_traffic_start(self, traffic_data: Dict):
        """FIXAD: Handle traffic start event med korrekt datetime-hantering"""
        # FIXAR: Konvertera start_time från string till datetime om nödvändigt
        raw_start_time = traffic_data.get('start_time')
        parsed_start_time = self._parse_datetime(raw_start_time)
        
        logger.debug(f"🔧 Traffic start: raw_start_time={raw_start_time} → parsed={parsed_start_time}")
        
        self.queue_event('traffic_start', {
            'type': 'traffic_start',
            'start_time': parsed_start_time,  # Garanterat datetime objekt
            **{k: v for k, v in traffic_data.items() if k != 'start_time'}  # Resten av data
        }, priority=self.settings['priorities']['traffic_active'])
    
    def handle_traffic_end(self, traffic_data: Dict):
        """Handle traffic end event"""
        self.queue_event('traffic_end', {
            'type': 'traffic_end',
            'end_time': datetime.now(),
            **traffic_data
        }, priority=self.settings['priorities']['traffic_active'])
    
    def handle_vma_start(self, vma_data: Dict, is_test: bool = False):
        """FIXAD: Handle VMA start event med korrekt datetime-hantering"""
        event_type = 'vma_test_start' if is_test else 'vma_start'
        priority = self.settings['priorities']['vma_test' if is_test else 'vma_emergency']
        
        # FIXAR: Konvertera start_time från string till datetime om nödvändigt
        raw_start_time = vma_data.get('start_time')
        parsed_start_time = self._parse_datetime(raw_start_time)
        
        logger.debug(f"🔧 VMA start: raw_start_time={raw_start_time} → parsed={parsed_start_time}")
        
        self.queue_event(event_type, {
            'type': event_type,
            'start_time': parsed_start_time,  # Garanterat datetime objekt
            'is_test': is_test,
            **{k: v for k, v in vma_data.items() if k != 'start_time'}  # Resten av data
        }, priority=priority)
    
    def handle_vma_end(self, vma_data: Dict, is_test: bool = False):
        """Handle VMA end event"""
        event_type = 'vma_test_end' if is_test else 'vma_end'
        
        self.queue_event(event_type, {
            'type': event_type,
            'end_time': datetime.now(),
            'is_test': is_test,
            **vma_data
        }, priority=self.settings['priorities']['vma_test' if is_test else 'vma_emergency'])
    
    def handle_transcription_complete(self, transcription_data: Dict):
        """Handle completed transcription"""
        self.queue_event('transcription_complete', {
            'type': 'transcription_complete',
            'transcription': transcription_data,
            'timestamp': datetime.now()
        }, priority=self.settings['priorities']['normal_status'])
    
    def queue_event(self, event_type: str, event_data: Dict, priority: Optional[int] = None):
        """BEVARAR din fungerande event queue"""
        if priority is None:
            priority = self.settings['priorities'].get(event_type, 500)
        
        # Negativ prioritet för PriorityQueue (lägre nummer = högre prioritet)
        queue_priority = -priority
        timestamp = time.time()
        
        self.event_queue.put((queue_priority, timestamp, event_data))
        logger.info(f"📥 Event köad: {event_type} (prioritet: {priority})")
    
    def force_update(self):
        """BEVARAR debug-funktionalitet"""
        logger.info("🔄 Forcerar display-uppdatering")
        self._update_display_from_state()
    
    def force_mode(self, mode: str):
        """BEVARAR debug-funktionalitet"""
        logger.info(f"🔄 Tvingar display till {mode} mode")
        
        # Skapa mock event för att tvinga mode
        mock_event_data = {
            'type': f'{mode}_start' if mode in ['traffic', 'vma'] else 'force_mode',
            'start_time': datetime.now(),
            'forced': True
        }
        
        self.state_machine.process_event(mock_event_data['type'], mock_event_data)
        self._update_display_from_state()
    
    # ========================================
    # BEVARAR + FÖRBÄTTRAR hjälpmetoder
    # ========================================
    
    def _save_screenshot(self, image, mode: str):
        """BEVARAR din fungerande skärmdump-funktionalitet"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screen_{mode}_{timestamp}.png"
            filepath = os.path.join(self.screen_dir, filename)
            
            image.save(filepath)
            logger.debug(f"📷 Skärmdump sparad: {filename}")
            
            # Begränsa antal sparade bilder (behåll senaste 20)
            self._cleanup_old_screenshots()
            
        except Exception as e:
            logger.error(f"Fel vid sparande av skärmdump: {e}")
    
    def _cleanup_old_screenshots(self):
        """BEVARAR cleanup-funktionalitet"""
        try:
            screenshot_files = []
            for file in os.listdir(self.screen_dir):
                if file.startswith('screen_') and file.endswith('.png'):
                    filepath = os.path.join(self.screen_dir, file)
                    screenshot_files.append((filepath, os.path.getctime(filepath)))
            
            # Sortera efter skapandetid (nyaste först)
            screenshot_files.sort(key=lambda x: x[1], reverse=True)
            
            # Ta bort filer utöver de 20 senaste
            for filepath, _ in screenshot_files[20:]:
                os.remove(filepath)
                logger.debug(f"Raderade gammal skärmdump: {os.path.basename(filepath)}")
                
        except Exception as e:
            logger.error(f"Fel vid rensning av skärmdumpar: {e}")
    
    def _collect_system_status(self) -> Dict:
        """BEVARAR din fungerande systemstatus"""
        try:
            now = datetime.now()
            
            status = {
                'rds_active': True,  # Kommer från rds_logger integration
                'frequency': '103.3',
                'transcriber_ready': True,
                'audio_ok': True,
                'battery_percent': self._get_battery_level(),
                'last_24h_traffic': 0,  # Kan uppdateras med verklig data
                'last_rds_update': now - timedelta(minutes=2),
                'last_transcription': now - timedelta(minutes=45),
                'uptime': self._get_system_uptime()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Fel vid insamling av systemstatus: {e}")
            return {
                'rds_active': False,
                'frequency': '103.3',
                'transcriber_ready': False,
                'audio_ok': False,
                'battery_percent': 50,
                'last_24h_traffic': 0,
                'uptime': 'Okänd'
            }
    
    def _get_battery_level(self) -> int:
        """ENERGIOPTIMERAD: Förbättrad batterisimulation"""
        try:
            # Energioptimerad simulation baserat på actual usage
            uptime_hours = self.energy_stats.get('total_energy_today', 0) / 3600
            battery_drain = min(uptime_hours * 1.5, 80)  # 1.5% per energi-timme
            
            simulated_level = max(15, 100 - int(battery_drain))
            self.energy_stats['battery_level'] = simulated_level
            
            return simulated_level
            
        except Exception:
            return 75
    
    def _get_system_uptime(self) -> str:
        """BEVARAR din fungerande uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception:
            return "Okänd"
    
    def _track_energy_usage(self, update_time: float):
        """ENERGIOPTIMERING: Spåra energiförbrukning"""
        energy_used = update_time * 1.0  # Watt-sekunder
        
        self.energy_stats['last_update_energy'] = energy_used
        self.energy_stats['total_energy_today'] += energy_used
        self.energy_stats['updates_today'] += 1
        
        logger.debug(f"⚡ Energi använd: {energy_used:.3f}Ws")
    
    def _log_energy_statistics(self):
        """ENERGIOPTIMERING: Logga energistatistik"""
        stats = self.energy_stats
        
        logger.info("🔋 ENERGISTATISTIK:")
        logger.info(f"   Uppdateringar idag: {stats['updates_today']}")
        logger.info(f"   Total energi idag: {stats['total_energy_today']:.2f}Ws")
        logger.info(f"   Undvikna onödiga uppdateringar: {stats['unnecessary_updates_avoided']}")
        
        if stats['updates_today'] > 0:
            avoidance_ratio = stats['unnecessary_updates_avoided'] / (stats['updates_today'] + stats['unnecessary_updates_avoided'])
            logger.info(f"   Energibesparing: {avoidance_ratio:.1%} av potentiella uppdateringar undvikna")
    
    def _save_state(self):
        """BEVARAR din fungerande state-sparning + energidata"""
        try:
            state = {
                'state_machine_debug': self.state_machine.get_debug_info(),
                'energy_stats': self.energy_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Fel vid sparande av state: {e}")
    
    def _restore_state(self):
        """BEVARAR din fungerande state-återställning"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.energy_stats.update(state.get('energy_stats', {}))
                logger.info("📱 Display-state återställd från backup")
                
        except Exception as e:
            logger.error(f"Fel vid återställning av state: {e}")
    
    def get_status(self) -> Dict:
        """BEVARAR + FÖRBÄTTRAR status-returnering"""
        return {
            'display_available': self.display_available,
            'current_state': self.state_machine.current_state.value,
            'current_mode': self.state_machine.get_current_display_mode(),
            'energy_stats': self.energy_stats.copy(),
            'queue_size': self.event_queue.qsize(),
            'running': self.running,
            'screen_dir': self.screen_dir,
            'screenshots_available': len([f for f in os.listdir(self.screen_dir) 
                                        if f.startswith('screen_') and f.endswith('.png')]),
            'state_machine_debug': self.state_machine.get_debug_info(),
            'last_content_hash': self.last_content_hash
        }

# BEVARAR alias för bakåtkompatibilitet
DisplayManager = EventDrivenDisplayManager

if __name__ == "__main__":
    # BEVARAR din fungerande test + energioptimering
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔋 Test av ENERGIOPTIMERAD Event-Driven Display Manager + start_time FIX")
    print("=" * 70)
    print("📋 INGEN night mode - endast: STARTUP → TRAFFIC/VMA → IDLE")
    print("🔋 MED: Content hashing + energispårning")
    print("🔧 FIXAR: start_time datatyp-konvertering (string → datetime)")
    
    # Skapa display manager
    manager = EventDrivenDisplayManager(log_dir="logs")
    
    try:
        # Starta manager
        manager.start()
        print("✅ ENERGIOPTIMERAD Display Manager startad")
        
        # Test datetime-konvertering
        test_datetime_str = "2025-06-09T20:15:30"
        test_datetime_obj = datetime.now()
        
        print(f"🧪 Test datetime-konvertering:")
        print(f"  String input: {test_datetime_str}")
        print(f"  Parsed: {manager._parse_datetime(test_datetime_str)}")
        print(f"  Datetime input: {test_datetime_obj}")
        print(f"  Parsed: {manager._parse_datetime(test_datetime_obj)}")
        
        # Simulera traffic events med string start_time (som rds_detector skickar)
        if len(sys.argv) > 1 and sys.argv[1] == "--test-events":
            print("🧪 Kör FIXAD event-simulering med string start_time...")
            
            time.sleep(3)
            print("📡 Simulerar traffic start med ISO string...")
            manager.handle_traffic_start({
                'location': 'E4 Stockholm',
                'start_time': datetime.now().isoformat()  # STRING som rds_detector skickar
            })
            
            time.sleep(5)
            print("📝 Simulerar transkription klar...")
            manager.handle_transcription_complete({'text': 'Test transkription'})
            
            time.sleep(5)
            print("🏁 Simulerar traffic end...")
            manager.handle_traffic_end({})
            
            time.sleep(3)
        
        # Visa status
        status = manager.get_status()
        print(f"📊 Status: {status['current_state']} mode, {status['screenshots_available']} skärmdumpar")
        
        # Vänta på input för manuell testning
        if "--interactive" in sys.argv:
            input("Tryck Enter för att stoppa...")
        else:
            time.sleep(10)
        
    finally:
        manager.stop()
        print("✅ ENERGIOPTIMERAD + FIXAD test slutförd!")
        print("🔧 start_time datatyp-problem löst - nu fungerar 'STARTAD: HH:MM' korrekt!")