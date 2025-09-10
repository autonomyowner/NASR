#!/usr/bin/env node

const WebSocket = require('ws');
const http = require('http');

console.log('🚀 Starting Mock Translation Services...');

// Mock STT Service (Port 8001)
const sttServer = http.createServer();
const sttWss = new WebSocket.Server({ server: sttServer, path: '/ws/stt' });

sttWss.on('connection', (ws) => {
  console.log('🎤 STT client connected');
  
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      console.log('🎤 STT received:', message.type || 'audio data');
      
      // Mock transcription response
      setTimeout(() => {
        ws.send(JSON.stringify({
          type: 'transcription',
          text: 'Hello, this is mock speech recognition',
          confidence: 0.95,
          timestamp: Date.now()
        }));
      }, 100);
    } catch (e) {
      // Handle binary audio data
      setTimeout(() => {
        ws.send(JSON.stringify({
          type: 'transcription', 
          text: 'Mock transcription from audio',
          confidence: 0.9,
          timestamp: Date.now()
        }));
      }, 150);
    }
  });
  
  ws.on('close', () => {
    console.log('🎤 STT client disconnected');
  });
});

sttServer.listen(8001, () => {
  console.log('🎤 Mock STT service running on ws://localhost:8001/ws/stt');
});

// Mock MT Service (Port 8002) 
const mtServer = http.createServer();
const mtWss = new WebSocket.Server({ server: mtServer, path: '/ws/translate' });

mtWss.on('connection', (ws) => {
  console.log('🌐 MT client connected');
  
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      console.log('🌐 MT received:', message.text || 'translation request');
      
      // Mock translation response
      setTimeout(() => {
        const translations = {
          'en': { 'es': 'Hola, esta es traducción simulada', 'fr': 'Bonjour, ceci est une traduction simulée' },
          'es': { 'en': 'Hello, this is mock translation', 'fr': 'Bonjour, ceci est une traduction simulée' },
          'fr': { 'en': 'Hello, this is mock translation', 'es': 'Hola, esta es traducción simulada' }
        };
        
        const source = message.source_language || 'en';
        const target = message.target_language || 'es';
        const translated = translations[source]?.[target] || 'Mock translation result';
        
        ws.send(JSON.stringify({
          type: 'translation',
          original_text: message.text,
          translated_text: translated,
          source_language: source,
          target_language: target,
          confidence: 0.92,
          timestamp: Date.now()
        }));
      }, 80);
    } catch (e) {
      console.error('MT parsing error:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('🌐 MT client disconnected');
  });
});

mtServer.listen(8002, () => {
  console.log('🌐 Mock MT service running on ws://localhost:8002/ws/translate');
});

// Mock TTS Service (Port 8003)
const ttsServer = http.createServer();
const ttsWss = new WebSocket.Server({ server: ttsServer, path: '/ws/synthesize' });

ttsWss.on('connection', (ws) => {
  console.log('🔊 TTS client connected');
  
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      console.log('🔊 TTS received:', message.text || 'synthesis request');
      
      // Mock TTS response with fake audio data
      setTimeout(() => {
        ws.send(JSON.stringify({
          type: 'audio',
          audio_data: 'mock_audio_base64_data_here',
          text: message.text,
          voice: message.voice || 'default',
          language: message.language || 'en',
          timestamp: Date.now()
        }));
      }, 120);
    } catch (e) {
      console.error('TTS parsing error:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('🔊 TTS client disconnected');
  });
});

ttsServer.listen(8003, () => {
  console.log('🔊 Mock TTS service running on ws://localhost:8003/ws/synthesize');
});

// Health check endpoints
sttServer.on('request', (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy', service: 'STT' }));
  }
});

mtServer.on('request', (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy', service: 'MT' }));
  }
});

ttsServer.on('request', (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'healthy', service: 'TTS' }));
  }
});

console.log('✅ All mock translation services started!');
console.log('📋 Services available:');
console.log('   🎤 STT: ws://localhost:8001/ws/stt');
console.log('   🌐 MT:  ws://localhost:8002/ws/translate'); 
console.log('   🔊 TTS: ws://localhost:8003/ws/synthesize');
console.log('');
console.log('💡 These are mock services for testing the UI and WebSocket connections.');
console.log('   They will respond with simulated translation data.');