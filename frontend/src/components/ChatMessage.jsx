import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { motion } from 'framer-motion'

export function ChatMessage({ role, content }) {
  const isUser = role === 'user'

  return (
    <motion.div
      className="flex flex-col gap-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {!isUser && (
        <div className="text-xs font-mono font-semibold text-gray-500 uppercase tracking-wide">
          Assistant
        </div>
      )}
      <div className={isUser ? 'bg-gray-50 rounded-lg p-12' : 'border-l-2 border-teal pl-16'}>
        {content && (
          <ReactMarkdown
            remarkPlugins={[remarkMath]}
            rehypePlugins={[rehypeKatex]}
            className="prose prose-sm max-w-none text-gray-700 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:leading-relaxed"
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </motion.div>
  )
}
