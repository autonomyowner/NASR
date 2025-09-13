/**
 * Translation State Management Hook
 * 
 * Centralized state management for translation features including mode,
 * preferences, captions, and real-time translation status.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { 
  TranslationState, 
  TranslationMode, 
  Caption, 
  TranslationSession
} from '../types/translation';

interface UseTranslationStateOptions {
  initialMode?: TranslationMode;
  initialTargetLanguage?: string;
  maxCaptions?: number;
  persistToStorage?: boolean;
  storageKey?: string;
}

interface UseTranslationStateReturn {
  // State
  state: TranslationState;
  captions: Caption[];
  session: TranslationSession | null;
  
  // Mode management
  setMode: (mode: TranslationMode) => void;
  toggleMode: () => void;
  
  // Language management
  setSourceLanguage: (language: string) => void;
  setTargetLanguage: (language: string) => void;
  setSelectedVoice: (voiceId: string) => void;
  
  // Caption management
  addCaption: (caption: Caption) => void;
  updateCaption: (id: string, updates: Partial<Caption>) => void;
  clearCaptions: () => void;
  
  // Session management
  startSession: (sourceLanguage: string, targetLanguages: string[]) => void;
  endSession: () => void;
  exportSession: () => TranslationSession | null;
  
  // Status management
  setTranslating: (isTranslating: boolean) => void;
  setError: (error: string | null) => void;
  setLatency: (latency: number) => void;
  
  // Utility functions
  getActiveSession: () => TranslationSession | null;
  getCaptionStats: () => {
    total: number;
    stable: number;
    averageConfidence: number;
  };
}

export const useTranslationState = (
  options: UseTranslationStateOptions = {}
): UseTranslationStateReturn => {
  const {
    initialMode = 'off',
    initialTargetLanguage = 'es',
    maxCaptions = 100,
    persistToStorage = true,
    storageKey = 'hive-translation-state'
  } = options;

  // Load initial state from storage
  const loadInitialState = useCallback((): TranslationState => {
    if (persistToStorage && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
          const parsedState = JSON.parse(stored);
          return {
            isEnabled: parsedState.isEnabled || false,
            mode: parsedState.mode || initialMode,
            sourceLanguage: parsedState.sourceLanguage || 'en',
            targetLanguage: parsedState.targetLanguage || initialTargetLanguage,
            selectedVoice: parsedState.selectedVoice || '',
            currentLatency: undefined,
            isTranslating: false,
            error: undefined
          };
        }
      } catch (error) {
        console.warn('Failed to load translation state from storage:', error);
      }
    }

    return {
      isEnabled: initialMode !== 'off',
      mode: initialMode,
      sourceLanguage: 'en',
      targetLanguage: initialTargetLanguage,
      selectedVoice: '',
      currentLatency: undefined,
      isTranslating: false,
      error: undefined
    };
  }, [initialMode, initialTargetLanguage, persistToStorage, storageKey]);

  // State
  const [state, setState] = useState<TranslationState>(loadInitialState);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [session, setSession] = useState<TranslationSession | null>(null);

  // Session ID generator
  const sessionIdRef = useRef<number>(0);

  // Persist state to storage
  useEffect(() => {
    if (persistToStorage && typeof window !== 'undefined') {
      try {
        const stateToStore = {
          isEnabled: state.isEnabled,
          mode: state.mode,
          sourceLanguage: state.sourceLanguage,
          targetLanguage: state.targetLanguage,
          selectedVoice: state.selectedVoice
        };
        localStorage.setItem(storageKey, JSON.stringify(stateToStore));
      } catch (error) {
        console.warn('Failed to persist translation state:', error);
      }
    }
  }, [state, persistToStorage, storageKey]);

  // Mode management
  const setMode = useCallback((mode: TranslationMode) => {
    setState(prev => ({
      ...prev,
      mode,
      isEnabled: mode !== 'off',
      error: mode === 'off' ? undefined : prev.error
    }));
  }, []);

  const toggleMode = useCallback(() => {
    const modes: TranslationMode[] = ['off', 'push', 'always'];
    const currentIndex = modes.indexOf(state.mode);
    const nextMode = modes[(currentIndex + 1) % modes.length];
    setMode(nextMode);
  }, [state.mode, setMode]);

  // Language management
  const setSourceLanguage = useCallback((language: string) => {
    setState(prev => ({ ...prev, sourceLanguage: language }));
  }, []);

  const setTargetLanguage = useCallback((language: string) => {
    setState(prev => ({ ...prev, targetLanguage: language }));
  }, []);

  const setSelectedVoice = useCallback((voiceId: string) => {
    setState(prev => ({ ...prev, selectedVoice: voiceId }));
  }, []);

  // Caption management
  const addCaption = useCallback((caption: Caption) => {
    setCaptions(prev => {
      const newCaptions = [...prev, caption];
      // Limit captions to prevent memory issues
      return newCaptions.slice(-maxCaptions);
    });

    // Add to current session if active
    if (session) {
      setSession(prev => prev ? {
        ...prev,
        captions: [...prev.captions, caption].slice(-maxCaptions)
      } : null);
    }
  }, [maxCaptions, session]);

  const updateCaption = useCallback((id: string, updates: Partial<Caption>) => {
    setCaptions(prev => prev.map(caption => 
      caption.id === id ? { ...caption, ...updates } : caption
    ));

    // Update in current session if active
    if (session) {
      setSession(prev => prev ? {
        ...prev,
        captions: prev.captions.map(caption => 
          caption.id === id ? { ...caption, ...updates } : caption
        )
      } : null);
    }
  }, [session]);

  const clearCaptions = useCallback(() => {
    setCaptions([]);
    if (session) {
      setSession(prev => prev ? { ...prev, captions: [] } : null);
    }
  }, [session]);

  // Session management
  const startSession = useCallback((sourceLanguage: string, targetLanguages: string[]) => {
    const sessionId = `session-${Date.now()}-${++sessionIdRef.current}`;
    const newSession: TranslationSession = {
      sessionId,
      participantId: 'current-user',
      sourceLanguage,
      targetLanguages,
      startTime: Date.now(),
      captions: [],
      metrics: []
    };

    setSession(newSession);
    clearCaptions(); // Start with fresh captions
  }, [clearCaptions]);

  const endSession = useCallback(() => {
    if (session) {
      setSession(prev => prev ? {
        ...prev,
        endTime: Date.now()
      } : null);
    }
  }, [session]);

  const exportSession = useCallback((): TranslationSession | null => {
    if (!session) return null;

    return {
      ...session,
      endTime: session.endTime || Date.now(),
      captions: [...captions]
    };
  }, [session, captions]);

  // Status management
  const setTranslating = useCallback((isTranslating: boolean) => {
    setState(prev => ({ ...prev, isTranslating }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error: error || undefined }));
  }, []);

  const setLatency = useCallback((latency: number) => {
    setState(prev => ({ ...prev, currentLatency: latency }));
  }, []);

  // Utility functions
  const getActiveSession = useCallback((): TranslationSession | null => {
    return session && !session.endTime ? session : null;
  }, [session]);

  const getCaptionStats = useCallback(() => {
    const total = captions.length;
    const stable = captions.filter(c => c.isStable).length;
    const averageConfidence = total > 0 
      ? captions.reduce((sum, c) => sum + c.confidence, 0) / total 
      : 0;

    return { total, stable, averageConfidence };
  }, [captions]);

  return {
    // State
    state,
    captions,
    session,

    // Mode management
    setMode,
    toggleMode,

    // Language management
    setSourceLanguage,
    setTargetLanguage,
    setSelectedVoice,

    // Caption management
    addCaption,
    updateCaption,
    clearCaptions,

    // Session management
    startSession,
    endSession,
    exportSession,

    // Status management
    setTranslating,
    setError,
    setLatency,

    // Utility functions
    getActiveSession,
    getCaptionStats
  };
};