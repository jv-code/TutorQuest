import { useState } from 'react'
import { Button } from './ui/button'
import { ArrowRight } from 'lucide-react'
import { motion } from 'framer-motion'

export function AnswerInput({ onSubmit, disabled }) {
  const [answer, setAnswer] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (answer.trim() && !disabled) {
      onSubmit(answer)
      setAnswer('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-12">
      <input
        type="text"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer..."
        className="flex-1 text-lg h-48 px-16 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-teal focus:ring-2 focus:ring-teal/20 text-gray-800 font-mono transition-all"
        autoFocus
        disabled={disabled}
      />
      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
        <Button
          type="submit"
          className="h-48 px-24 bg-teal hover:bg-teal-600 text-white font-mono transition-all"
          disabled={!answer.trim() || disabled}
        >
          Submit
          <ArrowRight className="h-16 w-16 ml-8" />
        </Button>
      </motion.div>
    </form>
  )
}
