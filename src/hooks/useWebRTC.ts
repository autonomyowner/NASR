import { useState, useEffect, useRef, useCallback } from 'react'
import type { CallState, CallControls } from '../types/call'
import { useCallQuality } from './useCallQuality'
import { v4 as uuidv4 } from 'uuid'

const ICE_SERVERS = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' }
]

export const useWebRTC = (): CallState & CallControls => {
  const [callState, setCallState] = useState<CallState>({
    isCallActive: false,
    isConnecting: false,
    isMuted: false,
    isTranslationEnabled: false,
    localStream: null,
    remoteStream: null,
    callId: null,
    peerId: null,
    qualityMetrics: undefined,
    qualityScore: 0,
    qualityText: 'Unknown'
  })

  const peerConnection = useRef<RTCPeerConnection | null>(null)
  
  // Initialize call quality monitoring
  const callQuality = useCallQuality()

  // Initialize peer connection
  const initializePeerConnection = useCallback(() => {
    if (peerConnection.current) {
      peerConnection.current.close()
    }

    peerConnection.current = new RTCPeerConnection({ iceServers: ICE_SERVERS })

    // Handle incoming remote stream
    peerConnection.current.ontrack = (event) => {
      const [remoteStream] = event.streams
      setCallState(prev => ({ ...prev, remoteStream }))
    }

    // Handle ICE candidates
    peerConnection.current.onicecandidate = (event) => {
      if (event.candidate) {
        // In a real app, send this via signaling server
        console.log('ICE candidate:', event.candidate)
      }
    }

    // Handle connection state changes
    peerConnection.current.onconnectionstatechange = () => {
      const state = peerConnection.current?.connectionState
      console.log('Connection state:', state)
      
      if (state === 'connected') {
        setCallState(prev => ({ ...prev, isConnecting: false, isCallActive: true }))
        // Start call quality monitoring when connected
        if (peerConnection.current) {
          callQuality.startMonitoring(peerConnection.current)
        }
      } else if (state === 'disconnected' || state === 'failed' || state === 'closed') {
        endCall()
      }
    }
  }, [])

  // Get user media (audio only for voice calls)
  const getUserMedia = useCallback(async (): Promise<MediaStream> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      setCallState(prev => ({ ...prev, localStream: stream }))
      return stream
    } catch (error) {
      console.error('Error accessing microphone:', error)
      throw new Error('Could not access microphone. Please check permissions.')
    }
  }, [])

  // Start a call
  const startCall = useCallback(async (peerId: string) => {
    try {
      setCallState(prev => ({ ...prev, isConnecting: true, callId: uuidv4(), peerId }))
      
      initializePeerConnection()
      const localStream = await getUserMedia()

      // Add local stream to peer connection
      localStream.getTracks().forEach(track => {
        peerConnection.current?.addTrack(track, localStream)
      })

      // Create offer
      const offer = await peerConnection.current!.createOffer()
      await peerConnection.current!.setLocalDescription(offer)

      // In a real app, send offer via signaling server
      console.log('Created offer:', offer)
      
    } catch (error) {
      console.error('Error starting call:', error)
      setCallState(prev => ({ ...prev, isConnecting: false }))
      throw error
    }
  }, [initializePeerConnection, getUserMedia])

  // Answer a call
  const answerCall = useCallback(async () => {
    try {
      setCallState(prev => ({ ...prev, isConnecting: true }))
      
      initializePeerConnection()
      const localStream = await getUserMedia()

      // Add local stream to peer connection
      localStream.getTracks().forEach(track => {
        peerConnection.current?.addTrack(track, localStream)
      })

      // In a real app, this would be triggered by receiving an offer
      // For now, we'll simulate it
      console.log('Answering call...')
      
    } catch (error) {
      console.error('Error answering call:', error)
      setCallState(prev => ({ ...prev, isConnecting: false }))
      throw error
    }
  }, [initializePeerConnection, getUserMedia])

  // End call
  const endCall = useCallback(() => {
    // Stop call quality monitoring
    callQuality.stopMonitoring()
    
    // Stop all tracks
    callState.localStream?.getTracks().forEach(track => track.stop())
    
    // Close peer connection
    if (peerConnection.current) {
      peerConnection.current.close()
      peerConnection.current = null
    }

    // Reset state
    setCallState({
      isCallActive: false,
      isConnecting: false,
      isMuted: false,
      isTranslationEnabled: false,
      localStream: null,
      remoteStream: null,
      callId: null,
      peerId: null,
      qualityMetrics: undefined,
      qualityScore: 0,
      qualityText: 'Unknown'
    })
  }, [callState.localStream, callQuality])

  // Decline call
  const declineCall = useCallback(() => {
    endCall()
  }, [endCall])

  // Toggle mute
  const toggleMute = useCallback(() => {
    if (callState.localStream) {
      const audioTrack = callState.localStream.getAudioTracks()[0]
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled
        setCallState(prev => ({ ...prev, isMuted: !audioTrack.enabled }))
      }
    }
  }, [callState.localStream])

  // Toggle translation
  const toggleTranslation = useCallback(() => {
    setCallState(prev => ({ ...prev, isTranslationEnabled: !prev.isTranslationEnabled }))
  }, [])

  // Update call state with quality metrics
  useEffect(() => {
    if (callQuality.isMonitoring) {
      setCallState(prev => ({
        ...prev,
        qualityMetrics: callQuality.metrics,
        qualityScore: callQuality.getQualityScore(),
        qualityText: callQuality.getQualityText()
      }))
    }
  }, [callQuality.metrics, callQuality.isMonitoring])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endCall()
    }
  }, [])

  return {
    ...callState,
    startCall,
    endCall,
    toggleMute,
    toggleTranslation,
    answerCall,
    declineCall
  }
}