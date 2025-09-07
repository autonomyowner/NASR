import React, { useEffect, useState } from 'react'
import type { IncomingCall } from '../hooks/useIncomingCall'

interface IncomingCallModalProps {
  incomingCall: IncomingCall | null
  isRinging: boolean
  onAccept: () => Promise<void>
  onDecline: () => void
}

const IncomingCallModal: React.FC<IncomingCallModalProps> = ({
  incomingCall,
  isRinging,
  onAccept,
  onDecline
}) => {
  const [timeRemaining, setTimeRemaining] = useState(30)
  const [isAccepting, setIsAccepting] = useState(false)

  // Countdown timer
  useEffect(() => {
    if (incomingCall && isRinging) {
      const startTime = incomingCall.timestamp
      const timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000)
        const remaining = Math.max(0, 30 - elapsed)
        setTimeRemaining(remaining)
        
        if (remaining === 0) {
          onDecline()
        }
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [incomingCall, isRinging, onDecline])

  const handleAccept = async () => {
    setIsAccepting(true)
    try {
      await onAccept()
    } finally {
      setIsAccepting(false)
    }
  }

  if (!incomingCall || !isRinging) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl border border-gray-200">
        {/* Pulsing Ring Animation */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center animate-pulse">
              <span className="text-3xl text-white">📞</span>
            </div>
            {/* Ripple effect */}
            <div className="absolute inset-0 w-20 h-20 bg-green-400 rounded-full animate-ping opacity-25"></div>
            <div className="absolute inset-0 w-20 h-20 bg-green-400 rounded-full animate-ping opacity-25 animation-delay-200"></div>
          </div>
        </div>

        {/* Incoming Call Info */}
        <div className="text-center mb-6">
          <h3 className="text-2xl font-bold text-gray-800 mb-2">Incoming Call</h3>
          <p className="text-lg text-gray-600 mb-1">From:</p>
          <p className="text-xl font-semibold text-gray-800 font-mono bg-gray-100 px-3 py-2 rounded-lg">
            {incomingCall.fromPeerId}
          </p>
        </div>

        {/* Timer */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm">
            <span className="mr-1">⏱️</span>
            Auto-decline in {timeRemaining}s
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4">
          <button
            onClick={onDecline}
            disabled={isAccepting}
            className="flex-1 bg-red-500 text-white py-4 px-6 rounded-xl font-semibold hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="text-xl mr-2">📵</span>
            Decline
          </button>
          
          <button
            onClick={handleAccept}
            disabled={isAccepting}
            className="flex-1 bg-green-500 text-white py-4 px-6 rounded-xl font-semibold hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAccepting ? (
              <>
                <span className="animate-spin mr-2">⏳</span>
                Connecting...
              </>
            ) : (
              <>
                <span className="text-xl mr-2">📞</span>
                Accept
              </>
            )}
          </button>
        </div>

        {/* Call Quality Info */}
        <div className="mt-4 text-center text-xs text-gray-500">
          Voice call with real-time translation available
        </div>
      </div>
    </div>
  )
}

export default IncomingCallModal