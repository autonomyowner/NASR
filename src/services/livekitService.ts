import { 
  Room, 
  RoomEvent, 
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication,
  Track,
  ConnectionState,
  type RoomOptions,
  VideoPresets,
  DataPacket_Kind,
  LocalTrackPublication
} from 'livekit-client'

export interface LiveKitConfig {
  url: string
  token: string
}

export interface TranslationTrack {
  participant: RemoteParticipant
  audioTrack: RemoteTrack | null
  language: string
  isTranslated: boolean
}

export interface LiveKitServiceEvents {
  onParticipantConnected: (participant: RemoteParticipant) => void
  onParticipantDisconnected: (participant: RemoteParticipant) => void
  onTrackSubscribed: (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => void
  onTrackUnsubscribed: (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => void
  onConnectionStateChanged: (state: ConnectionState) => void
  onTranslationReceived: (translation: string, language: string, confidence: number) => void
  onError: (error: Error) => void
}

export class LiveKitService {
  private room: Room | null = null
  private localAudioTrack: LocalTrackPublication | null = null
  private translationTracks: Map<string, TranslationTrack> = new Map()
  private events: Partial<LiveKitServiceEvents> = {}
  private connected = false
  private currentLanguage = 'en-US'
  private enabledTranslationLanguages: Set<string> = new Set(['es', 'fr', 'de'])

  constructor() {
    this.setupRoom()
  }

  private setupRoom(): void {
    const roomOptions: RoomOptions = {
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: {
        resolution: VideoPresets.h720.resolution
      },
      publishDefaults: {
        audioPreset: {
          maxBitrate: 64_000, // Optimize for speech
        },
        red: true, // Enable RED for packet loss recovery
        dtx: true  // Discontinuous transmission for silence suppression
      },
      // WebRTC configuration for optimal performance
      webAudioMix: true
    }

    this.room = new Room(roomOptions)
    this.attachRoomEvents()
  }

  private attachRoomEvents(): void {
    if (!this.room) return

    this.room.on(RoomEvent.Connected, () => {
      console.log('✅ Connected to LiveKit room')
      this.connected = true
      this.events.onConnectionStateChanged?.(ConnectionState.Connected)
    })

    this.room.on(RoomEvent.Disconnected, () => {
      console.log('🔌 Disconnected from LiveKit room')
      this.connected = false
      this.events.onConnectionStateChanged?.(ConnectionState.Disconnected)
    })

    this.room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
      console.log('👤 Participant connected:', participant.identity)
      this.handleParticipantConnected(participant)
      this.events.onParticipantConnected?.(participant)
    })

    this.room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
      console.log('👤 Participant disconnected:', participant.identity)
      this.translationTracks.delete(participant.identity)
      this.events.onParticipantDisconnected?.(participant)
    })

    this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
      console.log('🎵 Track subscribed:', track.kind, 'from', participant.identity)
      this.handleTrackSubscribed(track, publication, participant)
      this.events.onTrackSubscribed?.(track, publication, participant)
    })

    this.room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
      console.log('🎵 Track unsubscribed:', track.kind, 'from', participant.identity)
      this.events.onTrackUnsubscribed?.(track, publication, participant)
    })

    this.room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant, _kind?: DataPacket_Kind, topic?: string) => {
      if (topic === 'translation') {
        this.handleTranslationData(payload, participant)
      }
    })

    this.room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      console.log('🔗 Connection state changed:', state)
      this.connected = state === ConnectionState.Connected
      this.events.onConnectionStateChanged?.(state)
    })

    this.room.on(RoomEvent.Reconnecting, () => {
      console.log('🔄 Reconnecting to LiveKit room...')
    })

    this.room.on(RoomEvent.Reconnected, () => {
      console.log('✅ Reconnected to LiveKit room')
      this.connected = true
    })
  }

  private handleParticipantConnected(participant: RemoteParticipant): void {
    // Check if this is a translator participant
    const isTranslator = participant.metadata ? 
      JSON.parse(participant.metadata).role === 'translator' : false

    if (isTranslator) {
      console.log('🤖 Translator participant detected:', participant.identity)
    }
  }

  private handleTrackSubscribed(track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant): void {
    if (track.kind === Track.Kind.Audio) {
      // Check if this is a translated audio track based on track name
      const trackName = publication.trackName || ''
      const isTranslated = trackName.includes('translated')
      const languageMatch = trackName.match(/_([a-z]{2})$/)
      const language = languageMatch ? languageMatch[1] : 'unknown'

      const translationTrack: TranslationTrack = {
        participant,
        audioTrack: track,
        language,
        isTranslated
      }

      this.translationTracks.set(`${participant.identity}_${language}`, translationTrack)

      console.log(`🎧 ${isTranslated ? 'Translated' : 'Original'} audio track (${language}) from ${participant.identity}`)
    }
  }

  private handleTranslationData(payload: Uint8Array, _participant?: RemoteParticipant): void {
    try {
      const textDecoder = new TextDecoder()
      const data = JSON.parse(textDecoder.decode(payload))
      
      if (data.type === 'translation') {
        console.log('📝 Translation received:', data.text, `(${data.language}, confidence: ${data.confidence})`)
        this.events.onTranslationReceived?.(data.text, data.language, data.confidence)
      }
    } catch (error) {
      console.error('❌ Error parsing translation data:', error)
    }
  }

  async connect(config: LiveKitConfig): Promise<void> {
    if (!this.room) {
      throw new Error('Room not initialized')
    }

    try {
      console.log('🔗 Connecting to LiveKit SFU:', config.url)
      await this.room.connect(config.url, config.token)
      console.log('✅ Successfully connected to LiveKit room')
    } catch (error) {
      console.error('❌ Failed to connect to LiveKit room:', error)
      this.events.onError?.(error as Error)
      throw error
    }
  }

  async enableMicrophone(deviceId?: string): Promise<LocalTrackPublication> {
    if (!this.room) {
      throw new Error('Room not connected')
    }

    try {
      // Create local audio track with optimized settings for speech
      const tracks = await this.room.localParticipant.createTracks({
        audio: {
          deviceId,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000, // High quality for better transcription
          channelCount: 1,   // Mono for speech
        }
      })
      const audioTrack = tracks.find(track => track.kind === Track.Kind.Audio)!
      
      if (!audioTrack) {
        throw new Error('Failed to create audio track')
      }

      // Publish the track
      this.localAudioTrack = await this.room.localParticipant.publishTrack(audioTrack, {
        name: `audio_${this.currentLanguage}`
      })

      console.log('🎤 Microphone enabled and published')
      return this.localAudioTrack

    } catch (error) {
      console.error('❌ Failed to enable microphone:', error)
      this.events.onError?.(error as Error)
      throw error
    }
  }

  async disableMicrophone(): Promise<void> {
    if (this.localAudioTrack) {
      await this.room?.localParticipant.unpublishTrack(this.localAudioTrack.track!)
      this.localAudioTrack = null
      console.log('🎤 Microphone disabled')
    }
  }

  setMicrophoneMuted(muted: boolean): void {
    if (this.localAudioTrack?.track) {
      if (muted) {
        this.localAudioTrack.track.mute()
      } else {
        this.localAudioTrack.track.unmute()
      }
      console.log(`🎤 Microphone ${muted ? 'muted' : 'unmuted'}`)
    }
  }

  // Request translation for specific languages
  requestTranslation(languages: string[]): void {
    if (!this.room || !this.connected) {
      console.warn('⚠️ Cannot request translation: room not connected')
      return
    }

    const request = {
      type: 'translation_request',
      languages,
      source_language: this.currentLanguage,
      timestamp: Date.now()
    }

    const encoder = new TextEncoder()
    const payload = encoder.encode(JSON.stringify(request))

    this.room.localParticipant.publishData(payload, { topic: 'translation_control' })
    this.enabledTranslationLanguages = new Set(languages)
    
    console.log('🔄 Translation requested for languages:', languages)
  }

  // Send text for translation via data channel
  sendTextForTranslation(text: string, targetLanguages: string[]): void {
    if (!this.room || !this.connected) {
      console.warn('⚠️ Cannot send text for translation: room not connected')
      return
    }

    const request = {
      type: 'translate_text',
      text,
      source_language: this.currentLanguage,
      target_languages: targetLanguages,
      timestamp: Date.now()
    }

    const encoder = new TextEncoder()
    const payload = encoder.encode(JSON.stringify(request))

    this.room.localParticipant.publishData(payload, { topic: 'translation_request' })
    console.log('💬 Text sent for translation:', text)
  }

  // Get all available translation tracks
  getTranslationTracks(): TranslationTrack[] {
    return Array.from(this.translationTracks.values())
  }

  // Get specific language track
  getLanguageTrack(language: string): TranslationTrack | null {
    for (const track of this.translationTracks.values()) {
      if (track.language === language && track.isTranslated) {
        return track
      }
    }
    return null
  }

  // Set current user's language
  setCurrentLanguage(language: string): void {
    this.currentLanguage = language
    console.log('🌐 Current language set to:', language)
  }

  // Event subscription methods
  on<K extends keyof LiveKitServiceEvents>(event: K, handler: LiveKitServiceEvents[K]): void {
    this.events[event] = handler
  }

  off<K extends keyof LiveKitServiceEvents>(event: K): void {
    delete this.events[event]
  }

  // Connection status
  isConnected(): boolean {
    return this.connected && this.room?.state === ConnectionState.Connected
  }

  // Get room statistics for monitoring
  getRoomStats() {
    if (!this.room) return null

    return {
      participantCount: this.room.numParticipants + 1, // +1 for local participant
      translationTracks: this.translationTracks.size,
      enabledLanguages: Array.from(this.enabledTranslationLanguages),
      connectionState: this.room.state,
      localParticipant: {
        identity: this.room.localParticipant.identity,
        audioTracks: this.room.localParticipant.audioTrackPublications.size,
      }
    }
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      await this.room.disconnect()
      this.room = null
      this.connected = false
      this.translationTracks.clear()
      console.log('🔌 Disconnected from LiveKit room')
    }
  }

  // Cleanup
  destroy(): void {
    this.disconnect()
    this.events = {}
  }
}

// Singleton instance for global use
export const liveKitService = new LiveKitService()

// Helper function to generate LiveKit tokens (for development)
export async function generateLiveKitToken(
  apiKey: string,
  _apiSecret: string,
  roomName: string,
  participantName: string,
  metadata?: string
): Promise<string> {
  // In production, this should be done on your backend server
  // This is a simplified version for development
  const now = Math.floor(Date.now() / 1000)
  const exp = now + (6 * 60 * 60) // 6 hours

  const payload = {
    iss: apiKey,
    sub: participantName,
    aud: roomName,
    exp: exp,
    nbf: now,
    video: {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true,
      canUpdateOwnMetadata: true,
    }
  }

  if (metadata) {
    (payload.video as any).metadata = metadata
  }

  // Note: In production, use a proper JWT library on your backend
  console.warn('⚠️ Token generation should be done on backend in production')
  
  // For development, you'll need to implement proper JWT signing
  // or use your backend service to generate tokens
  return 'your-jwt-token-here'
}