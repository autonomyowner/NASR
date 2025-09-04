import { useState, useEffect, useRef, useCallback } from 'react'

export interface CallQualityMetrics {
  connectionState: string
  iceConnectionState: string
  audioLevel: number
  packetsLost: number
  packetsReceived: number
  jitter: number
  rtt: number // Round trip time
  bitrate: number
  networkType: string
  signalStrength: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown'
}

interface CallQualityHook {
  metrics: CallQualityMetrics
  isMonitoring: boolean
  startMonitoring: (peerConnection: RTCPeerConnection) => void
  stopMonitoring: () => void
  getQualityScore: () => number // 0-100 score
  getQualityText: () => string
}

export const useCallQuality = (): CallQualityHook => {
  const [metrics, setMetrics] = useState<CallQualityMetrics>({
    connectionState: 'new',
    iceConnectionState: 'new',
    audioLevel: 0,
    packetsLost: 0,
    packetsReceived: 0,
    jitter: 0,
    rtt: 0,
    bitrate: 0,
    networkType: 'unknown',
    signalStrength: 'unknown'
  })

  const [isMonitoring, setIsMonitoring] = useState(false)
  const intervalRef = useRef<number | null>(null)
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)

  // Get network information
  const getNetworkInfo = useCallback(() => {
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection
    if (connection) {
      return {
        networkType: connection.effectiveType || 'unknown',
        downlink: connection.downlink || 0,
        rtt: connection.rtt || 0
      }
    }
    return { networkType: 'unknown', downlink: 0, rtt: 0 }
  }, [])

  // Monitor audio levels
  const setupAudioLevelMonitoring = useCallback((stream: MediaStream) => {
    try {
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      
      analyserRef.current.fftSize = 256
    } catch (error) {
      console.warn('Could not set up audio level monitoring:', error)
    }
  }, [])

  // Get current audio level
  const getAudioLevel = useCallback((): number => {
    if (!analyserRef.current) return 0

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)
    
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length
    return Math.round((average / 255) * 100)
  }, [])

  // Get WebRTC statistics
  const getWebRTCStats = useCallback(async (peerConnection: RTCPeerConnection) => {
    try {
      const stats = await peerConnection.getStats()
      let packetsLost = 0
      let packetsReceived = 0
      let jitter = 0
      let rtt = 0
      let bitrate = 0

      stats.forEach((report) => {
        if (report.type === 'inbound-rtp' && report.mediaType === 'audio') {
          packetsLost += report.packetsLost || 0
          packetsReceived += report.packetsReceived || 0
          jitter = report.jitter || 0
        }
        
        if (report.type === 'remote-inbound-rtp' && report.mediaType === 'audio') {
          rtt = report.roundTripTime || 0
        }

        if (report.type === 'candidate-pair' && report.state === 'succeeded') {
          bitrate = Math.round((report.availableOutgoingBitrate || 0) / 1000) // Convert to kbps
        }
      })

      return { packetsLost, packetsReceived, jitter, rtt, bitrate }
    } catch (error) {
      console.warn('Could not get WebRTC stats:', error)
      return { packetsLost: 0, packetsReceived: 0, jitter: 0, rtt: 0, bitrate: 0 }
    }
  }, [])

  // Calculate signal strength based on metrics
  const calculateSignalStrength = useCallback((metrics: CallQualityMetrics): CallQualityMetrics['signalStrength'] => {
    const { packetsLost, packetsReceived, jitter, rtt } = metrics
    
    let score = 100
    
    // Packet loss penalty (most important)
    if (packetsReceived > 0) {
      const lossRate = (packetsLost / (packetsLost + packetsReceived)) * 100
      if (lossRate > 5) score -= 40
      else if (lossRate > 2) score -= 20
      else if (lossRate > 1) score -= 10
    }
    
    // Jitter penalty
    if (jitter > 0.1) score -= 20
    else if (jitter > 0.05) score -= 10
    
    // RTT penalty
    if (rtt > 0.3) score -= 20
    else if (rtt > 0.15) score -= 10
    
    if (score >= 80) return 'excellent'
    if (score >= 60) return 'good'
    if (score >= 40) return 'fair'
    if (score >= 20) return 'poor'
    return 'poor'
  }, [])

  // Start monitoring
  const startMonitoring = useCallback((peerConnection: RTCPeerConnection) => {
    peerConnectionRef.current = peerConnection
    setIsMonitoring(true)

    // Set up audio level monitoring if we have a local stream
    peerConnection.getSenders().forEach(sender => {
      if (sender.track?.kind === 'audio') {
        const stream = new MediaStream([sender.track])
        setupAudioLevelMonitoring(stream)
      }
    })

    // Monitor connection states
    const updateConnectionState = () => {
      setMetrics(prev => ({
        ...prev,
        connectionState: peerConnection.connectionState,
        iceConnectionState: peerConnection.iceConnectionState
      }))
    }

    peerConnection.addEventListener('connectionstatechange', updateConnectionState)
    peerConnection.addEventListener('iceconnectionstatechange', updateConnectionState)

    // Start periodic monitoring
    intervalRef.current = window.setInterval(async () => {
      const networkInfo = getNetworkInfo()
      const webrtcStats = await getWebRTCStats(peerConnection)
      const audioLevel = getAudioLevel()
      
      const newMetrics: CallQualityMetrics = {
        connectionState: peerConnection.connectionState,
        iceConnectionState: peerConnection.iceConnectionState,
        audioLevel,
        packetsLost: webrtcStats.packetsLost,
        packetsReceived: webrtcStats.packetsReceived,
        jitter: webrtcStats.jitter,
        rtt: Math.max(webrtcStats.rtt * 1000, networkInfo.rtt), // Convert to ms
        bitrate: webrtcStats.bitrate,
        networkType: networkInfo.networkType,
        signalStrength: 'unknown'
      }
      
      // Calculate signal strength
      newMetrics.signalStrength = calculateSignalStrength(newMetrics)
      
      setMetrics(newMetrics)
    }, 1000) // Update every second

    // Initial update
    updateConnectionState()
  }, [getNetworkInfo, getWebRTCStats, getAudioLevel, setupAudioLevelMonitoring, calculateSignalStrength])

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    setIsMonitoring(false)
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    peerConnectionRef.current = null
    analyserRef.current = null

    // Reset metrics
    setMetrics({
      connectionState: 'new',
      iceConnectionState: 'new',
      audioLevel: 0,
      packetsLost: 0,
      packetsReceived: 0,
      jitter: 0,
      rtt: 0,
      bitrate: 0,
      networkType: 'unknown',
      signalStrength: 'unknown'
    })
  }, [])

  // Calculate quality score (0-100)
  const getQualityScore = useCallback((): number => {
    const { signalStrength } = metrics
    
    switch (signalStrength) {
      case 'excellent': return 95
      case 'good': return 75
      case 'fair': return 50
      case 'poor': return 25
      default: return 0
    }
  }, [metrics.signalStrength])

  // Get quality text
  const getQualityText = useCallback((): string => {
    const { signalStrength } = metrics
    
    const qualityTexts = {
      excellent: 'Excellent',
      good: 'Good',
      fair: 'Fair',
      poor: 'Poor',
      unknown: 'Connecting...'
    }
    
    return qualityTexts[signalStrength]
  }, [metrics.signalStrength])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring()
    }
  }, [stopMonitoring])

  return {
    metrics,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    getQualityScore,
    getQualityText
  }
}