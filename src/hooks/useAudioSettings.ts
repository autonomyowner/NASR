import { useState, useEffect, useCallback } from 'react'

interface AudioConstraints {
  echoCancellation: boolean
  noiseSuppression: boolean
  autoGainControl: boolean
  sampleRate?: number
  channelCount?: number
}

interface AudioSettings {
  constraints: AudioConstraints
  deviceId: string | null
}

interface AudioSettingsHook {
  settings: AudioSettings
  updateConstraint: <K extends keyof AudioConstraints>(key: K, value: AudioConstraints[K]) => void
  updateDeviceId: (deviceId: string) => void
  resetToDefaults: () => void
  createMediaStream: () => Promise<MediaStream>
  getOptimalConstraints: () => MediaStreamConstraints
}

const defaultConstraints: AudioConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  sampleRate: 48000,
  channelCount: 1
}

export const useAudioSettings = (): AudioSettingsHook => {
  const [settings, setSettings] = useState<AudioSettings>({
    constraints: { ...defaultConstraints },
    deviceId: null
  })

  // Load settings from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('travoice-audio-settings')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setSettings(prev => ({
          ...prev,
          constraints: { ...defaultConstraints, ...parsed.constraints },
          deviceId: parsed.deviceId || null
        }))
      } catch (error) {
        console.warn('Failed to parse saved audio settings:', error)
      }
    }
  }, [])

  // Save settings to localStorage
  const saveSettings = useCallback((newSettings: AudioSettings) => {
    localStorage.setItem('travoice-audio-settings', JSON.stringify(newSettings))
  }, [])

  // Update a specific constraint
  const updateConstraint = useCallback(<K extends keyof AudioConstraints>(
    key: K, 
    value: AudioConstraints[K]
  ) => {
    setSettings(prev => {
      const newSettings = {
        ...prev,
        constraints: {
          ...prev.constraints,
          [key]: value
        }
      }
      saveSettings(newSettings)
      return newSettings
    })
  }, [saveSettings])

  // Update device ID
  const updateDeviceId = useCallback((deviceId: string) => {
    setSettings(prev => {
      const newSettings = {
        ...prev,
        deviceId
      }
      saveSettings(newSettings)
      return newSettings
    })
  }, [saveSettings])

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    const defaultSettings: AudioSettings = {
      constraints: { ...defaultConstraints },
      deviceId: null
    }
    setSettings(defaultSettings)
    saveSettings(defaultSettings)
  }, [saveSettings])

  // Get optimal constraints based on current settings
  const getOptimalConstraints = useCallback((): MediaStreamConstraints => {
    const audioConstraints: MediaTrackConstraints = {
      ...settings.constraints
    }

    // Add device ID if specified
    if (settings.deviceId) {
      audioConstraints.deviceId = { exact: settings.deviceId }
    }

    // Add optional constraints that improve quality
    if (settings.constraints.sampleRate) {
      audioConstraints.sampleRate = { ideal: settings.constraints.sampleRate }
    }

    if (settings.constraints.channelCount) {
      audioConstraints.channelCount = { ideal: settings.constraints.channelCount }
    }

    // Note: latency is controlled by the audio context, not constraints

    return {
      audio: audioConstraints,
      video: false
    }
  }, [settings])

  // Create media stream with current settings
  const createMediaStream = useCallback(async (): Promise<MediaStream> => {
    try {
      const constraints = getOptimalConstraints()
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      
      // Log the actual settings applied
      const track = stream.getAudioTracks()[0]
      if (track) {
        const actualSettings = track.getSettings()
        console.log('Actual audio settings applied:', actualSettings)
      }
      
      return stream
    } catch (error: any) {
      console.error('Failed to create media stream:', error)
      
      // Try with fallback constraints if the specific device fails
      if (error.name === 'OverconstrainedError' && settings.deviceId) {
        console.warn('Device-specific constraints failed, trying without device ID')
        
        const fallbackConstraints = getOptimalConstraints()
        delete (fallbackConstraints.audio as MediaTrackConstraints).deviceId
        
        try {
          return await navigator.mediaDevices.getUserMedia(fallbackConstraints)
        } catch (fallbackError) {
          console.error('Fallback constraints also failed:', fallbackError)
          throw fallbackError
        }
      }
      
      throw error
    }
  }, [getOptimalConstraints, settings.deviceId])

  return {
    settings,
    updateConstraint,
    updateDeviceId,
    resetToDefaults,
    createMediaStream,
    getOptimalConstraints
  }
}