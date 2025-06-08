#!/usr/bin/env python3
"""
Screen Layouts - FIXAD för ny arkitektur med startup/idle modes
Fil: screen_layouts.py (ERSÄTTER befintlig)
Placering: ~/rds_logger3/screen_layouts.py

STÖDJER NYA MODES:
- startup: Startskärm vid systemstart
- idle: Normal drift utan aktiva meddelanden  
- traffic: Trafikmeddelande
- vma: VMA-meddelande
- vma_test: VMA-test

FIXAR:
1. Lägger till startup_layout och idle_layout metoder
2. Uppdaterar create_layout för att hantera alla modes
3. Behåller ren svenska text utan emoji-dubletter
"""

import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Tuple, Optional
import textwrap
import os
import glob

from display_config import DISPLAY_SETTINGS

logger = logging.getLogger(__name__)

class ScreenLayout:
    """
    Skapar faktiska layouter för e-paper display - STÖDER ALLA NYA MODES
    """
    
    def __init__(self):
        self.settings = DISPLAY_SETTINGS
        self.width = self.settings['width']
        self.height = self.settings['height']
        
        # Font-cache för prestanda
        self.font_cache = {}
        
        # Förbättrade font-sökvägar med prioritering
        self.font_search_paths = [
            # Raspberry Pi standard
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            
            # Noto fonts (bra Unicode-stöd)
            '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
            '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
            
            # Ubuntu fonts
            '/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf',
            '/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf',
            
            # Fallback till None för PIL default
            None
        ]
        
        # Hitta och cache tillgängliga fonts vid start
        self.available_fonts = self._find_available_fonts()
        
    def _find_available_fonts(self) -> List[str]:
        """Hitta fonts som faktiskt finns på systemet"""
        available = []
        
        for font_path in self.font_search_paths:
            if font_path is None:
                available.append(None)  # PIL default
                continue
                
            if os.path.exists(font_path):
                available.append(font_path)
                logger.debug(f"Font tillgänglig: {font_path}")
        
        # Om inga fonts hittades, lägg till None som fallback
        if not available:
            available.append(None)
            
        logger.info(f"Hittade {len(available)} tillgängliga fonts")
        return available
    
    def create_layout(self, formatted_content: Dict) -> Image.Image:
        """
        Skapar en komplett layout baserat på formaterat innehåll - ALLA NYA MODES
        """
        try:
            # Skapa tom canvas
            image = Image.new('1', (self.width, self.height), 255)  # Vit bakgrund
            draw = ImageDraw.Draw(image)
            
            mode = formatted_content.get('mode', 'idle')
            sections = formatted_content.get('sections', {})
            
            # UPPDATERAT: Stödjer alla nya modes
            if mode == 'startup':
                self._render_startup_layout(draw, sections)
            elif mode == 'idle':
                self._render_idle_layout(draw, sections)
            elif mode == 'traffic':
                self._render_traffic_layout(draw, sections)
            elif mode == 'vma':
                self._render_vma_layout(draw, sections)
            elif mode == 'vma_test':
                self._render_vma_layout(draw, sections)  # Samma som VMA
            elif mode == 'normal':  # Bakåtkompatibilitet
                self._render_idle_layout(draw, sections)
            else:
                logger.error(f"Okänd layout-mode: {mode}")
                self._render_error_layout(draw, f"Okänd layouttyp: {mode}")
            
            return image
            
        except Exception as e:
            logger.error(f"Fel vid skapande av layout: {e}")
            # Skapa fallback error-layout
            error_image = Image.new('1', (self.width, self.height), 255)
            error_draw = ImageDraw.Draw(error_image)
            self._render_error_layout(error_draw, f"Layout-fel: {str(e)}")
            return error_image
    
    def _render_startup_layout(self, draw: ImageDraw.Draw, sections: Dict):
        """
        NY METOD: Renderar startup-layout för systemstart
        """
        current_y = 20
        
        # Header: "VMA-SYSTEM STARTAR"
        if 'header' in sections:
            header_data = sections['header']
            font = self._get_font(header_data.get('font_size', 28), bold=True)
            
            text = header_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + header_data.get('spacing_after', 25)
        
        # Datum och tid
        if 'datetime' in sections:
            datetime_data = sections['datetime']
            font = self._get_font(datetime_data.get('font_size', 18))
            
            text = datetime_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + datetime_data.get('spacing_after', 25)
        
        # Separator
        self._draw_separator(draw, current_y)
        current_y += 15
        
        # Startup info sektion
        if 'startup_info' in sections:
            startup_data = sections['startup_info']
            current_y = self._render_section_with_title(
                draw, startup_data, current_y, margin=30
            )
        
        # System status sektion
        if 'system_status' in sections:
            status_data = sections['system_status']
            current_y = self._render_section_with_title(
                draw, status_data, current_y, margin=30
            )
        
        # Status footer
        if 'status_footer' in sections:
            footer_data = sections['status_footer']
            # Placera i botten
            footer_y = self.height - 60
            self._draw_separator(draw, footer_y - 10)
            font = self._get_font(footer_data.get('font_size', 14))
            text = footer_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, footer_y), text, font=font, fill=0)
    
    def _render_idle_layout(self, draw: ImageDraw.Draw, sections: Dict):
        """
        NY METOD: Renderar idle-layout för normal drift
        """
        current_y = 20
        
        # Header: "INGA AKTIVA LARM"
        if 'header' in sections:
            header_data = sections['header']
            font = self._get_font(header_data.get('font_size', 24), bold=True)
            
            text = header_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + 25
        
        # Datum och tid
        if 'datetime' in sections:
            datetime_data = sections['datetime']
            font = self._get_font(datetime_data.get('font_size', 18))
            
            text = datetime_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + datetime_data.get('spacing_after', 20)
        
        # Separator
        self._draw_separator(draw, current_y)
        current_y += 15
        
        # Systemstatus sektion
        if 'system_status' in sections:
            status_data = sections['system_status']
            current_y = self._render_section_with_title(
                draw, status_data, current_y, margin=40
            )
        
        # Separator mellan sektioner
        self._draw_separator(draw, current_y)
        current_y += 15
        
        # Aktivitetssammanfattning
        if 'activity' in sections:
            activity_data = sections['activity']
            current_y = self._render_section_with_title(
                draw, activity_data, current_y, margin=40
            )
        
        # Status footer
        if 'status_footer' in sections:
            footer_data = sections['status_footer']
            # Placera i botten
            footer_y = self.height - 60
            self._draw_separator(draw, footer_y - 10)
            font = self._get_font(footer_data.get('font_size', 14))
            text = footer_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, footer_y), text, font=font, fill=0)
    
    def _render_traffic_layout(self, draw: ImageDraw.Draw, sections: Dict):
        """
        Renderar trafikmeddelande-layout - OFÖRÄNDRAD
        """
        current_y = 15
        
        # Traffic header med bakgrund
        if 'header' in sections:
            header_data = sections['header']
            font = self._get_font(header_data.get('font_size', 28), bold=True)
            
            text = header_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_height = bbox[3] - bbox[1]
            
            # Bakgrundsfärg för header (grå rektangel)
            if header_data.get('background'):
                rect_height = text_height + 20
                draw.rectangle([10, current_y-5, self.width-10, current_y + rect_height], 
                             fill=200, outline=0, width=2)
            
            # Centrera text
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, current_y + 10), text, font=font, fill=0)
            current_y += text_height + 35
        
        # Nyckelinformation
        if 'key_info' in sections:
            key_info_data = sections['key_info']
            font = self._get_font(key_info_data.get('font_size', 18), bold=True)
            
            margin = 30
            for info_line in key_info_data.get('content', []):
                draw.text((margin, current_y), info_line, font=font, fill=0)
                bbox = self._get_text_bbox(draw, info_line, font)
                current_y += (bbox[3] - bbox[1]) + 8
            
            current_y += key_info_data.get('spacing_after', 15)
        
        # Separator
        self._draw_separator(draw, current_y)
        current_y += 15
        
        # Fullständig transkription
        if 'transcription' in sections:
            transcription_data = sections['transcription']
            current_y = self._render_section_with_title(
                draw, transcription_data, current_y, margin=30
            )
        
        # Status information
        if 'status_info' in sections:
            status_data = sections['status_info']
            current_y = self._render_section_content(
                draw, status_data.get('content', []), current_y, 
                font_size=status_data.get('font_size', 14), margin=30
            )
        
        # Status footer
        if 'status_footer' in sections:
            footer_data = sections['status_footer']
            footer_y = self.height - 60
            self._draw_separator(draw, footer_y - 10)
            font = self._get_font(footer_data.get('font_size', 14))
            text = footer_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, footer_y), text, font=font, fill=0)
    
    def _render_vma_layout(self, draw: ImageDraw.Draw, sections: Dict):
        """
        Renderar VMA-layout - OFÖRÄNDRAD
        """
        current_y = 20
        
        # Huvudrubrik
        if 'main_header' in sections:
            header_data = sections['main_header']
            font = self._get_font(header_data.get('font_size', 42), bold=True)
            
            text = header_data['text']
            # Word wrap för lång rubrik
            if len(text) > 30:
                wrapped_lines = textwrap.wrap(text, width=30)
            else:
                wrapped_lines = [text]
            
            for line in wrapped_lines:
                bbox = self._get_text_bbox(draw, line, font)
                text_width = bbox[2] - bbox[0]
                x = (self.width - text_width) // 2
                
                draw.text((x, current_y), line, font=font, fill=0)
                current_y += bbox[3] - bbox[1] + 5
            
            current_y += header_data.get('spacing_after', 10)
        
        # Underrubrik
        if 'sub_header' in sections:
            sub_data = sections['sub_header']
            font = self._get_font(sub_data.get('font_size', 28), bold=True)
            
            text = sub_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + sub_data.get('spacing_after', 15)
        
        # Alert level
        if 'alert_level' in sections:
            alert_data = sections['alert_level']
            font = self._get_font(alert_data.get('font_size', 20), bold=True)
            
            text = alert_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            # Rektangel runt alert level
            draw.rectangle([x-10, current_y-5, x+text_width+10, current_y+bbox[3]-bbox[1]+5], 
                         outline=0, width=3)
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + alert_data.get('spacing_after', 10)
        
        # Tidsstämpel
        if 'timestamp' in sections:
            timestamp_data = sections['timestamp']
            font = self._get_font(timestamp_data.get('font_size', 18))
            
            text = timestamp_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            draw.text((x, current_y), text, font=font, fill=0)
            current_y += bbox[3] - bbox[1] + timestamp_data.get('spacing_after', 20)
        
        # Separator
        self._draw_separator(draw, current_y, thick=True)
        current_y += 20
        
        # VMA-innehåll
        if 'vma_content' in sections:
            vma_data = sections['vma_content']
            current_y = self._render_section_with_title(
                draw, vma_data, current_y, margin=20, 
                available_height=self.height - current_y - 100
            )
        
        # Kontaktinformation
        if 'contact' in sections:
            contact_data = sections['contact']
            contact_y = self.height - 80
            self._draw_separator(draw, contact_y - 10, thick=True)
            self._render_section_content(
                draw, contact_data.get('content', []), contact_y + 10,
                font_size=contact_data.get('font_size', 16), margin=20
            )
        
        # Status footer
        if 'status_footer' in sections:
            footer_data = sections['status_footer']
            footer_y = self.height - 40
            font = self._get_font(footer_data.get('font_size', 12))
            text = footer_data['text']
            bbox = self._get_text_bbox(draw, text, font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, footer_y), text, font=font, fill=0)
    
    def _render_section_with_title(self, draw: ImageDraw.Draw, section_data: Dict, 
                                 start_y: int, margin: int = 30, 
                                 available_height: Optional[int] = None) -> int:
        """
        Renderar en sektion med titel och innehåll
        """
        current_y = start_y
        
        # Titel om den finns
        if 'title' in section_data:
            title_font = self._get_font(section_data.get('font_size', 18), bold=True)
            title_text = section_data['title']
            draw.text((margin, current_y), title_text, font=title_font, fill=0)
            
            bbox = self._get_text_bbox(draw, title_text, title_font)
            current_y += bbox[3] - bbox[1] + 10
        
        # Innehåll
        content = section_data.get('content', [])
        if content:
            current_y = self._render_section_content(
                draw, content, current_y, 
                font_size=section_data.get('font_size', 16),
                margin=margin,
                word_wrap=section_data.get('word_wrap', False),
                line_spacing=section_data.get('line_spacing', 1.2),
                available_height=available_height
            )
        
        return current_y + section_data.get('spacing_after', 20)
    
    def _render_section_content(self, draw: ImageDraw.Draw, content: List[str], 
                              start_y: int, font_size: int = 16, margin: int = 30,
                              word_wrap: bool = False, line_spacing: float = 1.2,
                              available_height: Optional[int] = None) -> int:
        """
        Renderar innehållstext med ordbrytning och radavstånd
        """
        current_y = start_y
        font = self._get_font(font_size)
        
        max_width = self.width - (margin * 2)
        
        for item in content:
            if not item:  # Hoppa över tomma strängar
                continue
            
            clean_item = str(item)
                
            if word_wrap and len(clean_item) > 60:
                # Beräkna optimal radbredd baserat på font
                chars_per_line = max_width // (font_size * 0.6)
                wrapped_lines = textwrap.wrap(clean_item, width=int(chars_per_line))
            else:
                wrapped_lines = [clean_item]
            
            for line in wrapped_lines:
                # Kontrollera om vi har plats kvar
                if available_height and (current_y - start_y) > available_height:
                    draw.text((margin, current_y), "...", font=font, fill=0)
                    return current_y + 20
                
                draw.text((margin, current_y), line, font=font, fill=0)
                
                bbox = self._get_text_bbox(draw, line, font)
                line_height = (bbox[3] - bbox[1]) * line_spacing
                current_y += int(line_height)
        
        return current_y
    
    def _draw_separator(self, draw: ImageDraw.Draw, y: int, thick: bool = False):
        """Rita horisontell separator-linje"""
        width = 3 if thick else 1
        margin = 40 if thick else 60
        draw.line([margin, y, self.width - margin, y], fill=0, width=width)
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Hämta font från cache eller ladda ny med robust felhantering"""
        cache_key = f"{size}_{bold}"
        
        if cache_key in self.font_cache:
            return self.font_cache[cache_key]
        
        font_loaded = False
        font = None
        
        for font_path in self.available_fonts:
            try:
                if font_path is None:
                    font = ImageFont.load_default()
                    font_loaded = True
                    logger.debug(f"Laddar default font för storlek {size}")
                    break
                else:
                    actual_path = font_path
                    if bold and 'Bold' not in font_path and font_path.endswith('.ttf'):
                        bold_path = font_path.replace('.ttf', '-Bold.ttf')
                        if os.path.exists(bold_path):
                            actual_path = bold_path
                    
                    font = ImageFont.truetype(actual_path, size)
                    font_loaded = True
                    logger.debug(f"Laddar font: {os.path.basename(actual_path)} storlek {size}")
                    break
                    
            except Exception as e:
                logger.debug(f"Kunde inte ladda font {font_path}: {e}")
                continue
        
        if not font_loaded or font is None:
            logger.warning(f"Kunde inte ladda någon font för storlek {size}, använder PIL default")
            font = ImageFont.load_default()
        
        self.font_cache[cache_key] = font
        return font
    
    def _get_text_bbox(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int, int, int]:
        """Hämta text bounding box med fallback för äldre PIL-versioner"""
        try:
            return draw.textbbox((0, 0), text, font=font)
        except AttributeError:
            try:
                size = draw.textsize(text, font=font)
                return (0, 0, size[0], size[1])
            except:
                return (0, 0, len(text) * 10, 20)
    
    def _render_error_layout(self, draw: ImageDraw.Draw, error_message: str):
        """Renderar en enkel felmeddelande-layout"""
        font_large = self._get_font(32, bold=True)
        font_normal = self._get_font(18)
        
        # Error header
        error_text = "SYSTEM-FEL"
        bbox = self._get_text_bbox(draw, error_text, font_large)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2
        draw.text((x, 100), error_text, font=font_large, fill=0)
        
        # Error message
        y_pos = 200
        wrapped_lines = textwrap.wrap(error_message, width=60)
        for line in wrapped_lines:
            bbox = self._get_text_bbox(draw, line, font_normal)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, y_pos), line, font=font_normal, fill=0)
            y_pos += bbox[3] - bbox[1] + 10
        
        # Instructions
        instruction = "Kontrollera systemloggar för mer information"
        bbox = self._get_text_bbox(draw, instruction, font_normal)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2
        draw.text((x, y_pos + 40), instruction, font=font_normal, fill=0)

    def get_layout_info(self, formatted_content: Dict) -> Dict:
        """Returnerar information om layout utan att rendera den"""
        mode = formatted_content.get('mode', 'idle')
        sections = formatted_content.get('sections', {})
        
        estimated_elements = len(sections)
        estimated_height = 0
        
        for section_name, section_data in sections.items():
            if 'content' in section_data:
                estimated_height += len(section_data['content']) * 25
            else:
                estimated_height += 40
        
        return {
            'mode': mode,
            'estimated_height': min(estimated_height, self.height),
            'complexity': estimated_elements,
            'sections_count': len(sections),
            'available_fonts': len(self.available_fonts),
            'requires_word_wrap': any(
                section.get('word_wrap', False) 
                for section in sections.values()
            ),
            'has_long_content': any(
                len(str(section.get('content', ''))) > 200
                for section in sections.values()
            )
        }

if __name__ == "__main__":
    # Test av uppdaterad screen layout
    print("🖥️ Test av UPPDATERAD Screen Layout - STÖDER ALLA NYA MODES")
    print("=" * 70)
    
    layout = ScreenLayout()
    
    print(f"✅ Tillgängliga fonts: {len(layout.available_fonts)}")
    
    # Test nya startup mode
    test_startup_content = {
        'mode': 'startup',
        'priority': 100,
        'sections': {
            'header': {
                'text': 'VMA-SYSTEM STARTAR',
                'font_size': 28,
                'spacing_after': 25
            },
            'datetime': {
                'text': 'FREDAG 07 JUNI 2025     20:52',
                'font_size': 18,
                'spacing_after': 25
            },
            'startup_info': {
                'title': 'SYSTEMINITIALISERING',
                'content': [
                    'Systemet initialiseras...',
                    'Lyssnar efter VMA och trafikmeddelanden',
                    'Sveriges Radio P4 Stockholm 103.3 MHz'
                ],
                'font_size': 16
            },
            'status_footer': {
                'text': 'System OK • 20:52',
                'font_size': 14
            }
        }
    }
    
    try:
        image = layout.create_layout(test_startup_content)
        print(f"✅ STARTUP Layout skapad: {image.size}")
        
        # Test idle mode
        test_idle_content = {
            'mode': 'idle',
            'sections': {
                'header': {'text': 'INGA AKTIVA LARM'},
                'status_footer': {'text': 'System OK • 20:52'}
            }
        }
        
        idle_image = layout.create_layout(test_idle_content)
        print(f"✅ IDLE Layout skapad: {idle_image.size}")
        
        # Spara test-bilder
        try:
            image.save('/tmp/test_startup_layout.png')
            idle_image.save('/tmp/test_idle_layout.png')
            print("💾 Test-bilder sparade: /tmp/test_*_layout.png")
        except:
            print("ℹ️ Kunde inte spara test-bilder")
            
    except Exception as e:
        print(f"❌ Fel vid test: {e}")
    
    print("\n✅ UPPDATERAD Screen Layout test slutförd - STÖDER startup/idle/traffic/vma modes!")
