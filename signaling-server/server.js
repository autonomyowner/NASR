const express = require('express')
const { createServer } = require('http')
const { Server } = require('socket.io')
const cors = require('cors')

const app = express()
const server = createServer(app)

// Enable CORS for all origins (adjust in production)
app.use(cors({
  origin: ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000", "http://192.168.1.4:5174", "http://192.168.1.4:5173", "http://192.168.1.4:5175", "http://192.168.1.4:5176", "https://*.vercel.app"],
  methods: ["GET", "POST"],
  credentials: true
}))

const io = new Server(server, {
  cors: {
    origin: ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000", "http://192.168.1.4:5174", "http://192.168.1.4:5173", "http://192.168.1.4:5175", "http://192.168.1.4:5176", "https://*.vercel.app"],
    methods: ["GET", "POST"],
    credentials: true
  }
})

// Store connected users
const connectedUsers = new Map()
const userSockets = new Map()

app.get('/', (req, res) => {
  res.json({
    message: 'Travoice Signaling Server',
    version: '1.0.0',
    connectedUsers: connectedUsers.size,
    uptime: process.uptime()
  })
})

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() })
})

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`)

  // Generate a simple peer ID
  const peerId = `peer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  // Store user info
  connectedUsers.set(socket.id, {
    peerId: peerId,
    socketId: socket.id,
    connectedAt: new Date().toISOString()
  })
  
  userSockets.set(peerId, socket.id)

  // Send peer ID to client
  socket.emit('peer-id', peerId)

  // Broadcast updated user list
  const onlineUsers = Array.from(connectedUsers.values()).map(user => user.peerId)
  io.emit('users-updated', onlineUsers)

  console.log(`Assigned peer ID: ${peerId} to socket: ${socket.id}`)
  console.log(`Total connected users: ${connectedUsers.size}`)

  // Handle call requests
  socket.on('call-request', ({ to, from, offer }) => {
    console.log(`Call request from ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('incoming-call', { from, offer })
        console.log(`Call request forwarded to ${to}`)
      } else {
        socket.emit('call-failed', { reason: 'Target user not found' })
        console.log(`Target socket not found for peer: ${to}`)
      }
    } else {
      socket.emit('call-failed', { reason: 'User not online' })
      console.log(`Peer not found: ${to}`)
    }
  })

  // Handle call answers
  socket.on('call-answer', ({ to, from, answer }) => {
    console.log(`Call answer from ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('call-answered', { from, answer })
        console.log(`Call answer forwarded to ${to}`)
      }
    }
  })

  // Handle ICE candidates
  socket.on('ice-candidate', ({ to, from, candidate }) => {
    console.log(`ICE candidate from ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('ice-candidate', { from, candidate })
        console.log(`ICE candidate forwarded to ${to}`)
      }
    }
  })

  // Handle call declined
  socket.on('call-declined', ({ to, from }) => {
    console.log(`Call declined by ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('call-declined', { from })
        console.log(`Call declined notification sent to ${to}`)
      }
    }
  })

  // Handle call ended
  socket.on('call-ended', ({ to, from }) => {
    console.log(`Call ended by ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('call-ended', { from })
        console.log(`Call ended notification sent to ${to}`)
      }
    }
  })

  // Handle user busy
  socket.on('user-busy', ({ to, from }) => {
    console.log(`User busy notification from ${from} to ${to}`)
    
    const targetSocketId = userSockets.get(to)
    if (targetSocketId) {
      const targetSocket = io.sockets.sockets.get(targetSocketId)
      if (targetSocket) {
        targetSocket.emit('user-busy', { from })
      }
    }
  })

  // Handle disconnect
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`)
    
    const user = connectedUsers.get(socket.id)
    if (user) {
      userSockets.delete(user.peerId)
      connectedUsers.delete(socket.id)
      
      // Broadcast updated user list
      const onlineUsers = Array.from(connectedUsers.values()).map(user => user.peerId)
      io.emit('users-updated', onlineUsers)
      
      console.log(`Removed peer: ${user.peerId}`)
      console.log(`Total connected users: ${connectedUsers.size}`)
    }
  })

  // Handle errors
  socket.on('error', (error) => {
    console.error(`Socket error for ${socket.id}:`, error)
  })
})

const PORT = process.env.PORT || 3002
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Travoice Signaling Server running on port ${PORT}`)
  console.log(`📡 WebSocket endpoint: ws://192.168.1.4:${PORT}`)
  console.log(`🌐 HTTP endpoint: http://192.168.1.4:${PORT}`)
  console.log(`💪 Ready to handle WebRTC signaling!`)
})

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully')
  server.close(() => {
    console.log('Server closed')
    process.exit(0)
  })
})

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully')
  server.close(() => {
    console.log('Server closed')
    process.exit(0)
  })
})