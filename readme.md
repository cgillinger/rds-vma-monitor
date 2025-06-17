# VMA Emergency Broadcast Detection System

**Offline system for detecting, recording and transcribing VMA (Important Public Announcements) from Swedish FM radio**

**Status: Production ready system with automatic startup**

---

## What is this system

This system automatically monitors Swedish Radio P4 for emergency broadcasts (VMA - Viktigt Meddelande till Allmanheten) and traffic announcements. It uses FM radio and RDS (Radio Data System) signals to detect when important messages are broadcast, then records the audio and transcribes it using AI.

**Critical advantage: No internet or mobile connection required.** The system works completely offline using only FM radio reception. This makes it invaluable during emergencies when internet and mobile networks may be unreliable or completely unavailable. As long as you have adequate FM radio reception, the system will continue to monitor for emergency broadcasts.

The system is designed for deaf and hearing-impaired individuals who need access to critical safety information during emergencies, but is useful for anyone wanting reliable emergency information independent of internet infrastructure.

**Key features:**
- Automatic detection of VMA emergency broadcasts (PTY codes 30/31)
- Real-time audio recording and Swedish AI transcription
- Visual display on e-paper screen with automatic priority switching
- Extremely low power consumption for battery operation
- Session backup system ensures no data loss
- Automatic startup and self-maintenance
- **Works completely offline - only needs FM radio reception**

**Designed for Swedish conditions:**
- Monitors Sveriges Radio P4 (103.3 MHz Stockholm)
- Uses KBWhisper AI model optimized for Swedish language
- Follows Swedish emergency broadcast standards
- Can be adapted for other countries with similar RDS systems

---

## Hardware Requirements

### Required Components

**System tested on: Raspberry Pi 5 8GB RAM running Raspberry Pi OS**

| Component | Recommended Model | Price (SEK) | Notes |
|-----------|-------------------|-------------|-------|
| **Computer** | Raspberry Pi 5 (8GB RAM) | 1200 | Verified working configuration |
| **SDR Radio** | RTL-SDR Blog V4 | 400 | Requires special drivers |
| **Audio Interface** | Jabra EVOLVE 30 II USB headset | 800 | USB audio device needed |
| **Display** | Waveshare 4.26" E-Paper HAT | 600 | 800x480 pixels |
| **Antenna** | Telescopic antenna (SMA connector) | 100 | For FM reception |
| **Storage** | MicroSD 64GB+ (Class 10) | 200 | High-speed card required |

**Total cost: ~3300 SEK**

### Compatible Alternatives

**Computer alternatives:**
- Raspberry Pi 4 (4GB+) - Lower performance but functional
- Any Linux computer with USB ports and GPIO for display

**SDR alternatives:**
- RTL-SDR Blog V3 - Older version, may work
- Other RTL2832U-based dongles - Compatibility varies

**Audio alternatives:**
- Any USB audio interface or sound card
- Built-in audio may work but USB recommended

**Display alternatives:**
- Any Waveshare e-paper display - Requires code modifications
- Can run without display using log files only

### Critical Hardware Notes

**RTL-SDR Blog V4:**
- Must use drivers from rtlsdrblog/rtl-sdr-blog repository
- Standard rtl-sdr drivers will NOT work
- Verified working at 171kHz sample rate

**E-paper Display:**
- Requires SPI interface enabled on Raspberry Pi
- Uses minimal power (0W standby, 1W during updates)
- Updates take ~4 seconds (normal for e-paper technology)

---

## Reception Setup and Optimization

### Critical Reception Requirements

**This system only works with adequate FM radio reception.** Since it operates completely offline, good FM signal quality is essential for reliable emergency detection.

### P4 Frequencies by Region

**Major Swedish cities and their P4 frequencies:**
- Stockholm: 103.3 MHz (default in config.py)
- Gothenburg: 104.7 MHz
- Malmo: 101.8 MHz
- Uppsala: 105.0 MHz
- Vasteras: 102.8 MHz
- Orebro: 105.5 MHz
- Norrkoping: 106.1 MHz
- Helsingborg: 104.3 MHz
- Jonkoping: 105.9 MHz
- Umea: 102.1 MHz

**Find your local P4 frequency at:** sverigesradio.se/sida/artikel.aspx?programid=2054&artikel=5465699

### RTL-SDR Configuration Parameters

**Key settings in config.py:**
```python
FREQUENCY = 103300000    # Your local P4 frequency in Hz
SAMPLE_RATE = 171000     # 171kHz - optimal for RDS decoding
GAIN = 30                # 30dB - adjust based on signal strength
PPM_CORRECTION = 50      # Frequency correction - adjust for your device
```

**Gain adjustment guidelines:**
- **Strong signal (close to transmitter):** Start with gain 20-30
- **Medium signal (suburban):** Try gain 30-40
- **Weak signal (rural/distant):** May need gain 40-49
- **Too strong signal:** Causes distortion - reduce gain
- **Too weak signal:** RDS detection fails - increase gain or improve antenna

### Antenna Setup and Placement

**Antenna types in order of effectiveness:**
1. **Outdoor FM antenna** - Best performance, requires installation
2. **Telescopic antenna (included)** - Good for most situations
3. **Simple wire antenna** - 75cm wire works as emergency backup

**Antenna placement tips:**
- **Height matters:** Higher placement improves reception
- **Avoid interference:** Keep away from computers, power supplies, LED lights
- **Orientation:** Try different angles for best signal
- **Indoor vs outdoor:** Outdoor always better, but indoor often sufficient

**Test your reception:**
```bash
# Test signal strength and quality
rtl_fm -f 103.3M -s 200000 -g 30 - | aplay -r 22050 -f S16_LE
# You should hear clear P4 audio. Press Ctrl+C to stop.
```

### Reception Troubleshooting

**Poor RDS detection (system not responding to events):**
1. Check signal strength: Run the audio test above
2. Adjust antenna position and orientation
3. Try different gain values (edit GAIN in config.py)
4. Check for local interference sources
5. Verify you have the correct P4 frequency

**Audio quality issues:**
1. Reduce gain if audio is distorted (crackling sounds)
2. Increase gain if audio is weak or noisy
3. Check antenna connections are secure
4. Move antenna away from interference sources

**PPM correction for frequency accuracy:**
```bash
# Test frequency accuracy with known strong station
rtl_fm -f 103.3M -s 200000 -g 30 -p 0 - | aplay -r 22050 -f S16_LE
# If audio sounds off-pitch, adjust PPM_CORRECTION in config.py
# Typical values: -50 to +50 for most RTL-SDR devices
```

### Regional Adaptation

**For use outside Sweden:**
1. Find your local emergency broadcast frequency
2. Research local RDS emergency codes (may differ from PTY 30/31)
3. Update config.py with local frequency
4. May need to modify RDS detection logic in rds_detector.py
5. Consider switching to standard Whisper for local language support

### Signal Quality Monitoring

**Check reception quality after installation:**
```bash
# View RDS data being received
tail -f logs/rds_continuous_$(date +%Y%m%d).log

# Look for these indicators:
# - Regular RDS updates (every few seconds)
# - Correct station PI code
# - Clean program service name (PS field)
# - Regular radiotext updates (RT field)
```

**Minimum signal quality requirements:**
- RDS data should appear consistently (not sporadic)
- Audio should be clear without major static
- System should detect TA flags during actual traffic announcements
- No frequent "No RTL-SDR device found" errors in logs

---

## Installation Guide

**This guide has been tested on Raspberry Pi 5 8GB RAM. All commands can be copy-pasted directly into terminal.**

### Step 1: Operating System Setup

**Install Raspberry Pi OS (Bullseye or later) on your Pi 5**

```bash
# Enable SPI for e-paper display
sudo raspi-config
```
Select: Interface Options → SPI → Enable → Finish

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install required system packages
sudo apt install -y git python3 python3-pip python3-venv cmake build-essential libusb-1.0-0-dev pkg-config meson ninja-build sox alsa-utils
```

### Step 2: Install RTL-SDR Blog V4 Drivers

**Critical: Must use RTL-SDR Blog drivers, not standard rtl-sdr**

```bash
cd ~
git clone https://github.com/rtlsdrblog/rtl-sdr-blog
cd rtl-sdr-blog
mkdir build
cd build
cmake ../ -DINSTALL_UDEV_RULES=ON
make
sudo make install
sudo ldconfig
```

**Verify RTL-SDR installation:**
```bash
rtl_test -t
```
**Expected output:** "RTL-SDR Blog V4 Detected"

**If test fails:**
- Check USB connection
- Replug RTL-SDR device
- Verify it's RTL-SDR Blog V4 (other versions may not work)

### Step 3: Install Redsea RDS Decoder

```bash
cd ~
git clone https://github.com/windytan/redsea
cd redsea
meson setup build
cd build
meson compile
```

**Verify Redsea installation:**
```bash
./redsea --help
```
**Expected output:** Help text without errors

**If compilation fails:**
- Ensure all build tools are installed from Step 1
- Check for missing dependencies in error messages

### Step 4: Install E-paper Display Library

```bash
cd ~
git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python/lib
sudo cp -r waveshare_epd /usr/local/lib/python3.11/dist-packages/
sudo chmod -R 755 /usr/local/lib/python3.11/dist-packages/waveshare_epd
```

**Verify e-paper library installation:**
```bash
python3 -c "from waveshare_epd import epd4in26; print('✅ E-paper library OK')"
```
**Expected output:** "✅ E-paper library OK"

**If import fails:**
- Verify SPI is enabled: `sudo raspi-config`
- Check GPIO connections to display
- Verify Python version (adjust path if needed)

### Step 5: Setup AI Environment (CRITICAL STEP)

**This step is essential for transcription functionality**

```bash
# Create Python virtual environment for AI
python3 -m venv ~/vma_env

# Activate the AI environment
source ~/vma_env/bin/activate

# Verify we're in the correct environment
echo "🔍 Active Python environment:"
which python
python --version
```

**Install PyTorch (CPU version optimized for Raspberry Pi):**
```bash
# Install PyTorch CPU version (takes 5-10 minutes)
echo "📦 Installing PyTorch CPU version..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**Install AI dependencies:**
```bash
# Install Transformers and related packages (takes 3-5 minutes)
echo "📦 Installing Transformers and dependencies..."
pip install transformers datasets tokenizers

# Optional: Install standard Whisper as fallback
pip install openai-whisper
```

**CRITICAL: Verify AI installation:**
```bash
# Test PyTorch installation
python -c "
import torch
print(f'✅ PyTorch version: {torch.__version__}')
print(f'✅ PyTorch device: {torch.device(\"cpu\")}')
"

# Test Transformers installation
python -c "
from transformers import pipeline
print('✅ Transformers pipeline imported successfully')
"

# Test KBWhisper model loading (this will download the model - takes 2-3 minutes first time)
python -c "
try:
    from transformers import pipeline
    whisper = pipeline('automatic-speech-recognition', model='KBLab/kb-whisper-medium')
    print('✅ KBWhisper model loaded successfully')
    print('🎯 AI transcription ready!')
except Exception as e:
    print(f'❌ Model loading failed: {e}')
    print('ℹ️ This will be retried automatically during first transcription')
"

# Deactivate environment when done testing
deactivate
```

**Expected outputs:**
- ✅ PyTorch version: 2.x.x
- ✅ Transformers pipeline imported successfully  
- ✅ KBWhisper model loaded successfully
- 🎯 AI transcription ready!

**AI Installation Troubleshooting:**

**If PyTorch installation fails:**
```bash
# Try with more memory allocated
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=1024
sudo systemctl restart dphys-swapfile
# Retry PyTorch installation
```

**If model loading fails:**
- Check internet connection (needed only for first download)
- Verify sufficient disk space: `df -h` (need ~2GB free)
- Model will auto-download during first transcription if this test fails

**Alternative: Use Standard Whisper for Other Languages**

To use standard OpenAI Whisper instead of KBWhisper (for non-Swedish languages):
```bash
# Already installed above with: pip install openai-whisper
```

Then edit `transcriber.py` and change line:
```python
self.model_name = "KBLab/kb-whisper-medium"
```
to:
```python
self.model_name = "openai/whisper-medium"
```

### Step 6: Download and Setup VMA System

```bash
cd ~
# Download/copy all VMA system files to ~/rds_logger3/
# (Files should be provided separately or downloaded from repository)

cd ~/rds_logger3
chmod +x *.sh
```

**Configure for your location and reception:**
```bash
nano config.py
```

**Critical settings to verify/change:**
```python
# Your local P4 frequency (see Reception Setup section above)
FREQUENCY = 103300000    # Default: Stockholm 103.3 MHz

# RTL-SDR reception parameters
GAIN = 30                # Start with 30, adjust based on signal quality
PPM_CORRECTION = 50      # Frequency correction for your RTL-SDR device

# Path to redsea (update if installed elsewhere)
REDSEA_PATH = "/home/chris/redsea/build/redsea"
```

**Test your configuration:**
```bash
# Test FM reception with your settings
rtl_fm -f $(python3 -c "from config import FREQUENCY; print(f'{FREQUENCY/1000000:.1f}M')") -s 200000 -g $(python3 -c "from config import GAIN; print(GAIN)") - | aplay -r 22050 -f S16_LE
```
You should hear clear P4 audio. Press Ctrl+C to stop. If audio is poor, adjust GAIN and antenna position.

### Project File Structure

```
~/rds_logger3/
├── start_vma_with_display.sh    # Main startup script - starts entire system
├── start_vma_system.sh          # Core VMA system without display
├── vma-system.service           # Systemd service file for automatic startup
├── config.py                   # Central configuration (frequency, paths, etc.)
├── rds_logger.py               # Main application - processes RDS data
├── rds_detector.py             # Detects VMA and traffic events from RDS
├── rds_parser.py               # Parses JSON RDS data from redsea
├── audio_recorder.py           # Records audio when events detected
├── transcriber.py              # AI transcription using KBWhisper
├── display_monitor.py          # Monitors logs and updates display
├── display_manager.py          # Manages display content and updates
├── display_state_machine.py    # Handles display mode switching
├── content_formatter.py        # Formats content for display
├── screen_layouts.py           # Creates visual layouts for e-paper
├── display_config.py           # Display configuration and settings
├── cleanup.py                  # Automatic cleanup and maintenance
├── test_display_functionality.py # Test suite for display system
├── test_display_live.py        # Live display demonstration
├── vma_simulator.py            # Simulate VMA events for testing
├── backup/                     # Session backups (created automatically)
└── logs/                       # All log files and recordings
    ├── audio/                  # Recorded audio files
    ├── transcriptions/         # AI transcriptions
    ├── screen/                 # Display screenshots
    └── *.log                   # Various log files
```

**Core System Scripts:**
- `start_vma_with_display.sh` - Main entry point, starts everything
- `rds_logger.py` - Heart of the system, processes all RDS data
- `audio_recorder.py` - Records audio automatically during events
- `transcriber.py` - Converts audio to text using Swedish AI

**Display System Scripts:**
- `display_monitor.py` - Watches for events and updates display
- `display_manager.py` - Manages what appears on screen
- `content_formatter.py` - Formats text for the e-paper display
- `screen_layouts.py` - Creates the visual appearance

**Configuration and Maintenance:**
- `config.py` - All settings (frequency, file paths, durations)
- `cleanup.py` - Automatic file cleanup and backup management
- `vma-system.service` - Makes system start automatically on boot

### Step 7: Test System Components

**First, verify FM reception quality:**
```bash
cd ~/rds_logger3

# Test RTL-SDR with your antenna
rtl_test -t
```
Expected output: "RTL-SDR Blog V4 Detected"

```bash
# Test FM audio reception
rtl_fm -f $(python3 -c "from config import FREQUENCY; print(f'{FREQUENCY/1000000:.1f}M')") -s 200000 -g $(python3 -c "from config import GAIN; print(GAIN)") - | aplay -r 22050 -f S16_LE
```
You should hear clear P4 audio. If not, check antenna positioning and adjust GAIN in config.py.

**Test AI transcription system:**
```bash
# Test AI environment and model loading
cd ~/rds_logger3
python3 -c "
try:
    from transcriber import AudioTranscriber
    print('✅ transcriber.py can be imported')
    transcriber = AudioTranscriber()
    print(f'✅ AudioTranscriber created: {transcriber.is_initialized}')
    print(f'📁 Model: {transcriber.model_name}')
    print(f'🐍 Python: {transcriber.venv_python}')
    
    # Test AI environment
    stats = transcriber.get_stats()
    print(f'📊 AI Status: {stats}')
except Exception as e:
    print(f'❌ Transcriber error: {e}')
    print('🔧 Run AI troubleshooting commands below')
"
```

**If AI test fails, run diagnostic:**
```bash
# Check AI environment
echo "🔍 Checking AI environment..."
if [ -d ~/vma_env ]; then
    echo "✅ Virtual environment exists: ~/vma_env"
    source ~/vma_env/bin/activate
    python -c "
import sys
print(f'Python: {sys.executable}')
try:
    import torch
    print(f'✅ PyTorch: {torch.__version__}')
except:
    print('❌ PyTorch missing - rerun Step 5')
try:
    from transformers import pipeline
    print('✅ Transformers available')
except:
    print('❌ Transformers missing - rerun Step 5')
"
    deactivate
else
    echo "❌ Virtual environment missing - rerun Step 5"
fi
```

**Test the display system:**
```bash
# Test display system
python3 test_display_functionality.py
```
Expected output: "9/9 tests PASSED"

```bash
# Test live display (optional)
python3 test_display_live.py
```

**Test complete system:**
```bash
# Test manual system start
./start_vma_with_display.sh
```
System should start without errors and show startup screen. Press Ctrl+C to stop.

**Check transcription works:**
```bash
# Generate test audio and verify transcription
python3 vma_simulator.py
# Wait 30 seconds, then check for transcription files:
ls -la logs/transcriptions/
# Should see .txt files with transcribed content
```

### Step 8: Setup Automatic Startup

```bash
cd ~/rds_logger3

# Install systemd service
sudo cp vma-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vma-system.service
```

**Test automatic startup:**
```bash
sudo systemctl start vma-system.service
sudo systemctl status vma-system.service
```
Expected output: "Active: active (running)"

**Test reboot functionality:**
```bash
sudo reboot
```
After reboot, system should start automatically.

### Step 9: Setup Automatic Maintenance

```bash
# Open crontab for editing
crontab -e
```

Add these lines to the crontab:
```bash
# Daily cleanup at 3 AM
0 3 * * * cd /home/chris/rds_logger3 && python3 cleanup.py --daily 2>&1 | logger -t vma-cleanup

# Weekly deep clean on Sundays at 4 AM
0 4 * * 0 cd /home/chris/rds_logger3 && python3 cleanup.py --weekly 2>&1 | logger -t vma-cleanup
```

### Step 10: Final Verification

**Check system status:**
```bash
sudo systemctl status vma-system.service
```
Expected output: "Active: active (running)"

**Check RDS reception:**
```bash
tail -f logs/rds_continuous_$(date +%Y%m%d).log
```
You should see regular RDS data updates. If not, check antenna and signal strength.

**Verify transcription is working:**
```bash
# Check recent system logs for transcription activity
grep -i "transcrib" logs/system_$(date +%Y%m%d).log | tail -5

# Look for successful transcription messages:
# "✅ Transcription completed"
# "💾 Saved to: filename.txt"
```

**Check file creation:**
```bash
ls -la logs/
ls -la logs/audio/
ls -la logs/transcriptions/
```

The e-paper display should show current system status and indicate "RDS: Active".

**Complete system verification:**
```bash
# Test with simulator to verify end-to-end functionality
python3 vma_simulator.py

# After 2 minutes, check results:
echo "📁 Audio files:"
ls -la logs/audio/ | tail -3
echo "📝 Transcription files:"
ls -la logs/transcriptions/ | tail -3
echo "🖥️ Display images:"
ls -la logs/screen/ | tail -3
```

All three directories should contain recent files if system is working correctly.

---

## Troubleshooting Common Issues

### AI/Transcription Problems

**Problem: "Transcription failed" in logs**
```bash
# Diagnostic commands:
cd ~/rds_logger3
python3 -c "
from transcriber import AudioTranscriber
transcriber = AudioTranscriber()
print(f'Initialized: {transcriber.is_initialized}')
print(f'Stats: {transcriber.get_stats()}')
"

# Check AI environment:
source ~/vma_env/bin/activate
python -c "
import torch
from transformers import pipeline
print('✅ AI environment OK')
"
deactivate
```

**Solution if AI environment broken:**
```bash
# Recreate AI environment
rm -rf ~/vma_env
python3 -m venv ~/vma_env
source ~/vma_env/bin/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers datasets tokenizers
deactivate
```

**Problem: "None of PyTorch, TensorFlow >= 2.0, or Flax have been found"**
- This means PyTorch installation failed
- Rerun Step 5 completely
- Check available disk space: `df -h`
- Increase swap if needed: edit `/etc/dphys-swapfile`

### System Not Starting

**Problem: System service fails to start**
```bash
# Check service status and logs
sudo systemctl status vma-system.service
sudo journalctl -u vma-system.service -f

# Manual start for debugging
cd ~/rds_logger3
./start_vma_with_display.sh
```

**Problem: RTL-SDR not detected**
```bash
# Test RTL-SDR
rtl_test -t

# If fails:
lsusb  # Should show RTL2838 device
sudo udevadm control --reload-rules
# Replug USB device
```

### Reception Problems

**Problem: No RDS data in logs**
```bash
# Test FM reception manually
rtl_fm -f 103.3M -s 200000 -g 30 - | aplay -r 22050 -f S16_LE

# If no audio or poor quality:
# 1. Check antenna connection
# 2. Try different gain values (20-45)
# 3. Adjust antenna position
# 4. Verify correct frequency for your location
```

**Problem: Audio recorded but no transcription**
- Check AI environment (see AI troubleshooting above)
- Verify transcription files: `ls -la logs/transcriptions/`
- Check audio file size: `ls -lh logs/audio/` (should be >500KB)

### Display Problems

**Problem: Display not updating**
```bash
# Test display manually
python3 test_display_functionality.py

# Check display logs
grep -i "display" logs/system_$(date +%Y%m%d).log

# Verify SPI enabled
sudo raspi-config  # Interface Options → SPI → Enable
```

### Storage Problems

**Problem: Disk full**
```bash
# Check disk usage
df -h
du -sh logs/ backup/

# Emergency cleanup
python3 cleanup.py --emergency

# Manual cleanup if needed
rm -rf backup/session_* # Remove old backups
rm logs/audio/*.wav     # Remove old audio files
```

---

## Emergency Preparedness and Power Management

### Power Consumption Analysis

**Measured power consumption:**
- Normal operation: 9W continuous
- During transcription: 16W peak
- Display updates: 10W for 4 seconds
- Display standby: 0W (retains image without power)

**Battery life estimates:**
- 12V car battery (100Ah): 133 hours = 5.5 days continuous
- 20,000mAh power bank: 11 hours continuous
- With 50W solar panel: Indefinite operation with 4+ hours daily sun

### Crisis Operation Features

**Offline capability:**
- No internet required for basic VMA detection
- All processing done locally
- FM radio works when other infrastructure fails
- **Only requires adequate FM radio reception**

**Reception reliability:**
- Works as long as P4 transmitters are operating
- Independent of internet and mobile networks
- Can operate during power grid issues (with battery backup)
- Antenna positioning critical for reliable operation during storms

**Data preservation:**
- Session backup system preserves all data across restarts
- Emergency cleanup maintains operation during storage crises
- Multiple retention policies for different data types

**Automatic operation:**
- Starts automatically on power-on
- Self-maintains and cleans up old files
- Continues operation without user intervention
- Automatic restart if system crashes

### Monitoring and Maintenance

**System status:**
```bash
# Check if system is running
sudo systemctl status vma-system.service

# View recent activity
tail -f logs/system_$(date +%Y%m%d).log

# Monitor RDS reception quality
tail -f logs/rds_continuous_$(date +%Y%m%d).log

# Check storage usage
du -sh logs/ backup/

# Manual cleanup if needed
python3 cleanup.py --status
python3 cleanup.py --emergency  # If storage critical
```

**Log files locations:**
- System logs: `logs/system_YYYYMMDD.log`
- RDS data: `logs/rds_continuous_YYYYMMDD.log`
- Audio recordings: `logs/audio/`
- Transcriptions: `logs/transcriptions/`
- Backups: `backup/session_YYYYMMDD_HHMMSS/`
- Display images: `logs/screen/`

### Emergency Procedures

**If system stops working:**
1. Check power and USB connections
2. Restart: `sudo systemctl restart vma-system.service`
3. Check logs: `sudo journalctl -u vma-system.service`
4. Manual start: `cd ~/rds_logger3 && ./start_vma_with_display.sh`

**If poor FM reception/no RDS data:**
1. Check antenna connection and positioning
2. Test audio: `rtl_fm -f 103.3M -s 200000 -g 30 - | aplay -r 22050 -f S16_LE`
3. Adjust gain in config.py (try values 20-45)
4. Move antenna to higher location or away from interference
5. Verify correct P4 frequency for your location
6. Check PPM correction value in config.py

**If RTL-SDR not detected:**
1. Check USB connection
2. Test: `rtl_test -t`
3. Replug USB device
4. Restart system

**If transcription not working:**
1. Check AI environment: `source ~/vma_env/bin/activate && python -c "import torch; from transformers import pipeline; print('OK')"`
2. Verify audio files exist: `ls -la logs/audio/`
3. Check transcription logs: `grep -i transcrib logs/system_$(date +%Y%m%d).log`
4. If AI environment broken, recreate it (see troubleshooting above)

**If no emergency events detected:**
1. Verify RDS data flow: `tail -f logs/rds_continuous_$(date +%Y%m%d).log`
2. Test with VMA simulator: `python3 vma_simulator.py`
3. Check signal quality during actual P4 traffic announcements
4. Verify TA flags appear during real traffic reports

**If storage full:**
1. Run emergency cleanup: `python3 cleanup.py --emergency`
2. Check backup size: `du -sh backup/`
3. Remove old backups manually if needed

---

## License and Credits

**License:** MIT License - Free for commercial and personal use

**Credits:**
- Development: Christian Gillinger
- RDS decoding: Oona Raisanen (redsea)
- Swedish AI model: KBLab (kb-whisper)
- RTL-SDR: RTL-SDR Blog team
- E-paper display: Waveshare technology

**Created:** 2025-06-08  
**Version:** 4.2 (Production ready with improved AI installation guide)  
**Designed for:** Swedish emergency broadcast system  
**Tested on:** Raspberry Pi 5, RTL-SDR Blog V4, Waveshare 4.26" display