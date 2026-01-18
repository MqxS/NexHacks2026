import { Trash2 } from 'lucide-react'
import { PaperCard } from './PaperCard'
import { cn } from '../lib/utils'

export const SessionCard = ({
  title,
  subtitle,
  tags,
  onResume,
  onDelete
}: {
  title: string
  subtitle?: string
  tags: string[]
  onResume?: () => void
  onDelete?: () => void
}) => {
  return (
    <PaperCard className="h-[200px] w-[240px] shrink-0 border border-espresso/15 bg-paper/90">
      <div className="flex h-full flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-espresso">{title}</p>
            {subtitle ? <p className="mt-1 text-xs text-espresso/60">{subtitle}</p> : null}
          </div>
          {onDelete ? (
            <button
              type="button"
              onClick={onDelete}
              aria-label="Delete session"
              className="rounded-full border border-espresso/20 p-2 text-espresso transition hover:-translate-y-0.5 hover:bg-sand"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          ) : null}
        </div>
        <div className="flex flex-1 flex-wrap content-start gap-2 min-h-[48px] max-h-[72px] overflow-y-auto pr-1 scrollbar-hide">
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-sage/20 px-2 py-1 text-[11px] font-medium text-espresso/70"
            >
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <button
            type="button"
            onClick={onResume}
            className={cn(
              'rounded-full border border-espresso/20 px-3 py-1 text-xs font-medium text-espresso transition hover:-translate-y-0.5 hover:bg-sand'
            )}
          >
            Resume
          </button>
        </div>
      </div>
    </PaperCard>
  )
}
