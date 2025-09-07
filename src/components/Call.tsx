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

const Call = () => {
  const [peerId, setPeerId] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState('es-ES')
  const [showTranscript, setShowTranscript] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
  const [showContacts, setShowContacts] = useState(false)

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
            <div className="max-w-6xl mx-auto space-y-8">
              {/* Your ID and Connection Status */}
              <div className="max-w-2xl mx-auto">
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-xl font-bold text-white mb-4 text-center">Your Connection</h3>
                  
                  {/* Your ID */}
                  <div className="mb-4">
                    <label className="block text-gray-300 font-medium mb-2">Your ID</label>
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={peerConnection.peerId}
                        readOnly
                        className="flex-1 p-3 bg-white/80 border border-emerald-300 rounded-lg text-white font-mono text-sm"
                      />
                      <button
                        onClick={peerConnection.copyPeerId}
                        className="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm font-medium"
                      >
                        📋 Copy
                      </button>
                    </div>
                    <p className="text-xs text-white mt-1">Share this ID with others so they can call you</p>
                  </div>

                  {/* Connection Status */}
                  <div className="flex items-center justify-center space-x-3 p-3 rounded-lg mb-4" style={{
                    backgroundColor: peerConnection.isConnected ? 'rgb(220, 252, 231)' : peerConnection.connectionError ? 'rgb(254, 226, 226)' : 'rgb(254, 243, 199)'
                  }}>
                    <div className={`w-3 h-3 rounded-full ${
                      peerConnection.isConnected ? 'bg-green-500 animate-pulse' : 
                      peerConnection.connectionError ? 'bg-red-500' : 'bg-yellow-500'
                    }`} />
                    <span className={`font-medium ${
                      peerConnection.isConnected ? 'text-green-800' : 
                      peerConnection.connectionError ? 'text-red-800' : 'text-yellow-800'
                    }`}>
                      {peerConnection.isConnected ? 'Connected' : 
                       peerConnection.connectionError ? `Disconnected (${peerConnection.connectionError})` : 'Connecting...'}
                    </span>
                    {!peerConnection.isConnected && (
                      <button
                        onClick={peerConnection.reconnect}
                        className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                      >
                        Reconnect
                      </button>
                    )}
                  </div>

                  {/* Online Users Count */}
                  {peerConnection.isConnected && (
                    <div className="text-center text-sm text-white">
                      {peerConnection.onlineUsers.length} other user{peerConnection.onlineUsers.length !== 1 ? 's' : ''} online
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Contacts & Quick Actions */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
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

              {/* Call Setup Interface */}
              <div className="max-w-2xl mx-auto">
              <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-8 rounded-2xl shadow-2xl">
                <h3 className="text-2xl font-bold text-white mb-6 text-center">
                  Start a Voice Call
                </h3>
                
                {/* Peer ID Input */}
                <div className="mb-6">
                  <label className="block text-gray-300 font-medium mb-2">
                    Enter Peer ID or Phone Number
                  </label>
                  <input
                    type="text"
                    value={peerId}
                    onChange={(e) => setPeerId(e.target.value)}
                    placeholder="e.g. user-123 or +1234567890"
                    className="w-full p-4 bg-white/80 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-400 text-white"
                  />
                </div>

                {/* Language Selection */}
                <div className="mb-6">
                  <label className="block text-gray-300 font-medium mb-2">
                    Translate to Language
                  </label>
                  <select
                    value={selectedLanguage}
                    onChange={(e) => {
                      setSelectedLanguage(e.target.value)
                      translatedSpeech.setTargetLanguage(e.target.value)
                    }}
                    className="w-full p-4 bg-white/80 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-400 text-white"
                  >
                    {supportedLanguages.map(lang => (
                      <option key={lang} value={lang}>
                        {formatLanguageName(lang)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Microphone Status */}
                <div className="mb-4">
                  <MicrophoneStatus />
                </div>

                {/* Speech Recognition Support Check */}
                {!translatedSpeech.isSupported && (
                  <div className="mb-4 p-4 bg-yellow-100 border border-yellow-300 rounded-lg">
                    <p className="text-yellow-800 text-sm">
                      ⚠️ Speech recognition is not supported in this browser. 
                      Translation features will be limited.
                    </p>
                  </div>
                )}

                {/* Call Button */}
                <button
                  onClick={handleStartCall}
                  disabled={webRTC.isConnecting || !peerId.trim() || !peerConnection.isConnected}
                  className="w-full btn-primary py-4 text-xl font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {webRTC.isConnecting ? 'Connecting...' : 
                   !peerConnection.isConnected ? 'Disconnected - Cannot Start Call' : 'Start Call'}
                </button>

                {/* Save Contact Option */}
                {peerId.trim() && !callHistory.findContact(peerId.trim()) && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-800 mb-2">
                      💡 Save this contact for easy calling later?
                    </p>
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
                      className="text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
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
            <div className="max-w-6xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Call Controls */}
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-xl font-bold text-white mb-4 text-center">
                    Call Controls
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Call Status */}
                    <div className="text-center p-3 bg-green-100 rounded-lg">
                      <p className="text-green-800 font-medium">
                        📞 Connected to {webRTC.peerId}
                      </p>
                    </div>

                    {/* Call Timer */}
                    <CallTimer 
                      isActive={webRTC.isCallActive} 
                      startTime={callStartTimeRef.current || undefined} 
                    />

                    {/* Call Quality Indicator */}
                    {webRTC.qualityMetrics && (
                      <div className="p-3 bg-white/80 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-300">Call Quality</span>
                          <span className={`text-sm font-bold ${
                            webRTC.qualityScore! >= 80 ? 'text-green-600' :
                            webRTC.qualityScore! >= 60 ? 'text-yellow-600' :
                            webRTC.qualityScore! >= 40 ? 'text-orange-600' : 'text-red-600'
                          }`}>
                            {webRTC.qualityText}
                          </span>
                        </div>
                        
                        {/* Quality Progress Bar */}
                        <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              webRTC.qualityScore! >= 80 ? 'bg-green-500' :
                              webRTC.qualityScore! >= 60 ? 'bg-yellow-500' :
                              webRTC.qualityScore! >= 40 ? 'bg-orange-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${webRTC.qualityScore}%` }}
                          />
                        </div>

                        {/* Detailed Metrics */}
                        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                          <div>
                            <span className="block">Network: {webRTC.qualityMetrics.networkType}</span>
                            <span className="block">Bitrate: {webRTC.qualityMetrics.bitrate}kbps</span>
                          </div>
                          <div>
                            <span className="block">RTT: {Math.round(webRTC.qualityMetrics.rtt)}ms</span>
                            <span className="block">Audio: {webRTC.qualityMetrics.audioLevel}%</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Mute Toggle */}
                    <button
                      onClick={webRTC.toggleMute}
                      className={`w-full p-3 rounded-lg font-medium transition-colors ${
                        webRTC.isMuted 
                          ? 'bg-red-500 text-white' 
                          : 'bg-green-500 text-white'
                      }`}
                    >
                      {webRTC.isMuted ? '🔇 Unmute' : '🔊 Mute'}
                    </button>

                    {/* Translation Toggle */}
                    <button
                      onClick={webRTC.toggleTranslation}
                      className={`w-full p-3 rounded-lg font-medium transition-colors ${
                        webRTC.isTranslationEnabled 
                          ? 'bg-blue-500 text-white' 
                          : 'bg-gray-500 text-white'
                      }`}
                    >
                      {webRTC.isTranslationEnabled ? '🌐 Translation: ON' : '🌐 Translation: OFF'}
                    </button>

                    {/* Transcript Toggle */}
                    <button
                      onClick={() => setShowTranscript(!showTranscript)}
                      className="w-full p-3 bg-purple-500 text-white rounded-lg font-medium"
                    >
                      {showTranscript ? '📝 Hide Transcript' : '📝 Show Transcript'}
                    </button>

                    {/* End Call */}
                    <button
                      onClick={webRTC.endCall}
                      className="w-full p-3 bg-red-600 text-white rounded-lg font-medium"
                    >
                      📞 End Call
                    </button>
                  </div>
                </div>

                {/* Real-time Translation Display */}
                <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                  <h3 className="text-xl font-bold text-white mb-4 text-center">
                    Live Translation
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Language Info */}
                    <div className="text-center p-3 bg-blue-100 rounded-lg">
                      <p className="text-blue-800 text-sm">
                        {formatLanguageName(translatedSpeech.detectedLanguage)} → {formatLanguageName(translatedSpeech.targetLanguage)}
                      </p>
                    </div>

                    {/* Listening Status */}
                    {translatedSpeech.isListening && (
                      <div className="text-center p-2 bg-green-100 rounded-lg">
                        <p className="text-green-800 text-sm flex items-center justify-center">
                          <span className="animate-pulse mr-2">🎤</span>
                          Listening...
                        </p>
                      </div>
                    )}

                    {/* Original Speech */}
                    {translatedSpeech.transcript && (
                      <div className="p-4 bg-gray-100 rounded-lg">
                        <p className="text-sm text-gray-600 mb-1">Original:</p>
                        <p className="text-white">{translatedSpeech.transcript}</p>
                      </div>
                    )}

                    {/* Translated Text */}
                    {translatedSpeech.translatedText && (
                      <div className="p-4 bg-emerald-100 rounded-lg">
                        <p className="text-sm text-emerald-600 mb-1">Translation:</p>
                        <p className="text-emerald-800 font-medium">{translatedSpeech.translatedText}</p>
                      </div>
                    )}

                    {/* Error Display */}
                    {translatedSpeech.error && (
                      <div className="p-3 bg-red-100 border border-red-300 rounded-lg">
                        <p className="text-red-800 text-sm">{translatedSpeech.error}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Call History / Transcript */}
                {showTranscript && (
                  <div className="glass-effect backdrop-blur-lg bg-white/20 border border-emerald-400/30 p-6 rounded-2xl shadow-2xl">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xl font-bold text-white">
                        Conversation Log
                      </h3>
                      <button
                        onClick={translatedSpeech.clearHistory}
                        className="text-sm bg-red-500 text-white px-3 py-1 rounded"
                      >
                        Clear
                      </button>
                    </div>
                    
                    <div className="max-h-96 overflow-y-auto space-y-3">
                      {translatedSpeech.transcriptHistory.length === 0 ? (
                        <p className="text-slate-600 text-center italic">
                          No conversation yet. Start speaking to see translations appear here.
                        </p>
                      ) : (
                        translatedSpeech.transcriptHistory
                          .filter(item => item.isFinal)
                          .map((item, index) => (
                            <div key={index} className="p-3 bg-white/50 rounded-lg">
                              <div className="text-sm text-gray-600 mb-1">
                                {new Date(item.timestamp).toLocaleTimeString()}
                              </div>
                              <div className="text-white mb-2">{item.text}</div>
                              {item.translation && (
                                <div className="text-emerald-700 italic">
                                  → {item.translation}
                                </div>
                              )}
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