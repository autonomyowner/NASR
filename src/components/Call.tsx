import { useState, useEffect, useRef } from 'react'
import { useWebRTC } from '../hooks/useWebRTC'
import { useTranslatedSpeech } from '../hooks/useTranslatedSpeech'
import { useCallHistory } from '../hooks/useCallHistory'
import { usePeerConnection } from '../hooks/usePeerConnection'
import { useIncomingCall } from '../hooks/useIncomingCall'
import { useNotifications } from '../hooks/useNotifications'
import { translationService } from '../services/translationService'
import { signalingService } from '../services/signalingService'
import IncomingCallModal from './IncomingCallModal'
import CallTimer from './CallTimer'
import NotificationContainer from './NotificationContainer'
import MicrophoneStatus from './MicrophoneStatus'
import WebRTCDebug from './WebRTCDebug'
import RoomManager from './RoomManager'

const Call = () => {
  const [peerId, setPeerId] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState('es-ES')
  const [showTranscript, setShowTranscript] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
  const [showContacts, setShowContacts] = useState(false)
  
  // Room management state
  const [roomId, setRoomId] = useState<string | null>(null)
  const [isInRoom, setIsInRoom] = useState(false)

  const webRTC = useWebRTC()
  const translatedSpeech = useTranslatedSpeech(selectedLanguage)
  const callHistory = useCallHistory()
  const peerConnection = usePeerConnection()
  const incomingCall = useIncomingCall(webRTC.answerCall)
  const notifications = useNotifications()
  
  const callStartTimeRef = useRef<number | null>(null)

  const supportedLanguages = translationService.getSupportedLanguages()

  // Auto-start/stop translation based on call state
  useEffect(() => {
    if (webRTC.isCallActive && webRTC.isTranslationEnabled) {
      translatedSpeech.startListening()
    } else {
      translatedSpeech.stopListening()
    }
  }, [webRTC.isCallActive, webRTC.isTranslationEnabled])

  // Handle call start - add to history and track time
  useEffect(() => {
    if (webRTC.isCallActive && webRTC.peerId && !callHistory.currentCall) {
      const contact = callHistory.findContact(webRTC.peerId)
      callHistory.startCall(webRTC.peerId, contact?.name)
      callStartTimeRef.current = Date.now()
    } else if (!webRTC.isCallActive) {
      callStartTimeRef.current = null
    }
  }, [webRTC.isCallActive, webRTC.peerId, callHistory])

  // Handle call end - update history with quality
  useEffect(() => {
    if (!webRTC.isCallActive && callHistory.currentCall) {
      const quality = webRTC.qualityScore! >= 80 ? 'excellent' : 
                     webRTC.qualityScore! >= 60 ? 'good' : 
                     webRTC.qualityScore! >= 40 ? 'fair' : 'poor'
      callHistory.endCall(quality)
    }
  }, [webRTC.isCallActive, callHistory.currentCall, webRTC.qualityScore, callHistory])

  // Add translations to call history
  useEffect(() => {
    if (translatedSpeech.translatedText && callHistory.currentCall) {
      callHistory.addTranslationToCurrentCall(
        translatedSpeech.transcript,
        translatedSpeech.translatedText
      )
    }
  }, [translatedSpeech.translatedText, callHistory])

  // Set up signaling error handlers
  useEffect(() => {
    signalingService.onCallFailed = (reason: string) => {
      notifications.error('Call Failed', reason)
    }

    signalingService.onUserBusy = (peerId: string) => {
      notifications.warning('User Busy', `${peerId} is currently on another call`)
    }

    return () => {
      signalingService.onCallFailed = null
      signalingService.onUserBusy = null
    }
  }, [])

  // Room management functions
  const handleCreateRoom = (_source: string, target: string) => {
    const newRoomId = `room-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setRoomId(newRoomId)
    setSelectedLanguage(target)
    setIsInRoom(true)
    notifications.success('Room Created', `Room ID: ${newRoomId}`)
  }

  const handleJoinRoom = (id: string, _source: string, target: string) => {
    setRoomId(id)
    setSelectedLanguage(target)
    setIsInRoom(true)
    notifications.success('Joined Room', `Connected to room: ${id}`)
  }

  const handleLeaveRoom = () => {
    if (webRTC.isCallActive) {
      webRTC.endCall()
    }
    setRoomId(null)
    setIsInRoom(false)
    notifications.info('Left Room', 'You have left the translation room')
  }

  // Connection status notifications
  useEffect(() => {
    if (peerConnection.connectionError) {
      notifications.error('Connection Error', peerConnection.connectionError, true)
    } else if (peerConnection.isConnected) {
      notifications.success('Connected', 'Successfully connected to signaling server')
    }
  }, [peerConnection.isConnected, peerConnection.connectionError])

  // Call state notifications
  useEffect(() => {
    if (webRTC.isCallActive && webRTC.peerId) {
      notifications.success('Call Connected', `Connected to ${webRTC.peerId}`)
    }
  }, [webRTC.isCallActive, webRTC.peerId])

  const handleStartCall = async () => {
    if (!peerId.trim()) {
      notifications.warning('Missing Peer ID', 'Please enter a Peer ID to start the call')
      return
    }

    if (!peerConnection.isConnected) {
      notifications.error('Connection Required', 'Please wait for the connection to be established before starting a call')
      return
    }
    
    try {
      await webRTC.startCall(peerId.trim())
      notifications.info('Calling...', `Attempting to connect to ${peerId.trim()}`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      notifications.error('Call Failed', `Failed to start call: ${errorMessage}`)
    }
  }

  const handleCallContact = (contactPeerId: string) => {
    setPeerId(contactPeerId)
    handleStartCall()
  }

  const formatLanguageName = (langCode: string) => {
    const names: { [key: string]: string } = {
      'en-US': 'English',
      'es-ES': 'Spanish',
      'fr-FR': 'French',
      'de-DE': 'German',
      'it-IT': 'Italian',
      'pt-PT': 'Portuguese',
      'ar-SA': 'Arabic',
      'zh-CN': 'Chinese',
      'ja-JP': 'Japanese',
      'ko-KR': 'Korean',
      'hi-IN': 'Hindi'
    }
    return names[langCode] || langCode
  }

  return (
    <section id="call" className="section-padding relative overflow-hidden min-h-screen">
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/photo_2025-09-03_05-58-08.jpg" 
          alt="Call Page Background" 
          className="w-full h-full object-cover"
        />
      </div>
      
      {/* Content Container */}
      <div className="relative z-10">
        <div className="container-custom">
          {!isInRoom ? (
            // Show Room Manager when not in a room
            <div>
              <div className="text-center mb-16">
                <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                  Voice Call with <span className="premium-text">Real-time Translation</span>
                </h2>
                <p className="text-gray-300 text-lg max-w-2xl mx-auto">
                  Connect with people around the world and break language barriers with instant translation
                </p>
              </div>
              <RoomManager 
                onCreateRoom={handleCreateRoom}
                onJoinRoom={handleJoinRoom}
              />
            </div>
          ) : (
            // Show existing interface when in a room
            <div>
              <div className="text-center mb-8">
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                  Translation Room: <span className="premium-text">{roomId}</span>
                </h2>
                <div className="flex justify-center items-center gap-4 text-slate-300 mb-4">
                  <span>Language: {selectedLanguage}</span>
                  <button
                    onClick={handleLeaveRoom}
                    className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                  >
                    Leave Room
                  </button>
                </div>
              </div>
              <div className="text-center mb-16">
                <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                  Voice Call with <span className="premium-text">Real-time Translation</span>
                </h2>
                <p className="text-gray-300 text-lg max-w-2xl mx-auto">
                  Connect with people around the world and break language barriers with Travoice's 
                  real-time voice translation technology.
                </p>
              </div>

          {!webRTC.isCallActive ? (
            <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8 px-4 sm:px-6 lg:px-8">
              {/* Your ID and Connection Status - Enhanced */}
              <div className="max-w-2xl mx-auto">
                <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-8 rounded-3xl shadow-2xl hover:shadow-cyan-500/20 transition-all duration-300">
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse mr-3"></div>
                    <h3 className="text-xl font-bold text-white">Your Connection</h3>
                  </div>
                  
                  {/* Your ID - Enhanced */}
                  <div className="mb-6">
                    <label className="text-gray-300 font-semibold mb-3 flex items-center">
                      <span className="text-lg mr-2">🆔</span>
                      Your ID
                    </label>
                    <div className="flex space-x-3">
                      <input
                        type="text"
                        value={peerConnection.peerId}
                        readOnly
                        className="flex-1 p-4 bg-white/10 border border-white/20 rounded-2xl text-white font-mono text-sm backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50"
                      />
                      <button
                        onClick={peerConnection.copyPeerId}
                        className="px-6 py-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-2xl hover:from-blue-600 hover:to-blue-700 transition-all duration-300 text-sm font-semibold transform hover:scale-105 active:scale-95 shadow-lg shadow-blue-500/25"
                      >
                        📋 Copy
                      </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-2 flex items-center">
                      <span className="mr-1">💡</span>
                      Share this ID with others so they can call you
                    </p>
                  </div>

                  {/* Connection Status - Enhanced */}
                  <div className={`flex items-center justify-center space-x-3 p-4 rounded-2xl mb-4 backdrop-blur-sm border ${
                    peerConnection.isConnected 
                      ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-400/30' 
                      : peerConnection.connectionError 
                        ? 'bg-gradient-to-r from-red-500/20 to-red-600/20 border-red-400/30' 
                        : 'bg-gradient-to-r from-yellow-500/20 to-yellow-600/20 border-yellow-400/30'
                  }`}>
                    <div className={`w-3 h-3 rounded-full ${
                      peerConnection.isConnected ? 'bg-green-400 animate-pulse' : 
                      peerConnection.connectionError ? 'bg-red-400' : 'bg-yellow-400 animate-pulse'
                    }`} />
                    <span className={`font-semibold ${
                      peerConnection.isConnected ? 'text-green-300' : 
                      peerConnection.connectionError ? 'text-red-300' : 'text-yellow-300'
                    }`}>
                      {peerConnection.isConnected ? 'Connected' : 
                       peerConnection.connectionError ? `Disconnected (${peerConnection.connectionError})` : 'Connecting...'}
                    </span>
                    {!peerConnection.isConnected && (
                      <button
                        onClick={peerConnection.reconnect}
                        className="text-xs bg-blue-500 text-white px-3 py-1 rounded-lg hover:bg-blue-600 transition-colors font-medium"
                      >
                        Reconnect
                      </button>
                    )}
                  </div>

                  {/* Online Users Count - Enhanced */}
                  {peerConnection.isConnected && (
                    <div className="text-center p-3 bg-white/5 border border-white/10 rounded-2xl">
                      <div className="flex items-center justify-center space-x-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                        <span className="text-sm text-gray-300">
                          <span className="font-semibold text-white">{peerConnection.onlineUsers.length}</span> other user{peerConnection.onlineUsers.length !== 1 ? 's' : ''} online
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Contacts & Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                
                {/* Recent Contacts */}
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-lg font-bold text-white mb-4">Recent Contacts</h3>
                  <div className="space-y-3">
                    {callHistory.recentContacts.slice(0, 3).map(contact => (
                      <div key={contact.id} className="flex items-center justify-between p-2 bg-white/30 rounded-lg">
                        <div>
                          <p className="font-medium text-white">{contact.name}</p>
                          <p className="text-sm text-slate-600">{contact.peerId}</p>
                        </div>
                        <button
                          onClick={() => handleCallContact(contact.peerId)}
                          className="text-green-600 hover:text-green-700 p-1"
                        >
                          📞
                        </button>
                      </div>
                    ))}
                    {callHistory.recentContacts.length === 0 && (
                      <p className="text-slate-600 text-sm italic">No recent contacts</p>
                    )}
                  </div>
                </div>

                {/* Favorites */}
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-lg font-bold text-white mb-4">Favorites</h3>
                  <div className="space-y-3">
                    {callHistory.favoriteContacts.slice(0, 3).map(contact => (
                      <div key={contact.id} className="flex items-center justify-between p-2 bg-white/30 rounded-lg">
                        <div>
                          <p className="font-medium text-white">{contact.name} ⭐</p>
                          <p className="text-sm text-slate-600">{contact.peerId}</p>
                        </div>
                        <button
                          onClick={() => handleCallContact(contact.peerId)}
                          className="text-green-600 hover:text-green-700 p-1"
                        >
                          📞
                        </button>
                      </div>
                    ))}
                    {callHistory.favoriteContacts.length === 0 && (
                      <p className="text-slate-600 text-sm italic">No favorite contacts</p>
                    )}
                  </div>
                </div>

                {/* Call Stats */}
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-lg font-bold text-white mb-4">Call Statistics</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-300">Total Calls:</span>
                      <span className="font-medium text-white">{callHistory.callStats.totalCalls}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Total Duration:</span>
                      <span className="font-medium text-white">
                        {Math.floor(callHistory.callStats.totalDuration / 60)}m {callHistory.callStats.totalDuration % 60}s
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-300">Answer Rate:</span>
                      <span className="font-medium text-white">{Math.round(callHistory.callStats.answerRate)}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Navigation Buttons */}
              <div className="flex justify-center space-x-4">
                <button
                  onClick={() => setShowContacts(!showContacts)}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  {showContacts ? 'Hide Contacts' : 'Manage Contacts'}
                </button>
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="px-6 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
                >
                  {showHistory ? 'Hide History' : 'Call History'}
                </button>
              </div>

              {/* Contacts Management */}
              {showContacts && (
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-xl font-bold text-white mb-4">Contacts</h3>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {callHistory.contacts.map(contact => (
                      <div key={contact.id} className="flex items-center justify-between p-3 bg-white/30 rounded-lg">
                        <div className="flex-1">
                          <p className="font-medium text-white">
                            {contact.name} {contact.isFavorite && '⭐'}
                          </p>
                          <p className="text-sm text-slate-600">{contact.peerId}</p>
                          <p className="text-xs text-slate-500">{formatLanguageName(contact.language)}</p>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => callHistory.updateContact(contact.id, { isFavorite: !contact.isFavorite })}
                            className="text-yellow-600 hover:text-yellow-700 p-1"
                            title={contact.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                          >
                            {contact.isFavorite ? '⭐' : '☆'}
                          </button>
                          <button
                            onClick={() => handleCallContact(contact.peerId)}
                            className="text-green-600 hover:text-green-700 p-1"
                            title="Call contact"
                          >
                            📞
                          </button>
                          <button
                            onClick={() => callHistory.deleteContact(contact.id)}
                            className="text-red-600 hover:text-red-700 p-1"
                            title="Delete contact"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    ))}
                    {callHistory.contacts.length === 0 && (
                      <p className="text-slate-600 text-center italic">No contacts yet. Add some to get started!</p>
                    )}
                  </div>
                </div>
              )}

              {/* Call History */}
              {showHistory && (
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold text-white">Call History</h3>
                    <button
                      onClick={callHistory.clearHistory}
                      className="text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
                    >
                      Clear All
                    </button>
                  </div>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {callHistory.callHistory.slice(0, 10).map(entry => (
                      <div key={entry.id} className="p-3 bg-white/30 rounded-lg">
                        <div className="flex justify-between items-start mb-1">
                          <p className="font-medium text-white">{entry.contactName}</p>
                          <span className={`text-xs px-2 py-1 rounded ${
                            entry.quality === 'excellent' ? 'bg-green-200 text-green-800' :
                            entry.quality === 'good' ? 'bg-blue-200 text-blue-800' :
                            entry.quality === 'fair' ? 'bg-yellow-200 text-yellow-800' :
                            'bg-red-200 text-red-800'
                          }`}>
                            {entry.quality}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm text-slate-600">
                          <span>{entry.startTime.toLocaleString()}</span>
                          <span>{Math.floor(entry.duration / 60)}:{(entry.duration % 60).toString().padStart(2, '0')}</span>
                        </div>
                        {entry.translations && entry.translations.length > 0 && (
                          <p className="text-xs text-slate-500 mt-1">
                            💬 {entry.translations.length} translation{entry.translations.length > 1 ? 's' : ''}
                          </p>
                        )}
                      </div>
                    ))}
                    {callHistory.callHistory.length === 0 && (
                      <p className="text-slate-600 text-center italic">No call history yet.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Call Setup Interface - Enhanced */}
              <div className="max-w-2xl mx-auto">
                <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-8 rounded-3xl shadow-2xl hover:shadow-cyan-500/20 transition-all duration-300">
                  <div className="flex items-center justify-center mb-8">
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse mr-3"></div>
                    <h3 className="text-2xl font-bold text-white">Start a Voice Call</h3>
                  </div>
                  
                  {/* Peer ID Input - Enhanced */}
                  <div className="mb-6">
                    <label className="text-gray-300 font-semibold mb-3 flex items-center">
                      <span className="text-lg mr-2">📞</span>
                      Enter Peer ID or Phone Number
                    </label>
                    <input
                      type="text"
                      value={peerId}
                      onChange={(e) => setPeerId(e.target.value)}
                      placeholder="e.g. user-123 or +1234567890"
                      className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                    />
                  </div>

                  {/* Language Selection - Enhanced */}
                  <div className="mb-6">
                    <label className="text-gray-300 font-semibold mb-3 flex items-center">
                      <span className="text-lg mr-2">🌐</span>
                      Translate to Language
                    </label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => {
                        setSelectedLanguage(e.target.value)
                        translatedSpeech.setTargetLanguage(e.target.value)
                      }}
                      className="w-full p-4 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white backdrop-blur-sm transition-all duration-300"
                    >
                      {supportedLanguages.map(lang => (
                        <option key={lang} value={lang} className="bg-slate-800 text-white">
                          {formatLanguageName(lang)}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Microphone Status - Enhanced */}
                  <div className="mb-6">
                    <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                      <MicrophoneStatus />
                    </div>
                  </div>

                  {/* Speech Recognition Support Check - Enhanced */}
                  {!translatedSpeech.isSupported && (
                    <div className="mb-6 p-4 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-400/30 rounded-2xl backdrop-blur-sm">
                      <div className="flex items-center space-x-2">
                        <span className="text-yellow-400 text-lg">⚠️</span>
                        <p className="text-yellow-300 text-sm font-medium">
                          Speech recognition is not supported in this browser. 
                          Translation features will be limited.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Call Button - Enhanced */}
                  <button
                    onClick={handleStartCall}
                    disabled={webRTC.isConnecting || !peerId.trim() || !peerConnection.isConnected}
                    className="w-full py-4 text-xl font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-900 hover:from-cyan-400 hover:to-cyan-500 shadow-cyan-500/25 hover:shadow-cyan-500/40"
                  >
                    <div className="flex items-center justify-center space-x-2">
                      {webRTC.isConnecting ? (
                        <>
                          <div className="w-5 h-5 border-2 border-slate-900 border-t-transparent rounded-full animate-spin"></div>
                          <span>Connecting...</span>
                        </>
                      ) : !peerConnection.isConnected ? (
                        <>
                          <span>🔌</span>
                          <span>Disconnected - Cannot Start Call</span>
                        </>
                      ) : (
                        <>
                          <span>📞</span>
                          <span>Start Call</span>
                        </>
                      )}
                    </div>
                  </button>

                  {/* Save Contact Option - Enhanced */}
                  {peerId.trim() && !callHistory.findContact(peerId.trim()) && (
                    <div className="mt-6 p-4 bg-gradient-to-r from-blue-500/10 to-blue-600/10 border border-blue-400/30 rounded-2xl backdrop-blur-sm">
                      <div className="flex items-center space-x-2 mb-3">
                        <span className="text-blue-400 text-lg">💡</span>
                        <p className="text-blue-300 text-sm font-medium">
                          Save this contact for easy calling later?
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          const name = prompt('Enter a name for this contact:', peerId.trim())
                          if (name) {
                            callHistory.addContact({
                              name,
                              peerId: peerId.trim(),
                              language: selectedLanguage,
                              isFavorite: false
                            })
                          }
                        }}
                        className="px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl text-sm font-semibold hover:from-blue-600 hover:to-blue-700 transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg shadow-blue-500/25"
                      >
                        💾 Save Contact
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* Active Call Interface */
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
                
                {/* Call Controls - Enhanced Design */}
                <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl hover:shadow-cyan-500/20 transition-all duration-300">
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse mr-3"></div>
                    <h3 className="text-xl font-bold text-white">Call Controls</h3>
                  </div>
                  
                  <div className="space-y-5">
                    {/* Call Status - Enhanced */}
                    <div className="text-center p-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-400/30 rounded-2xl backdrop-blur-sm">
                      <div className="flex items-center justify-center mb-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
                        <span className="text-green-300 text-sm font-medium">LIVE</span>
                      </div>
                      <p className="text-white font-semibold text-lg">
                        Connected to {webRTC.peerId}
                      </p>
                    </div>

                    {/* Call Timer - Enhanced */}
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
                      <CallTimer 
                        isActive={webRTC.isCallActive} 
                        startTime={callStartTimeRef.current || undefined} 
                      />
                    </div>

                    {/* Call Quality Indicator - Enhanced */}
                    {webRTC.qualityMetrics && (
                      <div className="p-4 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-medium text-gray-300 flex items-center">
                            <div className="w-2 h-2 bg-blue-400 rounded-full mr-2"></div>
                            Call Quality
                          </span>
                          <span className={`text-sm font-bold px-3 py-1 rounded-full ${
                            webRTC.qualityScore! >= 80 ? 'bg-green-500/20 text-green-300' :
                            webRTC.qualityScore! >= 60 ? 'bg-yellow-500/20 text-yellow-300' :
                            webRTC.qualityScore! >= 40 ? 'bg-orange-500/20 text-orange-300' : 'bg-red-500/20 text-red-300'
                          }`}>
                            {webRTC.qualityText}
                          </span>
                        </div>
                        
                        {/* Quality Progress Bar - Enhanced */}
                        <div className="w-full bg-gray-700/50 rounded-full h-3 mb-4 overflow-hidden">
                          <div 
                            className={`h-3 rounded-full transition-all duration-500 ease-out ${
                              webRTC.qualityScore! >= 80 ? 'bg-gradient-to-r from-green-400 to-green-500' :
                              webRTC.qualityScore! >= 60 ? 'bg-gradient-to-r from-yellow-400 to-yellow-500' :
                              webRTC.qualityScore! >= 40 ? 'bg-gradient-to-r from-orange-400 to-orange-500' : 'bg-gradient-to-r from-red-400 to-red-500'
                            }`}
                            style={{ width: `${webRTC.qualityScore}%` }}
                          />
                        </div>

                        {/* Detailed Metrics - Enhanced */}
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span className="text-gray-400">Network:</span>
                              <span className="text-white font-medium">{webRTC.qualityMetrics.networkType}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Bitrate:</span>
                              <span className="text-white font-medium">{webRTC.qualityMetrics.bitrate}kbps</span>
                            </div>
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span className="text-gray-400">RTT:</span>
                              <span className="text-white font-medium">{Math.round(webRTC.qualityMetrics.rtt)}ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Audio:</span>
                              <span className="text-white font-medium">{webRTC.qualityMetrics.audioLevel}%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Control Buttons Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {/* Mute Toggle - Enhanced */}
                      <button
                        onClick={webRTC.toggleMute}
                        aria-label={webRTC.isMuted ? 'Unmute microphone' : 'Mute microphone'}
                        className={`group relative p-4 rounded-2xl font-semibold transition-all duration-300 transform hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 ${
                          webRTC.isMuted 
                            ? 'bg-gradient-to-br from-red-500 to-red-600 text-white shadow-lg shadow-red-500/25' 
                            : 'bg-gradient-to-br from-green-500 to-green-600 text-white shadow-lg shadow-green-500/25'
                        }`}
                      >
                        <div className="flex flex-col items-center space-y-1">
                          <span className="text-2xl">{webRTC.isMuted ? '🔇' : '🎤'}</span>
                          <span className="text-sm">{webRTC.isMuted ? 'Unmute' : 'Mute'}</span>
                        </div>
                        {webRTC.isMuted && (
                          <div className="absolute inset-0 bg-red-400/20 rounded-2xl animate-pulse"></div>
                        )}
                      </button>

                      {/* Translation Toggle - Enhanced */}
                      <button
                        onClick={webRTC.toggleTranslation}
                        aria-label={webRTC.isTranslationEnabled ? 'Disable translation' : 'Enable translation'}
                        className={`group relative p-4 rounded-2xl font-semibold transition-all duration-300 transform hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 ${
                          webRTC.isTranslationEnabled 
                            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/25' 
                            : 'bg-gradient-to-br from-gray-600 to-gray-700 text-gray-300 shadow-lg'
                        }`}
                      >
                        <div className="flex flex-col items-center space-y-1">
                          <span className="text-2xl">🌐</span>
                          <span className="text-sm">{webRTC.isTranslationEnabled ? 'ON' : 'OFF'}</span>
                        </div>
                        {webRTC.isTranslationEnabled && (
                          <div className="absolute inset-0 bg-blue-400/20 rounded-2xl animate-pulse"></div>
                        )}
                      </button>
                    </div>

                    {/* Secondary Controls */}
                    <div className="space-y-3">
                      {/* Delay Toggle - Enhanced */}
                      <button
                        onClick={webRTC.toggleDelay}
                        className={`w-full p-3 rounded-xl font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 ${
                          webRTC.isDelayEnabled 
                            ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/25' 
                            : 'bg-white/10 text-gray-300 border border-white/20 hover:bg-white/20'
                        }`}
                      >
                        <div className="flex items-center justify-center space-x-2">
                          <span className="text-lg">⏰</span>
                          <span>{webRTC.isDelayEnabled ? 'Delay: ON (10s)' : 'Delay: OFF'}</span>
                        </div>
                      </button>

                      {/* Transcript Toggle - Enhanced */}
                      <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="w-full p-3 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg shadow-purple-500/25"
                      >
                        <div className="flex items-center justify-center space-x-2">
                          <span className="text-lg">📝</span>
                          <span>{showTranscript ? 'Hide Transcript' : 'Show Transcript'}</span>
                        </div>
                      </button>
                    </div>

                    {/* End Call - Enhanced */}
                    <button
                      onClick={webRTC.endCall}
                      aria-label="End the current call"
                      className="w-full p-4 bg-gradient-to-r from-red-600 to-red-700 text-white rounded-2xl font-bold text-lg transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg shadow-red-500/25 hover:shadow-red-500/40 focus:outline-none focus:ring-2 focus:ring-red-400/50"
                    >
                      <div className="flex items-center justify-center space-x-2">
                        <span className="text-xl">📞</span>
                        <span>End Call</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Real-time Translation Display - Enhanced */}
                <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl hover:shadow-cyan-500/20 transition-all duration-300">
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse mr-3"></div>
                    <h3 className="text-xl font-bold text-white">Live Translation</h3>
                  </div>
                  
                  <div className="space-y-5">
                    {/* Language Info - Enhanced */}
                    <div className="text-center p-4 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-400/30 rounded-2xl backdrop-blur-sm">
                      <div className="flex items-center justify-center space-x-3">
                        <span className="text-cyan-300 text-sm font-medium">
                          {formatLanguageName(translatedSpeech.detectedLanguage)}
                        </span>
                        <div className="flex items-center space-x-1">
                          <div className="w-1 h-1 bg-cyan-400 rounded-full animate-pulse"></div>
                          <div className="w-1 h-1 bg-cyan-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                          <div className="w-1 h-1 bg-cyan-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                        </div>
                        <span className="text-cyan-300 text-sm font-medium">
                          {formatLanguageName(translatedSpeech.targetLanguage)}
                        </span>
                      </div>
                    </div>

                    {/* Listening Status - Enhanced */}
                    {translatedSpeech.isListening && (
                      <div className="text-center p-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-400/30 rounded-2xl backdrop-blur-sm">
                        <div className="flex items-center justify-center space-x-2">
                          <div className="relative">
                            <span className="text-2xl animate-pulse">🎤</span>
                            <div className="absolute -inset-1 bg-green-400/30 rounded-full animate-ping"></div>
                          </div>
                          <span className="text-green-300 font-semibold">Listening...</span>
                        </div>
                      </div>
                    )}

                    {/* Original Speech - Enhanced */}
                    {translatedSpeech.transcript && (
                      <div className="p-5 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-sm">
                        <div className="flex items-center space-x-2 mb-3">
                          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          <p className="text-sm text-gray-400 font-medium">Original Speech</p>
                        </div>
                        <p className="text-white text-lg leading-relaxed font-medium">
                          {translatedSpeech.transcript}
                        </p>
                      </div>
                    )}

                    {/* Translated Text - Enhanced */}
                    {translatedSpeech.translatedText && (
                      <div className="p-5 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-400/30 rounded-2xl backdrop-blur-sm">
                        <div className="flex items-center space-x-2 mb-3">
                          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
                          <p className="text-sm text-cyan-300 font-medium">Translation</p>
                        </div>
                        <p className="text-cyan-100 text-lg leading-relaxed font-semibold">
                          {translatedSpeech.translatedText}
                        </p>
                      </div>
                    )}

                    {/* Error Display - Enhanced */}
                    {translatedSpeech.error && (
                      <div className="p-4 bg-gradient-to-r from-red-500/20 to-red-600/20 border border-red-400/30 rounded-2xl backdrop-blur-sm">
                        <div className="flex items-center space-x-2">
                          <span className="text-red-400 text-lg">⚠️</span>
                          <p className="text-red-300 text-sm font-medium">{translatedSpeech.error}</p>
                        </div>
                      </div>
                    )}

                    {/* Translation Status Indicator */}
                    {!translatedSpeech.isListening && !translatedSpeech.transcript && !translatedSpeech.error && (
                      <div className="text-center p-6 bg-white/5 border border-white/10 rounded-2xl">
                        <div className="flex flex-col items-center space-y-3">
                          <div className="w-12 h-12 bg-cyan-500/20 rounded-full flex items-center justify-center">
                            <span className="text-2xl text-cyan-400">🌐</span>
                          </div>
                          <p className="text-gray-400 text-sm">Ready to translate your speech</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Call History / Transcript - Enhanced */}
                {showTranscript && (
                  <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl hover:shadow-cyan-500/20 transition-all duration-300">
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-3">
                        <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse"></div>
                        <h3 className="text-xl font-bold text-white">
                          Conversation Log
                        </h3>
                      </div>
                      <button
                        onClick={translatedSpeech.clearHistory}
                        className="px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl text-sm font-medium transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg shadow-red-500/25"
                      >
                        Clear
                      </button>
                    </div>
                    
                    <div className="max-h-96 overflow-y-auto space-y-4 scrollbar-enhanced">
                      {translatedSpeech.transcriptHistory.length === 0 ? (
                        <div className="text-center p-8 bg-white/5 border border-white/10 rounded-2xl">
                          <div className="flex flex-col items-center space-y-3">
                            <div className="w-12 h-12 bg-purple-500/20 rounded-full flex items-center justify-center">
                              <span className="text-2xl text-purple-400">💬</span>
                            </div>
                            <p className="text-gray-400 text-sm">
                              No conversation yet. Start speaking to see translations appear here.
                            </p>
                          </div>
                        </div>
                      ) : (
                        translatedSpeech.transcriptHistory
                          .filter(item => item.isFinal)
                          .map((item, index) => (
                            <div key={index} className="p-4 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                              <div className="flex items-center space-x-2 mb-3">
                                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                                <span className="text-xs text-gray-400 font-medium">
                                  {new Date(item.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              
                              <div className="space-y-3">
                                {/* Original Text */}
                                <div className="p-3 bg-white/10 rounded-xl">
                                  <p className="text-white text-sm leading-relaxed">{item.text}</p>
                                </div>
                                
                                {/* Translation */}
                                {item.translation && (
                                  <div className="p-3 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-400/20 rounded-xl">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse"></div>
                                      <span className="text-xs text-cyan-300 font-medium">Translation</span>
                                    </div>
                                    <p className="text-cyan-100 text-sm leading-relaxed font-medium">
                                      {item.translation}
                                    </p>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
            </div>
          )}
        </div>
      </div>

      {/* Hidden Audio Element for Remote Stream */}
      {webRTC.remoteStream && (
        <audio
          ref={(audio) => {
            if (audio && webRTC.remoteStream) {
              audio.srcObject = webRTC.remoteStream
              audio.play().catch(console.error)
            }
          }}
          autoPlay
          playsInline
          style={{ display: 'none' }}
        />
      )}

      {/* Incoming Call Modal */}
      <IncomingCallModal
        incomingCall={incomingCall.incomingCall}
        isRinging={incomingCall.isRinging}
        onAccept={incomingCall.acceptCall}
        onDecline={incomingCall.declineCall}
      />

      {/* Notifications */}
      <NotificationContainer
        notifications={notifications.notifications}
        onClose={notifications.removeNotification}
      />

      {/* WebRTC Debug Info (only in development) */}
      <WebRTCDebug show={import.meta.env.DEV} />
    </section>
  )
}

export default Call