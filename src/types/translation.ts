/**
 * TypeScript type definitions for The HIVE translation system
 */

export interface Language {
  code: string;
  name: string;
  flag: string;
  nativeName?: string;
}

export interface Voice {
  id: string;
  name: string;
  language: string;
  gender: 'male' | 'female' | 'neutral';
  description?: string;
  isDefault?: boolean;
}

export interface Caption {
  id: string;
  text: string;
  speakerName: string;
  originalLanguage: string;
  translatedText?: string;
  targetLanguage?: string;
  timestamp: number;
  isStable: boolean;
  confidence: number;
  wordStability?: Record<string, number>;
}

export interface TranslationPreference {
  userId: string;
  sourceLanguage: string;
  targetLanguages: string[];
  preferredVoice: Record<string, string>;
  autoDetect: boolean;
}

export interface TranslationMetrics {
  ttft_ms?: number; // Time to first translated audio
  caption_latency_ms?: number;
  processing_time_ms: number;
  confidence: number;
  retraction_rate?: number;
}

export interface TranslationSession {
  sessionId: string;
  participantId: string;
  sourceLanguage: string;
  targetLanguages: string[];
  startTime: number;
  endTime?: number;
  captions: Caption[];
  metrics: TranslationMetrics[];
}

export type TranslationMode = 'always' | 'push' | 'off';

export interface TranslationState {
  isEnabled: boolean;
  mode: TranslationMode;
  sourceLanguage: string;
  targetLanguage: string;
  selectedVoice: string;
  currentLatency?: number;
  isTranslating: boolean;
  error?: string;
}

export interface AudioChunk {
  data: ArrayBuffer;
  timestamp: number;
  sampleRate: number;
  channels: number;
}

export interface STTResult {
  text: string;
  confidence: number;
  detectedLanguage: string;
  isFinal: boolean;
  timestamp: number;
  processingTimeMs: number;
  words?: Array<{
    word: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

export interface MTResult {
  text: string;
  confidence: number;
  sourceLanguage: string;
  targetLanguage: string;
  processingTimeMs: number;
  modelUsed: string;
  contextUsed: boolean;
}

export interface TTSResult {
  audioData: Float32Array;
  sampleRate: number;
  voiceId: string;
  language: string;
  processingTimeMs: number;
  ttftMs?: number;
  isFinal: boolean;
}

export interface LiveKitParticipant {
  sid: string;
  identity: string;
  name?: string;
  audioTrack?: MediaStreamTrack;
  isTranslationEnabled: boolean;
  sourceLanguage?: string;
  targetLanguages: string[];
}

export interface TranslationRoom {
  name: string;
  participants: LiveKitParticipant[];
  translatorWorkers: string[];
  supportedLanguages: string[];
  isActive: boolean;
}

// Event types for translation system
export interface TranslationEvents {
  'translation-started': { sessionId: string; sourceLanguage: string; targetLanguage: string };
  'translation-completed': { sessionId: string; result: MTResult };
  'caption-received': { sessionId: string; caption: Caption };
  'audio-received': { sessionId: string; audio: TTSResult };
  'translation-error': { sessionId: string; error: string };
  'latency-warning': { sessionId: string; latency: number };
  'slo-violation': { type: 'ttft' | 'caption' | 'retraction'; value: number; threshold: number };
}

// Configuration interfaces
export interface ServiceConfig {
  sttServiceUrl: string;
  mtServiceUrl: string;
  ttsServiceUrl: string;
  livekitUrl: string;
  livekitApiKey: string;
}

export interface PerformanceConfig {
  chunkDurationMs: number;
  contextLength: number;
  ttftTargetMs: number;
  captionLatencyTargetMs: number;
  maxRetractionRate: number;
}

export interface UIConfig {
  showOriginalCaptions: boolean;
  showTranslatedCaptions: boolean;
  maxVisibleCaptions: number;
  stableWordThreshold: number;
  autoScrollCaptions: boolean;
  enableKeyboardShortcuts: boolean;
}

// Utility types
export type SupportedLanguageCode = 
  | 'en' | 'es' | 'fr' | 'de' | 'it' | 'pt' 
  | 'ar' | 'zh' | 'ja' | 'ko' | 'hi' | 'ru';

export type TranslationQuality = 'fast' | 'balanced' | 'quality';

export type VoiceGender = 'male' | 'female' | 'neutral';

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: number;
}

export interface TranslationApiResponse extends ApiResponse<MTResult> {
  processingTimeMs: number;
  sourceLanguage: string;
  targetLanguage: string;
}

export interface VoiceListResponse extends ApiResponse<Voice[]> {
  availableLanguages: string[];
  totalVoices: number;
}

export interface TranslationStatusResponse extends ApiResponse<{
  isActive: boolean;
  currentSessions: number;
  averageLatency: number;
  sloCompliance: {
    ttft: number;
    captions: number;
    retractions: number;
  };
}> {}

// Hook return types
export interface UseTranslationReturn {
  state: TranslationState;
  captions: Caption[];
  currentSession?: TranslationSession;
  startTranslation: (sourceLanguage: string, targetLanguage: string) => void;
  stopTranslation: () => void;
  setMode: (mode: TranslationMode) => void;
  setTargetLanguage: (language: string) => void;
  setVoice: (voiceId: string) => void;
  clearCaptions: () => void;
  exportSession: () => TranslationSession | null;
}

export interface UseLanguagePreferencesReturn {
  preferences: TranslationPreference;
  availableLanguages: Language[];
  availableVoices: Voice[];
  updatePreference: (updates: Partial<TranslationPreference>) => void;
  getVoicesForLanguage: (languageCode: string) => Voice[];
  resetToDefaults: () => void;
  addTargetLanguage: (languageCode: string) => void;
  removeTargetLanguage: (languageCode: string) => void;
  setVoiceForLanguage: (languageCode: string, voiceId: string) => void;
  getLanguageByCode: (code: string) => Language | undefined;
  getVoiceById: (id: string) => Voice | undefined;
  getPreferredVoiceForLanguage: (languageCode: string) => Voice | undefined;
}