/**
 * Translation Settings Panel Component
 * 
 * Comprehensive settings panel for translation preferences, voice customization,
 * quality controls, and per-participant language selection with premium HIVE design.
 */

import React, { useState, useCallback, useEffect } from 'react';
import type { Language, Voice, TranslationPreference, TranslationMode } from '../../types/translation';

interface TranslationSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: TranslationPreference;
  availableLanguages: Language[];
  availableVoices: Voice[];
  onUpdatePreferences: (updates: Partial<TranslationPreference>) => void;
  translationMode: TranslationMode;
  onModeChange: (mode: TranslationMode) => void;
  currentLatency?: number;
  isTranslationEnabled: boolean;
  onToggleTranslation: () => void;
  participantLanguages?: Record<string, string>;
  onParticipantLanguageChange?: (participantId: string, language: string) => void;
}

const TranslationSettingsPanel: React.FC<TranslationSettingsPanelProps> = ({
  isOpen,
  onClose,
  preferences,
  availableLanguages,
  availableVoices,
  onUpdatePreferences,
  translationMode,
  onModeChange,
  currentLatency,
  isTranslationEnabled,
  onToggleTranslation,
  participantLanguages = {},
  onParticipantLanguageChange
}) => {
  const [activeTab, setActiveTab] = useState<'general' | 'voices' | 'participants' | 'advanced'>('general');
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);
  const [unsavedChanges] = useState(false);

  // Voice preview functionality
  const handleVoicePreview = useCallback(async (voiceId: string) => {
    setPreviewingVoice(voiceId);
    try {
      // This would integrate with TTS service for voice preview
      // For now, simulate a preview duration
      setTimeout(() => setPreviewingVoice(null), 2000);
    } catch (error) {
      console.error('Voice preview error:', error);
      setPreviewingVoice(null);
    }
  }, []);

  // Get voices for specific language
  const getVoicesForLanguage = useCallback((languageCode: string) => {
    return availableVoices.filter(voice => voice.language === languageCode);
  }, [availableVoices]);

  // Handle escape key to close panel
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Tab navigation with keyboard
  useEffect(() => {
    const handleTabNavigation = (event: KeyboardEvent) => {
      if (!isOpen) return;
      
      if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
          case '1':
            event.preventDefault();
            setActiveTab('general');
            break;
          case '2':
            event.preventDefault();
            setActiveTab('voices');
            break;
          case '3':
            event.preventDefault();
            setActiveTab('participants');
            break;
          case '4':
            event.preventDefault();
            setActiveTab('advanced');
            break;
        }
      }
    };

    document.addEventListener('keydown', handleTabNavigation);
    return () => document.removeEventListener('keydown', handleTabNavigation);
  }, [isOpen]);

  if (!isOpen) return null;

  const tabs = [
    { id: 'general', label: 'General', icon: '🌐', shortcut: '1' },
    { id: 'voices', label: 'Voices', icon: '🎤', shortcut: '2' },
    { id: 'participants', label: 'Participants', icon: '👥', shortcut: '3' },
    { id: 'advanced', label: 'Advanced', icon: '⚙️', shortcut: '4' }
  ] as const;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-hive-cyan/20 rounded-lg flex items-center justify-center">
              <span className="text-lg">🌐</span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Translation Settings</h2>
              <p className="text-sm text-gray-400">Configure your real-time translation preferences</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Status Indicator */}
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-lg ${
              isTranslationEnabled 
                ? 'bg-emerald-500/20 text-emerald-300' 
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isTranslationEnabled ? 'bg-emerald-400 animate-pulse' : 'bg-gray-400'
              }`} />
              <span className="text-xs font-medium">
                {isTranslationEnabled ? 'Active' : 'Inactive'}
              </span>
            </div>
            
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
              aria-label="Close settings"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex h-[70vh]">
          {/* Sidebar Navigation */}
          <div className="w-64 border-r border-white/10 p-4 space-y-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  activeTab === tab.id
                    ? 'bg-hive-cyan/20 text-hive-cyan border border-hive-cyan/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="text-lg">{tab.icon}</span>
                <div className="flex-1 text-left">
                  <div className="font-medium">{tab.label}</div>
                </div>
                <kbd className="px-1.5 py-0.5 text-xs bg-white/10 rounded border border-white/20">
                  ⌘{tab.shortcut}
                </kbd>
              </button>
            ))}
          </div>

          {/* Content Area */}
          <div className="flex-1 p-6 overflow-y-auto">
            
            {/* General Tab */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">General Settings</h3>
                  
                  {/* Translation Toggle */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4 mb-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-white">Real-time Translation</h4>
                        <p className="text-sm text-gray-400">Enable or disable translation features</p>
                      </div>
                      <button
                        onClick={onToggleTranslation}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          isTranslationEnabled ? 'bg-hive-cyan' : 'bg-gray-600'
                        }`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          isTranslationEnabled ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  </div>

                  {/* Translation Mode */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4 mb-4">
                    <h4 className="font-medium text-white mb-3">Translation Mode</h4>
                    <div className="grid grid-cols-3 gap-2">
                      {(['always', 'push', 'off'] as TranslationMode[]).map((mode) => (
                        <button
                          key={mode}
                          onClick={() => onModeChange(mode)}
                          disabled={!isTranslationEnabled && mode !== 'off'}
                          className={`p-3 rounded-lg border transition-all duration-200 ${
                            translationMode === mode
                              ? 'bg-hive-cyan/20 border-hive-cyan text-hive-cyan'
                              : 'border-white/20 text-gray-400 hover:border-white/40 hover:text-white'
                          } ${!isTranslationEnabled && mode !== 'off' ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          <div className="text-center">
                            <div className="text-lg mb-1">
                              {mode === 'always' ? '🌐' : mode === 'push' ? '🎤' : '🚫'}
                            </div>
                            <div className="text-xs font-medium">
                              {mode === 'always' ? 'Always On' : mode === 'push' ? 'Push to Talk' : 'Disabled'}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Source Language */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4 mb-4">
                    <label className="block font-medium text-white mb-2">Your Language</label>
                    <select
                      value={preferences.sourceLanguage}
                      onChange={(e) => onUpdatePreferences({ sourceLanguage: e.target.value })}
                      disabled={!isTranslationEnabled}
                      className="w-full p-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-hive-cyan disabled:opacity-50"
                    >
                      <option value="">Auto-detect</option>
                      {availableLanguages.map(lang => (
                        <option key={lang.code} value={lang.code} className="bg-slate-800">
                          {lang.flag} {lang.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Target Languages */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4">
                    <label className="block font-medium text-white mb-2">Translate To</label>
                    <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                      {availableLanguages.map(lang => (
                        <label key={lang.code} className="flex items-center p-2 hover:bg-white/5 rounded cursor-pointer">
                          <input
                            type="checkbox"
                            checked={preferences.targetLanguages.includes(lang.code)}
                            onChange={(e) => {
                              const newTargets = e.target.checked
                                ? [...preferences.targetLanguages, lang.code]
                                : preferences.targetLanguages.filter(l => l !== lang.code);
                              onUpdatePreferences({ targetLanguages: newTargets });
                            }}
                            disabled={!isTranslationEnabled}
                            className="w-4 h-4 text-hive-cyan bg-transparent border-white/30 rounded focus:ring-hive-cyan focus:ring-2 disabled:opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-300">{lang.flag} {lang.name}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Voices Tab */}
            {activeTab === 'voices' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Voice Preferences</h3>
                  
                  {preferences.targetLanguages.length === 0 ? (
                    <div className="glass-effect backdrop-blur-lg bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6 text-center">
                      <div className="text-yellow-400 text-4xl mb-2">🎤</div>
                      <p className="text-yellow-300 font-medium mb-1">No target languages selected</p>
                      <p className="text-yellow-400/80 text-sm">Select target languages in the General tab to configure voices</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {preferences.targetLanguages.map(langCode => {
                        const language = availableLanguages.find(l => l.code === langCode);
                        const voices = getVoicesForLanguage(langCode);
                        const selectedVoice = preferences.preferredVoice[langCode];
                        
                        return (
                          <div key={langCode} className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="font-medium text-white">
                                {language?.flag} {language?.name}
                              </h4>
                              <span className="text-xs text-gray-400 bg-white/10 px-2 py-1 rounded">
                                {voices.length} voice{voices.length !== 1 ? 's' : ''}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-1 gap-2">
                              {voices.map(voice => (
                                <div key={voice.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                                  <label className="flex items-center flex-1 cursor-pointer">
                                    <input
                                      type="radio"
                                      name={`voice-${langCode}`}
                                      value={voice.id}
                                      checked={selectedVoice === voice.id}
                                      onChange={() => onUpdatePreferences({
                                        preferredVoice: { ...preferences.preferredVoice, [langCode]: voice.id }
                                      })}
                                      className="w-4 h-4 text-hive-cyan bg-transparent border-white/30 focus:ring-hive-cyan focus:ring-2"
                                    />
                                    <div className="ml-3 flex-1">
                                      <div className="flex items-center space-x-2">
                                        <span className="text-white font-medium">{voice.name}</span>
                                        <span className={`text-xs px-2 py-1 rounded ${
                                          voice.gender === 'female' ? 'bg-pink-500/20 text-pink-300' :
                                          voice.gender === 'male' ? 'bg-blue-500/20 text-blue-300' :
                                          'bg-gray-500/20 text-gray-300'
                                        }`}>
                                          {voice.gender}
                                        </span>
                                        {voice.isDefault && (
                                          <span className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded">
                                            Default
                                          </span>
                                        )}
                                      </div>
                                      {voice.description && (
                                        <p className="text-xs text-gray-400 mt-1">{voice.description}</p>
                                      )}
                                    </div>
                                  </label>
                                  
                                  <button
                                    onClick={() => handleVoicePreview(voice.id)}
                                    disabled={previewingVoice === voice.id || !isTranslationEnabled}
                                    className="ml-3 p-2 bg-hive-cyan/20 text-hive-cyan rounded-lg hover:bg-hive-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    title="Preview voice"
                                  >
                                    {previewingVoice === voice.id ? (
                                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 8h8a2 2 0 002-2V6a2 2 0 00-2-2H8a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                      </svg>
                                    )}
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Participants Tab */}
            {activeTab === 'participants' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Per-Participant Settings</h3>
                  
                  {Object.keys(participantLanguages).length === 0 ? (
                    <div className="glass-effect backdrop-blur-lg bg-blue-500/10 border border-blue-500/30 rounded-lg p-6 text-center">
                      <div className="text-blue-400 text-4xl mb-2">👥</div>
                      <p className="text-blue-300 font-medium mb-1">No other participants</p>
                      <p className="text-blue-400/80 text-sm">When others join the call, you can configure individual translation settings here</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {Object.entries(participantLanguages).map(([participantId, currentLanguage]) => (
                        <div key={participantId} className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-3">
                              <div className="w-10 h-10 bg-gradient-to-br from-hive-cyan to-cyan-400 rounded-full flex items-center justify-center">
                                <span className="text-slate-900 font-bold text-sm">{participantId.charAt(0).toUpperCase()}</span>
                              </div>
                              <div>
                                <h4 className="font-medium text-white">{participantId}</h4>
                                <p className="text-xs text-gray-400">Configure translation for this participant</p>
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Translate their speech to:</label>
                            <select
                              value={currentLanguage}
                              onChange={(e) => onParticipantLanguageChange?.(participantId, e.target.value)}
                              className="w-full p-2 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-hive-cyan"
                            >
                              <option value="" className="bg-slate-800">No translation</option>
                              {availableLanguages.map(lang => (
                                <option key={lang.code} value={lang.code} className="bg-slate-800">
                                  {lang.flag} {lang.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Advanced Tab */}
            {activeTab === 'advanced' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Advanced Settings</h3>
                  
                  {/* Performance Metrics */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4 mb-4">
                    <h4 className="font-medium text-white mb-3">Performance</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Current Latency</label>
                        <div className={`text-lg font-mono ${
                          !currentLatency ? 'text-gray-500' :
                          currentLatency > 500 ? 'text-red-400' :
                          currentLatency > 300 ? 'text-yellow-400' : 'text-green-400'
                        }`}>
                          {currentLatency ? `${Math.round(currentLatency)}ms` : 'N/A'}
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Status</label>
                        <div className={`text-lg font-medium ${
                          !isTranslationEnabled ? 'text-gray-500' :
                          (!currentLatency || currentLatency <= 300) ? 'text-green-400' :
                          currentLatency <= 500 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {!isTranslationEnabled ? 'Disabled' :
                           !currentLatency ? 'Ready' :
                           currentLatency <= 300 ? 'Excellent' :
                           currentLatency <= 500 ? 'Good' : 'Poor'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Auto-detect Settings */}
                  <div className="glass-effect backdrop-blur-lg bg-white/5 border border-white/10 rounded-lg p-4 mb-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-white">Auto-detect Language</h4>
                        <p className="text-sm text-gray-400">Automatically detect the source language</p>
                      </div>
                      <button
                        onClick={() => onUpdatePreferences({ autoDetect: !preferences.autoDetect })}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          preferences.autoDetect ? 'bg-hive-cyan' : 'bg-gray-600'
                        }`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          preferences.autoDetect ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  </div>

                  {/* Reset Settings */}
                  <div className="glass-effect backdrop-blur-lg bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                    <h4 className="font-medium text-red-300 mb-2">Reset Settings</h4>
                    <p className="text-sm text-red-400/80 mb-3">
                      Reset all translation settings to default values. This action cannot be undone.
                    </p>
                    <button className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-colors border border-red-500/30">
                      Reset to Defaults
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-white/10">
          <div className="text-sm text-gray-400">
            Use <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/20">Esc</kbd> to close
          </div>
          <div className="flex items-center space-x-3">
            {unsavedChanges && (
              <span className="text-sm text-yellow-400">Unsaved changes</span>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranslationSettingsPanel;