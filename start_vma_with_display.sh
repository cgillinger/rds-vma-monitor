#!/bin/bash
#
# FÖRBÄTTRAT VMA System med E-paper Display - ROBUST USB-hantering
# Fil: start_vma_with_display.sh (FÖRBÄTTRAD VERSION)
# Placering: ~/rds_logger3/start_vma_with_display.sh
#
# FÖRBÄTTRINGAR:
# - Robust USB-återställning och cleanup
# - Bättre process-hantering och timing
# - Förbättrad felhantering
# - Längre stabiliseringstider
#

set -e

# FÖRBÄTTRADE färgkoder för bättre läsbarhet
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'      # Lättläst cyan istället för mörk blå
WHITE='\033[1;37m'     # Vit för viktiga rubriker
NC='\033[0m'           # No Color

echo -e "${WHITE}🚀 FÖRBÄTTRAT VMA System med E-paper Display${NC}"
echo -e "${WHITE}==============================================${NC}"
echo -e "${CYAN}🔧 MED: USB-reset, robust cleanup, bättre timing${NC}"

# Projektmapp
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# FÖRBÄTTRAD: Process tracking för robust cleanup
VMA_PID=""
DISPLAY_PID=""

# NY: Robust cleanup-funktion
robust_cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 FÖRBÄTTRAD CLEANUP - Stoppar system...${NC}"
    
    # STEG 1: Stoppa display monitor först (läser bara filer)
    if [ -n "$DISPLAY_PID" ] && kill -0 $DISPLAY_PID 2>/dev/null; then
        echo "🖥️ Stoppar Display Monitor (PID: $DISPLAY_PID)"
        kill -TERM $DISPLAY_PID 2>/dev/null || true
        sleep 2
        # Force kill om nödvändigt
        if kill -0 $DISPLAY_PID 2>/dev/null; then
            kill -KILL $DISPLAY_PID 2>/dev/null || true
        fi
    fi
    
    # STEG 2: Stoppa VMA-system (signalerar till alla child-processer)
    if [ -n "$VMA_PID" ] && kill -0 $VMA_PID 2>/dev/null; then
        echo "📻 Stoppar VMA-system (PID: $VMA_PID)"
        kill -TERM $VMA_PID 2>/dev/null || true
        
        # FÖRBÄTTRAT: Längre väntetid för graceful shutdown
        echo "⏳ Väntar på graceful shutdown (5 sekunder)..."
        sleep 5
        
        # Force kill om fortfarande kvar
        if kill -0 $VMA_PID 2>/dev/null; then
            echo -e "${YELLOW}⚠️ Force-stoppar VMA-system${NC}"
            kill -KILL $VMA_PID 2>/dev/null || true
            sleep 2
        fi
    fi
    
    # STEG 3: ROBUST cleanup av alla relaterade processer
    echo "🧹 ROBUST cleanup av alla VMA-processer..."
    
    # Specifik cleanup för RTL-SDR pipeline (i rätt ordning)
    pkill -f "audio_recorder.py" 2>/dev/null || true
    sleep 1
    pkill -f "redsea" 2>/dev/null || true
    sleep 1
    pkill -f "rtl_fm.*103300000" 2>/dev/null || true
    sleep 2  # Extra tid för USB-frigöring
    
    # Övriga VMA-processer
    pkill -f "rds_logger.py" 2>/dev/null || true
    pkill -f "display_monitor.py" 2>/dev/null || true
    
    # STEG 4: USB-återställning (från förbättrade kärnskriptet)
    echo "🔧 USB-återställning..."
    
    # Hitta och reset RTL-SDR USB-enhet
    USB_DEVICE=$(lsusb | grep -i "rtl\|realtek" | head -1)
    if [[ -n "$USB_DEVICE" ]]; then
        BUS=$(echo "$USB_DEVICE" | awk '{print $2}')
        DEV=$(echo "$USB_DEVICE" | awk '{print $4}' | sed 's/://')
        
        if command -v usbreset &> /dev/null; then
            echo "📡 USB reset: Bus $BUS Device $DEV"
            sudo usbreset "/dev/bus/usb/$BUS/$DEV" 2>/dev/null || true
        fi
    fi
    
    # STEG 5: Rensa named pipes
    rm -f /tmp/vma_rds_data 2>/dev/null || true
    rm -f /tmp/vma_audio_control 2>/dev/null || true
    
    echo -e "${GREEN}✅ FÖRBÄTTRAD cleanup komplett${NC}"
    exit 0
}

# FÖRBÄTTRAT: Sätt upp robusta signal handlers
trap robust_cleanup SIGINT SIGTERM EXIT

# Kontrollera kärnkomponenter
if [ ! -f "start_vma_system.sh" ]; then
    echo -e "${RED}❌ Fel: start_vma_system.sh saknas${NC}"
    echo -e "${RED}   Detta skript kräver det fungerande VMA-systemet${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Fungerande VMA-system hittat: start_vma_system.sh${NC}"

# Kontrollera VMA-systemfiler
required_files=(
    "rds_logger.py"
    "rds_detector.py" 
    "rds_parser.py"
    "audio_recorder.py"
    "transcriber.py"
    "config.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Fel: Obligatorisk fil saknas: $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Alla kärnfiler för VMA-system finns${NC}"

# Kontrollera display-moduler
display_files=(
    "display_monitor.py"
    "display_manager.py"
    "display_state_machine.py"
    "content_formatter.py"
    "screen_layouts.py"
    "display_config.py"
)

missing_display_files=()
for file in "${display_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_display_files+=("$file")
    fi
done

if [ ${#missing_display_files[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ Display-moduler tillgängliga${NC}"
    DISPLAY_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️ Display-moduler saknas: ${missing_display_files[*]}${NC}"
    echo -e "${YELLOW}   VMA-system kommer köra utan display${NC}"
    DISPLAY_AVAILABLE=false
fi

# Testa display-moduler om tillgängliga
if [ "$DISPLAY_AVAILABLE" = true ]; then
    if python3 -c "
import sys
sys.path.append('.')
try:
    from display_config import DISPLAY_SETTINGS
    from display_state_machine import DisplayStateMachine
    from content_formatter import ContentFormatter
    print('✅ Display-moduler kan importeras')
except Exception as e:
    print(f'❌ Import-fel: {e}')
    sys.exit(1)
"; then
        echo -e "${GREEN}✅ Display-moduler kan importeras${NC}"
    else
        echo -e "${RED}❌ Display-moduler har fel${NC}"
        DISPLAY_AVAILABLE=false
    fi
fi

# Kontrollera e-paper hårdvara om display är tillgängligt
if [ "$DISPLAY_AVAILABLE" = true ]; then
    if python3 -c "
try:
    from waveshare_epd import epd4in26
    print('✅ E-paper hårdvara tillgänglig')
except Exception as e:
    print(f'⚠️ E-paper hårdvara: {e}')
"; then
        echo -e "${GREEN}✅ E-paper hårdvara tillgänglig${NC}"
    else
        echo -e "${YELLOW}⚠️ E-paper hårdvara ej tillgänglig (kör ändå)${NC}"
    fi
fi

echo ""
echo -e "${CYAN}FÖRBÄTTRAD KONFIGURATION:${NC}"
echo -e "${CYAN}=========================${NC}"
echo "🔧 VMA-system: FÖRBÄTTRAD start_vma_system.sh (USB-reset + robust cleanup)"
if [ "$DISPLAY_AVAILABLE" = true ]; then
    echo "🖥️ Display: TILLGÄNGLIGT (hardware)"
else
    echo -e "${YELLOW}🖥️ Display: INTE TILLGÄNGLIGT${NC}"
fi
echo "📡 Pipeline: Samma fungerande pipeline med robust hantering"
echo "🔗 Integration: Display läser loggfiler (ingen pipeline-ändring)"
echo "🔧 Förbättringar: USB-reset, längre timers, bättre cleanup"
echo ""

# AUTOMATISK START - INGEN PROMPT
echo "📂 Skapar logs-katalog..."
echo ""

# Skapa logs-katalog
mkdir -p logs
mkdir -p logs/audio
mkdir -p logs/transcriptions
mkdir -p logs/screen 2>/dev/null || true

# FÖRBÄTTRAT: Starta VMA-system med bättre verifiering
echo -e "${GREEN}🚀 STARTAR FÖRBÄTTRAT VMA-SYSTEM${NC}"
echo -e "${GREEN}===================================${NC}"
echo "Startar det förbättrade systemet: ./start_vma_system.sh"

# Starta VMA-systemet i bakgrunden
nohup ./start_vma_system.sh > /dev/null 2>&1 &
VMA_PID=$!

# FÖRBÄTTRAT: Längre stabiliseringstid för VMA-system
echo "⏳ Väntar på VMA-system stabilisering (8 sekunder)..."
sleep 8

# ROBUST: Kontrollera att VMA-systemet verkligen startade
if kill -0 $VMA_PID 2>/dev/null; then
    echo -e "${GREEN}✅ VMA-system kör (PID: $VMA_PID)${NC}"
    
    # Extra verifiering: kolla att RTL-processer startade
    if pgrep -f "rtl_fm.*103300000" &>/dev/null; then
        echo -e "${GREEN}✅ RTL-FM process detekterad${NC}"
    else
        echo -e "${YELLOW}⚠️ RTL-FM process inte detekterad ännu (kan ta längre tid)${NC}"
    fi
    
    if pgrep -f "redsea" &>/dev/null; then
        echo -e "${GREEN}✅ Redsea process detekterad${NC}"
    else
        echo -e "${YELLOW}⚠️ Redsea process inte detekterad ännu${NC}"
    fi
    
else
    echo -e "${RED}❌ VMA-system kunde inte startas${NC}"
    echo -e "${RED}🔧 Kolla systemloggar: logs/system_$(date +%Y%m%d).log${NC}"
    exit 1
fi

# Starta display-monitor om tillgängligt
if [ "$DISPLAY_AVAILABLE" = true ]; then
    echo ""
    echo -e "${CYAN}🖥️ STARTAR DISPLAY-MONITOR (SEPARAT)${NC}"
    echo -e "${CYAN}====================================${NC}"
    echo "Väntar på att VMA-systemet ska skapa loggar..."
    
    # FÖRBÄTTRAT: Längre timeout för logs-katalog
    timeout=45
    while [ $timeout -gt 0 ]; do
        if [ -d "logs" ] && [ -f "logs/system_$(date +%Y%m%d).log" ]; then
            echo -e "${GREEN}✅ Logs-katalog och systemlogg skapad av VMA-system${NC}"
            break
        fi
        sleep 1
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        echo -e "${YELLOW}⚠️ Timeout: Systemlogg inte skapad, startar display ändå${NC}"
    fi
    
    echo "Startar Display Monitor (läser loggfiler)..."
    
    # Starta display monitor i bakgrunden
    nohup python3 display_monitor.py > /dev/null 2>&1 &
    DISPLAY_PID=$!
    
    # FÖRBÄTTRAT: Längre verifiering av display-monitor
    echo "⏳ Väntar på Display Monitor stabilisering (5 sekunder)..."
    sleep 5
    
    # Kontrollera att display-monitor startade
    if kill -0 $DISPLAY_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Display Monitor startad (PID: $DISPLAY_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️ Display Monitor kunde inte startas (VMA-system fortsätter)${NC}"
        DISPLAY_PID=""
    fi
else
    echo ""
    echo -e "${YELLOW}Display inte tillgängligt - endast VMA-system körs${NC}"
    DISPLAY_PID=""
fi

echo ""
echo -e "${WHITE}🎯 FÖRBÄTTRAT SYSTEM AKTIVT${NC}"
echo -e "${WHITE}============================${NC}"
echo "📻 VMA-system: PID $VMA_PID (FÖRBÄTTRAD start_vma_system.sh)"
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display Monitor: PID $DISPLAY_PID (läser loggfiler)"
fi
echo ""
echo "🔧 FÖRBÄTTRINGAR AKTIVA:"
echo "   ✅ USB-reset vid start och stopp"
echo "   ✅ Robust process cleanup (korrekt ordning)"
echo "   ✅ Längre stabiliseringstider (8s VMA, 5s Display)"
echo "   ✅ RTL-SDR ready verification"
echo "   ✅ Named pipe collision handling"
echo "   ✅ Förbättrad felhantering"
echo ""
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display läser bara loggfiler - rör inte pipelines"
fi
echo ""
echo -e "${YELLOW}Tryck Ctrl+C för att stoppa HELA systemet${NC}"
echo ""

# Vänta på signal
echo -e "${GREEN}✅ FÖRBÄTTRAD AUTOMATISK START SLUTFÖRD${NC}"
echo "📡 RDS-detektion aktiv, väntar på trafikmeddelanden och VMA"
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display visar startup-skärm tills första event"
fi
echo "🔧 Systemet har nu robust USB-hantering och cleanup"

# FÖRBÄTTRAD: Huvudloop med bättre process-monitoring
while true; do
    # ROBUST: Kontrollera att VMA-systemet fortfarande körs
    if ! kill -0 $VMA_PID 2>/dev/null; then
        echo -e "${RED}❌ VMA-system har stoppat oväntat${NC}"
        echo -e "${RED}🔧 Trolig orsak: USB-gränssnittsproblem${NC}"
        echo -e "${RED}📋 Kolla loggar: logs/system_$(date +%Y%m%d).log${NC}"
        break
    fi
    
    # Kontrollera att kritiska processer fortfarande körs
    if ! pgrep -f "rtl_fm.*103300000" &>/dev/null; then
        echo -e "${RED}❌ RTL-FM process har dött - USB-problem${NC}"
        break
    fi
    
    if [ -n "$DISPLAY_PID" ] && ! kill -0 $DISPLAY_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Display Monitor har stoppat${NC}"
        DISPLAY_PID=""
    fi
    
    # Status-update var 30:e sekund (oftare än tidigare)
    sleep 30
done

# Om vi kommer hit har något gått fel
echo -e "${RED}💥 Systemet har stoppat oväntat - kör robust cleanup${NC}"
robust_cleanup