/**
 * Enhanced Translated Audio Selector Component
 * 
 * Premium UI for language and voice selection with voice preview, quality controls,
 * latency monitoring, and advanced audio settings with HIVE glassmorphism design.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import type { Language, Voice } from '../../types/translation';

interface TranslatedAudioSelectorProps {
  availableLanguages: Language[];
  selectedLanguage: string;
  onLanguageChange: (language: string) => void;
  availableVoices: Voice[];
  selectedVoice: string;
  onVoiceChange: (voice: string) => void;
  isTranslationEnabled: boolean;
  latency?: number;
  onToggleTranslation?: () => void;
  audioQuality?: 'low' | 'medium' | 'high';
  onAudioQualityChange?: (quality: 'low' | 'medium' | 'high') => void;
  voiceSpeed?: number;
  onVoiceSpeedChange?: (speed: number) => void;
  volume?: number;
  onVolumeChange?: (volume: number) => void;
  isCompact?: boolean;
  showAdvancedControls?: boolean;
}

const TranslatedAudioSelector: React.FC<TranslatedAudioSelectorProps> = ({
  availableLanguages,
  selectedLanguage,
  onLanguageChange,
  availableVoices,
  selectedVoice,
  onVoiceChange,
  isTranslationEnabled,
  latency,
  onToggleTranslation,
  audioQuality = 'medium',
  onAudioQualityChange,
  voiceSpeed = 1.0,
  onVoiceSpeedChange,
  volume = 0.8,
  onVolumeChange,
  isCompact = false,
  showAdvancedControls = true
}) => {
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);
  const [showVoiceGrid, setShowVoiceGrid] = useState(false);
  const [selectedLanguageInfo, setSelectedLanguageInfo] = useState<Language | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement>(null);

  // Update selected language info when language changes
  useEffect(() => {
    const langInfo = availableLanguages.find(lang => lang.code === selectedLanguage);
    setSelectedLanguageInfo(langInfo || null);
  }, [selectedLanguage, availableLanguages]);

  // Voice preview functionality
  const handleVoicePreview = useCallback(async (voiceId: string) => {
    setPreviewingVoice(voiceId);
    
    try {
      // In a real implementation, this would call the TTS service
      // For demo purposes, we'll just simulate a preview
      const voice = availableVoices.find(v => v.id === voiceId);
      if (voice) {
        // Create a test audio for preview
        // This would be replaced with actual TTS service call
        setTimeout(() => setPreviewingVoice(null), 2000);
      }
    } catch (error) {
      console.error('Voice preview error:', error);
      setPreviewingVoice(null);
    }
  }, [availableVoices]);

  // Get voices for current language
  const currentLanguageVoices = availableVoices.filter(voice => voice.language === selectedLanguage);
  const selectedVoiceInfo = currentLanguageVoices.find(voice => voice.id === selectedVoice);

  // Get quality badge color
  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'high': return 'text-emerald-400 bg-emerald-500/20';
      case 'low': return 'text-yellow-400 bg-yellow-500/20';
      default: return 'text-blue-400 bg-blue-500/20';
    }
  };

  // Get latency status
  const getLatencyStatus = () => {
    if (!latency) return { color: 'text-gray-400', status: 'N/A', icon: '⏱️' };
    if (latency <= 300) return { color: 'text-green-400', status: 'Excellent', icon: '🟢' };
    if (latency <= 500) return { color: 'text-yellow-400', status: 'Good', icon: '🟡' };
    return { color: 'text-red-400', status: 'Poor', icon: '🔴' };
  };

  const latencyStatus = getLatencyStatus();

  if (isCompact) {
    return (
      <div className="translation-controls-compact glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-xl shadow-lg">
        <div className="flex items-center justify-between p-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-hive-cyan/20 rounded-lg flex items-center justify-center">
              <span className="text-lg">🌐</span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-white font-medium text-sm">{selectedLanguageInfo?.flag}</span>
                <span className="text-white text-sm">{selectedLanguageInfo?.name}</span>
              </div>
              {selectedVoiceInfo && (
                <div className="text-xs text-gray-400">{selectedVoiceInfo.name}</div>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {latency && (
              <div className={`text-xs ${latencyStatus.color}`}>
                {latencyStatus.icon} {Math.round(latency)}ms
              </div>
            )}
            
            {onToggleTranslation && (
              <button
                onClick={onToggleTranslation}
                className={`w-8 h-8 rounded-lg transition-colors ${
                  isTranslationEnabled
                    ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                    : 'bg-gray-500/20 text-gray-400 hover:bg-gray-500/30'
                }`}
              >
                {isTranslationEnabled ? '✓' : '✗'}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="translation-controls glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-2xl shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-hive-cyan/20 rounded-xl flex items-center justify-center">
            <span className="text-xl">🌐</span>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Translation Audio</h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`text-xs px-2 py-1 rounded-full ${getQualityColor(audioQuality)}`}>
                {audioQuality.toUpperCase()} Quality
              </span>
              <span className={`text-xs px-2 py-1 rounded-full ${latencyStatus.color.replace('text-', 'bg-').replace('-400', '-500/20')}`}>
                {latencyStatus.icon} {latencyStatus.status}
              </span>
            </div>
          </div>
        </div>
        
        {onToggleTranslation && (
          <button
            onClick={onToggleTranslation}
            className={`relative inline-flex h-8 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-hive-cyan focus:ring-offset-2 focus:ring-offset-slate-900 ${
              isTranslationEnabled ? 'bg-hive-cyan' : 'bg-gray-600'
            }`}
          >
            <span className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
              isTranslationEnabled ? 'translate-x-7' : 'translate-x-1'
            }`} />
          </button>
        )}
      </div>

      {isTranslationEnabled && (
        <div className="p-6 space-y-6">
          {/* Language Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-3">
              Translate to Language
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {availableLanguages.map(lang => (
                <button
                  key={lang.code}
                  onClick={() => onLanguageChange(lang.code)}
                  className={`p-3 rounded-xl border-2 transition-all duration-200 ${
                    selectedLanguage === lang.code
                      ? 'bg-hive-cyan/20 border-hive-cyan text-hive-cyan'
                      : 'bg-white/5 border-white/20 text-gray-300 hover:border-white/40 hover:bg-white/10'
                  }`}
                >
                  <div className="text-center">
                    <div className="text-lg mb-1">{lang.flag}</div>
                    <div className="text-xs font-medium">{lang.name}</div>
                    {lang.nativeName && (
                      <div className="text-xs text-gray-400 mt-1">{lang.nativeName}</div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Voice Selection */}
          {currentLanguageVoices.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-white">
                  Voice ({currentLanguageVoices.length} available)
                </label>
                <button
                  onClick={() => setShowVoiceGrid(!showVoiceGrid)}
                  className="text-xs text-hive-cyan hover:text-cyan-300 transition-colors"
                >
                  {showVoiceGrid ? 'Hide Grid' : 'Show Grid'}
                </button>
              </div>
              
              {showVoiceGrid ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {currentLanguageVoices.map(voice => (
                    <div
                      key={voice.id}
                      className={`p-4 rounded-xl border transition-all duration-200 ${
                        selectedVoice === voice.id
                          ? 'bg-hive-cyan/20 border-hive-cyan'
                          : 'bg-white/5 border-white/20 hover:border-white/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <input
                            type="radio"
                            name="voice-selection"
                            value={voice.id}
                            checked={selectedVoice === voice.id}
                            onChange={() => onVoiceChange(voice.id)}
                            className="w-4 h-4 text-hive-cyan bg-transparent border-white/30 focus:ring-hive-cyan focus:ring-2"
                          />
                          <span className="text-white font-medium text-sm">{voice.name}</span>
                        </div>
                        
                        <button
                          onClick={() => handleVoicePreview(voice.id)}
                          disabled={previewingVoice === voice.id || !isTranslationEnabled}
                          className="p-2 bg-hive-cyan/20 text-hive-cyan rounded-lg hover:bg-hive-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                      
                      <div className="flex items-center space-x-2">
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          voice.gender === 'female' ? 'bg-pink-500/20 text-pink-300' :
                          voice.gender === 'male' ? 'bg-blue-500/20 text-blue-300' :
                          'bg-gray-500/20 text-gray-300'
                        }`}>
                          {voice.gender}
                        </span>
                        
                        {voice.isDefault && (
                          <span className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded-full">
                            Default
                          </span>
                        )}
                      </div>
                      
                      {voice.description && (
                        <p className="text-xs text-gray-400 mt-2">{voice.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <select
                  value={selectedVoice}
                  onChange={(e) => onVoiceChange(e.target.value)}
                  className="w-full p-3 bg-white/10 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-hive-cyan focus:border-transparent"
                >
                  {currentLanguageVoices.map(voice => (
                    <option key={voice.id} value={voice.id} className="bg-slate-800">
                      {voice.name} ({voice.gender}) {voice.isDefault ? '- Default' : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Advanced Controls */}
          {showAdvancedControls && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-white">Advanced Audio Settings</h4>
              
              {/* Audio Quality */}
              {onAudioQualityChange && (
                <div>
                  <label className="block text-sm text-gray-300 mb-2">Audio Quality</label>
                  <div className="flex space-x-2">
                    {(['low', 'medium', 'high'] as const).map((quality) => (
                      <button
                        key={quality}
                        onClick={() => onAudioQualityChange(quality)}
                        className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                          audioQuality === quality
                            ? 'bg-hive-cyan/20 text-hive-cyan border border-hive-cyan/30'
                            : 'bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {quality.charAt(0).toUpperCase() + quality.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Voice Speed */}
              {onVoiceSpeedChange && (
                <div>
                  <label className="block text-sm text-gray-300 mb-2">
                    Voice Speed: {voiceSpeed.toFixed(1)}x
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="2.0"
                    step="0.1"
                    value={voiceSpeed}
                    onChange={(e) => onVoiceSpeedChange(parseFloat(e.target.value))}
                    className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider-thumb"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>Slow</span>
                    <span>Normal</span>
                    <span>Fast</span>
                  </div>
                </div>
              )}

              {/* Volume */}
              {onVolumeChange && (
                <div>
                  <label className="block text-sm text-gray-300 mb-2">
                    Volume: {Math.round(volume * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={volume}
                    onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
                    className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider-thumb"
                  />
                </div>
              )}
            </div>
          )}

          {/* Latency and Status Info */}
          <div className="pt-4 border-t border-white/10">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-400 mb-1">Translation Latency</div>
                <div className={`font-mono ${latencyStatus.color}`}>
                  {latency ? `${Math.round(latency)}ms` : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 mb-1">Status</div>
                <div className={`font-medium ${latencyStatus.color}`}>
                  {latencyStatus.status}
                </div>
              </div>
            </div>

            {/* Performance Warning */}
            {latency && latency > 500 && (
              <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.664-.833-2.464 0L5.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <p className="text-yellow-300 text-xs">
                    High latency detected. Consider switching to a lower quality setting or checking your network connection.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hidden audio element for voice previews */}
      <audio ref={previewAudioRef} style={{ display: 'none' }} />
    </div>
  );
};

export default TranslatedAudioSelector;