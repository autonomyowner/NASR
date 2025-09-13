import { useState, useEffect, useCallback } from 'react'
import { signalingService } from '../services/signalingService'

export interface PeerConnectionState {
  peerId: string
  isConnected: boolean
  onlineUsers: string[]
  connectionError: string | null
}

export interface PeerConnectionActions {
  copyPeerId: () => Promise<void>
  reconnect: () => Promise<void>
}

export const usePeerConnection = (): PeerConnectionState & PeerConnectionActions => {
  const [peerId, setPeerId] = useState(() => {
    // Get stored peer ID, but don't create one - wait for server assignment
    return localStorage.getItem('travoice-peer-id') || ''
  })

  const [isConnected, setIsConnected] = useState(false)
  const [onlineUsers, setOnlineUsers] = useState<string[]>([])
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const connect = useCallback(async () => {
    try {
      setConnectionError(null)
      await signalingService.connect()
      // Peer ID will be assigned automatically by server
    } catch (error) {
      console.error('Failed to connect to signaling server:', error)
      setConnectionError(error instanceof Error ? error.message : 'Connection failed')
    }
  }, [])

  const copyPeerId = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(peerId)
    } catch (error) {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea')
      textArea.value = peerId
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
    }
  }, [peerId])

  const reconnect = useCallback(async () => {
    signalingService.disconnect()
    await connect()
  }, [connect])

  // Set up signaling service callbacks
  useEffect(() => {
    signalingService.onConnectionStatus = setIsConnected
    signalingService.onUsersUpdated = setOnlineUsers

    // Connect on mount
    connect()

    return () => {
      signalingService.disconnect()
    }
  }, [connect])

  // Listen for peer ID updates from signaling service
  useEffect(() => {
    const checkPeerIdUpdate = () => {
      const currentStoredId = localStorage.getItem('travoice-peer-id')
      if (currentStoredId && currentStoredId !== peerId) {
        setPeerId(currentStoredId)
      }
    }

    const interval = setInterval(checkPeerIdUpdate, 100)
    return () => clearInterval(interval)
  }, [peerId])

  return {
    peerId,
    isConnected,
    onlineUsers,
    connectionError,
    copyPeerId,
    reconnect
  }
}