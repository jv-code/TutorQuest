import { useChat } from './hooks/useChat'
import { ChatMessage } from './components/ChatMessage'
import { QuestionCard } from './components/QuestionCard'
import { VideoDisplay } from './components/VideoDisplay'
import { DifficultyControl } from './components/DifficultyControl'
import { ConfettiEffect } from './components/ConfettiEffect'
import { Button } from './components/ui/button'
import { Calculator, Video, TrendingUp } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react'

function App() {
  const {
    messages,
    currentQuestion,
    attempts,
    loading,
    offerVideo,
    generatingVideo,
    showConfetti,
    currentVideoUrl,
    userDifficulty,
    submitAnswer,
    requestVideo,
    loadNextQuestion,
    updateDifficulty
  } = useChat()

  const messagesEndRef = useRef(null)
  const [completedCount, setCompletedCount] = useState(0)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const correctMessages = messages.filter(m => m.content?.includes('Correct'))
    setCompletedCount(correctMessages.length)
  }, [messages])

  return (
    <div
      className="min-h-screen"
      style={{
        backgroundColor: '#b2bec3',
        backgroundImage: `
          linear-gradient(to right, #95a5a6 1px, transparent 1px),
          linear-gradient(to bottom, #95a5a6 1px, transparent 1px)
        `,
        backgroundSize: '20px 20px'
      }}
    >
      <ConfettiEffect trigger={showConfetti} />
      <header className="backdrop-blur-sm border-b border-gray-400 sticky top-0 z-50" style={{ backgroundColor: '#dfe6e9e6' }}>
        <div className="max-w-7xl mx-auto px-24 py-16">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-12">
              <Calculator className="h-24 w-24 text-teal" />
              <h1 className="text-2xl font-mono font-bold text-gray-800">Poocho</h1>
            </div>
            <div className="flex items-center gap-24">
              <SignedOut>
                <SignInButton mode="modal" />
                <SignUpButton mode="modal" />
              </SignedOut>
              <SignedIn>
                <UserButton />
              </SignedIn>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-24 py-32">
        <div className="grid grid-cols-[1fr_400px] gap-32">
          <motion.div
            className="space-y-24"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-center justify-between mb-16">
              <h2 className="text-3xl font-mono font-bold text-gray-800">Long Division</h2>
              <div className="flex items-center gap-8 text-sm font-mono text-gray-600">
                <TrendingUp className="h-16 w-16 text-teal" />
                <span>{completedCount} Questions</span>
              </div>
            </div>

            {currentQuestion && (
              <QuestionCard
                question={currentQuestion.question}
                topic={currentQuestion.topic}
                difficulty={currentQuestion.difficulty}
                attempts={attempts}
                onSubmit={submitAnswer}
                disabled={loading || generatingVideo}
              />
            )}

            <VideoDisplay
              videoUrl={currentVideoUrl}
              onNextQuestion={loadNextQuestion}
            />

            <AnimatePresence>
              {generatingVideo && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="border-[3px] border-gray-900 rounded-lg p-24"
                  style={{
                    backgroundColor: '#dfe6e9',
                    boxShadow: '6px 6px 0px 0px rgba(0,0,0,1)'
                  }}
                >
                  <div className="flex items-center gap-16">
                    <div className="animate-spin rounded-full h-32 w-32 border-2 border-gray-200 border-t-teal"></div>
                    <div className="flex-1">
                      <h3 className="text-lg font-mono font-semibold text-gray-800 mb-8">Generating Video</h3>
                      <div className="w-full bg-gray-200 rounded-full h-8">
                        <div className="bg-teal h-8 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {offerVideo && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="border-[3px] border-gray-900 rounded-lg p-24"
                  style={{
                    backgroundColor: '#dfe6e9',
                    boxShadow: '6px 6px 0px 0px rgba(0,0,0,1)'
                  }}
                >
                  <div className="flex items-start gap-16">
                    <div className="p-12 bg-amber rounded-lg">
                      <Video className="h-20 w-20 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-mono font-semibold text-gray-800 mb-8">Need Help?</h3>
                      <p className="text-gray-700 mb-16">
                        See a step-by-step video explanation for this problem.
                      </p>
                      <Button
                        onClick={requestVideo}
                        disabled={generatingVideo}
                        className="bg-teal hover:bg-teal-600 text-white font-mono"
                      >
                        <Video className="h-16 w-16 mr-8" />
                        Show Video Explanation
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          <motion.div
            className="sticky top-[120px] h-[calc(100vh-160px)]"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div
              className="border-[3px] border-gray-900 rounded-lg h-full flex flex-col"
              style={{
                backgroundColor: '#dfe6e9',
                boxShadow: '6px 6px 0px 0px rgba(0,0,0,1)'
              }}
            >
              <div className="px-20 py-16 border-b-[3px] border-gray-900">
                <h2 className="text-sm font-mono font-semibold text-gray-800">Assistant</h2>
              </div>
              <div className="flex-1 overflow-y-auto px-20 py-16">
                <motion.div className="space-y-16">
                  {messages.map((msg, index) => (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      <ChatMessage
                        role={msg.role}
                        content={msg.content}
                      />
                    </motion.div>
                  ))}
                  <div ref={messagesEndRef} />
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

export default App
