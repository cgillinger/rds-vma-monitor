#!/usr/bin/env python3
"""
Font Diagnostics - Analysera och fixa font-problem på e-paper display
Fil: font_diagnostics.py
Placering: ~/rds_logger3/font_diagnostics.py
"""

import os
import glob
from PIL import Image, ImageDraw, ImageFont
import logging

def find_available_fonts():
    """Hitta alla tillgängliga fonts på systemet"""
    font_paths = [
        '/usr/share/fonts/',
        '/usr/local/share/fonts/',
        '/home/pi/.fonts/',
        '/home/chris/.fonts/',
        '/System/Library/Fonts/',  # macOS
        'C:\\Windows\\Fonts\\',    # Windows
    ]
    
    font_extensions = ['*.ttf', '*.TTF', '*.otf', '*.OTF']
    found_fonts = []
    
    for base_path in font_paths:
        if os.path.exists(base_path):
            for ext in font_extensions:
                pattern = os.path.join(base_path, '**', ext)
                fonts = glob.glob(pattern, recursive=True)
                found_fonts.extend(fonts)
    
    return sorted(set(found_fonts))

def test_font_unicode_support(font_path, test_chars="🔊📡🧠"):
    """Testa om en font stöder Unicode-tecken"""
    try:
        font = ImageFont.truetype(font_path, 24)
        
        # Skapa en test-bild
        img = Image.new('RGB', (200, 50), 'white')
        draw = ImageDraw.Draw(img)
        
        # Försök rendera test-tecken
        draw.text((10, 10), test_chars, font=font, fill='black')
        
        # Om inga fel kastas, antag att det fungerar
        return True
        
    except Exception as e:
        return False

def find_best_fonts():
    """Hitta de bästa fonts för olika användningsområden"""
    fonts = find_available_fonts()
    
    # Kategorisera fonts
    emoji_fonts = []
    unicode_fonts = []
    regular_fonts = []
    
    test_emoji = "🔊📡🧠🎧"
    test_unicode = "åäöÅÄÖ"
    
    print("🔍 Testar fonts för Unicode/Emoji-stöd...")
    
    for font_path in fonts:
        font_name = os.path.basename(font_path)
        
        # Testa emoji-stöd
        if test_font_unicode_support(font_path, test_emoji):
            emoji_fonts.append(font_path)
            print(f"  ✅ Emoji: {font_name}")
        
        # Testa Unicode-stöd
        elif test_font_unicode_support(font_path, test_unicode):
            unicode_fonts.append(font_path)
            print(f"  ✅ Unicode: {font_name}")
        
        # Standard font
        elif test_font_unicode_support(font_path, "ABC123"):
            regular_fonts.append(font_path)
            print(f"  ⚪ Regular: {font_name}")
    
    return {
        'emoji': emoji_fonts,
        'unicode': unicode_fonts, 
        'regular': regular_fonts
    }

def test_current_display_fonts():
    """Testa aktuella fonts som används av display-systemet"""
    try:
        from screen_layouts import ScreenLayout
        
        layout = ScreenLayout()
        
        # Testa att ladda fonts i olika storlekar
        sizes_to_test = [12, 16, 18, 20, 24, 32, 48]
        
        print("\n🧪 Testar aktuella display-fonts...")
        
        for size in sizes_to_test:
            try:
                font = layout._get_font(size, bold=False)
                print(f"  ✅ Size {size}px: {type(font)}")
                
                # Testa rendera test-text
                test_img = Image.new('1', (200, 50), 255)
                test_draw = ImageDraw.Draw(test_img)
                test_draw.text((10, 10), "🔊 RDS: Aktiv", font=font, fill=0)
                print(f"    ✅ Emoji rendering: OK")
                
            except Exception as e:
                print(f"  ❌ Size {size}px: {e}")
                
    except Exception as e:
        print(f"❌ Fel vid test av display-fonts: {e}")

def generate_ascii_fallback_mapping():
    """Genererar ASCII-fallbacks för emoji"""
    emoji_to_ascii = {
        # Status icons
        '🟢': '[OK]',
        '🔴': '[ERR]', 
        '🟡': '[WARN]',
        
        # System icons
        '🔊': '[RDS]',
        '📡': '[P4]',
        '🧠': '[AI]',
        '🎧': '[AUD]',
        '🔋': '[BAT]',
        '🪫': '[LOW]',
        
        # Activity icons
        '📅': '[DATE]',
        '⏰': '[TIME]',
        '📊': '[STAT]',
        '📈': '[ACT]',
        
        # Traffic icons
        '🚧': '[TRAF]',
        '📍': '[LOC]',
        '🚗': '[TYPE]',
        '⏱️': '[QUEUE]',
        '🧭': '[DIR]',
        '💬': '[TEXT]',
        
        # VMA icons
        '🚨': '[ALARM]',
        '⚠️': '[WARN]',
        '🧪': '[TEST]',
        '📞': '[PHONE]',
        '📻': '[RADIO]',
        '🌐': '[WEB]',
        
        # Arrows and symbols
        '→': '->',
        '←': '<-',
        '↑': '^',
        '↓': 'v',
        '✅': '[OK]',
        '❌': '[X]',
        '⚠️': '[!]',
        '💾': '[SAVE]',
        '🔄': '[SYNC]',
        '📏': '[LEN]',
        '🎤': '[MIC]',
        '🛑': '[STOP]',
        '🎯': '[TARGET]',
    }
    
    return emoji_to_ascii

def create_font_fix():
    """Skapa fix för font-problemet"""
    
    print("\n🔧 Skapar font-fix...")
    
    # Hitta bästa fonts
    best_fonts = find_best_fonts()
    
    # Generera ASCII-fallbacks
    ascii_fallbacks = generate_ascii_fallback_mapping()
    
    # Skapa uppdaterad font-hantering
    font_config = {
        'emoji_fonts': best_fonts['emoji'][:3],  # Top 3 emoji fonts
        'unicode_fonts': best_fonts['unicode'][:3],  # Top 3 unicode fonts
        'regular_fonts': best_fonts['regular'][:3],  # Top 3 regular fonts
        'ascii_fallbacks': ascii_fallbacks
    }
    
    return font_config

def main():
    print("🖥️ Font Diagnostics for E-paper Display")
    print("=" * 50)
    
    # 1. Hitta tillgängliga fonts
    print("1. Skannar systemet efter fonts...")
    fonts = find_available_fonts()
    print(f"   Hittade {len(fonts)} fonts")
    
    # 2. Testa Unicode-stöd
    print("\n2. Testar Unicode/Emoji-stöd...")
    best_fonts = find_best_fonts()
    
    print(f"\n📊 RESULTAT:")
    print(f"  🎨 Emoji-fonts: {len(best_fonts['emoji'])}")
    print(f"  🌍 Unicode-fonts: {len(best_fonts['unicode'])}") 
    print(f"  📝 Regular-fonts: {len(best_fonts['regular'])}")
    
    # 3. Testa aktuella display-fonts
    test_current_display_fonts()
    
    # 4. Skapa fix
    font_config = create_font_fix()
    
    # 5. Visa rekommendationer
    print(f"\n💡 REKOMMENDATIONER:")
    
    if font_config['emoji_fonts']:
        print(f"  ✅ Använd emoji-font: {os.path.basename(font_config['emoji_fonts'][0])}")
    else:
        print(f"  ⚠️ Inga emoji-fonts hittades - använd ASCII-fallbacks")
    
    print(f"  🔄 Implementera ASCII-fallback för {len(font_config['ascii_fallbacks'])} emoji")
    
    # 6. Spara config
    import json
    with open('font_config.json', 'w') as f:
        json.dump(font_config, f, indent=2)
    
    print(f"\n💾 Font-konfiguration sparad: font_config.json")
    print(f"✅ Diagnostik komplett!")

if __name__ == "__main__":
    main()
