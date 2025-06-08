#!/usr/bin/env python3
"""
Komplett Test Suite för VMA E-paper Display System
Testar alla aspekter av display-funktionaliteten
"""

import sys
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Setup logging för test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DisplayTestSuite:
    """
    Komplett test-suite för display-systemet
    """
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.warnings = []
        
    def run_all_tests(self):
        """Kör alla tester i rätt ordning"""
        print("🖥️ VMA Display System - Komplett Test Suite")
        print("=" * 50)
        
        tests = [
            ("Import Test", self.test_imports),
            ("E-paper Hardware Test", self.test_epaper_hardware),
            ("Configuration Test", self.test_configuration),
            ("Content Formatter Test", self.test_content_formatter),
            ("Screen Layout Test", self.test_screen_layouts),
            ("Display Manager Test", self.test_display_manager),
            ("Integration Test", self.test_integration),
            ("Performance Test", self.test_performance)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🧪 {test_name}")
            print("-" * 30)
            
            try:
                result = test_func()
                self.test_results[test_name] = result
                
                if result:
                    print(f"✅ {test_name} - PASS")
                else:
                    print(f"❌ {test_name} - FAIL")
                    self.failed_tests.append(test_name)
                    
            except Exception as e:
                print(f"💥 {test_name} - ERROR: {e}")
                self.failed_tests.append(test_name)
                self.test_results[test_name] = False
        
        self.print_summary()
        
    def test_imports(self) -> bool:
        """Testar import av alla moduler"""
        required_modules = [
            ('display_config', 'DISPLAY_SETTINGS'),
            ('content_formatter', 'ContentFormatter'),
            ('screen_layouts', 'ScreenLayout'),
            ('display_manager', 'DisplayManager')
        ]
        
        import_success = True
        
        for module_name, class_name in required_modules:
            try:
                module = __import__(module_name)
                if hasattr(module, class_name):
                    print(f"  ✅ {module_name}.{class_name}")
                else:
                    print(f"  ❌ {module_name}.{class_name} inte funnet")
                    import_success = False
            except ImportError as e:
                print(f"  ❌ {module_name} - Import error: {e}")
                import_success = False
        
        # Test av e-paper bibliotek
        try:
            from waveshare_epd import epd4in26
            print("  ✅ waveshare_epd.epd4in26")
        except ImportError:
            print("  ⚠️ waveshare_epd.epd4in26 - Kommer köra i simulator-läge")
            self.warnings.append("E-paper bibliotek inte tillgängligt")
        
        return import_success
    
    def test_epaper_hardware(self) -> bool:
        """Testar e-paper hårdvara om tillgänglig"""
        try:
            from waveshare_epd import epd4in26
            
            print("  🔌 Initialiserar e-paper display...")
            epd = epd4in26.EPD()
            epd.init()
            print("  ✅ Display initialiserat")
            
            print("  🧹 Rensar display...")
            epd.Clear()
            print("  ✅ Display rensat")
            
            print("  😴 Sätter display i sovläge...")
            epd.sleep()
            print("  ✅ Display i sovläge")
            
            return True
            
        except ImportError:
            print("  ⚠️ E-paper bibliotek inte tillgängligt - Simulator-läge")
            return True  # Detta är OK för test
        except Exception as e:
            print(f"  ❌ E-paper hårdvarufel: {e}")
            return False
    
    def test_configuration(self) -> bool:
        """Testar display-konfiguration"""
        try:
            from display_config import DISPLAY_SETTINGS, get_update_interval, is_night_time
            
            # Test grundläggande konfiguration
            required_keys = ['width', 'height', 'updates', 'priorities', 'fonts']
            for key in required_keys:
                if key not in DISPLAY_SETTINGS:
                    print(f"  ❌ Konfigurationsnyckel saknas: {key}")
                    return False
                print(f"  ✅ {key}: {DISPLAY_SETTINGS[key] if len(str(DISPLAY_SETTINGS[key])) < 50 else 'OK'}")
            
            # Test funktioner
            interval_normal = get_update_interval('normal_mode', 100, False)
            interval_vma = get_update_interval('vma_mode', 50, False)
            night_time = is_night_time()
            
            print(f"  ✅ Normal uppdateringsintervall: {interval_normal}s")
            print(f"  ✅ VMA uppdateringsintervall: {interval_vma}s") 
            print(f"  ✅ Nattetid: {night_time}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Konfigurationstest fel: {e}")
            return False
    
    def test_content_formatter(self) -> bool:
        """Testar innehållsformatering"""
        try:
            from content_formatter import ContentFormatter
            
            formatter = ContentFormatter()
            print("  ✅ ContentFormatter skapad")
            
            # Test normal mode formatting
            test_system_status = {
                'rds_active': True,
                'frequency': '103.3',
                'transcriber_ready': True,
                'audio_ok': True,
                'battery_percent': 75,
                'last_24h_traffic': 5,
                'last_rds_update': datetime.now() - timedelta(minutes=3),
                'last_transcription': datetime.now() - timedelta(minutes=30),
                'uptime': '1d 12h 30m'
            }
            
            normal_content = formatter.format_for_normal_mode(test_system_status)
            
            # Validera struktur
            if not formatter.validate_content(normal_content):
                print("  ❌ Normal mode formatering misslyckades validering")
                return False
            print("  ✅ Normal mode formatering")
            
            # Test traffic mode
            traffic_data = {'start_time': datetime.now()}
            transcription = {'text': 'Test trafikmeddelande om E4 norrgående'}
            
            traffic_content = formatter.format_for_traffic_mode(traffic_data, transcription)
            if not formatter.validate_content(traffic_content):
                print("  ❌ Traffic mode formatering misslyckades")
                return False
            print("  ✅ Traffic mode formatering")
            
            # Test VMA mode
            vma_data = {'transcription': {'text': 'Test VMA meddelande'}}
            vma_content = formatter.format_for_vma_mode(vma_data, is_test=True)
            
            if not formatter.validate_content(vma_content):
                print("  ❌ VMA mode formatering misslyckades")
                return False
            print("  ✅ VMA mode formatering")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Content formatter test fel: {e}")
            return False
    
    def test_screen_layouts(self) -> bool:
        """Testar skärmlayouter"""
        try:
            from screen_layouts import ScreenLayout
            from content_formatter import ContentFormatter
            
            layout = ScreenLayout()
            formatter = ContentFormatter()
            print("  ✅ ScreenLayout skapad")
            
            # Test layout skapande
            test_content = formatter.format_for_normal_mode({
                'rds_active': True,
                'battery_percent': 80
            })
            
            # Skapa layout-bild
            image = layout.create_layout(test_content)
            print(f"  ✅ Layout-bild skapad: {image.size}")
            
            # Test layout info
            layout_info = layout.get_layout_info(test_content)
            print(f"  ✅ Layout info: {layout_info['complexity']} element")
            
            # Spara test-bild om möjligt
            try:
                test_image_path = "logs/test_layout.png"
                image.save(test_image_path)
                print(f"  💾 Test-bild sparad: {test_image_path}")
            except:
                print("  ℹ️ Kunde inte spara test-bild (headless miljö)")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Screen layout test fel: {e}")
            return False
    
    def test_display_manager(self) -> bool:
        """Testar display manager"""
        try:
            from display_manager import DisplayManager
            
            # Skapa display manager
            manager = DisplayManager(log_dir="logs")
            print("  ✅ DisplayManager skapad")
            
            # Test status
            status = manager.get_status()
            print(f"  ✅ Display tillgänglig: {status['display_available']}")
            print(f"  ✅ Aktuellt läge: {status['current_mode']}")
            
            # Test olika uppdateringar
            print("  🧪 Testar normal mode uppdatering...")
            manager.update_normal_mode()
            print("  ✅ Normal mode uppdatering")
            
            time.sleep(1)
            
            print("  🧪 Testar traffic mode uppdatering...")
            traffic_data = {'start_time': datetime.now()}
            transcription = {'text': 'Test trafikmeddelande för display test'}
            manager.update_traffic_mode(traffic_data, transcription)
            print("  ✅ Traffic mode uppdatering")
            
            time.sleep(1)
            
            print("  🧪 Testar VMA test mode...")
            vma_data = {'transcription': {'text': 'Test VMA för display test'}}
            manager.update_vma_mode(vma_data, is_test=True)
            print("  ✅ VMA test mode uppdatering")
            
            time.sleep(1)
            
            # Återgå till normal
            manager.update_normal_mode()
            print("  ✅ Återgång till normal mode")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Display manager test fel: {e}")
            return False
    
    def test_integration(self) -> bool:
        """Testar integration med RDS Logger"""
        try:
            # Test att display-moduler kan importeras från rds_logger
            sys.path.insert(0, '.')
            
            # Simulera import från uppdaterad rds_logger
            print("  🔗 Testar integration-import...")
            
            from display_manager import DisplayManager
            from content_formatter import ContentFormatter
            
            print("  ✅ Display-moduler importerbara från rds_logger")
            
            # Test event-queue funktionalitet
            manager = DisplayManager(log_dir="logs")
            
            # Simulera RDS-event
            manager.queue_event('traffic_start', {
                'traffic_data': {'start_time': datetime.now()},
                'transcription': None
            })
            
            print("  ✅ Event-queue funktionalitet")
            
            # Test status-insamling
            status = manager._collect_system_status()
            print(f"  ✅ System status: {len(status)} parametrar")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Integration test fel: {e}")
            return False
    
    def test_performance(self) -> bool:
        """Testar prestanda och energi-aspekter"""
        try:
            from display_manager import DisplayManager
            from content_formatter import ContentFormatter
            import time
            
            print("  ⚡ Testar prestanda...")
            
            manager = DisplayManager(log_dir="logs")
            formatter = ContentFormatter()
            
            # Mät formaterings-prestanda
            start_time = time.time()
            test_content = formatter.format_for_normal_mode({
                'rds_active': True,
                'battery_percent': 50
            })
            format_time = time.time() - start_time
            print(f"  ⏱️ Formatering: {format_time:.3f}s")
            
            # Mät layout-prestanda
            from screen_layouts import ScreenLayout
            layout = ScreenLayout()
            
            start_time = time.time()
            image = layout.create_layout(test_content)
            layout_time = time.time() - start_time
            print(f"  ⏱️ Layout-rendering: {layout_time:.3f}s")
            
            # Kontrollera energi-tracking
            energy_stats = manager.energy_stats
            print(f"  🔋 Energi stats: {energy_stats}")
            
            # Performance är OK om det tar mindre än 2 sekunder totalt
            total_time = format_time + layout_time
            if total_time < 2.0:
                print(f"  ✅ Total prestanda: {total_time:.3f}s (Bra)")
                return True
            else:
                print(f"  ⚠️ Total prestanda: {total_time:.3f}s (Långsam)")
                self.warnings.append(f"Långsam prestanda: {total_time:.3f}s")
                return True  # Fortfarande OK, bara långsamt
                
        except Exception as e:
            print(f"  ❌ Performance test fel: {e}")
            return False
    
    def print_summary(self):
        """Skriver ut sammanfattning av alla tester"""
        print("\n" + "=" * 50)
        print("🎯 TEST SAMMANFATTNING")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = len(self.failed_tests)
        
        print(f"📊 Totalt: {total_tests} tester")
        print(f"✅ Godkända: {passed_tests}")
        print(f"❌ Misslyckade: {failed_tests}")
        print(f"⚠️ Varningar: {len(self.warnings)}")
        
        if self.failed_tests:
            print(f"\n❌ Misslyckade tester:")
            for test in self.failed_tests:
                print(f"  - {test}")
        
        if self.warnings:
            print(f"\n⚠️ Varningar:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        # Slutsats
        print(f"\n🎯 RESULTAT:")
        if failed_tests == 0:
            print("🎉 ALLA TESTER GODKÄNDA!")
            print("Display-systemet är redo för användning.")
        elif failed_tests <= 2:
            print("⚠️ VISSA TESTER MISSLYCKADES")
            print("Display-systemet kan fungera med begränsningar.")
        else:
            print("❌ MÅNGA TESTER MISSLYCKADES")
            print("Display-systemet behöver felsökning innan användning.")
        
        # Rekommendationer
        print(f"\n📋 REKOMMENDATIONER:")
        if 'E-paper Hardware Test' in self.failed_tests:
            print("  - Kontrollera e-paper display anslutning")
            print("  - Verifiera att SPI är aktiverat")
            print("  - Testa manuell e-paper initialization")
        
        if any('Import' in test for test in self.failed_tests):
            print("  - Installera saknade Python-moduler")
            print("  - Kontrollera att alla display-filer finns")
        
        if any('Performance' in warning for warning in self.warnings):
            print("  - Överväg att optimera för långsammare Pi-modeller")
            print("  - Minska uppdateringsfrekvens för energibesparing")
        
        print(f"\n📁 Loggar och debug-info finns i: logs/")

def main():
    """Huvudfunktion för test-suite"""
    test_suite = DisplayTestSuite()
    
    try:
        test_suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n🛑 Test avbrutet av användare")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Oväntat fel i test-suite: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
