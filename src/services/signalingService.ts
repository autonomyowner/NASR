import { io, Socket } from 'socket.io-client'

export class SignalingService {
  private socket: Socket | null = null
  private currentPeerId: string | null = null
  private onlineUsers: string[] = []

  // Callbacks
  public onIncomingCall: ((from: string, offer: RTCSessionDescriptionInit) => void) | null = null
  public onCallAnswered: ((from: string, answer: RTCSessionDescriptionInit) => void) | null = null
  public onIceCandidate: ((candidate: RTCIceCandidateInit) => void) | null = null
  public onCallEnded: (() => void) | null = null
  public onUsersUpdated: ((users: string[]) => void) | null = null
  public onConnectionStatus: ((connected: boolean) => void) | null = null

  connect(serverUrl: string = 'ws://localhost:3001'): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = io(serverUrl)
        
        this.socket.on('connect', () => {
          console.log('Connected to signaling server')
          if (this.onConnectionStatus) {
            this.onConnectionStatus(true)
          }
          resolve()
        })

        this.socket.on('disconnect', () => {
          console.log('Disconnected from signaling server')
          if (this.onConnectionStatus) {
            this.onConnectionStatus(false)
          }
        })

        this.socket.on('connect_error', (error) => {
          console.error('Signaling server connection error:', error)
          reject(error)
        })

        // Handle incoming calls
        this.socket.on('incoming-call', ({ from, offer }) => {
          console.log('Incoming call from:', from)
          if (this.onIncomingCall) {
            this.onIncomingCall(from, offer)
          }
        })

        // Handle call answers
        this.socket.on('call-answered', ({ from, answer }) => {
          console.log('Call answered by:', from)
          if (this.onCallAnswered) {
            this.onCallAnswered(from, answer)
          }
        })

        // Handle ICE candidates
        this.socket.on('ice-candidate', ({ candidate }) => {
          if (this.onIceCandidate) {
            this.onIceCandidate(candidate)
          }
        })

        // Handle call end
        this.socket.on('call-ended', () => {
          console.log('Call ended by remote peer')
          if (this.onCallEnded) {
            this.onCallEnded()
          }
        })

        // Handle online users
        this.socket.on('users-online', (users: string[]) => {
          this.onlineUsers = users
          if (this.onUsersUpdated) {
            this.onUsersUpdated(users)
          }
        })

        // Handle call failures
        this.socket.on('call-failed', ({ reason }) => {
          console.log('Call failed:', reason)
          alert(`Call failed: ${reason}`)
        })

      } catch (error) {
        reject(error)
      }
    })
  }

  register(peerId: string): void {
    if (this.socket?.connected) {
      this.currentPeerId = peerId
      this.socket.emit('register', peerId)
      console.log('Registered with peer ID:', peerId)
    }
  }

  sendCallRequest(to: string, offer: RTCSessionDescriptionInit): void {
    if (this.socket?.connected && this.currentPeerId) {
      this.socket.emit('call-request', {
        to,
        from: this.currentPeerId,
        offer
      })
    }
  }

  sendCallAnswer(to: string, answer: RTCSessionDescriptionInit): void {
    if (this.socket?.connected && this.currentPeerId) {
      this.socket.emit('call-answer', {
        to,
        from: this.currentPeerId,
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
    if (this.socket?.connected) {
      this.socket.emit('end-call', { to })
    }
  }

  getOnlineUsers(): string[] {
    return this.onlineUsers.filter(user => user !== this.currentPeerId)
  }

  isUserOnline(peerId: string): boolean {
    return this.onlineUsers.includes(peerId)
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.currentPeerId = null
      this.onlineUsers = []
    }
  }
}

export const signalingService = new SignalingService()