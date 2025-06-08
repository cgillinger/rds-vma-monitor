# 🚨 VMA FIX IMPLEMENTATION GUIDE 
**För AI-assistent - Komplett instruktion baserad på Sveriges Radio dokumentation**

## 🎯 MISSION
Implementera VMA-funktionalitet i befintligt VMA-system **UTAN att påverka fungerande trafikmeddelande-funktionalitet**. Alla fixes ska vara **MINIMALA och ADDITIVA** - lägg bara till VMA-stöd, förändra aldrig befintlig traffic-logik.

## 📋 TEKNISK BAKGRUND (från SR dokumentation)
```
TRAFFIC: TA=1 + PTY=normal(3) + RT=normal
VMA:     TA=1 + PTY=30/31   + RT="VMA. Viktigt meddelande..."

PTY 30 = VMA Test
PTY 31 = Skarpt VMA
```

## 🔧 EXAKTA FILER ATT ÄNDRA

### **1. config.py** - Lägg till VMA duration filter
**Sökväg:** `~/rds_logger3/config.py`

**EXAKT ÄNDRING:** Lägg till EFTER befintlig `MIN_EVENT_DURATION_SECONDS = 15`:
```python
# VMA-specific duration filters (from SR documentation)
MIN_VMA_DURATION_SECONDS = 10      # VMA can be shorter than traffic
MIN_TRAFFIC_DURATION_SECONDS = 15  # Keep existing traffic filter
```

**VARFÖR:** VMA-meddelanden kan vara kortare än trafikmeddelanden enligt dokumentation.

---

### **2. rds_detector.py** - Fix VMA end event handling + duration
**Sökväg:** `~/rds_logger3/rds_detector.py`

**ÄNDRING A:** I `_handle_traffic_end()` metoden, HITTA denna kodsektion:
```python
# FILTER 1: Duration check (UPDATED to 15s)
if duration_seconds < self.min_traffic_duration_seconds:
    filter_reasons.append(f"Duration {duration_seconds:.1f}s < minimum {self.min_traffic_duration_seconds}s")
```

**ERSÄTT MED:**
```python
# FILTER 1: Duration check - different thresholds for VMA vs Traffic
current_event_type = getattr(self, 'current_event_type', 'traffic')
if 'vma' in current_event_type.lower():
    min_duration = MIN_VMA_DURATION_SECONDS
else:
    min_duration = self.min_traffic_duration_seconds

if duration_seconds < min_duration:
    filter_reasons.append(f"Duration {duration_seconds:.1f}s < minimum {min_duration}s")
```

**ÄNDRING B:** I `_handle_traffic_start()` metoden, LÄGG TILL efter `self.current_traffic_start_time = datetime.now()`:
```python
# Track event type for duration filtering
if self.current_state.get('pty') in [30, 31]:
    self.current_event_type = 'vma'
else:
    self.current_event_type = 'traffic'
```

**ÄNDRING C:** I imports-sektionen LÄNGST UPP, lägg till:
```python
from config import EVENT_TIMEOUT_SECONDS, MIN_EVENT_DURATION_SECONDS, MIN_VMA_DURATION_SECONDS
```

**VARFÖR:** VMA behöver kortare duration threshold och event-typ tracking.

---

### **3. transcriber.py** - VMA-aware content filtering  
**Sökväg:** `~/rds_logger3/transcriber.py`

**ÄNDRING A:** I `filter_traffic_content()` metoden, HITTA:
```python
def filter_traffic_content(self, text: str) -> str:
```

**ERSÄTT METODSIGNATUREN MED:**
```python
def filter_traffic_content(self, text: str, event_type: str = None) -> str:
```

**ÄNDRING B:** I SAMMA metod, LÄGG TILL i början av metoden:
```python
# VMA content should not be filtered - all content is critical
if event_type and 'vma' in event_type.lower():
    return self._clean_vma_text(text)
```

**ÄNDRING C:** LÄGG TILL ny metod i transcriber-klassen:
```python
def _clean_vma_text(self, text: str) -> str:
    """Clean VMA text without aggressive filtering"""
    if not text:
        return ""
    
    # Minimal cleaning for VMA - preserve all content
    text = ' '.join(text.split())  # Remove extra whitespace
    
    # Ensure proper sentence ending
    if text and not text.endswith('.'):
        text += '.'
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    
    return text
```

**ÄNDRING D:** I `_is_traffic_sentence()` metoden, LÄGG TILL VMA keywords:
```python
# Swedish traffic keywords
traffic_keywords = [
    # Existing traffic keywords (KEEP ALL)
    'väg', 'länsväg', 'riksväg', 'motorväg', 'e4', 'e6', 'e18', 'e20', 'rv',
    'trafik', 'trafikinformation', 'trafikmeddelande', 'olycka', 'krock',
    # ... keep all existing ...
    
    # VMA keywords (ADDITIVE ONLY)
    'vma', 'viktigt meddelande', 'allmänheten', 'faran över', 'varning',
    'meddelande', 'sök skydd', 'evakuera', 'kärnkraftverk', 'militär'
]
```

**ÄNDRING E:** I `transcribe_file_async()` metodanropet, uppdatera parameter:
```python
# In _transcribe_worker method, find this call:
processed_result = self._process_transcription(result, event_type, event_data)

# Update filter_traffic_content call in _process_transcription:
filtered_text = self.filter_traffic_content(text, event_type)
```

**VARFÖR:** VMA-innehåll är alltid kritiskt och ska inte filtreras som trafikmeddelanden.

---

### **4. display_monitor.py** - VMA end event handling
**Sökväg:** `~/rds_logger3/display_monitor.py`

**ÄNDRING:** I `_handle_event()` metoden, HITTA denna sektion:
```python
elif event_type in ['vma_start', 'vma_test_start']:
    is_test = event_type == 'vma_test_start'
    self.display_manager.handle_vma_start({
        'start_time': event_time,
        'content': event.get('content', ''),
        'rds_data': {}
    }, is_test=is_test)
```

**LÄGG TILL DIREKT EFTER (samma indenteringsnivå):**
```python
elif event_type in ['vma_end', 'vma_test_end']:
    is_test = event_type == 'vma_test_end'
    self.display_manager.handle_vma_end({
        'end_time': event_time,
        'content': event.get('content', ''),
        'rds_data': {}
    }, is_test=is_test)
```

**VARFÖR:** VMA end events hanteras inte för närvarande, vilket gör att displayen fastnar i VMA-läge.

---

## 🔒 BACKUP KOMMANDO
**OBLIGATORISKT före alla ändringar:**

```bash
# === BACKUP KOMMANDO (kopiera och kör) ===
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/vma_fixes_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp config.py "$BACKUP_DIR/"
cp rds_detector.py "$BACKUP_DIR/"
cp transcriber.py "$BACKUP_DIR/"
cp display_monitor.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/config.py"
echo "✅ Backup: $BACKUP_DIR/rds_detector.py"
echo "✅ Backup: $BACKUP_DIR/transcriber.py"
echo "✅ Backup: $BACKUP_DIR/display_monitor.py"
cat > "$BACKUP_DIR/README_backup.txt" << EOF
VMA FIXES BACKUP
================
Datum: $(date)
Ändring: VMA-funktionalitet fixes baserat på SR dokumentation
Problem: VMA end events + duration + content filtering
Säkerhetskopierade filer: config.py rds_detector.py transcriber.py display_monitor.py
EOF
# === SLUTFÖR BACKUP FÖRE FORTSÄTTNING ===
```

## ✅ VALIDERING
Efter implementation, systemet ska:

### **Traffic (OFÖRÄNDRAT):**
- TA=1 med PTY≠30/31 → Traffic event
- 15s minimum duration filter
- Content filtering som tidigare
- Display visar traffic-läge

### **VMA (NYTT):**
- TA=1 med PTY=30/31 → VMA event
- 10s minimum duration filter  
- Ingen content filtering (VMA är alltid viktiskt)
- Display visar VMA-läge
- VMA end events hanteras korrekt

### **Simulator Test:**
```bash
python3 vma_simulator.py list
python3 vma_simulator.py test test_short    # Ska filtreras (8s)
python3 vma_simulator.py test test_normal   # Ska sparas (25s)
python3 vma_simulator.py test emergency_nuclear  # Ska sparas (60s)
```

## 🚫 KRITISKA REGLER

### **FÖRBJUDET:**
- ❌ Ändra befintlig traffic-logik
- ❌ Modifiera TA-flagg handling för traffic
- ❌ Ändra display_manager.py (redan fungerar)
- ❌ Komplicera event detection-logik
- ❌ Ändra RDS parsing (redan korrekt)

### **TILLÅTET:**
- ✅ Lägga till VMA-specifika tillägg
- ✅ Additive keyword-lists
- ✅ Nya metoder för VMA-hantering
- ✅ Separata duration filters
- ✅ VMA end event handling

## 🎯 FRAMGÅNGSKRITERIER
1. **Traffic fortsätter fungera exakt som tidigare**
2. **VMA events startar och stannar korrekt**
3. **VMA får 10s duration filter (kortare än traffic 15s)**
4. **VMA content filtreras INTE (alltid viktigt)**
5. **Display växlar korrekt mellan Traffic/VMA/Idle**
6. **VMA-simulator fungerar för alla scenarios**

## 📝 IMPLEMENTATION ORDNING
1. **Backup** (obligatoriskt)
2. **config.py** (lägg till VMA duration)
3. **rds_detector.py** (duration + event type tracking)
4. **transcriber.py** (VMA content handling)
5. **display_monitor.py** (VMA end events)
6. **Test** med simulator

## 🔍 TEST PROTOKOLL
```bash
# 1. Verifiera backup
ls -la backup/vma_fixes_*/

# 2. Starta system
./start_vma_with_display.sh

# 3. Testa traffic (ska fungera som tidigare)
# (Vänta på verkliga trafikmeddelanden eller använd befintliga metoder)

# 4. Testa VMA
python3 vma_simulator.py test test_normal
python3 vma_simulator.py test emergency_nuclear

# 5. Kontrollera loggar
tail -f logs/system_$(date +%Y%m%d).log
ls -la logs/transcriptions/
```

---

**SLUTRESULTAT:** VMA-funktionalitet adderad till befintligt system utan att påverka fungerande traffic-hantering. Alla ändringar är MINIMALA och ADDITIVA.