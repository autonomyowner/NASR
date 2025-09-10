import React, { useState, useEffect } from 'react'
import { useRNNoise } from '../hooks/useRNNoise'

interface RNNoiseSettingsProps {
  localStream?: MediaStream
  onProcessedStreamChange?: (stream: MediaStream | null) => void
}

const RNNoiseSettings: React.FC<RNNoiseSettingsProps> = ({
  localStream,
  onProcessedStreamChange
}) => {
  const rnnoise = useRNNoise()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Auto-load RNNoise when component mounts
  useEffect(() => {
    if (rnnoise.isSupported && !rnnoise.isLoaded && !rnnoise.error) {
      rnnoise.loadRNNoise().catch(err => {
        console.error('Failed to auto-load RNNoise:', err)
      })
    }
  }, [rnnoise.isSupported])

  // Handle stream processing
  useEffect(() => {
    if (rnnoise.settings.enabled && rnnoise.isLoaded && localStream) {
      rnnoise.enableProcessing(localStream).then(processedStream => {
        onProcessedStreamChange?.(processedStream)
      }).catch(err => {
        console.error('Failed to enable RNNoise processing:', err)
      })
    } else if (!rnnoise.settings.enabled && rnnoise.isProcessing) {
      rnnoise.disableProcessing()
      onProcessedStreamChange?.(localStream || null)
    }
  }, [rnnoise.settings.enabled, rnnoise.isLoaded, localStream])

  const handleToggleRNNoise = () => {
    if (!rnnoise.isLoaded) {
      rnnoise.loadRNNoise().then(() => {
        rnnoise.updateSettings({ enabled: !rnnoise.settings.enabled })
      }).catch(err => {
        console.error('Failed to load RNNoise:', err)
      })
    } else {
      rnnoise.updateSettings({ enabled: !rnnoise.settings.enabled })
    }
  }

  const getCpuUsageColor = (usage?: number | null): string => {
    if (!usage) return 'text-gray-400'
    if (usage < 25) return 'text-green-500'
    if (usage < 50) return 'text-yellow-500'
    if (usage < 75) return 'text-orange-500'
    return 'text-red-500'
  }

  const getCpuUsageLabel = (usage?: number | null): string => {
    if (!usage) return 'N/A'
    if (usage < 25) return 'Low'
    if (usage < 50) return 'Moderate'
    if (usage < 75) return 'High'
    return 'Very High'
  }

  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h4 className="font-semibold text-white">AI Noise Suppression</h4>
          <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-200">
            Beta
          </span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-blue-400 hover:text-blue-300 text-sm"
        >
          {isExpanded ? 'Hide' : 'Show'}
        </button>
      </div>

      {/* Status and Toggle */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-300">Status:</span>
            <span className={`text-sm font-medium ${
              rnnoise.error ? 'text-red-400' : 
              rnnoise.isProcessing ? 'text-green-400' : 
              rnnoise.isLoaded ? 'text-blue-400' : 'text-gray-400'
            }`}>
              {rnnoise.getStatus()}
            </span>
          </div>
          
          <button
            onClick={handleToggleRNNoise}
            disabled={!rnnoise.isSupported || !localStream}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              rnnoise.settings.enabled
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-gray-500 hover:bg-gray-600 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {rnnoise.settings.enabled ? 'Enabled' : 'Disabled'}
          </button>
        </div>

        {/* CPU Usage Indicator */}
        {rnnoise.isProcessing && rnnoise.cpuUsage !== null && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-300">CPU Usage:</span>
            <div className="flex items-center space-x-2">
              <span className={getCpuUsageColor(rnnoise.cpuUsage)}>
                {getCpuUsageLabel(rnnoise.cpuUsage)} ({rnnoise.cpuUsage.toFixed(1)}%)
              </span>
              {rnnoise.cpuUsage > 75 && (
                <span className="text-red-400" title="High CPU usage detected">
                  ⚠️
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Support Status */}
      {!rnnoise.isSupported && (
        <div className="bg-yellow-50/10 border border-yellow-200/20 rounded-lg p-3 mb-4">
          <div className="flex items-center space-x-2">
            <span className="text-yellow-200">⚠️</span>
            <div>
              <p className="text-yellow-200 text-sm font-medium">Not Supported</p>
              <p className="text-yellow-200/80 text-xs">
                Your browser doesn't support AudioWorklet or WebAssembly required for RNNoise.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {rnnoise.error && (
        <div className="bg-red-50/10 border border-red-200/20 rounded-lg p-3 mb-4">
          <div className="flex items-center space-x-2">
            <span className="text-red-200">❌</span>
            <div>
              <p className="text-red-200 text-sm font-medium">Error</p>
              <p className="text-red-200/80 text-xs">{rnnoise.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Expanded Settings */}
      {isExpanded && rnnoise.isSupported && (
        <div className="space-y-4">
          {/* Basic Settings */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                Fallback to Built-in NS
              </label>
              <button
                onClick={() => rnnoise.updateSettings({ 
                  fallbackToBuiltIn: !rnnoise.settings.fallbackToBuiltIn 
                })}
                className={`px-2 py-1 rounded text-xs ${
                  rnnoise.settings.fallbackToBuiltIn
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-500 text-white'
                }`}
              >
                {rnnoise.settings.fallbackToBuiltIn ? 'On' : 'Off'}
              </button>
            </div>
            <p className="text-xs text-gray-400">
              Automatically use browser's built-in noise suppression if RNNoise fails
            </p>

            {/* VAD Threshold */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-300">
                  Voice Detection Sensitivity
                </label>
                <span className="text-xs text-white font-mono">
                  {(rnnoise.settings.vadThreshold * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={rnnoise.settings.vadThreshold}
                onChange={(e) => rnnoise.updateSettings({ 
                  vadThreshold: parseFloat(e.target.value) 
                })}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>More Aggressive</span>
                <span>More Conservative</span>
              </div>
            </div>
          </div>

          {/* Advanced Settings Toggle */}
          <div className="pt-3 border-t border-gray-600">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center justify-between w-full text-sm text-blue-400 hover:text-blue-300"
            >
              <span>Advanced Settings</span>
              <span>{showAdvanced ? '▼' : '▶'}</span>
            </button>
          </div>

          {/* Advanced Settings */}
          {showAdvanced && (
            <div className="space-y-3 pt-3">
              {/* Performance Metrics */}
              {rnnoise.isProcessing && (
                <div className="bg-black/20 rounded-lg p-3">
                  <h5 className="text-sm font-semibold text-white mb-2">Performance Metrics</h5>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-gray-300">Avg Processing Time:</span>
                      <div className="text-white font-mono">
                        {rnnoise.getPerformanceMetrics().avgProcessingTime.toFixed(2)}ms
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-300">Max Processing Time:</span>
                      <div className="text-white font-mono">
                        {rnnoise.getPerformanceMetrics().maxProcessingTime.toFixed(2)}ms
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-300">Samples Processed:</span>
                      <div className="text-white font-mono">
                        {rnnoise.getPerformanceMetrics().samplesProcessed.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-300">CPU Budget:</span>
                      <div className={`font-mono ${
                        rnnoise.cpuUsage && rnnoise.cpuUsage > 75 ? 'text-red-400' : 'text-white'
                      }`}>
                        {rnnoise.cpuUsage ? `${rnnoise.cpuUsage.toFixed(1)}%` : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Manual Actions */}
              <div className="bg-black/20 rounded-lg p-3">
                <h5 className="text-sm font-semibold text-white mb-2">Manual Actions</h5>
                <div className="space-y-2">
                  <button
                    onClick={rnnoise.loadRNNoise}
                    disabled={rnnoise.isLoaded}
                    className="w-full bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1 rounded text-sm"
                  >
                    {rnnoise.isLoaded ? 'RNNoise Loaded' : 'Load RNNoise'}
                  </button>
                  
                  {rnnoise.isProcessing && (
                    <button
                      onClick={rnnoise.disableProcessing}
                      className="w-full bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm"
                    >
                      Stop Processing
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Info */}
          <div className="bg-blue-50/10 rounded-lg p-3">
            <p className="text-xs text-blue-200">
              💡 <strong>RNNoise</strong> is an advanced AI-powered noise suppression algorithm that runs locally in your browser. 
              It provides superior noise reduction compared to built-in browser features but may use more CPU resources.
            </p>
            {rnnoise.cpuUsage && rnnoise.cpuUsage > 50 && (
              <p className="text-xs text-yellow-200 mt-2">
                ⚠️ High CPU usage detected. Consider disabling on slower devices or when battery is low.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default RNNoiseSettings