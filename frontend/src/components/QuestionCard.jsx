import { AnswerInput } from './AnswerInput'
import { motion } from 'framer-motion'

export function QuestionCard({ question, topic, difficulty, attempts, onSubmit, disabled }) {
  const attemptDots = [0, 1, 2].map(i => ({
    filled: i < attempts,
    color: i < attempts ? (attempts <= 1 ? 'bg-teal' : attempts === 2 ? 'bg-amber' : 'bg-red-500') : 'bg-gray-200'
  }))

  return (
    <motion.div
      className="border-[3px] border-gray-900 rounded-lg overflow-hidden"
      style={{
        backgroundColor: '#dfe6e9',
        boxShadow: '6px 6px 0px 0px rgba(0,0,0,1)'
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="border-l-4 border-teal px-24 py-20">
        <div className="flex items-start justify-between mb-16">
          <h2 className="text-sm font-mono font-semibold text-gray-600 uppercase tracking-wide">{topic}</h2>
          <div className="flex items-center gap-4">
            {attemptDots.map((dot, i) => (
              <motion.div
                key={i}
                className={`w-8 h-8 rounded-full ${dot.color}`}
                initial={{ scale: 0 }}
                animate={{ scale: dot.filled ? 1 : 1 }}
                transition={{ duration: 0.2, delay: i * 0.1 }}
              />
            ))}
          </div>
        </div>

        <div className="mb-24">
          <p className="text-3xl font-mono font-bold text-gray-800">{question}</p>
        </div>

        <AnswerInput onSubmit={onSubmit} disabled={disabled} />
      </div>
    </motion.div>
  )
}
