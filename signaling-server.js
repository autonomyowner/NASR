// Simple WebRTC signaling server using Socket.IO
// Deploy this on Railway, Render, or Heroku for free

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());

// Store connected users
const users = new Map();

// Handle WebRTC signaling
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  // Register user with peer ID
  socket.on('register', (peerId) => {
    users.set(peerId, socket.id);
    users.set(socket.id, peerId);
    socket.join(peerId);
    console.log(`User ${peerId} registered with socket ${socket.id}`);
    
    // Send updated user list to all clients
    io.emit('users-online', Array.from(users.keys()).filter(key => typeof key === 'string' && key !== socket.id));
  });

  // Handle call request
  socket.on('call-request', ({ to, from, offer }) => {
    const targetSocketId = users.get(to);
    if (targetSocketId) {
      io.to(targetSocketId).emit('incoming-call', { from, offer });
      console.log(`Call from ${from} to ${to}`);
    } else {
      socket.emit('call-failed', { reason: 'User not online' });
    }
  });

  // Handle call answer
  socket.on('call-answer', ({ to, from, answer }) => {
    const targetSocketId = users.get(to);
    if (targetSocketId) {
      io.to(targetSocketId).emit('call-answered', { from, answer });
    }
  });

  // Handle ICE candidates
  socket.on('ice-candidate', ({ to, candidate }) => {
    const targetSocketId = users.get(to);
    if (targetSocketId) {
      io.to(targetSocketId).emit('ice-candidate', { candidate });
    }
  });

  // Handle call end
  socket.on('end-call', ({ to }) => {
    const targetSocketId = users.get(to);
    if (targetSocketId) {
      io.to(targetSocketId).emit('call-ended');
    }
  });

  // Handle disconnect
  socket.on('disconnect', () => {
    const peerId = users.get(socket.id);
    if (peerId) {
      users.delete(peerId);
      users.delete(socket.id);
      console.log(`User ${peerId} disconnected`);
      
      // Update user list
      io.emit('users-online', Array.from(users.keys()).filter(key => typeof key === 'string' && key !== socket.id));
    }
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Signaling server running on port ${PORT}`);
  console.log('Ready to handle WebRTC signaling!');
});

module.exports = app;