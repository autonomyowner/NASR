const express = require('express')
const { createServer } = require('http')
const { Server } = require('socket.io')
const cors = require('cors')

const app = express()
const server = createServer(app)

// Enable CORS for all origins (adjust in production)
app.use(cors({
  origin: [
    "http://localhost:5173", 
    "http://localhost:5174", 
    "http://localhost:5175", 
    "http://localhost:5176", 
    "http://localhost:3000", 
    "http://192.168.1.4:5174", 
    "http://192.168.1.4:5173", 
    "http://192.168.1.4:5175", 
    "http://192.168.1.4:5176", 
    "https://travoice1.vercel.app",
    "https://*.vercel.app"
  ],
  methods: ["GET", "POST"],
  credentials: true
}))

const io = new Server(server, {
  cors: {
    origin: [
      "http://localhost:5173", 
      "http://localhost:5174", 
      "http://localhost:5175", 
      "http://localhost:5176", 
      "http://localhost:3000", 
      "http://192.168.1.4:5174", 
      "http://192.168.1.4:5173", 
      "http://192.168.1.4:5175", 
      "http://192.168.1.4:5176", 
      "https://travoice1.vercel.app",
      "https://*.vercel.app"
    ],
    methods: ["GET", "POST"],
    credentials: true
  }
})

// Store connected users
const connectedUsers = new Map()
const userSockets = new Map()

// Store rooms and participants
const rooms = new Map()
const roomParticipants = new Map() // roomId -> Set of participant IDs

app.get('/', (req, res) => {
  res.json({
    message: 'Travoice Signaling Server',
    version: '1.0.0',
    connectedUsers: connectedUsers.size,
    activeRooms: rooms.size,
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

  // Room management handlers
  socket.on('create-room', ({ name, sourceLanguage, targetLanguage, maxParticipants, isPublic, participantName }) => {
    console.log(`Creating room: ${name} by ${participantName}`)
    
    const roomId = `room_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const user = connectedUsers.get(socket.id)
    
    if (!user) {
      socket.emit('room-error', { error: 'User not found' })
      return
    }

    const room = {
      id: roomId,
      name: name,
      participants: [],
      languageSettings: {
        sourceLanguage: sourceLanguage,
        targetLanguage: targetLanguage
      },
      createdAt: new Date(),
      isActive: true,
      hostId: user.peerId,
      shareableLink: `${process.env.FRONTEND_URL || 'http://localhost:5173'}/room/${roomId}`,
      maxParticipants: maxParticipants || 10,
      isPublic: isPublic || false
    }

    const participant = {
      id: user.peerId,
      name: participantName,
      isHost: true,
      isConnected: true,
      language: sourceLanguage,
      joinedAt: new Date(),
      peerId: user.peerId
    }

    room.participants.push(participant)
    rooms.set(roomId, room)
    roomParticipants.set(roomId, new Set([user.peerId]))

    // Join the room
    socket.join(roomId)
    
    // Send room created event
    socket.emit('room-created', room)
    console.log(`Room created: ${roomId} with ${room.participants.length} participants`)
  })

  socket.on('join-room', ({ roomId, participantName }) => {
    console.log(`Joining room: ${roomId} by ${participantName}`)
    
    const room = rooms.get(roomId)
    const user = connectedUsers.get(socket.id)
    
    if (!room) {
      socket.emit('room-error', { error: 'Room not found' })
      return
    }

    if (!user) {
      socket.emit('room-error', { error: 'User not found' })
      return
    }

    // Check if room is full
    if (room.participants.length >= room.maxParticipants) {
      socket.emit('room-error', { error: 'Room is full' })
      return
    }

    // Check if user is already in the room
    const existingParticipant = room.participants.find(p => p.id === user.peerId)
    if (existingParticipant) {
      socket.emit('room-error', { error: 'Already in this room' })
      return
    }

    const participant = {
      id: user.peerId,
      name: participantName,
      isHost: false,
      isConnected: true,
      language: room.languageSettings.sourceLanguage,
      joinedAt: new Date(),
      peerId: user.peerId
    }

    room.participants.push(participant)
    roomParticipants.get(roomId).add(user.peerId)

    // Join the room
    socket.join(roomId)
    
    // Notify all participants in the room
    io.to(roomId).emit('participant-joined', participant)
    
    // Send room joined event to the new participant
    socket.emit('room-joined', { room, participant })
    console.log(`User ${participantName} joined room: ${roomId}`)
  })

  socket.on('leave-room', ({ roomId }) => {
    console.log(`Leaving room: ${roomId}`)
    
    const room = rooms.get(roomId)
    const user = connectedUsers.get(socket.id)
    
    if (!room || !user) {
      return
    }

    const participant = room.participants.find(p => p.id === user.peerId)
    if (!participant) {
      return
    }

    // Remove participant from room
    room.participants = room.participants.filter(p => p.id !== user.peerId)
    roomParticipants.get(roomId)?.delete(user.peerId)

    // Leave the room
    socket.leave(roomId)
    
    // Notify other participants
    io.to(roomId).emit('participant-left', user.peerId)
    
    // If no participants left, delete the room
    if (room.participants.length === 0) {
      rooms.delete(roomId)
      roomParticipants.delete(roomId)
      console.log(`Room ${roomId} deleted (no participants)`)
    } else {
      // If host left, assign new host
      if (participant.isHost && room.participants.length > 0) {
        room.participants[0].isHost = true
        room.hostId = room.participants[0].id
        io.to(roomId).emit('room-updated', room)
      }
    }
    
    // Send room left event
    socket.emit('room-left')
    console.log(`User left room: ${roomId}`)
  })

  // Handle disconnect
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`)
    
    const user = connectedUsers.get(socket.id)
    if (user) {
      // Remove from all rooms
      for (const [roomId, participants] of roomParticipants.entries()) {
        if (participants.has(user.peerId)) {
          const room = rooms.get(roomId)
          if (room) {
            const participant = room.participants.find(p => p.id === user.peerId)
            if (participant) {
              room.participants = room.participants.filter(p => p.id !== user.peerId)
              participants.delete(user.peerId)
              
              // Notify other participants
              io.to(roomId).emit('participant-left', user.peerId)
              
              // If no participants left, delete the room
              if (room.participants.length === 0) {
                rooms.delete(roomId)
                roomParticipants.delete(roomId)
                console.log(`Room ${roomId} deleted (no participants)`)
              } else {
                // If host left, assign new host
                if (participant.isHost && room.participants.length > 0) {
                  room.participants[0].isHost = true
                  room.hostId = room.participants[0].id
                  io.to(roomId).emit('room-updated', room)
                }
              }
            }
          }
        }
      }
      
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