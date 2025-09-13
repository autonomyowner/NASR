import { io, Socket } from 'socket.io-client'
import { getConfig } from './configService'

// Room-based interfaces
export interface Room {
  id: string
  name: string
  participants: Participant[]
  languageSettings: {
    sourceLanguage: string
    targetLanguage: string
  }
  createdAt: Date
  isActive: boolean
  hostId: string
  shareableLink: string
}

export interface Participant {
  id: string
  name: string
  isHost: boolean
  isConnected: boolean
  language: string
  joinedAt: Date
  peerId: string
}

export interface RoomSettings {
  name: string
  sourceLanguage: string
  targetLanguage: string
  maxParticipants?: number
  isPublic?: boolean
}

export class RoomService {
  private socket: Socket | null = null
  private currentRoom: Room | null = null
  private currentParticipant: Participant | null = null

  // Callbacks
  public onRoomJoined: ((room: Room, participant: Participant) => void) | null = null
  public onRoomLeft: (() => void) | null = null
  public onParticipantJoined: ((participant: Participant) => void) | null = null
  public onParticipantLeft: ((participantId: string) => void) | null = null
  public onRoomError: ((error: string) => void) | null = null
  public onConnectionStatus: ((connected: boolean) => void) | null = null
  public onRoomCreated: ((room: Room) => void) | null = null

  // WebRTC callbacks (for room-based calls)
  public onIncomingCall: ((from: string, offer: RTCSessionDescriptionInit) => void) | null = null
  public onCallAnswered: ((from: string, answer: RTCSessionDescriptionInit) => void) | null = null
  public onIceCandidate: ((candidate: RTCIceCandidateInit) => void) | null = null
  public onCallEnded: (() => void) | null = null
  public onCallFailed: ((reason: string) => void) | null = null

  connect(serverUrl?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const config = getConfig()
        const url = serverUrl || config.signalingUrl
        this.socket = io(url)
        
        this.socket.on('connect', () => {
          console.log('Connected to room signaling server')
          if (this.onConnectionStatus) {
            this.onConnectionStatus(true)
          }
          resolve()
        })

        this.socket.on('disconnect', () => {
          console.log('Disconnected from room signaling server')
          if (this.onConnectionStatus) {
            this.onConnectionStatus(false)
          }
        })

        this.socket.on('connect_error', (error) => {
          console.error('Room signaling server connection error:', error)
          reject(error)
        })

        // Room-based events
        this.socket.on('room-created', (room: Room) => {
          console.log('Room created:', room)
          this.currentRoom = room
          if (this.onRoomCreated) {
            this.onRoomCreated(room)
          }
        })

        this.socket.on('room-joined', ({ room, participant }: { room: Room, participant: Participant }) => {
          console.log('Joined room:', room)
          this.currentRoom = room
          this.currentParticipant = participant
          if (this.onRoomJoined) {
            this.onRoomJoined(room, participant)
          }
        })

        this.socket.on('room-left', () => {
          console.log('Left room')
          this.currentRoom = null
          this.currentParticipant = null
          if (this.onRoomLeft) {
            this.onRoomLeft()
          }
        })

        this.socket.on('participant-joined', (participant: Participant) => {
          console.log('Participant joined:', participant)
          if (this.currentRoom) {
            this.currentRoom.participants.push(participant)
          }
          if (this.onParticipantJoined) {
            this.onParticipantJoined(participant)
          }
        })

        this.socket.on('participant-left', (participantId: string) => {
          console.log('Participant left:', participantId)
          if (this.currentRoom) {
            this.currentRoom.participants = this.currentRoom.participants.filter(p => p.id !== participantId)
          }
          if (this.onParticipantLeft) {
            this.onParticipantLeft(participantId)
          }
        })

        this.socket.on('room-error', ({ error }: { error: string }) => {
          console.error('Room error:', error)
          if (this.onRoomError) {
            this.onRoomError(error)
          }
        })

        // WebRTC events for room-based calls
        this.socket.on('incoming-call', ({ from, offer }) => {
          console.log('Incoming call from:', from)
          if (this.onIncomingCall) {
            this.onIncomingCall(from, offer)
          }
        })

        this.socket.on('call-answered', ({ from, answer }) => {
          console.log('Call answered by:', from)
          if (this.onCallAnswered) {
            this.onCallAnswered(from, answer)
          }
        })

        this.socket.on('ice-candidate', ({ candidate }) => {
          if (this.onIceCandidate) {
            this.onIceCandidate(candidate)
          }
        })

        this.socket.on('call-ended', () => {
          console.log('Call ended by remote peer')
          if (this.onCallEnded) {
            this.onCallEnded()
          }
        })

        this.socket.on('call-failed', ({ reason }) => {
          console.log('Call failed:', reason)
          if (this.onCallFailed) {
            this.onCallFailed(reason)
          }
        })

      } catch (error) {
        reject(error)
      }
    })
  }

  // Room management methods
  createRoom(settings: RoomSettings, participantName: string): void {
    if (this.socket?.connected) {
      this.socket.emit('create-room', {
        ...settings,
        participantName
      })
    }
  }

  joinRoom(roomId: string, participantName: string): void {
    if (this.socket?.connected) {
      this.socket.emit('join-room', {
        roomId,
        participantName
      })
    }
  }

  leaveRoom(): void {
    if (this.socket?.connected && this.currentRoom) {
      this.socket.emit('leave-room', {
        roomId: this.currentRoom.id
      })
    }
  }

  // WebRTC methods for room-based calls
  sendCallRequest(to: string, offer: RTCSessionDescriptionInit): void {
    if (this.socket?.connected && this.currentParticipant) {
      this.socket.emit('call-request', {
        to,
        from: this.currentParticipant.peerId,
        offer
      })
    }
  }

  sendCallAnswer(to: string, answer: RTCSessionDescriptionInit): void {
    if (this.socket?.connected && this.currentParticipant) {
      this.socket.emit('call-answer', {
        to,
        from: this.currentParticipant.peerId,
        answer
      })
    }
  }

  sendIceCandidate(to: string, candidate: RTCIceCandidateInit): void {
    if (this.socket?.connected) {
      this.socket.emit('ice-candidate', {
        to,
        candidate
      })
    }
  }

  endCall(to: string): void {
    if (this.socket?.connected && this.currentParticipant) {
      this.socket.emit('end-call', { 
        to, 
        from: this.currentParticipant.peerId 
      })
    }
  }

  // Utility methods
  getCurrentRoom(): Room | null {
    return this.currentRoom
  }

  getCurrentParticipant(): Participant | null {
    return this.currentParticipant
  }

  isInRoom(): boolean {
    return this.currentRoom !== null
  }

  generateShareableLink(roomId: string): string {
    const baseUrl = window.location.origin
    return `${baseUrl}/room/${roomId}`
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.currentRoom = null
      this.currentParticipant = null
    }
  }
}

export const roomService = new RoomService()
