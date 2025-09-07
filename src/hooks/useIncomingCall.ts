import { useState, useEffect, useCallback } from 'react'
import { signalingService } from '../services/signalingService'

export interface IncomingCall {
  fromPeerId: string
  offer: RTCSessionDescriptionInit
  timestamp: number
}

export interface IncomingCallState {
  incomingCall: IncomingCall | null
  isRinging: boolean
}

export interface IncomingCallActions {
  acceptCall: () => Promise<void>
  declineCall: () => void
}

export const useIncomingCall = (
  onAcceptCall: (fromPeerId: string, offer: RTCSessionDescriptionInit) => Promise<void>
): IncomingCallState & IncomingCallActions => {
  const [incomingCall, setIncomingCall] = useState<IncomingCall | null>(null)
  const [isRinging, setIsRinging] = useState(false)

  const handleIncomingCall = useCallback((fromPeerId: string, offer: RTCSessionDescriptionInit) => {
    const newIncomingCall: IncomingCall = {
      fromPeerId,
      offer,
      timestamp: Date.now()
    }
    
    setIncomingCall(newIncomingCall)
    setIsRinging(true)

    // Auto-decline after 30 seconds
    const timeout = setTimeout(() => {
      if (incomingCall?.fromPeerId === fromPeerId) {
        declineCall()
      }
    }, 30000)

    return () => clearTimeout(timeout)
  }, [])

  const acceptCall = useCallback(async () => {
    if (incomingCall) {
      setIsRinging(false)
      try {
        await onAcceptCall(incomingCall.fromPeerId, incomingCall.offer)
      } catch (error) {
        console.error('Error accepting call:', error)
      }
      setIncomingCall(null)
    }
  }, [incomingCall, onAcceptCall])

  const declineCall = useCallback(() => {
    setIsRinging(false)
    setIncomingCall(null)
  }, [])

  // Set up signaling service callback
  useEffect(() => {
    signalingService.onIncomingCall = handleIncomingCall
    
    return () => {
      signalingService.onIncomingCall = null
    }
  }, [handleIncomingCall])

  return {
    incomingCall,
    isRinging,
    acceptCall,
    declineCall
  }
}