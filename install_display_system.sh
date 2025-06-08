#!/bin/bash

# Installation Script för VMA E-paper Display System
# Installerar dependencies och konfigurerar e-paper display för Raspberry Pi

set -e  # Exit vid fel

echo "🖥️ VMA Display System - Installation"
echo "===================================="

# Färger för output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktioner för färgad output
error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Kontrollera om vi kör på Raspberry Pi
check_raspberry_pi() {
    if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        warning "Detta script är optimerat för Raspberry Pi"
        echo "Fortsätter ändå..."
    else
        success "Raspberry Pi detekterat"
    fi
}

# Kontrollera att vi kör som vanlig användare (inte root)
check_user() {
    if [ "$EUID" -eq 0 ]; then
        error "Kör inte detta script som root!"
        echo "Använd: ./install_display_system.sh"
        exit 1
    fi
    success "Kör som användare: $USER"
}

# Uppdatera system
update_system() {
    info "Uppdaterar system packages..."
    sudo apt update
    success "System packages uppdaterade"
}

# Aktivera SPI för e-paper display
enable_spi() {
    info "Kontrollerar SPI-konfiguration..."
    
    if [ -f /boot/config.txt ]; then
        if grep -q "^dtparam=spi=on" /boot/config.txt; then
            success "SPI redan aktiverat"
        else
            info "Aktiverar SPI..."
            echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
            warning "SPI aktiverat - omstart krävs efter installation"
            SPI_RESTART_REQUIRED=1
        fi
    else
        error "/boot/config.txt inte funnet - manuell SPI-konfiguration krävs"
    fi
}

# Installera Python-dependencies för e-paper
install_epaper_dependencies() {
    info "Installerar e-paper display dependencies..."
    
    # System packages
    sudo apt install -y \
        python3-pip \
        python3-pil \
        python3-numpy \
        python3-spidev \
        python3-rpi.gpio \
        python3-gpiozero
    
    success "System packages installerade"
    
    # Python packages
    info "Installerar Python packages..."
    pip3 install --user \
        Pillow \
        spidev \
        RPi.GPIO \
        gpiozero \
        psutil
    
    success "Python packages installerade"
}

# Installera Waveshare e-paper bibliotek
install_waveshare_library() {
    info "Installerar Waveshare e-paper bibliotek..."
    
    # Kontrollera om biblioteket redan finns
    if python3 -c "from waveshare_epd import epd4in26" 2>/dev/null; then
        success "Waveshare bibliotek redan installerat"
        return
    fi
    
    # Klona Waveshare repository
    if [ ! -d "e-Paper" ]; then
        info "Klonar Waveshare e-Paper repository..."
        git clone https://github.com/waveshare/e-Paper.git
    else
        info "e-Paper repository finns redan"
    fi
    
    # Installera Python-biblioteket
    cd e-Paper/RaspberryPi_JetsonNano/python
    sudo python3 setup.py install
    cd ../../..
    
    success "Waveshare bibliotek installerat"
}

# Kontrollera e-paper display anslutning
test_epaper_connection() {
    info "Testar e-paper display anslutning..."
    
    # Kontrollera SPI-enheter
    if [ ! -e /dev/spidev0.0 ] && [ ! -e /dev/spidev0.1 ]; then
        error "SPI-enheter inte tillgängliga"
        echo "Kontrollera att:"
        echo "  1. SPI är aktiverat i raspi-config"
        echo "  2. E-paper display är korrekt anslutet"
        echo "  3. Systemet har startats om efter SPI-aktivering"
        return 1
    fi
    
    success "SPI-enheter tillgängliga"
    
    # Test import av e-paper bibliotek
    if python3 -c "from waveshare_epd import epd4in26; print('Library import OK')" 2>/dev/null; then
        success "E-paper bibliotek importerar korrekt"
    else
        error "E-paper bibliotek kan inte importeras"
        echo "Kontrollera installation av Waveshare bibliotek"
        return 1
    fi
    
    return 0
}

# Skapa project-struktur för display-moduler
setup_project_structure() {
    info "Skapar projekt-struktur..."
    
    PROJECT_DIR="$HOME/rds_logger3"
    
    # Kontrollera att bas-projektet finns
    if [ ! -d "$PROJECT_DIR" ]; then
        error "Bas-projekt inte funnet: $PROJECT_DIR"
        echo "Kontrollera att VMA-projektet är installerat först"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    
    # Skapa backup av befintliga filer
    if [ -f "rds_logger.py" ]; then
        info "Skapar backup av befintlig rds_logger.py..."
        cp rds_logger.py rds_logger_backup_$(date +%Y%m%d_%H%M%S).py
    fi
    
    success "Projekt-struktur redo"
}

# Kontrollera dependencies för display-moduler
check_display_dependencies() {
    info "Kontrollerar Python-dependencies för display-moduler..."
    
    MISSING_DEPS=()
    
    # Kontrollera krävda moduler
    python3 -c "import PIL" 2>/dev/null || MISSING_DEPS+=("PIL/Pillow")
    python3 -c "import json" 2>/dev/null || MISSING_DEPS+=("json")
    python3 -c "import threading" 2>/dev/null || MISSING_DEPS+=("threading")
    python3 -c "import queue" 2>/dev/null || MISSING_DEPS+=("queue")
    python3 -c "import psutil" 2>/dev/null || MISSING_DEPS+=("psutil")
    
    if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
        success "Alla dependencies tillgängliga"
    else
        error "Saknade dependencies: ${MISSING_DEPS[*]}"
        exit 1
    fi
}

# Skapa test-skript för display
create_test_script() {
    info "Skapar test-skript för display..."
    
    cat > test_display.py << 'EOF'
#!/usr/bin/env python3
"""
Test Script för E-paper Display System
"""

import sys
import time
from datetime import datetime

def test_imports():
    """Testar import av alla display-moduler"""
    print("🧪 Testar imports...")
    
    try:
        from display_config import DISPLAY_SETTINGS
        print("✅ display_config - OK")
    except ImportError as e:
        print(f"❌ display_config - FAIL: {e}")
        return False
    
    try:
        from content_formatter import ContentFormatter
        print("✅ content_formatter - OK")
    except ImportError as e:
        print(f"❌ content_formatter - FAIL: {e}")
        return False
    
    try:
        from screen_layouts import ScreenLayout
        print("✅ screen_layouts - OK")
    except ImportError as e:
        print(f"❌ screen_layouts - FAIL: {e}")
        return False
    
    try:
        from display_manager import DisplayManager
        print("✅ display_manager - OK")
    except ImportError as e:
        print(f"❌ display_manager - FAIL: {e}")
        return False
    
    return True

def test_epaper_hardware():
    """Testar e-paper hårdvara"""
    print("\n🖥️ Testar e-paper hårdvara...")
    
    try:
        from waveshare_epd import epd4in26
        print("✅ Waveshare bibliotek - OK")
        
        epd = epd4in26.EPD()
        epd.init()
        print("✅ E-paper display init - OK")
        
        epd.Clear(0xFF)
        print("✅ Display clear - OK")
        
        epd.sleep()
        print("✅ Display sleep - OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Waveshare bibliotek - FAIL: {e}")
        return False
    except Exception as e:
        print(f"❌ E-paper test - FAIL: {e}")
        return False

def test_display_manager():
    """Testar display manager"""
    print("\n📱 Testar Display Manager...")
    
    try:
        from display_manager import DisplayManager
        
        # Skapa display manager
        manager = DisplayManager(log_dir="logs")
        print("✅ DisplayManager skapad - OK")
        
        # Testa status
        status = manager.get_status()
        print(f"✅ Status: {status['display_available']}")
        
        return True
        
    except Exception as e:
        print(f"❌ DisplayManager test - FAIL: {e}")
        return False

def main():
    print("🖥️ VMA Display System - Test Suite")
    print("=" * 40)
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import-test misslyckades")
        sys.exit(1)
    
    # Test 2: E-paper hårdvara
    if not test_epaper_hardware():
        print("\n⚠️ E-paper hårdvarutest misslyckades - kör i simulator-läge")
    
    # Test 3: Display Manager
    if not test_display_manager():
        print("\n❌ Display Manager-test misslyckades")
        sys.exit(1)
    
    print("\n🎉 Alla tester slutförda framgångsrikt!")
    print("Display-systemet är redo att användas.")

if __name__ == "__main__":
    main()
EOF

    chmod +x test_display.py
    success "Test-skript skapat: test_display.py"
}

# Skapa display-aktiverat start-skript
create_display_startup() {
    info "Skapar display-aktiverat start-skript..."
    
    cat > start_vma_with_display.sh << 'EOF'
#!/bin/bash

# VMA System Startup Script med E-paper Display
# Startar hela VMA-systemet inklusive display-integration

echo "🚀 VMA System med E-paper Display - Startup"
echo "==========================================="

# Kontrollera att vi är i rätt katalog
if [ ! -f "rds_logger.py" ]; then
    echo "❌ ERROR: rds_logger.py inte funnet"
    echo "Kör skriptet från ~/rds_logger3/ katalogen"
    exit 1
fi

# Kontrollera display-moduler
echo "🖥️ Kontrollerar display-moduler..."
if python3 -c "from display_manager import DisplayManager" 2>/dev/null; then
    echo "✅ Display-moduler OK"
    DISPLAY_MODE="enabled"
else
    echo "⚠️ Display-moduler inte tillgängliga - kör utan display"
    DISPLAY_MODE="disabled"
fi

# Kontrollera e-paper hårdvara
if [ "$DISPLAY_MODE" = "enabled" ]; then
    if python3 -c "from waveshare_epd import epd4in26" 2>/dev/null; then
        echo "✅ E-paper hårdvara OK"
    else
        echo "⚠️ E-paper hårdvara inte tillgänglig - simulator-läge"
    fi
fi

# Starta RTL_FM pipeline med display integration
echo "📡 Startar VMA-system med display..."
rtl_fm -f 103300000 -M fm -l 0 -A std -p 50 -s 171k -g 30 -F 9 - | \
~/redsea/build/redsea -r 171k -e 2>/dev/null | \
python3 rds_logger.py

echo "🛑 VMA-system stoppat"
EOF

    chmod +x start_vma_with_display.sh
    success "Display-startup skript skapat: start_vma_with_display.sh"
}

# Visa post-installation instruktioner
show_post_install_instructions() {
    echo ""
    echo "🎉 Installation slutförd!"
    echo "========================"
    echo ""
    echo "📋 Nästa steg:"
    echo ""
    echo "1. 🧪 Testa display-systemet:"
    echo "   cd ~/rds_logger3"
    echo "   ./test_display.py"
    echo ""
    echo "2. 🚀 Starta VMA-systemet med display:"
    echo "   ./start_vma_with_display.sh"
    echo ""
    echo "3. 🔧 Konfigurera display-inställningar:"
    echo "   Redigera display_config.py för anpassningar"
    echo ""
    
    if [ "${SPI_RESTART_REQUIRED:-}" = "1" ]; then
        warning "OMSTART KRÄVS för att aktivera SPI!"
        echo "Kör: sudo reboot"
        echo ""
    fi
    
    echo "📚 Dokumentation:"
    echo "   - Display konfiguration: display_config.py"
    echo "   - Layouter: screen_layouts.py"
    echo "   - Content formatting: content_formatter.py"
    echo "   - Main manager: display_manager.py"
    echo ""
    echo "🐛 Vid problem:"
    echo "   - Kontrollera logs/system_YYYYMMDD.log"
    echo "   - Testa e-paper anslutning manuellt"
    echo "   - Verifiera att SPI är aktiverat"
}

# Huvudinstallation
main() {
    echo "Startar installation av VMA Display System..."
    echo ""
    
    # Grundläggande kontroller
    check_raspberry_pi
    check_user
    
    # System-uppdatering
    update_system
    
    # SPI-konfiguration
    enable_spi
    
    # Installera dependencies
    install_epaper_dependencies
    install_waveshare_library
    
    # Projekt-setup
    setup_project_structure
    check_display_dependencies
    
    # Test e-paper anslutning
    test_epaper_connection
    
    # Skapa hjälp-skript
    create_test_script
    create_display_startup
    
    # Visa instruktioner
    show_post_install_instructions
    
    success "Installation slutförd framgångsrikt!"
}

# Hantera command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "VMA Display System - Installation Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h     Visa denna hjälp"
    echo "  --test-only    Kör endast tester utan installation"
    echo ""
    echo "Detta script installerar:"
    echo "  - E-paper display dependencies"
    echo "  - Waveshare bibliotek"
    echo "  - SPI-konfiguration"
    echo "  - Test-skript"
    echo ""
    exit 0
fi

if [ "$1" = "--test-only" ]; then
    echo "🧪 Kör endast tester..."
    check_raspberry_pi
    test_epaper_connection
    exit 0
fi

# Kör huvudinstallation
main "$@"
EOF
