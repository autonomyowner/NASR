import { useState, useEffect, useRef, useCallback } from 'react'

interface MicTestHook {
  isTestActive: boolean
  audioLevel: number
  isClipping: boolean
  canPlayback: boolean
  isPlaybackActive: boolean
  startTest: (deviceId?: string) => Promise<void>
  stopTest: () => void
  togglePlayback: () => void
  error: string | null
}

export const useMicTest = (): MicTestHook => {
  const [isTestActive, setIsTestActive] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [isClipping, setIsClipping] = useState(false)
  const [canPlayback, setCanPlayback] = useState(false)
  const [isPlaybackActive, setIsPlaybackActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const playbackGainRef = useRef<GainNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const clippingTimeoutRef = useRef<number | null>(null)

  // Cleanup function
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    if (clippingTimeoutRef.current) {
      clearTimeout(clippingTimeoutRef.current)
      clippingTimeoutRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    micSourceRef.current = null
    analyserRef.current = null
    playbackGainRef.current = null

    setIsTestActive(false)
    setAudioLevel(0)
    setIsClipping(false)
    setIsPlaybackActive(false)
    setCanPlayback(false)
    setError(null)
  }, [])

  // Audio level monitoring
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current) return

    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate RMS level
    let sum = 0
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i] * dataArray[i]
    }
    const rms = Math.sqrt(sum / bufferLength)
    const level = Math.min(100, (rms / 128) * 100) // Normalize to 0-100

    setAudioLevel(level)

    // Detect clipping (threshold at 90% to give some headroom)
    const isCurrentlyClipping = level > 90
    if (isCurrentlyClipping && !isClipping) {
      setIsClipping(true)
      // Clear clipping indicator after 500ms
      if (clippingTimeoutRef.current) {
        clearTimeout(clippingTimeoutRef.current)
      }
      clippingTimeoutRef.current = window.setTimeout(() => {
        setIsClipping(false)
      }, 500)
    }

    animationFrameRef.current = requestAnimationFrame(monitorAudioLevel)
  }, [isClipping])

  // Start mic test
  const startTest = useCallback(async (deviceId?: string) => {
    try {
      setError(null)
      
      // Stop any existing test first
      cleanup()

      const constraints: MediaStreamConstraints = {
        audio: {
          deviceId: deviceId ? { exact: deviceId } : undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      // Create audio context and nodes
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      await audioContextRef.current.resume()

      // Create nodes
      micSourceRef.current = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      playbackGainRef.current = audioContextRef.current.createGain()

      // Configure analyser
      analyserRef.current.fftSize = 2048
      analyserRef.current.smoothingTimeConstant = 0.8

      // Set up audio graph: mic -> analyser -> gain -> destination (for playback)
      micSourceRef.current.connect(analyserRef.current)
      analyserRef.current.connect(playbackGainRef.current)
      
      // Initially mute playback to prevent feedback
      playbackGainRef.current.gain.setValueAtTime(0, audioContextRef.current.currentTime)

      setIsTestActive(true)
      setCanPlayback(true)
      
      // Start monitoring
      monitorAudioLevel()

    } catch (error: any) {
      console.error('Failed to start mic test:', error)
      
      let errorMessage = 'Failed to start microphone test'
      if (error.name === 'NotFoundError') {
        errorMessage = 'Microphone not found'
      } else if (error.name === 'NotAllowedError') {
        errorMessage = 'Microphone access denied'
      } else if (error.name === 'OverconstrainedError') {
        errorMessage = 'Microphone constraints not supported'
      }
      
      setError(errorMessage)
      cleanup()
    }
  }, [cleanup, monitorAudioLevel])

  // Stop mic test
  const stopTest = useCallback(() => {
    cleanup()
  }, [cleanup])

  // Toggle playback (local echo for testing)
  const togglePlayback = useCallback(() => {
    if (!playbackGainRef.current || !audioContextRef.current) return

    try {
      if (isPlaybackActive) {
        // Mute playback
        playbackGainRef.current.disconnect()
        playbackGainRef.current.gain.setValueAtTime(0, audioContextRef.current.currentTime)
        setIsPlaybackActive(false)
      } else {
        // Enable playback (with low volume to prevent feedback)
        playbackGainRef.current.connect(audioContextRef.current.destination)
        playbackGainRef.current.gain.setValueAtTime(0.3, audioContextRef.current.currentTime)
        setIsPlaybackActive(true)
      }
    } catch (error) {
      console.error('Failed to toggle playback:', error)
      setError('Failed to toggle playback')
    }
  }, [isPlaybackActive])

  // Cleanup on unmount
  useEffect(() => {
    return cleanup
  }, [cleanup])

  return {
    isTestActive,
    audioLevel,
    isClipping,
    canPlayback,
    isPlaybackActive,
    startTest,
    stopTest,
    togglePlayback,
    error
  }
}