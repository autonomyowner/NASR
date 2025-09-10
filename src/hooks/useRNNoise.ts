import { useState, useCallback, useRef, useEffect } from 'react'

export interface RNNoiseSettings {
  enabled: boolean
  fallbackToBuiltIn: boolean
  vadThreshold: number // Voice Activity Detection threshold (0-1)
}

export interface UseRNNoiseReturn {
  isSupported: boolean
  isLoaded: boolean
  isProcessing: boolean
  settings: RNNoiseSettings
  error: string | null
  cpuUsage: number | null
  
  // Actions
  loadRNNoise: () => Promise<void>
  enableProcessing: (inputStream: MediaStream) => Promise<MediaStream | null>
  disableProcessing: () => void
  updateSettings: (newSettings: Partial<RNNoiseSettings>) => void
  
  // Status
  getStatus: () => string
  getPerformanceMetrics: () => {
    avgProcessingTime: number
    maxProcessingTime: number
    samplesProcessed: number
  }
}

// RNNoise processor worklet code as string (will be loaded dynamically)
const RNNOISE_PROCESSOR_CODE = `
class RNNoiseProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    
    this.bufferSize = 480; // 10ms at 48kHz
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
    this.vadThreshold = options.processorOptions?.vadThreshold || 0.5;
    this.isNoiseSuppressionEnabled = true;
    this.processingTimes = [];
    this.maxMetrics = 100; // Keep last 100 measurements
    
    // Mock RNNoise state (in real implementation, this would be WASM)
    this.rnnoiseState = null;
    this.isWasmLoaded = false;
    
    this.port.onmessage = (event) => {
      const { type, data } = event.data;
      
      switch (type) {
        case 'init-wasm':
          this.initWasm(data);
          break;
        case 'update-settings':
          this.updateSettings(data);
          break;
        case 'get-metrics':
          this.sendMetrics();
          break;
      }
    };
  }
  
  initWasm(wasmData) {
    try {
      // In a real implementation, this would initialize the WASM module
      // For this example, we'll simulate the initialization
      console.log('Initializing RNNoise WASM (simulated)');
      this.isWasmLoaded = true;
      this.port.postMessage({ type: 'wasm-loaded', success: true });
    } catch (error) {
      this.port.postMessage({ type: 'wasm-error', error: error.message });
    }
  }
  
  updateSettings(settings) {
    if (settings.vadThreshold !== undefined) {
      this.vadThreshold = settings.vadThreshold;
    }
    if (settings.enabled !== undefined) {
      this.isNoiseSuppressionEnabled = settings.enabled;
    }
  }
  
  sendMetrics() {
    const avgTime = this.processingTimes.length > 0 
      ? this.processingTimes.reduce((a, b) => a + b, 0) / this.processingTimes.length 
      : 0;
    const maxTime = this.processingTimes.length > 0 
      ? Math.max(...this.processingTimes) 
      : 0;
    
    this.port.postMessage({
      type: 'metrics',
      data: {
        avgProcessingTime: avgTime,
        maxProcessingTime: maxTime,
        samplesProcessed: this.bufferIndex,
        cpuUsage: avgTime / 10.0 // Rough CPU usage estimate (10ms budget)
      }
    });
  }
  
  // Simulate RNNoise processing
  processAudioWithRNNoise(audioBuffer) {
    if (!this.isWasmLoaded || !this.isNoiseSuppressionEnabled) {
      return audioBuffer;
    }
    
    const startTime = performance.now();
    
    // Simulate processing - in real implementation, this would call WASM
    // For now, we'll apply a simple high-pass filter as a placeholder
    const processed = new Float32Array(audioBuffer.length);
    let prevSample = 0;
    const cutoff = 0.95; // High-pass filter coefficient
    
    for (let i = 0; i < audioBuffer.length; i++) {
      processed[i] = audioBuffer[i] - prevSample * cutoff;
      prevSample = audioBuffer[i];
    }
    
    // Voice Activity Detection simulation
    const energy = audioBuffer.reduce((sum, sample) => sum + Math.abs(sample), 0) / audioBuffer.length;
    if (energy < this.vadThreshold * 0.1) {
      // Apply more aggressive suppression for low-energy frames
      for (let i = 0; i < processed.length; i++) {
        processed[i] *= 0.1;
      }
    }
    
    const processingTime = performance.now() - startTime;
    this.processingTimes.push(processingTime);
    
    // Keep only recent measurements
    if (this.processingTimes.length > this.maxMetrics) {
      this.processingTimes.shift();
    }
    
    return processed;
  }
  
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    
    if (input.length === 0) return true;
    
    const inputChannel = input[0];
    const outputChannel = output[0];
    
    // Buffer audio for processing in blocks
    for (let i = 0; i < inputChannel.length; i++) {
      this.buffer[this.bufferIndex] = inputChannel[i];
      this.bufferIndex++;
      
      if (this.bufferIndex >= this.bufferSize) {
        // Process buffer
        const processedBuffer = this.processAudioWithRNNoise(this.buffer);
        
        // Copy processed audio to output (with delay compensation)
        const outputStartIndex = Math.max(0, i - this.bufferSize + 1);
        const copyLength = Math.min(this.bufferSize, inputChannel.length - outputStartIndex);
        
        for (let j = 0; j < copyLength; j++) {
          if (outputStartIndex + j < outputChannel.length) {
            outputChannel[outputStartIndex + j] = processedBuffer[j];
          }
        }
        
        this.bufferIndex = 0;
      }
    }
    
    // For samples not yet processed, pass through
    for (let i = 0; i < inputChannel.length; i++) {
      if (outputChannel[i] === undefined) {
        outputChannel[i] = inputChannel[i];
      }
    }
    
    return true;
  }
}

registerProcessor('rnnoise-processor', RNNoiseProcessor);
`;

const DEFAULT_SETTINGS: RNNoiseSettings = {
  enabled: false,
  fallbackToBuiltIn: true,
  vadThreshold: 0.5
}

export const useRNNoise = (): UseRNNoiseReturn => {
  const [isSupported, setIsSupported] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [settings, setSettings] = useState<RNNoiseSettings>(DEFAULT_SETTINGS)
  const [error, setError] = useState<string | null>(null)
  const [cpuUsage, setCpuUsage] = useState<number | null>(null)

  const audioContextRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const destinationRef = useRef<MediaStreamAudioDestinationNode | null>(null)
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const performanceMetricsRef = useRef({
    avgProcessingTime: 0,
    maxProcessingTime: 0,
    samplesProcessed: 0
  })

  // Check if AudioWorklet is supported
  useEffect(() => {
    const checkSupport = () => {
      const hasAudioWorklet = typeof AudioWorklet !== 'undefined' && 
                             typeof AudioContext !== 'undefined' &&
                             'audioWorklet' in AudioContext.prototype
      
      const hasWasm = typeof WebAssembly !== 'undefined'
      
      setIsSupported(hasAudioWorklet && hasWasm)
      
      if (!hasAudioWorklet) {
        setError('AudioWorklet not supported in this browser')
      } else if (!hasWasm) {
        setError('WebAssembly not supported in this browser')
      }
    }

    checkSupport()
  }, [])

  // Load RNNoise WASM and set up AudioWorklet
  const loadRNNoise = useCallback(async (): Promise<void> => {
    if (!isSupported) {
      throw new Error('RNNoise is not supported in this browser')
    }

    if (isLoaded) return

    try {
      setError(null)
      
      // Initialize AudioContext
      const AudioContextClass = AudioContext || (window as any).webkitAudioContext
      const audioContext = new AudioContextClass({
        sampleRate: 48000,
        latencyHint: 'interactive'
      })
      audioContextRef.current = audioContext

      // Resume context if needed
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }

      // Create blob URL for the worklet processor
      const processorBlob = new Blob([RNNOISE_PROCESSOR_CODE], { type: 'application/javascript' })
      const processorURL = URL.createObjectURL(processorBlob)

      // Load the worklet module
      await audioContext.audioWorklet.addModule(processorURL)

      // Clean up blob URL
      URL.revokeObjectURL(processorURL)

      // In a real implementation, we would also load the RNNoise WASM here
      // For this example, we'll simulate a delay
      await new Promise(resolve => setTimeout(resolve, 500))

      setIsLoaded(true)
      console.log('RNNoise loaded successfully (simulated)')
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load RNNoise'
      setError(errorMessage)
      console.error('Failed to load RNNoise:', err)
      throw err
    }
  }, [isSupported, isLoaded])

  // Enable RNNoise processing on input stream
  const enableProcessing = useCallback(async (inputStream: MediaStream): Promise<MediaStream | null> => {
    if (!isLoaded || !audioContextRef.current) {
      if (settings.fallbackToBuiltIn) {
        console.warn('RNNoise not loaded, falling back to built-in noise suppression')
        return inputStream
      }
      throw new Error('RNNoise is not loaded')
    }

    if (isProcessing) {
      console.warn('RNNoise processing already enabled')
      return destinationRef.current?.stream || null
    }

    try {
      setError(null)
      const audioContext = audioContextRef.current

      // Create source node from input stream
      const sourceNode = audioContext.createMediaStreamSource(inputStream)
      sourceNodeRef.current = sourceNode

      // Create destination node for output stream
      const destinationNode = audioContext.createMediaStreamDestination()
      destinationRef.current = destinationNode

      // Create RNNoise worklet node
      const workletNode = new AudioWorkletNode(audioContext, 'rnnoise-processor', {
        processorOptions: {
          vadThreshold: settings.vadThreshold
        }
      })
      workletNodeRef.current = workletNode

      // Set up message handling
      workletNode.port.onmessage = (event) => {
        const { type, data, error: workletError } = event.data

        switch (type) {
          case 'wasm-loaded':
            console.log('RNNoise WASM initialized in worklet')
            break
          case 'wasm-error':
            console.error('RNNoise WASM error:', workletError)
            setError(`WASM error: ${workletError}`)
            break
          case 'metrics':
            performanceMetricsRef.current = data
            setCpuUsage(data.cpuUsage)
            break
        }
      }

      // Initialize WASM in worklet (simulated)
      workletNode.port.postMessage({
        type: 'init-wasm',
        data: {} // In real implementation, this would contain WASM binary
      })

      // Connect nodes: source -> worklet -> destination
      sourceNode.connect(workletNode)
      workletNode.connect(destinationNode)

      // Start metrics collection
      metricsIntervalRef.current = setInterval(() => {
        if (workletNodeRef.current) {
          workletNodeRef.current.port.postMessage({ type: 'get-metrics' })
        }
      }, 1000)

      setIsProcessing(true)
      
      return destinationNode.stream

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to enable processing'
      setError(errorMessage)
      console.error('Failed to enable RNNoise processing:', err)
      
      if (settings.fallbackToBuiltIn) {
        console.warn('Falling back to built-in noise suppression')
        return inputStream
      }
      
      return null
    }
  }, [isLoaded, isProcessing, settings])

  // Disable RNNoise processing
  const disableProcessing = useCallback(() => {
    if (!isProcessing) return

    try {
      // Stop metrics collection
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current)
        metricsIntervalRef.current = null
      }

      // Disconnect and clean up nodes
      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect()
        sourceNodeRef.current = null
      }

      if (workletNodeRef.current) {
        workletNodeRef.current.disconnect()
        workletNodeRef.current = null
      }

      if (destinationRef.current) {
        destinationRef.current = null
      }

      setIsProcessing(false)
      setCpuUsage(null)
      
    } catch (err) {
      console.error('Error disabling RNNoise processing:', err)
      setError(err instanceof Error ? err.message : 'Failed to disable processing')
    }
  }, [isProcessing])

  // Update settings
  const updateSettings = useCallback((newSettings: Partial<RNNoiseSettings>) => {
    const updatedSettings = { ...settings, ...newSettings }
    setSettings(updatedSettings)

    // Update worklet settings if processing is active
    if (isProcessing && workletNodeRef.current) {
      workletNodeRef.current.port.postMessage({
        type: 'update-settings',
        data: updatedSettings
      })
    }
  }, [settings, isProcessing])

  // Get status string
  const getStatus = useCallback((): string => {
    if (!isSupported) return 'Not Supported'
    if (error) return `Error: ${error}`
    if (!isLoaded) return 'Not Loaded'
    if (isProcessing) return 'Processing'
    return 'Ready'
  }, [isSupported, error, isLoaded, isProcessing])

  // Get performance metrics
  const getPerformanceMetrics = useCallback(() => {
    return performanceMetricsRef.current
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disableProcessing()
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [])

  return {
    isSupported,
    isLoaded,
    isProcessing,
    settings,
    error,
    cpuUsage,
    
    loadRNNoise,
    enableProcessing,
    disableProcessing,
    updateSettings,
    
    getStatus,
    getPerformanceMetrics
  }
}