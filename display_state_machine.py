#!/usr/bin/env python3
"""
HOTFIX Display State Machine - Fixar start_time uppdatering för nya trafikmeddelanden
Fil: display_state_machine.py (ERSÄTTER befintlig - HOTFIX VERSION)
Placering: ~/rds_logger3/display_state_machine.py

HOTFIX PROBLEM:
- Nya trafikmeddelanden medan redan i TRAFFIC state uppdaterade inte start_time
- "STARTAD: HH:MM" visade alltid första trafikmeddelandes tid
- _should_update_content() hanterade inte 'traffic_start' events

HOTFIX LÖSNING:
- _should_update_content() hanterar nu 'traffic_start' events
- _update_current_content() uppdaterar start_time och event_start_time
- Nya trafikmeddelanden får korrekt ny start_time även i samma state

FÖRENKLADE STATES (ingen night mode):
- STARTUP: Vid systemstart tills första event
- TRAFFIC: Trafikmeddelande (persistent)
- VMA: VMA-meddelande (persistent)  
- IDLE: Väntar på events

INGEN night mode - håller det enkelt för krisberedskap!
"""

import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class DisplayState(Enum):
    """FÖRENKLADE Display-lägen"""
    STARTUP = "startup"           # Startskärm tills första event
    TRAFFIC = "traffic"           # Trafikmeddelande (persistent)
    VMA = "vma"                   # VMA-meddelande (persistent)  
    VMA_TEST = "vma_test"         # VMA-test (persistent)
    IDLE = "idle"                 # Väntar på events

@dataclass
class DisplayContent:
    """Data för aktuellt display-innehåll"""
    state: DisplayState
    primary_data: Dict[str, Any]
    last_update: datetime
    event_start_time: Optional[datetime] = None
    transcription: Optional[Dict] = None
    
class DisplayStateMachine:
    """
    HOTFIX Event-driven state machine - Fixar start_time för nya trafikmeddelanden
    """
    
    def __init__(self):
        # Initial state
        self.current_state = DisplayState.STARTUP
        self.current_content = DisplayContent(
            state=DisplayState.STARTUP,
            primary_data={},
            last_update=datetime.now()
        )
        
        # State history för debugging
        self.state_history = [(DisplayState.STARTUP, datetime.now())]
        
        logger.info("🎯 HOTFIX DisplayStateMachine initialiserad")
        logger.info(f"Initial state: {self.current_state.value}")
        logger.info("📋 States: STARTUP → TRAFFIC/VMA → IDLE → repeat")
        logger.info("🩹 HOTFIX: Nya trafikmeddelanden uppdaterar start_time korrekt")
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Processa event och uppdatera state
        Returnerar True om display behöver uppdateras
        """
        old_state = self.current_state
        new_state = self._determine_new_state(event_type, event_data)
        
        if new_state != old_state:
            self._transition_to_state(new_state, event_type, event_data)
            logger.info(f"State transition: {old_state.value} → {new_state.value} (event: {event_type})")
            return True
        else:
            # Samma state, men uppdatera content om relevant
            if self._should_update_content(event_type, event_data):
                self._update_current_content(event_type, event_data)
                logger.info(f"Content update i {self.current_state.value} (event: {event_type})")
                return True
        
        return False
    
    def get_current_display_mode(self) -> str:
        """Returnera display-mode för content formatter"""
        state_to_mode = {
            DisplayState.STARTUP: 'startup',
            DisplayState.TRAFFIC: 'traffic', 
            DisplayState.VMA: 'vma',
            DisplayState.VMA_TEST: 'vma_test',
            DisplayState.IDLE: 'idle'
        }
        return state_to_mode.get(self.current_state, 'idle')
    
    def get_current_content(self) -> DisplayContent:
        """Returnera aktuellt display-innehåll"""
        return self.current_content
    
    def get_status_info(self) -> Dict[str, Any]:
        """Returnera status-info för feedback"""
        now = datetime.now()
        
        # Beräkna duration för current state
        duration = now - self.current_content.last_update
        duration_str = self._format_duration(duration)
        
        return {
            'current_state': self.current_state.value,
            'last_update': now.strftime('%H:%M'),
            'state_duration': duration_str,
            'system_status': 'OK'
        }
    
    def _determine_new_state(self, event_type: str, event_data: Dict[str, Any]) -> DisplayState:
        """FÖRENKLAD: Bestäm ny state baserat på event"""
        
        # VMA har högsta prioritet
        if event_type == 'vma_start':
            return DisplayState.VMA
        elif event_type == 'vma_test_start':
            return DisplayState.VMA_TEST
        
        # Traffic events
        elif event_type == 'traffic_start':
            return DisplayState.TRAFFIC
        
        # END events - enkelt: gå till IDLE
        elif event_type in ['traffic_end', 'vma_end', 'vma_test_end']:
            return DisplayState.IDLE
        
        # Andra events förändrar inte state
        return self.current_state
    
    def _transition_to_state(self, new_state: DisplayState, event_type: str, event_data: Dict[str, Any]):
        """Genomför state transition"""
        old_state = self.current_state
        
        self.current_state = new_state
        self.current_content = DisplayContent(
            state=new_state,
            primary_data=event_data.copy(),
            last_update=datetime.now(),
            event_start_time=event_data.get('start_time') or datetime.now(),
            transcription=event_data.get('transcription')
        )
        
        # Lägg till i history
        self.state_history.append((new_state, datetime.now()))
        
        # Behåll bara senaste 20 transitions
        if len(self.state_history) > 20:
            self.state_history = self.state_history[-20:]
    
    def _should_update_content(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        HOTFIX: Ska vi uppdatera innehåll utan att byta state?
        
        TILLAGT: Hantera 'traffic_start' för att uppdatera start_time 
        när nya trafikmeddelanden kommer medan redan i TRAFFIC state
        """
        # HOTFIX: Uppdatera för nya trafikmeddelanden i samma state
        if event_type == 'traffic_start' and self.current_state == DisplayState.TRAFFIC:
            logger.info("🩹 HOTFIX: Nytt trafikmeddelande medan redan i TRAFFIC - uppdaterar start_time")
            return True
        
        # HOTFIX: Uppdatera för nya VMA i samma state
        if event_type in ['vma_start', 'vma_test_start'] and self.current_state in [DisplayState.VMA, DisplayState.VMA_TEST]:
            logger.info("🩹 HOTFIX: Nytt VMA medan redan i VMA - uppdaterar start_time")
            return True
        
        # Uppdatera om vi får ny transkription för samma event
        if event_type == 'transcription_complete' and self.current_state == DisplayState.TRAFFIC:
            return True
        
        # Uppdatera periodisk status
        if event_type == 'status_update':
            return True
        
        return False
    
    def _update_current_content(self, event_type: str, event_data: Dict[str, Any]):
        """
        HOTFIX: Uppdatera innehåll i current state
        
        TILLAGT: Hantera start_time uppdatering för nya events i samma state
        """
        # HOTFIX: Uppdatera start_time för nya trafikmeddelanden
        if event_type == 'traffic_start':
            new_start_time = event_data.get('start_time', datetime.now())
            logger.info(f"🩹 HOTFIX: Uppdaterar start_time från {self.current_content.event_start_time} till {new_start_time}")
            
            # Uppdatera både event_start_time och primary_data
            self.current_content.event_start_time = new_start_time
            self.current_content.primary_data.update(event_data)
            self.current_content.primary_data['start_time'] = new_start_time
        
        # HOTFIX: Uppdatera start_time för nya VMA
        elif event_type in ['vma_start', 'vma_test_start']:
            new_start_time = event_data.get('start_time', datetime.now())
            logger.info(f"🩹 HOTFIX: Uppdaterar VMA start_time från {self.current_content.event_start_time} till {new_start_time}")
            
            # Uppdatera både event_start_time och primary_data
            self.current_content.event_start_time = new_start_time
            self.current_content.primary_data.update(event_data)
            self.current_content.primary_data['start_time'] = new_start_time
        
        # Ursprungliga uppdateringar
        elif event_type == 'transcription_complete':
            self.current_content.transcription = event_data.get('transcription')
        
        # Uppdatera andra data
        if event_type not in ['traffic_start', 'vma_start', 'vma_test_start']:
            self.current_content.primary_data.update(event_data)
        
        # Alltid uppdatera last_update timestamp
        self.current_content.last_update = datetime.now()
    
    def _format_duration(self, duration) -> str:
        """Formatera varaktighet som sträng"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Debug information för troubleshooting"""
        return {
            'current_state': self.current_state.value,
            'content_last_update': self.current_content.last_update.isoformat(),
            'event_start_time': self.current_content.event_start_time.isoformat() if self.current_content.event_start_time else None,
            'has_transcription': self.current_content.transcription is not None,
            'primary_data_start_time': self.current_content.primary_data.get('start_time'),
            'recent_transitions': [
                (state.value, ts.strftime('%H:%M:%S')) 
                for state, ts in self.state_history[-5:]
            ]
        }

# Singleton instance för global access
display_state_machine = DisplayStateMachine()

if __name__ == "__main__":
    # Test av HOTFIX state machine
    import time as time_module
    
    print("🩹 Test av HOTFIX DisplayStateMachine - start_time fix")
    print("=" * 60)
    
    sm = DisplayStateMachine()
    
    # Test HOTFIX scenario
    test_events = [
        ('traffic_start', {'start_time': datetime.now(), 'location': 'E4 Stockholm'}),
        ('traffic_start', {'start_time': datetime.now(), 'location': 'E20 Göteborg'}),  # HOTFIX test
        ('transcription_complete', {'transcription': {'text': 'Test transkription'}}),
        ('traffic_end', {}),
    ]
    
    for event_type, event_data in test_events:
        print(f"\n📡 Event: {event_type}")
        if 'start_time' in event_data:
            print(f"  Event start_time: {event_data['start_time'].strftime('%H:%M:%S')}")
        
        needs_update = sm.process_event(event_type, event_data)
        
        print(f"State: {sm.current_state.value}")
        print(f"Mode: {sm.get_current_display_mode()}")
        print(f"Needs update: {needs_update}")
        print(f"Content start_time: {sm.current_content.event_start_time.strftime('%H:%M:%S') if sm.current_content.event_start_time else 'None'}")
        
        time_module.sleep(1)
    
    print(f"\n📊 Debug info: {sm.get_debug_info()}")
    print("\n✅ HOTFIX State Machine - start_time uppdateras nu korrekt för nya trafikmeddelanden!")
