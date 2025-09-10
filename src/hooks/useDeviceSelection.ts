import { useState, useEffect, useCallback } from 'react'

interface AudioDevice {
  deviceId: string
  label: string
  kind: 'audioinput' | 'audiooutput'
}

interface DeviceSelectionHook {
  audioInputDevices: AudioDevice[]
  audioOutputDevices: AudioDevice[]
  selectedInputDevice: string
  selectedOutputDevice: string
  setSelectedInputDevice: (deviceId: string) => void
  setSelectedOutputDevice: (deviceId: string) => void
  refreshDevices: () => Promise<void>
  hasPermissions: boolean
  requestPermissions: () => Promise<boolean>
}

export const useDeviceSelection = (): DeviceSelectionHook => {
  const [audioInputDevices, setAudioInputDevices] = useState<AudioDevice[]>([])
  const [audioOutputDevices, setAudioOutputDevices] = useState<AudioDevice[]>([])
  const [selectedInputDevice, setSelectedInputDevice] = useState('')
  const [selectedOutputDevice, setSelectedOutputDevice] = useState('')
  const [hasPermissions, setHasPermissions] = useState(false)

  // Load saved device preferences from localStorage
  useEffect(() => {
    const savedInputDevice = localStorage.getItem('travoice-audio-input-device')
    const savedOutputDevice = localStorage.getItem('travoice-audio-output-device')
    
    if (savedInputDevice) setSelectedInputDevice(savedInputDevice)
    if (savedOutputDevice) setSelectedOutputDevice(savedOutputDevice)
  }, [])

  // Save device preferences to localStorage
  const saveSelectedInputDevice = useCallback((deviceId: string) => {
    setSelectedInputDevice(deviceId)
    localStorage.setItem('travoice-audio-input-device', deviceId)
  }, [])

  const saveSelectedOutputDevice = useCallback((deviceId: string) => {
    setSelectedOutputDevice(deviceId)
    localStorage.setItem('travoice-audio-output-device', deviceId)
  }, [])

  // Request microphone permissions
  const requestPermissions = useCallback(async (): Promise<boolean> => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return false
      }

      // Request temporary access to get device labels
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Stop the tracks immediately - we just needed permission
      stream.getTracks().forEach(track => track.stop())
      
      setHasPermissions(true)
      return true
    } catch (error) {
      console.error('Failed to get microphone permissions:', error)
      setHasPermissions(false)
      return false
    }
  }, [])

  // Enumerate audio devices
  const refreshDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.warn('Device enumeration not supported')
        return
      }

      const devices = await navigator.mediaDevices.enumerateDevices()
      
      const inputs: AudioDevice[] = []
      const outputs: AudioDevice[] = []

      devices.forEach(device => {
        if (device.kind === 'audioinput') {
          inputs.push({
            deviceId: device.deviceId,
            label: device.label || `Microphone ${inputs.length + 1}`,
            kind: 'audioinput'
          })
        } else if (device.kind === 'audiooutput') {
          outputs.push({
            deviceId: device.deviceId,
            label: device.label || `Speaker ${outputs.length + 1}`,
            kind: 'audiooutput'
          })
        }
      })

      setAudioInputDevices(inputs)
      setAudioOutputDevices(outputs)

      // Set default devices if none selected
      if (!selectedInputDevice && inputs.length > 0) {
        setSelectedInputDevice(inputs[0].deviceId)
      }
      if (!selectedOutputDevice && outputs.length > 0) {
        setSelectedOutputDevice(outputs[0].deviceId)
      }

    } catch (error) {
      console.error('Failed to enumerate devices:', error)
    }
  }, [selectedInputDevice, selectedOutputDevice])

  // Check permissions on mount and refresh devices
  useEffect(() => {
    const checkPermissions = async () => {
      if (navigator.permissions) {
        try {
          const micPermission = await navigator.permissions.query({ name: 'microphone' as PermissionName })
          if (micPermission.state === 'granted') {
            setHasPermissions(true)
            await refreshDevices()
          }
        } catch (error) {
          console.warn('Could not check microphone permissions:', error)
        }
      }
    }

    checkPermissions()
  }, [refreshDevices])

  // Listen for device changes
  useEffect(() => {
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener('devicechange', refreshDevices)
      
      return () => {
        navigator.mediaDevices.removeEventListener('devicechange', refreshDevices)
      }
    }
  }, [refreshDevices])

  return {
    audioInputDevices,
    audioOutputDevices,
    selectedInputDevice,
    selectedOutputDevice,
    setSelectedInputDevice: saveSelectedInputDevice,
    setSelectedOutputDevice: saveSelectedOutputDevice,
    refreshDevices,
    hasPermissions,
    requestPermissions
  }
}