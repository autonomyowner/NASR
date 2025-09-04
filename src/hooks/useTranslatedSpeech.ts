import { useState, useCallback } from 'react'
import { useSpeechRecognition } from './useSpeechRecognition'
import { translationService } from '../services/translationService'
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
}

export const useTranslatedSpeech = (
  initialTargetLanguage: string = 'es-ES'
): TranslatedSpeechHook => {
  const [translatedText, setTranslatedText] = useState('')
  const [detectedLanguage, setDetectedLanguage] = useState('en-US')
  const [targetLanguage, setTargetLanguage] = useState(initialTargetLanguage)
  const [transcriptHistory, setTranscriptHistory] = useState<TranscriptionData[]>([])

  const handleTranscript = useCallback(async (data: TranscriptionData) => {
    // Add to history
    setTranscriptHistory(prev => [...prev, data])

    if (data.isFinal && data.text.trim()) {
      try {
        // Detect language
        const detected = await translationService.detectLanguage(data.text)
        setDetectedLanguage(detected)

        // Only translate if the detected language is different from target
        if (detected !== targetLanguage) {
          const translation = await translationService.translate(
            data.text, 
            detected, 
            targetLanguage
          )
          
          setTranslatedText(translation)
          
          // Update history with translation
          setTranscriptHistory(prev => 
            prev.map(item => 
              item.timestamp === data.timestamp 
                ? { ...item, translation } 
                : item
            )
          )
        } else {
          setTranslatedText(data.text) // No translation needed
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
    clearHistory
  }
}