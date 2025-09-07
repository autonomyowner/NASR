import React, { useState, useEffect } from 'react'

interface CallTimerProps {
  isActive: boolean
  startTime?: number
}

const CallTimer: React.FC<CallTimerProps> = ({ isActive, startTime }) => {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!isActive || !startTime) {
      setElapsed(0)
      return
    }

    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)

    return () => clearInterval(timer)
  }, [isActive, startTime])

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (!isActive) return null

  return (
    <div className="text-center p-2 bg-green-100 rounded-lg">
      <div className="flex items-center justify-center space-x-2">
        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
        <span className="font-mono text-green-800 font-semibold">
          {formatTime(elapsed)}
        </span>
      </div>
    </div>
  )
}

export default CallTimer