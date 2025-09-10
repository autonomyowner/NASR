import React, { useState } from 'react'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useVolumeControls } from '../hooks/useVolumeControls'

interface AccessibilityControlsProps {
  remoteAudioElement?: HTMLAudioElement
  localStream?: MediaStream
  isCallActive: boolean
  onMute?: () => void
  onToggleCaptions?: () => void
  onToggleRecording?: () => void
  onPushToTalkStart?: () => void
  onPushToTalkEnd?: () => void
}

const AccessibilityControls: React.FC<AccessibilityControlsProps> = ({
  remoteAudioElement,
  localStream,
  isCallActive,
  onMute,
  onToggleCaptions,
  onToggleRecording,
  onPushToTalkStart,
  onPushToTalkEnd
}) => {
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [showVolumeSettings, setShowVolumeSettings] = useState(false)

  const volumeControls = useVolumeControls(remoteAudioElement, localStream)
  
  const keyboardShortcuts = useKeyboardShortcuts({
    onMute,
    onToggleCaptions,
    onToggleRecording,
    onPushToTalkStart,
    onPushToTalkEnd,
    onVolumeUp: () => volumeControls.volumeUp('remote'),
    onVolumeDown: () => volumeControls.volumeDown('remote'),
    isCallActive
  })

  const formatVolumeDb = (volume: number): string => {
    const db = volumeControls.getVolumeDb(volume)
    return db === -Infinity ? '-∞ dB' : `${db.toFixed(1)} dB`
  }

  return (
    <div className="space-y-4">
      {/* Push-to-Talk Toggle */}
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-white">Push-to-Talk Mode</h4>
          <button
            onClick={keyboardShortcuts.togglePushToTalkMode}
            className={`px-3 py-1 rounded text-sm font-medium ${
              keyboardShortcuts.isPushToTalkEnabled
                ? 'bg-green-500 text-white'
                : 'bg-gray-500 text-white'
            }`}
          >
            {keyboardShortcuts.isPushToTalkEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
        
        {keyboardShortcuts.isPushToTalkEnabled && (
          <div className="space-y-2">
            <p className="text-sm text-gray-300">
              Hold <kbd className="px-2 py-1 bg-black/30 rounded text-white font-mono">
                {keyboardShortcuts.pushToTalkKey === 'Space' ? 'Space' : keyboardShortcuts.pushToTalkKey}
              </kbd> to speak
            </p>
            
            {keyboardShortcuts.isPushToTalkActive && (
              <div className="flex items-center text-sm text-green-400">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
                Push-to-Talk Active
              </div>
            )}
            
            <div className="mt-3">
              <label className="block text-sm text-gray-300 mb-2">
                Push-to-Talk Key:
              </label>
              <select
                value={keyboardShortcuts.pushToTalkKey}
                onChange={(e) => keyboardShortcuts.setPushToTalkKey(e.target.value)}
                className="bg-black/30 text-white rounded px-2 py-1 text-sm"
              >
                <option value="Space">Space</option>
                <option value="KeyT">T</option>
                <option value="KeyV">V</option>
                <option value="KeyB">B</option>
                <option value="ControlLeft">Left Ctrl</option>
                <option value="AltLeft">Left Alt</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Volume Controls */}
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-white">Volume Controls</h4>
          <button
            onClick={() => setShowVolumeSettings(!showVolumeSettings)}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {showVolumeSettings ? 'Hide' : 'Show'} Settings
          </button>
        </div>

        {!volumeControls.isSupported && (
          <div className="bg-yellow-50/10 border border-yellow-200/20 rounded-lg p-3 mb-4">
            <p className="text-yellow-200 text-sm">
              ⚠️ Advanced volume controls require a modern browser with Web Audio API support.
            </p>
          </div>
        )}

        {/* Remote Audio Volume */}
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Remote Voice Volume
            </label>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-white font-mono">
                {volumeControls.settings.remoteVolume}%
              </span>
              <button
                onClick={volumeControls.toggleRemoteMute}
                className={`p-1 rounded text-sm ${
                  volumeControls.settings.isRemoteMuted
                    ? 'bg-red-500 text-white'
                    : 'bg-green-500 text-white'
                }`}
              >
                {volumeControls.settings.isRemoteMuted ? '🔇' : '🔊'}
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => volumeControls.volumeDown('remote')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              -
            </button>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={volumeControls.settings.remoteVolume}
              onChange={(e) => volumeControls.setRemoteVolume(Number(e.target.value))}
              className="flex-1 accent-blue-500"
            />
            <button
              onClick={() => volumeControls.volumeUp('remote')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              +
            </button>
          </div>
        </div>

        {/* Local Monitoring Volume */}
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Local Monitoring
            </label>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-white font-mono">
                {volumeControls.settings.localVolume}%
              </span>
              <button
                onClick={volumeControls.toggleLocalMute}
                className={`p-1 rounded text-sm ${
                  volumeControls.settings.isLocalMuted
                    ? 'bg-red-500 text-white'
                    : 'bg-green-500 text-white'
                }`}
              >
                {volumeControls.settings.isLocalMuted ? '🔇' : '🎤'}
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => volumeControls.volumeDown('local')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              -
            </button>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={volumeControls.settings.localVolume}
              onChange={(e) => volumeControls.setLocalVolume(Number(e.target.value))}
              className="flex-1 accent-green-500"
            />
            <button
              onClick={() => volumeControls.volumeUp('local')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              +
            </button>
          </div>
          
          <p className="text-xs text-gray-400">
            💡 Lets you hear your own voice during the call
          </p>
        </div>

        {/* Master Volume */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Master Volume
            </label>
            <span className="text-sm text-white font-mono">
              {volumeControls.settings.masterVolume}%
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => volumeControls.volumeDown('master')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              -
            </button>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={volumeControls.settings.masterVolume}
              onChange={(e) => volumeControls.setMasterVolume(Number(e.target.value))}
              className="flex-1 accent-purple-500"
            />
            <button
              onClick={() => volumeControls.volumeUp('master')}
              className="bg-gray-600 hover:bg-gray-500 text-white px-2 py-1 rounded text-sm"
            >
              +
            </button>
          </div>
        </div>

        {/* Advanced Volume Settings */}
        {showVolumeSettings && volumeControls.isSupported && (
          <div className="mt-4 pt-4 border-t border-white/20">
            <div className="grid grid-cols-2 gap-4 text-xs text-gray-300">
              <div>
                <p>Remote: {formatVolumeDb(volumeControls.settings.remoteVolume)}</p>
                <p>Local: {formatVolumeDb(volumeControls.settings.localVolume)}</p>
              </div>
              <div>
                <p>Master: {formatVolumeDb(volumeControls.settings.masterVolume)}</p>
                <p>Audio Context: {volumeControls.audioContext ? 'Active' : 'Inactive'}</p>
              </div>
            </div>
            
            <div className="flex space-x-2 mt-3">
              <button
                onClick={volumeControls.muteAll}
                className="text-xs bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded"
              >
                Mute All
              </button>
              <button
                onClick={volumeControls.unmuteAll}
                className="text-xs bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded"
              >
                Unmute All
              </button>
              <button
                onClick={volumeControls.resetToDefaults}
                className="text-xs bg-gray-500 hover:bg-gray-600 text-white px-2 py-1 rounded"
              >
                Reset Defaults
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Keyboard Shortcuts */}
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-white">Keyboard Shortcuts</h4>
          <button
            onClick={() => setShowShortcuts(!showShortcuts)}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {showShortcuts ? 'Hide' : 'Show'}
          </button>
        </div>
        
        {showShortcuts && (
          <div className="space-y-2">
            {keyboardShortcuts.getShortcutHelp().map((shortcut, index) => (
              <div key={index} className="flex justify-between items-center text-sm">
                <span className="text-gray-300">{shortcut.split(' - ')[1]}</span>
                <kbd className="px-2 py-1 bg-black/30 rounded text-white font-mono text-xs">
                  {shortcut.split(' - ')[0]}
                </kbd>
              </div>
            ))}
            
            <div className="mt-4 pt-3 border-t border-white/20">
              <p className="text-xs text-gray-400">
                💡 Shortcuts only work when the call interface is active and no input fields are focused.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
        <h4 className="font-semibold text-white mb-4">Quick Actions</h4>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onMute}
            disabled={!isCallActive}
            className="bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm"
          >
            🔇 Toggle Mute
          </button>
          <button
            onClick={onToggleCaptions}
            disabled={!isCallActive}
            className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm"
          >
            📝 Toggle Captions
          </button>
          <button
            onClick={onToggleRecording}
            disabled={!isCallActive}
            className="bg-purple-500 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm"
          >
            🔴 Toggle Recording
          </button>
          <button
            onClick={() => {
              volumeControls.setMasterVolume(85)
              volumeControls.setRemoteVolume(80)
              volumeControls.unmuteAll()
            }}
            className="bg-green-500 hover:bg-green-600 text-white px-3 py-2 rounded text-sm"
          >
            🔧 Reset Audio
          </button>
        </div>
      </div>
    </div>
  )
}

export default AccessibilityControls