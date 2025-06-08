#!/usr/bin/env python3
"""
Display Configuration - Energioptimerade inställningar för e-paper display
Designat för döva/hörselskadade med fokus på krisberedskap och låg energiförbrukning
"""

# E-paper hårdvarukonfiguration
DISPLAY_CONFIG = {
    'width': 800,
    'height': 480,
    'rotation': 0,  # 0, 90, 180, 270
    'color_mode': 'BW',  # Black & White för energieffektivitet
}

# Energioptimerade uppdateringsintervall (sekunder)
UPDATE_INTERVALS = {
    'vma_mode': 0,          # OMEDELBART - livsviktigt
    'vma_test_mode': 5,     # 5 sekunder för VMA-test
    'traffic_mode': 10,     # 10 sekunder under trafikmeddelanden
    'normal_mode': 600,     # 10 minuter för normal drift
    'night_mode': 1800,     # 30 minuter nattetid (23:00-06:00)
    'battery_save': 3600,   # 1 timme vid låg batterinivå (<20%)
}

# Display-timers och timeouts
DISPLAY_TIMERS = {
    'traffic_display_duration': 300,    # 5 minuter efter trafikmeddelande-slut
    'normal_return_delay': 30,          # 30 sekunder innan återgång till normalläge  
    'vma_minimum_duration': 60,         # VMA visas minst 1 minut
    'update_batch_delay': 30,           # Samla uppdateringar i 30 sekunder
    'partial_update_threshold': 0.3,    # Använd partiell uppdatering om <30% ändras
}

# Event-prioritering (högre nummer = högre prioritet)
EVENT_PRIORITIES = {
    'vma_emergency': 1000,     # Skarpt VMA (PTY 31)
    'vma_test': 800,           # VMA-test (PTY 30)  
    'system_error': 700,       # Kritiska systemfel
    'traffic_active': 600,     # Pågående trafikmeddelanden
    'traffic_recent': 400,     # Nyligen avslutade trafikmeddelanden
    'system_warning': 300,     # Systemvarningar
    'normal_status': 100,      # Normal systemstatus
    'decorative': 50,          # Statistik, extra info
}

# Font-storlekar och typografi (pixlar för 800×480 skärm)
FONT_SIZES = {
    'vma_header': 48,          # STORT för VMA-rubriker
    'vma_content': 24,         # VMA-meddelande text
    'traffic_header': 32,      # Trafikmeddelande-rubriker  
    'traffic_content': 20,     # Trafikinfo text
    'normal_header': 24,       # Normal läge rubriker
    'normal_content': 18,      # Normal text
    'metadata': 14,            # Tid, datum, systeminfo
    'small_details': 12,       # Mindre detaljer, fotnoter
}

# Layout-konfiguration för olika lägen
LAYOUT_CONFIG = {
    'normal_mode': {
        'status_area_height': 120,     # Övre statusområde
        'content_area_height': 280,    # Huvudinnehålls-område
        'footer_height': 80,           # Nedre systeminfo
        'margin': 20,                  # Marginaler runt text
        'line_spacing': 1.2,           # Radavstånd
    },
    'traffic_mode': {
        'header_height': 80,           # Traffic-rubrik
        'content_area_height': 320,    # Trafikinfo + transkription
        'footer_height': 80,           # Status + timing
        'margin': 15,
        'line_spacing': 1.1,
    },
    'vma_mode': {
        'header_height': 100,          # VMA-rubrik + varning
        'content_area_height': 340,    # VMA-meddelande (maximal yta)
        'footer_height': 40,           # Minimal footer
        'margin': 10,                  # Mindre marginaler för max text
        'line_spacing': 1.15,
    }
}

# Energisparsystem
BATTERY_CONFIG = {
    'low_battery_threshold': 20,       # % - aktivera energisparläge
    'critical_battery_threshold': 10,  # % - endast VMA-uppdateringar
    'night_start_hour': 23,            # Nattetid börjar
    'night_end_hour': 6,               # Nattetid slutar
    'max_daily_updates': 500,          # Begränsa uppdateringar per dag
    'emergency_update_reserve': 50,    # Reservera uppdateringar för VMA
}

# Textformatering och truncation
TEXT_CONFIG = {
    'max_content_chars': {
        'vma': 1000,           # VMA får använda all tillgänglig plats
        'traffic': 600,        # Trafikmeddelanden
        'normal': 400,         # Normal innehåll
    },
    'truncation_suffix': '...',
    'word_wrap': True,
    'auto_font_scaling': True,         # Minska font om text inte får plats
    'min_font_scale': 0.7,            # Minsta font-skalning (70%)
}

# Visuella designelement
VISUAL_CONFIG = {
    'header_separators': True,         # Linjer under rubriker
    'section_dividers': True,          # Avdelare mellan sektioner
    'status_icons': {
        'vma_emergency': '🚨',
        'vma_test': '🧪',  
        'traffic': '🚧',
        'system_ok': '🟢',
        'system_warning': '🟡',
        'system_error': '🔴',
        'battery_ok': '🔋',
        'battery_low': '🪫',
        'rds_active': '📡',
        'audio_ok': '🎧',
    },
    'emphasis_chars': {
        'critical_start': '>>> ',
        'critical_end': ' <<<',
        'important_bullet': '• ',
    }
}

# System-integration inställningar
INTEGRATION_CONFIG = {
    'rds_logger_integration': True,    # Integrera med befintlig rds_logger
    'transcriber_integration': True,   # Visa transkriptioner
    'cleanup_integration': True,       # Respektera cleanup-scheman
    'weather_integration': False,      # Väder-API (Fas 5)
    'web_integration': False,          # Webb-interface (framtida)
}

# Felsökning och diagnostik
DEBUG_CONFIG = {
    'log_all_updates': True,           # Logga alla display-uppdateringar
    'performance_monitoring': True,    # Mät uppdateringstider
    'energy_tracking': True,          # Spåra energiförbrukning
    'test_mode': False,               # Test-läge för utveckling
    'simulate_events': False,         # Simulera events för test
}

# Backup och återställning
BACKUP_CONFIG = {
    'save_last_display_state': True,  # Spara senaste visning
    'restore_on_startup': True,       # Återställ vid omstart
    'fallback_layouts': True,         # Fallback vid layoutfel
    'emergency_text_mode': True,      # Text-only vid display-fel
}

# Exportera huvudkonfiguration för enkel import
DISPLAY_SETTINGS = {
    **DISPLAY_CONFIG,
    'updates': UPDATE_INTERVALS,
    'timers': DISPLAY_TIMERS,
    'priorities': EVENT_PRIORITIES,
    'fonts': FONT_SIZES,
    'layouts': LAYOUT_CONFIG,
    'battery': BATTERY_CONFIG,
    'text': TEXT_CONFIG,
    'visual': VISUAL_CONFIG,
    'integration': INTEGRATION_CONFIG,
    'debug': DEBUG_CONFIG,
    'backup': BACKUP_CONFIG,
}

def get_update_interval(mode, battery_level=100, is_night=False):
    """
    Beräkna optimal uppdateringsintervall baserat på läge, batteri och tid
    """
    base_interval = UPDATE_INTERVALS.get(mode, UPDATE_INTERVALS['normal_mode'])
    
    # Energisparjusteringar
    if battery_level < BATTERY_CONFIG['critical_battery_threshold']:
        if mode not in ['vma_mode', 'vma_test_mode']:  # VMA får alltid uppdatering
            base_interval = UPDATE_INTERVALS['battery_save']
    elif battery_level < BATTERY_CONFIG['low_battery_threshold']:
        base_interval *= 2  # Dubbla intervallet vid låg batteri
    
    # Nattetid-justering
    if is_night and mode == 'normal_mode':
        base_interval = UPDATE_INTERVALS['night_mode']
    
    return base_interval

def get_font_size(content_type, content_length=0):
    """
    Beräkna optimal font-storlek baserat på innehållstyp och längd
    """
    base_size = FONT_SIZES.get(content_type, FONT_SIZES['normal_content'])
    
    # Automatisk skalning för långt innehåll
    if TEXT_CONFIG['auto_font_scaling'] and content_length > 0:
        max_chars = TEXT_CONFIG['max_content_chars'].get(
            content_type.split('_')[0], 400
        )
        if content_length > max_chars:
            scale = max(TEXT_CONFIG['min_font_scale'], 
                       max_chars / content_length)
            base_size = int(base_size * scale)
    
    return base_size

def is_night_time():
    """
    Kontrollera om det är nattetid för energisparläge
    """
    from datetime import datetime
    current_hour = datetime.now().hour
    start = BATTERY_CONFIG['night_start_hour'] 
    end = BATTERY_CONFIG['night_end_hour']
    
    if start > end:  # Nattetid går över midnatt
        return current_hour >= start or current_hour < end
    else:
        return start <= current_hour < end

if __name__ == "__main__":
    # Test-utskrift av konfiguration
    print("🖥️ E-Paper Display Configuration")
    print("=" * 40)
    print(f"Display: {DISPLAY_CONFIG['width']}×{DISPLAY_CONFIG['height']}")
    print(f"Normal uppdatering: {UPDATE_INTERVALS['normal_mode']} sekunder")
    print(f"VMA uppdatering: {UPDATE_INTERVALS['vma_mode']} sekunder")
    print(f"Font storlekar: {FONT_SIZES['vma_header']}px (VMA) → {FONT_SIZES['small_details']}px (detaljer)")
    print(f"Nattetid: {BATTERY_CONFIG['night_start_hour']}:00 - {BATTERY_CONFIG['night_end_hour']}:00")
    print(f"Energisparläge: <{BATTERY_CONFIG['low_battery_threshold']}% batteri")
    
    # Test energifunktioner
    print("\n🔋 Energitest:")
    print(f"Normal läge, 100% batteri: {get_update_interval('normal_mode', 100)} sek")
    print(f"Normal läge, 15% batteri: {get_update_interval('normal_mode', 15)} sek") 
    print(f"VMA läge, 5% batteri: {get_update_interval('vma_mode', 5)} sek")
    print(f"Nattetid: {'Ja' if is_night_time() else 'Nej'}")
