import React, { useState, useEffect, useRef } from 'react'
import { roomService, type Room, type Participant } from '../services/roomService'
import { useTranslatedSpeech } from '../hooks/useTranslatedSpeech'
import { useNotifications } from '../hooks/useNotifications'
import { useWebRTC } from '../hooks/useWebRTC'
import EnhancedRoomManager from './EnhancedRoomManager'
import CallTimer from './CallTimer'
import NotificationContainer from './NotificationContainer'

const EnhancedCall: React.FC = () => {
  const [currentRoom, setCurrentRoom] = useState<Room | null>(null)
  const [currentParticipant, setCurrentParticipant] = useState<Participant | null>(null)
  const [isInRoom, setIsInRoom] = useState(false)
  const [showTranscript] = useState(true)
  const [selectedLanguage, setSelectedLanguage] = useState('es-ES')
  
  const webRTC = useWebRTC()
  const translatedSpeech = useTranslatedSpeech(selectedLanguage)
  const notifications = useNotifications()
  const callStartTimeRef = useRef<number | null>(null)

  // Connect to room service
  useEffect(() => {
    roomService.connect().catch(error => {
      console.error('Failed to connect to room service:', error)
      notifications.error('Connection Error', 'Failed to connect to room service')
    })
  }, [notifications])

  // Auto-start/stop translation based on call state
  useEffect(() => {
    if (webRTC.isCallActive && webRTC.isTranslationEnabled) {
      translatedSpeech.startListening()
    } else {
      translatedSpeech.stopListening()
    }
  }, [webRTC.isCallActive, webRTC.isTranslationEnabled])

  // Handle call start - track time
  useEffect(() => {
    if (webRTC.isCallActive && !callStartTimeRef.current) {
      callStartTimeRef.current = Date.now()
    } else if (!webRTC.isCallActive) {
      callStartTimeRef.current = null
    }
  }, [webRTC.isCallActive])

  // Set up room service callbacks
  useEffect(() => {
    roomService.onRoomJoined = (room: Room, participant: Participant) => {
      setCurrentRoom(room)
      setCurrentParticipant(participant)
      setIsInRoom(true)
      setSelectedLanguage(room.languageSettings.targetLanguage)
    }

    roomService.onRoomLeft = () => {
      setCurrentRoom(null)
      setCurrentParticipant(null)
      setIsInRoom(false)
      if (webRTC.isCallActive) {
        webRTC.endCall()
      }
    }

    roomService.onParticipantJoined = (participant: Participant) => {
      notifications.info('New Participant', `${participant.name} joined the room`)
    }

    roomService.onParticipantLeft = (participantId: string) => {
      const participant = currentRoom?.participants.find(p => p.id === participantId)
      if (participant) {
        notifications.info('Participant Left', `${participant.name} left the room`)
      }
    }

    roomService.onRoomError = (error: string) => {
      notifications.error('Room Error', error)
    }

    // WebRTC callbacks
    roomService.onIncomingCall = (from: string, offer: RTCSessionDescriptionInit) => {
      // Handle incoming call from room participant
      webRTC.answerCall(from, offer)
    }

    roomService.onCallAnswered = (from: string, answer: RTCSessionDescriptionInit) => {
      webRTC.handleCallAnswer(from, answer)
    }

    roomService.onIceCandidate = (candidate: RTCIceCandidateInit) => {
      webRTC.handleIceCandidate(candidate)
    }

    roomService.onCallEnded = () => {
      webRTC.endCall()
    }

    roomService.onCallFailed = (reason: string) => {
      notifications.error('Call Failed', reason)
    }

    return () => {
      roomService.onRoomJoined = null
      roomService.onRoomLeft = null
      roomService.onParticipantJoined = null
      roomService.onParticipantLeft = null
      roomService.onRoomError = null
      roomService.onIncomingCall = null
      roomService.onCallAnswered = null
      roomService.onIceCandidate = null
      roomService.onCallEnded = null
      roomService.onCallFailed = null
    }
  }, [webRTC, notifications, currentRoom])

  const handleStartCall = async (participantId: string) => {
    if (!currentRoom || !currentParticipant) return

    try {
      await webRTC.startCall(participantId)
      notifications.info('Calling...', `Connecting to ${participantId}`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      notifications.error('Call Failed', `Failed to start call: ${errorMessage}`)
    }
  }

  const handleLeaveRoom = () => {
    roomService.leaveRoom()
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

  if (!isInRoom) {
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
            <EnhancedRoomManager 
              onRoomJoined={(room, participant) => {
                setCurrentRoom(room)
                setCurrentParticipant(participant)
                setIsInRoom(true)
              }}
              onRoomLeft={() => {
                setCurrentRoom(null)
                setCurrentParticipant(null)
                setIsInRoom(false)
              }}
            />
          </div>
        </div>

        {/* Notifications */}
        <NotificationContainer
          notifications={notifications.notifications}
          onClose={notifications.removeNotification}
        />
      </section>
    )
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
          {/* Room Header */}
          <div className="text-center mb-8">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Room: <span className="text-cyan-400">{currentRoom?.name}</span>
            </h2>
            <div className="flex justify-center items-center gap-4 text-slate-300 mb-4">
              <span>Language: {formatLanguageName(currentRoom?.languageSettings.sourceLanguage || '')} → {formatLanguageName(currentRoom?.languageSettings.targetLanguage || '')}</span>
              <button
                onClick={handleLeaveRoom}
                className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                Leave Room
              </button>
            </div>
          </div>

          {!webRTC.isCallActive ? (
            /* Room Interface - Show Participants */
            <div className="max-w-6xl mx-auto space-y-8">
              {/* Participants List */}
              <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-8 rounded-3xl shadow-2xl">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse mr-3"></div>
                  <h3 className="text-2xl font-bold text-white">Room Participants</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {currentRoom?.participants.map(participant => (
                    <div key={participant.id} className="p-4 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                      <div className="flex items-center space-x-3 mb-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                          {participant.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-white font-semibold">{participant.name}</p>
                          <p className="text-gray-400 text-sm">{formatLanguageName(participant.language)}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <div className={`w-2 h-2 rounded-full ${
                            participant.isConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                          }`}></div>
                          <span className="text-sm text-gray-300">
                            {participant.isConnected ? 'Online' : 'Offline'}
                          </span>
                        </div>
                        
                        {participant.id !== currentParticipant?.id && participant.isConnected && (
                          <button
                            onClick={() => handleStartCall(participant.peerId)}
                            className="px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg shadow-green-500/25"
                          >
                            📞 Call
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Room Info */}
              <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl">
                <div className="text-center">
                  <h3 className="text-xl font-bold text-white mb-4">Room Information</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="p-3 bg-white/5 border border-white/10 rounded-xl">
                      <p className="text-gray-400">Room ID</p>
                      <p className="text-white font-mono">{currentRoom?.id}</p>
                    </div>
                    <div className="p-3 bg-white/5 border border-white/10 rounded-xl">
                      <p className="text-gray-400">Participants</p>
                      <p className="text-white font-semibold">{currentRoom?.participants.length}</p>
                    </div>
                    <div className="p-3 bg-white/5 border border-white/10 rounded-xl">
                      <p className="text-gray-400">Created</p>
                      <p className="text-white">{currentRoom?.createdAt.toLocaleString()}</p>
                    </div>
                  </div>
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

                {/* Conversation Log - Enhanced */}
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

      {/* Notifications */}
      <NotificationContainer
        notifications={notifications.notifications}
        onClose={notifications.removeNotification}
      />
    </section>
  )
}

export default EnhancedCall
