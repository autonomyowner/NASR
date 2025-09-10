import React, { useState } from 'react'
import { useWebRTCStats } from '../hooks/useWebRTCStats'

interface WebRTCDebugProps {
  peerConnection?: RTCPeerConnection
  show?: boolean
  isCallActive?: boolean
}

const WebRTCDebug: React.FC<WebRTCDebugProps> = ({ 
  peerConnection, 
  show = false, 
  isCallActive = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeTab, setActiveTab] = useState<'current' | 'history' | 'export'>('current')
  
  const stats = useWebRTCStats(peerConnection)

  const formatBytes = (bytes?: number): string => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  const formatDuration = (ms: number): string => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) {
      return `${hours}:${(minutes % 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`
    }
    return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`
  }

  const getConnectionStatusColor = (state: string): string => {
    switch (state) {
      case 'connected': case 'completed': case 'stable':
        return 'text-green-500'
      case 'connecting': case 'checking': case 'gathering':
        return 'text-yellow-500'
      case 'disconnected': case 'failed': case 'closed':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const renderCurrentStats = () => {
    if (!stats.currentStats) {
      return (
        <div className="text-center text-gray-400 py-4">
          No stats available. Start a call to see WebRTC statistics.
        </div>
      )
    }

    const s = stats.currentStats

    return (
      <div className="space-y-4">
        {/* Connection State */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-black/20 p-3 rounded">
            <h5 className="text-sm font-semibold text-white mb-2">Connection State</h5>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-300">Peer Connection:</span>
                <span className={getConnectionStatusColor(s.connectionState)}>
                  {s.connectionState}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">ICE Connection:</span>
                <span className={getConnectionStatusColor(s.iceConnectionState)}>
                  {s.iceConnectionState}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Signaling:</span>
                <span className={getConnectionStatusColor(s.signalingState)}>
                  {s.signalingState}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-black/20 p-3 rounded">
            <h5 className="text-sm font-semibold text-white mb-2">Network</h5>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-300">RTT:</span>
                <span className="text-white">
                  {s.currentRoundTripTime ? `${(s.currentRoundTripTime * 1000).toFixed(1)}ms` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Sent:</span>
                <span className="text-white">{formatBytes(s.bytesSent)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Received:</span>
                <span className="text-white">{formatBytes(s.bytesReceived)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Audio Stats */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-2">Audio Quality</h5>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-300">Codec:</span>
                <span className="text-white">{s.audioCodec || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Bitrate:</span>
                <span className="text-white">
                  {s.audioBitrate ? `${(s.audioBitrate / 1000).toFixed(1)} kbps` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Sample Rate:</span>
                <span className="text-white">
                  {s.audioSampleRate ? `${(s.audioSampleRate / 1000).toFixed(1)} kHz` : 'N/A'}
                </span>
              </div>
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-300">Packets Lost:</span>
                <span className={s.packetsLostPercent && s.packetsLostPercent > 5 ? 'text-red-400' : 'text-white'}>
                  {s.packetsLostPercent ? `${s.packetsLostPercent.toFixed(2)}%` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Jitter:</span>
                <span className="text-white">
                  {s.audioJitter ? `${(s.audioJitter * 1000).toFixed(1)}ms` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Concealment:</span>
                <span className={s.concealmentEvents && s.concealmentEvents > 0 ? 'text-yellow-400' : 'text-white'}>
                  {s.concealmentEvents || 0} events
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ICE Candidates */}
        {(s.localCandidateType || s.remoteCandidateType) && (
          <div className="bg-black/20 p-3 rounded">
            <h5 className="text-sm font-semibold text-white mb-2">ICE Candidates</h5>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-300">Local Type:</span>
                  <span className="text-white">{s.localCandidateType || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Local Network:</span>
                  <span className="text-white">{s.localNetworkType || 'N/A'}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-300">Remote Type:</span>
                  <span className="text-white">{s.remoteCandidateType || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Remote Network:</span>
                  <span className="text-white">{s.remoteNetworkType || 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Advanced Audio Metrics */}
        {s.concealedSamples !== undefined && (
          <div className="bg-black/20 p-3 rounded">
            <h5 className="text-sm font-semibold text-white mb-2">Audio Processing</h5>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-300">Concealed Samples:</span>
                  <span className="text-white">{s.concealedSamples || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Silent Concealed:</span>
                  <span className="text-white">{s.silentConcealedSamples || 0}</span>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-300">Samples Inserted:</span>
                  <span className="text-white">{s.insertedSamplesForDeceleration || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Samples Removed:</span>
                  <span className="text-white">{s.removedSamplesForAcceleration || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderHistory = () => {
    if (stats.statsHistory.length === 0) {
      return (
        <div className="text-center text-gray-400 py-4">
          No stats history available. Enable stats collection to see historical data.
        </div>
      )
    }

    const recent = stats.statsHistory.slice(-10).reverse()
    const avgBitrate = stats.getAverageStats('audioBitrate', 1)
    const avgRTT = stats.getAverageStats('currentRoundTripTime', 1)
    const avgPacketLoss = stats.getAverageStats('packetsLostPercent', 1)

    return (
      <div className="space-y-4">
        {/* Summary Stats */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-2">1-Minute Averages</h5>
          <div className="grid grid-cols-3 gap-4 text-xs">
            <div className="text-center">
              <div className="text-gray-300">Bitrate</div>
              <div className="text-white font-semibold">
                {avgBitrate ? `${(avgBitrate / 1000).toFixed(1)} kbps` : 'N/A'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-300">RTT</div>
              <div className="text-white font-semibold">
                {avgRTT ? `${(avgRTT * 1000).toFixed(1)}ms` : 'N/A'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-gray-300">Packet Loss</div>
              <div className={`font-semibold ${avgPacketLoss && avgPacketLoss > 5 ? 'text-red-400' : 'text-white'}`}>
                {avgPacketLoss ? `${avgPacketLoss.toFixed(2)}%` : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Recent History */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-2">Recent History (Last 10 entries)</h5>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {recent.map((stat) => (
              <div key={stat.timestamp} className="flex justify-between items-center text-xs py-1 border-b border-gray-600/50">
                <span className="text-gray-300">
                  {new Date(stat.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-white">
                  {stat.audioBitrate ? `${(stat.audioBitrate / 1000).toFixed(1)}k` : 'N/A'}
                </span>
                <span className="text-white">
                  {stat.currentRoundTripTime ? `${(stat.currentRoundTripTime * 1000).toFixed(0)}ms` : 'N/A'}
                </span>
                <span className={stat.packetsLostPercent && stat.packetsLostPercent > 5 ? 'text-red-400' : 'text-white'}>
                  {stat.packetsLostPercent ? `${stat.packetsLostPercent.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Collection Info */}
        <div className="bg-blue-50/10 p-3 rounded text-xs text-blue-200">
          <div className="flex justify-between mb-1">
            <span>Total Entries:</span>
            <span>{stats.statsHistory.length}</span>
          </div>
          <div className="flex justify-between mb-1">
            <span>Collection Time:</span>
            <span>
              {stats.statsHistory.length > 0 
                ? formatDuration(Date.now() - stats.statsHistory[0].timestamp)
                : '0:00'
              }
            </span>
          </div>
          <div className="flex justify-between">
            <span>Status:</span>
            <span className={stats.isCollecting ? 'text-green-400' : 'text-gray-400'}>
              {stats.isCollecting ? 'Collecting' : 'Stopped'}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const renderExport = () => {
    return (
      <div className="space-y-4">
        {/* Export Options */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-3">Export Stats</h5>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Export as JSON (detailed)</span>
              <button
                onClick={() => stats.exportStats('json')}
                disabled={stats.statsHistory.length === 0}
                className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1 rounded text-sm"
              >
                📄 JSON
              </button>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Export as CSV (spreadsheet)</span>
              <button
                onClick={() => stats.exportStats('csv')}
                disabled={stats.statsHistory.length === 0}
                className="bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1 rounded text-sm"
              >
                📊 CSV
              </button>
            </div>
          </div>
          
          {stats.statsHistory.length === 0 && (
            <p className="text-xs text-yellow-200 mt-3">
              💡 No stats to export. Enable collection and wait for data to be gathered.
            </p>
          )}
        </div>

        {/* Collection Settings */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-3">Collection Settings</h5>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-300 mb-1">Collection Interval</label>
              <select
                value={1000} // Default interval
                onChange={(e) => stats.setCollectionInterval(Number(e.target.value))}
                className="bg-gray-600 text-white rounded px-2 py-1 text-xs w-full"
              >
                <option value={500}>500ms (High frequency)</option>
                <option value={1000}>1 second (Default)</option>
                <option value={2000}>2 seconds</option>
                <option value={5000}>5 seconds</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs text-gray-300 mb-1">Max History Entries</label>
              <select
                value={300} // Default max entries
                onChange={(e) => stats.setMaxEntries(Number(e.target.value))}
                className="bg-gray-600 text-white rounded px-2 py-1 text-xs w-full"
              >
                <option value={100}>100 entries (~2 min)</option>
                <option value={300}>300 entries (~5 min)</option>
                <option value={600}>600 entries (~10 min)</option>
                <option value={1800}>1800 entries (~30 min)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-black/20 p-3 rounded">
          <h5 className="text-sm font-semibold text-white mb-3">Actions</h5>
          <div className="space-y-2">
            <div className="flex space-x-2">
              {!stats.isCollecting ? (
                <button
                  onClick={stats.startCollecting}
                  disabled={!peerConnection || !isCallActive}
                  className="flex-1 bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1 rounded text-sm"
                >
                  ▶️ Start Collection
                </button>
              ) : (
                <button
                  onClick={stats.stopCollecting}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm"
                >
                  ⏹️ Stop Collection
                </button>
              )}
              
              <button
                onClick={stats.clearHistory}
                className="flex-1 bg-gray-500 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm"
              >
                🗑️ Clear History
              </button>
            </div>
            
            {!isCallActive && (
              <p className="text-xs text-yellow-200">
                💡 Stats collection requires an active call.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!show) return null

  if (!stats.isSupported) {
    return (
      <div className="fixed bottom-4 right-4 bg-yellow-500 text-black p-3 rounded-lg text-sm max-w-sm">
        ⚠️ WebRTC stats are not supported in this browser.
      </div>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {!isExpanded ? (
        <button
          onClick={() => setIsExpanded(true)}
          className="bg-gray-800/90 backdrop-blur-sm text-white p-3 rounded-lg shadow-lg hover:bg-gray-700/90 transition-colors"
        >
          <span className="text-sm">📊 Debug</span>
          {stats.error && <div className="w-2 h-2 bg-red-500 rounded-full ml-2 animate-pulse" />}
        </button>
      ) : (
        <div className="bg-gray-800/95 backdrop-blur-sm text-white rounded-lg shadow-xl w-96 max-h-[600px] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-gray-600">
            <h4 className="font-semibold">WebRTC Debug Panel</h4>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {/* Error Display */}
          {stats.error && (
            <div className="bg-red-500/20 border-l-4 border-red-500 p-2 mx-3 mt-3 rounded">
              <p className="text-red-200 text-xs">{stats.error}</p>
            </div>
          )}

          {/* Tabs */}
          <div className="flex border-b border-gray-600">
            {[
              { id: 'current', label: 'Current', icon: '📊' },
              { id: 'history', label: 'History', icon: '📈' },
              { id: 'export', label: 'Export', icon: '💾' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 p-2 text-sm ${
                  activeTab === tab.id
                    ? 'bg-blue-600/50 text-white border-b-2 border-blue-500'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-3 max-h-[500px] overflow-y-auto">
            {activeTab === 'current' && renderCurrentStats()}
            {activeTab === 'history' && renderHistory()}
            {activeTab === 'export' && renderExport()}
          </div>
        </div>
      )}
    </div>
  )
}

export default WebRTCDebug