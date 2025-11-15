import { Button } from './ui/button'
import { ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export function VideoDisplay({ videoUrl, onNextQuestion }) {
  if (!videoUrl) return null

  return (
    <AnimatePresence>
      <motion.div
        className="border-[3px] border-gray-900 rounded-lg overflow-hidden"
        style={{
          backgroundColor: '#dfe6e9',
          boxShadow: '6px 6px 0px 0px rgba(0,0,0,1)'
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.4 }}
      >
        <div className="border-l-4 border-teal p-24">
          <h3 className="text-sm font-mono font-semibold text-gray-600 uppercase tracking-wide mb-16">
            Video Explanation
          </h3>

          <video
            controls
            autoPlay
            muted
            className="w-full rounded-lg border border-gray-200 mb-20"
            src={videoUrl}
          />

          {onNextQuestion && (
            <Button
              onClick={onNextQuestion}
              className="w-full bg-teal hover:bg-teal-600 text-white font-mono"
            >
              Next Question
              <ArrowRight className="h-16 w-16 ml-8" />
            </Button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
