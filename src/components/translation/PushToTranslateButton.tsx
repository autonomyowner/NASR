/**
 * Enhanced Push-to-Translate Button Component
 * 
 * Premium push-to-talk style translation control with smooth animations,
 * haptic feedback, visual ripple effects, and mode switching with HIVE design.
 */

import React, { useCallback, useEffect, useState, useRef } from 'react';

type TranslationMode = 'always' | 'push' | 'off';

interface PushToTranslateButtonProps {
  isPressed: boolean;
  onPressStart: () => void;
  onPressEnd: () => void;
  translationMode: TranslationMode;
  onModeChange: (mode: TranslationMode) => void;
  disabled?: boolean;
  isTranslating?: boolean;
  showModeSelector?: boolean;
  isCompact?: boolean;
  customShortcuts?: boolean;
  enableHapticFeedback?: boolean;
}

const PushToTranslateButton: React.FC<PushToTranslateButtonProps> = ({
  isPressed,
  onPressStart,
  onPressEnd,
  translationMode,
  onModeChange,
  disabled = false,
  isTranslating = false,
  showModeSelector = true,
  isCompact = false,
  customShortcuts = true,
  enableHapticFeedback = true
}) => {
  const [isHolding, setIsHolding] = useState(false);
  const [rippleEffect, setRippleEffect] = useState<{ x: number; y: number; id: string } | null>(null);
  const [pressStartTime, setPressStartTime] = useState<number | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const rippleTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Haptic feedback function
  const triggerHapticFeedback = useCallback((type: 'start' | 'end' = 'start') => {
    if (enableHapticFeedback && 'vibrate' in navigator) {
      if (type === 'start') {
        navigator.vibrate(50); // Short vibration for press
      } else {
        navigator.vibrate(30); // Shorter vibration for release
      }
    }
  }, [enableHapticFeedback]);

  // Create ripple effect
  const createRipple = useCallback((event: React.MouseEvent | React.TouchEvent) => {
    if (!buttonRef.current) return;
    
    const rect = buttonRef.current.getBoundingClientRect();
    const x = ('touches' in event ? event.touches[0].clientX : event.clientX) - rect.left;
    const y = ('touches' in event ? event.touches[0].clientY : event.clientY) - rect.top;
    
    const rippleId = Math.random().toString(36).substr(2, 9);
    setRippleEffect({ x, y, id: rippleId });
    
    if (rippleTimeoutRef.current) {
      clearTimeout(rippleTimeoutRef.current);
    }
    
    rippleTimeoutRef.current = setTimeout(() => {
      setRippleEffect(null);
    }, 600);
  }, []);

  // Enhanced keyboard shortcuts
  useEffect(() => {
    if (!customShortcuts) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (disabled) return;
      
      // Space bar for push-to-translate
      if (event.code === 'Space' && translationMode === 'push' && !event.repeat) {
        event.preventDefault();
        if (!isHolding) {
          setIsHolding(true);
          setPressStartTime(Date.now());
          triggerHapticFeedback('start');
          onPressStart();
        }
      }
      
      // Ctrl/Cmd + T to toggle translation mode
      if ((event.ctrlKey || event.metaKey) && event.key === 't') {
        event.preventDefault();
        const modes: TranslationMode[] = ['off', 'push', 'always'];
        const currentIndex = modes.indexOf(translationMode);
        const nextMode = modes[(currentIndex + 1) % modes.length];
        onModeChange(nextMode);
        triggerHapticFeedback('start');
      }
      
      // Escape to turn off translation
      if (event.key === 'Escape' && translationMode !== 'off') {
        event.preventDefault();
        onModeChange('off');
        triggerHapticFeedback('end');
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (disabled || translationMode !== 'push') return;
      
      if (event.code === 'Space' && isHolding) {
        event.preventDefault();
        setIsHolding(false);
        setPressStartTime(null);
        triggerHapticFeedback('end');
        onPressEnd();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
    };
  }, [disabled, translationMode, isHolding, onPressStart, onPressEnd, onModeChange, customShortcuts, triggerHapticFeedback]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (disabled || translationMode !== 'push') return;
    setIsHolding(true);
    setPressStartTime(Date.now());
    createRipple(e);
    triggerHapticFeedback('start');
    onPressStart();
  }, [disabled, translationMode, onPressStart, createRipple, triggerHapticFeedback]);

  const handleMouseUp = useCallback(() => {
    if (disabled || translationMode !== 'push') return;
    setIsHolding(false);
    setPressStartTime(null);
    triggerHapticFeedback('end');
    onPressEnd();
  }, [disabled, translationMode, onPressEnd, triggerHapticFeedback]);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault(); // Prevent mouse events
    if (disabled || translationMode !== 'push') return;
    setIsHolding(true);
    setPressStartTime(Date.now());
    createRipple(e);
    triggerHapticFeedback('start');
    onPressStart();
  }, [disabled, translationMode, onPressStart, createRipple, triggerHapticFeedback]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.preventDefault(); // Prevent mouse events
    if (disabled || translationMode !== 'push') return;
    setIsHolding(false);
    setPressStartTime(null);
    triggerHapticFeedback('end');
    onPressEnd();
  }, [disabled, translationMode, onPressEnd, triggerHapticFeedback]);

  // Helper functions
  const getModeIcon = (mode: TranslationMode) => {
    switch (mode) {
      case 'always': return '🌐';
      case 'push': return '🎤';
      case 'off': return '🚫';
      default: return '❓';
    }
  };

  const getModeLabel = (mode: TranslationMode) => {
    switch (mode) {
      case 'always': return 'Always On';
      case 'push': return 'Push to Talk';
      case 'off': return 'Disabled';
      default: return 'Unknown';
    }
  };

  const getModeDescription = (mode: TranslationMode) => {
    switch (mode) {
      case 'always': return 'Automatic translation for all speech';
      case 'push': return 'Hold button or spacebar to translate';
      case 'off': return 'Translation is disabled';
      default: return '';
    }
  };

  const getButtonStyle = () => {
    if (disabled) return 'bg-gray-500/50 cursor-not-allowed opacity-50 border-gray-500/30';
    
    const baseClasses = 'transition-all duration-200 ease-out transform border-2';
    
    switch (translationMode) {
      case 'always':
        return `${baseClasses} ${
          isTranslating 
            ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 hover:bg-emerald-500/30 animate-pulse scale-105 shadow-lg shadow-emerald-500/25'
            : 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/30 hover:scale-105 shadow-lg'
        }`;
      case 'push':
        return `${baseClasses} ${
          (isPressed || isHolding)
            ? 'bg-hive-cyan/30 border-hive-cyan text-white scale-110 shadow-2xl shadow-hive-cyan/30 animate-pulse'
            : 'bg-hive-cyan/20 border-hive-cyan/50 text-hive-cyan hover:bg-hive-cyan/30 hover:scale-105 hover:shadow-xl hover:shadow-hive-cyan/20'
        }`;
      case 'off':
        return `${baseClasses} bg-gray-500/20 border-gray-500/50 text-gray-400 hover:bg-gray-500/30 hover:scale-105`;
      default:
        return `${baseClasses} bg-gray-500/20 border-gray-500/50 text-gray-400`;
    }
  };

  // Get press duration for visual feedback
  const getPressProgress = () => {
    if (!pressStartTime || !isHolding) return 0;
    const duration = Date.now() - pressStartTime;
    return Math.min(duration / 1000, 1); // Normalize to 0-1 over 1 second
  };

  // Compact mode
  if (isCompact) {
    return (
      <div className="push-to-translate-compact">
        {translationMode === 'push' && (
          <button
            ref={buttonRef}
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            disabled={disabled}
            className={`relative overflow-hidden w-16 h-16 rounded-2xl font-bold select-none ${getButtonStyle()}`}
            aria-label={isHolding ? 'Translating...' : 'Hold to translate'}
          >
            {/* Ripple effect */}
            {rippleEffect && (
              <div
                className="absolute bg-white/30 rounded-full pointer-events-none animate-ping"
                style={{
                  left: rippleEffect.x - 10,
                  top: rippleEffect.y - 10,
                  width: 20,
                  height: 20,
                }}
              />
            )}
            
            <div className="relative z-10 flex flex-col items-center justify-center h-full">
              <div className="text-2xl">
                {(isPressed || isHolding) ? '🔊' : '🎤'}
              </div>
            </div>
          </button>
        )}
        
        {translationMode === 'always' && (
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 border-2 border-emerald-500/50 flex items-center justify-center">
            <div className={`text-2xl ${isTranslating ? 'animate-pulse' : ''}`}>🌐</div>
          </div>
        )}
        
        {translationMode === 'off' && (
          <div className="w-16 h-16 rounded-2xl bg-gray-500/20 border-2 border-gray-500/50 flex items-center justify-center">
            <div className="text-2xl opacity-50">🚫</div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="push-to-translate glass-effect backdrop-blur-xl bg-slate-900/80 border border-hive-cyan/30 rounded-2xl shadow-2xl">
      
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-hive-cyan/20 rounded-xl flex items-center justify-center">
            <span className="text-xl">{getModeIcon(translationMode)}</span>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Translation Control</h3>
            <p className="text-sm text-gray-400">{getModeDescription(translationMode)}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className={`text-xs px-3 py-1 rounded-full font-medium ${
            translationMode === 'always' ? 'bg-emerald-500/20 text-emerald-300' :
            translationMode === 'push' ? 'bg-hive-cyan/20 text-hive-cyan' :
            'bg-gray-500/20 text-gray-400'
          }`}>
            {getModeLabel(translationMode)}
          </span>
        </div>
      </div>

      <div className="p-6">
        {/* Mode Selector */}
        {showModeSelector && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-white mb-3">
              Translation Mode
            </label>
            <div className="grid grid-cols-3 gap-3">
              {(['always', 'push', 'off'] as TranslationMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => onModeChange(mode)}
                  disabled={disabled}
                  className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                    translationMode === mode
                      ? 'bg-hive-cyan/20 text-hive-cyan border-hive-cyan shadow-lg'
                      : 'bg-white/5 text-gray-400 border-white/20 hover:border-white/40 hover:bg-white/10'
                  } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className="text-center">
                    <div className="text-2xl mb-2">{getModeIcon(mode)}</div>
                    <div className="text-sm font-medium">{getModeLabel(mode)}</div>
                    <div className="text-xs text-gray-500 mt-1 leading-tight">
                      {getModeDescription(mode).split(' ').slice(0, 3).join(' ')}...
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Push-to-Translate Button */}
        {translationMode === 'push' && (
          <div className="space-y-4">
            <button
              ref={buttonRef}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              disabled={disabled}
              className={`relative overflow-hidden w-full py-8 px-6 rounded-2xl font-bold select-none ${getButtonStyle()}`}
              aria-label={isHolding ? 'Translating...' : 'Hold to translate'}
            >
              {/* Ripple effect */}
              {rippleEffect && (
                <div
                  className="absolute bg-white/30 rounded-full pointer-events-none"
                  style={{
                    left: rippleEffect.x - 25,
                    top: rippleEffect.y - 25,
                    width: 50,
                    height: 50,
                    animation: 'ripple 0.6s ease-out forwards'
                  }}
                />
              )}
              
              {/* Progress ring for press duration */}
              {isHolding && pressStartTime && (
                <div className="absolute inset-4 rounded-xl border-2 border-white/30">
                  <div 
                    className="absolute inset-0 rounded-xl border-2 border-white transition-all duration-100"
                    style={{
                      clipPath: `polygon(0 0, ${getPressProgress() * 100}% 0, ${getPressProgress() * 100}% 100%, 0 100%)`
                    }}
                  />
                </div>
              )}
              
              <div className="relative z-10 flex flex-col items-center space-y-3">
                <div className={`text-6xl transition-all duration-200 ${
                  (isPressed || isHolding) ? 'scale-110' : 'scale-100'
                }`}>
                  {(isPressed || isHolding) ? '🔊' : '🎤'}
                </div>
                <div className="text-xl font-bold">
                  {(isPressed || isHolding) ? 'Translating...' : 'Hold to Translate'}
                </div>
                {(isPressed || isHolding) && (
                  <div className="flex items-center space-x-1 text-sm">
                    <div className="w-1 h-1 bg-current rounded-full animate-ping" />
                    <div className="w-1 h-1 bg-current rounded-full animate-ping" style={{ animationDelay: '0.2s' }} />
                    <div className="w-1 h-1 bg-current rounded-full animate-ping" style={{ animationDelay: '0.4s' }} />
                  </div>
                )}
              </div>
            </button>
            
            <div className="text-center space-y-2">
              <div className="flex items-center justify-center space-x-4 text-xs text-gray-400">
                <div className="flex items-center space-x-1">
                  <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20">Space</kbd>
                  <span>Hold to translate</span>
                </div>
                {customShortcuts && (
                  <>
                    <div className="flex items-center space-x-1">
                      <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20">⌘T</kbd>
                      <span>Toggle mode</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20">Esc</kbd>
                      <span>Disable</span>
                    </div>
                  </>
                )}
              </div>
              
              {isTranslating && (
                <div className="flex items-center justify-center space-x-2 text-emerald-400">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  <span className="text-sm font-medium">Active translation in progress...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Always-on Mode Display */}
        {translationMode === 'always' && (
          <div className="text-center py-8">
            <div className="w-24 h-24 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border-2 border-emerald-500/30">
              <div className={`text-4xl ${isTranslating ? 'animate-pulse' : ''}`}>🌐</div>
            </div>
            <h4 className="text-xl font-bold text-emerald-300 mb-2">Always-On Translation</h4>
            <p className="text-gray-400 mb-4 max-w-xs mx-auto">
              All speech is being automatically translated in real-time
            </p>
            
            {isTranslating && (
              <div className="flex items-center justify-center space-x-2 text-emerald-400">
                <div className="flex space-x-1">
                  <div className="w-1 h-1 bg-emerald-400 rounded-full animate-ping" />
                  <div className="w-1 h-1 bg-emerald-400 rounded-full animate-ping" style={{ animationDelay: '0.2s' }} />
                  <div className="w-1 h-1 bg-emerald-400 rounded-full animate-ping" style={{ animationDelay: '0.4s' }} />
                </div>
                <span className="text-sm font-medium">Processing...</span>
              </div>
            )}
          </div>
        )}

        {/* Off Mode Display */}
        {translationMode === 'off' && (
          <div className="text-center py-8">
            <div className="w-24 h-24 bg-gray-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border-2 border-gray-500/30">
              <div className="text-4xl opacity-50">🚫</div>
            </div>
            <h4 className="text-xl font-bold text-gray-400 mb-2">Translation Disabled</h4>
            <p className="text-gray-500 mb-4 max-w-xs mx-auto">
              Select a different mode above to enable real-time translation
            </p>
            
            {customShortcuts && (
              <p className="text-xs text-gray-500">
                Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/20">⌘T</kbd> to cycle modes
              </p>
            )}
          </div>
        )}
      </div>
      
      {/* Custom ripple animation styles */}
      <style>{`
        @keyframes ripple {
          0% {
            transform: scale(0);
            opacity: 1;
          }
          100% {
            transform: scale(2);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

export default PushToTranslateButton;