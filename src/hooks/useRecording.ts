import { useState, useRef, useCallback } from 'react'

export type RecordingSource = 'local' | 'remote' | 'mixed'
export type RecordingState = 'idle' | 'recording' | 'paused' | 'stopped'

export interface RecordingOptions {
  source: RecordingSource
  mimeType?: string
  videoBitsPerSecond?: number
  audioBitsPerSecond?: number
}

export interface RecordingInfo {
  startTime: Date
  duration: number
  size: number
  source: RecordingSource
  fileName: string
}

export interface UseRecordingReturn {
  isRecording: boolean
  isPaused: boolean
  recordingState: RecordingState
  currentRecording: RecordingInfo | null
  recordings: RecordingInfo[]
  error: string | null
  isSupported: boolean
  
  // Actions
  startRecording: (options?: RecordingOptions) => Promise<void>
  stopRecording: () => Promise<void>
  pauseRecording: () => void
  resumeRecording: () => void
  downloadRecording: (recording: RecordingInfo) => void
  deleteRecording: (index: number) => void
  clearAllRecordings: () => void
  
  // Configuration
  getSupportedMimeTypes: () => string[]
  setRecordingOptions: (options: Partial<RecordingOptions>) => void
}

export const useRecording = (
  localStream?: MediaStream,
  remoteStream?: MediaStream
): UseRecordingReturn => {
  const [recordingState, setRecordingState] = useState<RecordingState>('idle')
  const [currentRecording, setCurrentRecording] = useState<RecordingInfo | null>(null)
  const [recordings, setRecordings] = useState<RecordingInfo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [options, setOptions] = useState<RecordingOptions>({
    source: 'mixed',
    mimeType: 'audio/webm;codecs=opus',
    audioBitsPerSecond: 128000
  })

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startTimeRef = useRef<Date | null>(null)
  const recordedBlobsRef = useRef<Map<string, Blob>>(new Map())

  const isSupported = typeof MediaRecorder !== 'undefined'
  const isRecording = recordingState === 'recording'
  const isPaused = recordingState === 'paused'

  // Generate filename with timestamp and peer info
  const generateFileName = useCallback((source: RecordingSource): string => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')
    const dateStr = timestamp[0]
    const timeStr = timestamp[1].split('.')[0]
    return `call-${source}-${dateStr}-${timeStr}.webm`
  }, [])

  // Get supported MIME types
  const getSupportedMimeTypes = useCallback((): string[] => {
    if (!isSupported) return []
    
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/ogg'
    ]
    
    return types.filter(type => MediaRecorder.isTypeSupported(type))
  }, [isSupported])

  // Create mixed stream from local and remote
  const createMixedStream = useCallback((): MediaStream | null => {
    if (!localStream || !remoteStream) return null

    try {
      const audioContext = new AudioContext()
      const destination = audioContext.createMediaStreamDestination()
      
      // Create sources for local and remote streams
      if (localStream.getAudioTracks().length > 0) {
        const localSource = audioContext.createMediaStreamSource(localStream)
        localSource.connect(destination)
      }
      
      if (remoteStream.getAudioTracks().length > 0) {
        const remoteSource = audioContext.createMediaStreamSource(remoteStream)
        remoteSource.connect(destination)
      }
      
      return destination.stream
    } catch (err) {
      console.error('Failed to create mixed stream:', err)
      return null
    }
  }, [localStream, remoteStream])

  // Get stream based on recording source
  const getRecordingStream = useCallback((source: RecordingSource): MediaStream | null => {
    switch (source) {
      case 'local':
        return localStream || null
      case 'remote':
        return remoteStream || null
      case 'mixed':
        return createMixedStream()
      default:
        return null
    }
  }, [localStream, remoteStream, createMixedStream])

  // Start recording
  const startRecording = useCallback(async (recordingOptions?: RecordingOptions): Promise<void> => {
    if (!isSupported) {
      setError('MediaRecorder is not supported in this browser')
      return
    }

    if (recordingState !== 'idle') {
      setError('Recording is already in progress')
      return
    }

    const currentOptions = { ...options, ...recordingOptions }
    const stream = getRecordingStream(currentOptions.source)

    if (!stream) {
      setError(`No ${currentOptions.source} stream available for recording`)
      return
    }

    if (stream.getAudioTracks().length === 0) {
      setError('No audio tracks found in the stream')
      return
    }

    try {
      // Ensure MIME type is supported
      const mimeType = getSupportedMimeTypes().find(type => 
        type === currentOptions.mimeType
      ) || getSupportedMimeTypes()[0]

      if (!mimeType) {
        setError('No supported audio recording format found')
        return
      }

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: currentOptions.audioBitsPerSecond
      })

      chunksRef.current = []
      startTimeRef.current = new Date()

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        const fileName = generateFileName(currentOptions.source)
        const endTime = new Date()
        const duration = startTimeRef.current ? 
          Math.floor((endTime.getTime() - startTimeRef.current.getTime()) / 1000) : 0

        const recordingInfo: RecordingInfo = {
          startTime: startTimeRef.current!,
          duration,
          size: blob.size,
          source: currentOptions.source,
          fileName
        }

        // Store the blob for download
        recordedBlobsRef.current.set(fileName, blob)

        setRecordings(prev => [...prev, recordingInfo])
        setCurrentRecording(null)
        setRecordingState('idle')
        setError(null)
      }

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event)
        setError('Recording failed due to an error')
        setRecordingState('idle')
        setCurrentRecording(null)
      }

      mediaRecorder.onstart = () => {
        const recordingInfo: RecordingInfo = {
          startTime: startTimeRef.current!,
          duration: 0,
          size: 0,
          source: currentOptions.source,
          fileName: generateFileName(currentOptions.source)
        }
        setCurrentRecording(recordingInfo)
        setRecordingState('recording')
        setError(null)
      }

      mediaRecorder.onpause = () => {
        setRecordingState('paused')
      }

      mediaRecorder.onresume = () => {
        setRecordingState('recording')
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start(1000) // Collect data every second

    } catch (err) {
      console.error('Failed to start recording:', err)
      setError(err instanceof Error ? err.message : 'Failed to start recording')
      setRecordingState('idle')
    }
  }, [isSupported, recordingState, options, getRecordingStream, getSupportedMimeTypes, generateFileName])

  // Stop recording
  const stopRecording = useCallback(async (): Promise<void> => {
    if (!mediaRecorderRef.current || recordingState === 'idle') {
      return
    }

    try {
      mediaRecorderRef.current.stop()
      setRecordingState('stopped')
    } catch (err) {
      console.error('Failed to stop recording:', err)
      setError('Failed to stop recording')
    }
  }, [recordingState])

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (!mediaRecorderRef.current || recordingState !== 'recording') {
      return
    }

    try {
      mediaRecorderRef.current.pause()
    } catch (err) {
      console.error('Failed to pause recording:', err)
      setError('Failed to pause recording')
    }
  }, [recordingState])

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (!mediaRecorderRef.current || recordingState !== 'paused') {
      return
    }

    try {
      mediaRecorderRef.current.resume()
    } catch (err) {
      console.error('Failed to resume recording:', err)
      setError('Failed to resume recording')
    }
  }, [recordingState])

  // Download recording
  const downloadRecording = useCallback((recording: RecordingInfo) => {
    const blob = recordedBlobsRef.current.get(recording.fileName)
    if (!blob) {
      setError('Recording data not found')
      return
    }

    try {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = recording.fileName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download recording:', err)
      setError('Failed to download recording')
    }
  }, [])

  // Delete recording
  const deleteRecording = useCallback((index: number) => {
    setRecordings(prev => {
      const recording = prev[index]
      if (recording) {
        recordedBlobsRef.current.delete(recording.fileName)
      }
      return prev.filter((_, i) => i !== index)
    })
  }, [])

  // Clear all recordings
  const clearAllRecordings = useCallback(() => {
    recordedBlobsRef.current.clear()
    setRecordings([])
  }, [])

  // Set recording options
  const setRecordingOptions = useCallback((newOptions: Partial<RecordingOptions>) => {
    setOptions(prev => ({ ...prev, ...newOptions }))
  }, [])

  return {
    isRecording,
    isPaused,
    recordingState,
    currentRecording,
    recordings,
    error,
    isSupported,
    
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    downloadRecording,
    deleteRecording,
    clearAllRecordings,
    
    getSupportedMimeTypes,
    setRecordingOptions
  }
}