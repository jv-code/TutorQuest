import { Minus, Plus } from 'lucide-react'

export function DifficultyControl({ difficulty, onDecrease, onIncrease }) {
  return (
    <div className="flex items-center gap-8">
      <span className="text-sm font-mono text-gray-700">Difficulty</span>
      <div className="flex items-center gap-4">
        <button
          onClick={onDecrease}
          disabled={difficulty <= 1}
          className="w-24 h-24 inline-flex items-center justify-center rounded-md bg-[#63B3ED] text-gray-900 border-[2px] border-gray-900 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] active:shadow-none active:translate-x-[2px] active:translate-y-[2px] transition-all duration-150 disabled:opacity-30 disabled:pointer-events-none"
        >
          <Minus className="h-12 w-12" />
        </button>

        <div className="w-32 text-center">
          <span className="text-lg font-mono font-bold text-gray-800">{difficulty}</span>
        </div>

        <button
          onClick={onIncrease}
          disabled={difficulty >= 10}
          className="w-24 h-24 inline-flex items-center justify-center rounded-md bg-[#63B3ED] text-gray-900 border-[2px] border-gray-900 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[1px] hover:translate-y-[1px] active:shadow-none active:translate-x-[2px] active:translate-y-[2px] transition-all duration-150 disabled:opacity-30 disabled:pointer-events-none"
        >
          <Plus className="h-12 w-12" />
        </button>
      </div>
    </div>
  )
}
