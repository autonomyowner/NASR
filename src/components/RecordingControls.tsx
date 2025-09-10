import React from 'react'
import { useRecording, type RecordingSource } from '../hooks/useRecording'

interface RecordingControlsProps {
  localStream?: MediaStream
  remoteStream?: MediaStream
  peerId?: string
}

const RecordingControls: React.FC<RecordingControlsProps> = ({
  localStream,
  remoteStream,
  peerId: _peerId
}) => {
  const recording = useRecording(localStream, remoteStream)

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const getSourceIcon = (source: RecordingSource): string => {
    switch (source) {
      case 'local': return '🎤'
      case 'remote': return '👥'
      case 'mixed': return '🔄'
      default: return '🎵'
    }
  }

  const getSourceLabel = (source: RecordingSource): string => {
    switch (source) {
      case 'local': return 'My Voice Only'
      case 'remote': return 'Remote Voice Only'
      case 'mixed': return 'Both Voices'
      default: return source
    }
  }

  if (!recording.isSupported) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800 text-sm">
          ⚠️ Audio recording is not supported in this browser.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Recording Error */}
      {recording.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{recording.error}</p>
        </div>
      )}

      {/* Recording Controls */}
      <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-white">Call Recording</h4>
          {recording.currentRecording && (
            <div className="flex items-center text-sm text-red-400">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse mr-2"></div>
              Recording
            </div>
          )}
        </div>

        {/* Source Selection */}
        {!recording.isRecording && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Recording Source
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {(['local', 'remote', 'mixed'] as RecordingSource[]).map((source) => (
                <button
                  key={source}
                  onClick={() => recording.setRecordingOptions({ source })}
                  disabled={
                    (source === 'local' && !localStream) ||
                    (source === 'remote' && !remoteStream) ||
                    (source === 'mixed' && (!localStream || !remoteStream))
                  }
                  className={`p-3 rounded-lg text-sm font-medium transition-colors ${
                    recording.currentRecording?.source === source || 
                    (!recording.currentRecording && source === 'mixed')
                      ? 'bg-blue-500 text-white'
                      : 'bg-white/20 text-gray-300 hover:bg-white/30 disabled:opacity-50 disabled:cursor-not-allowed'
                  }`}
                >
                  <div className="text-lg mb-1">{getSourceIcon(source)}</div>
                  {getSourceLabel(source)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Recording Buttons */}
        <div className="flex space-x-2 mb-4">
          {!recording.isRecording && !recording.isPaused ? (
            <button
              onClick={() => recording.startRecording()}
              disabled={!localStream && !remoteStream}
              className="flex-1 bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium"
            >
              🔴 Start Recording
            </button>
          ) : (
            <>
              {recording.isRecording && (
                <button
                  onClick={recording.pauseRecording}
                  className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg font-medium"
                >
                  ⏸️ Pause
                </button>
              )}
              
              {recording.isPaused && (
                <button
                  onClick={recording.resumeRecording}
                  className="flex-1 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-medium"
                >
                  ▶️ Resume
                </button>
              )}
              
              <button
                onClick={recording.stopRecording}
                className="flex-1 bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium"
              >
                ⏹️ Stop
              </button>
            </>
          )}
        </div>

        {/* Current Recording Info */}
        {recording.currentRecording && (
          <div className="bg-black/20 rounded-lg p-3 mb-4">
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-300">Recording:</span>
              <span className="text-white font-medium">
                {getSourceIcon(recording.currentRecording.source)} {getSourceLabel(recording.currentRecording.source)}
              </span>
            </div>
            <div className="flex justify-between items-center text-sm mt-1">
              <span className="text-gray-300">Started:</span>
              <span className="text-white">{recording.currentRecording.startTime.toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </div>

      {/* Recording History */}
      {recording.recordings.length > 0 && (
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-white">Recorded Calls</h4>
            <button
              onClick={recording.clearAllRecordings}
              className="text-sm bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded"
            >
              Clear All
            </button>
          </div>
          
          <div className="space-y-2">
            {recording.recordings.map((rec, index) => (
              <div key={index} className="bg-black/20 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{getSourceIcon(rec.source)}</span>
                    <div>
                      <p className="text-sm font-medium text-white">
                        {getSourceLabel(rec.source)} Recording
                      </p>
                      <p className="text-xs text-gray-400">
                        {rec.startTime.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-white">{formatDuration(rec.duration)}</p>
                    <p className="text-xs text-gray-400">{formatSize(rec.size)}</p>
                  </div>
                </div>
                
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={() => recording.downloadRecording(rec)}
                    className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded"
                  >
                    💾 Download
                  </button>
                  <button
                    onClick={() => recording.deleteRecording(index)}
                    className="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supported Formats Info */}
      <div className="bg-blue-50/10 rounded-lg p-3">
        <p className="text-xs text-blue-200">
          💡 Recordings are saved in WebM format with Opus audio codec for best quality and compression.
        </p>
      </div>
    </div>
  )
}

export default RecordingControls