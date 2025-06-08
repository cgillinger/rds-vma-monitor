#!/bin/bash
#
# Transkribering Live-Monitor
# Visar om transkribering pågår och status
#

echo "🧠 Transkribering Live-Monitor"
echo "============================="

# Funktion för att visa aktuell status
show_current_status() {
    echo "📊 AKTUELL STATUS ($(date '+%H:%M:%S')):"
    echo "----------------------------------------"
    
    # Kolla om transkribering-processer körs
    TRANSCRIPTION_PROCESSES=$(ps aux | grep -E "(whisper|transcrib)" | grep -v grep | wc -l)
    
    if [ "$TRANSCRIPTION_PROCESSES" -gt 0 ]; then
        echo "🟢 Transkribering PÅGÅR ($TRANSCRIPTION_PROCESSES processer)"
        ps aux | grep -E "(whisper|transcrib)" | grep -v grep
    else
        echo "⚪ Ingen transkribering körs just nu"
    fi
    
    echo ""
    
    # Senaste transkribering från loggar
    echo "📝 SENASTE AKTIVITET:"
    echo "--------------------"
    TODAY_LOG="logs/system_$(date +%Y%m%d).log"
    
    if [ -f "$TODAY_LOG" ]; then
        # Senaste start
        LAST_START=$(grep "Transcription started in background" "$TODAY_LOG" | tail -1)
        if [ -n "$LAST_START" ]; then
            echo "🚀 Senaste start: $LAST_START"
        fi
        
        # Senaste slutförande
        LAST_COMPLETE=$(grep "Transcription completed" "$TODAY_LOG" | tail -1)
        if [ -n "$LAST_COMPLETE" ]; then
            echo "✅ Senaste slutförd: $LAST_COMPLETE"
        fi
        
        # Kolla om det finns pågående (start utan slutförande)
        START_COUNT=$(grep -c "Transcription started in background" "$TODAY_LOG")
        COMPLETE_COUNT=$(grep -c "Transcription completed" "$TODAY_LOG")
        
        if [ "$START_COUNT" -gt "$COMPLETE_COUNT" ]; then
            PENDING=$((START_COUNT - COMPLETE_COUNT))
            echo "⏳ PÅGÅENDE: $PENDING transkribering(ar) väntar på slutförande"
        fi
    else
        echo "Ingen logg för idag ännu"
    fi
    
    echo ""
    
    # Visa transkript-filer
    echo "📁 SENASTE TRANSKRIPT-FILER:"
    echo "----------------------------"
    if [ -d "logs/transcriptions" ]; then
        ls -lt logs/transcriptions/*.txt 2>/dev/null | head -3
    else
        echo "Ingen transkriptions-katalog ännu"
    fi
}

# Funktion för live-monitoring
live_monitor() {
    echo "🔴 LIVE MONITORING (Ctrl+C för att avsluta)"
    echo "==========================================="
    
    TODAY_LOG="logs/system_$(date +%Y%m%d).log"
    
    if [ ! -f "$TODAY_LOG" ]; then
        echo "Väntar på systemlogg: $TODAY_LOG"
        while [ ! -f "$TODAY_LOG" ]; do
            sleep 5
        done
    fi
    
    # Tail systemloggen och filtrera transkribering
    tail -F "$TODAY_LOG" | grep --line-buffered -E "(Transcription|transcription|🧠|✅.*Transcription)"
}

# Huvudmeny
while true; do
    clear
    show_current_status
    
    echo ""
    echo "🎯 ALTERNATIV:"
    echo "=============="
    echo "1) Uppdatera status"
    echo "2) Live monitoring (real-time)"
    echo "3) Visa senaste 10 transkribering-loggar"
    echo "4) Visa pågående Python-processer"
    echo "5) Avsluta"
    echo ""
    
    read -p "Välj (1-5): " choice
    
    case $choice in
        1)
            echo "Uppdaterar..."
            sleep 1
            ;;
        2)
            live_monitor
            ;;
        3)
            echo ""
            echo "📋 SENASTE 10 TRANSKRIBERING-LOGGAR:"
            echo "===================================="
            if [ -f "$TODAY_LOG" ]; then
                grep -E "(Transcription|🧠)" "$TODAY_LOG" | tail -10
            else
                echo "Ingen logg tillgänglig"
            fi
            echo ""
            read -p "Tryck Enter för att fortsätta..."
            ;;
        4)
            echo ""
            echo "🐍 PYTHON-PROCESSER:"
            echo "==================="
            ps aux | grep python | grep -v grep
            echo ""
            read -p "Tryck Enter för att fortsätta..."
            ;;
        5)
            echo "Avslutar..."
            exit 0
            ;;
        *)
            echo "Ogiltigt val"
            sleep 1
            ;;
    esac
done
