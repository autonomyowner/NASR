import React, { useState, useEffect } from 'react'
import { roomService, type Room, type Participant, type RoomSettings } from '../services/roomService'
import { useNotifications } from '../hooks/useNotifications'

interface EnhancedRoomManagerProps {
  onRoomJoined: (room: Room, participant: Participant) => void
  onRoomLeft: () => void
}

const LANGUAGES = [
  { code: 'en-US', name: 'English', flag: '🇺🇸' },
  { code: 'es-ES', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr-FR', name: 'French', flag: '🇫🇷' },
  { code: 'de-DE', name: 'German', flag: '🇩🇪' },
  { code: 'it-IT', name: 'Italian', flag: '🇮🇹' },
  { code: 'pt-PT', name: 'Portuguese', flag: '🇵🇹' },
  { code: 'ar-SA', name: 'Arabic', flag: '🇸🇦' },
  { code: 'zh-CN', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ja-JP', name: 'Japanese', flag: '🇯🇵' },
  { code: 'ko-KR', name: 'Korean', flag: '🇰🇷' },
  { code: 'hi-IN', name: 'Hindi', flag: '🇮🇳' }
]

const EnhancedRoomManager: React.FC<EnhancedRoomManagerProps> = ({ 
  onRoomJoined, 
  onRoomLeft 
}) => {
  const [activeTab, setActiveTab] = useState<'create' | 'join'>('create')
  const [roomName, setRoomName] = useState('')
  const [participantName, setParticipantName] = useState('')
  const [sourceLanguage, setSourceLanguage] = useState('en-US')
  const [targetLanguage, setTargetLanguage] = useState('es-ES')
  const [roomId, setRoomId] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [createdRoom, setCreatedRoom] = useState<Room | null>(null)
  
  const notifications = useNotifications()

  useEffect(() => {
    // Set up room service callbacks
    roomService.onRoomCreated = (room: Room) => {
      setCreatedRoom(room)
      setIsConnecting(false)
      notifications.success('Room Created!', `Room "${room.name}" is ready. Share the link with others.`)
    }

    roomService.onRoomJoined = (room: Room, participant: Participant) => {
      setIsConnecting(false)
      notifications.success('Joined Room!', `Welcome to "${room.name}"`)
      onRoomJoined(room, participant)
    }

    roomService.onRoomLeft = () => {
      setCreatedRoom(null)
      onRoomLeft()
    }

    roomService.onRoomError = (error: string) => {
      setIsConnecting(false)
      notifications.error('Room Error', error)
    }

    // Check if we're joining via URL
    const urlParams = new URLSearchParams(window.location.search)
    const joinRoomId = urlParams.get('room')
    if (joinRoomId) {
      setRoomId(joinRoomId)
      setActiveTab('join')
    }
    
    // Check if we're on a room URL path
    const pathParts = window.location.pathname.split('/')
    if (pathParts[1] === 'room' && pathParts[2]) {
      setRoomId(pathParts[2])
      setActiveTab('join')
    }

    return () => {
      roomService.onRoomCreated = null
      roomService.onRoomJoined = null
      roomService.onRoomLeft = null
      roomService.onRoomError = null
    }
  }, [notifications, onRoomJoined, onRoomLeft])

  const handleCreateRoom = async () => {
    if (!roomName.trim() || !participantName.trim()) {
      notifications.warning('Missing Information', 'Please enter both room name and your name')
      return
    }

    setIsConnecting(true)
    
    const settings: RoomSettings = {
      name: roomName.trim(),
      sourceLanguage,
      targetLanguage,
      maxParticipants: 10,
      isPublic: false
    }

    roomService.createRoom(settings, participantName.trim())
  }

  const handleJoinRoom = async () => {
    if (!roomId.trim() || !participantName.trim()) {
      notifications.warning('Missing Information', 'Please enter both room ID and your name')
      return
    }

    setIsConnecting(true)
    roomService.joinRoom(roomId.trim(), participantName.trim())
  }

  const copyRoomLink = () => {
    if (createdRoom) {
      const link = roomService.generateShareableLink(createdRoom.id)
      navigator.clipboard.writeText(link)
      notifications.success('Link Copied!', 'Room link copied to clipboard')
    }
  }


  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
          Create or Join a <span className="text-cyan-400">Translation Room</span>
        </h2>
        <p className="text-gray-300 text-lg max-w-2xl mx-auto">
          Start a conversation with real-time translation. Create a room and share the link, or join an existing room.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex justify-center">
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-1 border border-white/20">
          <button
            onClick={() => setActiveTab('create')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all duration-300 ${
              activeTab === 'create'
                ? 'bg-cyan-500 text-slate-900 shadow-lg'
                : 'text-gray-300 hover:text-white'
            }`}
          >
            Create Room
          </button>
          <button
            onClick={() => setActiveTab('join')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all duration-300 ${
              activeTab === 'join'
                ? 'bg-cyan-500 text-slate-900 shadow-lg'
                : 'text-gray-300 hover:text-white'
            }`}
          >
            Join Room
          </button>
        </div>
      </div>

      {/* Room Creation/Join Interface */}
      <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-8 rounded-3xl shadow-2xl">
        {activeTab === 'create' ? (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-white mb-2">Create New Room</h3>
              <p className="text-gray-300">Set up a new translation room and invite others to join</p>
            </div>

            {/* Room Name */}
            <div>
              <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                <span className="text-lg mr-2">🏠</span>
                Room Name
              </label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="e.g., Team Meeting, Language Exchange"
                className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
              />
            </div>

            {/* Participant Name */}
            <div>
              <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                <span className="text-lg mr-2">👤</span>
                Your Name
              </label>
              <input
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                placeholder="Enter your name"
                className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
              />
            </div>

            {/* Language Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                  <span className="text-lg mr-2">🗣️</span>
                  Your Language
                </label>
                <select
                  value={sourceLanguage}
                  onChange={(e) => setSourceLanguage(e.target.value)}
                  className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white backdrop-blur-sm transition-all duration-300"
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.code} className="bg-slate-800 text-white">
                      {lang.flag} {lang.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                  <span className="text-lg mr-2">🌐</span>
                  Translate To
                </label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white backdrop-blur-sm transition-all duration-300"
                >
                  {LANGUAGES.map(lang => (
                    <option key={lang.code} value={lang.code} className="bg-slate-800 text-white">
                      {lang.flag} {lang.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Create Room Button */}
            <button
              onClick={handleCreateRoom}
              disabled={isConnecting || !roomName.trim() || !participantName.trim()}
              className="w-full py-4 text-xl font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-900 hover:from-cyan-400 hover:to-cyan-500 shadow-cyan-500/25 hover:shadow-cyan-500/40"
            >
              {isConnecting ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-5 h-5 border-2 border-slate-900 border-t-transparent rounded-full animate-spin"></div>
                  <span>Creating Room...</span>
                </div>
              ) : (
                <div className="flex items-center justify-center space-x-2">
                  <span>🚀</span>
                  <span>Create Room</span>
                </div>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-white mb-2">Join Existing Room</h3>
              <p className="text-gray-300">Enter the room ID or click a shared link to join</p>
            </div>

            {/* Room ID */}
            <div>
              <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                <span className="text-lg mr-2">🔗</span>
                Room ID
              </label>
              <input
                type="text"
                value={roomId}
                onChange={(e) => setRoomId(e.target.value)}
                placeholder="Enter room ID (e.g., abc-123-def)"
                className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
              />
            </div>

            {/* Participant Name */}
            <div>
              <label className="block text-gray-300 font-semibold mb-3 flex items-center">
                <span className="text-lg mr-2">👤</span>
                Your Name
              </label>
              <input
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                placeholder="Enter your name"
                className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
              />
            </div>

            {/* Join Room Button */}
            <button
              onClick={handleJoinRoom}
              disabled={isConnecting || !roomId.trim() || !participantName.trim()}
              className="w-full py-4 text-xl font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-900 hover:from-cyan-400 hover:to-cyan-500 shadow-cyan-500/25 hover:shadow-cyan-500/40"
            >
              {isConnecting ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-5 h-5 border-2 border-slate-900 border-t-transparent rounded-full animate-spin"></div>
                  <span>Joining Room...</span>
                </div>
              ) : (
                <div className="flex items-center justify-center space-x-2">
                  <span>🚪</span>
                  <span>Join Room</span>
                </div>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Created Room Info */}
      {createdRoom && (
        <div className="glass-effect backdrop-blur-xl bg-white/10 border border-green-400/30 p-6 rounded-3xl shadow-2xl">
          <div className="text-center">
            <h3 className="text-xl font-bold text-white mb-4">🎉 Room Created Successfully!</h3>
            <div className="space-y-4">
              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <p className="text-gray-300 text-sm mb-1">Room Name</p>
                <p className="text-white font-semibold">{createdRoom.name}</p>
              </div>
              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <p className="text-gray-300 text-sm mb-1">Room ID</p>
                <p className="text-white font-mono text-lg">{createdRoom.id}</p>
              </div>
              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <p className="text-gray-300 text-sm mb-1">Shareable Link</p>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={roomService.generateShareableLink(createdRoom.id)}
                    readOnly
                    className="flex-1 p-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm font-mono"
                  />
                  <button
                    onClick={copyRoomLink}
                    className="px-4 py-2 bg-cyan-500 text-slate-900 rounded-lg hover:bg-cyan-400 transition-colors font-semibold"
                  >
                    📋 Copy
                  </button>
                </div>
              </div>
              <p className="text-gray-400 text-sm">
                Share this link with others to invite them to your room. They can join instantly!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl">
        <h4 className="text-lg font-bold text-white mb-4 flex items-center">
          <span className="mr-2">💡</span>
          How It Works
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h5 className="font-semibold text-cyan-300 mb-2">Creating a Room:</h5>
            <ol className="text-sm text-gray-300 space-y-1 list-decimal list-inside">
              <li>Enter a room name and your name</li>
              <li>Select your speaking language and target language</li>
              <li>Click "Create Room" to generate a shareable link</li>
              <li>Share the link with others to invite them</li>
            </ol>
          </div>
          <div>
            <h5 className="font-semibold text-cyan-300 mb-2">Joining a Room:</h5>
            <ol className="text-sm text-gray-300 space-y-1 list-decimal list-inside">
              <li>Click a shared room link or enter room ID manually</li>
              <li>Enter your name to identify yourself</li>
              <li>Click "Join Room" to connect instantly</li>
              <li>Start speaking - translations happen automatically!</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EnhancedRoomManager
