import { useEffect } from 'react'
import confetti from 'canvas-confetti'

export function ConfettiEffect({ trigger }) {
  useEffect(() => {
    if (trigger) {
      const duration = 2000
      const animationEnd = Date.now() + duration
      const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 9999 }

      function randomInRange(min, max) {
        return Math.random() * (max - min) + min
      }

      const interval = setInterval(function() {
        const timeLeft = animationEnd - Date.now()

        if (timeLeft <= 0) {
          return clearInterval(interval)
        }

        const particleCount = 50 * (timeLeft / duration)

        confetti({
          ...defaults,
          particleCount,
          origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
          colors: ['#16AA98', '#F59E0B', '#383838']
        })
        confetti({
          ...defaults,
          particleCount,
          origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
          colors: ['#16AA98', '#F59E0B', '#383838']
        })
      }, 250)

      return () => clearInterval(interval)
    }
  }, [trigger])

  return null
}
