#!/bin/bash
#
# AUTOMATISK VMA System med E-paper Display - LÄTTLÄSTA FÄRGER
# Fil: start_vma_with_display.sh (ERSÄTTER befintlig)
# Placering: ~/rds_logger3/start_vma_with_display.sh
#
# FÖRBÄTTRINGAR:
# - Bättre färgval för läsbarhet
# - Cyan istället för mörk blå
# - Normal text för info-meddelanden
#

set -e

# FÖRBÄTTRADE färgkoder för bättre läsbarhet
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'      # Lättläst cyan istället för mörk blå
WHITE='\033[1;37m'     # Vit för viktiga rubriker
NC='\033[0m'           # No Color

echo -e "${WHITE}🚀 VMA System med E-paper Display - AUTOMATISK START${NC}"
echo -e "${WHITE}=======================================================${NC}"

# Projektmapp
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

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
echo -e "${CYAN}KONFIGURATION:${NC}"
echo -e "${CYAN}==============${NC}"
echo "🔧 VMA-system: ORIGINAL start_vma_system.sh (OFÖRÄNDRAT)"
if [ "$DISPLAY_AVAILABLE" = true ]; then
    echo "🖥️ Display: TILLGÄNGLIGT (hardware)"
else
    echo -e "${YELLOW}🖥️ Display: INTE TILLGÄNGLIGT${NC}"
fi
echo "📡 Pipeline: Exakt samma som fungerande system"
echo "🔗 Integration: Display läser loggfiler (ingen pipeline-ändring)"
echo ""

# AUTOMATISK START - INGEN PROMPT
echo "📂 Skapar logs-katalog..."
echo ""

# Skapa logs-katalog
mkdir -p logs
mkdir -p logs/audio
mkdir -p logs/transcriptions
mkdir -p logs/screen 2>/dev/null || true

# Starta VMA-system
echo -e "${GREEN}🚀 STARTAR VMA-SYSTEM (ORIGINAL)${NC}"
echo -e "${GREEN}=================================${NC}"
echo "Startar det fungerande systemet: ./start_vma_system.sh"

# Starta VMA-systemet i bakgrunden
nohup ./start_vma_system.sh > /dev/null 2>&1 &
VMA_PID=$!

# Vänta lite för att systemet ska starta
sleep 3

# Kontrollera att VMA-systemet startade
if kill -0 $VMA_PID 2>/dev/null; then
    echo -e "${GREEN}✅ VMA-system kör (PID: $VMA_PID)${NC}"
else
    echo -e "${RED}❌ VMA-system kunde inte startas${NC}"
    exit 1
fi

# Starta display-monitor om tillgängligt
if [ "$DISPLAY_AVAILABLE" = true ]; then
    echo ""
    echo -e "${CYAN}🖥️ STARTAR DISPLAY-MONITOR (SEPARAT)${NC}"
    echo -e "${CYAN}====================================${NC}"
    echo "Väntar på att VMA-systemet ska skapa loggar..."
    
    # Vänta på att logs-katalogen skapas av VMA-systemet
    timeout=30
    while [ $timeout -gt 0 ]; do
        if [ -d "logs" ]; then
            echo -e "${GREEN}✅ Logs-katalog skapad av VMA-system${NC}"
            break
        fi
        sleep 1
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        echo -e "${YELLOW}⚠️ Timeout: Logs-katalog inte skapad, fortsätter ändå${NC}"
    fi
    
    echo "Startar Display Monitor (läser loggfiler)..."
    
    # Starta display monitor i bakgrunden
    nohup python3 display_monitor.py > /dev/null 2>&1 &
    DISPLAY_PID=$!
    
    # Vänta lite för att display-monitor ska starta
    sleep 2
    
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
echo -e "${WHITE}🎯 SYSTEM AKTIVT${NC}"
echo -e "${WHITE}================${NC}"
echo "📻 VMA-system: PID $VMA_PID (ORIGINAL start_vma_system.sh)"
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display Monitor: PID $DISPLAY_PID (läser loggfiler)"
fi
echo ""
echo "🔧 VMA-systemet kör exakt som vanligt"
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display läser bara loggfiler - rör inte pipelines"
fi
echo ""
echo -e "${YELLOW}Tryck Ctrl+C för att stoppa HELA systemet${NC}"
echo ""

# Cleanup-funktion vid avbrott
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stoppar system...${NC}"
    
    # Stoppa display monitor
    if [ -n "$DISPLAY_PID" ] && kill -0 $DISPLAY_PID 2>/dev/null; then
        echo "🖥️ Stoppar Display Monitor (PID: $DISPLAY_PID)"
        kill $DISPLAY_PID 2>/dev/null || true
    fi
    
    # Stoppa VMA-system
    if kill -0 $VMA_PID 2>/dev/null; then
        echo "📻 Stoppar VMA-system (PID: $VMA_PID)"
        kill $VMA_PID 2>/dev/null || true
        
        # Vänta lite och force-kill om nödvändigt
        sleep 2
        if kill -0 $VMA_PID 2>/dev/null; then
            echo -e "${YELLOW}⚠️ Force-stoppar VMA-system${NC}"
            kill -9 $VMA_PID 2>/dev/null || true
        fi
    fi
    
    # Cleanup andra processer som kan vara kvar
    echo "🧹 Cleanup av relaterade processer"
    pkill -f "rtl_fm" 2>/dev/null || true
    pkill -f "redsea" 2>/dev/null || true
    pkill -f "audio_recorder.py" 2>/dev/null || true
    pkill -f "rds_logger.py" 2>/dev/null || true
    pkill -f "display_monitor.py" 2>/dev/null || true
    
    echo -e "${GREEN}✅ System stoppat${NC}"
    exit 0
}

# Sätt upp signal handlers
trap cleanup SIGINT SIGTERM

# Vänta på signal
echo -e "${GREEN}✅ AUTOMATISK START SLUTFÖRD - System kör nu självständigt${NC}"
echo "📡 RDS-detektion aktiv, väntar på trafikmeddelanden och VMA"
if [ -n "$DISPLAY_PID" ]; then
    echo "🖥️ Display visar startup-skärm tills första event"
fi

# Huvudloop - vänta på Ctrl+C
while true; do
    # Kontrollera att processer fortfarande körs
    if ! kill -0 $VMA_PID 2>/dev/null; then
        echo -e "${RED}❌ VMA-system har stoppat oväntat${NC}"
        break
    fi
    
    if [ -n "$DISPLAY_PID" ] && ! kill -0 $DISPLAY_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Display Monitor har stoppat${NC}"
        DISPLAY_PID=""
    fi
    
    sleep 5
done

# Om vi kommer hit har något gått fel
cleanup
