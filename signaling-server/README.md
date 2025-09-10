# Travoice Signaling Server

A simple WebRTC signaling server for the Travoice application using Socket.IO.

## Features

- ✅ **WebRTC Signaling**: Handles offer/answer/ICE candidate exchange
- ✅ **User Management**: Tracks online users and peer IDs
- ✅ **Call Management**: Call requests, answers, declines, and endings
- ✅ **Health Monitoring**: Health check endpoint and status reporting
- ✅ **CORS Support**: Configured for local development and Vercel deployment
- ✅ **Error Handling**: Comprehensive error handling and logging

## Quick Start

### Development (Local)

1. **Install dependencies**:
   ```bash
   cd signaling-server
   npm install
   ```

2. **Start the server**:
   ```bash
   npm run dev
   ```

3. **Verify it's running**:
   - Open http://localhost:3001 in your browser
   - You should see server status and connected users count

### Production

1. **Start the server**:
   ```bash
   npm start
   ```

2. **Environment Variables**:
   ```bash
   PORT=3001  # Default port
   ```

## API Endpoints

### HTTP Endpoints

- `GET /` - Server status and statistics
- `GET /health` - Health check endpoint

### WebSocket Events

#### Client → Server Events:
- `call-request` - Request to start a call
- `call-answer` - Answer an incoming call
- `ice-candidate` - Exchange ICE candidates
- `call-declined` - Decline an incoming call
- `call-ended` - End an active call
- `user-busy` - Notify caller that user is busy

#### Server → Client Events:
- `peer-id` - Assigned peer ID for the client
- `users-updated` - List of online users
- `incoming-call` - Incoming call notification
- `call-answered` - Call was answered
- `ice-candidate` - ICE candidate from peer
- `call-declined` - Call was declined
- `call-ended` - Call was ended
- `user-busy` - Target user is busy
- `call-failed` - Call failed for some reason

## Usage with Travoice App

The Travoice frontend will automatically connect to this signaling server when you:

1. **Start the signaling server**: `npm run dev`
2. **Start the frontend**: `npm run dev` (in the main project directory)
3. **Open the app**: Visit http://localhost:5173

The app will show "Connected" status when the signaling server is running.

## Configuration

### Frontend Configuration

The frontend automatically connects to `localhost:3001` by default. You can override this with environment variables:

```bash
# .env.local in main project
VITE_SIGNALING_URL=ws://localhost:3001
```

### CORS Configuration

The server is configured to accept connections from:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (alternative dev port)
- `https://*.vercel.app` (Vercel deployments)

## Deployment

### Local Network Access

To allow connections from other devices on your network:

```bash
# Find your local IP
ipconfig  # Windows
ifconfig  # macOS/Linux

# Start server with specific host
PORT=3001 node server.js
```

### Production Deployment

For production deployment (e.g., Vercel, Heroku, Railway):

1. **Update CORS origins** in `server.js`
2. **Set environment variables**:
   ```bash
   PORT=3001
   NODE_ENV=production
   ```
3. **Deploy using your platform's methods**

### Vercel Deployment

Create `vercel.json` in the signaling-server directory:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "server.js",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "server.js"
    }
  ]
}
```

Then:
```bash
vercel --prod
```

## Monitoring

### Server Status
Visit `http://localhost:3001` to see:
- Connected users count
- Server uptime
- Version information

### Logs
The server provides detailed logs for:
- User connections/disconnections
- Call signaling events
- Errors and warnings

### Health Check
Use `GET /health` for automated monitoring:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Troubleshooting

### Connection Issues
1. **Check if server is running**: Visit http://localhost:3001
2. **Verify port is available**: Use `netstat -an | findstr 3001`
3. **Check firewall settings**: Ensure port 3001 is open

### CORS Issues
1. **Add your domain** to the CORS origins in `server.js`
2. **Check browser console** for CORS error messages
3. **Verify protocol** (http vs https) matches

### WebRTC Issues
1. **Check browser console** for WebRTC errors
2. **Use chrome://webrtc-internals/** for detailed debugging
3. **Test on different networks** to identify connectivity issues

## Development

### Adding New Features

The server is designed to be extensible. To add new signaling events:

1. **Add client event handler**:
   ```javascript
   socket.on('your-new-event', (data) => {
     // Handle the event
     console.log('New event:', data)
   })
   ```

2. **Forward to target peer**:
   ```javascript
   const targetSocket = io.sockets.sockets.get(targetSocketId)
   if (targetSocket) {
     targetSocket.emit('your-response-event', data)
   }
   ```

### Testing

You can test the server manually using Socket.IO client:

```javascript
const io = require('socket.io-client')
const socket = io('http://localhost:3001')

socket.on('connect', () => {
  console.log('Connected to signaling server')
})

socket.on('peer-id', (peerId) => {
  console.log('My peer ID:', peerId)
})
```

## License

MIT License - see main project for details.