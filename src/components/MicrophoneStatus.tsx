import React, { useState, useEffect } from 'react'

const MicrophoneStatus: React.FC = () => {
  const [micStatus, setMicStatus] = useState<'checking' | 'granted' | 'denied' | 'unavailable'>('checking')

  useEffect(() => {
    const checkMicrophonePermission = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setMicStatus('unavailable')
          return
        }

        // Try to get microphone access
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          // Stop the stream immediately, we just wanted to check permission
          stream.getTracks().forEach(track => track.stop())
          setMicStatus('granted')
        } catch (error: any) {
          if (error.name === 'NotAllowedError') {
            setMicStatus('denied')
          } else if (error.name === 'NotFoundError') {
            setMicStatus('unavailable')
          } else {
            setMicStatus('unavailable')
          }
        }
      } catch (error) {
        setMicStatus('unavailable')
      }
    }

    checkMicrophonePermission()
  }, [])

  const getStatusInfo = () => {
    switch (micStatus) {
      case 'checking':
        return {
          icon: '⏳',
          text: 'Checking microphone...',
          color: 'text-yellow-700 bg-yellow-100 border-yellow-300'
        }
      case 'granted':
        return {
          icon: '🎤',
          text: 'Microphone ready',
          color: 'text-green-700 bg-green-100 border-green-300'
        }
      case 'denied':
        return {
          icon: '🔇',
          text: 'Microphone access denied. Please allow access and refresh.',
          color: 'text-red-700 bg-red-100 border-red-300'
        }
      case 'unavailable':
        return {
          icon: '❌',
          text: 'No microphone found. Please connect a microphone.',
          color: 'text-red-700 bg-red-100 border-red-300'
        }
    }
  }

  const status = getStatusInfo()

  return (
    <div className={`p-3 rounded-lg border text-sm ${status.color}`}>
      <div className="flex items-center space-x-2">
        <span className="text-lg">{status.icon}</span>
        <span>{status.text}</span>
      </div>
    </div>
  )
}

export default MicrophoneStatus