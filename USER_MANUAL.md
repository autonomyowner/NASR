# The HIVE Translation System - User Manual

## 🌟 Welcome to Real-Time Translation

The HIVE Translation System enables seamless multilingual conversations with sub-500ms latency. This manual will guide you through all features and help you get the most out of your translation experience.

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Translation Interface](#translation-interface)
3. [Audio Settings](#audio-settings)
4. [Language Selection](#language-selection)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Best Practices](#best-practices)

## 🚀 Getting Started

### Accessing the Translation System

1. **Open your web browser** (Chrome, Firefox, Safari, or Edge)
2. **Navigate to**: `https://yourdomain.com/call`
3. **Allow microphone permissions** when prompted
4. **Ensure stable internet connection** (minimum 1 Mbps recommended)

### System Requirements

**Minimum Requirements:**
- Modern web browser (Chrome 88+, Firefox 85+, Safari 14+, Edge 88+)
- Microphone access
- Internet connection: 1 Mbps upload/download
- RAM: 2GB available

**Recommended Requirements:**
- High-quality headset or microphone
- Internet connection: 5+ Mbps upload/download  
- RAM: 4GB available
- Quiet environment for optimal speech recognition

### First Time Setup

When you first access the translation interface:

1. **Browser permissions popup** will appear
   - Click "Allow" for microphone access
   - Click "Allow" for camera access (optional, for video calls)

2. **Audio setup will begin automatically**
   - Test your microphone
   - Adjust volume levels
   - Select preferred audio devices

3. **Choose your language preferences**
   - Set your primary speaking language
   - Select target translation languages

## 🎛️ Translation Interface

### Main Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│ The HIVE Translation System                    🌍 [Settings]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎤 [Speak English]  →  [Translate to: Spanish ▼]  🔊      │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Live Captions                                           │ │
│  │ "Hello, how are you today?"                             │ │
│  │ "Hola, ¿cómo estás hoy?"                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  👥 Participants (2/8)  📊 Connection: Excellent           │
│  • You (Host)          🎵 Audio Quality: High              │
│  • Maria (Listener)    ⏱️ Latency: 234ms                   │
│                                                             │
│  [🎙️ Mute] [📹 Camera] [⚙️ Settings] [📱 Record] [❓ Help] │
└─────────────────────────────────────────────────────────────┘
```

### Key Interface Elements

#### 1. Language Controls (Top Bar)
- **Source Language Button**: Shows your speaking language
  - Click to change your primary language
  - Auto-detection available for supported languages

- **Translation Language Dropdown**: Select target language
  - Currently supports: Spanish, French, German, Italian, Portuguese
  - Multiple languages can be selected for multi-participant calls

#### 2. Live Captions Area
- **Original Text**: Your speech appears in real-time
- **Translated Text**: Translation appears below in target language
- **Color Coding**: 
  - Green: High confidence translation
  - Yellow: Medium confidence  
  - Red: Low confidence (may need repetition)

#### 3. Participant Panel
- **Participant List**: Shows all connected users
- **Connection Status**: Real-time connection quality
- **Audio Levels**: Visual indication of speaking participants

#### 4. Control Buttons
- **Mute/Unmute**: Toggle your microphone
- **Camera**: Enable/disable video (if available)
- **Settings**: Access advanced configuration
- **Record**: Start/stop session recording
- **Help**: Access this manual and support

## 🔊 Audio Settings

### Accessing Audio Settings

Click the **Settings** button (⚙️) and select **Audio Settings** to access:

### Microphone Configuration

#### Device Selection
```
┌─────────────────────────────────────────────┐
│ Microphone Device                           │
│ ┌─────────────────────────────────────────┐ │
│ │ Built-in Microphone            [Select] │ │
│ │ USB Headset Microphone        [Select] │ │
│ │ Bluetooth Headphones          [Select] │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**How to select the best microphone:**
1. **Test each available device** using the mic test feature
2. **Choose the device with clearest audio** and least background noise
3. **Prefer wired headsets** over built-in microphones for best quality

#### Microphone Testing

Use the built-in mic test to verify your audio setup:

1. Click **Test Microphone**
2. **Speak clearly** for 5-10 seconds
3. **Listen to playback** to check:
   - Audio clarity
   - Volume levels
   - Background noise
4. **Adjust settings** if needed

#### Volume and Gain Controls

```
Input Volume:  ██████████░░ 75%
Input Gain:    ████████░░░░ 60%  
Monitor Level: ██████░░░░░░ 50%
```

- **Input Volume**: Overall microphone sensitivity
- **Input Gain**: Amplification level (increase for quiet microphones)
- **Monitor Level**: How loud you hear your own voice

### Speaker/Headphone Configuration

#### Output Device Selection
- **System Default**: Use system audio output
- **Specific Device**: Choose headphones, speakers, or other audio device
- **Bluetooth Devices**: Supported with potential latency increase

#### Volume Controls
```
Translation Audio: ████████░░ 75%
System Notifications: ██████░░░░ 50%
Background Music: ███░░░░░░░ 25%
```

### Advanced Audio Processing

#### Noise Suppression
- **Built-in Noise Suppression**: Always enabled by default
- **RNNoise AI Enhancement**: Advanced AI-powered noise reduction
  - Enable for very noisy environments
  - May increase CPU usage
  - Toggle on/off based on performance

#### Echo Cancellation
- **Automatic Echo Cancellation**: Enabled by default
- **Acoustic Echo Suppression**: Reduces feedback in speaker setups
- **Manual Adjustment**: Fine-tune for specific acoustic environments

#### Audio Quality Settings
```
Quality Mode:     🔘 Balanced  ⚪ High Quality  ⚪ Low Latency
Sample Rate:      16kHz (Optimal for translation)
Bit Rate:         64kbps (Excellent quality)
```

- **Balanced**: Best overall experience (recommended)
- **High Quality**: Maximum audio fidelity, higher bandwidth usage
- **Low Latency**: Prioritizes speed over quality

## 🌍 Language Selection

### Supported Languages

#### Primary Languages (Full Support)
- **English** → Spanish, French, German, Italian, Portuguese
- **Spanish** → English, French, German, Italian, Portuguese  
- **French** → English, Spanish, German, Italian, Portuguese
- **German** → English, Spanish, French, Italian, Portuguese
- **Italian** → English, Spanish, French, German, Portuguese
- **Portuguese** → English, Spanish, French, German, Italian

#### Language Auto-Detection

The system can automatically detect your speaking language:

1. **Enable Auto-Detection**: Click source language and select "Auto-Detect"
2. **Speak naturally**: System identifies language within 2-3 seconds
3. **Manual Override**: Change language anytime if detection is incorrect

### Setting Up Translation Languages

#### Single Language Translation
1. **Set Source Language**: Click source language button (e.g., "English")
2. **Select Target Language**: Use dropdown to choose target (e.g., "Spanish")
3. **Start Speaking**: Translation begins immediately

#### Multi-Language Rooms
For conversations with multiple languages:

1. **Create Multi-Language Room**: Enable in room settings
2. **Each Participant Sets Languages**: Individual language preferences
3. **System Routes Translations**: Automatic translation to each participant's preferred language

#### Language-Specific Settings

Each language pair has optimized settings:

```
English → Spanish
├── Translation Model: Helsinki-NLP/opus-mt-en-es
├── Confidence Threshold: 0.85
├── Context Length: 512 tokens
└── Voice: Spanish Female Premium

Spanish → English  
├── Translation Model: Helsinki-NLP/opus-mt-es-en
├── Confidence Threshold: 0.82
├── Context Length: 512 tokens
└── Voice: English US Male Standard
```

## 🎯 Advanced Features

### Push-to-Talk Mode

Enable for more controlled translation:

1. **Enable Push-to-Talk**: Settings → Audio → Push-to-Talk Mode
2. **Set Activation Key**: Default is Spacebar
3. **Usage**: Hold key while speaking, release when finished

**Benefits:**
- Prevents accidental translation of background conversations
- Reduces false positive speech detection
- Better for noisy environments

### Recording and Playback

#### Session Recording
Record your translation sessions for review:

1. **Start Recording**: Click Record button (red dot appears)
2. **Record Options**:
   - **Local Only**: Records your audio only
   - **Remote Only**: Records translated audio only  
   - **Mixed**: Records both original and translation
3. **Stop Recording**: Click Record button again
4. **Download**: Recording automatically downloads as MP3/WAV file

#### Recording Settings
```
Recording Quality:    🔘 High (48kHz)  ⚪ Medium (24kHz)  ⚪ Basic (16kHz)
Recording Format:     🔘 MP3          ⚪ WAV            ⚪ FLAC
Include Translations: ✅ Yes          ⚪ No
Separate Tracks:      ✅ Yes          ⚪ No
```

### Real-Time Captions

#### Caption Display Options
- **Font Size**: Small, Medium, Large, Extra Large
- **Color Scheme**: High contrast options for accessibility
- **Position**: Top, Center, Bottom of screen
- **Background**: Transparent, Semi-transparent, Solid

#### Caption Export
1. **During Session**: Captions are automatically saved
2. **Export Options**: 
   - Text file (.txt)
   - Subtitle file (.srt)
   - Word document (.docx)
3. **Download**: Available at end of session

### Translation Quality Controls

#### Confidence Indicators
Translations show confidence levels:
- **🟢 Green (90-100%)**: High confidence, reliable translation
- **🟡 Yellow (70-89%)**: Medium confidence, generally accurate  
- **🔴 Red (Below 70%)**: Low confidence, may need repetition

#### Manual Corrections
- **Retry Translation**: Click refresh icon next to low-confidence translations
- **Alternative Translations**: Right-click translated text for alternatives
- **Feedback**: Rate translation quality to improve system performance

### Accessibility Features

#### Keyboard Navigation
- **Tab Navigation**: Navigate all interface elements
- **Enter/Space**: Activate buttons and controls
- **Arrow Keys**: Navigate dropdowns and lists
- **Escape**: Close dialogs and panels

#### Screen Reader Support
- **Full ARIA Labels**: All interface elements properly labeled
- **Live Regions**: Translation updates announced automatically
- **Keyboard Shortcuts**: All features accessible via keyboard

#### Visual Accessibility
- **High Contrast Mode**: Enhanced visibility for low vision users
- **Large Text Mode**: Increased font sizes throughout interface
- **Color Blind Support**: Color-blind friendly color schemes

## 🔧 Troubleshooting

### Common Issues and Solutions

#### No Audio / Microphone Not Working

**Symptoms:** Red microphone icon, no input detected, "Microphone not available" message

**Solutions:**
1. **Check Browser Permissions**
   - Look for microphone icon in address bar
   - Click and ensure "Allow" is selected
   - Refresh page if permissions were recently changed

2. **Check System Audio Settings**
   - Ensure microphone is not muted in system settings
   - Verify correct microphone is selected as default
   - Test microphone in other applications

3. **Browser-Specific Issues**
   - **Chrome**: Go to Settings → Privacy → Site Settings → Microphone
   - **Firefox**: Click shield icon in address bar → Permissions
   - **Safari**: Safari menu → Preferences → Websites → Microphone

4. **Hardware Issues**
   - Try different microphone or headset
   - Check USB connections
   - Test Bluetooth device connectivity

#### Poor Translation Quality

**Symptoms:** Incorrect translations, garbled text, low confidence scores

**Solutions:**
1. **Improve Audio Quality**
   - Speak clearly and at moderate pace
   - Reduce background noise
   - Use headset microphone instead of built-in mic
   - Enable RNNoise AI enhancement

2. **Check Language Settings**
   - Verify correct source language selected
   - Ensure target language is supported
   - Try language auto-detection if speaking multiple languages

3. **Optimize Speaking Technique**
   - Pause briefly between sentences
   - Avoid speaking over others
   - Articulate clearly without exaggerating
   - Speak at normal conversational volume

4. **Technical Adjustments**
   - Adjust microphone gain and volume
   - Check internet connection stability
   - Try different translation confidence threshold

#### High Latency / Slow Translation

**Symptoms:** Long delays between speaking and translated audio, >500ms latency indicator

**Solutions:**
1. **Check Network Connection**
   - Test internet speed (minimum 1 Mbps recommended)
   - Close other bandwidth-intensive applications
   - Use wired internet connection if possible
   - Check for network congestion

2. **Optimize Browser Performance**
   - Close unnecessary browser tabs
   - Clear browser cache and cookies
   - Disable unnecessary browser extensions
   - Restart browser

3. **System Performance**
   - Close other applications using CPU/memory
   - Check system resource usage
   - Ensure adequate RAM available (4GB+ recommended)

4. **Audio Settings Adjustment**
   - Switch to "Low Latency" quality mode
   - Reduce audio sample rate if needed
   - Disable advanced audio processing features

#### Connection Issues

**Symptoms:** "Connection lost", "Reconnecting...", unstable audio

**Solutions:**
1. **Network Troubleshooting**
   - Check WiFi signal strength
   - Try different network (mobile hotspot, etc.)
   - Restart router/modem
   - Contact ISP if persistent issues

2. **Browser Issues**
   - Refresh the page
   - Clear browser cache
   - Try different browser
   - Disable VPN if active

3. **Firewall/Security Software**
   - Check firewall settings for WebRTC access
   - Temporarily disable antivirus web protection
   - Ensure required ports are open (3478, 5349, 50000-50199)

### Debug Information

If you need to report an issue to support, collect this information:

#### Connection Statistics
Access via Settings → Debug → Connection Stats:
```
Connection Type: WiFi
Network Latency: 45ms
Packet Loss: 0.1%
Bandwidth: 15 Mbps down / 5 Mbps up
WebRTC State: Connected
ICE Connection: Completed
```

#### Browser Information
```
Browser: Chrome 91.0.4472.124
Operating System: Windows 10
Audio Device: USB Headset (Logitech H540)
Microphone: Built-in Array
```

#### Export Debug Data
1. Go to **Settings → Debug**
2. Click **Export Debug Information**
3. Save file and include with support request

## ⌨️ Keyboard Shortcuts

### Global Shortcuts
- **Spacebar**: Push-to-talk (when enabled)
- **Ctrl/Cmd + M**: Toggle mute/unmute
- **Ctrl/Cmd + D**: Toggle camera on/off
- **Ctrl/Cmd + R**: Start/stop recording
- **Ctrl/Cmd + S**: Open settings
- **Ctrl/Cmd + H**: Show/hide help panel
- **Escape**: Close current dialog

### Navigation Shortcuts
- **Tab**: Next interface element
- **Shift + Tab**: Previous interface element
- **Enter**: Activate selected button
- **Arrow Keys**: Navigate dropdowns
- **Home**: Go to first item in list
- **End**: Go to last item in list

### Translation Controls
- **Ctrl/Cmd + 1-5**: Quick language selection
  - Ctrl+1: English
  - Ctrl+2: Spanish  
  - Ctrl+3: French
  - Ctrl+4: German
  - Ctrl+5: Italian
- **Ctrl/Cmd + A**: Auto-detect language
- **Ctrl/Cmd + T**: Retry last translation

### Accessibility Shortcuts
- **Ctrl/Cmd + Plus**: Increase font size
- **Ctrl/Cmd + Minus**: Decrease font size
- **Ctrl/Cmd + 0**: Reset font size
- **Ctrl/Cmd + Shift + H**: Toggle high contrast mode

## 💡 Best Practices

### For Optimal Translation Quality

#### Speaking Techniques
1. **Speak Clearly**: Articulate words without exaggerating
2. **Normal Pace**: Avoid speaking too fast or too slow  
3. **Natural Pauses**: Brief pauses between sentences help processing
4. **Complete Thoughts**: Finish sentences before pausing
5. **Avoid Filler Words**: Minimize "um", "ah", "like" for clearer translations

#### Environment Optimization
1. **Quiet Space**: Minimize background noise and conversations
2. **Good Acoustics**: Avoid echoing rooms or spaces with hard surfaces
3. **Consistent Distance**: Maintain steady distance from microphone
4. **Stable Position**: Avoid moving microphone or headset while speaking

#### Technical Best Practices
1. **Quality Hardware**: Use good microphone/headset for best input quality
2. **Stable Internet**: Ensure reliable, high-speed internet connection
3. **Updated Browser**: Keep browser updated to latest version
4. **Close Unnecessary Apps**: Minimize system resource usage

### For Group Conversations

#### Room Management
1. **Designate Moderator**: One person manages technical issues
2. **Clear Speaking Order**: Establish who speaks when to avoid overlaps
3. **Mute When Not Speaking**: Reduces background noise and processing load
4. **Use Push-to-Talk**: For larger groups or noisy environments

#### Communication Etiquette
1. **Speak One at a Time**: Avoid overlapping conversations
2. **Pause for Translation**: Allow time for translation to complete
3. **Confirm Understanding**: Check that translations were clear
4. **Repeat if Needed**: Re-phrase unclear or poorly translated content
5. **Be Patient**: Allow time for processing and translation

### Accessibility Guidelines

#### For Screen Reader Users
1. **Use Keyboard Navigation**: All features accessible via keyboard
2. **Enable Audio Announcements**: Turn on translation announcements
3. **High Contrast Mode**: Enable for better visibility
4. **Large Text Mode**: Increase text size for easier reading

#### For Users with Hearing Impairments
1. **Maximize Caption Display**: Use large, high-contrast captions
2. **Enable Visual Notifications**: Turn on visual alerts
3. **Use Recording Feature**: Record sessions for later review
4. **Export Captions**: Save text transcripts of conversations

#### For Users with Motor Impairments
1. **Enable Push-to-Talk**: Use spacebar or other convenient key
2. **Adjust Timing**: Increase timeouts for interface interactions
3. **Use Voice Commands**: Where available in browser
4. **Simplified Interface**: Hide advanced controls if not needed

## 📞 Support and Help

### Getting Additional Help

#### In-App Help
- **Help Button**: Click (❓) for contextual help
- **Tooltips**: Hover over interface elements for quick explanations
- **Status Indicators**: Check connection and quality indicators

#### Online Resources
- **User Manual**: This complete guide (always available online)
- **Video Tutorials**: Step-by-step video guides for common tasks
- **FAQ**: Frequently asked questions and solutions
- **Community Forum**: User community support and tips

#### Technical Support
- **Email Support**: support@yourdomain.com
- **Live Chat**: Available during business hours
- **Phone Support**: +1-XXX-XXX-XXXX (premium support)

### Feedback and Feature Requests

Help us improve The HIVE Translation System:

1. **In-App Feedback**: Use feedback button to rate translations
2. **Feature Requests**: Submit via Settings → Feedback
3. **Bug Reports**: Include debug information with reports
4. **Community Contributions**: Join our user community forum

---

## 🎉 Conclusion

Congratulations! You now have comprehensive knowledge of The HIVE Translation System. With sub-500ms real-time translation, advanced audio processing, and accessibility features, you're ready to break down language barriers and engage in seamless multilingual conversations.

**Remember:**
- **Start with good audio setup** for best results
- **Speak clearly and naturally** for accurate translations
- **Use keyboard shortcuts** for efficient operation
- **Enable accessibility features** as needed
- **Provide feedback** to help us improve

**Happy translating!** 🌍

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-01  
**For System Version**: The HIVE v1.0  
**Support**: support@yourdomain.com