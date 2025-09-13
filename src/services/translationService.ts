export interface TranslationResult {
  text: string
  confidence: number
  detectedSourceLang?: string
  processing_time_ms: number
}

export interface TranslationService {
  translate: (text: string, fromLang: string, toLang: string) => Promise<TranslationResult>
  detectLanguage: (text: string) => Promise<string>
  getSupportedLanguages: () => string[]
  isConnected: () => boolean
  connect: () => Promise<void>
  disconnect: () => void
}

// Production Translation Service connecting to backend MT service
// TODO: Uncomment for Phase 2 when translation is needed
/*
class ProductionTranslationService implements TranslationService {
  private ws: WebSocket | null = null
  private pendingRequests = new Map<string, { resolve: Function, reject: Function }>()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private connected = false
  
  private supportedLanguages = [
    'en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-PT', 
    'ar-SA', 'zh-CN', 'ja-JP', 'ko-KR', 'hi-IN', 'ru-RU',
    'nl-NL', 'sv-SE', 'pl-PL', 'tr-TR'
  ]

  private getMTServiceUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = process.env.NODE_ENV === 'production' 
      ? window.location.host 
      : 'localhost:8002'
    return `${protocol}//${host}/ws/translate`
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const url = this.getMTServiceUrl()
        console.log(`🔗 Connecting to MT service: ${url}`)
        
        this.ws = new WebSocket(url)
        
        this.ws.onopen = () => {
          console.log('✅ Connected to MT service')
          this.connected = true
          this.reconnectAttempts = 0
          resolve()
        }
        
        this.ws.onmessage = (event) => {
          try {
            const response = JSON.parse(event.data)
            const requestId = response.request_id
            
            if (this.pendingRequests.has(requestId)) {
              const { resolve } = this.pendingRequests.get(requestId)!
              this.pendingRequests.delete(requestId)
              resolve(response)
            }
          } catch (error) {
            console.error('❌ Error parsing MT service response:', error)
          }
        }
        
        this.ws.onclose = () => {
          console.log('🔌 Disconnected from MT service')
          this.connected = false
          this.attemptReconnect()
        }
        
        this.ws.onerror = (error) => {
          console.error('❌ MT service WebSocket error:', error)
          this.connected = false
          if (this.reconnectAttempts === 0) {
            reject(error)
          }
        }
        
        // Connection timeout
        setTimeout(() => {
          if (!this.connected) {
            reject(new Error('Connection timeout to MT service'))
          }
        }, 5000)
        
      } catch (error) {
        reject(error)
      }
    })
  }

  private async attemptReconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnection attempts reached for MT service')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`🔄 Attempting to reconnect to MT service (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`)
    
    setTimeout(() => {
      this.connect().catch(() => {
        // Retry will be handled by onclose event
      })
    }, delay)
  }

  async translate(text: string, fromLang: string, toLang: string): Promise<TranslationResult> {
    if (!this.connected || !this.ws) {
      // Fallback to mock translation if service unavailable
      console.warn('⚠️ MT service not connected, using fallback translation')
      return {
        text: `[${toLang.split('-')[0].toUpperCase()}] ${text}`,
        confidence: 0.7,
        detectedSourceLang: fromLang,
        processing_time_ms: 100
      }
    }

    const requestId = `translate-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const startTime = performance.now()
    
    return new Promise((resolve, reject) => {
      const request = {
        request_id: requestId,
        type: 'translate',
        text: text.trim(),
        source_lang: this.normalizeLanguageCode(fromLang),
        target_lang: this.normalizeLanguageCode(toLang),
        context: [], // Add conversation context for rolling context
        options: {
          quality_mode: 'fast', // or 'quality' for higher accuracy
          preserve_formatting: true,
          handle_code_switching: true
        }
      }

      this.pendingRequests.set(requestId, { 
        resolve: (response: any) => {
          const processingTime = performance.now() - startTime
          resolve({
            text: response.translated_text || response.text,
            confidence: response.confidence || 0.9,
            detectedSourceLang: response.detected_language || fromLang,
            processing_time_ms: Math.round(processingTime)
          })
        }, 
        reject 
      })

      // Request timeout (SLO: 100ms target)
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId)
          reject(new Error('Translation request timeout (>100ms SLO violation)'))
        }
      }, 200) // Allow some buffer over 100ms SLO

      this.ws!.send(JSON.stringify(request))
    })
  }

  async detectLanguage(text: string): Promise<string> {
    if (!this.connected || !this.ws) {
      // Fallback language detection using heuristics
      if (/[ñáéíóúü]/i.test(text)) return 'es-ES'
      if (/[àâäéèêëïîôöùûüÿç]/i.test(text)) return 'fr-FR'
      if (/[äöüß]/i.test(text)) return 'de-DE'
      if (/[\u0600-\u06FF]/i.test(text)) return 'ar-SA'
      if (/[\u4e00-\u9fff]/i.test(text)) return 'zh-CN'
      return 'en-US'
    }

    const requestId = `detect-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    return new Promise((resolve, reject) => {
      const request = {
        request_id: requestId,
        type: 'detect_language',
        text: text.trim()
      }

      this.pendingRequests.set(requestId, { 
        resolve: (response: any) => {
          resolve(response.detected_language || 'en-US')
        }, 
        reject 
      })

      // Request timeout
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId)
          reject(new Error('Language detection timeout'))
        }
      }, 5000)

      this.ws!.send(JSON.stringify(request))
    })
  }

  private normalizeLanguageCode(lang: string): string {
    const langMap: { [key: string]: string } = {
      'en-US': 'en',
      'es-ES': 'es',
      'fr-FR': 'fr',
      'de-DE': 'de',
      'it-IT': 'it',
      'pt-PT': 'pt',
      'ar-SA': 'ar',
      'zh-CN': 'zh',
      'ja-JP': 'ja',
      'ko-KR': 'ko',
      'hi-IN': 'hi',
      'ru-RU': 'ru',
      'nl-NL': 'nl',
      'sv-SE': 'sv',
      'pl-PL': 'pl',
      'tr-TR': 'tr'
    }
    return langMap[lang] || lang.split('-')[0]
  }

  getSupportedLanguages(): string[] {
    return this.supportedLanguages
  }

  isConnected(): boolean {
    return this.connected
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
    this.pendingRequests.clear()
  }
}
*/

// Mock Translation Service for Phase 1 (no actual translation needed)
class MockTranslationService implements TranslationService {
  private supportedLanguages = [
    'en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-PT', 
    'ar-SA', 'zh-CN', 'ja-JP', 'ko-KR', 'hi-IN', 'ru-RU',
    'nl-NL', 'sv-SE', 'pl-PL', 'tr-TR'
  ]

  async translate(text: string, fromLang: string, _toLang: string): Promise<TranslationResult> {
    // Mock translation - just return the original text with mock data
    return {
      text: `[Mock Translation] ${text}`,
      confidence: 0.95,
      detectedSourceLang: fromLang,
      processing_time_ms: 50
    }
  }

  async detectLanguage(_text: string): Promise<string> {
    // Mock language detection - return English by default
    return 'en-US'
  }

  getSupportedLanguages(): string[] {
    return this.supportedLanguages
  }

  isConnected(): boolean {
    // Mock service is always "connected"
    return true
  }

  async connect(): Promise<void> {
    // Mock connection - always succeeds
    console.log('🔧 Mock translation service connected (Phase 1)')
  }

  disconnect(): void {
    // Mock disconnect - no action needed
    console.log('🔧 Mock translation service disconnected')
  }
}

// Create global service instance - use mock service for Phase 1 (no translation needed)
const mockService = new MockTranslationService()

// Export the service instance
export const translationService: TranslationService = mockService

// For Phase 2+ when translation is needed, switch to:
// export const translationService: TranslationService = new ProductionTranslationService()