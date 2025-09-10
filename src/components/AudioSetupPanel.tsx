import React, { useState } from 'react'
import DeviceSelector from './DeviceSelector'
import MicTest from './MicTest'
import AudioSettings from './AudioSettings'

interface AudioSetupPanelProps {
  className?: string
  onDeviceChange?: (inputDevice: string, outputDevice: string) => void
  onSettingsChange?: () => void
}

const AudioSetupPanel: React.FC<AudioSetupPanelProps> = ({
  className = '',
  onDeviceChange,
  onSettingsChange
}) => {
  const [selectedInputDevice, setSelectedInputDevice] = useState('')
  const [selectedOutputDevice, setSelectedOutputDevice] = useState('')
  const [activeTab, setActiveTab] = useState<'devices' | 'test' | 'settings'>('devices')

  const handleInputDeviceChange = (deviceId: string) => {
    setSelectedInputDevice(deviceId)
    if (onDeviceChange) {
      onDeviceChange(deviceId, selectedOutputDevice)
    }
  }

  const handleOutputDeviceChange = (deviceId: string) => {
    setSelectedOutputDevice(deviceId)
    if (onDeviceChange) {
      onDeviceChange(selectedInputDevice, deviceId)
    }
  }

  const tabs = [
    { id: 'devices', name: 'Devices', icon: '🎤' },
    { id: 'test', name: 'Test', icon: '🔊' },
    { id: 'settings', name: 'Settings', icon: '⚙️' }
  ] as const

  return (
    <div className={`bg-white border border-gray-200 rounded-xl shadow-lg ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Audio Setup</h2>
        <p className="text-sm text-gray-600 mt-1">
          Configure your microphone and audio settings for the best call experience
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="px-6 pt-4">
        <nav className="flex space-x-1" aria-label="Audio setup tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-700 border border-blue-200'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="px-6 py-4">
        {activeTab === 'devices' && (
          <div className="space-y-6">
            <DeviceSelector
              onInputDeviceChange={handleInputDeviceChange}
              onOutputDeviceChange={handleOutputDeviceChange}
            />
            
            {/* Quick Setup Tips */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-blue-900 mb-2">🚀 Quick Setup Guide</h3>
              <div className="space-y-2 text-sm text-blue-800">
                <div className="flex items-start space-x-2">
                  <span className="text-blue-600 font-bold">1.</span>
                  <span>Select your preferred microphone and speakers</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-600 font-bold">2.</span>
                  <span>Test your microphone to ensure proper levels</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-600 font-bold">3.</span>
                  <span>Adjust audio settings for optimal quality</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'test' && (
          <div className="space-y-6">
            <MicTest selectedDeviceId={selectedInputDevice} />
            
            {/* Test Guidelines */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-green-900 mb-2">✅ Testing Guidelines</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-green-800">
                <div>
                  <h4 className="font-medium mb-1">Optimal Audio Levels:</h4>
                  <ul className="space-y-1 text-xs">
                    <li>• 40-80% is ideal for clear speech</li>
                    <li>• Below 20% may be too quiet</li>
                    <li>• Above 90% risks distortion</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-1">Environment Tips:</h4>
                  <ul className="space-y-1 text-xs">
                    <li>• Use a quiet room when possible</li>
                    <li>• Avoid echo-prone spaces</li>
                    <li>• Position mic 6-12 inches away</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-6">
            <AudioSettings onSettingsChange={onSettingsChange} />
            
            {/* Performance Impact Info */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-yellow-900 mb-2">⚡ Performance Impact</h3>
              <div className="text-sm text-yellow-800 space-y-1">
                <p><strong>Echo Cancellation:</strong> Minimal impact, highly recommended</p>
                <p><strong>Noise Suppression:</strong> Light CPU usage, great for noisy environments</p>
                <p><strong>Auto Gain Control:</strong> No performance impact, prevents volume fluctuations</p>
                <p><strong>Higher Sample Rates:</strong> More bandwidth usage, better quality</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer with Status */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 rounded-b-xl">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${selectedInputDevice ? 'bg-green-500' : 'bg-gray-400'}`} />
              <span className="text-gray-600">
                Microphone: {selectedInputDevice ? 'Selected' : 'None'}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${selectedOutputDevice ? 'bg-green-500' : 'bg-gray-400'}`} />
              <span className="text-gray-600">
                Speaker: {selectedOutputDevice ? 'Selected' : 'Default'}
              </span>
            </div>
          </div>
          
          <span className="text-gray-500">
            Ready for high-quality calls 🎯
          </span>
        </div>
      </div>
    </div>
  )
}

export default AudioSetupPanel