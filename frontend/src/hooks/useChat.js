import { useState, useEffect } from 'react'
import { useUser } from '@clerk/clerk-react'
import * as api from '@/lib/api'

export function useChat() {
  const { user, isLoaded } = useUser()
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [attempts, setAttempts] = useState(0)
  const [loading, setLoading] = useState(false)
  const [offerVideo, setOfferVideo] = useState(null)
  const [generatingVideo, setGeneratingVideo] = useState(false)
  const [showConfetti, setShowConfetti] = useState(false)
  const [currentVideoUrl, setCurrentVideoUrl] = useState(null)
  const [userDifficulty, setUserDifficulty] = useState(() => {
    const stored = localStorage.getItem('poocho_difficulty')
    return stored ? parseInt(stored) : 1
  })

  useEffect(() => {
    if (isLoaded && user) {
      initSession()
    }
  }, [isLoaded, user])

  async function initSession() {
    if (!user) return
    const session = await api.createSession(user.id)
    const sid = session.session_id
    setSessionId(sid)
    await loadNextQuestion(sid)
  }

  async function loadNextQuestion(sid) {
    const effectiveSessionId = sid || sessionId
    if (!effectiveSessionId || typeof effectiveSessionId !== 'string') {
      console.error('Invalid session ID:', effectiveSessionId)
      return
    }
    // Auto level is now default - pass null to use backend auto-scaling
    // Change to userDifficulty to enable manual difficulty control
    const question = await api.getNextQuestion(effectiveSessionId, null)
    setCurrentQuestion(question)
    setAttempts(0)
    setOfferVideo(null)
    setCurrentVideoUrl(null)
  }

  function updateDifficulty(newDifficulty) {
    const difficulty = Math.max(1, Math.min(10, newDifficulty))
    setUserDifficulty(difficulty)
    localStorage.setItem('poocho_difficulty', difficulty.toString())
    loadNextQuestion()
  }

  async function submitAnswer(answer) {
    if (!currentQuestion) return

    setLoading(true)

    const result = await api.validateAnswer(sessionId, currentQuestion.question_id, answer)
    setAttempts(result.attempts)

    setMessages(prev => [
      ...prev,
      { id: Date.now(), role: 'user', content: answer },
      { id: Date.now() + 1, role: 'assistant', content: result.feedback }
    ])

    if (result.offer_video) {
      setOfferVideo({
        questionId: currentQuestion.question_id,
        question: result.question,
        topic: result.topic
      })
    }

    if (result.correct) {
      setOfferVideo(null)
      setShowConfetti(true)
      setTimeout(() => {
        setShowConfetti(false)
        loadNextQuestion()
      }, 2000)
    }

    setLoading(false)
  }

  async function requestVideo() {
    if (!offerVideo) return

    const questionId = offerVideo.questionId
    setOfferVideo(null)
    setGeneratingVideo(true)

    const loadingMsgId = Date.now()
    setMessages(prev => [...prev, {
      id: loadingMsgId,
      role: 'assistant',
      content: 'Generating video explanation...',
      loading: true
    }])

    try {
      const result = await api.generateVideo(sessionId, questionId)

      if (result.status === 'completed' && result.video_url) {
        setCurrentVideoUrl(result.video_url)
        setMessages(prev => prev.map(msg =>
          msg.id === loadingMsgId
            ? { ...msg, content: 'Video explanation ready! See below.', loading: false }
            : msg
        ))
      } else {
        setMessages(prev => prev.map(msg =>
          msg.id === loadingMsgId
            ? { ...msg, content: `Failed to generate video: ${result.error || 'Unknown error'}`, loading: false }
            : msg
        ))
      }
    } catch (error) {
      setMessages(prev => prev.map(msg =>
        msg.id === loadingMsgId
          ? { ...msg, content: `Error generating video: ${error.message}`, loading: false }
          : msg
      ))
    }

    setGeneratingVideo(false)
  }

  async function sendChatMessage(content) {
    setLoading(true)
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content }])

    const response = await api.sendMessage(sessionId, content)
    setMessages(prev => [...prev, { id: Date.now(), ...response.message }])

    setLoading(false)
  }

  return {
    sessionId,
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
    sendChatMessage,
    loadNextQuestion,
    updateDifficulty
  }
}
