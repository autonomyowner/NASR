/**
 * Enhanced Captions View Component
 * 
 * Premium real-time captions with stable word highlighting, dual language support,
 * speaker identification, accessibility features, and HIVE glassmorphism design.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { Caption } from '../../types/translation';

interface CaptionsViewProps {
  captions: Caption[];
  showOriginal: boolean;
  showTranslated: boolean;
  stableWordThreshold: number;
  maxCaptions?: number;
  autoScroll?: boolean;
  onCaptionClick?: (caption: Caption) => void;
  isMinimized?: boolean;
  onToggleMinimized?: () => void;
  showSpeakerAvatars?: boolean;
  enableConfidenceIndicators?: boolean;
  fontSize?: 'small' | 'medium' | 'large';
  highContrastMode?: boolean;
}

const CaptionsView: React.FC<CaptionsViewProps> = ({
  captions,
  showOriginal,
  showTranslated,
  stableWordThreshold,
  maxCaptions = 50,
  autoScroll = true,
  onCaptionClick,
  isMinimized = false,
  onToggleMinimized,
  showSpeakerAvatars = true,
  enableConfidenceIndicators = true,
  fontSize = 'medium',
  highContrastMode = false
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [selectedCaption, setSelectedCaption] = useState<string | null>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();

  // Detect user scrolling to prevent auto-scroll interruption
  const handleScroll = useCallback(() => {
    setIsUserScrolling(true);
    
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    scrollTimeoutRef.current = setTimeout(() => {
      setIsUserScrolling(false);
    }, 2000);
  }, []);

  // Auto-scroll to bottom when new captions arrive (only if user isn't scrolling)
  useEffect(() => {
    if (autoScroll && !isUserScrolling && bottomRef.current && !isMinimized) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [captions, autoScroll, isUserScrolling, isMinimized]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!containerRef.current) return;

      switch (event.key) {
        case 'ArrowUp':
          event.preventDefault();
          // Navigate to previous caption
          break;
        case 'ArrowDown':
          event.preventDefault();
          // Navigate to next caption
          break;
        case 'Home':
          event.preventDefault();
          containerRef.current.scrollTop = 0;
          break;
        case 'End':
          event.preventDefault();
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
          break;
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      container.addEventListener('scroll', handleScroll);
      
      return () => {
        container.removeEventListener('keydown', handleKeyDown);
        container.removeEventListener('scroll', handleScroll);
      };
    }
  }, [handleScroll]);

  // Limit captions to prevent memory issues
  const visibleCaptions = captions.slice(-maxCaptions);

  const renderStableText = (text: string, wordStability: Record<string, number>, threshold: number) => {
    const words = text.split(' ');
    
    return (
      <span className="stable-text">
        {words.map((word, index) => {
          const stability = wordStability[word] || 0;
          const isStable = stability >= threshold;
          
          return (
            <span
              key={`${word}-${index}`}
              className={`word transition-all duration-300 ${
                isStable ? 'stable opacity-100' : 'unstable opacity-70'
              }`}
              data-confidence={stability}
              title={`Confidence: ${Math.round(stability * 100)}%`}
            >
              {word}
              {index < words.length - 1 && ' '}
            </span>
          );
        })}
      </span>
    );
  };

  // Get font size classes
  const getFontSizeClasses = () => {
    switch (fontSize) {
      case 'small': return 'text-xs';
      case 'large': return 'text-base';
      default: return 'text-sm';
    }
  };

  // Get speaker avatar color
  const getSpeakerColor = (speakerName: string) => {
    const colors = [
      'from-hive-cyan to-cyan-400',
      'from-emerald-500 to-emerald-400',
      'from-blue-500 to-blue-400',
      'from-purple-500 to-purple-400',
      'from-pink-500 to-pink-400',
      'from-orange-500 to-orange-400'
    ];
    const index = speakerName.length % colors.length;
    return colors[index];
  };

  if (captions.length === 0) {
    return (
      <div className={`captions-container glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-2xl shadow-2xl transition-all duration-300 ${
        isMinimized ? 'h-16' : 'min-h-[200px]'
      }`}>
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-hive-cyan/20 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-hive-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10m0 0V6a2 2 0 00-2-2H9a2 2 0 00-2 2v2m0 0v10a2 2 0 002 2h6a2 2 0 002-2V8" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white">Live Captions</h3>
            <span className="text-xs text-gray-400">Ready</span>
          </div>
          
          {onToggleMinimized && (
            <button
              onClick={onToggleMinimized}
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
              aria-label={isMinimized ? 'Expand captions' : 'Minimize captions'}
            >
              <svg className={`w-4 h-4 transition-transform duration-200 ${isMinimized ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>

        {!isMinimized && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-3">
              <svg className="w-16 h-16 mx-auto opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <p className="text-gray-300 font-medium mb-1">Ready for Captions</p>
            <p className="text-gray-400 text-xs max-w-xs mx-auto">
              Start speaking to see real-time transcription and translation appear here
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div 
      className={`captions-container glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-2xl shadow-2xl transition-all duration-300 ${
        highContrastMode ? 'bg-black/90 border-white/50' : ''
      } ${isMinimized ? 'h-16' : ''}`}
      role="log"
      aria-live="polite"
      aria-label="Live captions display"
    >
      {/* Enhanced Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 bg-hive-cyan/20 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-hive-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10m0 0V6a2 2 0 00-2-2H9a2 2 0 00-2 2v2m0 0v10a2 2 0 002 2h6a2 2 0 002-2V8" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">Live Captions</h3>
            <div className="flex items-center space-x-2">
              {showOriginal && (
                <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded-full">
                  Original
                </span>
              )}
              {showTranslated && (
                <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-300 rounded-full">
                  Translation
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Live indicator */}
          {visibleCaptions.some(c => !c.isStable) && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-red-400 font-medium">LIVE</span>
            </div>
          )}
          
          {/* Auto-scroll indicator */}
          {isUserScrolling && (
            <div className="text-xs text-yellow-400 bg-yellow-500/20 px-2 py-1 rounded-full">
              Manual scroll
            </div>
          )}
          
          {/* Minimize button */}
          {onToggleMinimized && (
            <button
              onClick={onToggleMinimized}
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
              aria-label={isMinimized ? 'Expand captions' : 'Minimize captions'}
            >
              <svg className={`w-4 h-4 transition-transform duration-200 ${isMinimized ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Enhanced Captions List */}
          <div 
            ref={containerRef}
            className={`max-h-80 overflow-y-auto p-4 space-y-3 ${getFontSizeClasses()} scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/20`}
            style={{ scrollBehavior: 'smooth' }}
            tabIndex={0}
            role="region"
            aria-label="Captions list - use arrow keys to navigate"
          >
            {visibleCaptions.map(caption => (
              <CaptionLine
                key={caption.id}
                caption={caption}
                showOriginal={showOriginal}
                showTranslated={showTranslated}
                stableWordThreshold={stableWordThreshold}
                showSpeakerAvatars={showSpeakerAvatars}
                enableConfidenceIndicators={enableConfidenceIndicators}
                highContrastMode={highContrastMode}
                isSelected={selectedCaption === caption.id}
                onClick={() => {
                  setSelectedCaption(caption.id);
                  onCaptionClick?.(caption);
                }}
                renderStableText={renderStableText}
                getSpeakerColor={getSpeakerColor}
              />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Enhanced Footer with detailed stats */}
          <div className="px-4 py-3 border-t border-white/10 bg-white/5">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-4 text-gray-400">
                <span>{captions.length} total</span>
                <span className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>{captions.filter(c => c.isStable).length} stable</span>
                </span>
                {captions.length > 0 && (
                  <span>
                    {Math.round((captions.filter(c => c.isStable).length / captions.length) * 100)}% stable
                  </span>
                )}
              </div>
              
              <div className="flex items-center space-x-2">
                {enableConfidenceIndicators && captions.length > 0 && (
                  <span className="text-gray-400">
                    Avg confidence: {Math.round(captions.reduce((sum, c) => sum + c.confidence, 0) / captions.length * 100)}%
                  </span>
                )}
                
                <button
                  onClick={() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' })}
                  className="text-gray-400 hover:text-white transition-colors"
                  aria-label="Scroll to bottom"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

interface CaptionLineProps {
  caption: Caption;
  showOriginal: boolean;
  showTranslated: boolean;
  stableWordThreshold: number;
  showSpeakerAvatars?: boolean;
  enableConfidenceIndicators?: boolean;
  highContrastMode?: boolean;
  isSelected?: boolean;
  onClick?: () => void;
  renderStableText: (text: string, wordStability: Record<string, number>, threshold: number) => React.ReactElement;
  getSpeakerColor: (speakerName: string) => string;
}

const CaptionLine: React.FC<CaptionLineProps> = ({
  caption,
  showOriginal,
  showTranslated,
  stableWordThreshold,
  showSpeakerAvatars = true,
  enableConfidenceIndicators = true,
  highContrastMode = false,
  isSelected = false,
  onClick,
  renderStableText,
  getSpeakerColor
}) => {
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div 
      className={`caption-line p-4 rounded-xl transition-all duration-300 ${
        isSelected 
          ? 'bg-hive-cyan/20 border-2 border-hive-cyan/50 shadow-lg' 
          : caption.isStable 
            ? `bg-white/10 border border-green-400/30 ${highContrastMode ? 'bg-white/20 border-white/50' : ''}` 
            : `bg-white/5 border border-yellow-400/30 ${highContrastMode ? 'bg-white/10 border-yellow-400/60' : ''}`
      } ${onClick ? 'cursor-pointer hover:bg-white/15 hover:scale-[1.02]' : ''} ${
        highContrastMode ? 'shadow-lg' : ''
      }`}
      onClick={onClick}
      role="article"
      aria-label={`Caption from ${caption.speakerName} at ${formatTime(caption.timestamp)}`}
    >
      {/* Enhanced Header with speaker avatar and timestamp */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          {/* Speaker Avatar */}
          {showSpeakerAvatars && (
            <div className={`w-8 h-8 bg-gradient-to-br ${getSpeakerColor(caption.speakerName)} rounded-full flex items-center justify-center flex-shrink-0`}>
              <span className="text-slate-900 font-bold text-xs">
                {caption.speakerName.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
          
          <div className="min-w-0 flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <span className={`font-medium ${highContrastMode ? 'text-white' : 'text-white'}`}>
                {caption.speakerName}
              </span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-400 text-xs">
                {formatTime(caption.timestamp)}
              </span>
              {caption.originalLanguage && (
                <>
                  <span className="text-gray-400">•</span>
                  <span className="text-blue-300 text-xs bg-blue-500/20 px-2 py-0.5 rounded-full">
                    {caption.originalLanguage.toUpperCase()}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        
        {/* Status indicators */}
        <div className="flex items-center space-x-2 flex-shrink-0">
          {enableConfidenceIndicators && (
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${getConfidenceColor(caption.confidence).replace('text-', 'bg-')}`} />
              <span className={`text-xs font-mono ${getConfidenceColor(caption.confidence)}`}>
                {Math.round(caption.confidence * 100)}%
              </span>
            </div>
          )}
          
          {!caption.isStable && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" title="Processing..." />
              <span className="text-xs text-yellow-400 font-medium">Processing</span>
            </div>
          )}
          
          {caption.isStable && (
            <div className="w-2 h-2 bg-green-400 rounded-full" title="Stable" />
          )}
        </div>
      </div>

      {/* Enhanced Original text */}
      {showOriginal && caption.text && (
        <div className="mb-3">
          <div className="flex items-center space-x-2 text-xs text-blue-300 mb-2">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h10M7 16h10" />
            </svg>
            <span>Original</span>
          </div>
          <div className={`${highContrastMode ? 'text-white font-medium' : 'text-white'} text-sm leading-relaxed`}>
            {caption.wordStability ? 
              renderStableText(caption.text, caption.wordStability, stableWordThreshold) :
              caption.text
            }
          </div>
        </div>
      )}

      {/* Enhanced Translated text */}
      {showTranslated && caption.translatedText && (
        <div>
          <div className="flex items-center space-x-2 text-xs text-emerald-300 mb-2">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span>Translation</span>
            {caption.targetLanguage && (
              <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-200 rounded-full text-xs">
                {caption.targetLanguage.toUpperCase()}
              </span>
            )}
          </div>
          <div className={`${highContrastMode ? 'text-emerald-200 font-medium' : 'text-emerald-100'} text-sm font-medium leading-relaxed`}>
            {caption.translatedText}
          </div>
        </div>
      )}

      {/* Enhanced Processing indicator */}
      {!caption.isStable && (
        <div className="mt-3 flex items-center justify-center space-x-2 p-2 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
          <div className="flex space-x-1">
            <div className="w-1 h-1 bg-yellow-400 rounded-full animate-ping" style={{ animationDelay: '0ms' }} />
            <div className="w-1 h-1 bg-yellow-400 rounded-full animate-ping" style={{ animationDelay: '150ms' }} />
            <div className="w-1 h-1 bg-yellow-400 rounded-full animate-ping" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-xs text-yellow-300 font-medium">Processing translation...</span>
        </div>
      )}
    </div>
  );
};

export default CaptionsView;