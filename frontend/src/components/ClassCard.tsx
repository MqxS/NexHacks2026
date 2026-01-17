import { PenLine } from 'lucide-react'
import { PaperCard } from './PaperCard'
import { cn } from '../lib/utils'

export const ClassCard = ({
  name,
  professor,
  selected,
  onOpen,
  onEdit,
  artUrl,
  variant = 'class'
}: {
  name: string
  professor: string
  selected?: boolean
  onOpen?: () => void
  onEdit?: () => void
  artUrl?: string
  variant?: 'class' | 'create'
}) => {
  return (
    <PaperCard
      className={cn(
        'w-[420px] min-h-[300px] shrink-0 overflow-hidden border border-espresso/15 bg-paper/90 p-0 transition-all',
        selected ? 'shadow-lift -translate-y-2' : 'shadow-paper',
        variant === 'create' && 'border-dashed'
      )}
    >
      <div className="relative h-full min-h-[300px]">
        {artUrl ? (
          <img src={artUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-sand via-paper to-sage/30" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-espresso/90 via-espresso/30 to-transparent" />
        {variant === 'class' && (
          <button
            type="button"
            onClick={onEdit}
            className="absolute right-4 top-4 rounded-full border border-paper/40 bg-paper/80 p-2 text-espresso/80 shadow-paper transition hover:-translate-y-0.5 hover:text-espresso"
          >
            <PenLine className="h-4 w-4" />
          </button>
        )}
        <div className="absolute bottom-0 left-0 right-0 p-5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h3 className="text-2xl font-semibold text-paper">{name}</h3>
              <p className="text-sm text-paper/70">{professor}</p>
            </div>
            <button
              type="button"
              onClick={onOpen}
              className={cn(
                'rounded-full border border-paper/40 bg-paper/90 px-4 py-2 text-sm font-medium text-espresso shadow-paper transition',
                'hover:-translate-y-0.5 hover:bg-paper'
              )}
            >
              {variant === 'create' ? 'Create class' : 'Open'}
            </button>
          </div>
        </div>
      </div>
    </PaperCard>
  )
}
