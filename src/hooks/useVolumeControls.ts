import { useState, useCallback, useRef, useEffect } from 'react'

export interface VolumeSettings {
  remoteVolume: number      // 0-100
  localVolume: number       // 0-100
  isRemoteMuted: boolean
  isLocalMuted: boolean
  masterVolume: number      // 0-100
}

export interface UseVolumeControlsReturn {
  settings: VolumeSettings
  audioContext: AudioContext | null
  
  // Remote audio controls
  setRemoteVolume: (volume: number) => void
  toggleRemoteMute: () => void
  
  // Local audio controls (for monitoring)
  setLocalVolume: (volume: number) => void
  toggleLocalMute: () => void
  
  // Master volume
  setMasterVolume: (volume: number) => void
  
  // Quick actions
  volumeUp: (target?: 'remote' | 'local' | 'master') => void
  volumeDown: (target?: 'remote' | 'local' | 'master') => void
  muteAll: () => void
  unmuteAll: () => void
  
  // Persistence
  saveSettings: () => void
  loadSettings: () => void
  resetToDefaults: () => void
  
  // Utils
  isSupported: boolean
  getVolumeDb: (volume: number) => number
  getVolumePercentage: (db: number) => number
}

const DEFAULT_SETTINGS: VolumeSettings = {
  remoteVolume: 80,
  localVolume: 50,
  isRemoteMuted: false,
  isLocalMuted: true, // Local monitoring usually muted by default
  masterVolume: 85
}

const STORAGE_KEY = 'travoice-volume-settings'

export const useVolumeControls = (
  remoteAudioElement?: HTMLAudioElement,
  localStream?: MediaStream
): UseVolumeControlsReturn => {
  const [settings, setSettings] = useState<VolumeSettings>(DEFAULT_SETTINGS)
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null)
  
  const remoteGainRef = useRef<GainNode | null>(null)
  const localGainRef = useRef<GainNode | null>(null)
  const masterGainRef = useRef<GainNode | null>(null)

  const isSupported = typeof AudioContext !== 'undefined' || typeof (window as any).webkitAudioContext !== 'undefined'

  // Convert volume percentage to gain value (0-1)
  const volumeToGain = useCallback((volume: number): number => {
    return Math.max(0, Math.min(1, volume / 100))
  }, [])

  // Convert volume percentage to decibels
  const getVolumeDb = useCallback((volume: number): number => {
    if (volume === 0) return -Infinity
    return 20 * Math.log10(volume / 100)
  }, [])

  // Convert decibels to volume percentage
  const getVolumePercentage = useCallback((db: number): number => {
    if (db === -Infinity) return 0
    return Math.max(0, Math.min(100, Math.pow(10, db / 20) * 100))
  }, [])

  // Initialize audio context and nodes
  useEffect(() => {
    if (!isSupported) return

    const initAudioContext = async () => {
      try {
        const AudioContextClass = AudioContext || (window as any).webkitAudioContext
        const ctx = new AudioContextClass()
        
        // Create master gain node
        const masterGain = ctx.createGain()
        masterGain.connect(ctx.destination)
        masterGain.gain.value = volumeToGain(settings.masterVolume)
        masterGainRef.current = masterGain
        
        setAudioContext(ctx)
      } catch (error) {
        console.error('Failed to initialize audio context:', error)
      }
    }

    initAudioContext()

    return () => {
      if (audioContext) {
        audioContext.close()
      }
    }
  }, [isSupported]) // Only depend on isSupported, not settings

  // Set up remote audio processing
  useEffect(() => {
    if (!audioContext || !remoteAudioElement || !masterGainRef.current) return

    try {
      // Create source from audio element
      const source = audioContext.createMediaElementSource(remoteAudioElement)
      
      // Create gain node for remote audio
      const remoteGain = audioContext.createGain()
      remoteGain.gain.value = settings.isRemoteMuted ? 0 : volumeToGain(settings.remoteVolume)
      remoteGainRef.current = remoteGain
      
      // Connect: source -> remoteGain -> masterGain -> destination
      source.connect(remoteGain)
      remoteGain.connect(masterGainRef.current)
      
      return () => {
        try {
          source.disconnect()
          remoteGain.disconnect()
        } catch (e) {
          // Ignore disconnect errors
        }
      }
    } catch (error) {
      console.error('Failed to set up remote audio processing:', error)
    }
  }, [audioContext, remoteAudioElement, masterGainRef.current])

  // Set up local audio monitoring
  useEffect(() => {
    if (!audioContext || !localStream || !masterGainRef.current) return

    try {
      // Create source from local stream
      const source = audioContext.createMediaStreamSource(localStream)
      
      // Create gain node for local monitoring
      const localGain = audioContext.createGain()
      localGain.gain.value = settings.isLocalMuted ? 0 : volumeToGain(settings.localVolume)
      localGainRef.current = localGain
      
      // Connect: source -> localGain -> masterGain -> destination
      source.connect(localGain)
      localGain.connect(masterGainRef.current)
      
      return () => {
        try {
          source.disconnect()
          localGain.disconnect()
        } catch (e) {
          // Ignore disconnect errors
        }
      }
    } catch (error) {
      console.error('Failed to set up local audio monitoring:', error)
    }
  }, [audioContext, localStream, masterGainRef.current])

  // Update gain values when settings change
  useEffect(() => {
    if (remoteGainRef.current) {
      remoteGainRef.current.gain.value = settings.isRemoteMuted ? 0 : volumeToGain(settings.remoteVolume)
    }
    if (localGainRef.current) {
      localGainRef.current.gain.value = settings.isLocalMuted ? 0 : volumeToGain(settings.localVolume)
    }
    if (masterGainRef.current) {
      masterGainRef.current.gain.value = volumeToGain(settings.masterVolume)
    }

    // Also update HTML audio element volume as fallback
    if (remoteAudioElement) {
      remoteAudioElement.volume = settings.isRemoteMuted ? 0 : volumeToGain(settings.remoteVolume) * volumeToGain(settings.masterVolume)
    }
  }, [settings, remoteAudioElement, volumeToGain])

  // Set remote volume
  const setRemoteVolume = useCallback((volume: number) => {
    const clampedVolume = Math.max(0, Math.min(100, volume))
    setSettings(prev => ({ ...prev, remoteVolume: clampedVolume }))
  }, [])

  // Toggle remote mute
  const toggleRemoteMute = useCallback(() => {
    setSettings(prev => ({ ...prev, isRemoteMuted: !prev.isRemoteMuted }))
  }, [])

  // Set local volume
  const setLocalVolume = useCallback((volume: number) => {
    const clampedVolume = Math.max(0, Math.min(100, volume))
    setSettings(prev => ({ ...prev, localVolume: clampedVolume }))
  }, [])

  // Toggle local mute
  const toggleLocalMute = useCallback(() => {
    setSettings(prev => ({ ...prev, isLocalMuted: !prev.isLocalMuted }))
  }, [])

  // Set master volume
  const setMasterVolume = useCallback((volume: number) => {
    const clampedVolume = Math.max(0, Math.min(100, volume))
    setSettings(prev => ({ ...prev, masterVolume: clampedVolume }))
  }, [])

  // Volume up
  const volumeUp = useCallback((target: 'remote' | 'local' | 'master' = 'remote') => {
    const increment = 10
    switch (target) {
      case 'remote':
        setRemoteVolume(settings.remoteVolume + increment)
        break
      case 'local':
        setLocalVolume(settings.localVolume + increment)
        break
      case 'master':
        setMasterVolume(settings.masterVolume + increment)
        break
    }
  }, [settings, setRemoteVolume, setLocalVolume, setMasterVolume])

  // Volume down
  const volumeDown = useCallback((target: 'remote' | 'local' | 'master' = 'remote') => {
    const decrement = 10
    switch (target) {
      case 'remote':
        setRemoteVolume(settings.remoteVolume - decrement)
        break
      case 'local':
        setLocalVolume(settings.localVolume - decrement)
        break
      case 'master':
        setMasterVolume(settings.masterVolume - decrement)
        break
    }
  }, [settings, setRemoteVolume, setLocalVolume, setMasterVolume])

  // Mute all
  const muteAll = useCallback(() => {
    setSettings(prev => ({
      ...prev,
      isRemoteMuted: true,
      isLocalMuted: true
    }))
  }, [])

  // Unmute all
  const unmuteAll = useCallback(() => {
    setSettings(prev => ({
      ...prev,
      isRemoteMuted: false,
      isLocalMuted: false
    }))
  }, [])

  // Save settings to localStorage
  const saveSettings = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save volume settings:', error)
    }
  }, [settings])

  // Load settings from localStorage
  const loadSettings = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsedSettings = JSON.parse(saved)
        setSettings({ ...DEFAULT_SETTINGS, ...parsedSettings })
      }
    } catch (error) {
      console.error('Failed to load volume settings:', error)
      setSettings(DEFAULT_SETTINGS)
    }
  }, [])

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULT_SETTINGS)
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (error) {
      console.error('Failed to clear volume settings:', error)
    }
  }, [])

  // Auto-save settings when they change
  useEffect(() => {
    saveSettings()
  }, [saveSettings])

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  return {
    settings,
    audioContext,
    
    setRemoteVolume,
    toggleRemoteMute,
    setLocalVolume,
    toggleLocalMute,
    setMasterVolume,
    
    volumeUp,
    volumeDown,
    muteAll,
    unmuteAll,
    
    saveSettings,
    loadSettings,
    resetToDefaults,
    
    isSupported,
    getVolumeDb,
    getVolumePercentage
  }
}