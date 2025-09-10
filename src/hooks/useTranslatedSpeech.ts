import { useState, useCallback } from 'react'
import { useSpeechRecognition } from './useSpeechRecognition'
import { translationService, type TranslationResult } from '../services/translationService'
import type { TranscriptionData } from '../types/call'

interface TranslatedSpeechHook {
  startListening: () => void
  stopListening: () => void
  isListening: boolean
  transcript: string
  translatedText: string
  detectedLanguage: string
  targetLanguage: string
  setTargetLanguage: (lang: string) => void
  error: string | null
  isSupported: boolean
  transcriptHistory: TranscriptionData[]
  clearHistory: () => void
  translationLatency: number
  translationConfidence: number
  isServiceConnected: boolean
}

export const useTranslatedSpeech = (
  initialTargetLanguage: string = 'es-ES'
): TranslatedSpeechHook => {
  const [translatedText, setTranslatedText] = useState('')
  const [detectedLanguage, setDetectedLanguage] = useState('en-US')
  const [targetLanguage, setTargetLanguage] = useState(initialTargetLanguage)
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptionData[]>([])
  const [translationLatency, setTranslationLatency] = useState(0)
  const [translationConfidence, setTranslationConfidence] = useState(0)
  const [isServiceConnected, setIsServiceConnected] = useState(false)

  const handleTranscript = useCallback(async (data: TranscriptionData) => {
    // Add to history
    setTranscriptHistory(prev => [...prev, data])

    if (data.isFinal && data.text.trim()) {
      try {
        // Detect language
        const detected = await translationService.detectLanguage(data.text)
        setDetectedLanguage(detected)

        // Check service connection status
        setIsServiceConnected(translationService.isConnected())
        
        // Only translate if the detected language is different from target
        if (detected !== targetLanguage) {
          const translationStart = performance.now()
          const translationResult: TranslationResult = await translationService.translate(
            data.text, 
            detected, 
            targetLanguage
          )
          const translationEnd = performance.now()
          
          // Update metrics for SLO monitoring
          setTranslationLatency(Math.round(translationEnd - translationStart))
          setTranslationConfidence(translationResult.confidence)
          setTranslatedText(translationResult.text)
          
          // Log SLO compliance
          const latencyMs = Math.round(translationEnd - translationStart)
          if (latencyMs > 100) {
            console.warn(`⚠️ Translation SLO violation: ${latencyMs}ms > 100ms target`)
          }
          
          // Update history with translation result
          setTranscriptHistory(prev => 
            prev.map(item => 
              item.timestamp === data.timestamp 
                ? { 
                    ...item, 
                    translation: translationResult.text,
                    translationLatency: latencyMs,
                    translationConfidence: translationResult.confidence
                  } 
                : item
            )
          )
        } else {
          setTranslatedText(data.text) // No translation needed
          setTranslationLatency(0)
          setTranslationConfidence(1.0)
        }
      } catch (error) {
        console.error('Translation error:', error)
        setTranslatedText(data.text) // Fallback to original text
      }
    }
  }, [targetLanguage])

  const {
    isListening,
    transcript,
    startListening,
    stopListening,
    isSupported,
    error
  } = useSpeechRecognition(detectedLanguage, handleTranscript)

  const clearHistory = useCallback(() => {
    setTranscriptHistory([])
    setTranslatedText('')
  }, [])

  return {
    startListening,
    stopListening,
    isListening,
    transcript,
    translatedText,
    detectedLanguage,
    targetLanguage,
    setTargetLanguage,
    error,
    isSupported,
    transcriptHistory,
    clearHistory,
    translationLatency,
    translationConfidence,
    isServiceConnected
  }
}