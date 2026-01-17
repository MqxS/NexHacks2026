import type { ReactNode } from 'react'
import { cn } from '../lib/utils'

export const PaperCard = ({
  children,
  className
}: {
  children: ReactNode
  className?: string
}) => {
  return (
    <div className={cn('graph-panel relative rounded-2xl p-6', className)}>
      <div className="relative z-10">{children}</div>
    </div>
  )
}
