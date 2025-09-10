# Travoice Deployment Guide for Vercel

This guide covers deploying the Travoice application with all new features to Vercel, including specific considerations for the advanced features.

## Pre-deployment Checklist

### 1. Environment Configuration

Ensure your `.env` file (if any) contains necessary environment variables:
```bash
# Example environment variables (create .env.local for local development)
NEXT_PUBLIC_APP_NAME=Travoice
NEXT_PUBLIC_SIGNALING_SERVER_URL=wss://your-signaling-server.com
```

### 2. Build Configuration

Verify `vite.config.ts` is properly configured for production:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext', // Required for AudioWorklet support
    rollupOptions: {
      output: {
        manualChunks: {
          'audio-processing': [
            './src/hooks/useRNNoise.ts',
            './src/hooks/useWebRTCStats.ts',
            './src/hooks/useVolumeControls.ts'
          ]
        }
      }
    }
  },
  optimizeDeps: {
    exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/util'] // Exclude heavy dependencies if not used
  }
})
```

### 3. Browser Compatibility

Ensure `browserslist` in `package.json` includes modern browsers:
```json
{
  "browserslist": [
    "last 2 Chrome versions",
    "last 2 Firefox versions",
    "last 2 Safari versions",
    "last 2 Edge versions"
  ]
}
```

## Feature-Specific Deployment Considerations

### 1. Recording Features (MediaRecorder API)
- ✅ **No server-side changes needed**
- ✅ **Works on HTTPS** (required for MediaRecorder)
- ⚠️ **Browser compatibility**: Modern browsers only
- 💡 **File size limits**: Browser-dependent, typically 2GB max

**Vercel Configuration:**
```json
{
  "functions": {
    "app/api/**/*.js": {
      "maxDuration": 30
    }
  }
}
```

### 2. Accessibility Controls (Keyboard Shortcuts, Volume Controls)
- ✅ **Client-side only**
- ✅ **No additional configuration needed**
- ⚠️ **AudioContext**: Requires user interaction to start
- 💡 **Cross-browser testing recommended**

### 3. WebRTC Debug Panel with Stats Export
- ✅ **Client-side analysis**
- ✅ **No server storage required**
- ⚠️ **Development mode**: Uses `import.meta.env.DEV`
- 💡 **Production usage**: Set environment variable to enable

**Environment Variables:**
```bash
VITE_ENABLE_DEBUG=true  # Enable debug panel in production
```

### 4. RNNoise WASM Integration
- ⚠️ **AudioWorklet required**: Modern browsers only
- ⚠️ **WASM support**: Check browser compatibility
- ⚠️ **Memory usage**: Can be significant on mobile devices
- ⚠️ **Loading time**: WASM files may take time to load

**Vercel Headers Configuration (`vercel.json`):**
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Cross-Origin-Embedder-Policy",
          "value": "require-corp"
        },
        {
          "key": "Cross-Origin-Opener-Policy", 
          "value": "same-origin"
        },
        {
          "key": "Cross-Origin-Isolate",
          "value": "require-corp"
        }
      ]
    },
    {
      "source": "/(.*)\\.(wasm|js)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### 5. TURN Server Configuration
- ✅ **Client-side configuration**
- ✅ **No server-side requirements**
- ⚠️ **External TURN servers**: Require proper credentials
- ⚠️ **Network connectivity**: Test in production environment

**Testing TURN Connectivity:**
```javascript
// Test script to run in browser console
const turnConfig = {
  enabled: true,
  servers: [{
    urls: 'turn:your-turn-server.com:3478',
    username: 'your-username',
    credential: 'your-password'
  }]
}

// The app includes built-in TURN testing functionality
```

## Deployment Steps

### 1. Pre-flight Checks
```bash
# Install dependencies
npm install

# Type check
npm run type-check

# Build locally to test
npm run build

# Preview build
npm run preview
```

### 2. Vercel Deployment

#### Option A: GitHub Integration
1. Push code to GitHub repository
2. Connect repository to Vercel
3. Deploy automatically on push

#### Option B: Vercel CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 3. Post-deployment Verification

#### Essential Tests:
1. **Basic WebRTC connectivity**
   - Test peer-to-peer connections
   - Verify STUN server fallback

2. **Recording functionality**
   - Test local, remote, and mixed recording
   - Verify download functionality
   - Check file format compatibility

3. **Audio processing**
   - Test built-in audio constraints
   - Verify RNNoise loading (if enabled)
   - Test volume controls

4. **Keyboard shortcuts**
   - Verify shortcuts work in production
   - Test push-to-talk functionality

5. **Debug panel**
   - Verify WebRTC stats collection
   - Test stats export functionality

## Production Optimizations

### 1. Performance
```typescript
// In vite.config.ts
export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
        drop_debugger: true
      }
    }
  }
})
```

### 2. Monitoring
Add error tracking and analytics:
```typescript
// Example error boundary for production
window.addEventListener('unhandledrejection', event => {
  console.error('Unhandled promise rejection:', event.reason)
  // Send to monitoring service
})
```

### 3. Progressive Enhancement
```typescript
// Feature detection example
const supportsAudioWorklet = typeof AudioWorklet !== 'undefined'
const supportsWebAssembly = typeof WebAssembly !== 'undefined'
const supportsMediaRecorder = typeof MediaRecorder !== 'undefined'

if (!supportsAudioWorklet) {
  console.warn('AudioWorklet not supported - RNNoise disabled')
}
```

## Troubleshooting

### Common Issues:

1. **AudioContext not starting**
   ```javascript
   // Solution: Ensure user interaction before starting
   document.addEventListener('click', () => {
     if (audioContext.state === 'suspended') {
       audioContext.resume()
     }
   })
   ```

2. **WebRTC connection failures**
   - Check HTTPS requirement
   - Verify STUN server connectivity
   - Test with different networks

3. **Recording not working**
   - Verify HTTPS deployment
   - Check microphone permissions
   - Test in incognito mode

4. **RNNoise performance issues**
   - Monitor CPU usage
   - Implement fallback to built-in NS
   - Consider disabling on mobile

### Debug Commands:
```bash
# Check deployed version
curl -I https://your-app.vercel.app

# Test WebRTC connectivity
# Use browser's WebRTC internals: chrome://webrtc-internals/

# Monitor performance
# Use browser DevTools Performance tab
```

## Security Considerations

1. **HTTPS Only**: All features require HTTPS in production
2. **Permissions**: Handle microphone/camera permissions gracefully
3. **CORS**: Ensure proper CORS configuration for any external resources
4. **Content Security Policy**: Configure CSP headers if needed

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss: ws:; media-src 'self' blob:; worker-src 'self' blob:;"
        }
      ]
    }
  ]
}
```

## Performance Monitoring

Monitor these metrics in production:
- WebRTC connection success rate
- Audio quality scores
- Recording completion rates
- RNNoise CPU usage
- Page load times

## Final Checklist

- [ ] All features tested in production environment
- [ ] HTTPS certificate valid
- [ ] WebRTC connectivity verified across networks
- [ ] Recording functionality tested
- [ ] Keyboard shortcuts working
- [ ] Debug panel accessible (if enabled)
- [ ] RNNoise loading properly
- [ ] TURN server configuration tested
- [ ] Error monitoring in place
- [ ] Performance metrics being tracked

## Support

For deployment issues:
1. Check Vercel deployment logs
2. Use browser DevTools for client-side debugging
3. Test in different browsers and networks
4. Monitor WebRTC internals (chrome://webrtc-internals/)

Remember: WebRTC applications are heavily dependent on network conditions and browser capabilities. Always test thoroughly in the target deployment environment.