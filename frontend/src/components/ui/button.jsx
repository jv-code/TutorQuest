import * as React from 'react'
import { cn } from '@/lib/utils'

const Button = React.forwardRef(
  ({ className, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-lg font-mono font-semibold',
          'bg-[#63B3ED] text-gray-900 border-[3px] border-gray-900',
          'shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]',
          'hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px]',
          'active:shadow-none active:translate-x-[4px] active:translate-y-[4px]',
          'transition-all duration-150',
          'disabled:opacity-50 disabled:pointer-events-none',
          'px-16 py-8 text-sm',
          className
        )}
        ref={ref}
        disabled={disabled}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
