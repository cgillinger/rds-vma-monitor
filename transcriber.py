#!/usr/bin/env python3
"""
Audio Transcriber Module for VMA Project
Uses KBWhisper (Swedish Whisper model) for transcription
Extracts key information from traffic announcements + VMA Support

SAVE AS: ~/rds_logger3/transcriber.py
"""

import os
import re
import time
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ========================================
# CONFIGURATION
# ========================================
PROJECT_DIR = Path(__file__).parent
VENV_PATH = Path.home() / "vma_env"
TRANSCRIPTION_DIR = PROJECT_DIR / "logs" / "transcriptions"

# Ensure transcription directory exists
TRANSCRIPTION_DIR.mkdir(parents=True, exist_ok=True)

# ========================================
# LOGGING SETUP
# ========================================
logger = logging.getLogger(__name__)

# ========================================
# TRANSCRIBER CLASS
# ========================================
class AudioTranscriber:
    """
    Handles audio transcription with KBWhisper
    Extracts key information from Swedish traffic announcements + VMA Support
    """
    
    def __init__(self):
        self.venv_python = str(VENV_PATH / "bin" / "python")
        self.model_name = "KBLab/kb-whisper-medium"  # UPDATED: Using medium model
        self.transcription_count = 0
        self.total_transcribe_time = 0
        self.is_initialized = False
        
        logger.info("AudioTranscriber initialized")
        logger.info(f"Virtual environment: {VENV_PATH}")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Output directory: {TRANSCRIPTION_DIR}")
        
        # Validate setup
        self._validate_setup()
    
    def _validate_setup(self) -> bool:
        """Validate that transcription setup is ready"""
        if not VENV_PATH.exists():
            logger.error(f"Virtual environment not found: {VENV_PATH}")
            return False
        
        if not os.path.exists(self.venv_python):
            logger.error(f"Python executable not found: {self.venv_python}")
            return False
        
        logger.info("✅ Transcriber setup validation passed")
        self.is_initialized = True
        return True
    
    def transcribe_file_async(self, audio_file_path: str, event_type: str, event_data: Dict[str, Any]):
        """
        Start transcription in background thread
        Non-blocking to avoid disrupting RDS monitoring
        """
        if not self.is_initialized:
            logger.error("Transcriber not properly initialized")
            return
        
        # Start transcription in background
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(audio_file_path, event_type, event_data),
            daemon=True
        )
        thread.start()
        logger.info(f"🧠 Transcription started in background for {Path(audio_file_path).name}")
    
    def _transcribe_worker(self, audio_file_path: str, event_type: str, event_data: Dict[str, Any]):
        """
        Worker function that runs transcription in background thread
        """
        try:
            start_time = time.time()
            
            # Perform transcription
            result = self._transcribe_file_sync(audio_file_path)
            
            if result:
                # Process and save results
                processed_result = self._process_transcription(result, event_type, event_data)
                saved_file = self._save_transcription(processed_result, audio_file_path)
                
                total_time = time.time() - start_time
                
                logger.info(f"✅ Transcription completed in {total_time:.1f}s")
                logger.info(f"💾 Saved to: {saved_file.name if saved_file else 'FAILED'}")
                
                # Update statistics
                self.transcription_count += 1
                self.total_transcribe_time += total_time
                
            else:
                logger.error(f"❌ Transcription failed for {Path(audio_file_path).name}")
                
        except Exception as e:
            logger.error(f"Error in transcription worker: {e}")
    
    def _transcribe_file_sync(self, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous transcription using KBWhisper
        Returns transcription result or None on failure
        """
        logger.debug(f"Starting transcription: {Path(audio_file_path).name}")
        
        # KBWhisper transcription script
        transcribe_script = f'''
import sys
import time
from pathlib import Path

try:
    from transformers import pipeline
    
    # Load model
    start_load = time.time()
    whisper = pipeline("automatic-speech-recognition", model="{self.model_name}")
    load_time = time.time() - start_load
    
    # Check if file exists
    audio_file = Path("{audio_file_path}")
    if not audio_file.exists():
        print("ERROR: Audio file not found")
        sys.exit(1)
    
    # Get file size
    file_size = audio_file.stat().st_size
    
    # Transcribe with proper configuration for long audio files
    start_transcribe = time.time()
    result = whisper(str(audio_file), return_timestamps=True)
    transcribe_time = time.time() - start_transcribe
    
    # Output structured result
    print("TRANSCRIPTION_RESULT_START")
    print(f"FILE_SIZE_BYTES: {{file_size}}")
    print(f"MODEL_LOAD_TIME: {{load_time:.3f}}")
    print(f"TRANSCRIBE_TIME: {{transcribe_time:.3f}}")
    print(f"TEXT_LENGTH: {{len(result['text'])}}")
    print("TEXT_START")
    print(result["text"])
    print("TEXT_END")
    print("TRANSCRIPTION_RESULT_END")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        try:
            # Run transcription with timeout
            result = subprocess.run(
                [self.venv_python, "-c", transcribe_script],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max per file
            )
            
            if result.returncode != 0:
                logger.error(f"Transcription process failed: {result.stderr}")
                return None
            
            # Parse output
            return self._parse_transcription_output(result.stdout, audio_file_path)
            
        except subprocess.TimeoutExpired:
            logger.error("Transcription timed out (5 minutes)")
            return None
        except Exception as e:
            logger.error(f"Error running transcription: {e}")
            return None
    
    def _parse_transcription_output(self, output: str, audio_file_path: str) -> Optional[Dict[str, Any]]:
        """Parse structured output from transcription script"""
        lines = output.strip().split('\n')
        
        result = {
            'audio_file': audio_file_path,
            'file_size_bytes': 0,
            'model_load_time': 0,
            'transcribe_time': 0,
            'text_length': 0,
            'transcription': ""
        }
        
        capturing_text = False
        text_lines = []
        
        for line in lines:
            if line.startswith("ERROR:"):
                logger.error(f"Transcription error: {line}")
                return None
            elif line.startswith("FILE_SIZE_BYTES:"):
                result['file_size_bytes'] = int(line.split(":")[1].strip())
            elif line.startswith("MODEL_LOAD_TIME:"):
                result['model_load_time'] = float(line.split(":")[1].strip())
            elif line.startswith("TRANSCRIBE_TIME:"):
                result['transcribe_time'] = float(line.split(":")[1].strip())
            elif line.startswith("TEXT_LENGTH:"):
                result['text_length'] = int(line.split(":")[1].strip())
            elif line == "TEXT_START":
                capturing_text = True
            elif line == "TEXT_END":
                capturing_text = False
            elif capturing_text:
                text_lines.append(line)
        
        result['transcription'] = '\n'.join(text_lines).strip()
        
        if not result['transcription']:
            logger.warning("Empty transcription result")
            return None
        
        return result
    
    def _process_transcription(self, transcription_result: Dict[str, Any], event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process transcription and extract key information
        """
        text = transcription_result['transcription']
        
        # VMA-AWARE: Hybrid approach - filter based on event type
        filtered_text = self.filter_traffic_content(text, event_type)
        
        # Extract key information from filtered text (better accuracy)
        key_info = self.extract_key_info(filtered_text)
        
        # Create processed result with both versions
        processed = {
            'transcription_raw': transcription_result,
            'event_type': event_type,
            'event_data': event_data,
            'transcription_original': text,  # Full transcription (music + speech)
            'transcription_filtered': filtered_text,  # Event-appropriate content
            'extracted_info': key_info,
            'transcription_timestamp': datetime.now().isoformat(),
            'processing_stats': {
                'original_length': len(text),
                'filtered_length': len(filtered_text),
                'content_filtered_out': len(text) - len(filtered_text),
                'key_items_found': len([v for v in key_info.values() if v]),
                'confidence': self._estimate_confidence(filtered_text, key_info)
            }
        }
        
        return processed
    
    def extract_key_info(self, text: str) -> Dict[str, Any]:
        """
        Extract key information from Swedish traffic announcement text
        Works on filtered text for better accuracy
        """
        text_lower = text.lower()
        
        info = {
            'roads': [],
            'locations': [],
            'incident_type': None,
            'direction': None,
            'queue_info': None,
            'alternative_routes': [],
            'time_info': None,
            'severity': None,
            'short_summary': None
        }
        
        # Extract roads (E4, E6, Rv40, etc.)
        road_patterns = [
            r'\b(e\d+)\b',  # E4, E6, etc.
            r'\b(rv\s*\d+)\b',  # Rv40, Rv 40
            r'\b(länsväg\s*\d+)\b',  # Länsväg 123
            r'\b(\d+\s*:an)\b'  # 40:an, etc.
        ]
        
        for pattern in road_patterns:
            matches = re.findall(pattern, text_lower)
            info['roads'].extend([m.upper().replace(' ', '') for m in matches])
        
        # Remove duplicates
        info['roads'] = list(set(info['roads']))
        
        # Extract locations/places
        # Look for "vid X", "i X", "mellan X och Y"
        location_patterns = [
            r'vid\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)',
            r'i\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)',
            r'mellan\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)\s+och\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            if isinstance(matches[0], tuple) if matches else False:
                # "mellan X och Y" case
                for match_tuple in matches:
                    info['locations'].extend(list(match_tuple))
            else:
                info['locations'].extend(matches)
        
        # Extract direction
        if 'norrgående' in text_lower or 'norrut' in text_lower:
            info['direction'] = 'norrgående'
        elif 'södergående' in text_lower or 'söderut' in text_lower:
            info['direction'] = 'södergående'
        elif 'östergående' in text_lower or 'österut' in text_lower:
            info['direction'] = 'östergående'
        elif 'västergående' in text_lower or 'västerut' in text_lower:
            info['direction'] = 'västergående'
        
        # Extract incident type
        incident_types = {
            'olycka': ['olycka', 'krock', 'kollision'],
            'fordon_stannat': ['stannat fordon', 'fordon stannat', 'bil stannat'],
            'vägarbete': ['vägarbete', 'väjarbete', 'arbete'],
            'kö': ['kö', 'köer', 'trafikstörning'],
            'avstängning': ['avstängd', 'stängd', 'blockerad']
        }
        
        for incident_key, keywords in incident_types.items():
            if any(keyword in text_lower for keyword in keywords):
                info['incident_type'] = incident_key
                break
        
        # Extract queue information
        queue_patterns = [
            r'(\d+)\s*(?:km|kilometer)',
            r'kö\s*(?:på\s*)?(\d+)\s*(?:km|kilometer)',
            r'(\d+)\s*minuter?\s*extra'
        ]
        
        for pattern in queue_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['queue_info'] = match.group(1) + ("km" if "km" in pattern else "min")
                break
        
        # Generate short summary for display (will be updated by caller)
        info['short_summary'] = self._generate_short_summary(info, text)
        
        return info
    
    def filter_traffic_content(self, text: str, event_type: str = None) -> str:
        """
        Filter transcription to extract relevant content based on event type
        VMA content should not be filtered - all content is critical
        """
        if not text:
            return ""
        
        # VMA content should not be filtered - all content is critical
        if event_type and 'vma' in event_type.lower():
            return self._clean_vma_text(text)
        
        # Split into sentences and filter each one
        sentences = []
        for delimiter in ['.', '!', '?']:
            text = text.replace(delimiter, '|||SENTENCE_BREAK|||')
        
        potential_sentences = text.split('|||SENTENCE_BREAK|||')
        
        for sentence in potential_sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Too short to be meaningful
                continue
                
            if self._is_traffic_sentence(sentence):
                sentences.append(sentence)
        
        filtered_text = '. '.join(sentences)
        
        # Clean up the result
        filtered_text = self._clean_filtered_text(filtered_text)
        
        logger.debug(f"Text filtering: {len(text)} → {len(filtered_text)} chars")
        return filtered_text
    
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
    
    def _is_traffic_sentence(self, sentence: str) -> bool:
        """Check if a sentence contains traffic information"""
        sentence_lower = sentence.lower()
        
        # Swedish traffic keywords + VMA keywords (ADDITIVE ONLY)
        traffic_keywords = [
            # Roads
            'väg', 'länsväg', 'riksväg', 'motorväg', 'e4', 'e6', 'e18', 'e20', 'rv',
            # Traffic terms
            'trafik', 'trafikinformation', 'trafikmeddelande', 'olycka', 'krock',
            'kö', 'köer', 'bil', 'bilar', 'fordon', 'lastbil', 'motorcykel',
            # Directions & locations
            'norrgående', 'södergående', 'östergående', 'västergående', 
            'norrut', 'söderut', 'österut', 'västerut', 'riktning', 'mot',
            'mellan', 'vid', 'i närheten', 'avfart', 'påfart', 'tunnel', 'bro',
            # Emergency services
            'räddningstjänst', 'polis', 'ambulans', 'brandkår',
            # Road conditions
            'avstängd', 'stängd', 'blockerad', 'växelvis', 'omkörning',
            'vägarbete', 'reparation', 'underhåll', 'snö', 'halka',
            # Places (common Swedish locations)
            'stockholm', 'göteborg', 'malmö', 'uppsala', 'västerås', 
            'örebro', 'linköping', 'norrköping', 'sundsvall', 'umeå',
            'arlanda', 'bromma', 'skavsta', 'landvetter',
            
            # VMA keywords (ADDITIVE ONLY)
            'vma', 'viktigt meddelande', 'allmänheten', 'faran över', 'varning',
            'meddelande', 'sök skydd', 'evakuera', 'kärnkraftverk', 'militär'
        ]
        
        # Must contain at least one traffic keyword
        has_traffic_words = any(keyword in sentence_lower for keyword in traffic_keywords)
        
        if not has_traffic_words:
            return False
        
        # Filter out obvious music/gibberish patterns
        music_indicators = [
            # English nonsense (often from music)
            'problem it', 'just feel', 'matte feeling', 'macaron', 'don\'t down',
            'yeah yeah', 'la la', 'na na', 'oh oh', 'hey hey',
            # Repeated sounds/syllables
            'da da da', 'ba ba ba', 'doo doo', 'dum dum',
            # Non-Swedish gibberish patterns
            'lorem ipsum', 'blah blah', 'test test'
        ]
        
        has_music_indicators = any(indicator in sentence_lower for indicator in music_indicators)
        if has_music_indicators:
            return False
        
        # Check for reasonable word count and structure
        words = sentence.split()
        if len(words) < 3:  # Too short to be meaningful traffic info
            return False
        
        # Check for reasonable Swedish word patterns
        # Traffic sentences should have proper Swedish structure
        has_reasonable_structure = self._has_swedish_structure(sentence_lower)
        
        return has_reasonable_structure
    
    def _has_swedish_structure(self, sentence: str) -> bool:
        """Check if sentence has reasonable Swedish word structure"""
        # Swedish common words that indicate proper language
        swedish_indicators = [
            'en', 'ett', 'är', 'på', 'i', 'av', 'till', 'från', 'med', 'för',
            'som', 'har', 'blir', 'kan', 'ska', 'kommer', 'går', 'finns',
            'det', 'där', 'här', 'när', 'hur', 'vad', 'varför', 'sedan'
        ]
        
        words = sentence.split()
        swedish_word_count = sum(1 for word in words if word.lower() in swedish_indicators)
        
        # At least 15% of words should be common Swedish words for traffic context
        return swedish_word_count >= max(1, len(words) * 0.15)
    
    def _clean_filtered_text(self, text: str) -> str:
        """Clean up the filtered text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Ensure proper sentence ending
        if text and not text.endswith('.'):
            text += '.'
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        return text
    
    def _generate_short_summary(self, info: Dict[str, Any], filtered_text: str) -> str:
        """Generate short summary suitable for e-paper display using filtered text"""
        parts = []
        
        # Add main road
        if info['roads']:
            parts.append(info['roads'][0])
        
        # Add direction
        if info['direction']:
            direction_short = {
                'norrgående': 'N',
                'södergående': 'S',
                'östergående': 'Ö',
                'västergående': 'V'
            }.get(info['direction'], info['direction'][:1].upper())
            parts.append(direction_short)
        
        # Add location
        if info['locations']:
            parts.append(info['locations'][0])
        
        # Add incident
        if info['incident_type']:
            incident_short = {
                'olycka': 'Olycka',
                'fordon_stannat': 'Stannat fordon',
                'vägarbete': 'Vägarbete',
                'kö': 'Kö',
                'avstängning': 'Avstängd'
            }.get(info['incident_type'], info['incident_type'])
            parts.append(f"- {incident_short}")
        
        # Add queue info
        if info['queue_info']:
            parts.append(f", {info['queue_info']}")
        
        summary = " ".join(parts)
        
        # Fallback to first 50 chars of filtered text if extraction failed
        if len(summary) < 10 and filtered_text:
            summary = filtered_text[:50] + "..." if len(filtered_text) > 50 else filtered_text
        
        return summary
    
    def _estimate_confidence(self, text: str, key_info: Dict[str, Any]) -> float:
        """Estimate confidence in extracted information"""
        confidence_factors = []
        
        # Text length factor
        if 20 <= len(text) <= 500:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.4)
        
        # Key information extraction factor
        extracted_count = sum(1 for v in key_info.values() if v)
        if extracted_count >= 3:
            confidence_factors.append(0.9)
        elif extracted_count >= 2:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Text quality factor (has expected Swedish words)
        expected_words = ['trafik', 'väg', 'bil', 'kö', 'olycka', 'fordon']
        found_words = sum(1 for word in expected_words if word in text.lower())
        if found_words >= 2:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _save_transcription(self, processed_result: Dict[str, Any], audio_file_path: str) -> Optional[Path]:
        """Save transcription to structured text file"""
        try:
            # Generate filename
            audio_filename = Path(audio_file_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = TRANSCRIPTION_DIR / f"{audio_filename}_{timestamp}.txt"
            
            # Format content
            content = self._format_transcription_file(processed_result)
            
            # Write file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"💾 Transcription saved: {output_file.name}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error saving transcription: {e}")
            return None
    
    def _format_transcription_file(self, processed_result: Dict[str, Any]) -> str:
        """Format transcription result as structured text file with VMA awareness"""
        raw = processed_result['transcription_raw']
        info = processed_result['extracted_info']
        stats = processed_result['processing_stats']
        event_type = processed_result['event_type']
        
        # Header with event type awareness
        content = [
            f"# VMA Project - Transkription ({event_type.upper()})",
            "=" * 65,
            f"Tidpunkt: {processed_result['transcription_timestamp']}",
            f"Event-typ: {processed_result['event_type']}",
            f"Ljudfil: {Path(raw['audio_file']).name}",
            f"Filstorlek: {raw['file_size_bytes'] / 1024:.1f} KB",
            f"Transkriberings-tid: {raw['transcribe_time']:.2f}s",
            f"AI-modell: KBWhisper Medium",
            ""
        ]
        
        # Processing statistics
        content.extend([
            "## PROCESSING STATISTIK",
            "-" * 30,
            f"Original text: {stats['original_length']} tecken",
            f"Filtrerad text: {stats['filtered_length']} tecken",
            f"Innehåll filtrerat: {stats['content_filtered_out']} tecken",
            f"Konfidensgrad: {stats['confidence']:.1%}",
            ""
        ])
        
        # Extracted key information (from filtered text)
        content.extend([
            "## EXTRAHERAD INFORMATION",
            "-" * 25
        ])
        
        if info['roads']:
            content.append(f"Vägar: {', '.join(info['roads'])}")
        if info['locations']:
            content.append(f"Platser: {', '.join(info['locations'])}")
        if info['direction']:
            content.append(f"Riktning: {info['direction']}")
        if info['incident_type']:
            content.append(f"Typ: {info['incident_type']}")
        if info['queue_info']:
            content.append(f"Köinformation: {info['queue_info']}")
        
        # Short summary for display
        if info['short_summary']:
            content.extend([
                "",
                "## KORTVERSION (för display)",
                "-" * 30,
                info['short_summary']
            ])
        
        # Filtered transcription (event-appropriate content)
        filtered_text = processed_result['transcription_filtered']
        filter_label = "VMA MEDDELANDE" if 'vma' in event_type.lower() else "FILTRERAD TRANSKRIPTION"
        content.extend([
            "",
            f"## {filter_label}",
            "-" * (len(filter_label) + 3),
            filtered_text if filtered_text else "[Inget relevant innehåll extraherat]",
            ""
        ])
        
        # Original full transcription (for reference/debug)
        content.extend([
            "## ORIGINAL TRANSKRIPTION (komplett)",
            "-" * 40,
            processed_result['transcription_original'],
            "",
            "=" * 65,
            f"Genererad av KBWhisper Medium + VMA-medveten filtrering {datetime.now():%Y-%m-%d %H:%M:%S}"
        ])
        
        return '\n'.join(content)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transcriber statistics"""
        avg_time = self.total_transcribe_time / max(1, self.transcription_count)
        
        return {
            'transcriptions_completed': self.transcription_count,
            'total_time_seconds': self.total_transcribe_time,
            'average_time_per_transcription': avg_time,
            'is_initialized': self.is_initialized,
            'model_name': self.model_name,
            'output_directory': str(TRANSCRIPTION_DIR),
            'vma_support': True
        }

# ========================================
# STANDALONE TESTING
# ========================================
def test_transcriber():
    """Test function for standalone usage"""
    transcriber = AudioTranscriber()
    
    # Example test
    test_text = "Nu kommer trafikinformation. På E4 norrgående vid Rotebro har det skett en olycka. Kö på 3 kilometer."
    info = transcriber.extract_key_info(test_text)
    
    print("Test extraction:")
    print(f"Text: {test_text}")
    print(f"Extracted: {info}")

if __name__ == "__main__":
    test_transcriber()