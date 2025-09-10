import React, { useEffect, useState } from 'react'
import { useMicTest } from '../hooks/useMicTest'

interface MicTestProps {
  selectedDeviceId?: string
  className?: string
}

const MicTest: React.FC<MicTestProps> = ({
  selectedDeviceId,
  className = ''
}) => {
  const {
    isTestActive,
    audioLevel,
    isClipping,
    canPlayback,
    isPlaybackActive,
    startTest,
    stopTest,
    togglePlayback,
    error
  } = useMicTest()

  const [showAdvanced, setShowAdvanced] = useState(false)

  // Auto-restart test when device changes
  useEffect(() => {
    if (isTestActive && selectedDeviceId) {
      startTest(selectedDeviceId)
    }
  }, [selectedDeviceId, isTestActive, startTest])

  const getLevelColor = () => {
    if (isClipping) return 'bg-red-500'
    if (audioLevel > 80) return 'bg-yellow-500'
    if (audioLevel > 40) return 'bg-green-500'
    return 'bg-blue-500'
  }

  const getLevelText = () => {
    if (isClipping) return 'Clipping!'
    if (audioLevel > 80) return 'Loud'
    if (audioLevel > 40) return 'Good'
    if (audioLevel > 10) return 'Quiet'
    return 'Silent'
  }

  const handleStartTest = () => {
    startTest(selectedDeviceId)
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900">Microphone Test</h3>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Test Controls */}
      <div className="flex space-x-2 mb-4">
        <button
          onClick={isTestActive ? stopTest : handleStartTest}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            isTestActive
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
        >
          {isTestActive ? '⏹️ Stop Test' : '🎤 Start Test'}
        </button>

        {canPlayback && (
          <button
            onClick={togglePlayback}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              isPlaybackActive
                ? 'bg-orange-500 text-white hover:bg-orange-600'
                : 'bg-gray-500 text-white hover:bg-gray-600'
            }`}
            title="Enable local echo to hear yourself"
          >
            {isPlaybackActive ? '🔇 Mute Echo' : '🔊 Enable Echo'}
          </button>
        )}
      </div>

      {/* Audio Level Meter */}
      {isTestActive && (
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-700">Audio Level</span>
              <span className={`text-xs font-medium ${isClipping ? 'text-red-600' : 'text-gray-600'}`}>
                {getLevelText()} ({Math.round(audioLevel)}%)
              </span>
            </div>
            
            {/* Level meter */}
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-100 ${getLevelColor()} ${
                  isClipping ? 'animate-pulse' : ''
                }`}
                style={{ width: `${Math.min(audioLevel, 100)}%` }}
              />
            </div>

            {/* Level markers */}
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span>25%</span>
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Clipping Warning */}
          {isClipping && (
            <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-xs text-red-800 font-medium">
                  Audio is clipping! Speak softer or adjust microphone distance.
                </span>
              </div>
            </div>
          )}

          {/* Playback Warning */}
          {isPlaybackActive && (
            <div className="p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800">
                🎧 Echo enabled. Use headphones to prevent feedback loops.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Advanced Info */}
      {showAdvanced && isTestActive && (
        <div className="mt-4 pt-3 border-t border-gray-200">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Technical Info</h4>
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
            <div>
              <span className="font-medium">Device:</span> {selectedDeviceId || 'Default'}
            </div>
            <div>
              <span className="font-medium">Level:</span> {Math.round(audioLevel)}%
            </div>
            <div>
              <span className="font-medium">Status:</span> 
              <span className={`ml-1 ${isClipping ? 'text-red-600 font-medium' : ''}`}>
                {isClipping ? 'Clipping' : 'Normal'}
              </span>
            </div>
            <div>
              <span className="font-medium">Echo:</span> {isPlaybackActive ? 'On' : 'Off'}
            </div>
          </div>
        </div>
      )}

      {/* Usage Tips */}
      {!isTestActive && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="text-xs font-medium text-blue-800 mb-1">💡 Tips for best results:</h4>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• Keep microphone 6-12 inches from your mouth</li>
            <li>• Speak at normal conversation level</li>
            <li>• Use headphones if testing echo playback</li>
            <li>• Green level (40-80%) is ideal for calls</li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default MicTest