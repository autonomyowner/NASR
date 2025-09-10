import { useState, useCallback, useRef, useEffect } from 'react'

export interface WebRTCStats {
  timestamp: number
  
  // Connection stats
  connectionState: RTCPeerConnectionState
  iceConnectionState: RTCIceConnectionState
  iceGatheringState: RTCIceGatheringState
  signalingState: RTCSignalingState
  
  // Audio stats
  audioCodec?: string
  audioSampleRate?: number
  audioChannels?: number
  audioBitrate?: number
  audioPacketsLost?: number
  audioPacketsSent?: number
  audioPacketsReceived?: number
  audioJitterBufferDelay?: number
  audioRoundTripTime?: number
  audioTotalAudioEnergy?: number
  audioJitter?: number
  
  // Network stats
  bytesSent?: number
  bytesReceived?: number
  packetsLost?: number
  packetsLostPercent?: number
  availableOutgoingBitrate?: number
  availableIncomingBitrate?: number
  currentRoundTripTime?: number
  
  // Quality metrics
  concealedSamples?: number
  concealmentEvents?: number
  insertedSamplesForDeceleration?: number
  removedSamplesForAcceleration?: number
  silentConcealedSamples?: number
  
  // ICE candidates
  localCandidateType?: string
  remoteCandidateType?: string
  localNetworkType?: string
  remoteNetworkType?: string
  
  // Browser and platform info
  userAgent: string
  platform: string
}

export interface WebRTCStatsHistory {
  stats: WebRTCStats[]
  maxEntries: number
  startTime: number
}

export interface UseWebRTCStatsReturn {
  currentStats: WebRTCStats | null
  statsHistory: WebRTCStats[]
  isCollecting: boolean
  error: string | null
  
  // Actions
  startCollecting: () => void
  stopCollecting: () => void
  clearHistory: () => void
  exportStats: (format?: 'json' | 'csv') => void
  
  // Configuration
  setCollectionInterval: (ms: number) => void
  setMaxEntries: (count: number) => void
  
  // Utils
  getAverageStats: (field: keyof WebRTCStats, minutes?: number) => number | null
  getStatsAtTime: (timestamp: number) => WebRTCStats | null
  isSupported: boolean
}

const DEFAULT_INTERVAL = 1000 // 1 second
const DEFAULT_MAX_ENTRIES = 300 // 5 minutes at 1Hz

export const useWebRTCStats = (
  peerConnection?: RTCPeerConnection
): UseWebRTCStatsReturn => {
  const [currentStats, setCurrentStats] = useState<WebRTCStats | null>(null)
  const [statsHistory, setStatsHistory] = useState<WebRTCStats[]>([])
  const [isCollecting, setIsCollecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [collectionInterval, setCollectionIntervalState] = useState(DEFAULT_INTERVAL)
  const [maxEntries, setMaxEntriesState] = useState(DEFAULT_MAX_ENTRIES)
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const previousStatsRef = useRef<RTCStatsReport | null>(null)

  const isSupported = typeof RTCPeerConnection !== 'undefined' && 
                     'getStats' in RTCPeerConnection.prototype

  // Parse stats report into our format
  const parseStatsReport = useCallback(async (peerConn: RTCPeerConnection): Promise<WebRTCStats | null> => {
    try {
      const stats = await peerConn.getStats()
      const parsedStats: Partial<WebRTCStats> = {
        timestamp: Date.now(),
        connectionState: peerConn.connectionState,
        iceConnectionState: peerConn.iceConnectionState,
        iceGatheringState: peerConn.iceGatheringState,
        signalingState: peerConn.signalingState,
        userAgent: navigator.userAgent,
        platform: navigator.platform
      }

      // Parse individual stat reports
      for (const report of stats.values()) {
        switch (report.type) {
          case 'inbound-rtp':
            if (report.mediaType === 'audio') {
              parsedStats.audioPacketsReceived = report.packetsReceived
              parsedStats.audioPacketsLost = report.packetsLost
              parsedStats.audioJitter = report.jitter
              parsedStats.audioJitterBufferDelay = report.jitterBufferDelay
              parsedStats.audioTotalAudioEnergy = report.totalAudioEnergy
              parsedStats.concealedSamples = report.concealedSamples
              parsedStats.concealmentEvents = report.concealmentEvents
              parsedStats.insertedSamplesForDeceleration = report.insertedSamplesForDeceleration
              parsedStats.removedSamplesForAcceleration = report.removedSamplesForAcceleration
              parsedStats.silentConcealedSamples = report.silentConcealedSamples
              
              // Calculate packet loss percentage
              if (report.packetsReceived && report.packetsLost) {
                const total = report.packetsReceived + report.packetsLost
                parsedStats.packetsLostPercent = (report.packetsLost / total) * 100
              }
            }
            parsedStats.bytesReceived = (parsedStats.bytesReceived || 0) + (report.bytesReceived || 0)
            break

          case 'outbound-rtp':
            if (report.mediaType === 'audio') {
              parsedStats.audioPacketsSent = report.packetsSent
              
              // Calculate bitrate from bytes sent
              if (previousStatsRef.current) {
                const previousReport = Array.from(previousStatsRef.current.values())
                  .find(r => r.type === 'outbound-rtp' && r.id === report.id)
                if (previousReport && report.bytesSent && previousReport.bytesSent) {
                  const timeDiff = (report.timestamp - previousReport.timestamp) / 1000
                  const bytesDiff = report.bytesSent - previousReport.bytesSent
                  parsedStats.audioBitrate = Math.round((bytesDiff * 8) / timeDiff)
                }
              }
            }
            parsedStats.bytesSent = (parsedStats.bytesSent || 0) + (report.bytesSent || 0)
            break

          case 'remote-inbound-rtp':
            if (report.mediaType === 'audio') {
              parsedStats.audioRoundTripTime = report.roundTripTime
              parsedStats.currentRoundTripTime = report.roundTripTime
            }
            break

          case 'media-source':
            if (report.kind === 'audio') {
              parsedStats.audioSampleRate = report.audioLevel
            }
            break

          case 'codec':
            if (report.mimeType?.includes('audio')) {
              parsedStats.audioCodec = report.mimeType.split('/')[1]
              parsedStats.audioChannels = report.channels
              parsedStats.audioSampleRate = report.clockRate
            }
            break

          case 'candidate-pair':
            if (report.state === 'succeeded') {
              parsedStats.availableOutgoingBitrate = report.availableOutgoingBitrate
              parsedStats.availableIncomingBitrate = report.availableIncomingBitrate
              parsedStats.currentRoundTripTime = report.currentRoundTripTime
            }
            break

          case 'local-candidate':
            if (report.candidateType) {
              parsedStats.localCandidateType = report.candidateType
              parsedStats.localNetworkType = report.networkType
            }
            break

          case 'remote-candidate':
            if (report.candidateType) {
              parsedStats.remoteCandidateType = report.candidateType
              parsedStats.remoteNetworkType = report.networkType
            }
            break
        }
      }

      previousStatsRef.current = stats
      return parsedStats as WebRTCStats
    } catch (err) {
      console.error('Failed to parse WebRTC stats:', err)
      throw err
    }
  }, [])

  // Collect stats
  const collectStats = useCallback(async () => {
    if (!peerConnection || !isSupported) return

    try {
      const stats = await parseStatsReport(peerConnection)
      if (stats) {
        setCurrentStats(stats)
        setStatsHistory(prev => {
          const newHistory = [...prev, stats]
          if (newHistory.length > maxEntries) {
            return newHistory.slice(-maxEntries)
          }
          return newHistory
        })
      }
      setError(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to collect stats'
      setError(errorMessage)
    }
  }, [peerConnection, isSupported, parseStatsReport, maxEntries])

  // Start collecting stats
  const startCollecting = useCallback(() => {
    if (!peerConnection || !isSupported || isCollecting) return

    setIsCollecting(true)
    setError(null)
    
    // Collect immediately
    collectStats()
    
    // Set up interval
    intervalRef.current = setInterval(collectStats, collectionInterval)
  }, [peerConnection, isSupported, isCollecting, collectStats, collectionInterval])

  // Stop collecting stats
  const stopCollecting = useCallback(() => {
    setIsCollecting(false)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Clear stats history
  const clearHistory = useCallback(() => {
    setStatsHistory([])
    setCurrentStats(null)
    previousStatsRef.current = null
  }, [])

  // Export stats
  const exportStats = useCallback((format: 'json' | 'csv' = 'json') => {
    if (statsHistory.length === 0) return

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `webrtc-stats-${timestamp}.${format}`

    if (format === 'json') {
      const data = {
        exportDate: new Date().toISOString(),
        totalEntries: statsHistory.length,
        collectionInterval,
        stats: statsHistory
      }
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } else if (format === 'csv') {
      if (statsHistory.length === 0) return

      const headers = Object.keys(statsHistory[0])
      const csvContent = [
        headers.join(','),
        ...statsHistory.map(stat => 
          headers.map(header => {
            const value = (stat as any)[header]
            return typeof value === 'string' && value.includes(',') 
              ? `"${value}"` 
              : value ?? ''
          }).join(',')
        )
      ].join('\n')

      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }, [statsHistory, collectionInterval])

  // Set collection interval
  const setCollectionInterval = useCallback((ms: number) => {
    setCollectionIntervalState(Math.max(100, ms)) // Minimum 100ms
    
    if (isCollecting) {
      stopCollecting()
      // Restart with new interval (will be picked up by the effect)
    }
  }, [isCollecting, stopCollecting])

  // Set max entries
  const setMaxEntries = useCallback((count: number) => {
    const newMaxEntries = Math.max(10, count) // Minimum 10 entries
    setMaxEntriesState(newMaxEntries)
    
    // Trim existing history if needed
    setStatsHistory(prev => {
      if (prev.length > newMaxEntries) {
        return prev.slice(-newMaxEntries)
      }
      return prev
    })
  }, [])

  // Get average stats for a field over time
  const getAverageStats = useCallback((
    field: keyof WebRTCStats, 
    minutes: number = 1
  ): number | null => {
    if (statsHistory.length === 0) return null

    const cutoffTime = Date.now() - (minutes * 60 * 1000)
    const recentStats = statsHistory.filter(stat => stat.timestamp >= cutoffTime)
    
    if (recentStats.length === 0) return null

    const values = recentStats
      .map(stat => (stat as any)[field])
      .filter(value => typeof value === 'number')

    if (values.length === 0) return null

    return values.reduce((sum, value) => sum + value, 0) / values.length
  }, [statsHistory])

  // Get stats at specific time
  const getStatsAtTime = useCallback((timestamp: number): WebRTCStats | null => {
    return statsHistory.find(stat => 
      Math.abs(stat.timestamp - timestamp) < collectionInterval
    ) || null
  }, [statsHistory, collectionInterval])

  // Restart collecting when interval changes
  useEffect(() => {
    if (isCollecting) {
      stopCollecting()
      setTimeout(startCollecting, 100)
    }
  }, [collectionInterval]) // Only depend on collectionInterval

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  return {
    currentStats,
    statsHistory,
    isCollecting,
    error,
    
    startCollecting,
    stopCollecting,
    clearHistory,
    exportStats,
    
    setCollectionInterval,
    setMaxEntries,
    
    getAverageStats,
    getStatsAtTime,
    isSupported
  }
}