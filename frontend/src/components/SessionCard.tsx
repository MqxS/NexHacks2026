import {PaperCard} from './PaperCard'
import {cn} from '../lib/utils'

export const SessionCard = ({
  title,
  subtitle,
  tags,
  onResume
}: {
  title: string
  subtitle?: string
  tags: string[]
  onResume?: () => void
}) => {
  return (
    <PaperCard className="w-[220px] shrink-0 border border-espresso/15 bg-paper/90">
      <div className="flex h-full flex-col gap-3">
        <div>
          <p className="text-sm font-medium text-espresso">{title}</p>
          {subtitle ? <p className="mt-1 text-xs text-espresso/60">{subtitle}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-sage/20 px-2 py-1 text-[11px] font-medium text-espresso/70"
            >
              {tag}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={onResume}
          className={cn(
            'mt-auto rounded-full border border-espresso/20 px-3 py-1 text-xs font-medium text-espresso transition hover:-translate-y-0.5 hover:bg-sand'
          )}
        >
          Resume
        </button>
      </div>
    </PaperCard>
  )
}
