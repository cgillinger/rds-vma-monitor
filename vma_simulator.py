#!/usr/bin/env python3
"""
VMA Simulator - Isolerad version som inte förorenar systemloggar
Fil: vma_simulator.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/vma_simulator.py

FÖRBÄTTRINGAR:
- Separata kataloger för simulator-data
- Tydliga prefix för alla simulator-filer  
- RDS-pipe prioritet (inget logg-skapande om system aktivt)
- Auto-cleanup efter test
- Ingen förorening av huvudapplikationens loggar

BASERAT PÅ DOKUMENTATION:
- PTY 30 = VMA Test, PTY 31 = Skarpt VMA
- TA=1 vid start, TA=0 vid slut
- RT börjar med "VMA. Viktigt meddelande till allmänheten..."
"""

import os
import sys
import json
import time
import threading
import atexit
from datetime import datetime, timedelta
from pathlib import Path

# ========================================
# VMA SCENARIOS BASERADE PÅ DOKUMENTATION
# ========================================

VMA_SCENARIOS = {
    'test_short': {
        'type': 'vma_test',
        'pty_code': 30,
        'duration': 8,  # Under 10s filter - ska filtreras
        'radiotext': 'VMA. Detta är ett test av varningssystemet. Test avslutat.',
        'description': 'Kort VMA-test (under 10s filter)'
    },
    
    'test_normal': {
        'type': 'vma_test', 
        'pty_code': 30,
        'duration': 25,
        'radiotext': 'VMA. Viktigt meddelande till allmänheten. Detta är ett test av det svenska varningssystemet. Testet pågår nu. Inget åtgärd krävs. Test avslutat.',
        'description': 'Normal VMA-test (kvartalstest)'
    },
    
    'emergency_nuclear': {
        'type': 'vma_emergency',
        'pty_code': 31,
        'duration': 60,
        'radiotext': 'VMA. Viktigt meddelande till allmänheten. Olycka vid kärnkraftverk. Håll er inomhus. Stäng dörrar och fönster. Lyssna på Sveriges Radio för uppdateringar.',
        'description': 'Kärnkraftsolycka (skarpt VMA)'
    },
    
    'emergency_war': {
        'type': 'vma_emergency',
        'pty_code': 31,
        'duration': 45,
        'radiotext': 'VMA. Viktigt meddelande till allmänheten. Militär aktivitet upptäckt. Sök skydd inomhus omedelbart. Följ myndigheternas anvisningar.',
        'description': 'Militärt hot (skarpt VMA)'
    },
    
    'emergency_evacuation': {
        'type': 'vma_emergency',
        'pty_code': 31,
        'duration': 75,
        'radiotext': 'VMA. Viktigt meddelande till allmänheten. Evakuering påbörjad i följande områden. Lämna området enligt myndigheternas anvisningar. Tag med nödvändigheter.',
        'description': 'Evakuering (långt skarpt VMA)'
    },
    
    'faran_over': {
        'type': 'vma_emergency',
        'pty_code': 31,
        'duration': 20,
        'radiotext': 'VMA. Viktigt meddelande till allmänheten. Faran över. Tidigare utfärdat varningsmeddelande upphävs. Normala aktiviteter kan återupptas.',
        'description': 'Faran över-meddelande'
    }
}

# ========================================
# ISOLERAD VMA SIMULATOR CLASS
# ========================================

class IsolatedVMASimulator:
    """
    VMA-simulator som inte förorenar huvudapplikationens loggar
    """
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path(__file__).parent
        self.logs_dir = self.project_dir / "logs"
        
        # ISOLERAD: Separata kataloger för simulator
        self.simulator_dir = self.logs_dir / "simulator"
        self.simulator_dir.mkdir(parents=True, exist_ok=True)
        
        self.rds_pipe = "/tmp/vma_rds_data"
        
        # ISOLERAT: Spåra skapade filer för cleanup
        self.created_files = []
        
        # ISOLERAT: Registrera cleanup vid exit
        atexit.register(self._cleanup_on_exit)
        
        # Kontrollera att system är aktivt
        self.system_active = self._check_system_active()
        
        print("🧪 VMA Simulator - ISOLERAD VERSION (förorenar ej systemloggar)")
        print("=" * 70)
        print(f"System status: {'✅ Aktivt' if self.system_active else '❌ Inaktivt'}")
        print(f"Simulator-katalog: {self.simulator_dir}")
        print(f"Test-strategi: {'RDS-injection' if self.system_active else 'Isolerade demo-loggar'}")
        
    def _check_system_active(self) -> bool:
        """Kontrollera att VMA-systemet körs"""
        return os.path.exists(self.rds_pipe)
    
    def simulate_scenario(self, scenario_name: str):
        """Simulera specifikt VMA-scenario - ISOLERAT"""
        if scenario_name not in VMA_SCENARIOS:
            print(f"❌ Okänt scenario: {scenario_name}")
            print(f"Tillgängliga: {list(VMA_SCENARIOS.keys())}")
            return
        
        scenario = VMA_SCENARIOS[scenario_name]
        print(f"\n🎯 Simulerar: {scenario['description']}")
        print(f"📡 PTY: {scenario['pty_code']} ({'Test' if scenario['pty_code'] == 30 else 'Skarpt'})")
        print(f"⏱️ Längd: {scenario['duration']} sekunder")
        print(f"📝 Text: {scenario['radiotext'][:50]}...")
        
        if self.system_active:
            print("🔄 System aktivt - använder RDS-injection (inga loggfiler)")
            self._send_rds_injection_sequence(scenario)
        else:
            print("📁 System inaktivt - skapar ISOLERADE demo-loggar")
            self._create_isolated_demo_logs(scenario)
    
    def _send_rds_injection_sequence(self, scenario: dict):
        """PRIORITERAT: RDS-injection för aktivt system (ingen loggförorening)"""
        try:
            print("\n📡 Skickar RDS-sekvens direkt till systemet...")
            
            # 1. VMA START - PTY ändras + TA=1
            vma_start_rds = {
                'pi': '2001',  # P4 Stockholm PI
                'ps': 'P4STHLM',
                'pty': scenario['pty_code'],  # 30 eller 31
                'prog_type': 'Alarm' if scenario['pty_code'] == 31 else 'Test',
                'ta': True,  # VMA använder TA också
                'tp': True,
                'rt': scenario['radiotext'],
                'timestamp': datetime.now().isoformat(),
                'ews': False  # Sverige använder PTY, inte EWS
            }
            
            # Skicka start-signal
            with open(self.rds_pipe, 'w') as pipe:
                pipe.write(json.dumps(vma_start_rds) + '\n')
                pipe.flush()
            
            print(f"✅ VMA START injicerad - PTY {scenario['pty_code']}, TA=1")
            
            # 2. Håll VMA aktivt under duration
            start_time = time.time()
            duration = scenario['duration']
            
            # Skicka uppdateringar var 3:e sekund för att hålla RDS-stream levande
            while time.time() - start_time < duration:
                # Kontinuerliga RDS-uppdateringar under VMA
                current_rds = vma_start_rds.copy()
                current_rds['timestamp'] = datetime.now().isoformat()
                
                with open(self.rds_pipe, 'w') as pipe:
                    pipe.write(json.dumps(current_rds) + '\n')
                    pipe.flush()
                
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                print(f"🔄 VMA pågår... {elapsed}/{duration}s (⏱️ {remaining}s kvar)", end='\r')
                time.sleep(3)
            
            print(f"\n⏱️ VMA varade {duration} sekunder")
            
            # 3. VMA END - PTY tillbaka till normal + TA=0
            vma_end_rds = {
                'pi': '2001',
                'ps': 'P4STHLM',
                'pty': 3,  # Tillbaka till "Information/Nyheter"
                'prog_type': 'Information',
                'ta': False,  # TA av
                'tp': True,
                'rt': 'P4 Stockholm - Sveriges Radio',  # Normal radiotext
                'timestamp': datetime.now().isoformat(),
                'ews': False
            }
            
            with open(self.rds_pipe, 'w') as pipe:
                pipe.write(json.dumps(vma_end_rds) + '\n')
                pipe.flush()
            
            print("✅ VMA END injicerad - PTY återställd, TA=0")
            print("🎯 RDS-injection komplett!")
            
            # Vänta lite för att se systemreaktionen
            print("\n⏱️ Väntar 5 sekunder för att se systemreaktion...")
            time.sleep(5)
            self._show_system_reaction()
            
        except Exception as e:
            print(f"❌ Fel vid RDS-injection: {e}")
            print("🔄 Försöker med isolerade demo-loggar istället...")
            self._create_isolated_demo_logs(scenario)
    
    def _create_isolated_demo_logs(self, scenario: dict):
        """ISOLERAT: Skapa demo-loggar som inte förorenar systemet"""
        try:
            print("\n📁 Skapar ISOLERADE demo-loggar...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # ISOLERAT: Använd simulator-katalog och tydliga prefix
            start_event_file = self.simulator_dir / f"sim_vma_{scenario['type']}_start_{timestamp}.log"
            
            rds_data_start = {
                'pty': scenario['pty_code'],
                'ta': True,
                'rt': scenario['radiotext'],
                'prog_type': 'Alarm' if scenario['pty_code'] == 31 else 'Test',
                'simulator': True  # ISOLERAT: Märk som simulator-data
            }
            
            start_content = f"""# SIMULATOR EVENT: {scenario['type']}_start
# ISOLERAT - Förorenar ej systemloggar
# Start time: {datetime.now().isoformat()}
# Trigger: pty_{scenario['pty_code']}_activated
# RDS at start: {json.dumps(rds_data_start, default=str)}
===============================================
{{"timestamp": "{datetime.now().isoformat()}", "rds": {json.dumps(rds_data_start, default=str)}, "simulator": true}}
"""
            
            with open(start_event_file, 'w') as f:
                f.write(start_content)
            
            # ISOLERAT: Spåra skapad fil för cleanup
            self.created_files.append(start_event_file)
            
            print(f"📁 Simulator start-logg: {start_event_file.name}")
            
            # 2. Visa progress under duration
            duration = scenario['duration']
            print(f"⏱️ Simulerar {duration} sekunder VMA...")
            
            for i in range(duration):
                remaining = duration - i - 1
                print(f"🔄 Demo VMA pågår... {i+1}/{duration}s (⏱️ {remaining}s kvar)", end='\r')
                time.sleep(1)
            
            # 3. Skapa end event-logg
            end_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            end_event_file = self.simulator_dir / f"sim_vma_{scenario['type']}_end_{end_timestamp}.log"
            
            rds_data_end = {
                'pty': 3,
                'ta': False,
                'rt': 'P4 Stockholm',
                'simulator': True  # ISOLERAT: Märk som simulator-data
            }
            
            end_content = f"""# SIMULATOR EVENT: {scenario['type']}_end
# ISOLERAT - Förorenar ej systemloggar
# End time: {datetime.now().isoformat()}
# End trigger: pty_{scenario['pty_code']}_deactivated
# Duration: {duration} seconds
===============================================
{{"timestamp": "{datetime.now().isoformat()}", "rds": {json.dumps(rds_data_end, default=str)}, "simulator": true}}
"""
            
            with open(end_event_file, 'w') as f:
                f.write(end_content)
            
            # ISOLERAT: Spåra skapad fil för cleanup
            self.created_files.append(end_event_file)
            
            print(f"\n📁 Simulator end-logg: {end_event_file.name}")
            print("✅ ISOLERADE demo-loggar skapade!")
            print("ℹ️ Dessa loggar förorenar INTE systemet - de ligger i simulator-katalog")
            
        except Exception as e:
            print(f"❌ Fel vid skapande av isolerade demo-loggar: {e}")
    
    def _show_system_reaction(self):
        """Visa systemreaktion efter RDS-injection"""
        try:
            # Kontrollera senaste systemloggar
            today = datetime.now().strftime("%Y%m%d")
            system_log = self.logs_dir / f"system_{today}.log"
            
            if system_log.exists():
                print("\n📊 SENASTE SYSTEMREAKTION:")
                print("-" * 30)
                
                # Visa senaste 10 raderna från systemloggen
                with open(system_log, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:] if len(lines) >= 10 else lines
                    
                    for line in recent_lines:
                        if any(keyword in line.lower() for keyword in ['vma', 'pty', 'alarm', 'test']):
                            print(f"🔍 {line.strip()}")
                
                # Kontrollera audio-filer
                audio_dir = self.logs_dir / "audio"
                if audio_dir.exists():
                    recent_audio = sorted(audio_dir.glob("*.wav"), key=lambda f: f.stat().st_mtime)
                    if recent_audio:
                        latest_audio = recent_audio[-1]
                        file_age = time.time() - latest_audio.stat().st_mtime
                        if file_age < 120:  # Yngre än 2 minuter
                            print(f"🎤 Audio-fil skapad: {latest_audio.name}")
                
                # Kontrollera display-uppdateringar
                screen_dir = self.logs_dir / "screen"
                if screen_dir.exists():
                    recent_screens = sorted(screen_dir.glob("*.png"), key=lambda f: f.stat().st_mtime)
                    if recent_screens:
                        latest_screen = recent_screens[-1]
                        file_age = time.time() - latest_screen.stat().st_mtime
                        if file_age < 120:  # Yngre än 2 minuter
                            print(f"🖥️ Display uppdaterad: {latest_screen.name}")
            else:
                print("ℹ️ Ingen systemlogg funnen för idag")
                
        except Exception as e:
            print(f"⚠️ Kunde inte visa systemreaktion: {e}")
    
    def list_scenarios(self):
        """Lista alla tillgängliga VMA-scenarios"""
        print("\n📋 TILLGÄNGLIGA VMA-SCENARIOS:")
        print("=" * 50)
        
        for name, scenario in VMA_SCENARIOS.items():
            pty = scenario['pty_code']
            duration = scenario['duration']
            desc = scenario['description']
            
            pty_text = "🟡 Test" if pty == 30 else "🔴 Skarpt"
            filter_text = "🗑️ Filtreras" if duration < 10 else "✅ Sparas"
            
            print(f"{name:20} | {pty_text} | {duration:2}s | {filter_text} | {desc}")
        
        print(f"\n💡 Simulator-strategi: {'RDS-injection' if self.system_active else 'Isolerade demo-loggar'}")
        print(f"📁 Simulator-katalog: {self.simulator_dir}")
    
    def test_vma_detection(self):
        """Testa VMA-detektion med olika scenarios - ISOLERAT"""
        print("\n🧪 TESTAR VMA-DETEKTION (ISOLERAT)...")
        print("=" * 50)
        
        if not self.system_active:
            print("⚠️ System inaktivt - kommer skapa isolerade demo-loggar endast")
        
        # Testa kort VMA (ska filtreras)
        print("1. Testar kort VMA (under 10s)...")
        self.simulate_scenario('test_short')
        time.sleep(3)
        
        # Testa normal VMA-test
        print("\n2. Testar normal VMA-test...")
        self.simulate_scenario('test_normal')
        time.sleep(3)
        
        # Testa skarpt VMA
        print("\n3. Testar skarpt VMA...")
        self.simulate_scenario('emergency_nuclear')
        
        print("\n✅ VMA-detektion test komplett!")
        print("🧹 Auto-cleanup kommer köras vid exit")
    
    def simulate_quarterly_test(self):
        """Simulera kvartalsvis VMA-test"""
        print("\n📅 SIMULERAR KVARTALSVIS VMA-TEST")
        print("=" * 40)
        print("Baserat på: Första måndagen i mars, juni, sep, dec kl 15:00")
        print("PTY 30 (Test) enligt Sveriges Radio dokumentation")
        
        self.simulate_scenario('test_normal')
    
    def cleanup_simulator_files(self):
        """ISOLERAT: Rensa alla simulator-filer"""
        cleaned_count = 0
        
        try:
            # Rensa spårade filer
            for file_path in self.created_files:
                if file_path.exists():
                    file_path.unlink()
                    cleaned_count += 1
            
            # Rensa hela simulator-katalogen
            if self.simulator_dir.exists():
                for sim_file in self.simulator_dir.glob("sim_*"):
                    sim_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} simulator-filer")
            else:
                print("✅ Inga simulator-filer att rensa")
                
        except Exception as e:
            print(f"⚠️ Fel vid cleanup: {e}")
    
    def _cleanup_on_exit(self):
        """AUTO-CLEANUP vid exit"""
        if self.created_files:
            print("\n🧹 Auto-cleanup av simulator-filer vid exit...")
            self.cleanup_simulator_files()

# ========================================
# COMMAND LINE INTERFACE - UPPDATERAT
# ========================================

def main():
    """Huvudfunktion med förbättrat kommandoradsgränssnitt"""
    simulator = IsolatedVMASimulator()
    
    if len(sys.argv) < 2:
        print("\n🎯 ANVÄNDNING:")
        print("=" * 30)
        print("python3 vma_simulator.py <kommando>")
        print("\nKOMMANDON:")
        print("  list                    - Lista alla scenarios")
        print("  test <scenario>         - Simulera specifikt scenario")
        print("  quarterly               - Simulera kvartalstest")
        print("  detection-test          - Testa hela VMA-detection")
        print("  cleanup                 - Rensa simulator-filer")
        print("")
        simulator.list_scenarios()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        simulator.list_scenarios()
        
    elif command == 'test' and len(sys.argv) > 2:
        scenario = sys.argv[2]
        simulator.simulate_scenario(scenario)
        
    elif command == 'quarterly':
        simulator.simulate_quarterly_test()
        
    elif command == 'detection-test':
        simulator.test_vma_detection()
        
    elif command == 'cleanup':
        simulator.cleanup_simulator_files()
        
    else:
        print(f"❌ Okänt kommando: {command}")
        print("Kör utan argument för hjälp")

if __name__ == "__main__":
    main()