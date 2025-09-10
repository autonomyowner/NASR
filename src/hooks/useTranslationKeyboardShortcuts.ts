/**
 * Translation Keyboard Shortcuts Hook
 * 
 * Provides comprehensive keyboard navigation and shortcuts for translation features
 * with accessibility support and customizable key bindings.
 */

import { useEffect, useCallback, useRef } from 'react';
import type { TranslationMode } from '../types/translation';

interface KeyBinding {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  metaKey?: boolean;
  preventDefault?: boolean;
}

interface TranslationKeyboardShortcuts {
  toggleTranslation?: KeyBinding;
  cycleMode?: KeyBinding;
  pushToTranslate?: KeyBinding;
  clearCaptions?: KeyBinding;
  toggleSettings?: KeyBinding;
  increaseVolume?: KeyBinding;
  decreaseVolume?: KeyBinding;
  nextLanguage?: KeyBinding;
  prevLanguage?: KeyBinding;
  exportSession?: KeyBinding;
}

interface UseTranslationKeyboardShortcutsOptions {
  enabled?: boolean;
  shortcuts?: TranslationKeyboardShortcuts;
  preventDefaults?: boolean;
}

interface UseTranslationKeyboardShortcutsParams {
  // Translation controls
  onToggleTranslation?: () => void;
  onModeChange?: (mode: TranslationMode) => void;
  onPushToTranslateStart?: () => void;
  onPushToTranslateEnd?: () => void;
  
  // Caption controls
  onClearCaptions?: () => void;
  onToggleSettings?: () => void;
  
  // Audio controls
  onVolumeChange?: (delta: number) => void;
  
  // Language controls
  onNextLanguage?: () => void;
  onPrevLanguage?: () => void;
  
  // Session controls
  onExportSession?: () => void;
  
  // State
  currentMode?: TranslationMode;
  isTranslationEnabled?: boolean;
  isSettingsOpen?: boolean;
}

const DEFAULT_SHORTCUTS: TranslationKeyboardShortcuts = {
  toggleTranslation: { key: 't', ctrlKey: true, preventDefault: true },
  cycleMode: { key: 'm', ctrlKey: true, preventDefault: true },
  pushToTranslate: { key: ' ', preventDefault: true }, // Space bar
  clearCaptions: { key: 'c', ctrlKey: true, shiftKey: true, preventDefault: true },
  toggleSettings: { key: ',', ctrlKey: true, preventDefault: true },
  increaseVolume: { key: 'ArrowUp', ctrlKey: true, preventDefault: true },
  decreaseVolume: { key: 'ArrowDown', ctrlKey: true, preventDefault: true },
  nextLanguage: { key: 'ArrowRight', ctrlKey: true, preventDefault: true },
  prevLanguage: { key: 'ArrowLeft', ctrlKey: true, preventDefault: true },
  exportSession: { key: 's', ctrlKey: true, shiftKey: true, preventDefault: true }
};

export const useTranslationKeyboardShortcuts = (
  params: UseTranslationKeyboardShortcutsParams,
  options: UseTranslationKeyboardShortcutsOptions = {}
) => {
  const {
    enabled = true,
    shortcuts = DEFAULT_SHORTCUTS,
    preventDefaults = true
  } = options;

  const {
    onToggleTranslation,
    onModeChange,
    onPushToTranslateStart,
    onPushToTranslateEnd,
    onClearCaptions,
    onToggleSettings,
    onVolumeChange,
    onNextLanguage,
    onPrevLanguage,
    onExportSession,
    currentMode = 'off',
    isTranslationEnabled = false,
    isSettingsOpen = false
  } = params;

  // Track currently pressed keys for combinations
  const pressedKeysRef = useRef<Set<string>>(new Set());
  const isPushToTranslateActiveRef = useRef(false);

  // Check if key combination matches binding
  const matchesBinding = useCallback((event: KeyboardEvent, binding: KeyBinding): boolean => {
    return (
      event.key === binding.key &&
      !!event.ctrlKey === !!binding.ctrlKey &&
      !!event.shiftKey === !!binding.shiftKey &&
      !!event.altKey === !!binding.altKey &&
      !!event.metaKey === !!binding.metaKey
    );
  }, []);

  // Handle mode cycling
  const cycleModes = useCallback(() => {
    if (!onModeChange) return;
    
    const modes: TranslationMode[] = ['off', 'push', 'always'];
    const currentIndex = modes.indexOf(currentMode);
    const nextMode = modes[(currentIndex + 1) % modes.length];
    onModeChange(nextMode);
  }, [currentMode, onModeChange]);

  // Handle volume adjustment
  const adjustVolume = useCallback((delta: number) => {
    if (onVolumeChange) {
      onVolumeChange(delta);
    }
  }, [onVolumeChange]);

  // Handle keydown events
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    // Skip if user is typing in an input field
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.contentEditable === 'true'
    ) {
      return;
    }

    pressedKeysRef.current.add(event.key);

    // Toggle translation
    if (shortcuts.toggleTranslation && matchesBinding(event, shortcuts.toggleTranslation)) {
      if (shortcuts.toggleTranslation.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onToggleTranslation?.();
      return;
    }

    // Cycle translation mode
    if (shortcuts.cycleMode && matchesBinding(event, shortcuts.cycleMode)) {
      if (shortcuts.cycleMode.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      cycleModes();
      return;
    }

    // Push to translate (only in push mode)
    if (
      shortcuts.pushToTranslate &&
      matchesBinding(event, shortcuts.pushToTranslate) &&
      currentMode === 'push' &&
      isTranslationEnabled &&
      !event.repeat &&
      !isPushToTranslateActiveRef.current
    ) {
      if (shortcuts.pushToTranslate.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      isPushToTranslateActiveRef.current = true;
      onPushToTranslateStart?.();
      return;
    }

    // Clear captions
    if (shortcuts.clearCaptions && matchesBinding(event, shortcuts.clearCaptions)) {
      if (shortcuts.clearCaptions.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onClearCaptions?.();
      return;
    }

    // Toggle settings
    if (shortcuts.toggleSettings && matchesBinding(event, shortcuts.toggleSettings)) {
      if (shortcuts.toggleSettings.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onToggleSettings?.();
      return;
    }

    // Volume controls
    if (shortcuts.increaseVolume && matchesBinding(event, shortcuts.increaseVolume)) {
      if (shortcuts.increaseVolume.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      adjustVolume(0.1);
      return;
    }

    if (shortcuts.decreaseVolume && matchesBinding(event, shortcuts.decreaseVolume)) {
      if (shortcuts.decreaseVolume.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      adjustVolume(-0.1);
      return;
    }

    // Language navigation
    if (shortcuts.nextLanguage && matchesBinding(event, shortcuts.nextLanguage)) {
      if (shortcuts.nextLanguage.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onNextLanguage?.();
      return;
    }

    if (shortcuts.prevLanguage && matchesBinding(event, shortcuts.prevLanguage)) {
      if (shortcuts.prevLanguage.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onPrevLanguage?.();
      return;
    }

    // Export session
    if (shortcuts.exportSession && matchesBinding(event, shortcuts.exportSession)) {
      if (shortcuts.exportSession.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      onExportSession?.();
      return;
    }

    // Escape key - universal cancel/close
    if (event.key === 'Escape') {
      if (preventDefaults) {
        event.preventDefault();
      }
      
      // Priority order: settings > push-to-translate > disable translation
      if (isSettingsOpen) {
        onToggleSettings?.();
      } else if (isPushToTranslateActiveRef.current) {
        isPushToTranslateActiveRef.current = false;
        onPushToTranslateEnd?.();
      } else if (isTranslationEnabled) {
        onModeChange?.('off');
      }
      return;
    }
  }, [
    enabled,
    shortcuts,
    matchesBinding,
    preventDefaults,
    onToggleTranslation,
    cycleModes,
    currentMode,
    isTranslationEnabled,
    onPushToTranslateStart,
    onClearCaptions,
    onToggleSettings,
    adjustVolume,
    onNextLanguage,
    onPrevLanguage,
    onExportSession,
    isSettingsOpen,
    onPushToTranslateEnd,
    onModeChange
  ]);

  // Handle keyup events
  const handleKeyUp = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    pressedKeysRef.current.delete(event.key);

    // Handle push-to-translate release
    if (
      shortcuts.pushToTranslate &&
      matchesBinding(event, shortcuts.pushToTranslate) &&
      isPushToTranslateActiveRef.current
    ) {
      if (shortcuts.pushToTranslate.preventDefault && preventDefaults) {
        event.preventDefault();
      }
      isPushToTranslateActiveRef.current = false;
      onPushToTranslateEnd?.();
    }
  }, [
    enabled,
    shortcuts,
    matchesBinding,
    preventDefaults,
    onPushToTranslateEnd
  ]);

  // Clean up on window blur
  const handleWindowBlur = useCallback(() => {
    pressedKeysRef.current.clear();
    if (isPushToTranslateActiveRef.current) {
      isPushToTranslateActiveRef.current = false;
      onPushToTranslateEnd?.();
    }
  }, [onPushToTranslateEnd]);

  // Set up event listeners
  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    window.addEventListener('blur', handleWindowBlur);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('blur', handleWindowBlur);
    };
  }, [enabled, handleKeyDown, handleKeyUp, handleWindowBlur]);

  // Return current shortcut information for UI display
  const getShortcutDisplay = useCallback(() => {
    const formatShortcut = (binding: KeyBinding) => {
      const parts: string[] = [];
      if (binding.ctrlKey || binding.metaKey) {
        parts.push(navigator.platform.includes('Mac') ? '⌘' : 'Ctrl');
      }
      if (binding.shiftKey) parts.push('Shift');
      if (binding.altKey) parts.push('Alt');
      
      let key = binding.key;
      if (key === ' ') key = 'Space';
      else if (key.startsWith('Arrow')) key = key.replace('Arrow', '');
      
      parts.push(key);
      return parts.join(' + ');
    };

    return {
      toggleTranslation: shortcuts.toggleTranslation ? formatShortcut(shortcuts.toggleTranslation) : null,
      cycleMode: shortcuts.cycleMode ? formatShortcut(shortcuts.cycleMode) : null,
      pushToTranslate: shortcuts.pushToTranslate ? formatShortcut(shortcuts.pushToTranslate) : null,
      clearCaptions: shortcuts.clearCaptions ? formatShortcut(shortcuts.clearCaptions) : null,
      toggleSettings: shortcuts.toggleSettings ? formatShortcut(shortcuts.toggleSettings) : null,
      increaseVolume: shortcuts.increaseVolume ? formatShortcut(shortcuts.increaseVolume) : null,
      decreaseVolume: shortcuts.decreaseVolume ? formatShortcut(shortcuts.decreaseVolume) : null,
      nextLanguage: shortcuts.nextLanguage ? formatShortcut(shortcuts.nextLanguage) : null,
      prevLanguage: shortcuts.prevLanguage ? formatShortcut(shortcuts.prevLanguage) : null,
      exportSession: shortcuts.exportSession ? formatShortcut(shortcuts.exportSession) : null
    };
  }, [shortcuts]);

  return {
    getShortcutDisplay,
    isPushToTranslateActive: isPushToTranslateActiveRef.current
  };
};