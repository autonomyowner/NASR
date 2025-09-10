export interface CallState {
  isCallActive: boolean
  isConnecting: boolean
  isMuted: boolean
  isTranslationEnabled: boolean
  isDelayEnabled: boolean
  localStream: MediaStream | null
  remoteStream: MediaStream | null
  callId: string | null
  peerId: string | null
  peerConnection?: RTCPeerConnection | null
  qualityMetrics?: CallQualityMetrics
  qualityScore?: number
  qualityText?: string
}

export interface CallQualityMetrics {
  connectionState: string
  iceConnectionState: string
  audioLevel: number
  packetsLost: number
  packetsReceived: number
  jitter: number
  rtt: number
  bitrate: number
  networkType: string
  signalStrength: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown'
}

export interface CallControls {
  startCall: (peerId: string) => Promise<void>
  endCall: () => void
  toggleMute: () => void
  toggleTranslation: () => void
  toggleDelay: () => void
  answerCall: (fromPeerId: string, offer: RTCSessionDescriptionInit) => Promise<void>
  declineCall: () => void
  handleCallAnswer: (fromPeerId: string, answer: RTCSessionDescriptionInit) => Promise<void>
  handleIceCandidate: (candidate: RTCIceCandidateInit) => Promise<void>
}

export interface TranscriptionData {
  text: string
  language: string
  translation?: string
  timestamp: number
  isFinal: boolean
}

export interface SignalingMessage {
  type: 'offer' | 'answer' | 'ice-candidate' | 'call-request' | 'call-accepted' | 'call-declined' | 'call-ended'
  data?: unknown
  from: string
  to: string
  callId: string
}