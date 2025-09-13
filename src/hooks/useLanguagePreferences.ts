/**
 * Language Preferences Management Hook
 * 
 * Manages user language preferences, available languages/voices,
 * and provides utilities for language selection and voice management.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import type { 
  Language, 
  Voice, 
  TranslationPreference, 
  UseLanguagePreferencesReturn 
} from '../types/translation';

interface UseLanguagePreferencesOptions {
  persistToStorage?: boolean;
  storageKey?: string;
  defaultSourceLanguage?: string;
  defaultTargetLanguages?: string[];
}

// Mock data - in a real app, this would come from an API
const AVAILABLE_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', flag: '🇺🇸', nativeName: 'English' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸', nativeName: 'Español' },
  { code: 'fr', name: 'French', flag: '🇫🇷', nativeName: 'Français' },
  { code: 'de', name: 'German', flag: '🇩🇪', nativeName: 'Deutsch' },
  { code: 'it', name: 'Italian', flag: '🇮🇹', nativeName: 'Italiano' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹', nativeName: 'Português' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦', nativeName: 'العربية' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳', nativeName: '中文' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵', nativeName: '日本語' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷', nativeName: '한국어' },
  { code: 'hi', name: 'Hindi', flag: '🇮🇳', nativeName: 'हिन्दी' },
  { code: 'ru', name: 'Russian', flag: '🇷🇺', nativeName: 'Русский' },
];

const AVAILABLE_VOICES: Voice[] = [
  // English voices
  { id: 'en-us-female-1', name: 'Emma', language: 'en', gender: 'female', description: 'Clear American English', isDefault: true },
  { id: 'en-us-male-1', name: 'James', language: 'en', gender: 'male', description: 'Professional American English' },
  { id: 'en-uk-female-1', name: 'Sophie', language: 'en', gender: 'female', description: 'British English accent' },
  
  // Spanish voices
  { id: 'es-es-female-1', name: 'Carmen', language: 'es', gender: 'female', description: 'Castilian Spanish', isDefault: true },
  { id: 'es-es-male-1', name: 'Diego', language: 'es', gender: 'male', description: 'Madrid Spanish accent' },
  { id: 'es-mx-female-1', name: 'Lucia', language: 'es', gender: 'female', description: 'Mexican Spanish' },
  
  // French voices
  { id: 'fr-fr-female-1', name: 'Amelie', language: 'fr', gender: 'female', description: 'Parisian French', isDefault: true },
  { id: 'fr-fr-male-1', name: 'Henri', language: 'fr', gender: 'male', description: 'Standard French accent' },
  
  // German voices
  { id: 'de-de-female-1', name: 'Greta', language: 'de', gender: 'female', description: 'Berlin German', isDefault: true },
  { id: 'de-de-male-1', name: 'Klaus', language: 'de', gender: 'male', description: 'Standard German' },
  
  // Italian voices
  { id: 'it-it-female-1', name: 'Giulia', language: 'it', gender: 'female', description: 'Roman Italian', isDefault: true },
  { id: 'it-it-male-1', name: 'Marco', language: 'it', gender: 'male', description: 'Northern Italian' },
  
  // Portuguese voices
  { id: 'pt-pt-female-1', name: 'Cristina', language: 'pt', gender: 'female', description: 'European Portuguese', isDefault: true },
  { id: 'pt-br-female-1', name: 'Ana', language: 'pt', gender: 'female', description: 'Brazilian Portuguese' },
  
  // Arabic voices
  { id: 'ar-sa-female-1', name: 'Layla', language: 'ar', gender: 'female', description: 'Modern Standard Arabic', isDefault: true },
  { id: 'ar-sa-male-1', name: 'Omar', language: 'ar', gender: 'male', description: 'Gulf Arabic accent' },
  
  // Chinese voices
  { id: 'zh-cn-female-1', name: 'Li Wei', language: 'zh', gender: 'female', description: 'Mandarin Chinese', isDefault: true },
  { id: 'zh-cn-male-1', name: 'Wang Ming', language: 'zh', gender: 'male', description: 'Beijing Mandarin' },
  
  // Japanese voices
  { id: 'ja-jp-female-1', name: 'Yuki', language: 'ja', gender: 'female', description: 'Tokyo Japanese', isDefault: true },
  { id: 'ja-jp-male-1', name: 'Hiroshi', language: 'ja', gender: 'male', description: 'Standard Japanese' },
  
  // Korean voices
  { id: 'ko-kr-female-1', name: 'Min-jun', language: 'ko', gender: 'female', description: 'Seoul Korean', isDefault: true },
  { id: 'ko-kr-male-1', name: 'Seung-ho', language: 'ko', gender: 'male', description: 'Standard Korean' },
  
  // Hindi voices
  { id: 'hi-in-female-1', name: 'Priya', language: 'hi', gender: 'female', description: 'Delhi Hindi', isDefault: true },
  { id: 'hi-in-male-1', name: 'Raj', language: 'hi', gender: 'male', description: 'Standard Hindi' },
  
  // Russian voices
  { id: 'ru-ru-female-1', name: 'Katya', language: 'ru', gender: 'female', description: 'Moscow Russian', isDefault: true },
  { id: 'ru-ru-male-1', name: 'Dmitri', language: 'ru', gender: 'male', description: 'Standard Russian' },
];

export const useLanguagePreferences = (
  options: UseLanguagePreferencesOptions = {}
): UseLanguagePreferencesReturn => {
  const {
    persistToStorage = true,
    storageKey = 'hive-language-preferences',
    defaultSourceLanguage = 'en',
    defaultTargetLanguages = ['es']
  } = options;

  // Load initial preferences from storage
  const loadInitialPreferences = useCallback((): TranslationPreference => {
    if (persistToStorage && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          return {
            userId: parsed.userId || 'default-user',
            sourceLanguage: parsed.sourceLanguage || defaultSourceLanguage,
            targetLanguages: parsed.targetLanguages || defaultTargetLanguages,
            preferredVoice: parsed.preferredVoice || {},
            autoDetect: parsed.autoDetect !== undefined ? parsed.autoDetect : true
          };
        }
      } catch (error) {
        console.warn('Failed to load language preferences from storage:', error);
      }
    }

    return {
      userId: 'default-user',
      sourceLanguage: defaultSourceLanguage,
      targetLanguages: defaultTargetLanguages,
      preferredVoice: {},
      autoDetect: true
    };
  }, [persistToStorage, storageKey, defaultSourceLanguage, defaultTargetLanguages]);

  const [preferences, setPreferences] = useState<TranslationPreference>(loadInitialPreferences);

  // Persist preferences to storage
  useEffect(() => {
    if (persistToStorage && typeof window !== 'undefined') {
      try {
        localStorage.setItem(storageKey, JSON.stringify(preferences));
      } catch (error) {
        console.warn('Failed to persist language preferences:', error);
      }
    }
  }, [preferences, persistToStorage, storageKey]);

  // Memoized available data
  const availableLanguages = useMemo(() => AVAILABLE_LANGUAGES, []);
  const availableVoices = useMemo(() => AVAILABLE_VOICES, []);

  // Get voices for a specific language
  const getVoicesForLanguage = useCallback((languageCode: string): Voice[] => {
    return availableVoices.filter(voice => voice.language === languageCode);
  }, [availableVoices]);

  // Get default voice for a language
  const getDefaultVoiceForLanguage = useCallback((languageCode: string): Voice | undefined => {
    const voices = getVoicesForLanguage(languageCode);
    return voices.find(voice => voice.isDefault) || voices[0];
  }, [getVoicesForLanguage]);

  // Update preferences
  const updatePreference = useCallback((updates: Partial<TranslationPreference>) => {
    setPreferences(prev => {
      const updated = { ...prev, ...updates };
      
      // Auto-assign default voices for new target languages
      if (updates.targetLanguages) {
        const newPreferredVoice = { ...prev.preferredVoice };
        
        updates.targetLanguages.forEach(langCode => {
          if (!newPreferredVoice[langCode]) {
            const defaultVoice = getDefaultVoiceForLanguage(langCode);
            if (defaultVoice) {
              newPreferredVoice[langCode] = defaultVoice.id;
            }
          }
        });
        
        // Remove preferences for languages no longer in target list
        Object.keys(newPreferredVoice).forEach(langCode => {
          if (updates.targetLanguages && !updates.targetLanguages.includes(langCode)) {
            delete newPreferredVoice[langCode];
          }
        });
        
        updated.preferredVoice = newPreferredVoice;
      }
      
      return updated;
    });
  }, [getDefaultVoiceForLanguage]);

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    const defaultPrefs: TranslationPreference = {
      userId: preferences.userId,
      sourceLanguage: defaultSourceLanguage,
      targetLanguages: defaultTargetLanguages,
      preferredVoice: {},
      autoDetect: true
    };

    // Set default voices for target languages
    defaultTargetLanguages.forEach(langCode => {
      const defaultVoice = getDefaultVoiceForLanguage(langCode);
      if (defaultVoice) {
        defaultPrefs.preferredVoice[langCode] = defaultVoice.id;
      }
    });

    setPreferences(defaultPrefs);
  }, [preferences.userId, defaultSourceLanguage, defaultTargetLanguages, getDefaultVoiceForLanguage]);

  // Add target language
  const addTargetLanguage = useCallback((languageCode: string) => {
    if (!preferences.targetLanguages.includes(languageCode)) {
      const newTargetLanguages = [...preferences.targetLanguages, languageCode];
      updatePreference({ targetLanguages: newTargetLanguages });
    }
  }, [preferences.targetLanguages, updatePreference]);

  // Remove target language
  const removeTargetLanguage = useCallback((languageCode: string) => {
    const newTargetLanguages = preferences.targetLanguages.filter(lang => lang !== languageCode);
    updatePreference({ targetLanguages: newTargetLanguages });
  }, [preferences.targetLanguages, updatePreference]);

  // Set voice for language
  const setVoiceForLanguage = useCallback((languageCode: string, voiceId: string) => {
    const newPreferredVoice = {
      ...preferences.preferredVoice,
      [languageCode]: voiceId
    };
    updatePreference({ preferredVoice: newPreferredVoice });
  }, [preferences.preferredVoice, updatePreference]);

  // Get language by code
  const getLanguageByCode = useCallback((code: string): Language | undefined => {
    return availableLanguages.find(lang => lang.code === code);
  }, [availableLanguages]);

  // Get voice by ID
  const getVoiceById = useCallback((id: string): Voice | undefined => {
    return availableVoices.find(voice => voice.id === id);
  }, [availableVoices]);

  // Get preferred voice for language
  const getPreferredVoiceForLanguage = useCallback((languageCode: string): Voice | undefined => {
    const preferredVoiceId = preferences.preferredVoice[languageCode];
    if (preferredVoiceId) {
      return getVoiceById(preferredVoiceId);
    }
    return getDefaultVoiceForLanguage(languageCode);
  }, [preferences.preferredVoice, getVoiceById, getDefaultVoiceForLanguage]);


  return {
    preferences,
    availableLanguages,
    availableVoices,
    updatePreference,
    getVoicesForLanguage,
    resetToDefaults,
    addTargetLanguage,
    removeTargetLanguage,
    setVoiceForLanguage,
    getLanguageByCode,
    getVoiceById,
    getPreferredVoiceForLanguage
  };
};