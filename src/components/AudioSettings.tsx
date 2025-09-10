import React, { useState } from 'react'
import { useAudioSettings } from '../hooks/useAudioSettings'

interface AudioSettingsProps {
  className?: string
  onSettingsChange?: () => void
}

const AudioSettings: React.FC<AudioSettingsProps> = ({
  className = '',
  onSettingsChange
}) => {
  const {
    settings,
    updateConstraint,
    resetToDefaults,
    getOptimalConstraints
  } = useAudioSettings()

  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleConstraintChange = (key: keyof typeof settings.constraints, value: boolean | number) => {
    updateConstraint(key, value)
    if (onSettingsChange) {
      onSettingsChange()
    }
  }

  const handleReset = () => {
    resetToDefaults()
    if (onSettingsChange) {
      onSettingsChange()
    }
  }

  const getConstraintDescription = (key: string) => {
    const descriptions = {
      echoCancellation: 'Removes audio feedback and echo from speakers',
      noiseSuppression: 'Reduces background noise and ambient sounds',
      autoGainControl: 'Automatically adjusts microphone volume',
      sampleRate: 'Audio sample rate in Hz (higher = better quality)',
      channelCount: 'Number of audio channels (1 = mono, 2 = stereo)'
    }
    return descriptions[key as keyof typeof descriptions] || ''
  }

  const getQualityLevel = () => {
    const { constraints } = settings
    let score = 0
    
    if (constraints.echoCancellation) score += 20
    if (constraints.noiseSuppression) score += 20
    if (constraints.autoGainControl) score += 15
    if (constraints.sampleRate && constraints.sampleRate >= 48000) score += 25
    else if (constraints.sampleRate && constraints.sampleRate >= 44100) score += 20
    
    if (score >= 80) return { level: 'High', color: 'text-green-600', bgColor: 'bg-green-50' }
    if (score >= 60) return { level: 'Medium', color: 'text-yellow-600', bgColor: 'bg-yellow-50' }
    return { level: 'Basic', color: 'text-gray-600', bgColor: 'bg-gray-50' }
  }

  const quality = getQualityLevel()

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">Audio Settings</h3>
        <div className="flex items-center space-x-2">
          <div className={`px-2 py-1 rounded-full text-xs font-medium ${quality.color} ${quality.bgColor}`}>
            {quality.level} Quality
          </div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced
          </button>
        </div>
      </div>

      {/* Essential Settings */}
      <div className="space-y-4">
        {/* Echo Cancellation */}
        <div className="flex items-start space-x-3">
          <div className="flex items-center h-5">
            <input
              id="echoCancellation"
              type="checkbox"
              checked={settings.constraints.echoCancellation}
              onChange={(e) => handleConstraintChange('echoCancellation', e.target.checked)}
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label htmlFor="echoCancellation" className="text-sm font-medium text-gray-700">
              Echo Cancellation
            </label>
            <p className="text-xs text-gray-500 mt-0.5">
              {getConstraintDescription('echoCancellation')}
            </p>
          </div>
        </div>

        {/* Noise Suppression */}
        <div className="flex items-start space-x-3">
          <div className="flex items-center h-5">
            <input
              id="noiseSuppression"
              type="checkbox"
              checked={settings.constraints.noiseSuppression}
              onChange={(e) => handleConstraintChange('noiseSuppression', e.target.checked)}
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label htmlFor="noiseSuppression" className="text-sm font-medium text-gray-700">
              Noise Suppression
            </label>
            <p className="text-xs text-gray-500 mt-0.5">
              {getConstraintDescription('noiseSuppression')}
            </p>
          </div>
        </div>

        {/* Auto Gain Control */}
        <div className="flex items-start space-x-3">
          <div className="flex items-center h-5">
            <input
              id="autoGainControl"
              type="checkbox"
              checked={settings.constraints.autoGainControl}
              onChange={(e) => handleConstraintChange('autoGainControl', e.target.checked)}
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label htmlFor="autoGainControl" className="text-sm font-medium text-gray-700">
              Auto Gain Control
            </label>
            <p className="text-xs text-gray-500 mt-0.5">
              {getConstraintDescription('autoGainControl')}
            </p>
          </div>
        </div>
      </div>

      {/* Advanced Settings */}
      {showAdvanced && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Advanced Settings</h4>
          
          <div className="space-y-4">
            {/* Sample Rate */}
            <div>
              <label htmlFor="sampleRate" className="block text-sm font-medium text-gray-700 mb-1">
                Sample Rate: {settings.constraints.sampleRate || 'Auto'} Hz
              </label>
              <select
                id="sampleRate"
                value={settings.constraints.sampleRate || ''}
                onChange={(e) => handleConstraintChange('sampleRate', e.target.value ? parseInt(e.target.value) : true)}
                className="w-full p-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Auto (Browser Default)</option>
                <option value="8000">8 kHz (Phone Quality)</option>
                <option value="16000">16 kHz (Voice Calls)</option>
                <option value="22050">22.05 kHz (FM Radio)</option>
                <option value="44100">44.1 kHz (CD Quality)</option>
                <option value="48000">48 kHz (Professional)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Higher rates improve quality but use more bandwidth
              </p>
            </div>

            {/* Channel Count */}
            <div>
              <label htmlFor="channelCount" className="block text-sm font-medium text-gray-700 mb-1">
                Channels
              </label>
              <select
                id="channelCount"
                value={settings.constraints.channelCount || ''}
                onChange={(e) => handleConstraintChange('channelCount', e.target.value ? parseInt(e.target.value) : true)}
                className="w-full p-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Auto</option>
                <option value="1">Mono (Recommended for calls)</option>
                <option value="2">Stereo</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Mono is recommended for voice calls to save bandwidth
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Current Configuration Preview */}
      {showAdvanced && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Current Configuration</h4>
          <pre className="text-xs text-gray-600 font-mono whitespace-pre-wrap">
            {JSON.stringify(getOptimalConstraints(), null, 2)}
          </pre>
        </div>
      )}

      {/* Reset Button */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <button
          onClick={handleReset}
          className="text-sm text-gray-600 hover:text-gray-800 focus:outline-none"
        >
          🔄 Reset to Defaults
        </button>
      </div>

      {/* Recommendations */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="text-xs font-medium text-blue-800 mb-1">💡 Recommendations</h4>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• Keep all audio processing enabled for best call quality</li>
          <li>• Use 48 kHz sample rate for professional quality</li>
          <li>• Mono channel saves bandwidth and is ideal for voice</li>
          <li>• Test your settings before important calls</li>
        </ul>
      </div>
    </div>
  )
}

export default AudioSettings