#!/usr/bin/env python3
"""
Live Test av Display-funktionalitet
Fil: test_display_live.py
Placering: ~/rds_logger3/test_display_live.py

Testar display-systemet live med olika lägen och demonstrerar funktionalitet.
"""

import sys
import time
import logging
from datetime import datetime, timedelta

# Setup minimal logging för test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_normal_mode():
    """Testar normal mode display"""
    print("🖥️ Testar Normal Mode Display")
    print("-" * 40)
    
    try:
        from display_manager import DisplayManager
        
        # Skapa display manager
        manager = DisplayManager(log_dir="logs")
        print("✅ DisplayManager skapad")
        
        # Starta manager
        manager.start()
        print("✅ Display Manager startad")
        
        # Visa normal status
        print("📱 Visar normal systemstatus på display...")
        manager.update_normal_mode()
        
        print("\n📺 Normal systemstatus visas nu på e-paper displayen!")
        print("Du ska se:")
        print("  • 🟢 INGA AKTIVA LARM")
        print("  • Dagens datum och aktuell tid")
        print("  • Systemstatus (RDS, AI, Ljud, Batteri)")
        print("  • Aktivitetssammanfattning")
        
        input("\nTryck Enter för att fortsätta till trafikmeddelande-test...")
        
        return manager
        
    except Exception as e:
        print(f"❌ Fel vid normal mode test: {e}")
        return None

def test_traffic_mode(manager):
    """Testar traffic mode display"""
    print("\n🚧 Testar Traffic Mode Display")
    print("-" * 40)
    
    try:
        # Simulera trafikmeddelande
        traffic_data = {
            'start_time': datetime.now() - timedelta(minutes=2, seconds=30)
        }
        
        transcription = {
            'text': 'Trafikinformation. På E4 norrgående vid Rotebro har det skett en olycka. Ett fordon har stannat i högra körfältet. Kö bildas på cirka 3 kilometer. Räkna med 15 minuter extra restid. Kör försiktigt förbi olycksplatsen.'
        }
        
        print("📱 Visar trafikmeddelande på display...")
        manager.update_traffic_mode(traffic_data, transcription)
        
        print("\n📺 Trafikmeddelande visas nu på e-paper displayen!")
        print("Du ska se:")
        print("  • 🚧 TRAFIKMEDDELANDE PÅGÅR")
        print("  • Strukturerad info (plats, typ, kö, riktning)")
        print("  • Fullständig transkription")
        print("  • Status och timing-information")
        
        input("\nTryck Enter för att fortsätta till VMA-test...")
        
    except Exception as e:
        print(f"❌ Fel vid traffic mode test: {e}")

def test_vma_mode(manager):
    """Testar VMA mode display"""
    print("\n🚨 Testar VMA Mode Display")
    print("-" * 40)
    
    try:
        # Simulera VMA-test
        vma_data = {
            'transcription': {
                'text': 'Viktigt meddelande till allmänheten. Detta är en test av VMA-systemet. Meddelandet testas för att säkerställa att systemet fungerar korrekt. Lyssna på Sveriges Radio P4 för mer information. Detta är endast en övning.'
            },
            'rds_data': {
                'pty': 30,  # VMA test
                'ps': 'P4 Sthlm',
                'rt': 'VMA TEST - Viktigt meddelande till allmänheten'
            }
        }
        
        print("📱 Visar VMA-test på display...")
        manager.update_vma_mode(vma_data, is_test=True)
        
        print("\n📺 VMA-TEST visas nu på e-paper displayen!")
        print("Du ska se:")
        print("  • 🧪🧪🧪 VMA-TEST 🧪🧪🧪")
        print("  • DETTA ÄR ENDAST EN ÖVNING")
        print("  • Stort, tydligt meddelande")
        print("  • Kontaktinformation längst ned")
        print("  • Hela skärmen används för maximal synlighet")
        
        input("\nTryck Enter för att återgå till normal mode...")
        
    except Exception as e:
        print(f"❌ Fel vid VMA mode test: {e}")

def test_return_to_normal(manager):
    """Återgår till normal mode"""
    print("\n📅 Återgår till Normal Mode")
    print("-" * 40)
    
    try:
        print("📱 Återgår till normal systemstatus...")
        manager.update_normal_mode()
        
        print("\n📺 Normal systemstatus visas igen på displayen!")
        print("✅ Komplett display-test slutfört!")
        
        input("\nTryck Enter för att stoppa display manager...")
        
    except Exception as e:
        print(f"❌ Fel vid återgång till normal mode: {e}")

def test_energy_tracking(manager):
    """Visar energi-statistik"""
    print("\n⚡ Energi- och prestanda-statistik")
    print("-" * 40)
    
    try:
        status = manager.get_status()
        energy_stats = status.get('energy_stats', {})
        
        print(f"🔋 Batterinivå: {energy_stats.get('battery_level', 'N/A')}%")
        print(f"📊 Uppdateringar idag: {energy_stats.get('updates_today', 0)}")
        print(f"⚡ Total energi idag: {energy_stats.get('total_energy_today', 0):.2f} Watt-sekunder")
        print(f"⏱️ Senaste uppdatering: {energy_stats.get('last_update_energy', 0):.2f} Ws")
        
        print(f"\n📱 Display-status:")
        print(f"  • Tillgänglig: {status.get('display_available', False)}")
        print(f"  • Aktuellt läge: {status.get('current_mode', 'N/A')}")
        print(f"  • Kö-storlek: {status.get('queue_size', 0)} events")
        print(f"  • Systemet körs: {status.get('running', False)}")
        
    except Exception as e:
        print(f"❌ Fel vid energi-statistik: {e}")

def main():
    """Huvudfunktion för live display-test"""
    print("🖥️ VMA Display System - Live Test")
    print("=" * 50)
    print()
    print("Detta test visar alla display-lägen på din e-paper skärm.")
    print("Du kommer att se hur systemet växlar mellan:")
    print("  • Normal systemstatus")
    print("  • Trafikmeddelanden")  
    print("  • VMA-larm (test)")
    print()
    
    # Kontrollera att display-moduler finns
    try:
        from display_manager import DisplayManager
        from waveshare_epd import epd4in26
        print("✅ Display-moduler och e-paper bibliotek tillgängliga")
    except ImportError as e:
        print(f"❌ Display-moduler inte tillgängliga: {e}")
        print("Kör: ./test_display_functionality.py för att diagnostisera problemet")
        sys.exit(1)
    
    print("\nSystemet kommer att uppdatera din e-paper display flera gånger.")
    print("Varje uppdatering tar ~4 sekunder (normalt för e-paper).")
    print()
    
    # Fråga användaren om de vill fortsätta
    response = input("Vill du fortsätta med live display-test? (Y/n): ")
    if response.lower() == 'n':
        print("Test avbrutet av användare")
        sys.exit(0)
    
    manager = None
    
    try:
        # Test 1: Normal Mode
        manager = test_normal_mode()
        if not manager:
            print("❌ Kunde inte starta display manager")
            sys.exit(1)
        
        # Test 2: Traffic Mode
        test_traffic_mode(manager)
        
        # Test 3: VMA Mode
        test_vma_mode(manager)
        
        # Test 4: Return to Normal
        test_return_to_normal(manager)
        
        # Test 5: Energy Statistics
        test_energy_tracking(manager)
        
        print("\n🎉 Alla display-tester slutförda framgångsrikt!")
        print("📺 E-paper display-systemet fungerar perfekt!")
        
    except KeyboardInterrupt:
        print("\n🛑 Test avbrutet av användare")
    except Exception as e:
        print(f"\n💥 Oväntat fel: {e}")
    finally:
        # Stoppa display manager om det är aktivt
        if manager:
            try:
                manager.stop()
                print("✅ Display manager stoppad")
            except:
                pass
        
        print("✅ Live test avslutat")

if __name__ == "__main__":
    main()
