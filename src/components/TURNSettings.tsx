import React, { useState } from 'react'
import { useTURNConfig, type TURNServer } from '../hooks/useTURNConfig'

interface TURNSettingsProps {
  onICEServersChange?: (servers: RTCIceServer[]) => void
}

const TURNSettings: React.FC<TURNSettingsProps> = ({ onICEServersChange }) => {
  const turnConfig = useTURNConfig()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showAddServer, setShowAddServer] = useState(false)
  const [newServer, setNewServer] = useState<TURNServer>({
    urls: '',
    username: '',
    credential: ''
  })

  // Notify parent component when ICE servers change
  React.useEffect(() => {
    onICEServersChange?.(turnConfig.getICEServers())
  }, [turnConfig.config, onICEServersChange])

  const handleAddServer = () => {
    const urlsStr = Array.isArray(newServer.urls) ? newServer.urls[0] : newServer.urls
    if (!urlsStr || !urlsStr.trim()) return

    turnConfig.addTURNServer({
      urls: urlsStr.trim(),
      username: newServer.username?.trim() || undefined,
      credential: newServer.credential?.trim() || undefined
    })

    // Reset form
    setNewServer({ urls: '', username: '', credential: '' })
    setShowAddServer(false)
  }

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'testing': return '🔄'
      case 'success': return '✅'
      case 'failed': return '❌'
      case 'timeout': return '⏰'
      default: return '❓'
    }
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'testing': return 'text-yellow-400'
      case 'success': return 'text-green-400'
      case 'failed': return 'text-red-400'
      case 'timeout': return 'text-orange-400'
      default: return 'text-gray-400'
    }
  }

  const formatLatency = (latency?: number): string => {
    return latency ? `${latency}ms` : 'N/A'
  }

  const isValidTURNUrl = (url: string | string[]): boolean => {
    try {
      const urlStr = Array.isArray(url) ? url[0] : url
      return urlStr ? (urlStr.startsWith('turn:') || urlStr.startsWith('turns:')) : false
    } catch {
      return false
    }
  }

  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h4 className="font-semibold text-white">TURN Server Configuration</h4>
          <span className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-200">
            Advanced
          </span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-blue-400 hover:text-blue-300 text-sm"
        >
          {isExpanded ? 'Hide' : 'Show'}
        </button>
      </div>

      {/* Quick Status */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-300">TURN Enabled:</span>
          <button
            onClick={() => turnConfig.updateConfig({ enabled: !turnConfig.config.enabled })}
            className={`px-3 py-1 rounded text-sm font-medium ${
              turnConfig.config.enabled
                ? 'bg-green-500 text-white'
                : 'bg-gray-500 text-white'
            }`}
          >
            {turnConfig.config.enabled ? 'On' : 'Off'}
          </button>
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-300">Configured Servers:</span>
          <span className="text-white">{turnConfig.config.servers.length}</span>
        </div>
      </div>

      {!isExpanded && (
        <p className="text-xs text-gray-400">
          💡 TURN servers help establish connections through firewalls and NATs. Configure your own servers for improved connectivity.
        </p>
      )}

      {/* Expanded Settings */}
      {isExpanded && (
        <div className="space-y-4">
          {/* Error Display */}
          {turnConfig.error && (
            <div className="bg-red-50/10 border border-red-200/20 rounded-lg p-3">
              <p className="text-red-200 text-sm">{turnConfig.error}</p>
            </div>
          )}

          {/* Configuration Options */}
          <div className="bg-black/20 rounded-lg p-3">
            <h5 className="text-sm font-semibold text-white mb-3">Settings</h5>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-300">Test on Connect</label>
                  <p className="text-xs text-gray-400">Test TURN servers before using them</p>
                </div>
                <button
                  onClick={() => turnConfig.updateConfig({ 
                    testOnConnect: !turnConfig.config.testOnConnect 
                  })}
                  className={`px-2 py-1 rounded text-xs ${
                    turnConfig.config.testOnConnect
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-500 text-white'
                  }`}
                >
                  {turnConfig.config.testOnConnect ? 'On' : 'Off'}
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-300">Fallback to STUN</label>
                  <p className="text-xs text-gray-400">Use free STUN servers as backup</p>
                </div>
                <button
                  onClick={() => turnConfig.updateConfig({ 
                    fallbackToSTUN: !turnConfig.config.fallbackToSTUN 
                  })}
                  className={`px-2 py-1 rounded text-xs ${
                    turnConfig.config.fallbackToSTUN
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-500 text-white'
                  }`}
                >
                  {turnConfig.config.fallbackToSTUN ? 'On' : 'Off'}
                </button>
              </div>
            </div>
          </div>

          {/* Server List */}
          <div className="bg-black/20 rounded-lg p-3">
            <div className="flex items-center justify-between mb-3">
              <h5 className="text-sm font-semibold text-white">TURN Servers</h5>
              <div className="flex space-x-2">
                {turnConfig.config.servers.length > 0 && (
                  <button
                    onClick={turnConfig.testAllServers}
                    disabled={turnConfig.isTestingConnection}
                    className="bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                  >
                    {turnConfig.isTestingConnection ? '🔄 Testing...' : '🧪 Test All'}
                  </button>
                )}
                <button
                  onClick={() => setShowAddServer(!showAddServer)}
                  className="bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded text-xs"
                >
                  {showAddServer ? 'Cancel' : '+ Add'}
                </button>
              </div>
            </div>

            {/* Server List */}
            {turnConfig.config.servers.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-4">
                No TURN servers configured. Add one to get started.
              </p>
            ) : (
              <div className="space-y-2">
                {turnConfig.config.servers.map((server, index) => {
                  const testResult = turnConfig.testResults.find(r => 
                    Array.isArray(server.urls) 
                      ? server.urls.some(url => Array.isArray(r.server.urls) ? r.server.urls.includes(url) : r.server.urls === url)
                      : Array.isArray(r.server.urls) ? r.server.urls.includes(server.urls) : r.server.urls === server.urls
                  )

                  return (
                    <div key={index} className="bg-white/10 rounded p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <code className="text-xs bg-black/30 px-2 py-1 rounded text-blue-200">
                            {Array.isArray(server.urls) ? server.urls[0] : server.urls}
                          </code>
                          {testResult && (
                            <div className="flex items-center space-x-1">
                              <span>{getStatusIcon(testResult.status)}</span>
                              <span className={`text-xs ${getStatusColor(testResult.status)}`}>
                                {testResult.status}
                              </span>
                              {testResult.latency && (
                                <span className="text-xs text-gray-300">
                                  ({formatLatency(testResult.latency)})
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => turnConfig.removeTURNServer(index)}
                          className="text-red-400 hover:text-red-300 text-xs"
                        >
                          Remove
                        </button>
                      </div>
                      
                      {server.username && (
                        <div className="text-xs text-gray-300">
                          Username: <code className="bg-black/30 px-1 rounded">{server.username}</code>
                        </div>
                      )}
                      
                      {testResult?.error && (
                        <div className="text-xs text-red-300 mt-1">
                          Error: {testResult.error}
                        </div>
                      )}
                      
                      {testResult?.relayType && (
                        <div className="text-xs text-green-300 mt-1">
                          Relay Type: {testResult.relayType.toUpperCase()}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Add Server Form */}
            {showAddServer && (
              <div className="mt-4 p-3 bg-white/10 rounded-lg">
                <h6 className="text-sm font-semibold text-white mb-3">Add TURN Server</h6>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-300 mb-1">
                      TURN URL (required)
                    </label>
                    <input
                      type="text"
                      value={newServer.urls}
                      onChange={(e) => setNewServer(prev => ({ ...prev, urls: e.target.value }))}
                      placeholder="turn:your-turn-server.com:3478"
                      className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    />
                    {newServer.urls && !isValidTURNUrl(newServer.urls) && (
                      <p className="text-xs text-red-400 mt-1">
                        URL should start with 'turn:' or 'turns:'
                      </p>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-300 mb-1">
                      Username (optional)
                    </label>
                    <input
                      type="text"
                      value={newServer.username}
                      onChange={(e) => setNewServer(prev => ({ ...prev, username: e.target.value }))}
                      placeholder="username"
                      className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs text-gray-300 mb-1">
                      Credential (optional)
                    </label>
                    <input
                      type="password"
                      value={newServer.credential}
                      onChange={(e) => setNewServer(prev => ({ ...prev, credential: e.target.value }))}
                      placeholder="password or secret"
                      className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    />
                  </div>
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={handleAddServer}
                      disabled={!(Array.isArray(newServer.urls) ? newServer.urls[0]?.trim() : newServer.urls?.trim()) || !isValidTURNUrl(Array.isArray(newServer.urls) ? newServer.urls[0] : newServer.urls)}
                      className="flex-1 bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded text-sm"
                    >
                      Add Server
                    </button>
                    <button
                      onClick={() => setShowAddServer(false)}
                      className="flex-1 bg-gray-500 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="bg-black/20 rounded-lg p-3">
            <h5 className="text-sm font-semibold text-white mb-3">Actions</h5>
            <div className="flex space-x-2">
              <button
                onClick={turnConfig.resetToDefaults}
                className="bg-red-500 hover:bg-red-600 text-white px-3 py-2 rounded text-sm"
              >
                Reset to Defaults
              </button>
              <button
                onClick={turnConfig.saveConfig}
                className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded text-sm"
              >
                Save Config
              </button>
            </div>
          </div>

          {/* Current ICE Servers Preview */}
          <div className="bg-blue-50/10 rounded-lg p-3">
            <h5 className="text-sm font-semibold text-blue-200 mb-2">Active ICE Servers</h5>
            <div className="space-y-1">
              {turnConfig.getICEServers().map((server, index) => (
                <div key={index} className="text-xs text-blue-200">
                  <code className="bg-black/30 px-2 py-1 rounded">
                    {Array.isArray(server.urls) ? server.urls.join(', ') : server.urls}
                  </code>
                  {server.username && (
                    <span className="ml-2 text-blue-300">
                      (auth: {server.username})
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Information */}
          <div className="bg-yellow-50/10 rounded-lg p-3">
            <p className="text-xs text-yellow-200">
              💡 <strong>TURN servers</strong> help establish peer-to-peer connections through restrictive firewalls and NATs. 
              They relay traffic when direct connections aren't possible, improving connection success rates but using server bandwidth.
            </p>
            <p className="text-xs text-yellow-200 mt-2">
              ⚠️ <strong>Self-hosted TURN servers</strong> require proper configuration including authentication, firewall rules, and sufficient bandwidth. 
              Popular options include <code>coturn</code> and cloud provider TURN services.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TURNSettings