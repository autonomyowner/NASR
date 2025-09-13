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

// Store connected users and rooms
const connectedUsers = new Map()
const userSockets = new Map()
const rooms = new Map()

// Room management functions
function generateRoomId() {
  return `room_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function generateParticipantId() {
  return `participant_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function createRoom(roomData, hostSocket) {
  const roomId = generateRoomId()
  const hostParticipant = {
    id: generateParticipantId(),
    name: roomData.participantName,
    isHost: true,
    isConnected: true,
    language: roomData.sourceLanguage,
    joinedAt: new Date(),
    peerId: connectedUsers.get(hostSocket.id)?.peerId || `peer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const room = {
    id: roomId,
    name: roomData.name,
    participants: [hostParticipant],
    languageSettings: {
      sourceLanguage: roomData.sourceLanguage,
      targetLanguage: roomData.targetLanguage
    },
    createdAt: new Date(),
    isActive: true,
    hostId: hostParticipant.id,
    shareableLink: `http://localhost:5173/room/${roomId}`
  }

  rooms.set(roomId, room)
  hostSocket.join(roomId)
  hostSocket.roomId = roomId
  hostSocket.participantId = hostParticipant.id

  return { room, participant: hostParticipant }
}

function joinRoom(roomId, participantName, socket) {
  const room = rooms.get(roomId)
  if (!room) {
    throw new Error('Room not found')
  }

  if (room.participants.length >= (room.maxParticipants || 10)) {
    throw new Error('Room is full')
  }

  const participant = {
    id: generateParticipantId(),
    name: participantName,
    isHost: false,
    isConnected: true,
    language: room.languageSettings.sourceLanguage,
    joinedAt: new Date(),
    peerId: connectedUsers.get(socket.id)?.peerId || `peer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  room.participants.push(participant)
  socket.join(roomId)
  socket.roomId = roomId
  socket.participantId = participant.id

  return { room, participant }
}

function leaveRoom(socket) {
  if (!socket.roomId) return

  const room = rooms.get(socket.roomId)
  if (!room) return

  // Remove participant from room
  room.participants = room.participants.filter(p => p.id !== socket.participantId)
  
  // If host left, assign new host or close room
  if (socket.participantId === room.hostId) {
    if (room.participants.length > 0) {
      room.participants[0].isHost = true
      room.hostId = room.participants[0].id
    } else {
      rooms.delete(socket.roomId)
    }
  }

  socket.leave(socket.roomId)
  socket.roomId = null
  socket.participantId = null

  return room
}

app.get('/', (req, res) => {
  res.json({
    message: 'Enhanced Travoice Signaling Server',
    version: '2.0.0',
    connectedUsers: connectedUsers.size,
    activeRooms: rooms.size,
    uptime: process.uptime()
  })
})

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() })
})

app.get('/rooms', (req, res) => {
  const roomList = Array.from(rooms.values()).map(room => ({
    id: room.id,
    name: room.name,
    participantCount: room.participants.length,
    createdAt: room.createdAt,
    isActive: room.isActive
  }))
  res.json({ rooms: roomList })
})

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`)

  // Generate a simple peer ID
  const peerId = `peer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  // Store user info
  connectedUsers.set(socket.id, {
    peerId: peerId,
    socketId: socket.id,
    connectedAt: new Date()
  })
  userSockets.set(peerId, socket)

  // Send peer ID to client
  socket.emit('peer-id', peerId)
  console.log(`Assigned peer ID: ${peerId} to socket: ${socket.id}`)
  console.log(`Total connected users: ${connectedUsers.size}`)

  // Room management events
  socket.on('create-room', (data) => {
    try {
      const { room, participant } = createRoom(data, socket)
      socket.emit('room-created', room)
      
      // Notify all participants in the room
      io.to(room.id).emit('participant-joined', participant)
      
      console.log(`Room created: ${room.id} by ${participant.name}`)
    } catch (error) {
      socket.emit('room-error', { error: error.message })
    }
  })

  socket.on('join-room', (data) => {
    try {
      const { room, participant } = joinRoom(data.roomId, data.participantName, socket)
      socket.emit('room-joined', { room, participant })
      
      // Notify all other participants in the room
      socket.to(room.id).emit('participant-joined', participant)
      
      console.log(`${participant.name} joined room: ${room.id}`)
    } catch (error) {
      socket.emit('room-error', { error: error.message })
    }
  })

  socket.on('leave-room', (data) => {
    const room = leaveRoom(socket)
    if (room) {
      socket.emit('room-left')
      
      // Notify remaining participants
      socket.to(room.id).emit('participant-left', socket.participantId)
      
      console.log(`User left room: ${data.roomId}`)
    }
  })

  // WebRTC signaling events (room-based)
  socket.on('call-request', (data) => {
    const targetSocket = userSockets.get(data.to)
    if (targetSocket) {
      targetSocket.emit('incoming-call', {
        from: data.from,
        offer: data.offer
      })
      console.log(`Call request from ${data.from} to ${data.to}`)
    } else {
      socket.emit('call-failed', { reason: 'User not found' })
    }
  })

  socket.on('call-answer', (data) => {
    const targetSocket = userSockets.get(data.to)
    if (targetSocket) {
      targetSocket.emit('call-answered', {
        from: data.from,
        answer: data.answer
      })
      console.log(`Call answered by ${data.from} to ${data.to}`)
    }
  })

  socket.on('ice-candidate', (data) => {
    const targetSocket = userSockets.get(data.to)
    if (targetSocket) {
      targetSocket.emit('ice-candidate', {
        candidate: data.candidate
      })
    }
  })

  socket.on('end-call', (data) => {
    const targetSocket = userSockets.get(data.to)
    if (targetSocket) {
      targetSocket.emit('call-ended')
      console.log(`Call ended by ${data.from} to ${data.to}`)
    }
  })

  // Legacy peer-to-peer events (for backward compatibility)
  socket.on('register', (peerId) => {
    const userInfo = connectedUsers.get(socket.id)
    if (userInfo) {
      userInfo.peerId = peerId
      userSockets.set(peerId, socket)
      console.log(`User registered with peer ID: ${peerId}`)
    }
  })

  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`)
    
    // Handle room cleanup
    if (socket.roomId) {
      const room = leaveRoom(socket)
      if (room) {
        socket.to(room.id).emit('participant-left', socket.participantId)
      }
    }
    
    // Clean up user data
    const userInfo = connectedUsers.get(socket.id)
    if (userInfo) {
      userSockets.delete(userInfo.peerId)
    }
    connectedUsers.delete(socket.id)
    
    console.log(`Total connected users: ${connectedUsers.size}`)
  })
})

const PORT = process.env.PORT || 3002
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Enhanced Travoice Signaling Server running on port ${PORT}`)
  console.log(`📡 WebSocket endpoint: ws://192.168.1.4:${PORT}`)
  console.log(`🌐 HTTP endpoint: http://192.168.1.4:${PORT}`)
  console.log(`💪 Ready to handle room-based WebRTC signaling!`)
})

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nSIGINT received, shutting down gracefully')
  server.close(() => {
    console.log('Server closed')
    process.exit(0)
  })
})
