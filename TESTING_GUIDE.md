# NASR Voice Calling - Testing Guide

## Test Matrix (Phase 1)

### C1) Local Testing
- [x] **Two tabs same browser**: Open http://localhost:5174 in two Chrome tabs
  - ✅ Each tab gets unique Peer ID
  - ✅ Connection status shows "Connected" 
  - ✅ Copy ID button works
  - ✅ Can paste ID in other tab and start call
  - ✅ Incoming call modal appears with Accept/Decline
  - ✅ Audio flows both ways when call accepted
  - ✅ Mute/unmute works
  - ✅ Call timer displays correctly
  - ✅ End call works for both sides
  - ✅ Error messages display for invalid scenarios

- [ ] **Two different browsers**: Chrome + Edge/Firefox
  - [ ] Same tests as above
  - [ ] Check browser compatibility
  - [ ] Audio permissions work correctly

### C2) LAN Testing
- [ ] **Laptop + Phone same Wi-Fi**:
  - [ ] Access app via laptop's IP address (e.g., http://192.168.1.100:5174)
  - [ ] Both devices connect to signaling server
  - [ ] Cross-device calling works
  - [ ] Audio quality acceptable on both devices
  - [ ] Mobile browser permissions work

### C3) Cross-Network Testing (Requires TURN)
- [ ] **One device on LTE, another on home Wi-Fi**:
  - [ ] Both devices connect successfully
  - [ ] ICE candidates exchange properly
  - [ ] TURN server fallback works
  - [ ] Audio flows despite NAT/firewall
  - [ ] Connection remains stable

## Key Performance Indicators (KPIs)

### C2) Performance Metrics
- **Call Setup Time**: ≤ 3s on average networks ✅ (typically 1-2s locally)
- **Call Success Rate**: ≥ 95% across test matrix
  - Local (2 tabs): ✅ 100% success
  - Local (2 browsers): ⏳ Pending
  - LAN: ⏳ Pending  
  - Cross-network: ⏳ Pending
- **Audio Quality**: Minimal clipping, responsive mute/unmute ✅

## Demo Script for Investors (C3)

### Scene 1: Setup & Identity (30 seconds)
1. **Open the app** at http://localhost:5174
2. **Show "Your Connection" section**:
   - "Here's your unique ID that others can use to call you"
   - "Copy button makes it easy to share"
   - "Green status shows we're connected to the signaling server"
3. **Open second tab** (simulating second person)
   - "Each person gets their own unique ID"

### Scene 2: Making a Call (45 seconds)  
4. **Copy ID from first tab**
5. **In second tab, paste the ID** in "Enter Peer ID" field
6. **Click "Start Call"**
   - "The system finds your friend and sends the call request"
7. **Show incoming call modal on first tab**:
   - "Beautiful incoming call interface with caller info"
   - "Auto-decline timer prevents missed call buildup"
8. **Click Accept**

### Scene 3: Live Call Experience (60 seconds)
9. **Show connected call interface**:
   - "Call timer tracking duration"
   - "Real-time call quality monitoring"
   - "Your ID still visible for others to reach you"
10. **Demo mute/unmute**: 
    - "Professional call controls"
    - "Instant mute response"
11. **Show translation toggle**:
    - "Real-time translation ready when needed"
12. **Brief quality metrics explanation**:
    - "Network monitoring ensures best possible experience"

### Scene 4: Ending & Polish (30 seconds)
13. **End the call**
14. **Show call history updated**
15. **Highlight key benefits**:
    - "No downloads required - works in any browser"
    - "Universal peer-to-peer calling with your unique ID"
    - "Professional quality with translation capabilities"
    - "Ready for global deployment"

**Total Demo Time: ~2.5 minutes**

## Troubleshooting Common Issues

### Microphone Access Issues
- **"No microphone found"**: 
  - Ensure a microphone is connected and working
  - Try refreshing the page after connecting microphone
  - Check Windows/Mac sound settings
- **"Microphone access denied"**:
  - Click the microphone icon in browser address bar
  - Select "Always allow" for localhost
  - Refresh the page after granting permission
- **"Your browser does not support microphone access"**:
  - Use Chrome, Edge, or Firefox (latest versions)
  - Ensure you're on localhost (not a file:// URL)

### Connection Issues
- **"Disconnected" status**: Check if signaling server is running on port 3001
- **Call fails immediately**: Verify both devices connected to signaling server
- **Infinite loading/errors**: Check browser console for React errors

### Browser Compatibility
- **Chrome**: ✅ Full support, best experience
- **Edge**: ✅ Expected to work
- **Firefox**: ✅ Expected to work  
- **Safari**: ⚠️ May have WebRTC limitations
- **Mobile browsers**: ⚠️ Requires HTTPS for microphone access in production

### Network Issues
- **Local**: Should work without TURN servers
- **Across networks**: Requires TURN servers to traverse NAT/firewalls
- **Audio dropouts**: Usually network quality, check connection

## Next Steps (Post-Demo)

1. **Deploy signaling server** to production (Render/Railway)
2. **Configure production TURN servers** for reliable cross-network calling
3. **Deploy frontend** to live URL with HTTPS
4. **Update environment variables** for production
5. **Add more languages** for translation service
6. **Performance optimization** based on real usage patterns

## Technical Architecture Summary

- **Frontend**: React/TypeScript + Vite (runs in browser)
- **Signaling**: Node.js + Socket.IO (coordinates calls)  
- **WebRTC**: Peer-to-peer audio (direct between users)
- **TURN Servers**: NAT traversal for cross-network calls
- **No backend databases**: Stateless, privacy-focused

This creates a scalable foundation for global real-time voice communication with translation capabilities.