import { useState, useEffect } from 'react'

interface TypewriterEffectProps {
  words: string[]
  speed?: number
  pauseTime?: number
  className?: string
}

const TypewriterEffect = ({ 
  words, 
  speed = 100, 
  pauseTime = 2000, 
  className = '' 
}: TypewriterEffectProps) => {
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [currentText, setCurrentText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [isPaused, setIsPaused] = useState(false)

  useEffect(() => {
    const currentWord = words[currentWordIndex]
    
    const timeout = setTimeout(() => {
      if (isPaused) {
        setIsPaused(false)
        setIsDeleting(true)
        return
      }

      if (isDeleting) {
        setCurrentText(currentText.slice(0, -1))
        
        if (currentText === '') {
          setIsDeleting(false)
          setCurrentWordIndex((prev) => (prev + 1) % words.length)
        }
      } else {
        setCurrentText(currentWord.slice(0, currentText.length + 1))
        
        if (currentText === currentWord) {
          setIsPaused(true)
        }
      }
    }, isPaused ? pauseTime : isDeleting ? speed / 2 : speed)

    return () => clearTimeout(timeout)
  }, [currentText, isDeleting, isPaused, currentWordIndex, words, speed, pauseTime])

  return (
    <span className={`inline-block ${className}`} aria-live="polite">
      {currentText}
      <span 
        className="inline-block w-0.5 h-6 bg-cyan-400 ml-1 animate-pulse"
        aria-hidden="true"
      />
    </span>
  )
}

export default TypewriterEffect