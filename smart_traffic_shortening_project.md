# Projekt: Smart Förkortning av Trafikmeddelanden - VMA System

**Projektdatum:** 2025-06-17  
**Status:** Redo för implementation  
**Syfte:** Regelbaserad intelligent förkortning av svenska trafikmeddelanden utan ytterligare AI

---

## 🎯 **Projektmål**

### **Huvudmål**
- **Minimal bearbetning**: Visa originaltranskript när det får plats på e-paper displayen
- **Smart trunkering**: Bara förkorta när text faktiskt inte får plats på skärmen  
- **Bevara faktainnehåll**: Inga viktiga trafikdetaljer får försvinna under förkortning
- **Säker off-topic-rensning**: Ta bort uppenbart irrelevant innehåll (musik, väder) med hög säkerhet

### **Sekundära mål**
- **Energieffektivitet**: Ingen ytterligare AI-modell (behåll bara KBWhisper)
- **Svenska-optimerat**: Regelbaserat system som förstår svenska trafikmeddelanden
- **Tillförlitligt**: Deterministisk process - samma input ger samma output
- **Underhållbart**: Lätt att justera regler och tröskelvärden

---

## 📊 **Problemanalys**

### **Nuvarande situation**
- **Display**: 800×480 pixlar e-paper med begränsad textyta
- **Textkapacitet**: Cirka 300-350 tecken får plats innan trunkering med "..."
- **Aktuellt problem**: Långa trafikmeddelanden visas trunkerade, viktiga detaljer försvinner

### **Konkreta exempel**

**Exempel 1: För långt meddelande (873 tecken)**
```
Original: "E4 är avstängd för er som kommer från Sörmland in mot Järna..."
Display: "E4 är avstängd för er som kommer från Sörmland in mot Järna. Det är före avfarten Järna, som mellan Hölö och Järna. Där är hela E4 avstängd mot Södertälje. Det hör ihop med en personbil som tappat ett båtsläp. De ligger över körbanan och räddningstjänst är på plats. Men avstängt mellan Hölö och Järna, och ingen prognos på hur lång tid det tar. Sista möjliga avfart Det är då trafikplats Hölö just nu. På E4 E20 Essingeleden är infarten till Norra länken..."

Kortversion (för kort): "E4 N Hölö - Olycka"
```

**Exempel 2: Lagom längd (178 tecken)**
```
Original: "Det är en olycka på E4E20 Essingeleden. Det är precis vid infarten till Norra länken. I slutet av Essingeleden, precis före Norra länken och infarten mot Uppsalavägen, är stängd."
Display: Visas komplett utan trunkering ✅
```

### **Teknisk orsak**
Genom kodanalys identifierad:

1. **content_formatter.py**: Ska begränsa till 600 tecken men fungerar inte korrekt
2. **screen_layouts.py**: Renderar transcription-sektionen utan höjdbegränsning
3. **Resultat**: Långa texter renderas och trunkeras med "..." i slutet

---

## 🔧 **Teknisk strategi**

### **Fas 1: Detektera trunkeringsbehov**
- Implementera noggrann textmätning före rendering
- Beräkna faktisk tillgänglig höjd för transcription-text
- Trigga förkortning endast när text inte får plats

### **Fas 2: Graduell förkortning**
Prova tekniker i ordning tills text får plats:

1. **Off-topic rensning** (säker):
   - Ta bort musik-annonseringar: "Staffan Hellstrand, låten heter Fanfar"
   - Ta bort väder-omnämnanden som inte relaterar till trafik
   - Ta bort programinformation och reklam

2. **Redundant information**:
   - Ta bort upprepningar: "E4 avstängd... E4 avstängd"
   - Förkorta långdragna beskrivningar
   - Ta bort onödiga prepositioner och fyllnadsord

3. **Strukturell komprimering**:
   - Förkorta planamn: "trafikplats Hölö" → "Hölö"
   - Komprimera riktningar: "i riktning mot" → "mot"
   - Förkorta myndighetsnamn: "räddningstjänst" → "räddning"

4. **Smart meningsval**:
   - Prioritera huvudincident över sekundära händelser
   - Behåll kritisk info: väg, plats, incident-typ, köinformation, omledning
   - Ta bort mindre relevanta detaljer

### **Fas 3: Svenska trafikspecifik optimering**
- Kännedom om svenska vägnamn och trafiktermer
- Förstå svensk trafikrapporteringsstruktur
- Optimera för döva användares informationsbehov

---

## 📁 **Implementation Plan**

### **Filmodifikationer**

#### **1. Ny modul: `traffic_text_optimizer.py`**
```python
class TrafficTextOptimizer:
    def optimize_for_display(self, text: str, max_length: int) -> str:
        """Smart förkortning av svenska trafikmeddelanden"""
        
    def measure_text_fit(self, text: str, layout_constraints: dict) -> bool:
        """Mät om text får plats på display"""
        
    def remove_off_topic_content(self, text: str) -> str:
        """Ta bort musik, väder, program-info"""
        
    def compress_traffic_language(self, text: str) -> str:
        """Svenska trafikspecifik komprimering"""
```

#### **2. Modifierad: `content_formatter.py`**
```python
def format_for_traffic_mode(self, traffic_data: Dict, transcription: Dict = None, status_info: Dict = None):
    # Lägg till smart textpassning före rendering
    if transcription and transcription.get('text'):
        original_text = transcription['text']
        
        # Mät om text får plats
        if not self._text_fits_display(original_text):
            # Använd TrafficTextOptimizer för förkortning
            optimized_text = self.text_optimizer.optimize_for_display(
                original_text, 
                max_length=350  # Säker längd för display
            )
            transcription['text'] = optimized_text
```

#### **3. Förbättrad: `screen_layouts.py`**
```python
def _render_traffic_layout(self, draw: ImageDraw.Draw, sections: Dict):
    # Förbättra height calculation för transcription-sektionen
    # Lägg till available_height begränsning
    if 'transcription' in sections:
        transcription_data = sections['transcription']
        current_y = self._render_section_content(
            draw, transcription_data.get('content', []), current_y,
            available_height=self.height - current_y - 100  # Reservera för footer
        )
```

#### **4. Integration i: `transcriber.py`**
```python
def _process_transcription(self, transcription_result: Dict, event_type: str, event_data: Dict):
    # Använd TrafficTextOptimizer för initial off-topic-rensning
    text = transcription_result['transcription']
    
    # Säker rensning av uppenbart irrelevant innehåll
    cleaned_text = self.text_optimizer.remove_off_topic_content(text)
    
    # Behåll både original och rensat för jämförelse
    processed['transcription_original'] = text
    processed['transcription_cleaned'] = cleaned_text
    processed['transcription_filtered'] = cleaned_text  # Använd rensad version
```

### **Regelbaserade algoritmer**

#### **Off-topic detection (hög säkerhet)**
```python
MUSIC_PATTERNS = [
    r'(?:låten|sången)\s+heter\s+[\w\s]+',
    r'[\w\s]+,\s+låten\s+heter\s+[\w\s]+',
    r'musik\s+av\s+[\w\s]+',
    r'artist:\s*[\w\s]+',
    r'från\s+albumet\s+[\w\s]+'
]

WEATHER_PATTERNS = [
    r'väder(?:rapport|läge).*?(?:\.|$)',
    r'temperatur.*?grader.*?(?:\.|$)',
    r'(?:regn|snö|sol|moln).*?(?:\.|$)'
]

PROGRAM_PATTERNS = [
    r'P4\s+Stockholm.*?(?:\.|$)',
    r'program.*?(?:\.|$)',
    r'sändning.*?(?:\.|$)'
]
```

#### **Svenska trafikoptimering**
```python
TRAFFIC_COMPRESSIONS = {
    'trafikplats': '',
    'i riktning mot': 'mot',
    'räddningstjänst': 'räddning',
    'är på plats': 'på plats',
    'mycket trög trafik': 'kö',
    'hela vägen': 'vägen',
    'ingen prognos på': 'okänd tid'
}

CRITICAL_INFO_PRIORITY = [
    'väg_namn',      # E4, E20, Rv40
    'plats',         # Hölö, Järna
    'incident_typ',  # olycka, avstängd
    'kö_info',       # köer, längd
    'omledning'      # alternativ väg
]
```

---

## 🧪 **Testplan**

### **Enhets-tester**
```python
def test_text_length_detection():
    # Verifiera att system korrekt identifierar för långa texter
    
def test_off_topic_removal():
    # Testa att musik-annonseringar tas bort säkert
    
def test_traffic_compression():
    # Verifiera svenska trafiktermer förkortas korrekt
    
def test_no_modification_when_fits():
    # Säkerställ att korta texter inte modifieras
```

### **Integration-tester**
```python
def test_with_real_examples():
    # Använd exempel från logs/transcriptions/
    # Verifiera att långa meddelanden förkortas men behåller kritisk info
    
def test_display_rendering():
    # Verifiera att förkortade texter renderas utan trunkering
    
def test_energy_impact():
    # Mät att ingen märkbar energiökning sker
```

### **Användar-acceptans**
- Testa med döva användare att förkortade meddelanden fortfarande är informativa
- Verifiera att ingen kritisk trafikinformation förloras
- Bekräfta att off-topic-rensning inte tar bort relevant info

---

## 🛡️ **Risk-analys och mitigation**

### **Risk 1: För aggressiv förkortning**
- **Risk**: Viktig trafikinformation försvinner
- **Mitigation**: Konservativ approach, graduell förkortning, preserve-lista för kritiska termer

### **Risk 2: Fel-klassning av relevant innehåll**
- **Risk**: Systemet tar bort viktig information som "off-topic"
- **Mitigation**: Hög säkerhetströsklar, whitelist för trafiktermer, extensiva tester

### **Risk 3: Prestanda-påverkan**
- **Risk**: Textanalys gör systemet långsammare
- **Mitigation**: Optimerade regex, cache för vanliga patterns, bara köra vid behov

### **Risk 4: Språkspecifika problem**
- **Risk**: Systemet fungerar bara för perfekt svenska
- **Mitigation**: Robust error-handling, fallback till originaltext vid problem

---

## 📋 **Backup-strategi**

Enligt projektstandard ska följande backup utföras:

```bash
# === BACKUP KOMMANDO (kopiera och kör) ===
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/traffic_shortening_$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
cp content_formatter.py screen_layouts.py transcriber.py "$BACKUP_DIR/"
echo "✅ Backup: $BACKUP_DIR/"
# === SLUTFÖR BACKUP FÖRE FORTSÄTTNING ===
```

### **Backup-metadata**
```bash
cat > "$BACKUP_DIR/README_backup.txt" << EOF
BACKUP INFORMATION
==================
Datum: $(date)
Typ: traffic_shortening
Ändring: Intelligent förkortning av trafikmeddelanden
Original plats: $(pwd)
Säkerhetskopierade filer: content_formatter.py, screen_layouts.py, transcriber.py
Git commit (om tillgänglig): $(git rev-parse HEAD 2>/dev/null || echo "N/A")
EOF
```

---

## 🔄 **Implementation fas-plan**

### **Fas 1: Grundläggande infrastruktur (1-2 dagar)**
1. Skapa `traffic_text_optimizer.py` med basic struktur
2. Implementera text-mätning och fit-detection
3. Lägg till i `content_formatter.py`
4. Grundläggande tester

### **Fas 2: Off-topic rensning (1 dag)**
1. Implementera säker musik-detection
2. Lägg till väder och program-rensning  
3. Testa med verkliga exempel
4. Finjustera säkerhetströsklar

### **Fas 3: Svenska trafikoptimering (2-3 dagar)**
1. Implementera trafikspecifik komprimering
2. Utveckla intelligenta förkortningsregler
3. Prioriterings-algoritm för kritisk information
4. Extensiva tester med långa meddelanden

### **Fas 4: Integration och polering (1 dag)**
1. Integrera med alla display-komponenter
2. Performance-optimering
3. Error-handling och fallbacks
4. Slutlig testning

### **Fas 5: Validation (löpande)**
1. Test med verkliga trafikmeddelanden
2. Användartester med döva
3. Energimätningar
4. Dokumentation

---

## 📊 **Framgångsmått**

### **Tekniska mått**
- ✅ 0% trunkerade meddelanden på display
- ✅ <10% längdreduktion för meddelanden som får plats
- ✅ >90% bevarad kritisk trafikinformation  
- ✅ <50ms extra processing-tid per meddelande

### **Användar-mått**
- ✅ Döva användare kan fortfarande förstå trafikläget
- ✅ Ingen förvirring från för kort information
- ✅ Kritiska detaljer (väg, plats, incident, omledning) alltid synliga

### **System-mått**
- ✅ Ingen märkbar energiökning
- ✅ Robust hantering av språkvariationer
- ✅ Fungerar med befintlig KBWhisper utan modifikation

---

## 💡 **Slutsats**

Detta projekt löser det kritiska problemet med trunkerade trafikmeddelanden genom en smart, regelbaserad approach som:

- **Minimerar risken** för informationsförlust
- **Bevarar energieffektiviteten** (ingen extra AI)  
- **Optimerar för svenska** trafikmeddelanden specifikt
- **Säkerställer tillgänglighet** för döva användare
- **Integrerar smidig** med befintligt system

Projektet är **redo för implementation** och kommer dramatiskt förbättra användarupplevelsen för kritisk trafikinformation utan att kompromissa systemets tillförlitlighet eller energieffektivitet.

---

**Projektansvarig:** AI-assistent  
**Godkänt för implementation:** 2025-06-17  
**Nästa steg:** Skapa backup enligt standard och påbörja Fas 1