import { useState, useEffect, useCallback, useRef } from 'react'
import type { TranscriptionData } from '../types/call'

interface SpeechRecognitionHook {
  isListening: boolean
  transcript: string
  interimTranscript: string
  startListening: () => void
  stopListening: () => void
  isSupported: boolean
  error: string | null
}

export const useSpeechRecognition = (
  language: string = 'en-US',
  onTranscript?: (data: TranscriptionData) => void
): SpeechRecognitionHook => {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  
  const recognition = useRef<SpeechRecognition | null>(null)
  const isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window

  // Initialize speech recognition
  useEffect(() => {
    if (!isSupported) return

    const SpeechRecognitionConstructor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    recognition.current = new SpeechRecognitionConstructor() as SpeechRecognition

    recognition.current.continuous = true
    recognition.current.interimResults = true
    recognition.current.lang = language

    recognition.current.onstart = () => {
      setIsListening(true)
      setError(null)
    }

    recognition.current.onresult = (event: SpeechRecognitionEvent) => {
      let interimTranscript = ''
      let finalTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptPart = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += transcriptPart
        } else {
          interimTranscript += transcriptPart
        }
      }

      setInterimTranscript(interimTranscript)
      
      if (finalTranscript) {
        setTranscript(prev => prev + finalTranscript)
        
        // Call callback with transcription data
        if (onTranscript) {
          onTranscript({
            text: finalTranscript,
            language,
            timestamp: Date.now(),
            isFinal: true
          })
        }
      } else if (interimTranscript && onTranscript) {
        // Send interim results too
        onTranscript({
          text: interimTranscript,
          language,
          timestamp: Date.now(),
          isFinal: false
        })
      }
    }

    recognition.current.onerror = (event: SpeechRecognitionErrorEvent) => {
      setError(`Speech recognition error: ${event.error}`)
      setIsListening(false)
    }

    recognition.current.onend = () => {
      setIsListening(false)
    }

    return () => {
      if (recognition.current) {
        recognition.current.stop()
      }
    }
  }, [language, isSupported, onTranscript])

  const startListening = useCallback(() => {
    if (!isSupported) {
      setError('Speech recognition not supported in this browser')
      return
    }

    if (recognition.current && !isListening) {
      try {
        recognition.current.start()
      } catch {
        setError('Could not start speech recognition')
      }
    }
  }, [isSupported, isListening])

  const stopListening = useCallback(() => {
    if (recognition.current && isListening) {
      recognition.current.stop()
    }
  }, [isListening])

  // Auto-restart recognition if it stops during a call
  useEffect(() => {
    if (isListening && recognition.current) {
      const checkRecognition = setInterval(() => {
        if (!isListening && recognition.current) {
          try {
            recognition.current.start()
          } catch {
            console.warn('Could not restart speech recognition')
          }
        }
      }, 1000)

      return () => clearInterval(checkRecognition)
    }
  }, [isListening])

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    isSupported,
    error
  }
}