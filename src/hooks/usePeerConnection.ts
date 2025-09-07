import { useState, useEffect, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
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
  const [peerId] = useState(() => {
    // Get or create persistent peer ID
    const stored = localStorage.getItem('travoice-peer-id')
    if (stored) return stored
    
    const newId = uuidv4()
    localStorage.setItem('travoice-peer-id', newId)
    return newId
  })

  const [isConnected, setIsConnected] = useState(false)
  const [onlineUsers, setOnlineUsers] = useState<string[]>([])
  const [connectionError, setConnectionError] = useState<string | null>(null)

  const connect = useCallback(async () => {
    try {
      setConnectionError(null)
      await signalingService.connect()
      signalingService.register(peerId)
    } catch (error) {
      console.error('Failed to connect to signaling server:', error)
      setConnectionError(error instanceof Error ? error.message : 'Connection failed')
    }
  }, [peerId])

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

  return {
    peerId,
    isConnected,
    onlineUsers,
    connectionError,
    copyPeerId,
    reconnect
  }
}