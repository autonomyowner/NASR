import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { io, Socket } from 'socket.io-client'

interface CallState {
  isConnected: boolean
  isInCall: boolean
  isMuted: boolean
  localStream: MediaStream | null
  remoteStream: MediaStream | null
  peerConnection: RTCPeerConnection | null
  roomId: string
  peerId: string
}

const SimpleCall = () => {
  const [callState, setCallState] = useState<CallState>({
    isConnected: false,
    isInCall: false,
    isMuted: false,
    localStream: null,
    remoteStream: null,
    peerConnection: null,
    roomId: '',
    peerId: ''
  })

  const [inputRoomId, setInputRoomId] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState('en-US')
  const [error, setError] = useState('')
  const [status, setStatus] = useState('Disconnected')
  const [roomAction, setRoomAction] = useState<'create' | 'join'>('create')

  const socketRef = useRef<Socket | null>(null)
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null)
  const localStreamRef = useRef<MediaStream | null>(null)
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null)
  const queuedIceCandidatesRef = useRef<RTCIceCandidateInit[]>([])

  // ICE servers configuration
  const iceServers = useMemo(() => ({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]
  }), [])

  // End call function
  const endCall = useCallback(() => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop())
    }

    if (remoteAudioRef.current) {
      remoteAudioRef.current.pause()
      remoteAudioRef.current.srcObject = null
    }

    if (peerConnectionRef.current) {
      peerConnectionRef.current.close()
      peerConnectionRef.current = null
    }

    setCallState(prev => ({
      ...prev,
      isInCall: false,
      localStream: null,
      remoteStream: null,
      peerConnection: null
    }))
    setStatus('Call ended')
  }, [])

  // Get user media
  const getUserMedia = useCallback(async (): Promise<MediaStream> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      setCallState(prev => ({ ...prev, localStream: stream }))
      localStreamRef.current = stream
      return stream
    } catch (error) {
      console.error('Error accessing microphone:', error)
      throw new Error('Could not access microphone. Please allow microphone access and try again.')
    }
  }, [])

  // Initialize peer connection
  const initializePeerConnection = useCallback(() => {
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close()
    }

    // Clear any queued ICE candidates from previous calls
    queuedIceCandidatesRef.current = []

    const peerConnection = new RTCPeerConnection(iceServers)
    
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && socketRef.current) {
        socketRef.current.emit('ice-candidate', {
          to: callState.roomId,
          candidate: event.candidate
        })
      }
    }

    peerConnection.ontrack = (event) => {
      console.log('✅ Received remote stream - call established!')
      const [remoteStream] = event.streams
      setCallState(prev => ({ ...prev, remoteStream, isInCall: true }))
      setStatus('Call connected - you can hear each other!')
      
      if (remoteAudioRef.current) {
        remoteAudioRef.current.srcObject = remoteStream
        remoteAudioRef.current.play().catch(console.error)
      }
    }

    peerConnection.onconnectionstatechange = () => {
      const state = peerConnection.connectionState
      console.log('🔗 WebRTC Connection state:', state)
      
      if (state === 'connected') {
        setCallState(prev => ({ ...prev, isInCall: true }))
        setStatus('Call connected - audio streaming!')
      } else if (state === 'connecting') {
        setStatus('Connecting call...')
      } else if (state === 'disconnected' || state === 'failed' || state === 'closed') {
        console.log('❌ WebRTC connection lost')
        endCall()
      }
    }

    peerConnectionRef.current = peerConnection
    setCallState(prev => ({ ...prev, peerConnection }))
  }, [callState.roomId, iceServers, endCall])

  // Handle incoming offer
  const handleIncomingOffer = useCallback(async (from: string, offer: RTCSessionDescriptionInit) => {
    try {
      initializePeerConnection()
      const localStream = await getUserMedia()
      
      localStream.getTracks().forEach(track => {
        peerConnectionRef.current?.addTrack(track, localStream)
      })

      await peerConnectionRef.current?.setRemoteDescription(new RTCSessionDescription(offer))
      console.log('✅ Remote description set from offer')
      
      // Process any queued ICE candidates
      if (queuedIceCandidatesRef.current.length > 0) {
        console.log(`🔄 Processing ${queuedIceCandidatesRef.current.length} queued ICE candidates`)
        for (const candidate of queuedIceCandidatesRef.current) {
          try {
            await peerConnectionRef.current?.addIceCandidate(new RTCIceCandidate(candidate))
            console.log('✅ Queued ICE candidate added successfully')
          } catch (error) {
            console.error('❌ Error adding queued ICE candidate:', error)
          }
        }
        queuedIceCandidatesRef.current = []
      }
      
      const answer = await peerConnectionRef.current?.createAnswer()
      await peerConnectionRef.current?.setLocalDescription(answer)
      console.log('📤 Created and sent answer')

      socketRef.current?.emit('answer', {
        to: from,
        answer: answer
      })
    } catch (error) {
      console.error('Error handling offer:', error)
      setError('Failed to handle incoming call')
    }
  }, [initializePeerConnection, getUserMedia])

  // Handle incoming answer
  const handleIncomingAnswer = useCallback(async (answer: RTCSessionDescriptionInit) => {
    try {
      if (peerConnectionRef.current) {
        console.log('📥 Setting remote description from answer')
        await peerConnectionRef.current.setRemoteDescription(new RTCSessionDescription(answer))
        console.log('✅ Remote description set successfully')
        
        // Process any queued ICE candidates
        if (queuedIceCandidatesRef.current.length > 0) {
          console.log(`🔄 Processing ${queuedIceCandidatesRef.current.length} queued ICE candidates`)
          for (const candidate of queuedIceCandidatesRef.current) {
            try {
              await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(candidate))
              console.log('✅ Queued ICE candidate added successfully')
            } catch (error) {
              console.error('❌ Error adding queued ICE candidate:', error)
            }
          }
          queuedIceCandidatesRef.current = []
        }
      }
    } catch (error) {
      console.error('❌ Error handling answer:', error)
      setError('Failed to handle call answer')
    }
  }, [])

  // Handle incoming ICE candidate
  const handleIncomingIceCandidate = useCallback(async (candidate: RTCIceCandidateInit) => {
    try {
      if (peerConnectionRef.current) {
        // Check if remote description is set before adding ICE candidate
        if (peerConnectionRef.current.remoteDescription) {
          await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(candidate))
          console.log('✅ ICE candidate added successfully')
        } else {
          console.log('⏳ ICE candidate queued - waiting for remote description')
          // Queue the candidate for later
          queuedIceCandidatesRef.current.push(candidate)
        }
      }
    } catch (error) {
      console.error('❌ Error handling ICE candidate:', error)
    }
  }, [])

  // Initialize socket connection
  const initializeSocket = useCallback(() => {
    if (socketRef.current) return

    const serverUrl = import.meta.env.VITE_SIGNALING_SERVER_URL || import.meta.env.VITE_SIGNALING_URL || 'http://localhost:3002'
    console.log('🔧 Connecting to signaling server:', serverUrl)
    
    const socket = io(serverUrl, {
      transports: ['websocket']
    })

    socket.on('connect', () => {
      console.log('Connected to signaling server')
      setCallState(prev => ({ ...prev, isConnected: true, peerId: socket.id || '' }))
      setStatus('Connected')
      setError('')
    })

    socket.on('disconnect', () => {
      console.log('Disconnected from signaling server')
      setCallState(prev => ({ ...prev, isConnected: false }))
      setStatus('Disconnected')
    })

    socket.on('connect_error', (error) => {
      console.error('❌ Socket connection error:', error)
      setError(`Connection failed: ${error.message}`)
      setCallState(prev => ({ ...prev, isConnected: false }))
      setStatus('Connection failed')
      
      // Auto-retry connection after 3 seconds
      setTimeout(() => {
        console.log('🔄 Retrying connection...')
        socket.connect()
      }, 3000)
    })

    socket.on('room-joined', (data: { roomId: string, participants: string[] }) => {
      console.log('Joined room:', data.roomId)
      setCallState(prev => ({ ...prev, roomId: data.roomId }))
      setStatus(`In room: ${data.roomId}`)
    })

    socket.on('user-joined', (data: { userId: string }) => {
      console.log('User joined:', data.userId)
      setStatus(`User ${data.userId} joined`)
    })

    socket.on('user-left', (data: { userId: string }) => {
      console.log('User left:', data.userId)
      setStatus(`User ${data.userId} left`)
      if (callState.isInCall) {
        endCall()
      }
    })

    socket.on('offer', async (data: { from: string, offer: RTCSessionDescriptionInit }) => {
      console.log('Received offer from:', data.from)
      await handleIncomingOffer(data.from, data.offer)
    })

    socket.on('answer', async (data: { from: string, answer: RTCSessionDescriptionInit }) => {
      console.log('📥 Received answer from:', data.from)
      await handleIncomingAnswer(data.answer)
    })

    socket.on('ice-candidate', async (data: { from: string, candidate: RTCIceCandidateInit }) => {
      console.log('Received ICE candidate from:', data.from)
      await handleIncomingIceCandidate(data.candidate)
    })

    socketRef.current = socket
  }, [callState.isInCall, handleIncomingOffer, handleIncomingAnswer, handleIncomingIceCandidate, endCall])



  // Generate random room ID
  const generateRoomId = () => {
    const timestamp = Date.now().toString(36)
    const random = Math.random().toString(36).substr(2, 5)
    return `room-${timestamp}-${random}`
  }

  // Create room
  const createRoom = async () => {
    if (!socketRef.current) {
      setError('Not connected to server')
      return
    }

    try {
      setError('')
      const newRoomId = generateRoomId()
      setInputRoomId(newRoomId)
      setStatus('Creating room...')
      
      socketRef.current.emit('join-room', {
        roomId: newRoomId,
        language: selectedLanguage
      })
    } catch (error) {
      console.error('Error creating room:', error)
      setError('Failed to create room')
    }
  }

  // Join room
  const joinRoom = async () => {
    if (!inputRoomId.trim()) {
      setError('Please enter a room ID')
      return
    }

    if (!socketRef.current) {
      setError('Not connected to server')
      return
    }

    try {
      setError('')
      setStatus('Joining room...')
      
      socketRef.current.emit('join-room', {
        roomId: inputRoomId.trim(),
        language: selectedLanguage
      })
    } catch (error) {
      console.error('Error joining room:', error)
      setError('Failed to join room')
    }
  }

  // Handle room action (create or join)
  const handleRoomAction = async () => {
    if (roomAction === 'create') {
      await createRoom()
    } else {
      await joinRoom()
    }
  }

  // Start call
  const startCall = async () => {
    if (!callState.roomId || !socketRef.current) {
      setError('Not in a room or not connected')
      return
    }

    try {
      setError('')
      setStatus('Starting call...')
      console.log('🚀 Starting call in room:', callState.roomId)
      
      initializePeerConnection()
      const localStream = await getUserMedia()
      console.log('🎤 Got local media stream')
      
      localStream.getTracks().forEach(track => {
        peerConnectionRef.current?.addTrack(track, localStream)
      })
      console.log('📡 Added tracks to peer connection')

      const offer = await peerConnectionRef.current?.createOffer()
      await peerConnectionRef.current?.setLocalDescription(offer)
      console.log('📤 Created and set local offer')

      socketRef.current.emit('offer', {
        to: callState.roomId,
        offer: offer
      })
      console.log('📡 Sent offer to room:', callState.roomId)
      
      setStatus('Call started - waiting for answer...')
    } catch (error) {
      console.error('Error starting call:', error)
      setError('Failed to start call')
    }
  }


  // Toggle mute
  const toggleMute = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0]
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled
        setCallState(prev => ({ ...prev, isMuted: !audioTrack.enabled }))
      }
    }
  }

  // Copy peer ID
  const copyPeerId = () => {
    navigator.clipboard.writeText(callState.peerId)
    setStatus('Peer ID copied to clipboard')
    setTimeout(() => setStatus('Connected'), 2000)
  }

  // Copy room ID
  const copyRoomId = () => {
    navigator.clipboard.writeText(inputRoomId)
    setStatus('Room ID copied to clipboard')
    setTimeout(() => setStatus('Connected'), 2000)
  }

  // Initialize on mount
  useEffect(() => {
    initializeSocket()
    
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
      endCall()
    }
  }, [initializeSocket, endCall])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endCall()
    }
  }, [endCall])


  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-20">
        <div className="w-full h-full bg-gradient-to-br from-cyan-500/5 to-blue-500/5"></div>
      </div>
      
      <div className="relative z-10 w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            بسم الله الرحمن الرحيم
          </h1>
          <h2 className="text-2xl font-semibold text-cyan-400 mb-4">
            Phase 1 - Simple Voice Call
          </h2>
          <p className="text-gray-300">
            Connect with others instantly - No login required
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl">
          
          {/* Connection Status */}
          <div className="flex items-center justify-center mb-6">
            <div className={`w-3 h-3 rounded-full mr-3 ${
              callState.isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
            }`}></div>
            <span className="text-white font-medium">{status}</span>
            {!callState.isConnected && (
              <div className="ml-2">
                <span className="text-red-400 text-sm">(Check console for details)</span>
                <button
                  onClick={() => {
                    console.log('🔧 Manual connection test')
                    console.log('🔧 Environment URL:', import.meta.env.VITE_SIGNALING_SERVER_URL)
                    console.log('🔧 Socket ref:', socketRef.current)
                    console.log('🔧 Call state:', callState)
                    if (socketRef.current) {
                      console.log('🔧 Socket connected:', socketRef.current.connected)
                      console.log('🔧 Socket ID:', socketRef.current.id)
                      if (!socketRef.current.connected) {
                        console.log('🔧 Attempting to reconnect...')
                        socketRef.current.connect()
                      }
                    } else {
                      console.log('🔧 No socket ref - initializing...')
                      initializeSocket()
                    }
                  }}
                  className="ml-2 text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded hover:bg-blue-500/30"
                >
                  Reconnect
                </button>
              </div>
            )}
          </div>

          {/* Your ID */}
          {callState.isConnected && (
            <div className="mb-6">
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Your ID
              </label>
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={callState.peerId}
                  readOnly
                  className="flex-1 p-3 bg-white/10 border border-white/20 rounded-xl text-white font-mono text-sm"
                />
                <button
                  onClick={copyPeerId}
                  className="px-4 py-3 bg-cyan-500 hover:bg-cyan-600 text-white rounded-xl font-medium transition-colors"
                >
                  Copy
                </button>
              </div>
            </div>
          )}

          {/* Room Action Selection */}
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-medium mb-3">
              Room Action
            </label>
            <div className="flex space-x-2 mb-4">
              <button
                onClick={() => setRoomAction('create')}
                className={`flex-1 py-2 px-4 rounded-xl font-medium transition-colors ${
                  roomAction === 'create'
                    ? 'bg-green-500 text-white'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                🆕 Create Room
              </button>
              <button
                onClick={() => setRoomAction('join')}
                className={`flex-1 py-2 px-4 rounded-xl font-medium transition-colors ${
                  roomAction === 'join'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                🚪 Join Room
              </button>
            </div>
          </div>

          {/* Room ID Input */}
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              {roomAction === 'create' ? 'Room ID (Auto-generated)' : 'Room ID'}
            </label>
            <div className="flex space-x-3">
              <input
                type="text"
                value={inputRoomId}
                onChange={(e) => setInputRoomId(e.target.value)}
                placeholder={roomAction === 'create' ? 'Room ID will be generated...' : 'Enter room ID (e.g., room-123)'}
                readOnly={roomAction === 'create'}
                className={`flex-1 p-3 border rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 ${
                  roomAction === 'create'
                    ? 'bg-white/5 border-white/10 text-gray-400'
                    : 'bg-white/10 border-white/20'
                }`}
              />
              <button
                onClick={handleRoomAction}
                disabled={!callState.isConnected || (roomAction === 'join' && !inputRoomId.trim())}
                className={`px-6 py-3 rounded-xl font-medium transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed text-white ${
                  roomAction === 'create'
                    ? 'bg-green-500 hover:bg-green-600'
                    : 'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {roomAction === 'create' ? 'Create' : 'Join'}
              </button>
            </div>
            {roomAction === 'create' && (
              <div className="mt-2">
                <p className="text-xs text-gray-400 mb-2">
                  💡 A unique room ID will be generated for you to share with others
                </p>
                {inputRoomId && (
                  <button
                    onClick={copyRoomId}
                    className="text-xs bg-green-500/20 text-green-300 px-3 py-1 rounded-lg hover:bg-green-500/30 transition-colors"
                  >
                    📋 Copy Room ID
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Language Selection */}
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Language
            </label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="w-full p-3 bg-white/10 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
            >
              <option value="en-US" className="bg-slate-800">English</option>
              <option value="es-ES" className="bg-slate-800">Spanish</option>
              <option value="fr-FR" className="bg-slate-800">French</option>
              <option value="de-DE" className="bg-slate-800">German</option>
              <option value="it-IT" className="bg-slate-800">Italian</option>
              <option value="pt-PT" className="bg-slate-800">Portuguese</option>
              <option value="ar-SA" className="bg-slate-800">Arabic</option>
              <option value="zh-CN" className="bg-slate-800">Chinese</option>
              <option value="ja-JP" className="bg-slate-800">Japanese</option>
              <option value="ko-KR" className="bg-slate-800">Korean</option>
              <option value="hi-IN" className="bg-slate-800">Hindi</option>
            </select>
          </div>

          {/* Call Controls */}
          {callState.roomId && (
            <div className="space-y-4">
              <div className="text-center">
                <p className="text-gray-300 text-sm mb-4">
                  Room: <span className="text-cyan-400 font-medium">{callState.roomId}</span>
                </p>
              </div>

              <div className="flex justify-center space-x-4">
                {!callState.isInCall ? (
                  <button
                    onClick={startCall}
                    disabled={!callState.isConnected}
                    className="px-8 py-4 bg-green-500 hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl font-bold text-lg transition-colors"
                  >
                    📞 Start Call
                  </button>
                ) : (
                  <>
                    <button
                      onClick={toggleMute}
                      className={`px-6 py-3 rounded-xl font-medium transition-colors ${
                        callState.isMuted
                          ? 'bg-red-500 hover:bg-red-600 text-white'
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      }`}
                    >
                      {callState.isMuted ? '🔇 Unmute' : '🎤 Mute'}
                    </button>
                    <button
                      onClick={endCall}
                      className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium transition-colors"
                    >
                      📞 End Call
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="mt-6 p-4 bg-red-500/20 border border-red-400/30 rounded-xl">
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          {/* Instructions */}
          <div className="mt-8 p-4 bg-blue-500/10 border border-blue-400/30 rounded-xl">
            <h3 className="text-blue-300 font-medium mb-2">How to use:</h3>
            <div className="text-gray-300 text-sm space-y-2">
              <div>
                <strong className="text-green-300">To Create a Room:</strong>
                <ol className="ml-4 mt-1 space-y-1">
                  <li>1. Click "🆕 Create Room"</li>
                  <li>2. Click "Create" to generate a room ID</li>
                  <li>3. Share the room ID with others</li>
                  <li>4. Click "Start Call" when ready</li>
                </ol>
              </div>
              <div>
                <strong className="text-blue-300">To Join a Room:</strong>
                <ol className="ml-4 mt-1 space-y-1">
                  <li>1. Click "🚪 Join Room"</li>
                  <li>2. Enter the room ID you received</li>
                  <li>3. Click "Join" to enter the room</li>
                  <li>4. Wait for the call to start</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden Audio Element */}
      <audio
        ref={remoteAudioRef}
        autoPlay
        playsInline
        style={{ display: 'none' }}
      />
    </div>
  )
}

export default SimpleCall
