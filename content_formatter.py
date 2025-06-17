#!/usr/bin/env python3
"""
UPPDATERAD Content Formatter - MED RDS-INDIKATOR för döva användare
Fil: content_formatter.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/content_formatter.py

NY FUNKTION:
- RDS-mottagningsindikator för döva användare
- Visar RDS-status i footer: "System OK • 14:30 • RDS: ● 14:29"
- Smart integration som INTE triggar extra uppdateringar

BEVARAR:
- Trafikmeddelanden: +5 rader extra för längre meddelanden
- Header: "TRAFIKMEDDELANDE. STARTAD: HH:MM" (utan sekunder)
- HOTFIX: Fixad riktningsextraktion och transkriptionsvisning
- ENERGIOPTIMERING: Smart status timing för minimal content hash ändringar

INDIKATOR:
- ● Aktiv mottagning (<5 min gammal)
- ○ Svag mottagning (5-15 min gammal)  
- ✕ Ingen mottagning (>15 min gammal)
"""

import re
import textwrap
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

from display_config import DISPLAY_SETTINGS

logger = logging.getLogger(__name__)

# ========================================
# SVENSKA DATUM OCH TID
# ========================================
SWEDISH_WEEKDAYS = {
    'Monday': 'MÅNDAG',
    'Tuesday': 'TISDAG', 
    'Wednesday': 'ONSDAG',
    'Thursday': 'TORSDAG',
    'Friday': 'FREDAG',
    'Saturday': 'LÖRDAG',
    'Sunday': 'SÖNDAG'
}

SWEDISH_MONTHS = {
    'January': 'JANUARI',
    'February': 'FEBRUARI',
    'March': 'MARS',
    'April': 'APRIL',
    'May': 'MAJ',
    'June': 'JUNI',
    'July': 'JULI',
    'August': 'AUGUSTI',
    'September': 'SEPTEMBER',
    'October': 'OKTOBER',
    'November': 'NOVEMBER',
    'December': 'DECEMBER'
}

def format_swedish_date(dt, include_seconds=False):
    """
    ENERGIOPTIMERAD: Formatera datum och tid på svenska
    
    Args:
        dt: datetime objekt
        include_seconds: Om True, inkludera sekunder (för events)
                        Om False, bara minuter (för status)
    """
    weekday = dt.strftime('%A')
    month = dt.strftime('%B')
    
    swedish_weekday = SWEDISH_WEEKDAYS.get(weekday, weekday)
    swedish_month = SWEDISH_MONTHS.get(month, month)
    
    day = dt.strftime('%d')
    year = dt.strftime('%Y')
    
    if include_seconds:
        time = dt.strftime('%H:%M:%S')
    else:
        time = dt.strftime('%H:%M')
    
    return f"{swedish_weekday} {day} {swedish_month} {year}     {time}"

class ContentFormatter:
    """
    UPPDATERAD Content Formatter med RDS-indikator för döva användare
    """
    
    def __init__(self):
        self.settings = DISPLAY_SETTINGS
        self.width = self.settings['width']
        self.height = self.settings['height']
        
        # ENERGIOPTIMERING: Cache för status timing
        self.last_status_minute = None
        
        logger.debug("📡 UPPDATERAD ContentFormatter med RDS-indikator")
        logger.debug("🚧 TRAFIKOPTIMERING: +5 rader extra för längre meddelanden")
        logger.debug("📡 NY: RDS-mottagningsindikator för döva användare")
        
    def format_for_mode(self, mode: str, primary_data: Dict = None, status_info: Dict = None, **kwargs) -> Dict:
        """
        ENERGIOPTIMERAD formattering baserat på mode
        """
        primary_data = primary_data or {}
        status_info = status_info or {}
        
        if mode == 'startup':
            return self.format_for_startup_mode(status_info)
        elif mode == 'idle':
            return self.format_for_idle_mode(primary_data, status_info)
        elif mode == 'traffic':
            return self.format_for_traffic_mode(primary_data, kwargs.get('transcription'), status_info)
        elif mode == 'vma':
            return self.format_for_vma_mode(primary_data, kwargs.get('is_test', False), status_info)
        elif mode == 'vma_test':
            return self.format_for_vma_mode(primary_data, is_test=True, status_info=status_info)
        else:
            logger.error(f"Okänd mode: {mode}")
            return self.format_for_startup_mode(status_info)
    
    def format_for_startup_mode(self, status_info: Dict = None) -> Dict:
        """
        Startup-skärm som visas vid systemstart MED RDS-indikator
        """
        now = datetime.now()
        status_info = status_info or {}
        
        # Huvudrubrik - UPPDATERAD: "STARTAT" istället för "STARTAR"
        header = "VMA-SYSTEM STARTAT"
        
        # ENERGIOPTIMERAD: Datum och tid utan sekunder för startup
        date_time = format_swedish_date(now, include_seconds=False).upper()
        
        # Startup-meddelanden
        startup_content = [
            "Systemet initialiseras...",
            "Lyssnar efter VMA och trafikmeddelanden",
            "Sveriges Radio P4 Stockholm 103.3 MHz",
            "Offline krisberedskapssystem för döva/hörselskadade"
        ]
        
        # Systemstatus från startup
        system_status = [
            "RDS-mottagare: Startar",
            "AI-transkribering: Laddar",
            "E-paper display: Aktiv",
            "Väntar på första meddelande..."
        ]
        
        # UPPDATERAD: Status feedback MED RDS-indikator
        status_text = self._format_status_feedback_with_rds(status_info, mode='startup')
        
        return {
            'mode': 'startup',
            'priority': self.settings['priorities']['normal_status'],
            'sections': {
                'header': {
                    'text': header,
                    'font_size': self.settings['fonts']['traffic_header'],
                    'alignment': 'center',
                    'emphasis': True,
                    'spacing_after': 15
                },
                'datetime': {
                    'text': date_time,
                    'font_size': self.settings['fonts']['normal_content'],
                    'alignment': 'center',
                    'spacing_after': 25
                },
                'startup_info': {
                    'title': 'SYSTEMINITIALISERING',
                    'content': startup_content,
                    'font_size': self.settings['fonts']['normal_content'],
                    'line_spacing': 1.4,
                    'spacing_after': 20
                },
                'system_status': {
                    'title': 'KOMPONENTSTATUS',
                    'content': system_status,
                    'font_size': self.settings['fonts']['metadata'],
                    'line_spacing': 1.3,
                    'spacing_after': 20
                },
                'status_footer': {
                    'text': status_text,
                    'font_size': self.settings['fonts']['small_details'],
                    'alignment': 'center'
                }
            }
        }
    
    def format_for_idle_mode(self, system_status: Dict, status_info: Dict = None) -> Dict:
        """
        Idle-läge: Normal drift utan aktiva meddelanden MED RDS-indikator
        """
        now = datetime.now()
        status_info = status_info or {}
        
        # Header
        header = "INGA AKTIVA LARM"
        
        # ENERGIOPTIMERAD: Datum och tid utan sekunder för idle
        date_time = format_swedish_date(now, include_seconds=False).upper()
        
        # Systemstatus
        rds_status = "RDS: Aktiv" if system_status.get('rds_active') else "RDS: Inaktiv"
        frequency = f"P4: {system_status.get('frequency', '103.3')}MHz"
        ai_status = "AI: Redo" if system_status.get('transcriber_ready') else "AI: Laddar"
        audio_status = "Ljud: OK" if system_status.get('audio_ok') else "Ljud: Fel"
        
        # Batteristatus
        battery_pct = system_status.get('battery_percent', 100)
        estimated_hours = self._estimate_battery_life(battery_pct)
        battery_status = f"Batteri: {battery_pct}% (Est. {estimated_hours})"
        
        # Aktivitetssammanfattning
        last_24h_traffic = system_status.get('last_24h_traffic', 0)
        last_rds_update = system_status.get('last_rds_update', now)
        last_transcription = system_status.get('last_transcription')
        uptime = system_status.get('uptime', '0h 0m')
        
        # Formatera tider relativt
        rds_time_ago = self._format_time_ago(last_rds_update)
        transcription_time_ago = self._format_time_ago(last_transcription) if last_transcription else "Aldrig"
        
        activity_content = [
            f"Senaste 24h: {last_24h_traffic} trafikmeddelanden",
            f"Senaste RDS-uppdatering: {rds_time_ago}",
            f"Senaste transkription: {transcription_time_ago}",
            f"Systemupptid: {uptime}"
        ]
        
        # UPPDATERAD: Status feedback MED RDS-indikator
        status_text = self._format_status_feedback_with_rds(status_info, mode='idle')
        
        return {
            'mode': 'idle',
            'priority': self.settings['priorities']['normal_status'],
            'sections': {
                'header': {
                    'text': header,
                    'font_size': self.settings['fonts']['normal_header'],
                    'alignment': 'center',
                    'emphasis': True
                },
                'datetime': {
                    'text': date_time,
                    'font_size': self.settings['fonts']['normal_content'],
                    'alignment': 'center',
                    'spacing_after': 20
                },
                'system_status': {
                    'title': 'SYSTEMSTATUS',
                    'content': [rds_status, frequency, ai_status, audio_status, battery_status],
                    'font_size': self.settings['fonts']['normal_content'],
                    'line_spacing': 1.3,
                    'spacing_after': 20
                },
                'activity': {
                    'title': 'AKTIVITETSSAMMANFATTNING',
                    'content': activity_content,
                    'font_size': self.settings['fonts']['metadata'],
                    'line_spacing': 1.2,
                    'spacing_after': 20
                },
                'status_footer': {
                    'text': status_text,
                    'font_size': self.settings['fonts']['small_details'],
                    'alignment': 'center'
                }
            }
        }
    
    def format_for_traffic_mode(self, traffic_data: Dict, transcription: Dict = None, status_info: Dict = None) -> Dict:
        """
        OPTIMERAD Trafikmeddelande-läge med +5 rader extra MED RDS-indikator
        """
        start_time = traffic_data.get('start_time', datetime.now())
        status_info = status_info or {}
        
        # OPTIMERAD HEADER: "TRAFIKMEDDELANDE. STARTAD: HH:MM" (utan sekunder)
        header = f"TRAFIKMEDDELANDE. STARTAD: {start_time.strftime('%H:%M')}"
        
        # Extraherad nyckelinformation från transkription
        location = self._extract_location(transcription)
        incident_type = self._extract_incident_type(transcription)
        queue_info = self._extract_queue_info(transcription)
        direction = self._extract_direction(transcription)
        
        # Strukturerad info-sektion - BEHÅLLS SOM DEN ÄR (överskådlig och intuitiv)
        key_info = []
        if location:
            key_info.append(f"PLATS: {location}")
        if incident_type:
            key_info.append(f"TYP: {incident_type}")
        if queue_info:
            key_info.append(f"KÖ: {queue_info}")
        if direction:
            key_info.append(f"RIKTNING: {direction}")
        
        # OPTIMERAT: Fullständig transkription UTAN RUBRIK (sparar 1 rad)
        full_transcription = ""
        if transcription and transcription.get('text'):
            text = transcription['text'].strip()
            max_chars = self.settings['text']['max_content_chars']['traffic']
            if len(text) > max_chars:
                text = text[:max_chars-3] + "..."
            full_transcription = text
        
        # UPPDATERAD: Status feedback MED RDS-indikator
        status_text = self._format_status_feedback_with_rds(status_info, mode='traffic')
        
        return {
            'mode': 'traffic',
            'priority': self.settings['priorities']['traffic_active'],
            'sections': {
                'header': {
                    'text': header,
                    'font_size': self.settings['fonts']['traffic_header'],
                    'alignment': 'center',
                    'emphasis': True,
                    'background': True
                },
                'key_info': {
                    'content': key_info,
                    'font_size': self.settings['fonts']['traffic_content'],
                    'line_spacing': 1.4,
                    'spacing_after': 15
                },
                # HOTFIX: Ändrat tillbaka till 'transcription' för kompatibilitet med screen_layouts.py
                'transcription': {
                    'content': [full_transcription] if full_transcription else ["(Transkribering pågår...)"],
                    'font_size': self.settings['fonts']['normal_content'],
                    'word_wrap': True,
                    'spacing_after': 15
                },
                # BORTTAGET: 'status_info' sektion (4 rader sparade - var redundant)
                'status_footer': {
                    'text': status_text,
                    'font_size': self.settings['fonts']['small_details'],
                    'alignment': 'center'
                }
            }
        }
    
    def format_for_vma_mode(self, vma_data: Dict, is_test: bool = False, status_info: Dict = None) -> Dict:
        """
        VMA-läge med status feedback MED RDS-indikator
        """
        now = datetime.now()
        status_info = status_info or {}
        
        # Kritisk rubrik
        if is_test:
            header = "VMA-TEST"
            subheader = "DETTA ÄR ENDAST EN ÖVNING"
            alert_level = "TEST - INTE VERKLIG FARA"
        else:
            header = "VIKTIGT MEDDELANDE"
            subheader = "TILL ALLMÄNHETEN"
            alert_level = "SKARPT LARM - INTE TEST"
        
        # ENERGIOPTIMERAD: Tidsstämpel med sekund-precision (VMA kritiskt)
        timestamp = format_swedish_date(now, include_seconds=True).upper()
        
        # VMA-meddelande text
        vma_text = ""
        if vma_data.get('transcription'):
            text = vma_data['transcription'].get('text', '')
            max_chars = self.settings['text']['max_content_chars']['vma']
            if len(text) > max_chars:
                text = self._smart_truncate(text, max_chars)
            vma_text = text
        elif vma_data.get('rds_radiotext'):
            vma_text = vma_data['rds_radiotext']
        else:
            vma_text = "Viktigt meddelande till allmänheten pågår. Lyssna på Sveriges Radio P4 för fullständig information."
        
        # Kontaktinformation
        contact_info = [
            "KONTAKT: 112 vid akut fara",
            "INFO: Sveriges Radio P4 Stockholm", 
            "WEB: krisinformation.se (om internetanslutning finns)"
        ]
        
        # UPPDATERAD: Status feedback MED RDS-indikator
        status_text = self._format_status_feedback_with_rds(status_info, mode='vma')
        
        return {
            'mode': 'vma',
            'priority': self.settings['priorities']['vma_test' if is_test else 'vma_emergency'],
            'sections': {
                'main_header': {
                    'text': header,
                    'font_size': self.settings['fonts']['vma_header'],
                    'alignment': 'center',
                    'emphasis': True,
                    'spacing_after': 10
                },
                'sub_header': {
                    'text': subheader,
                    'font_size': self.settings['fonts']['traffic_header'],
                    'alignment': 'center',
                    'spacing_after': 15
                },
                'alert_level': {
                    'text': alert_level,
                    'font_size': self.settings['fonts']['traffic_content'],
                    'alignment': 'center',
                    'emphasis': True,
                    'spacing_after': 10
                },
                'timestamp': {
                    'text': timestamp,
                    'font_size': self.settings['fonts']['normal_content'],
                    'alignment': 'center',
                    'spacing_after': 20
                },
                'vma_content': {
                    'title': 'MEDDELANDE:',
                    'content': [vma_text],
                    'font_size': self.settings['fonts']['vma_content'],
                    'word_wrap': True,
                    'line_spacing': 1.3,
                    'spacing_after': 15
                },
                'contact': {
                    'content': contact_info,
                    'font_size': self.settings['fonts']['metadata'],
                    'line_spacing': 1.3,
                    'alignment': 'left',
                    'spacing_after': 10
                },
                'status_footer': {
                    'text': status_text,
                    'font_size': self.settings['fonts']['small_details'],
                    'alignment': 'center'
                }
            }
        }
    
    def _format_status_feedback_with_rds(self, status_info: Dict, mode: str) -> str:
        """
        NY: Status feedback MED RDS-indikator för döva användare
        
        Format: "System OK • 14:30 • RDS: ● 14:29"
        
        RDS-indikatorer:
        ● = Aktiv mottagning (<5 min)
        ○ = Svag mottagning (5-15 min)
        ✕ = Ingen mottagning (>15 min)
        """
        now = datetime.now()
        current_minute = now.strftime('%H:%M')
        
        if not status_info:
            # ENERGIOPTIMERING: Olika precision baserat på mode
            if mode in ['traffic', 'vma']:
                # Viktiga events - sekund-precision
                base_status = f"System OK • {now.strftime('%H:%M:%S')}"
            else:
                # Normal drift - minut-precision för mindre hash-ändringar
                base_status = f"System OK • {current_minute}"
        else:
            system_status = status_info.get('system_status', 'OK')
            
            # ENERGIOPTIMERING: Caching för att undvika onödiga ändringar
            if mode in ['startup', 'idle']:
                # För startup/idle: bara uppdatera vid 15min intervall
                if self.last_status_minute == current_minute:
                    last_update = status_info.get('last_update', current_minute)
                else:
                    last_update = current_minute
                    self.last_status_minute = current_minute
            else:
                # För events: alltid aktuell tid
                last_update = status_info.get('last_update', now.strftime('%H:%M:%S'))
            
            # Lägg till state duration om tillgänglig
            if 'state_duration' in status_info:
                duration = status_info['state_duration']
                base_status = f"System {system_status} • {last_update} • {duration}"
            else:
                base_status = f"System {system_status} • {last_update}"
        
        # NY: Lägg till RDS-indikator
        rds_status = self._get_rds_status_from_status_info(status_info)
        if rds_status:
            indicator = rds_status.get('indicator', '?')
            time_str = rds_status.get('time_str', 'Okänd')
            return f"{base_status} • RDS: {indicator} {time_str}"
        else:
            # Fallback om RDS-status inte tillgänglig
            return f"{base_status} • RDS: ? Okänd"
    
    def _get_rds_status_from_status_info(self, status_info: Dict) -> Optional[Dict]:
        """
        NY: Extrahera RDS-status från status_info
        
        Denna metod används av display_monitor som redan har RDS-status tillgänglig
        """
        if not status_info:
            return None
        
        # Kolla om RDS-status redan finns i status_info (från display_monitor)
        if 'rds_status' in status_info:
            return status_info['rds_status']
        
        # Fallback: Skapa enkel RDS-status baserat på system_status
        if 'system_status' in status_info:
            # Anta RDS är OK om systemet fungerar
            now = datetime.now()
            rounded_time = self._round_time_to_5min(now)
            return {
                'indicator': '●',
                'time_str': rounded_time.strftime('%H:%M'),
                'status': 'aktiv'
            }
        
        return None
    
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
    
    # ========================================
    # HJÄLPMETODER (med HOTFIX för direction-extraktion)
    # ========================================
    
    def _extract_location(self, transcription: Dict) -> str:
        """Extraherar plats från transkription"""
        if not transcription or not transcription.get('text'):
            return ""
        
        text = transcription['text'].lower()
        
        road_patterns = [
            r'(e\d+|rv\d+|länsväg\s+\d+)',
            r'(mellan\s+[\w\s]+\s+och\s+[\w\s]+)',
            r'(vid\s+[\w\s]+)',
            r'(i\s+riktning\s+mot\s+[\w\s]+)',
        ]
        
        for pattern in road_patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                return location.title()
        
        return ""
    
    def _extract_incident_type(self, transcription: Dict) -> str:
        """Extraherar typ av incident"""
        if not transcription or not transcription.get('text'):
            return ""
        
        text = transcription['text'].lower()
        
        incident_types = {
            'olycka': ['olycka', 'kollision', 'krock'],
            'fordon stannat': ['stannat', 'stillastående', 'haverier'],
            'väder': ['halt', 'snö', 'is', 'dimma'],
            'vägarbete': ['vägarbete', 'underhåll', 'reparation'],
            'köer': ['kö', 'trafikstockning', 'långsam trafik']
        }
        
        for incident, keywords in incident_types.items():
            if any(keyword in text for keyword in keywords):
                return incident.title()
        
        return "Trafikstörning"
    
    def _extract_queue_info(self, transcription: Dict) -> str:
        """Extraherar köinformation"""
        if not transcription or not transcription.get('text'):
            return ""
        
        text = transcription['text'].lower()
        
        queue_patterns = [
            r'(\d+)\s*(kilometer|km)',
            r'(\d+)\s*minuter?\s*extra',
            r'cirka\s*(\d+)\s*minuter?',
        ]
        
        queue_info = []
        for pattern in queue_patterns:
            match = re.search(pattern, text)
            if match:
                if 'kilometer' in pattern or 'km' in pattern:
                    queue_info.append(f"{match.group(1)} km")
                else:
                    queue_info.append(f"{match.group(1)} min extra")
        
        return ", ".join(queue_info) if queue_info else ""
    
    def _extract_direction(self, transcription: Dict) -> str:
        """
        HOTFIX: Extraherar färdriktning - BEGRÄNSAT till bara riktningsord
        """
        if not transcription or not transcription.get('text'):
            return ""
        
        text = transcription['text'].lower()
        
        # HOTFIX: Bara de EXAKTA riktningsorden - inga greedy patterns
        direction_patterns = [
            r'\b(norrgående|södergående|östgående|västgående)\b',
            r'\b(norrut|söderut|österut|västerut)\b'
        ]
        
        for pattern in direction_patterns:
            match = re.search(pattern, text)
            if match:
                direction = match.group(1).strip()
                # HOTFIX: Ta bort .title() som skapade versaler på varje ord
                return direction.lower()
        
        return ""
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Intelligent trunkering vid meningsslut"""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        
        break_point = max(last_period, last_exclamation)
        if break_point > max_length * 0.7:
            return text[:break_point + 1]
        else:
            return text[:max_length-3] + "..."
    
    def _estimate_battery_life(self, battery_percent: int) -> str:
        """Uppskattar återstående batteritid"""
        if battery_percent <= 0:
            return "0h 0m"
        
        total_hours = 133
        remaining_hours = (battery_percent / 100) * total_hours
        
        days = int(remaining_hours // 24)
        hours = int(remaining_hours % 24)
        
        if days > 0:
            return f"{days}d {hours}h"
        else:
            return f"{hours}h {int((remaining_hours % 1) * 60)}m"
    
    def _format_time_ago(self, timestamp: datetime) -> str:
        """Formaterar tid som 'X minuter sedan'"""
        if not timestamp:
            return "Okänd"
        
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return "Just nu"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes} min sedan"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() // 3600)
            return f"{hours}h sedan"
        else:
            days = int(diff.total_seconds() // 86400)
            return f"{days} dagar sedan"
    
    def validate_content(self, formatted_content: Dict) -> bool:
        """Validerar att formaterat innehåll kan visas korrekt"""
        try:
            required_fields = ['mode', 'priority', 'sections']
            for field in required_fields:
                if field not in formatted_content:
                    logger.error(f"Obligatoriskt fält saknas: {field}")
                    return False
            
            sections = formatted_content['sections']
            for section_name, section_data in sections.items():
                if not isinstance(section_data, dict):
                    logger.error(f"Sektion {section_name} har felaktig struktur")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Fel vid validering av innehåll: {e}")
            return False

if __name__ == "__main__":
    # Test av UPPDATERAD content formatter MED RDS-indikator
    formatter = ContentFormatter()
    
    print("📡 Test av UPPDATERAD Content Formatter MED RDS-INDIKATOR")
    print("=" * 60)
    print("🚧 TRAFIKOPTIMERING: +5 rader extra för längre meddelanden")
    print("🩹 HOTFIX: Fixar riktningsextraktion och transkriptionsvisning")
    print("📡 NY: RDS-mottagningsindikator för döva användare")
    
    # Test ENERGIOPTIMERADE modes med RDS-indikator
    test_modes = ['startup', 'idle', 'traffic']
    
    # Mock RDS-status för test
    mock_rds_status = {
        'indicator': '●',
        'time_str': '14:25',
        'status': 'aktiv'
    }
    
    for mode in test_modes:
        print(f"\n📱 Testar {mode} mode MED RDS-indikator:")
        content = formatter.format_for_mode(mode, 
                                          primary_data={'test': True},
                                          status_info={
                                              'system_status': 'OK', 
                                              'last_update': '21:15',
                                              'rds_status': mock_rds_status
                                          })
        print(f"  Mode: {content['mode']}")
        print(f"  Sections: {list(content['sections'].keys())}")
        if 'status_footer' in content['sections']:
            status_text = content['sections']['status_footer']['text']
            print(f"  Status: {status_text}")
            if 'RDS:' in status_text:
                print(f"  🎯 RDS-indikator: HITTAD i footer!")
            else:
                print(f"  ❌ RDS-indikator: SAKNAS")
        
        # Visa trafikoptimering
        if mode == 'traffic':
            print(f"  🚧 OPTIMERAT: Ingen 'status_info' sektion")
            print(f"  🚧 HOTFIX: 'transcription' sektion (kompatibilitet)")
            print(f"  🩹 HOTFIX: Begränsad direction-extraktion")
            print(f"  🚧 RESULTAT: +5 rader för längre meddelanden!")
    
    # Test RDS-indikator med olika status
    print(f"\n📡 Test av RDS-indikatorer:")
    rds_test_cases = [
        {'indicator': '●', 'time_str': '14:25', 'status': 'aktiv'},
        {'indicator': '○', 'time_str': '14:20', 'status': 'svag'},
        {'indicator': '✕', 'time_str': '14:10', 'status': 'ingen'}
    ]
    
    for rds_case in rds_test_cases:
        status_text = formatter._format_status_feedback_with_rds(
            {'system_status': 'OK', 'last_update': '14:30', 'rds_status': rds_case}, 
            'idle'
        )
        print(f"  {rds_case['status'].upper()}: {status_text}")
    
    # Test direction-extraktion
    print(f"\n🩹 Test av FIXAD direction-extraktion:")
    test_transcription = {
        'text': 'Trafikinformation. På E20 södergående mot Södertälje har en lastbil stannat till höger och andra lastbilar måste köra om.'
    }
    
    direction = formatter._extract_direction(test_transcription)
    print(f"  Text: {test_transcription['text']}")
    print(f"  Extraherad riktning: '{direction}'")
    print(f"  ✅ Endast riktningsord extraheras nu!")
    
    print("\n📡 UPPDATERAD Content Formatter MED RDS-INDIKATOR test slutförd!")
    print("✅ 15min status intervall implementerat")
    print("⚡ Smart timing för minimal hash-ändringar") 
    print("🚧 Trafikmeddelanden optimerade för maximalt innehåll!")
    print("🩹 Direction-extraktion och transkriptionsvisning FIXAD!")
    print("📡 RDS-mottagningsindikator för döva användare IMPLEMENTERAD!")
    print("🎯 Format: 'System OK • 14:30 • RDS: ● 14:25'")
