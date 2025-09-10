import { useEffect, useCallback, useState } from 'react'

export interface KeyboardShortcuts {
  mute: string
  captions: string
  record: string
  pushToTalk: string
  volumeUp: string
  volumeDown: string
}

export interface UseKeyboardShortcutsProps {
  onMute?: () => void
  onToggleCaptions?: () => void
  onToggleRecording?: () => void
  onPushToTalkStart?: () => void
  onPushToTalkEnd?: () => void
  onVolumeUp?: () => void
  onVolumeDown?: () => void
  onTogglePushToTalk?: () => void
  isCallActive?: boolean
  shortcuts?: Partial<KeyboardShortcuts>
}

export interface UseKeyboardShortcutsReturn {
  shortcuts: KeyboardShortcuts
  isPushToTalkActive: boolean
  isPushToTalkEnabled: boolean
  pushToTalkKey: string
  isKeyPressed: (key: string) => boolean
  
  // Configuration
  updateShortcuts: (newShortcuts: Partial<KeyboardShortcuts>) => void
  togglePushToTalkMode: () => void
  setPushToTalkKey: (key: string) => void
  
  // Help
  getShortcutHelp: () => string[]
}

const DEFAULT_SHORTCUTS: KeyboardShortcuts = {
  mute: 'KeyM',
  captions: 'KeyC', 
  record: 'KeyR',
  pushToTalk: 'Space',
  volumeUp: 'ArrowUp',
  volumeDown: 'ArrowDown'
}

export const useKeyboardShortcuts = ({
  onMute,
  onToggleCaptions,
  onToggleRecording,
  onPushToTalkStart,
  onPushToTalkEnd,
  onVolumeUp,
  onVolumeDown,
  onTogglePushToTalk,
  isCallActive = false,
  shortcuts: customShortcuts = {}
}: UseKeyboardShortcutsProps = {}): UseKeyboardShortcutsReturn => {
  const [shortcuts, setShortcuts] = useState<KeyboardShortcuts>({
    ...DEFAULT_SHORTCUTS,
    ...customShortcuts
  })
  
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set())
  const [isPushToTalkEnabled, setIsPushToTalkEnabled] = useState(false)
  const [isPushToTalkActive, setIsPushToTalkActive] = useState(false)
  const [pushToTalkKey, setPushToTalkKeyState] = useState(shortcuts.pushToTalk)

  // Convert key code to readable name
  const keyCodeToName = useCallback((code: string): string => {
    const keyNames: { [key: string]: string } = {
      'KeyM': 'M',
      'KeyC': 'C',
      'KeyR': 'R',
      'Space': 'Space',
      'ArrowUp': '↑',
      'ArrowDown': '↓',
      'Enter': 'Enter',
      'Escape': 'Esc',
      'Backspace': 'Backspace'
    }
    return keyNames[code] || code
  }, [])

  // Handle keydown events
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input fields
    const target = event.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return
    }

    const { code, ctrlKey, altKey, shiftKey, metaKey } = event
    
    // Track pressed keys
    setPressedKeys(prev => new Set([...prev, code]))

    // Only process shortcuts during active calls (except push-to-talk toggle)
    if (!isCallActive && code !== shortcuts.pushToTalk) {
      return
    }

    // Prevent default behavior for our shortcuts
    const isShortcut = Object.values(shortcuts).includes(code)
    if (isShortcut && !ctrlKey && !altKey && !shiftKey && !metaKey) {
      event.preventDefault()
    }

    switch (code) {
      case shortcuts.mute:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          onMute?.()
        }
        break

      case shortcuts.captions:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          onToggleCaptions?.()
        }
        break

      case shortcuts.record:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          onToggleRecording?.()
        }
        break

      case shortcuts.pushToTalk:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          if (isPushToTalkEnabled && !isPushToTalkActive) {
            setIsPushToTalkActive(true)
            onPushToTalkStart?.()
          }
        }
        break

      case shortcuts.volumeUp:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          onVolumeUp?.()
        }
        break

      case shortcuts.volumeDown:
        if (!ctrlKey && !altKey && !shiftKey && !metaKey) {
          event.preventDefault()
          onVolumeDown?.()
        }
        break
    }
  }, [
    shortcuts,
    isCallActive,
    isPushToTalkEnabled,
    isPushToTalkActive,
    onMute,
    onToggleCaptions,
    onToggleRecording,
    onPushToTalkStart,
    onVolumeUp,
    onVolumeDown
  ])

  // Handle keyup events
  const handleKeyUp = useCallback((event: KeyboardEvent) => {
    const { code } = event

    // Remove from pressed keys
    setPressedKeys(prev => {
      const newSet = new Set(prev)
      newSet.delete(code)
      return newSet
    })

    // Handle push-to-talk release
    if (code === shortcuts.pushToTalk && isPushToTalkEnabled && isPushToTalkActive) {
      event.preventDefault()
      setIsPushToTalkActive(false)
      onPushToTalkEnd?.()
    }
  }, [shortcuts.pushToTalk, isPushToTalkEnabled, isPushToTalkActive, onPushToTalkEnd])

  // Set up event listeners
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('keyup', handleKeyUp)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('keyup', handleKeyUp)
    }
  }, [handleKeyDown, handleKeyUp])

  // Update shortcuts
  const updateShortcuts = useCallback((newShortcuts: Partial<KeyboardShortcuts>) => {
    setShortcuts(prev => ({ ...prev, ...newShortcuts }))
  }, [])

  // Toggle push-to-talk mode
  const togglePushToTalkMode = useCallback(() => {
    setIsPushToTalkEnabled(prev => {
      const newState = !prev
      if (!newState && isPushToTalkActive) {
        setIsPushToTalkActive(false)
        onPushToTalkEnd?.()
      }
      onTogglePushToTalk?.()
      return newState
    })
  }, [isPushToTalkActive, onPushToTalkEnd, onTogglePushToTalk])

  // Set push-to-talk key
  const setPushToTalkKey = useCallback((key: string) => {
    setPushToTalkKeyState(key)
    setShortcuts(prev => ({ ...prev, pushToTalk: key }))
  }, [])

  // Check if key is currently pressed
  const isKeyPressed = useCallback((key: string): boolean => {
    return pressedKeys.has(key)
  }, [pressedKeys])

  // Get help text for shortcuts
  const getShortcutHelp = useCallback((): string[] => {
    const help = [
      `${keyCodeToName(shortcuts.mute)} - Toggle Mute`,
      `${keyCodeToName(shortcuts.captions)} - Toggle Captions`,
      `${keyCodeToName(shortcuts.record)} - Toggle Recording`,
      `${keyCodeToName(shortcuts.volumeUp)} / ${keyCodeToName(shortcuts.volumeDown)} - Volume Control`,
    ]

    if (isPushToTalkEnabled) {
      help.push(`Hold ${keyCodeToName(pushToTalkKey)} - Push to Talk`)
    }

    return help
  }, [shortcuts, isPushToTalkEnabled, pushToTalkKey, keyCodeToName])

  return {
    shortcuts,
    isPushToTalkActive,
    isPushToTalkEnabled,
    pushToTalkKey,
    isKeyPressed,
    
    updateShortcuts,
    togglePushToTalkMode,
    setPushToTalkKey,
    
    getShortcutHelp
  }
}