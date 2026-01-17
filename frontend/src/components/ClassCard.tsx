import { PenLine } from 'lucide-react'
import { PaperCard } from './PaperCard'
import { cn } from '../lib/utils'

export const ClassCard = ({
  name,
  professor,
  selected,
  onOpen,
  onEdit,
  variant = 'class'
}: {
  name: string
  professor: string
  selected?: boolean
  onOpen?: () => void
  onEdit?: () => void
  variant?: 'class' | 'create'
}) => {
  return (
    <PaperCard
      className={cn(
        'w-[420px] min-h-[300px] shrink-0 border border-espresso/15 bg-paper/90 transition-all',
        selected ? 'shadow-lift -translate-y-2' : 'shadow-paper',
        variant === 'create' && 'border-dashed'
      )}
    >
      <div className="flex h-full flex-col gap-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-semibold text-espresso">{name}</h3>
            <p className="text-sm text-espresso/70">{professor}</p>
          </div>
          {variant === 'class' && (
            <button
              type="button"
              onClick={onEdit}
              className="rounded-full border border-espresso/20 bg-sand p-2 text-espresso/70 transition hover:-translate-y-0.5 hover:text-espresso"
            >
              <PenLine className="h-4 w-4" />
            </button>
          )}
        </div>
        <span className="inline-flex w-fit items-center rounded-full bg-sage/20 px-3 py-1 text-xs font-medium text-espresso">
          Ready to study
        </span>
        <button
          type="button"
          onClick={onOpen}
          className={cn(
            'mt-auto rounded-full border border-espresso/20 px-4 py-2 text-sm font-medium text-espresso shadow-paper transition',
            'hover:-translate-y-0.5 hover:bg-sand'
          )}
        >
          {variant === 'create' ? 'Create class' : 'Open'}
        </button>
      </div>
    </PaperCard>
  )
}
