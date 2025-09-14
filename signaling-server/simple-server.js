const express = require('express')
const http = require('http')
const socketIo = require('socket.io')
const cors = require('cors')

const app = express()
const server = http.createServer(app)

// CORS configuration
app.use(cors({
  origin: [
    process.env.FRONTEND_URL || "http://localhost:5173", 
    "http://localhost:5174", 
    "http://localhost:5175",
    "https://travoice1.vercel.app",
    "https://*.vercel.app",
    "https://travoice1.vercel.app"
  ],
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}))

// Socket.IO configuration
const io = socketIo(server, {
  cors: {
    origin: [
      process.env.FRONTEND_URL || "http://localhost:5173", 
      "http://localhost:5174", 
      "http://localhost:5175",
      "https://travoice1.vercel.app",
      "https://*.vercel.app",
      "https://travoice1.vercel.app"
    ],
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    credentials: true,
    allowedHeaders: ["Content-Type", "Authorization"]
  },
  transports: ['websocket', 'polling'],
  allowEIO3: true
})

// Store active rooms and participants
const rooms = new Map()
const participants = new Map()

// Room management
const createRoom = (roomId) => {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, {
      id: roomId,
      participants: new Set(),
      createdAt: Date.now()
    })
  }
  return rooms.get(roomId)
}

const joinRoom = (socket, roomId, language = 'en-US') => {
  const room = createRoom(roomId)
  room.participants.add(socket.id)
  
  participants.set(socket.id, {
    roomId,
    language,
    joinedAt: Date.now()
  })

  socket.join(roomId)
  
  // Notify the user they joined
  socket.emit('room-joined', {
    roomId,
    participants: Array.from(room.participants)
  })

  // Notify other participants
  socket.to(roomId).emit('user-joined', {
    userId: socket.id
  })

  console.log(`User ${socket.id} joined room ${roomId}`)
  return room
}

const leaveRoom = (socket) => {
  const participant = participants.get(socket.id)
  if (!participant) return

  const { roomId } = participant
  const room = rooms.get(roomId)
  
  if (room) {
    room.participants.delete(socket.id)
    
    // Notify other participants
    socket.to(roomId).emit('user-left', {
      userId: socket.id
    })

    // Clean up empty rooms
    if (room.participants.size === 0) {
      rooms.delete(roomId)
      console.log(`Room ${roomId} deleted (empty)`)
    }
  }

  participants.delete(socket.id)
  socket.leave(roomId)
  
  console.log(`User ${socket.id} left room ${roomId}`)
}

// Socket.IO connection handling
io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`)

  // Handle room joining
  socket.on('join-room', (data) => {
    try {
      const { roomId, language } = data
      
      if (!roomId || typeof roomId !== 'string') {
        socket.emit('error', { message: 'Invalid room ID' })
        return
      }

      // Leave any existing room first
      leaveRoom(socket)
      
      // Join new room
      joinRoom(socket, roomId, language)
      
    } catch (error) {
      console.error('Error joining room:', error)
      socket.emit('error', { message: 'Failed to join room' })
    }
  })

  // Handle WebRTC offer
  socket.on('offer', (data) => {
    try {
      const { to, offer } = data
      
      if (!to || !offer) {
        socket.emit('error', { message: 'Invalid offer data' })
        return
      }

      // Forward offer to target room
      socket.to(to).emit('offer', {
        from: socket.id,
        offer
      })
      
      console.log(`Offer forwarded from ${socket.id} to room ${to}`)
      
    } catch (error) {
      console.error('Error handling offer:', error)
      socket.emit('error', { message: 'Failed to send offer' })
    }
  })

  // Handle WebRTC answer
  socket.on('answer', (data) => {
    try {
      const { to, answer } = data
      
      if (!to || !answer) {
        socket.emit('error', { message: 'Invalid answer data' })
        return
      }

      // Forward answer to specific user
      io.to(to).emit('answer', {
        from: socket.id,
        answer
      })
      
      console.log(`Answer forwarded from ${socket.id} to ${to}`)
      
    } catch (error) {
      console.error('Error handling answer:', error)
      socket.emit('error', { message: 'Failed to send answer' })
    }
  })

  // Handle ICE candidates
  socket.on('ice-candidate', (data) => {
    try {
      const { to, candidate } = data
      
      if (!to || !candidate) {
        socket.emit('error', { message: 'Invalid ICE candidate data' })
        return
      }

      // Forward ICE candidate to target room
      socket.to(to).emit('ice-candidate', {
        from: socket.id,
        candidate
      })
      
      console.log(`ICE candidate forwarded from ${socket.id} to room ${to}`)
      
    } catch (error) {
      console.error('Error handling ICE candidate:', error)
      socket.emit('error', { message: 'Failed to send ICE candidate' })
    }
  })

  // Handle call end
  socket.on('end-call', (data) => {
    try {
      const { to } = data
      
      if (to) {
        // Notify specific user
        io.to(to).emit('call-ended', {
          from: socket.id
        })
      } else {
        // Notify room
        const participant = participants.get(socket.id)
        if (participant) {
          socket.to(participant.roomId).emit('call-ended', {
            from: socket.id
          })
        }
      }
      
      console.log(`Call ended by ${socket.id}`)
      
    } catch (error) {
      console.error('Error handling call end:', error)
    }
  })

  // Handle disconnect
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`)
    leaveRoom(socket)
  })

  // Handle errors
  socket.on('error', (error) => {
    console.error(`Socket error from ${socket.id}:`, error)
  })
})

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'Simple Signaling Server for WebRTC Voice Calls',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      stats: '/stats'
    },
    timestamp: new Date().toISOString()
  })
})

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    rooms: rooms.size,
    participants: participants.size
  })
})

// Room statistics endpoint
app.get('/stats', (req, res) => {
  const roomStats = Array.from(rooms.entries()).map(([id, room]) => ({
    id,
    participants: room.participants.size,
    createdAt: room.createdAt
  }))

  res.json({
    totalRooms: rooms.size,
    totalParticipants: participants.size,
    rooms: roomStats
  })
})

// Start server
const PORT = process.env.PORT || 3001
server.listen(PORT, () => {
  console.log(`🚀 Simple Signaling Server running on port ${PORT}`)
  console.log(`📊 Health check: http://localhost:${PORT}/health`)
  console.log(`📈 Stats: http://localhost:${PORT}/stats`)
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
