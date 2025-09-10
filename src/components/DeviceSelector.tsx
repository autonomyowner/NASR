import React, { useEffect } from 'react'
import { useDeviceSelection } from '../hooks/useDeviceSelection'

interface DeviceSelectorProps {
  onInputDeviceChange?: (deviceId: string) => void
  onOutputDeviceChange?: (deviceId: string) => void
  className?: string
}

const DeviceSelector: React.FC<DeviceSelectorProps> = ({
  onInputDeviceChange,
  onOutputDeviceChange,
  className = ''
}) => {
  const {
    audioInputDevices,
    audioOutputDevices,
    selectedInputDevice,
    selectedOutputDevice,
    setSelectedInputDevice,
    setSelectedOutputDevice,
    refreshDevices,
    hasPermissions,
    requestPermissions
  } = useDeviceSelection()

  // Notify parent components of device changes
  useEffect(() => {
    if (selectedInputDevice && onInputDeviceChange) {
      onInputDeviceChange(selectedInputDevice)
    }
  }, [selectedInputDevice, onInputDeviceChange])

  useEffect(() => {
    if (selectedOutputDevice && onOutputDeviceChange) {
      onOutputDeviceChange(selectedOutputDevice)
    }
  }, [selectedOutputDevice, onOutputDeviceChange])

  const handleInputDeviceChange = (deviceId: string) => {
    setSelectedInputDevice(deviceId)
    if (onInputDeviceChange) {
      onInputDeviceChange(deviceId)
    }
  }

  const handleOutputDeviceChange = (deviceId: string) => {
    setSelectedOutputDevice(deviceId)
    if (onOutputDeviceChange) {
      onOutputDeviceChange(deviceId)
    }
  }

  const handleRequestPermissions = async () => {
    const granted = await requestPermissions()
    if (granted) {
      await refreshDevices()
    }
  }

  if (!hasPermissions) {
    return (
      <div className={`bg-yellow-50 border border-yellow-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <svg className="w-5 h-5 text-yellow-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-yellow-800">Microphone Access Required</h4>
            <p className="text-sm text-yellow-700 mt-1">
              Allow microphone access to see available audio devices and test your setup.
            </p>
            <button
              onClick={handleRequestPermissions}
              className="mt-3 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-yellow-800 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
            >
              Grant Access
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Microphone Selection */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Microphone
          </label>
          <button
            onClick={refreshDevices}
            className="text-xs text-blue-600 hover:text-blue-800 focus:outline-none"
            title="Refresh device list"
          >
            🔄 Refresh
          </button>
        </div>
        <select
          value={selectedInputDevice}
          onChange={(e) => handleInputDeviceChange(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Select microphone...</option>
          {audioInputDevices.map((device) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label}
            </option>
          ))}
        </select>
        {audioInputDevices.length === 0 && hasPermissions && (
          <p className="text-xs text-gray-500 mt-1">
            No microphones found. Make sure a microphone is connected.
          </p>
        )}
      </div>

      {/* Speaker Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Speaker / Headphones
        </label>
        <select
          value={selectedOutputDevice}
          onChange={(e) => handleOutputDeviceChange(e.target.value)}
          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Default speaker...</option>
          {audioOutputDevices.map((device) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label}
            </option>
          ))}
        </select>
        {audioOutputDevices.length === 0 && hasPermissions && (
          <p className="text-xs text-gray-500 mt-1">
            Only default audio output available.
          </p>
        )}
      </div>

      {/* Device Info */}
      {(audioInputDevices.length > 0 || audioOutputDevices.length > 0) && (
        <div className="text-xs text-gray-500 space-y-1">
          <div>📱 {audioInputDevices.length} microphone(s) available</div>
          <div>🔊 {audioOutputDevices.length} speaker(s) available</div>
        </div>
      )}
    </div>
  )
}

export default DeviceSelector