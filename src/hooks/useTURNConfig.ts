import { useState, useCallback, useEffect } from 'react'

export interface TURNServer {
  urls: string | string[]
  username?: string
  credential?: string
}

export interface TURNConfig {
  enabled: boolean
  servers: TURNServer[]
  testOnConnect: boolean
  fallbackToSTUN: boolean
}

export interface UseTURNConfigReturn {
  config: TURNConfig
  isTestingConnection: boolean
  testResults: TURNTestResult[]
  error: string | null
  
  // Configuration
  updateConfig: (newConfig: Partial<TURNConfig>) => void
  addTURNServer: (server: TURNServer) => void
  removeTURNServer: (index: number) => void
  updateTURNServer: (index: number, server: Partial<TURNServer>) => void
  
  // Testing
  testTURNServer: (server: TURNServer) => Promise<TURNTestResult>
  testAllServers: () => Promise<void>
  
  // Persistence
  saveConfig: () => void
  loadConfig: () => void
  resetToDefaults: () => void
  
  // ICE servers for RTCPeerConnection
  getICEServers: () => RTCIceServer[]
}

export interface TURNTestResult {
  server: TURNServer
  status: 'testing' | 'success' | 'failed' | 'timeout'
  latency?: number
  error?: string
  timestamp: number
  relayType?: 'udp' | 'tcp' | 'tls'
}

const STORAGE_KEY = 'travoice-turn-config'

const DEFAULT_CONFIG: TURNConfig = {
  enabled: false,
  servers: [],
  testOnConnect: true,
  fallbackToSTUN: true
}

// Default STUN servers for fallback
const DEFAULT_STUN_SERVERS: RTCIceServer[] = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
]

export const useTURNConfig = (): UseTURNConfigReturn => {
  const [config, setConfig] = useState<TURNConfig>(DEFAULT_CONFIG)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testResults, setTestResults] = useState<TURNTestResult[]>([])
  const [error, setError] = useState<string | null>(null)

  // Update configuration
  const updateConfig = useCallback((newConfig: Partial<TURNConfig>) => {
    setConfig(prev => ({ ...prev, ...newConfig }))
    setError(null)
  }, [])

  // Add TURN server
  const addTURNServer = useCallback((server: TURNServer) => {
    setConfig(prev => ({
      ...prev,
      servers: [...prev.servers, server]
    }))
  }, [])

  // Remove TURN server
  const removeTURNServer = useCallback((index: number) => {
    setConfig(prev => ({
      ...prev,
      servers: prev.servers.filter((_, i) => i !== index)
    }))
  }, [])

  // Update TURN server
  const updateTURNServer = useCallback((index: number, serverUpdate: Partial<TURNServer>) => {
    setConfig(prev => ({
      ...prev,
      servers: prev.servers.map((server, i) => 
        i === index ? { ...server, ...serverUpdate } : server
      )
    }))
  }, [])

  // Test TURN server connectivity
  const testTURNServer = useCallback(async (server: TURNServer): Promise<TURNTestResult> => {
    const startTime = Date.now()
    
    const result: TURNTestResult = {
      server,
      status: 'testing',
      timestamp: startTime
    }

    try {
      // Create a temporary peer connection to test TURN connectivity
      const pc = new RTCPeerConnection({
        iceServers: [{
          urls: server.urls,
          username: server.username,
          credential: server.credential
        }]
      })

      let resolved = false
      const timeoutMs = 10000 // 10 second timeout

      return new Promise((resolve) => {
        const timeout = setTimeout(() => {
          if (!resolved) {
            resolved = true
            pc.close()
            resolve({
              ...result,
              status: 'timeout',
              error: 'Connection test timed out',
              latency: Date.now() - startTime
            })
          }
        }, timeoutMs)

        pc.onicecandidate = (event) => {
          if (event.candidate) {
            const candidate = event.candidate
            
            // Check if we got a relay candidate (TURN)
            if (candidate.type === 'relay') {
              if (!resolved) {
                resolved = true
                clearTimeout(timeout)
                pc.close()
                
                // Determine relay type from candidate
                let relayType: 'udp' | 'tcp' | 'tls' = 'udp'
                if (candidate.protocol === 'tcp') {
                  relayType = 'tcp'
                } else if (candidate.relatedAddress && candidate.relatedPort === 443) {
                  relayType = 'tls'
                }
                
                resolve({
                  ...result,
                  status: 'success',
                  latency: Date.now() - startTime,
                  relayType
                })
              }
            }
          }
        }

        pc.onicegatheringstatechange = () => {
          if (pc.iceGatheringState === 'complete' && !resolved) {
            resolved = true
            clearTimeout(timeout)
            pc.close()
            
            resolve({
              ...result,
              status: 'failed',
              error: 'No relay candidates found - TURN server may be unreachable or misconfigured',
              latency: Date.now() - startTime
            })
          }
        }

        // Create a data channel to trigger ICE gathering
        pc.createDataChannel('test')
        
        // Create and set local description to start ICE gathering
        pc.createOffer().then(offer => {
          return pc.setLocalDescription(offer)
        }).catch(err => {
          if (!resolved) {
            resolved = true
            clearTimeout(timeout)
            pc.close()
            resolve({
              ...result,
              status: 'failed',
              error: `Failed to create offer: ${err.message}`,
              latency: Date.now() - startTime
            })
          }
        })
      })

    } catch (err) {
      return {
        ...result,
        status: 'failed',
        error: err instanceof Error ? err.message : 'Unknown error',
        latency: Date.now() - startTime
      }
    }
  }, [])

  // Test all configured TURN servers
  const testAllServers = useCallback(async (): Promise<void> => {
    if (config.servers.length === 0) {
      setError('No TURN servers configured to test')
      return
    }

    setIsTestingConnection(true)
    setError(null)
    setTestResults([])

    try {
      // Initialize test results with testing status
      const initialResults: TURNTestResult[] = config.servers.map(server => ({
        server,
        status: 'testing',
        timestamp: Date.now()
      }))
      setTestResults(initialResults)

      // Test all servers in parallel
      const testPromises = config.servers.map(server => testTURNServer(server))
      const results = await Promise.all(testPromises)
      
      setTestResults(results)
      
      // Check if any tests succeeded
      const successfulTests = results.filter(r => r.status === 'success')
      if (successfulTests.length === 0) {
        setError('All TURN servers failed connectivity tests')
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test TURN servers')
    } finally {
      setIsTestingConnection(false)
    }
  }, [config.servers, testTURNServer])

  // Get ICE servers for RTCPeerConnection
  const getICEServers = useCallback((): RTCIceServer[] => {
    const servers: RTCIceServer[] = []

    // Add TURN servers if enabled and configured
    if (config.enabled && config.servers.length > 0) {
      config.servers.forEach(turnServer => {
        servers.push({
          urls: turnServer.urls,
          username: turnServer.username,
          credential: turnServer.credential
        })
      })
    }

    // Add STUN servers (always included, or as fallback)
    if (!config.enabled || config.fallbackToSTUN) {
      servers.push(...DEFAULT_STUN_SERVERS)
    }

    return servers
  }, [config])

  // Save configuration to localStorage
  const saveConfig = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    } catch (err) {
      console.error('Failed to save TURN config:', err)
      setError('Failed to save configuration')
    }
  }, [config])

  // Load configuration from localStorage
  const loadConfig = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsedConfig = JSON.parse(saved)
        setConfig({ ...DEFAULT_CONFIG, ...parsedConfig })
      }
    } catch (err) {
      console.error('Failed to load TURN config:', err)
      setError('Failed to load configuration')
      setConfig(DEFAULT_CONFIG)
    }
  }, [])

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    setConfig(DEFAULT_CONFIG)
    setTestResults([])
    setError(null)
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (err) {
      console.error('Failed to clear TURN config:', err)
    }
  }, [])

  // Auto-save configuration when it changes
  useEffect(() => {
    saveConfig()
  }, [saveConfig])

  // Load configuration on mount
  useEffect(() => {
    loadConfig()
  }, [])

  return {
    config,
    isTestingConnection,
    testResults,
    error,
    
    updateConfig,
    addTURNServer,
    removeTURNServer,
    updateTURNServer,
    
    testTURNServer,
    testAllServers,
    
    saveConfig,
    loadConfig,
    resetToDefaults,
    
    getICEServers
  }
}