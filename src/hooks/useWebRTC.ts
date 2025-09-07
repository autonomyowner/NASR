import { useState, useEffect, useRef, useCallback } from 'react'
import type { CallState, CallControls } from '../types/call'
import { useCallQuality } from './useCallQuality'
import { v4 as uuidv4 } from 'uuid'
import { getConfig } from '../services/configService'
import { signalingService } from '../services/signalingService'

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
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null)
  const currentPeerIdRef = useRef<string | null>(null)
  
  // Initialize call quality monitoring
  const callQuality = useCallQuality()

  // Initialize peer connection
  const initializePeerConnection = useCallback(() => {
    if (peerConnection.current) {
      peerConnection.current.close()
    }

    const config = getConfig()
    peerConnection.current = new RTCPeerConnection({ iceServers: config.iceServers })

    // Handle incoming remote stream
    peerConnection.current.ontrack = (event) => {
      const [remoteStream] = event.streams
      setCallState(prev => ({ ...prev, remoteStream }))
      
      // Play remote audio
      if (!remoteAudioRef.current) {
        remoteAudioRef.current = new Audio()
        remoteAudioRef.current.autoplay = true
      }
      remoteAudioRef.current.srcObject = remoteStream
    }

    // Handle ICE candidates
    peerConnection.current.onicecandidate = (event) => {
      if (event.candidate && currentPeerIdRef.current) {
        signalingService.sendIceCandidate(currentPeerIdRef.current, event.candidate)
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
      // Check if mediaDevices is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Your browser does not support microphone access.')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      setCallState(prev => ({ ...prev, localStream: stream }))
      return stream
    } catch (error: any) {
      console.error('Error accessing microphone:', error)
      
      let errorMessage = 'Could not access microphone.'
      
      if (error.name === 'NotFoundError') {
        errorMessage = 'No microphone found. Please connect a microphone and try again.'
      } else if (error.name === 'NotAllowedError') {
        errorMessage = 'Microphone access denied. Please allow microphone access and try again.'
      } else if (error.name === 'NotSupportedError') {
        errorMessage = 'Your browser does not support microphone access.'
      } else if (error.name === 'OverconstrainedError') {
        errorMessage = 'Microphone constraints not supported. Please try with a different microphone.'
      }
      
      throw new Error(errorMessage)
    }
  }, [])

  // Start a call
  const startCall = useCallback(async (peerId: string) => {
    try {
      setCallState(prev => ({ ...prev, isConnecting: true, callId: uuidv4(), peerId }))
      currentPeerIdRef.current = peerId
      
      initializePeerConnection()
      const localStream = await getUserMedia()

      // Add local stream to peer connection
      localStream.getTracks().forEach(track => {
        peerConnection.current?.addTrack(track, localStream)
      })

      // Create offer
      const offer = await peerConnection.current!.createOffer()
      await peerConnection.current!.setLocalDescription(offer)

      // Send offer via signaling server
      signalingService.sendCallRequest(peerId, offer)
      
    } catch (error) {
      console.error('Error starting call:', error)
      setCallState(prev => ({ ...prev, isConnecting: false }))
      currentPeerIdRef.current = null
      throw error
    }
  }, [initializePeerConnection, getUserMedia])

  // Answer a call (now expects remote offer)
  const answerCall = useCallback(async (fromPeerId: string, offer: RTCSessionDescriptionInit) => {
    try {
      setCallState(prev => ({ ...prev, isConnecting: true, peerId: fromPeerId }))
      currentPeerIdRef.current = fromPeerId
      
      initializePeerConnection()
      const localStream = await getUserMedia()

      // Add local stream to peer connection
      localStream.getTracks().forEach(track => {
        peerConnection.current?.addTrack(track, localStream)
      })

      // Set remote offer and create answer
      console.log('Setting remote description with offer:', offer)
      await peerConnection.current!.setRemoteDescription(new RTCSessionDescription(offer))
      const answer = await peerConnection.current!.createAnswer()
      await peerConnection.current!.setLocalDescription(answer)

      // Send answer via signaling server
      signalingService.sendCallAnswer(fromPeerId, answer)
      
    } catch (error) {
      console.error('Error answering call:', error)
      setCallState(prev => ({ ...prev, isConnecting: false }))
      currentPeerIdRef.current = null
      throw error
    }
  }, [initializePeerConnection, getUserMedia])

  // Handle incoming call answer
  const handleCallAnswer = useCallback(async (_fromPeerId: string, answer: RTCSessionDescriptionInit) => {
    try {
      if (!peerConnection.current) {
        console.error('No peer connection available')
        return
      }
      
      if (!answer || typeof answer !== 'object' || !answer.type || !answer.sdp) {
        console.error('Invalid answer format:', answer)
        return
      }

      console.log('Setting remote description with answer:', answer)
      await peerConnection.current.setRemoteDescription(new RTCSessionDescription(answer))
    } catch (error) {
      console.error('Error handling call answer:', error)
    }
  }, [])

  // Handle incoming ICE candidate
  const handleIceCandidate = useCallback(async (candidate: RTCIceCandidateInit) => {
    try {
      if (!peerConnection.current) {
        console.error('No peer connection available for ICE candidate')
        return
      }

      if (!peerConnection.current.remoteDescription) {
        console.warn('Remote description not set, queueing ICE candidate')
        // In a production app, you might want to queue these candidates
        return
      }

      if (!candidate || (!candidate.candidate && candidate.candidate !== '')) {
        console.error('Invalid ICE candidate:', candidate)
        return
      }

      console.log('Adding ICE candidate:', candidate)
      await peerConnection.current.addIceCandidate(new RTCIceCandidate(candidate))
    } catch (error) {
      console.error('Error adding ICE candidate:', error)
    }
  }, [])

  // End call
  const endCall = useCallback(() => {
    // Notify remote peer
    if (currentPeerIdRef.current) {
      signalingService.endCall(currentPeerIdRef.current)
    }

    // Stop call quality monitoring
    callQuality.stopMonitoring()
    
    // Stop all tracks
    callState.localStream?.getTracks().forEach(track => track.stop())
    
    // Stop remote audio
    if (remoteAudioRef.current) {
      remoteAudioRef.current.pause()
      remoteAudioRef.current.srcObject = null
    }
    
    // Close peer connection
    if (peerConnection.current) {
      peerConnection.current.close()
      peerConnection.current = null
    }

    // Reset refs
    currentPeerIdRef.current = null

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

  // Set up signaling service callbacks
  useEffect(() => {
    signalingService.onCallAnswered = handleCallAnswer
    signalingService.onIceCandidate = handleIceCandidate
    signalingService.onCallEnded = endCall

    return () => {
      signalingService.onCallAnswered = null
      signalingService.onIceCandidate = null
      signalingService.onCallEnded = null
    }
  }, [handleCallAnswer, handleIceCandidate, endCall])

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
    declineCall,
    handleCallAnswer,
    handleIceCandidate
  }
}